import requests
from bs4 import BeautifulSoup
import pandas as pd

from config import NOMINEES, LISTENERS

def get_listeners(iden: str) -> int:
    resp = requests.get(f'https://open.spotify.com/artist/{iden}')
    soup = BeautifulSoup(resp.text, 'html.parser')
    listeners = soup.find(attrs={'data-testid': 'monthly-listeners-label'}).get_text(strip=True)
    listeners = int(listeners.replace(' monthly listeners', '').replace(',', ''))
    return listeners

noms = pd.read_parquet(NOMINEES)
results = {iden: get_listeners(iden) for iden in noms['id']}