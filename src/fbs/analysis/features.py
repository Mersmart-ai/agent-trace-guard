"""把 trace 提取成数字特征。

现在有 run 级计数和步级特征；序列级特征后续再加。
只读 history，不读标签、不读最终结果，
保证离线校准和在线监控用的是同一套口径。
"""
import json

from fbs.actions import TOOL_KINDS, tool_kind


def run_features(trace):
    """把一条 trace 压成一行 run 级特征。

    :param trace: dict，一条 trace，至少含 "steps" 列表；
                  每步形如 {"tool": "write_file", "args": {...}, ...}
    :return: dict，6 个键：
             steps     总步数
             navigate  list_files / grep 的步数
             read      read_file / 只读 bash 的步数
             write     改文件系统的步数（write_file 或写文件的 bash）
             verify    run_tests 的步数
             other     finish 等其余步数

    动作分类统一走 fbs.actions.tool_kind，
    和 data/labels/healthy.csv 的计数是同一个函数算出来的。
    """
    history = trace.get("steps") or []
    counts = {kind: 0 for kind in TOOL_KINDS}
    for h in history:
        counts[tool_kind(h)] += 1
    return {"steps": len(history), **counts}


def step_features(trace):
    """逐步提取特征；每一行只用当前步及之前的信息。

    :param trace: dict，一条 trace，含 "steps" 列表
    :return: list[dict]，一行一步，字段：
             step         步号（优先用 trace 里的 "step"，缺失时用 1-based 序号）
             tool         工具名
             kind         tool_kind 五类
             ok           工具调用是否成功
             tested       这一步后有没有 test_state（含写后强制判分）
             fails        红测试条数；没测过时为 0，用 tested 区分
             delta_fails  和上一次同判据的观测比，红测试增减
             since_test   距上次 run_tests 几步；从没测过就一直累加
             since_write  距上次写几步
             result_len   工具输出的字符数
             prev_kind    上一步的 kind；第一步为 None

    注意 since_test 只在 run_tests 时归零：
    写后强制判分也有 test_state，但那不算"主动验证"，
    所以 tested=True 时 since_test 仍然继续累加。
    """
    history = trace.get("steps") or []
    rows = []
    prev_kind = None
    last_fails = None
    last_judge = None
    since_test = 0
    since_write = 0

    for i, h in enumerate(history, 1):
        kind = tool_kind(h)
        tested = h.get("test_state") is not None
        state = h.get("test_state")
        fails = len(state) if isinstance(state, list) else 0
        judge = h.get("judge")

        since_test = 0 if kind == "verify" else since_test + 1
        since_write = 0 if kind == "write" else since_write + 1

        delta = 0
        if tested:
            # 判据换了就不能相减：多轮任务里两套判据的失败集合不可比
            if last_fails is not None and judge == last_judge:
                delta = fails - last_fails
            last_fails = fails
            last_judge = judge

        result = h.get("result")
        rows.append({
            "step": h.get("step", i),
            "tool": h.get("tool"),
            "kind": kind,
            "ok": bool(h.get("ok")),
            "tested": tested,
            "fails": fails,
            "delta_fails": delta,
            "since_test": since_test,
            "since_write": since_write,
            "result_len": len(json.dumps(result, ensure_ascii=False)) if result is not None else 0,
            "prev_kind": prev_kind,
        })
        prev_kind = kind

    return rows
