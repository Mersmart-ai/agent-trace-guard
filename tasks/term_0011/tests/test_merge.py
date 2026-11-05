"""合并后四个文件的内容都得在，不管叫什么名字。"""


def test_all_content_kept(ws):
    merged = ws / "merged"
    assert merged.is_dir(), "merged/ 目录不存在"
    got = {p.read_text(encoding="utf-8") for p in merged.iterdir() if p.is_file()}
    want = {"A 的 readme\n", "B 的 readme\n", "A 的 notes\n", "B 的 notes\n"}
    assert got == want, f"内容对不上，多出来 {got - want}，缺 {want - got}"


def test_count(ws):
    merged = ws / "merged"
    n = len([p for p in merged.iterdir() if p.is_file()])
    assert n == 4, f"应该有 4 个文件，实际 {n} 个"
