import pytest
import text


# The track and album title rules both live in text.py, so both fixtures hand
# the tests the same module.
@pytest.fixture(scope='module')
def rules():
    return text


@pytest.fixture(scope='module')
def album_rules():
    return text
