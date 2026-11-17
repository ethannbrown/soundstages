import json
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest
import requests

import config
from fake_api import Resp

# Pins how albums.py, tracks.py, features.py and ids.py react to each API response
# Each collector runs for real in tmp_path with a fake requests.get; no network, no data folders

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://api.reccobeats.com/v1'


def run(collector, paths, tmp_path, monkeypatch):
    for name, path in paths.items():
        assert tmp_path in path.parents
        monkeypatch.setattr(config, name, path)
    monkeypatch.setattr(sys, 'argv', [collector.script])
    runpy.run_path(str(ROOT / 'src' / 'collect' / collector.script), run_name='__main__')


# What each collector reads, where it writes, and what a good response looks like.
# An item is an artist (albums.py), an album (tracks.py) or a batch (features.py).


class Albums:
    script = 'albums.py'
    out = 'ALBUMS'
    log = 'LOG_A'

    def setup(self, tmp_path, items):
        pd.DataFrame({'id': items, 'uuid': items}).to_parquet(tmp_path / 'ids.parquet')
        return {
            'IDS': tmp_path / 'ids.parquet',
            'ALBUMS': tmp_path / 'albums.parquet',
            'LOG_A': tmp_path / 'logA.json',
        }

    def url(self, item, page=0):
        return f'{BASE}/artist/{item}/album?page={page}&size=50'

    def body(self, item, page=0, pages=1):
        return {
            'totalPages': pages,
            'content': [
                {
                    'id': f'{item}-al{page}',
                    'name': 'Album',
                    'albumType': 'album',
                    'releaseDate': '2020-01-01',
                    'popularity': 50,
                    'artists': [{'name': 'Artist', 'id': item}],
                    'totalTracks': 10,
                }
            ],
        }

    def rows(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def logged(self, path):
        return {r['uuid'] for r in self.rows(path)} if path.exists() else set()


class Tracks:
    script = 'tracks.py'
    out = 'TRACKS'
    log = 'LOG_T'

    def setup(self, tmp_path, items):
        pd.DataFrame({'albumID': items, 'uuid': [f'{i}-artist' for i in items]}).to_parquet(
            tmp_path / 'albums_clean.parquet'
        )
        return {
            'ALBUMS_CLEAN': tmp_path / 'albums_clean.parquet',
            'TRACKS': tmp_path / 'tracks.parquet',
            'LOG_T': tmp_path / 'logT.json',
        }

    def url(self, item, page=0):
        return f'{BASE}/album/{item}/track?page={page}&size=50'

    def body(self, item, page=0, pages=1):
        return {
            'totalPages': pages,
            'content': [
                {
                    'id': f'{item}-t{page}',
                    'trackTitle': 'Song',
                    'durationMs': 200000,
                    'popularity': 40,
                    'isrc': 'USABC',
                    'artists': [{'name': 'Artist', 'id': 'a1'}],
                }
            ],
        }

    def rows(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def logged(self, path):
        return {r['albumID'] for r in self.rows(path)} if path.exists() else set()


FEATS = [
    'acousticness',
    'danceability',
    'energy',
    'instrumentalness',
    'key',
    'liveness',
    'loudness',
    'mode',
    'speechiness',
    'tempo',
    'valence',
]


class Features:
    script = 'features.py'
    out = 'FEATURES'
    log = 'LOG_F'

    # 40 tracks per request; 'ok' is a full batch, every other item a batch of one
    def tracks(self, item):
        return [f'{item}-{i}' for i in range(40)] if item == 'ok' else [f'{item}-0']

    def setup(self, tmp_path, items):
        ids = [t for item in items for t in self.tracks(item)]
        pd.DataFrame({'trackID': ids}).to_parquet(tmp_path / 'tracks_clean.parquet')
        return {
            'TRACKS_CLEAN': tmp_path / 'tracks_clean.parquet',
            'FEATURES': tmp_path / 'features.parquet',
            'LOG_F': tmp_path / 'logF.csv',
        }

    def url(self, item, page=0):
        return f'{BASE}/audio-features?ids={",".join(self.tracks(item))}'

    def body(self, item, page=0, pages=1):
        return {'content': [{'id': t, **{f: 0.5 for f in FEATS}, 'key': 2, 'mode': 1} for t in self.tracks(item)]}

    def rows(self, path):
        return pd.read_csv(path)

    def logged(self, path):
        return {t.split('-')[0] for t in self.rows(path)['trackID']}


class Ids:
    script = 'ids.py'
    out = 'IDS'
    log = 'LOG_R'

    # 40 artists per request; 'ok' is a full batch, every other item a batch of one
    def artists(self, item):
        return [f'{item}-{i}' for i in range(40)] if item == 'ok' else [f'{item}-0']

    def setup(self, tmp_path, items):
        ids = [a for item in items for a in self.artists(item)]
        pd.DataFrame({'id': ids}).to_parquet(tmp_path / 'artists.parquet')
        return {
            'ARTISTS': tmp_path / 'artists.parquet',
            'IDS': tmp_path / 'ids.parquet',
            'LOG_R': tmp_path / 'logR.csv',
        }

    def url(self, item, page=0):
        return f'{BASE}/artist?ids={",".join(self.artists(item))}'

    def body(self, item, page=0, pages=1):
        return {
            'content': [{'id': f'r-{a}', 'href': f'https://open.spotify.com/artist/{a}'} for a in self.artists(item)]
        }

    def rows(self, path):
        return pd.read_csv(path)

    def logged(self, path):
        return {a.split('-')[0] for a in self.rows(path)['spotify']}


COLLECTORS = {
    'albums': Albums(),
    'tracks': Tracks(),
    'features': Features(),
    'ids': Ids(),
}


def responses(collector, case, item):
    ok = Resp(200, collector.body(item))
    return {
        '404': [Resp(404)],
        '429 then ok': [Resp(429, headers={'Retry-After': '7'}), ok],
        '429 no header then ok': [Resp(429), ok],
        '500 then ok': [Resp(500), ok],
        '500 exhausted': [Resp(500)],
        'connection error': [requests.ConnectionError('reset')],
        '429 exhausted': [Resp(429)],
        '403': [Resp(403)],
    }[case]


# Two items side by side: 'ok' always succeeds, 'case' gets the response under test.
# Columns: collector, case, is 'case' in the log, is the output parquet written
@pytest.mark.parametrize(
    'name, case, logged, written',
    [
        ('albums', '404', False, True),
        ('tracks', '404', False, True),
        ('features', '404', True, True),
        ('albums', '429 then ok', True, True),
        ('tracks', '429 then ok', True, True),
        ('features', '429 then ok', True, True),
        ('albums', '500 then ok', True, True),
        ('tracks', '500 then ok', True, True),
        ('features', '500 then ok', True, True),
        ('albums', '500 exhausted', False, False),
        ('tracks', '500 exhausted', False, False),
        ('features', '500 exhausted', False, False),
        ('albums', 'connection error', False, False),
        ('tracks', 'connection error', False, False),
        ('features', 'connection error', False, False),
        ('ids', '404', False, True),
        ('ids', '429 then ok', True, True),
        ('ids', '500 then ok', True, True),
        ('ids', '500 exhausted', False, False),
        ('ids', 'connection error', False, False),
    ],
)
def test_two_items(api, tmp_path, monkeypatch, name, case, logged, written):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['ok', 'case'])
    api.responses[collector.url('ok')] = [Resp(200, collector.body('ok'))]
    api.responses[collector.url('case')] = responses(collector, case, 'case')

    run(collector, paths, tmp_path, monkeypatch)

    expected = {'ok', 'case'} if logged else {'ok'}
    assert collector.logged(paths[collector.log]) == expected
    assert paths[collector.out].exists() == written


# 429 and 403 stop the whole run; one item keeps thread order out of it
# Columns: collector, case, calls made
@pytest.mark.parametrize(
    'name, case, calls',
    [
        ('albums', '429 exhausted', 4),
        ('tracks', '429 exhausted', 4),
        ('features', '429 exhausted', 4),
        ('albums', '403', 1),
        ('tracks', '403', 1),
        ('features', '403', 1),
        ('ids', '429 exhausted', 4),
        ('ids', '403', 1),
    ],
)
def test_stops(api, tmp_path, monkeypatch, name, case, calls):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['case'])
    api.responses[collector.url('case')] = responses(collector, case, 'case')

    run(collector, paths, tmp_path, monkeypatch)

    assert len(api.calls) == calls
    assert collector.logged(paths[collector.log]) == set()
    assert not paths[collector.out].exists()


