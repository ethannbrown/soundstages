import random
import threading
import time

import requests

from config import MAX_RETRIES

HEADERS = {'Accept': 'application/json'}


# Shared GET for the ReccoBeats scripts; returns JSON, None for a 404, or a sentinel
# -1 429, -2 403, -3 retries exhausted, -4 stopped by another worker
# Connection errors are left to the main thread
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
