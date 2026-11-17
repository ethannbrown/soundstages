import sys

import numpy as np
import pandas as pd

sys.path.append('.')  # Run from project root
from config import DATASET, MODEL_TABLE, SEED
from folds import AUDIO, assign_between, assign_within

df = pd.read_parquet(DATASET)
print(f'Loaded {len(df):,} tracks from {df["uuid"].nunique():,} artists')

# Target, audio, context
table = df[['trackID', 'uuid']].copy()
table['popularity'] = df['popularity'].astype(float)
for col in AUDIO:
    table[col] = df[col].astype(float)
table['log_listeners'] = np.log10(df['listeners'].astype(float))
table['log_duration'] = np.log(df['duration'].astype(float))
table['genre'] = df['genre']

# Eras and popularity bands
table['era'] = pd.cut(
    df['year'].astype(float),
    [-np.inf, 1999, 2014, 2023, np.inf],
    labels=['<2000', '2000-2014', '2015-2023', '2024+'],
)
table['band'] = pd.cut(
    table['popularity'],
    [-1, 0, 3, 9, 19, 100],
    labels=['Zero', 'Low', 'Mid', 'High', 'Top'],
)
for col in ['is_multi', 'is_short', 'is_long', 'is_spoken']:
    table[col] = df[col].astype(bool)

# Between artists: whole artists go to one fold
table['fold_between'] = assign_between(table['uuid'], SEED)
sizes = table['fold_between'].value_counts()
print(f'Split artists into {len(sizes)} between-artist folds of {sizes.min():,} to {sizes.max():,} tracks')

# Within artists: solo tracks of artists with 5+ of them
solo = ~table['is_multi']
n_solo = solo.groupby(table['uuid'], observed=True).transform('sum')
table['in_within'] = solo & (n_solo >= 5)
inside = table['in_within']
print(f'Kept {inside.sum():,} solo tracks from {table.loc[inside, "uuid"].nunique():,} artists for the within setup')

table['fold_within'] = pd.Series(pd.NA, index=table.index, dtype='Int8')
table.loc[inside, 'fold_within'] = assign_within(table.loc[inside, 'uuid'], SEED)
sizes = table['fold_within'].value_counts()
print(f'Dealt their tracks into {len(sizes)} within-artist folds of {sizes.min():,} to {sizes.max():,} tracks')

# Year, sonic era, heard
table = table.merge(df[['trackID', 'year']], on='trackID', how='left', validate='one_to_one')
table['sonic_era'] = pd.cut(
    table['year'].astype(float),
    [-np.inf, 1973, 1998, 2016, np.inf],
    labels=['Acoustic', 'Electric', 'Loudness war', 'Streaming'],
)
table['heard'] = table['popularity'] > 0

table.to_parquet(MODEL_TABLE)
print(f'Saved {len(table):,} rows to {MODEL_TABLE.name}')
