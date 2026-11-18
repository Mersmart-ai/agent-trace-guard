"""cli 的配置透传：meta.json 里的 judge/超时/轮数必须全部交给 agent_loop。"""
from fbs.cli import DEFAULT_ONLY, opts_from_meta, parse_only


def test_parse_only_default():
    assert parse_only(None) == DEFAULT_ONLY
    assert parse_only("") == DEFAULT_ONLY


def test_parse_only_all():
    assert parse_only("all") is None
    assert parse_only("ALL") is None


def test_parse_only_list():
    assert parse_only("tasks/a, tasks/b") == ["tasks/a", "tasks/b"]


def test_opts_from_meta_passes_all_loop_keys():
    meta = {
        "python": "py",
        "visible_command": "python -m pytest -q",
        "judge_command": "python -m pytest tests -q",
        "fast_judge_command": "python -m pytest tests/test_a.py -q",
        "judge_timeout": 180,
        "fast_judge_timeout": 60,
        "visible_timeout": 30,
        "max_turns": 12,
        "rounds": ["round1"],       # 不属于 loop 配置，不能混进来
    }
    assert opts_from_meta(meta) == {
        "python": "py",
        "visible_command": "python -m pytest -q",
        "judge_command": "python -m pytest tests -q",
        "fast_judge_command": "python -m pytest tests/test_a.py -q",
        "judge_timeout": 180,
        "fast_judge_timeout": 60,
        "visible_timeout": 30,
        "max_turns": 12,
    }


def test_opts_from_meta_skips_empty_values():
    assert opts_from_meta({}) == {}
    assert opts_from_meta({"judge_command": "", "max_turns": None}) == {}
