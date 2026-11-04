from core.stats import median
from app import run


def test_report_keys():
    assert set(run().keys()) == {"total", "average", "middle"}


def test_odd():
    # 奇数个：中间那个，怎么写都对
    assert median([3, 1, 2]) == 2


def test_single():
    assert median([5]) == 5
