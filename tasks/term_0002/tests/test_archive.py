"""检查日志是否按月份归档。"""


def _files_in(ws, sub):
    d = ws / sub
    if not d.is_dir():
        return None
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_august(ws):
    assert _files_in(ws, "archive/2026-08") == [
        "app_2026-08-01.log",
        "app_2026-08-15.log",
        "error_2026-08-03.log",
    ]


def test_september(ws):
    assert _files_in(ws, "archive/2026-09") == [
        "app_2026-09-01.log",
        "app_2026-09-20.log",
        "error_2026-09-11.log",
    ]


def test_october(ws):
    assert _files_in(ws, "archive/2026-10") == [
        "app_2026-10-05.log",
        "error_2026-10-11.log",
    ]


def test_logs_left_only_readme(ws):
    """logs/ 里只该剩 README.txt——日志是移动走的，不是复制。"""
    assert _files_in(ws, "logs") == ["README.txt"]
