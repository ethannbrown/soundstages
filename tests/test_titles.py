import pytest

# Pins the title rules in clean_tracks.py as they are today.


# Songs with near identical audio, matched only inside brackets or after a spaced dash
@pytest.mark.parametrize(
    'title, expected',
    [
        ('Hampstead Girl - Instrumental', True),
        ('Song (Inst.)', True),
        ('Song (Off Vocal)', True),
        ('Song - Off Vocal', True),
        ('Song (Radio Edit)', True),
        ('Song (Sped Up)', True),
        ('Mr. Clean', False),
        ('Instrumental Song', False),
        ('Song (Live)', False),
    ],
)
def test_near_copies(rules, title, expected):
    assert bool(rules.NEAR_COPIES.search(title)) == expected
