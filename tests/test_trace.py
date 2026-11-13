from pathlib import Path

from fbs.data.trace import prepare_workspace


def test_prepare_workspace_resets_stale_files(tmp_path):
    task = tmp_path / "task"
    src = task / "src"
    src.mkdir(parents=True)
    (src / "calc.py").write_text("x = 1\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "calc.pyc").write_bytes(b"bad")

    run_dir = tmp_path / "run"
    stale = run_dir / "workspace" / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")

    ws = prepare_workspace(task, run_dir)

    assert ws == run_dir / "workspace"
    assert (ws / "calc.py").read_text(encoding="utf-8") == "x = 1\n"
    assert not (ws / "stale.txt").exists()
    assert not (ws / "__pycache__").exists()


def test_prepare_workspace_missing_src_returns_none(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    assert prepare_workspace(task, tmp_path / "run") is None
