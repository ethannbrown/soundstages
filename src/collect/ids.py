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

batches = [','.join(idens[i : i + 40]) for i in range(0, len(idens), 40)]

# api.get needs a stop event; nothing sets it here
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

    # 404 skipped; asked for again next run
    if data is None:
        print(f'Skipped batch {count} of {len(batches)}, not found (404)')
        continue

    if data == -1:
        print(f'Still rate limited (429) on batch {count}, stopping')

    if data == -2:
        print('Forbidden (403), stopping')

    # A sentinel from api.get, -1 to -3
    if isinstance(data, int):
        completed = False
        break

    with open(LOG_R, 'a') as f:
        for artist in data['content']:
            spotify = artist['href'].split('/')[-1]
            f.write(f'{spotify},{artist["id"]}\n')

if completed is True:
    df = pd.read_csv(LOG_R, header=0)
    mapping = dict(zip(df['spotify'], df['recco'], strict=True))

    # Own file; rerunning merge.py keeps the uuids
    ids = pd.DataFrame({'id': artists['id'], 'uuid': artists['id'].map(mapping)})
    ids.to_parquet(IDS)
else:
    print('Early stoppage, requires rerun.')