# How long each collector waits before retrying
@pytest.mark.parametrize('name', COLLECTORS)
@pytest.mark.parametrize(
    'case, wait',
    [('429 then ok', 7), ('429 no header then ok', 30), ('500 then ok', 45)],
)
def test_waits(api, tmp_path, monkeypatch, name, case, wait):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['case'])
    api.responses[collector.url('case')] = responses(collector, case, 'case')

    run(collector, paths, tmp_path, monkeypatch)

    assert wait in api.sleeps


# First try plus MAX_RETRIES (3) retries, 45 s apart
@pytest.mark.parametrize('name', COLLECTORS)
def test_retries(api, tmp_path, monkeypatch, name):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['ok', 'case'])
    api.responses[collector.url('ok')] = [Resp(200, collector.body('ok'))]
    api.responses[collector.url('case')] = [Resp(500)]

    run(collector, paths, tmp_path, monkeypatch)

    assert api.calls.count(collector.url('case')) == 4
    assert api.sleeps.count(45) == 3


# Multi-page items: every page is fetched and logged
@pytest.mark.parametrize('name', ['albums', 'tracks'])
def test_pages(api, tmp_path, monkeypatch, name):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['case'])
    api.responses[collector.url('case', 0)] = [Resp(200, collector.body('case', 0, pages=2))]
    api.responses[collector.url('case', 1)] = [Resp(200, collector.body('case', 1, pages=2))]

    run(collector, paths, tmp_path, monkeypatch)

    assert len(collector.rows(paths[collector.log])) == 2
    assert paths[collector.out].exists()


