"""把一次运行归成一类。给 runs.csv 的 failure_category 用。

七类，和那份协作文档里给她的定义对齐：

    pass        全过
    wrong_fix   交了，但还有测试红      ← 最需要的那类
    gave_up     一次都没改就撞上限      ← django 那两条
    stuck       改了但一直没搞定
    no_verify   从头到尾没测过就交差
    timeout     某一步测试超时
    other       其他（抛异常之类）
"""

from fbs.actions import is_write
from fbs.legacy.locate import build_states, locate


def classify(history, reason):
    # 不能只数 write_file —— bash 用重定向也能改文件
    writes = sum(1 for h in history if is_write(h))
    states = build_states(history)
    final = locate(states)

    # 单步超时优先判——它会让后面的状态全不可信
    for h in history:
        r = h.get("result")
        if isinstance(r, dict):
            ft = r.get("failed_tests") or []
            if "<timeout>" in ft:
                return "timeout"

    if reason == "right exit":
        if final is None:
            return "no_verify"      # 一次都没测过
        if final == {}:
            return "pass"
        return "wrong_fix"          # 交了但还有红

    if reason == "Hit max_turns":
        return "gave_up" if writes == 0 else "stuck"

    return "other"
