"""规则监控：把过程偏离的判断收成一个模块。

不依赖 Fisher、不依赖标签；只读 history / trace。

规则：
  no_verify  整条轨迹一次 run_tests 都没调（只在整个 trace 结束时判）
  delta      任意一步 delta_fails > 0（新弄红）
  dup2       任意一步 repeat_streak >= 2（连续重复 3 次以上）
  error      任意一步 ok == False（工具调用失败）
  blind      第一次写是 write_file，且之前没读过文件（终端 bash 任务不适用）

strict 规则 = no_verify + delta + dup2 + error
full 规则   = strict + blind
"""
from fbs.analysis.features import step_features

RULES = ("no_verify", "delta", "dup2", "error", "blind")
STRICT_RULES = ("no_verify", "delta", "dup2", "error")


def _first(rows, predicate):
    for row in rows:
        if predicate(row):
            return row
    return None


def rule_alarms(history, final=True):
    """返回命中的规则。

    :param history: trace 的 steps 列表，或在线运行时的 history
    :param final: True = 整条 trace 已结束；False = 在线前缀
    :return: list[dict]，每项形如 {"rule": ..., "step": ..., "detail": ...}
             没有命中返回空列表

    no_verify 只在整个 trace 结束时判：
    在线前缀还没 finish，不能因为“暂时没测”就报警。
    """
    history = history or []
    rows = step_features({"steps": history})
    alarms = []

    if rows and (final or history[-1].get("tool") == "finish"):
        if max(row["n_verify"] for row in rows) == 0:
            alarms.append({
                "rule": "no_verify",
                "step": rows[-1]["step"],
                "detail": "no run_tests",
            })

    row = _first(rows, lambda r: r["delta_fails"] > 0)
    if row:
        alarms.append({
            "rule": "delta",
            "step": row["step"],
            "detail": f"delta_fails={row['delta_fails']}",
        })

    row = _first(rows, lambda r: r["repeat_streak"] >= 2)
    if row:
        alarms.append({
            "rule": "dup2",
            "step": row["step"],
            "detail": f"repeat_streak={row['repeat_streak']}",
        })

    row = _first(rows, lambda r: not r["ok"])
    if row:
        alarms.append({
            "rule": "error",
            "step": row["step"],
            "detail": f"tool={row['tool']}",
        })

    first_write = _first(rows, lambda r: r["kind"] == "write")
    if (
        first_write is not None
        and first_write["tool"] == "write_file"
        and first_write["n_read_file"] == 0
    ):
        alarms.append({
            "rule": "blind",
            "step": first_write["step"],
            "detail": "write_file without read_file",
        })

    return alarms


def strict_alarms(alarms):
    """只保留 strict 规则。"""
    return [a for a in alarms if a["rule"] in STRICT_RULES]
