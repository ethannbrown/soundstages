import urllib.parse
import requests, sys
import pandas as pd

sys.path.append('.') # Run from project root
from config import NOMINEES
from rule import is_artist
from genres import SUBS

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36'
}

artists = {}
count = 0

sub_strings = {sub: urllib.parse.quote(sub) for sub in SUBS}

# Nominates all artists from the sub(genre) for feature collection on discographies
for sub, string in sub_strings.items():
    url = f'https://everynoise.com/api/genre/{string}'
    response = requests.get(url, headers=headers)
    data = response.json()

    genre = SUBS[sub]
    sub_count = 0

    for artist in data[sub]:
        if artist['id'] not in artists:
            artists[artist['id']] = {'name': artist['name'], 'genres': set()}
        artists[artist['id']]['genres'].add(genre)
        sub_count += 1

    print(f'{sub_count} artists returned for {sub}.')
    count += sub_count

print(f'{count} total artists nominated.')

artists = {
    iden: data
    for iden, data in artists.items()
    if is_artist(data['name'])
}

rows = [
    {'id': iden, 'name': data['name'], 'genres': sorted(data['seeds'])}
     for iden, data in artists.items()
]
df = pd.DataFrame(rows)
df.to_parquet(NOMINEES)