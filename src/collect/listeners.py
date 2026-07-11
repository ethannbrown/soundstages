import random, requests, sys, time
import pandas as pd
from bs4 import BeautifulSoup

sys.path.append('.') # Run from project root
from config import NOMINEES, LISTENERS, LOG, MAX_RETRIES

# Resumability
done = set()
try:
    prev = pd.read_csv(LOG, names=['id', 'listeners'])
    done = set(prev['id'])
except FileNotFoundError:
    pass

# Returns present monthly listener counts; sentinel values for errors
def get_listeners(iden: str) -> int:
    url = f'https://open.spotify.com/artist/{iden}'

    attempts = 0
    while True:
        resp = requests.get(url)

        if resp.status_code == 200:
            break

        elif resp.status_code == 404:
            print(f'HTTP 404 error for {iden}')
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
                print(f'HTTP {resp.status_code} error for {iden}')
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
        print('HTTP 429 error, max retries hit. Breaking.')
        completed = False
        break

    if listeners == -2:
        print('HTTP 403 error, forbidden. Breaking.')
        completed = False
        break

    with open(LOG, 'a') as f:
        if listeners is None or listeners == -3:
            f.write(f'{iden},\n')
        else:
            f.write(f'{iden},{listeners}\n')

    time.sleep(random.uniform(0.75, 1.25))

if completed:
    df = pd.read_csv(LOG, names=['id', 'listeners'])
    df.to_parquet(LISTENERS)