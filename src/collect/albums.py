import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

sys.path.append('.') # Run from project root
from api import get
from config import ALBUMS, IDS, LOG_A

done = set()
try:
    prev = pd.read_json(LOG_A, orient='records', lines=True)
    done = set(prev['uuid'])
except FileNotFoundError:
    pass

ids = pd.read_parquet(IDS).dropna()
cols = ['uuid', 'albumID', 'title', 'type', 'released', 'popularity', 'artists', 'tracks']

# Returns list of all artist records
def get_records(iden: str) -> list | int | None:
    total, page = None, 0

    records = []
    while total is None or page < total:
        url = f'https://api.reccobeats.com/v1/artist/{iden}/album?page={page}&size=50'
        data = get(url, stop)

        # 404: skipped, and asked for again on the next run
        if data is None:
            print(f'HTTP 404 error for {iden}.')
            return None

        # A sentinel from api.get, -1 to -4
        if isinstance(data, int):
            if data == -2:
                print('HTTP 403 error, forbidden.')
            return data

        total = data['totalPages']

        if not data['content']:
            row = {'uuid': iden}
            for col in cols:
                if col != 'uuid':
                    row[col] = None
            return [row]

        for record in data['content']:
            row = {
                'uuid': iden,
                'albumID': record['id'],
                'title': record['name'],
                'type': record['albumType'],
                'released': record['releaseDate'],
                'popularity': record['popularity'],
                'artists': [{'name': a['name'], 'uuid': a['id']} for a in record['artists']],
                'tracks': record['totalTracks']
            }
            records.append(row)

        page += 1

    return records

stop = threading.Event()
todo = [i for i in ids['uuid'] if i not in done]

completed = True
count = len(done)
with ThreadPoolExecutor(max_workers=4) as executor, open(LOG_A, 'a') as f:
    futures = {executor.submit(get_records, iden): iden for iden in todo}

    for fut in as_completed(futures):
        iden = futures[fut]

        try:
            rows = fut.result()
        except Exception as e:
            print(f'{e} for {iden}.')
            completed = False
            continue

        if rows == -1 or rows == -2:
            stop.set()
            completed = False
            continue

        if rows in (-3, -4):
            completed = False
            continue

        # 404: nothing to log, asked for again on the next run
        if rows is None:
            continue

        f.write('\n'.join(json.dumps(r) for r in rows) + '\n')

        count += 1
        if count % 100 == 0:
            print(f'{count} of {len(ids)} artists completed.')

        if count == len(ids):
            print('Complete.')

if completed:
    df = pd.read_json(LOG_A, lines=True)
    df.to_parquet(ALBUMS)
else:
    print('Early stoppage, requires rerun.')
