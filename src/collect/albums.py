import sys, requests
import time, random, json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pandas as pd

sys.path.append('.') # Run from project root
from config import ARTISTS, ALBUMS, LOG_A, MAX_RETRIES

done = set()
try:
    prev = pd.read_json(LOG_A, orient='records', lines=True)
    done = set(prev['uuid'])
except FileNotFoundError:
    pass

artists = pd.read_parquet(ARTISTS).dropna()
cols = ['uuid', 'albumID', 'title', 'type', 'released', 'popularity', 'artists', 'tracks']

headers = {
  'Accept': 'application/json'
}

# Returns list of all artist records
def get_records(iden: str) -> list | int:
    total, page = None, 0

    attempts = 0
    records = []
    while total is None or page < total:
        if stop.is_set():
            return -1
        
        url = f'https://api.reccobeats.com/v1/artist/{iden}/album?page={page}&size=50'
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            data = resp.json()
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
            time.sleep(random.uniform(0.75, 1.25))

        elif resp.status_code == 404:
            print(f'HTTP 404 error for {iden}.')
            return None
            
        elif resp.status_code == 429:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -1
            
            sleep = int(resp.headers.get('Retry-After', 30))
            time.sleep(sleep)
            continue

        elif resp.status_code == 403:
            print('HTTP 403 error, forbidden.')
            return -2

        else:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -3

            time.sleep(45)
            continue

    return records

stop = threading.Event()
todo = [i for i in artists['uuid'] if i not in done]

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
            continue

        if rows == -1 or rows == -2:
            stop.set()
            completed = False
            continue

        if rows == -3 or rows is None:
            continue

        f.write('\n'.join(json.dumps(r) for r in rows) + '\n')

        count += 1
        if count % 100 == 0:
            print(f'{count} of {len(artists)} artists completed.')

        if count == len(artists):
            print('Complete.')

if completed:
    df = pd.read_json(LOG_A, lines=True)
    df.to_parquet(ALBUMS)