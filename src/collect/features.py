import sys, os, csv, requests
import time, random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

sys.path.append('.') # Run from project root
from config import TRACKS_CLEAN, FEATURES, LOG_F, MAX_RETRIES

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

headers = {
  'Accept': 'application/json'
}

# Returns one row per requested track; tracks with no features get empty values
def get_features(batch: list) -> list | int:
    url = f"https://api.reccobeats.com/v1/audio-features?ids={','.join(batch)}"

    attempts = 0
    while True:
        if stop.is_set():
            return -4

        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            found = {t['id']: t for t in resp.json()['content']}
            time.sleep(random.uniform(0.75, 1.25))
            return [[t] + ([found[t].get(f) for f in FEATS] if t in found else [None] * len(FEATS))
                    for t in batch]

        elif resp.status_code == 404:
            return [[t] + [None] * len(FEATS) for t in batch]

        elif resp.status_code == 429:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -1

            sleep = int(resp.headers.get('Retry-After', 30))
            time.sleep(sleep)
            continue

        elif resp.status_code == 403:
            return -2

        else:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -3

            time.sleep(45)
            continue

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
            print(f'HTTP 429 error on batch {i}. Breaking.')
            stop.set()
            completed = False
            continue

        if rows == -2:
            print('HTTP 403 error, forbidden. Breaking.')
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
            print(f'{len(done) + count * BATCH:,} tracks, {count / minutes:.0f} batches/min, {WORKERS} workers', flush=True)

if completed:
    df = pd.read_csv(LOG_F).drop_duplicates(subset='trackID')
    df['key'] = df['key'].astype('Int64')
    df['mode'] = df['mode'].astype('Int64')
    df.to_parquet(FEATURES)

    missing = df['danceability'].isna().sum()
    print(f'{len(df):,} tracks, {len(df) - missing:,} with features, {missing:,} missing')
else:
    print('Early stoppage, requires rerun.')