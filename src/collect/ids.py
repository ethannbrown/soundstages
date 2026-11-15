import sys
import threading

import pandas as pd

sys.path.append('.')  # Run from project root
from api import get

from config import ARTISTS, IDS, LOG_R

# Resumability
done = set()
try:
    prev = pd.read_csv(LOG_R, header=0)
    done = set(prev['spotify'])
except FileNotFoundError:
    with open(LOG_R, 'w') as f:
        f.write('spotify,recco\n')

artists = pd.read_parquet(ARTISTS)
idens = [iden for iden in artists['id'] if iden not in done]

batches = [','.join(idens[i:i+40])
           for i in range(0, len(idens), 40)]

# One request at a time, so nothing sets stop; api.get takes it anyway
stop = threading.Event()

completed = True
for count, batch in enumerate(batches, start=1):
    url = f'https://api.reccobeats.com/v1/artist?ids={batch}'

    try:
        data = get(url, stop)
    except Exception as e:
        print(f'Batch {count} failed: {e}')
        completed = False
        break

    # 404: skipped, and asked for again on the next run
    if data is None:
        print(f'HTTP 404 error on batch {count} of {len(batches)}.')
        continue

    if data == -2:
        print('HTTP 403 error, forbidden.')

    # A sentinel from api.get: -1 rate limited, -2 forbidden, -3 retries exhausted
    if isinstance(data, int):
        completed = False
        break

    with open(LOG_R, 'a') as f:
        for artist in data['content']:
            spotify = artist['href'].split('/')[-1]
            f.write(f"{spotify},{artist['id']}\n")

if completed is True:
    df = pd.read_csv(LOG_R, header=0)
    mapping = dict(zip(df['spotify'], df['recco'], strict=True))

    # Own file, so rerunning merge.py never drops the uuids
    ids = pd.DataFrame({'id': artists['id'], 'uuid': artists['id'].map(mapping)})
    ids.to_parquet(IDS)
else:
    print('Early stoppage, requires rerun.')
