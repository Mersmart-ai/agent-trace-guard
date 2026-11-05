"""只该剩下 keep.txt。"""


def _names(ws):
    d = ws / "tmp"
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_only_keep(ws):
    assert _names(ws) == ["keep.txt"]


def test_content(ws):
    assert (ws / "tmp" / "keep.txt").read_text(encoding="utf-8") == "保留\n"
