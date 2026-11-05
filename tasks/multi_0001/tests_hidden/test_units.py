"""第 2 轮：改成单位表驱动，加 TB。"""

import sys


def _fmt(ws):
    sys.path.insert(0, str(ws))
    import formatter
    return formatter.format_size


def test_tb(ws):
    assert _fmt(ws)(1024 ** 4) == "1.0 TB"


def test_small_unchanged(ws):
    assert _fmt(ws)(12) == "12 B"
