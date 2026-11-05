"""第 2 轮新增：TB。"""

import sys


def _fmt(ws):
    sys.path.insert(0, str(ws))
    import formatter
    return formatter.format_size


def test_tb(ws):
    assert _fmt(ws)(1024 ** 4) == "1.0 TB"
