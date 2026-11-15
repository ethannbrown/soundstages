import pytest

# Pins the title rules in clean_tracks.py as they are today.


# Songs with near identical audio, matched only inside brackets or after a spaced dash
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Hampstead Girl - Instrumental', True),
        ('Song (Inst.)', True),
        ('Song (Off Vocal)', True),
        ('Song - Off Vocal', True),
        ('Song (Radio Edit)', True),
        ('Song (Sped Up)', True),
        ('Swang (Screwed)', True),
        ('Song - Chopped & Screwed', True),
        ('Song (Chopped and Screwed)', True),
        ('Song (feat. Z-Ro of Screwed Up Click)', False),
        ('Okay - Acapella', True),
        ('Song (A Cappella)', True),
        ('Song (Accapella)', True),
        ('Song - Acappella', True),
        ('Mr. Clean', False),
        ('Instrumental Song', False),
        ('Song (Live)', False),
    ],
)
def test_near_copies(rules, title, expected):
    assert bool(rules.NEAR_COPIES.search(title)) == expected


# 'clean' is a whole word, and Clean Bandit is an artist, not a clean edit
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Song (Clean)', True),
        ('Song - Clean Album Version', True),
        ('Song - Clean Edit', True),
        ('Song (Clean Ver.)', True),
        ('Song (Remix) - Cleaned', True),
        ('Say It (Clean Bandit Remix)', False),
        ('Tell Me (feat. Clean Bandit)', False),
        ('Runaway (The Juan MacLean Remix)', False),
        ('Beacon - Street Cleaner Remix', False),
        ('Alone (Cleanse)', False),
    ],
)
def test_near_copies_clean(rules, title, expected):
    assert bool(rules.NEAR_COPIES.search(title)) == expected


# A near-copy is only dropped when the artist has an original with the same base
@pytest.mark.parametrize(
    'copy, original',
    [
        ('Hampstead Girl - Instrumental', 'Hampstead Girl'),
        ('Song (Off Vocal)', 'Song'),
        ('Song [Karaoke Version]', 'Song'),
        ('Won’t Stop (Instrumental)', "Won't Stop"),
    ],
)
def test_near_copy_shares_base(rules, copy, original):
    assert rules.NEAR_COPIES.search(copy)
    assert rules.base(copy) == rules.base(original)


# DJ mixes and spoken commentary
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Song (Mixed)', True),
        ('Song - Mix Cut', True),
        ('A State Of Trance (ASOT 1000) - Shout Outs, Pt. 3', True),
        ('Song (Track Commentary)', True),
        ('Song (Interview)', True),
        ('Mixed Feelings', False),
        ('Interview With the Vampire', False),
        ('Song (Extended Mix)', False),
    ],
)
def test_not_songs(rules, title, expected):
    assert bool(rules.NOT_SONGS.search(title)) == expected


# Labels count only inside brackets or after a dash with a space before it
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Song (Instrumental)', True),
        ('Song [Instrumental]', True),
        ('Song - Instrumental', True),
        ('Song – Instrumental', True),
        ('Song — Instrumental', True),
        ('Song -Instrumental', True),
        ('Song (INSTRUMENTAL)', True),
        ('Song-Instrumental', False),
        ('Instrumental', False),
        ('Mr. Clean', False),
    ],
)
def test_in_label(rules, title, expected):
    assert bool(rules.in_label('instrumental|clean').search(title)) == expected


# Strips only labels that don't change the recording
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Song', 'song'),
        ('Song - Remastered 2011', 'song'),
        ('Song (2011 Remaster)', 'song'),
        ('Song [Remastered Version]', 'song'),
        ('Song - 2009 Digital Remaster', 'song'),
        ('Song (Single Version)', 'song'),
        ('Song (Mono)', 'song'),
        ('Song (feat. X)', 'song'),
        ('Song (with X)', 'song'),
        ('Song - Original Mix', 'song'),
        ('Song (Original Mix)', 'song'),
        ('Song (Original)', 'song'),
        ('Song - Original', 'song'),
        ('Song (Original Soundtrack)', 'song (original soundtrack)'),
        ('Song - Pista Original', 'song - pista original'),
        ('Song - Extended Original Mix', 'song - extended original mix'),
        ('Song (Live)', 'song (live)'),
        ('Song (Acoustic)', 'song (acoustic)'),
        ('Song - Demo', 'song - demo'),
        ('Song (Remix)', 'song (remix)'),
        ('Song (Without You)', 'song (without you)'),
        ('Song (Live) - Remastered', 'song (live)'),
        ('Rock & Roll', 'rock and roll'),
    ],
)
def test_recording_key(rules, title, expected):
    assert rules.recording_key(title) == expected


# Likely wrong, pinned as is
@pytest.mark.parametrize(
    'title, expected',
    [
        # No space after the dash, so the label isn't stripped
        ('Song -Remastered', 'song -remastered'),
    ],
)
def test_recording_key_gaps(rules, title, expected):
    assert rules.recording_key(title) == expected


def test_recording_key_curly_apostrophe(rules):
    assert rules.recording_key('Won’t Stop') == rules.recording_key("Won't Stop")


# Strips every label
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Song', 'song'),
        ('Song (Live)', 'song'),
        ('Song [Instrumental]', 'song'),
        ('Song - Live at Wembley', 'song'),
        ('Song (feat. X) - Remix', 'song'),
        ('  Song   Title  ', 'song title'),
        ('Rock & Roll', 'rock and roll'),
        ('Won’t Stop', "won't stop"),
        ('Song -Live', 'song -live'),
        (None, ''),
        (float('nan'), ''),
    ],
)
def test_base(rules, title, expected):
    assert rules.base(title) == expected


# Generic titles never merge; matched against the lowercased base
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Intro', True),
        ('Outro (Live)', True),
        ('Interlude 2', True),
        ('Untitled 7', True),
        ('Track 3', True),
        ('Hidden Track', True),
        ('Introduction', False),
        ('Intro to Love', False),
        ('Reprise of the Night', False),
    ],
)
def test_generic(rules, title, expected):
    assert bool(rules.GENERIC.match(rules.base(title))) == expected


def test_generic_needs_lowercase(rules):
    assert not rules.GENERIC.match('Intro')


# Album titles: strips edition labels so reissues of one album match
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Abbey Road (Remastered 2009)', 'abbey road'),
        ('Album (Deluxe Edition)', 'album'),
        ('Album - Super Deluxe Version', 'album'),
        ('Album (20th Anniversary Edition)', 'album'),
        ('Album [Explicit]', 'album'),
        ('Album (feat. X)', 'album'),
        ('Album (Live)', 'album (live)'),
        ('Album & More', 'album and more'),
        ('Mr. Clean', 'mr. clean'),
    ],
)
def test_album_normalize_title(album_rules, title, expected):
    assert album_rules.normalize_title(title) == expected


def test_album_normalize_title_nan(album_rules):
    assert album_rules.normalize_title(None) is None
