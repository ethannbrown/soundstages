import sys

import pandas as pd

sys.path.append('.')  # Run from project root
from config import ALBUMS, ALBUMS_CLEAN
from text import normalize_title

df = pd.read_parquet(ALBUMS)
n = len(df)
print(f'Loaded {n:,} albums')

df = df.dropna(subset=['albumID'])
print(f'Dropped {n - len(df):,} placeholder rows for artists with no albums')

df['year'] = pd.to_numeric(df['released'].str[:4], errors='coerce').astype('Int64')

n = len(df)
df = df[df['type'] != 'compilation']
print(f'Dropped {n - len(df):,} compilations')

n = len(df)
df = df.sort_values(['albumID', 'uuid']).drop_duplicates(subset='albumID')
print(f'Dropped {n - len(df):,} duplicate albumIDs')

n = len(df)
df['norm'] = df['title'].map(normalize_title)
df = (df.sort_values(['popularity', 'albumID'], ascending=[False, True])
        .drop_duplicates(subset=['uuid', 'norm', 'tracks']))
print(f'Collapsed {n - len(df):,} editions')

df = df.sort_index()
print(f'Kept {len(df):,} albums from {df["uuid"].nunique():,} artists')

df.to_parquet(ALBUMS_CLEAN)