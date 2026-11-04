"""agent 的主循环：问模型要动作 → 执行 → 记录，直到 finish 或用完轮数。

这个文件只做"调度"，具体操作在 tools，判分在 judge，记录在 trace。
出问题时按这个顺序查：模型选错了工具（policy）→ 工具做错了（tools）
→ 判分判错了（judge）→ 记录记错了（trace）。
"""
from fbs.judge import judge_ok, judge_state
from fbs.my_llm import OutOfCredit
from fbs.tools import grep, list_files, read_file, run_tests, write_file
from fbs.trace import make_step

MAX_TURNS = 30


def agent_loop(workspace, tests, policy):
    """
    agent 的循环核心

    :param workspace:agent 的工作区路径
    :param tests:pytest 测试路径，agent 看不到
    :param policy:决定下一步动作的函数
    :return:(history, reason)
    """
    history = []
    for step in range(1, MAX_TURNS + 1):
        action = {}     # policy 接不住异常时，保证后面有值可用
        try:
            action = policy(step, history)
            if action["tool"] == "finish":
                history.append(make_step(step, action["tool"], action["args"], "right_finish"))
                break

            test_state = None
            if action["tool"] == "list_files":
                result = list_files(workspace)
            elif action["tool"] == "read_file":
                result = read_file(workspace, action["args"]["path"])
            elif action["tool"] == "grep":
                result = grep(workspace,
                              action["args"].get("pattern", ""),
                              action["args"].get("path", "."))
            elif action["tool"] == "write_file":
                result = write_file(workspace, action["args"]["path"], action["args"]["content"])
                # 强制判分：写完由循环自动测一次，状态记在这一步上。
                # 注意 result 仍然是"写入成功"——模型看不到这次测试的结果，
                # 这样它自己调 run_tests 的记录还留着，可以统计"它有没有主动验证"。
                test_state = judge_state(run_tests(workspace, tests))
            elif action["tool"] == "run_tests":
                result = run_tests(workspace, tests)
                test_state = judge_state(result)
            else:
                result = f"【错误】：未知工具{action['tool']}"

            ok = judge_ok(result)
            history.append(make_step(step, action["tool"], action["args"], result, ok, test_state))
        except OutOfCredit:
            # 余额不足不是任务失败，别当成【错误】记下去。往上抛，让 main 停掉整批。
            raise
        except Exception as e:
            result = f"【错误】：{e}"
            history.append(make_step(step, action.get("tool"), action.get("args") or {}, result, False))

    if history and history[-1]["tool"] == "finish":
        reason = "right exit"
    else:
        reason = "Hit max_turns"
    return history, reason
