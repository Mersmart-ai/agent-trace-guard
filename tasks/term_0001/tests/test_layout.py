"""检查 downloads 是否按扩展名分好类。"""


def _files_in(ws, sub):
    """某个子目录里的文件名列表；目录不存在返回 None。"""
    d = ws / sub
    if not d.is_dir():
        return None
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_images(ws):
    assert _files_in(ws, "images") == [
        "banner.gif",
        "icon.webp",
        "logo.jpeg",
        "photo_01.jpg",
        "photo_02.JPG",
    ]


def test_docs(ws):
    assert _files_in(ws, "docs") == ["note.txt", "report.docx", "scan.pdf"]


def test_videos(ws):
    assert _files_in(ws, "videos") == ["clip.mp4", "movie.MOV"]


def test_others(ws):
    assert _files_in(ws, "others") == ["data.csv"]


def test_downloads_left_only_untouchables(ws):
    """downloads/ 里只该剩 .hidden 和 README.md。"""
    left = _files_in(ws, "downloads")
    assert left == [".hidden", "README.md"]
