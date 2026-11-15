import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

sys.path.append('.') # Run from project root
from api import get
from config import ALBUMS_CLEAN, LOG_T, TRACKS

done = set()
try:
    prev = pd.read_json(LOG_T, orient='records', lines=True)
    done = set(prev['albumID'])
except FileNotFoundError:
    pass

albums = pd.read_parquet(ALBUMS_CLEAN)
cols = ['albumID', 'uuid', 'trackID', 'title', 'duration', 'popularity', 'isrc', 'artists']

# Returns list of all tracks on an album
def get_tracks(iden: str, uuid: str) -> list | int:
    total, page = None, 0

    tracks = []
    while total is None or page < total:
        url = f'https://api.reccobeats.com/v1/album/{iden}/track?page={page}&size=50'
        data = get(url, stop)

        # 404: skipped, and asked for again on the next run
        if data is None:
            print(f'HTTP 404 error for {iden}.')
            return None

        # A sentinel from api.get, -1 to -4
        if isinstance(data, int):
            return data

        total = data['totalPages']

        if not data['content']:
            row = {col: None for col in cols}
            row['albumID'], row['uuid'] = iden, uuid
            return [row]

        for track in data['content']:
            row = {
                'albumID': iden,
                'uuid': uuid,
                'trackID': track['id'],
                'title': track['trackTitle'],
                'duration': track['durationMs'],
                'popularity': track['popularity'],
                'isrc': track['isrc'],
                'artists': [{'name': a['name'], 'id': a['id']} for a in track['artists']]
            }
            tracks.append(row)

        page += 1

    return tracks

stop = threading.Event()
todo = [(a, u) for a, u in zip(albums['albumID'], albums['uuid']) if a not in done]

count = 0
start = time.time()
completed = True

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(get_tracks, a, u): a for a, u in todo}

    for fut in as_completed(futures):
        iden = futures[fut]

        try:
            rows = fut.result()
        except Exception as e:
            print(f'{iden} failed: {e}')
            completed = False
            continue

        if rows == -1:
            print(f'HTTP 429 error on {iden}. Breaking.')
            stop.set()
            completed = False
            continue

        if rows == -2:
            print('HTTP 403 error, forbidden. Breaking.')
            stop.set()
            completed = False
            continue

        if rows in (-3, -4):
            completed = False
            continue

        # 404: nothing to log, asked for again on the next run
        if rows is None:
            continue

        with open(LOG_T, 'a') as f:
            f.write('\n'.join(json.dumps(r) for r in rows) + '\n')

        count += 1
        if count % 1000 == 0:
            minutes = (time.time() - start) / 60
            print(f'{len(done) + count} albums')

if completed:
    df = pd.read_json(LOG_T, lines=True)
    df['popularity'] = df['popularity'].astype('Int64')
    df['duration'] = df['duration'].astype('Int64')
    df.to_parquet(TRACKS)
else:
    print('Early stoppage, requires rerun.')
