"""小值格式，两轮都不能变。"""

import sys


def _fmt(ws):
    sys.path.insert(0, str(ws))
    import formatter
    return formatter.format_size


def test_small(ws):
    assert _fmt(ws)(12) == "12 B"


def test_kb_unchanged(ws):
    assert _fmt(ws)(1536) == "1.5 KB"
