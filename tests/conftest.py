import time

import pytest
import requests

import text
from fake_api import FakeAPI


# The track and album title rules both live in text.py, so both fixtures hand
# the tests the same module.
@pytest.fixture(scope='module')
def rules():
    return text


@pytest.fixture(scope='module')
def album_rules():
    return text


# Replaces requests.get and time.sleep for the crawler and api.py tests
@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(time, 'sleep', fake.sleeps.append)
    yield fake
    # The crawlers catch every exception, so check unknown URLs here
    assert fake.unknown == []
