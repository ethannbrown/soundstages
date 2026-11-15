import threading
import time

import api as recco
import pytest
import requests
from fake_api import Resp

URL = 'https://api.reccobeats.com/v1/example'
BODY = {'content': []}


@pytest.fixture
def stop():
    return threading.Event()


# Columns: responses in order, what get returns, calls made, retry waits
@pytest.mark.parametrize(
    'responses, expected, calls, waits',
    [
        ([Resp(200, BODY)], BODY, 1, []),
        ([Resp(404)], None, 1, []),
        ([Resp(403)], -2, 1, []),
        ([Resp(429, headers={'Retry-After': '7'}), Resp(200, BODY)], BODY, 2, [7]),
        ([Resp(429), Resp(200, BODY)], BODY, 2, [30]),
        ([Resp(429)], -1, 4, [30, 30, 30]),
        ([Resp(500), Resp(200, BODY)], BODY, 2, [45]),
        ([Resp(503)], -3, 4, [45, 45, 45]),
        # 429s and 5xx share one count: the fourth failure of either kind ends it
        ([Resp(429), Resp(429), Resp(500), Resp(500)], -3, 4, [30, 30, 45]),
    ],
)
def test_get(api, stop, responses, expected, calls, waits):
    api.responses[URL] = responses

    assert recco.get(URL, stop) == expected
    assert len(api.calls) == calls
    assert [s for s in api.sleeps if s >= 7] == waits


def test_pause_after_success(api, stop):
    api.responses[URL] = [Resp(200, BODY)]
    recco.get(URL, stop)
    assert len(api.sleeps) == 1
    assert 0.75 <= api.sleeps[0] <= 1.25


def test_stopped_before_asking(api, stop):
    stop.set()
    assert recco.get(URL, stop) == -4
    assert api.calls == []


# Another worker sets stop while this one waits to retry
def test_stopped_while_retrying(api, stop, monkeypatch):
    api.responses[URL] = [Resp(500)]
    monkeypatch.setattr(time, 'sleep', lambda s: stop.set())
    assert recco.get(URL, stop) == -4
    assert len(api.calls) == 1


def test_connection_error_raises(api, stop):
    api.responses[URL] = [requests.ConnectionError('reset')]
    with pytest.raises(requests.ConnectionError):
        recco.get(URL, stop)


def test_sends_accept_header(monkeypatch, stop):
    seen = {}

    def fake_get(url, headers=None):
        seen['headers'] = headers
        return Resp(200, BODY)

    monkeypatch.setattr(requests, 'get', fake_get)
    monkeypatch.setattr(time, 'sleep', lambda s: None)
    recco.get(URL, stop)
    assert seen['headers'] == {'Accept': 'application/json'}
