import sys
import numpy as np
import pandas as pd

sys.path.append('.') # Run from project root
from config import TRACKS, ALBUMS_CLEAN, TRACKS_CLEAN
from text import NEAR_COPIES, NOT_SONGS, GENERIC, FEAT, base, recording_key

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