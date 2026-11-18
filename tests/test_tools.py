"""run_tests 的命令渲染：{python} 必须带引号。"""
import shlex

from fbs.agent.tools import render_command


def test_render_command_quotes_python_path():
    python = r"C:\Program Files\Python 3.12\python.exe"
    rendered = render_command("{python} tests/runtests.py --verbosity 0", python)
    assert rendered == f"{shlex.quote(python)} tests/runtests.py --verbosity 0"


def test_render_command_without_placeholder():
    assert render_command("pytest -q", "py") == "pytest -q"
