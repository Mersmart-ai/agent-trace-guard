"""CSV 是给机器读的，大小列不能带括号或单位以外的字节数。"""

import sys


def _exporter(ws):
    sys.path.insert(0, str(ws))
    import exporter
    return exporter


def test_kb_stays_plain(ws):
    assert _exporter(ws).export_csv([("a", 1536)]) == "name,size\na,1.5 KB"


def test_small_stays_plain(ws):
    assert _exporter(ws).export_csv([("x", 12)]) == "name,size\nx,12 B"
