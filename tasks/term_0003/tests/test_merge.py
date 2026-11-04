"""检查分段文件是否按数字顺序拼好。"""


def test_merged_exists(ws):
    assert (ws / "merged.txt").is_file(), "merged.txt 不存在"


def test_merged_order(ws):
    """内容必须是 line 1 到 line 11，按数字顺序。

    坑：parts/part_*.txt 按字典序是 1, 10, 11, 2, 3...，直接 cat 会乱。
    """
    lines = (ws / "merged.txt").read_text(encoding="utf-8").splitlines()
    assert lines == [f"line {i}" for i in range(1, 12)]


def test_parts_kept(ws):
    """原文件不能删。"""
    parts = ws / "parts"
    assert parts.is_dir()
    assert len(sorted(parts.glob("part_*.txt"))) == 11
