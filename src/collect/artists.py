import urllib.parse
import requests, sys
import pandas as pd

sys.path.append('.')
from genres import SUBS
from rule import is_artist
from config import NOMINEES

sub_strings = {sub: urllib.parse.quote(sub) for sub in SUBS}
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Safari/605.1.15'
}

artists = {}
count = 0

# Nominates all artists from the sub(genre) for feature collection on discographies
for sub, string in sub_strings.items():
    url = f'https://everynoise.com/api/genre/{string}'
    response = requests.get(url, headers=headers)
    data = response.json()

    seed = SUBS[sub]
    sub_count = 0

    for artist in data[sub]:
        if artist['id'] not in artists:
            artists[artist['id']] = {'name': artist['name'], 'seeds': set()}
        artists[artist['id']]['seeds'].add(seed)
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
    {'id': iden, 'name': data['name'], 'seeds': sorted(data['seeds'])}
     for iden, data in artists.items()
]
df = pd.DataFrame(rows)
df.to_parquet(NOMINEES)