"""第 1 轮的判据：GB 支持 + MB 不变。"""

import sys


def _fmt(ws):
    sys.path.insert(0, str(ws))
    import formatter
    return formatter.format_size


def test_gb(ws):
    assert _fmt(ws)(1024 ** 3) == "1.0 GB"


def test_mb_unchanged(ws):
    assert _fmt(ws)(1024 ** 2) == "1.0 MB"
