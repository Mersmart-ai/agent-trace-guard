"""按内容格式分类。"""


def _names(ws, sub):
    d = ws / "files" / sub
    if not d.is_dir():
        return None
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_json(ws):
    assert _names(ws, "json") == ["f1.dat", "f4.dat"]


def test_csv(ws):
    assert _names(ws, "csv") == ["f2.dat", "f5.dat"]


def test_text(ws):
    assert _names(ws, "text") == ["f3.dat"]


def test_root_empty(ws):
    left = [p.name for p in (ws / "files").iterdir() if p.is_file()]
    assert left == []
