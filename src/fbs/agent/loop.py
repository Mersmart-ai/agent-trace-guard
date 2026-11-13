"""agent 的主循环：问模型要动作 → 执行 → 记录，直到 finish 或用完轮数。

这个文件只做"调度"，具体操作在 tools，判分在 judge，记录在 trace。
出问题时按这个顺序查：模型选错了工具（policy）→ 工具做错了（tools）
→ 判分判错了（judge）→ 记录记错了（trace）。
"""
from pathlib import Path

from fbs.agent.judge import judge_ok, judge_state
from fbs.agent.tools import bash, grep, list_files, read_file, run_tests, write_file
from fbs.data.trace import make_step
from fbs.llm import OutOfCredit

MAX_TURNS = 60


def agent_loop(workspace, tests, policy, judge_tests=None, opts=None):
    """
    agent 的循环核心

    :param workspace:agent 的工作区路径
    :param tests:模型能看到的测试目录（它调 run_tests 时跑这个）
    :param policy:决定下一步动作的函数
    :param judge_tests:判据用的目录。None 表示和 tests 是同一套。
                       模型永远看不到这个目录的结果——这是"隐藏测试"的入口。
    :param opts:可选配置 dict，键：
                 python          —— 用哪个解释器跑测试（默认当前进程的）
                 visible_command —— 模型调 run_tests 时执行的命令（不给就走 pytest）
                 judge_command   —— 判据执行的命令（不给就沿用 visible_command）
                 命令里可以用 {python} 占位符。给 command 时 cwd 是 workspace。
    :return:(history, reason)
    """
    judge_dir = judge_tests or tests
    judge_name = Path(judge_dir).name if judge_tests else None
    opts = opts or {}
    py = opts.get("python")
    visible_cmd = opts.get("visible_command")
    judge_cmd = opts.get("judge_command") or visible_cmd
    history = []
    for step in range(1, MAX_TURNS + 1):
        action = {}     # policy 接不住异常时，保证后面有值可用
        try:
            action = policy(step, history)
            if action["tool"] == "finish":
                history.append(make_step(step, action["tool"], action["args"], "right_finish"))
                break

            test_state = None
            step_judge = None
            if action["tool"] == "list_files":
                result = list_files(workspace)
            elif action["tool"] == "read_file":
                result = read_file(workspace, action["args"]["path"])
            elif action["tool"] == "grep":
                result = grep(workspace,
                              action["args"].get("pattern", ""),
                              action["args"].get("path", "."))
            elif action["tool"] == "bash":
                result = bash(workspace, action["args"].get("command", ""))
                # bash 会改文件系统（mv / rm / cp / touch），所以也要判分。
                # 不加这一条的话，终端任务的 trace 每隔十几步才有一个 test_state，
                # 根本看不出"哪一步把东西弄坏了"。
                # 代价：只读命令（ls / cat）也白跑一次测试，0.1 秒，可以接受。
                test_state = judge_state(run_tests(workspace, judge_dir, python=py, command=judge_cmd))
                step_judge = judge_name
            elif action["tool"] == "write_file":
                result = write_file(workspace, action["args"]["path"], action["args"]["content"])
                # 强制判分：写完由循环自动测一次，状态记在这一步上。
                # 注意 result 仍然是"写入成功"——模型看不到这次测试的结果，
                # 这样它自己调 run_tests 的记录还留着，可以统计"它有没有主动验证"。
                test_state = judge_state(run_tests(workspace, judge_dir, python=py, command=judge_cmd))
                step_judge = judge_name
            elif action["tool"] == "run_tests":
                # 两套测试分开：模型看到的（tests）和记进 trace 的（judge_dir）。
                # 没配隐藏测试时两者相同，只跑一次。
                result = run_tests(workspace, tests, python=py, command=visible_cmd)
                if judge_tests or judge_cmd:
                    test_state = judge_state(
                        run_tests(workspace, judge_dir, python=py, command=judge_cmd))
                    step_judge = judge_name
                else:
                    test_state = judge_state(result)
            else:
                result = f"【错误】：未知工具{action['tool']}"

            ok = judge_ok(result)
            history.append(make_step(step, action["tool"], action["args"], result, ok,
                                      test_state, step_judge))
        except OutOfCredit:
            # 余额不足不是任务失败，别当成【错误】记下去。往上抛，让 main 停掉整批。
            raise
        except Exception as e:
            result = f"【错误】：{e}"
            # policy 抛异常时 action 还是空的 {}，tool 会是 None。
            # 记成 "error" 而不是 None，否则后面按 tool 分组统计会漏掉这些步。
            history.append(make_step(step, action.get("tool") or "error",
                                     action.get("args") or {}, result, False))

    if history and history[-1]["tool"] == "finish":
        reason = "right exit"
    else:
        reason = "Hit max_turns"
    return history, reason
