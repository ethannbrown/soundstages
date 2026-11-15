import sys

import pandas as pd

sys.path.append('.') # Run from project root
from config import ARTISTS, LISTENER_FLOOR, LISTENERS, RESOLVED

lis = pd.read_parquet(LISTENERS)
res = pd.read_parquet(RESOLVED)

artists = res.merge(lis, on='id')
artists = artists.sort_values(by=['genre', 'listeners'], ascending=[True, False])
artists = artists[artists['listeners'] >= LISTENER_FLOOR].reset_index(drop=True)
print(f'Kept {len(artists):,} artists with at least {LISTENER_FLOOR} monthly listeners')

artists.to_parquet(ARTISTS)