# Each page gets its own retry budget; 3 retries on page 0 and 1 on page 1 is fine
# Columns: collector, is the album/artist logged, is the output parquet written
@pytest.mark.parametrize(
    'name, logged, written',
    [
        ('albums', True, True),
        ('tracks', True, True),
    ],
)
def test_retry_budget_across_pages(api, tmp_path, monkeypatch, name, logged, written):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['case'])
    page0 = Resp(200, collector.body('case', 0, pages=2))
    page1 = Resp(200, collector.body('case', 1, pages=2))
    api.responses[collector.url('case', 0)] = [Resp(429)] * 3 + [page0]
    api.responses[collector.url('case', 1)] = [Resp(429), page1]

    run(collector, paths, tmp_path, monkeypatch)

    assert collector.logged(paths[collector.log]) == ({'case'} if logged else set())
    assert paths[collector.out].exists() == written


# After an incomplete run, the next run asks only for what is missing,
# then writes the parquet
@pytest.mark.parametrize('name', COLLECTORS)
def test_rerun_after_connection_error(api, tmp_path, monkeypatch, name):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['ok', 'case'])
    api.responses[collector.url('ok')] = [Resp(200, collector.body('ok'))]
    api.responses[collector.url('case')] = [requests.ConnectionError('reset')]

    run(collector, paths, tmp_path, monkeypatch)
    assert not paths[collector.out].exists()

    api.calls.clear()
    api.responses[collector.url('case')] = [Resp(200, collector.body('case'))]
    run(collector, paths, tmp_path, monkeypatch)

    assert api.calls == [collector.url('case')]
    assert collector.logged(paths[collector.log]) == {'ok', 'case'}
    assert paths[collector.out].exists()


# An incomplete run says so
@pytest.mark.parametrize('name', COLLECTORS)
def test_early_stoppage_message(api, tmp_path, monkeypatch, capsys, name):
    collector = COLLECTORS[name]
    paths = collector.setup(tmp_path, ['case'])
    api.responses[collector.url('case')] = [Resp(500)]

    run(collector, paths, tmp_path, monkeypatch)

    assert 'Early stoppage, requires rerun.' in capsys.readouterr().out


# Row contents, pinned


