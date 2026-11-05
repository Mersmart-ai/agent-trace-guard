"""按扩展名分类，文件名保持原样。"""


def _names(ws, sub):
    d = ws / "downloads" / sub
    if not d.is_dir():
        return None
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_txt(ws):
    assert _names(ws, "txt") == ["notes.txt", "我的 报告.txt"]


def test_pdf(ws):
    assert _names(ws, "pdf") == ["annual report 2024.pdf"]


def test_csv(ws):
    assert _names(ws, "csv") == ["数据 备份.csv"]


def test_jpg(ws):
    assert _names(ws, "jpg") == ["照片.jpg"]


def test_root_empty(ws):
    left = [p.name for p in (ws / "downloads").iterdir() if p.is_file()]
    assert left == []


def test_content_kept(ws):
    assert (ws / "downloads" / "txt" / "我的 报告.txt").read_text(encoding="utf-8") == "第一份报告\n"
