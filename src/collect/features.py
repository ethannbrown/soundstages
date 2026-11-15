import csv
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

sys.path.append('.') # Run from project root
from api import get
from config import FEATURES, LOG_F, TRACKS_CLEAN

WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
BATCH = 40
FEATS = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'key',
         'liveness', 'loudness', 'mode', 'speechiness', 'tempo', 'valence']
cols = ['trackID'] + FEATS

# Log is CSV, not JSON: on resume only the trackID column is read, which takes seconds
done = set()
if os.path.exists(LOG_F):
    done = set(pd.read_csv(LOG_F, usecols=['trackID'])['trackID'])
else:
    with open(LOG_F, 'w', newline='') as f:
        csv.writer(f).writerow(cols)

idens = [t for t in pd.read_parquet(TRACKS_CLEAN, columns=['trackID'])['trackID'] if t not in done]
batches = [idens[i:i + BATCH] for i in range(0, len(idens), BATCH)]

# Returns one row per requested track; tracks with no features get empty values
def get_features(batch: list) -> list | int:
    url = f"https://api.reccobeats.com/v1/audio-features?ids={','.join(batch)}"
    data = get(url, stop)

    # 404: none of these tracks have features
    if data is None:
        return [[t] + [None] * len(FEATS) for t in batch]

    # A sentinel from api.get, -1 to -4
    if isinstance(data, int):
        return data

    found = {t['id']: t for t in data['content']}
    return [[t] + ([found[t].get(f) for f in FEATS] if t in found else [None] * len(FEATS))
            for t in batch]

stop = threading.Event()

count = 0
start = time.time()
completed = True

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = {executor.submit(get_features, b): i for i, b in enumerate(batches)}

    for fut in as_completed(futures):
        i = futures[fut]

        try:
            rows = fut.result()
        except Exception as e:
            print(f'Batch {i} failed: {e}')
            completed = False
            continue

        if rows == -1:
            print(f'Still rate limited (429) on batch {i}, stopping')
            stop.set()
            completed = False
            continue

        if rows == -2:
            print('Forbidden (403), stopping')
            stop.set()
            completed = False
            continue

        if rows in (-3, -4):
            completed = False
            continue

        with open(LOG_F, 'a', newline='') as f:
            csv.writer(f).writerows(rows)

        count += 1
        if count % 1000 == 0:
            minutes = (time.time() - start) / 60
            print(f'Fetched {len(done) + count * BATCH:,} of {len(done) + len(idens):,} tracks, '
                  f'{count / minutes:.0f} batches a minute', flush=True)

if completed:
    df = pd.read_csv(LOG_F).drop_duplicates(subset='trackID')
    df['key'] = df['key'].astype('Int64')
    df['mode'] = df['mode'].astype('Int64')
    df.to_parquet(FEATURES)

    missing = df['danceability'].isna().sum()
    print(f'Wrote {len(df):,} tracks, {len(df) - missing:,} with features and {missing:,} without')
else:
    print('Early stoppage, requires rerun.')