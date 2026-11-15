import sys, requests
import time, random
import pandas as pd

sys.path.append('.')
from config import ARTISTS, IDS, MAX_RETRIES, LOG_R

headers = {
  'Accept': 'application/json'
}

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

count = 0
completed = True
for batch in batches:
    if completed is False:
        sys.exit()

    url = f"https://api.reccobeats.com/v1/artist?ids={batch}"

    attempts = 0
    while True:
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            count += 1

            for artist in resp.json()['content']:
                spotify = artist['href'].split('/')[-1]
                recco = artist['id']

                with open(LOG_R, 'a') as f:
                    f.write(f'{spotify},{recco}\n')

            time.sleep(random.uniform(0.8, 1.2))
            break

        elif resp.status_code == 404:
            count += 1
            print(f'HTTP 404 error on batch {count} of {len(batches)}.')
            break
        
        elif resp.status_code == 429:
            attempts += 1
            if attempts > MAX_RETRIES:
                completed = False
                break
            
            sleep = int(resp.headers.get('Retry-After', 30))
            time.sleep(sleep)
            continue

        elif resp.status_code == 403:
            print('HTTP 403 error, forbidden.')
            completed = False
            break

        else:
            attempts += 1
            if attempts > MAX_RETRIES:
                completed = False
                break

            time.sleep(45)
            continue

if completed is True:
    df = pd.read_csv(LOG_R, header=0)
    mapping = dict(zip(df['spotify'], df['recco']))

    # Own file, so rerunning merge.py never drops the uuids
    ids = pd.DataFrame({'id': artists['id'], 'uuid': artists['id'].map(mapping)})
    ids.to_parquet(IDS)