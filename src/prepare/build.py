import sys
import pandas as pd

sys.path.append('.')  # Run from project root
from config import TRACKS_CLEAN, FEATURES, ARTISTS, IDS, DATASET
from text import FEAT

tracks = pd.read_parquet(TRACKS_CLEAN)
feats = pd.read_parquet(FEATURES)
feats['trackID'] = feats['trackID'].astype('string[pyarrow]')
print(f'Loaded {len(tracks):,} tracks')

# Track flags for sensitivity checks, not features. Set before the merge so they
# sit next to the track columns, ahead of the audio features.
has_feat = tracks['title'].fillna('').str.contains(FEAT)
tracks['is_multi'] = (tracks['n_artists'] > 1) | has_feat
tracks['is_short'] = tracks['duration'] < 60_000
tracks['is_long'] = tracks['duration'] > 900_000

# 1. Tracks with no audio features
n = len(tracks)
df = tracks.merge(feats.dropna(subset=['danceability']), on='trackID', how='inner')
print(f'Dropped {n - len(df):,} tracks with no audio features')

# 2. Failed analyses: no tempo, silence, or louder than full scale
n = len(df)
df = df[(df['tempo'] > 0) & (df['loudness'] > -60) & (df['loudness'] <= 0)]
print(f'Dropped {n - len(df):,} tracks with impossible audio values')

# 3. No release year, so no era
n = len(df)
df = df.dropna(subset=['year'])
print(f'Dropped {n - len(df):,} tracks with no year')

# 4. Artist context: genre and monthly listeners
artists = pd.read_parquet(ARTISTS).merge(pd.read_parquet(IDS), on='id')
artists = artists.dropna(subset=['uuid']).set_index('uuid')
uuid = df['uuid'].astype(str)
df['genre'] = uuid.map(artists['genre']).astype('category')
df['listeners'] = uuid.map(artists['listeners']).astype('Int64')

# 5. Spoken word (audiobooks, poetry, skits). A flag, not a drop.
df['is_spoken'] = df['speechiness'] >= 0.66

df = df.reset_index(drop=True)

print(f'\nDone: {len(df):,} tracks from {df["uuid"].nunique():,} artists')
print(f'{df["is_spoken"].sum():,} spoken-word tracks flagged')
print(f'{df["genre"].isna().sum():,} tracks missing a genre')

df.to_parquet(DATASET)