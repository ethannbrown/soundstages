import sys
import pandas as pd

sys.path.append('.')  # Run from project root
from config import ALBUMS, ALBUMS_CLEAN
from text import normalize_title

df = pd.read_parquet(ALBUMS)
df = df.dropna(subset=['albumID'])

df['year'] = pd.to_numeric(df['released'].str[:4], errors='coerce').astype('Int64')

df = df[df['type'] != 'compilation']

df = df.sort_values(['albumID', 'uuid']).drop_duplicates(subset='albumID')

df['norm'] = df['title'].map(normalize_title)
df = (df.sort_values(['popularity', 'albumID'], ascending=[False, True])
        .drop_duplicates(subset=['uuid', 'norm', 'tracks']))

df = df.sort_index()
df.to_parquet(ALBUMS_CLEAN)