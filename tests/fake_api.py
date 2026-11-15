import threading


class Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self.body = body
        self.headers = headers or {}

    def json(self):
        return self.body


# Stands in for requests.get. Serves canned responses per URL, in order; the last one
# repeats. An unknown URL fails the test (see the api fixture), so no call can go live.
class FakeAPI:
    def __init__(self):
        self.responses = {}
        self.calls = []
        self.unknown = []
        self.sleeps = []
        self.lock = threading.Lock()

    def get(self, url, **kwargs):
        with self.lock:
            self.calls.append(url)
            if url not in self.responses:
                self.unknown.append(url)
                raise AssertionError(f'Unexpected URL {url}')
            queue = self.responses[url]
            resp = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(resp, Exception):
            raise resp
        return resp
