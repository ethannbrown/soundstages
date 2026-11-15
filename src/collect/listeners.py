import random
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append('.') # Run from project root
from config import LISTENERS, LOG_L, MAX_RETRIES, NOMINEES

# Resumability
done = set()
try:
    prev = pd.read_csv(LOG_L, header=0)
    done = set(prev['id'])
except FileNotFoundError:
    with open(LOG_L, 'w') as f:
        f.write('id,listeners\n')

# Returns present monthly listener counts; sentinel values for errors
def get_listeners(iden: str) -> int | None:
    url = f'https://open.spotify.com/artist/{iden}'

    attempts = 0
    while True:
        resp = requests.get(url)

        if resp.status_code == 200:
            break

        elif resp.status_code == 404:
            print(f'Skipped artist {iden}, not found (404)')
            return None
        
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
                print(f'Gave up on artist {iden} after HTTP {resp.status_code}')
                return -3
            
            time.sleep(30)
            continue

    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.find(attrs={'data-testid': 'monthly-listeners-label'})

    if text is None:
        return 0
    
    listeners = text.get_text(strip=True)
    listeners = int(''.join(filter(str.isdigit, listeners)))

    return listeners

noms = pd.read_parquet(NOMINEES)

completed = True
for iden in noms['id']:
    if iden in done:
        continue

    listeners = get_listeners(iden)

    if listeners == -1:
        print(f'Still rate limited (429) on artist {iden}, stopping')
        completed = False
        break

    elif listeners == -2:
        print('Forbidden (403), stopping')
        completed = False
        break

    with open(LOG_L, 'a') as f:
        if listeners is None or listeners == -3:
            f.write(f'{iden},\n')
        else:
            f.write(f'{iden},{listeners}\n')

    time.sleep(random.uniform(0.75, 1.25))

if completed:
    df = pd.read_csv(LOG_L, header=0)
    df.to_parquet(LISTENERS)