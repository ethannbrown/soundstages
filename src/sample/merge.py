import sys
import pandas as pd

sys.path.append('.') # Run from project root
from config import LISTENERS, RESOLVED, ARTISTS, LISTENER_FLOOR

lis = pd.read_parquet(LISTENERS)
res = pd.read_parquet(RESOLVED)

artists = res.merge(lis, on='id')
artists = artists.sort_values(by=['genre', 'listeners'], ascending=[True, False])
artists = artists[artists['listeners'] >= LISTENER_FLOOR].reset_index(drop=True)
artists.to_parquet(ARTISTS)