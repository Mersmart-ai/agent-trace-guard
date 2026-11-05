"""按 01_ / 02_ / 03_ 前缀重命名。"""


def _names(ws):
    d = ws / "notes"
    return sorted(p.name for p in d.iterdir() if p.is_file())


def test_prefix(ws):
    assert _names(ws) == ["01_alpha.txt", "02_beta.txt", "03_gamma.txt"]


def test_content(ws):
    n = ws / "notes"
    assert (n / "01_alpha.txt").read_text(encoding="utf-8") == "A\n"
