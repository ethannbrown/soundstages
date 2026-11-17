import time

import pytest
import requests

import text
from fake_api import FakeAPI


# Track and album rules both live in text.py
@pytest.fixture(scope='module')
def rules():
    return text


@pytest.fixture(scope='module')
def album_rules():
    return text


# Replaces requests.get and time.sleep for the collector and api.py tests
@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(time, 'sleep', fake.sleeps.append)
    yield fake
    # Collectors catch every exception; unknown URLs are checked here
    assert fake.unknown == []
