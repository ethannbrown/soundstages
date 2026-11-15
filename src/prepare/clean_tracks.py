import sys, re, unicodedata
import numpy as np
import pandas as pd

sys.path.append('.') # Run from project root
from config import TRACKS, ALBUMS_CLEAN, TRACKS_CLEAN

# Only matches track "labels" within brackets or after a dash
def in_label(words):
    bracket = rf'[\(\[][^\)\]]*(?:{words})[^\)\]]*[\)\]]'
    dash = rf'\s+[-–—]\s*[^-–—]*(?:{words})'
    return re.compile(f'{bracket}|{dash}', re.I)

# Songs with near identical audio
NEAR_COPIES = in_label(r'instrumental|\binst\b\.?|off[\s-]?vocal|a\s*cappella|karaoke|clean(?:\s+version)?|edited'
                      r'|radio\s+edit|sped[\s-]?up|slowed|nightcore|\b8d\b|tv\s*size')

# e.g., J mixes, spoken commentary
NOT_SONGS = in_label(r'\basot\s*\d+|\bmixed\b|mix\s+cut|continuous(?:\s+dj)?\s+mix|commentary|interview')

# Labels that don't change the recording at all
NEUTRAL = (r'remaster\w*|\d{4}\s+(?:digital\s+)?remaster\w*|single\s+version|album\s+version|original\s+version'
           r'|mono|stereo|explicit|bonus\s+track|feat\.?|ft\.?|featuring|with\s')

# Common track title labels; shared by a multitude of records
GENERIC = re.compile(r'^(?:intro|outro|interlude|skit|untitled|prelude|reprise|theme|hidden track'
                     r'|bonus track|track \d+|(?:intro|outro|interlude|untitled) \d+)$')

# Features (obviously)
FEAT = re.compile(r'[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s', re.I)

def clean_text(title):
    s = unicodedata.normalize('NFKC', title).lower()
    for a, b in [('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('&', ' and ')]:
        s = s.replace(a, b)
    return s

# Strips every label for a normalized dataset
def base(title):
    if pd.isna(title):
        return ''
    s = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', clean_text(title))
    s = re.sub(r'\s+[-–—]\s+.*$', '', s)
    return re.sub(r'\s+', ' ', s).strip()

# Recording key: strip only NEUTRAL labels, so "Song - Remastered" matches "Song" but "Song (Live)" doesn't
def recording_key(title):
    if pd.isna(title):
        return ''
    s = re.sub(rf'\s*[\(\[][^\)\]]*(?:{NEUTRAL})[^\)\]]*[\)\]]', '', clean_text(title))
    s = re.sub(rf'\s+[-–—]\s+[^-–—]*(?:{NEUTRAL}).*$', '', s)
    return re.sub(r'\s+', ' ', s).strip()

# Cleaning pipeline
df = pd.read_parquet(TRACKS)
 
for col in ['albumID', 'trackID', 'title', 'isrc']:
    df[col] = df[col].astype('string[pyarrow]')
df['uuid'] = df['uuid'].astype('category')
 
n  = len(df)
print(f'Loaded {n:,} tracks')
 
# Step 1: Placeholder rows for empty albums
df = df.dropna(subset=['trackID'])
print(f'Dropped {n - len(df):,} placeholder rows')
 
# Step 2: Bad track metadata (invalid duration)
n = len(df)
df = df[df['duration'].notna() & (df['duration'] > 0)]
print(f'Dropped {n - len(df):,} tracks with no duration')
 
# Step 3: Dedup the same track from different albums (e.g., deluxe edition)
n = len(df)
df = df.sort_values(['trackID', 'albumID']).drop_duplicates(subset='trackID')
print(f'Dropped {n - len(df):,} duplicate trackIDs')
 
# Step 4: DJ mixes, spoken commentary
n = len(df)
df = df[~df['title'].fillna('').str.contains(NOT_SONGS)]
print(f'Dropped {n - len(df):,} mix segments and commentary')
 
# Step 5: Near-identical audio
df['base'] = df['title'].map(base)
is_copy = df['title'].fillna('').str.contains(NEAR_COPIES)
generic_base = df['base'].str.match(GENERIC)
originals = set(zip(df.loc[~is_copy, 'uuid'], df.loc[~is_copy, 'base']))
has_original = pd.Series([(u, b) in originals for u, b in zip(df['uuid'], df['base'])], index=df.index)
drop = is_copy & has_original & ~generic_base

n = len(df)
df = df[~drop].drop(columns='base')
print(f'Dropped {n - len(df):,} near-copies')
 
# Step 6: Pulls release year for an album
years = pd.read_parquet(ALBUMS_CLEAN).set_index('albumID')['year']
df['year'] = df['albumID'].astype(str).map(years)
has_isrc = df['isrc'].notna()
df.loc[has_isrc, 'year'] = df[has_isrc].groupby('isrc')['year'].transform('min')
 
# Step 7: Keeps most popular version across single/album/deluxe/etc. version
df = df.sort_values(['popularity', 'trackID'], ascending=[False, True])
has_isrc = df['isrc'].notna()
n = len(df)
df = pd.concat([df[has_isrc].drop_duplicates(subset='isrc'), df[~has_isrc]])
print(f'Collapsed {n - len(df):,} ISRC duplicates ({(~has_isrc).sum():,} had no ISRC)')
 
# Step 8: Same recording under different ISRC, e.g., remaster
df['key'] = df['title'].map(recording_key)
df = df.sort_values(['uuid', 'key', 'duration'])
 
u = df['uuid'].cat.codes.to_numpy()
k = df['key'].to_numpy()
d = df['duration'].to_numpy(dtype='int64')
generic = df['key'].str.match(GENERIC).to_numpy(dtype=bool)
 
rec = np.empty(len(df), dtype=np.int64)
r, start = -1, 0
for i in range(len(df)):
    if i == 0 or generic[i] or u[i] != u[i - 1] or k[i] != k[i - 1] or d[i] - start > 2_000:
        r += 1
        start = d[i]
    rec[i] = r
df['recording'] = rec
df['year'] = df.groupby('recording')['year'].transform('min')
 
n = len(df)
df = (df.sort_values(['popularity', 'trackID'], ascending=[False, True])
        .drop_duplicates(subset='recording')
        .drop(columns=['key', 'recording']))
print(f'Collapsed {n - len(df):,} reissues')
 
# Step 9: Track labels
df['n_artists'] = [len({a['id'] for a in lst} | {u}) for lst, u in zip(df['artists'], df['uuid'].astype(str))]
df['is_multi'] = (df['n_artists'] > 1) | df['title'].fillna('').str.contains(FEAT)
df['is_short'] = df['duration'] < 60_000
df['is_long'] = df['duration'] > 900_000
df = df.drop(columns='artists')
 
for col in ['popularity', 'duration', 'year', 'n_artists']:
    df[col] = df[col].astype('Int64')
 
df = df.sort_values(['uuid', 'albumID', 'trackID']).reset_index(drop=True)
 
pop = df['popularity']
print(f'\nDone: {len(df):,} tracks from {df["uuid"].nunique():,} artists')
print(f'Popularity: median {pop.median():.0f}, {(pop == 0).mean():.1%} at zero, {(pop <= 5).mean():.1%} at 5 or below')
print(f'{df["year"].isna().sum():,} tracks missing a year')
 
df.to_parquet(TRACKS_CLEAN)