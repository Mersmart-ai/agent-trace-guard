"""合并后按 _a / _b 后缀区分。"""


def _names(ws):
    d = ws / "merged"
    if not d.is_dir():
        return None
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_names(ws):
    assert _names(ws) == ["data_a.txt", "data_b.txt", "readme_a.md", "readme_b.md"]


def test_content(ws):
    m = ws / "merged"
    assert (m / "readme_a.md").read_text(encoding="utf-8") == "A 的说明\n"
    assert (m / "readme_b.md").read_text(encoding="utf-8") == "B 的说明\n"