def test_album_rows(api, tmp_path, monkeypatch):
    collector = Albums()
    paths = collector.setup(tmp_path, ['a1', 'a2'])
    api.responses[collector.url('a1')] = [Resp(200, collector.body('a1'))]
    api.responses[collector.url('a2')] = [Resp(200, {'totalPages': 0, 'content': []})]

    run(collector, paths, tmp_path, monkeypatch)

    rows = sorted(collector.rows(paths['LOG_A']), key=lambda r: r['uuid'])
    assert rows == [
        {
            'uuid': 'a1',
            'albumID': 'a1-al0',
            'title': 'Album',
            'type': 'album',
            'released': '2020-01-01',
            'popularity': 50,
            'artists': [{'name': 'Artist', 'uuid': 'a1'}],
            'tracks': 10,
        },
        {
            'uuid': 'a2',
            'albumID': None,
            'title': None,
            'type': None,
            'released': None,
            'popularity': None,
            'artists': None,
            'tracks': None,
        },
    ]
    assert len(pd.read_parquet(paths['ALBUMS'])) == 2


def test_track_rows(api, tmp_path, monkeypatch):
    collector = Tracks()
    paths = collector.setup(tmp_path, ['al1', 'al2'])
    api.responses[collector.url('al1')] = [Resp(200, collector.body('al1'))]
    api.responses[collector.url('al2')] = [Resp(200, {'totalPages': 0, 'content': []})]

    run(collector, paths, tmp_path, monkeypatch)

    rows = sorted(collector.rows(paths['LOG_T']), key=lambda r: r['albumID'])
    assert rows == [
        {
            'albumID': 'al1',
            'uuid': 'al1-artist',
            'trackID': 'al1-t0',
            'title': 'Song',
            'duration': 200000,
            'popularity': 40,
            'isrc': 'USABC',
            'artists': [{'name': 'Artist', 'id': 'a1'}],
        },
        {
            'albumID': 'al2',
            'uuid': 'al2-artist',
            'trackID': None,
            'title': None,
            'duration': None,
            'popularity': None,
            'isrc': None,
            'artists': None,
        },
    ]
    df = pd.read_parquet(paths['TRACKS'])
    assert str(df['popularity'].dtype) == 'Int64'
    assert str(df['duration'].dtype) == 'Int64'


def test_feature_rows(api, tmp_path, monkeypatch):
    collector = Features()
    paths = collector.setup(tmp_path, ['b'])
    # Helpers can't make two tracks in one batch; built here
    pd.DataFrame({'trackID': ['t1', 't2']}).to_parquet(paths['TRACKS_CLEAN'])
    found = {'id': 't1', **{f: 0.5 for f in FEATS}, 'key': 2, 'mode': 1}
    api.responses[f'{BASE}/audio-features?ids=t1,t2'] = [Resp(200, {'content': [found]})]

    run(collector, paths, tmp_path, monkeypatch)

    log = collector.rows(paths['LOG_F'])
    assert list(log.columns) == ['trackID'] + FEATS
    assert log.set_index('trackID').loc['t1'].tolist() == [0.5] * 4 + [2] + [0.5] * 2 + [1] + [0.5] * 3
    assert log.set_index('trackID').loc['t2'].isna().all()
    df = pd.read_parquet(paths['FEATURES'])
    assert str(df['key'].dtype) == 'Int64'
    assert str(df['mode'].dtype) == 'Int64'


# ids.py writes the Spotify to ReccoBeats mapping to its own file and leaves
# artists.parquet alone. An artist the API doesn't return gets no uuid.
def test_id_rows(api, tmp_path, monkeypatch):
    artists = pd.DataFrame({'id': ['s1', 's2'], 'name': ['A', 'B']})
    artists.to_parquet(tmp_path / 'artists.parquet')
    paths = {
        'ARTISTS': tmp_path / 'artists.parquet',
        'IDS': tmp_path / 'ids.parquet',
        'LOG_R': tmp_path / 'logR.csv',
    }
    found = {'id': 'r1', 'href': 'https://open.spotify.com/artist/s1'}
    api.responses[f'{BASE}/artist?ids=s1,s2'] = [Resp(200, {'content': [found]})]

    run(Ids(), paths, tmp_path, monkeypatch)

    ids = pd.read_parquet(paths['IDS'])
    assert list(ids.columns) == ['id', 'uuid']
    assert ids['id'].tolist() == ['s1', 's2']
    assert ids['uuid'].iloc[0] == 'r1'
    assert pd.isna(ids['uuid'].iloc[1])
    pd.testing.assert_frame_equal(pd.read_parquet(paths['ARTISTS']), artists)
