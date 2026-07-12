import pandas as pd
import requests, sys

sys.path.append('.') # Run from project root
from config import NOMINEES, RESOLVED
from genres import SUBS

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36'
}

noms = pd.read_parquet(NOMINEES)
idens = noms[noms['genres'].str.len() > 1]['id'].tolist()
batches = [','.join(idens[i:i+100]) 
           for i in range(0, len(idens), 100)]

resolved = {row.id: row.genres[0]
            for row in noms.itertuples(index=False)
            if row.id not in idens}

for string in batches:
    url = f'https://everynoise.com/api/{string}'
    data = requests.get(url, headers=headers).json()

    for iden, genres in data.items(): # EN returns genres per artist ranked by relevance-to-artist
        for genre in genres:
            if genre not in SUBS:
                continue
            else:
                resolved[iden] = SUBS[genre]
                break

noms['genre'] = noms['id'].map(resolved)
noms = noms.drop(columns='genres')
noms.to_parquet(RESOLVED)