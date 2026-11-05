"""给人看的表格：大小后面要附上原始字节数。"""

import sys


def _report(ws):
    sys.path.insert(0, str(ws))
    import report
    return report


def test_kb_shows_bytes(ws):
    assert _report(ws).render_table([("a", 1536)]) == "a          1.5 KB (1536 B)"


def test_small_shows_bytes(ws):
    assert _report(ws).render_table([("x", 12)]) == "x          12 B (12 B)"
