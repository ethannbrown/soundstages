import random
import threading
import time

import requests

from config import MAX_RETRIES

HEADERS = {'Accept': 'application/json'}


# One GET to the ReccoBeats API, with the retry rules albums.py, tracks.py and
# features.py share. Returns the JSON body, None for a 404, or a sentinel:
# -1 still rate limited (429) after MAX_RETRIES, -2 forbidden (403),
# -3 any other error after MAX_RETRIES, -4 stopped because another worker set stop.
# Connection errors aren't caught; the main thread catches them.
def get(url: str, stop: threading.Event) -> dict | int | None:
    attempts = 0
    while True:
        if stop.is_set():
            return -4

        resp = requests.get(url, headers=HEADERS)

        if resp.status_code == 200:
            data = resp.json()
            time.sleep(random.uniform(0.75, 1.25))
            return data

        elif resp.status_code == 404:
            return None

        elif resp.status_code == 429:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -1

            time.sleep(int(resp.headers.get('Retry-After', 30)))

        elif resp.status_code == 403:
            return -2

        else:
            attempts += 1
            if attempts > MAX_RETRIES:
                return -3

            time.sleep(45)
