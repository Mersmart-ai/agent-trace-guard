"""规则监控：把过程偏离的判断收成一个模块。

不依赖 Fisher、不依赖标签；只读 history / trace。

规则：
  no_verify  整条轨迹一次 run_tests 都没调（只在整个 trace 结束时判）
  delta      任意一步出现新的红测试（集合差，不只看数量）
  dup2       任意一步 repeat_streak >= 2（连续重复 3 次以上）
  error      任意一步 ok == False（工具调用失败）
  long_gap   任意一步 since_test > 15（太久没显式 run_tests）
  unverified_write 最后一次写之后没有 run_tests（长程里常见）
  blind      任意一次成功 write_file 的目标文件，写之前没读过（只算 read_file，
             grep 片段不算；新建文件除外）

strict 规则 = no_verify + delta + dup2 + error + long_gap + unverified_write
full 规则   = strict + blind
"""
from fbs.analysis.features import step_features

RULES = ("no_verify", "delta", "dup2", "error", "long_gap", "unverified_write", "blind")
STRICT_RULES = ("no_verify", "delta", "dup2", "error", "long_gap", "unverified_write")
LONG_GAP = 15


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

    row = _first(rows, lambda r: bool(r["new_red"]))
    if row:
        alarms.append({
            "rule": "delta",
            "step": row["step"],
            "detail": f"new_red={','.join(row['new_red'])}",
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

    row = _first(rows, lambda r: r["since_test"] > LONG_GAP)
    if row:
        alarms.append({
            "rule": "long_gap",
            "step": row["step"],
            "detail": f"since_test={row['since_test']}",
        })

    writes = [i for i, row in enumerate(rows) if row["kind"] == "write"]
    if writes:
        last_write = writes[-1]
        if not any(row["kind"] == "verify" for row in rows[last_write + 1:]):
            alarms.append({
                "rule": "unverified_write",
                "step": rows[-1]["step"],
                "detail": "last write not followed by run_tests",
            })

    # blind 按目标文件判断，而不是“整条 trace 有没有读过任何文件”：
    #   读 a.py 之后盲写 b.py 仍然是 blind；新建文件则不算。
    read_paths = set()
    created_paths = set()
    blind_row = None
    for row in rows:
        if row["tool"] == "read_file" and row["ok"] and row["path"]:
            read_paths.add(row["path"])
        if row["path_missing"] and row["path"]:
            created_paths.add(row["path"])
        if (
            blind_row is None
            and row["tool"] == "write_file"
            and row["ok"]
            and row["path"]
            and row["path"] not in read_paths
            and row["path"] not in created_paths
        ):
            blind_row = row

    if blind_row is not None:
        alarms.append({
            "rule": "blind",
            "step": blind_row["step"],
            "detail": f"write_file {blind_row['path']} without prior read",
        })

    return alarms


def strict_alarms(alarms):
    """只保留 strict 规则。"""
    return [a for a in alarms if a["rule"] in STRICT_RULES]
