"""入口：挑任务 → 跑一轮 → 存 trace → 打归因。

其余都在别的模块里：
    policy.py   给模型看什么（提示词、工具清单）
    loop.py     怎么循环
    tools.py    能做什么操作
    judge.py    测试结果怎么判
    trace.py    怎么记录
    locate.py   怎么归因

跑法：python -m fbs.agent   （或根目录的 run.py）
注意要在项目根目录下运行，tasks/ runs/ run_traces/ 都是相对路径。
"""
import json
from pathlib import Path

from fbs.locate import build_states, locate, regressions, render
from fbs.loop import agent_loop
from fbs.my_llm import OutOfCredit
from fbs.policy import model_policy
from fbs.trace import check_trace, prepare_workspace, save_run


def main():
    # 只跑一个任务：填相对路径，比如 "tasks/boltons_0002"
    # 跑全部：改成 None
    # 可以填一个路径、一个路径列表，或者 None（跑全部）
    ONLY = "tasks/django_16820"

    if isinstance(ONLY, str):
        ONLY = [ONLY]
    todo = [Path(p) for p in ONLY] if ONLY else sorted(Path("tasks").iterdir())

    for task in todo:
        if not (task / "src").is_dir():
            continue
        # 没有测试文件的 task 是"题目配错了"，不该产出一条 trace。
        # 让脏数据进 trace，比不跑更糟——以后分析时会把"没测"当成"通过了"。
        # 例外：meta.json 配了 visible_command / judge_command 的（比如 django），
        # 测试不在 tests/ 目录里，靠命令跑，所以 tests/ 可以是空的。
        _mf = task / "meta.json"
        _meta = json.loads(_mf.read_text(encoding="utf-8")) if _mf.exists() else {}
        _has_cmd = bool(_meta.get("visible_command") or _meta.get("judge_command"))
        if not _has_cmd and not list((task / "tests").glob("test_*.py")):
            print(f"⚠️  {task.name}: tests/ 里没有 test_*.py，跳过")
            continue

        workspace = prepare_workspace(task, Path("runs") / task.name)
        if workspace is None:
            continue
        task_md = (task / "task.md").read_text(encoding="utf-8")

        # 方案 A 用 model_policy；方案 B 换成 model_policy_structured
        policy = model_policy(task_md)

        # 有 tests_hidden/ 就用它当判据，没有就用 tests/
        hidden = task / "tests_hidden"
        judge_tests = hidden if hidden.is_dir() else None
        if judge_tests:
            print(f"   隐藏测试已启用：{len(list(hidden.glob('test_*.py')))} 个文件")

        # meta.json 里可以指定解释器和测试命令（django 这类不用 pytest 的项目）
        opts = {}
        meta_file = task / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            for k in ("python", "visible_command", "judge_command"):
                if meta.get(k):
                    opts[k] = meta[k]
            if opts.get("judge_command"):
                judge_tests = None      # 用命令判据，就不用目录了
            if opts:
                print(f"   自定义测试配置：{sorted(opts)}")

        try:
            history, f_reason = agent_loop(workspace, task / "tests", policy,
                                           judge_tests=judge_tests, opts=opts)
        except OutOfCredit as e:
            print(f"❌ API 余额不足，停在 {task.name}。")
            print("   已经跑完的任务 trace 是有效的，后面的没有生成。")
            print(f"   原始报错：{e}")
            break

        bad = check_trace(history)
        if bad:
            print(f"⚠️  {task.name}: 第 {bad} 步写了文件却没有测试状态，强制判分可能没生效")

        run_id = save_run(task.name, history, f_reason)
        print(f"[saved] {run_id}  {f_reason}  {len(history)} 步")

        # 归因：先把每步的测试状态摊成一串，再分别看形状和结论
        states = build_states(history)
        print(f"  {render(states)}  ->  locate={locate(states)}")
        reg = regressions(states)
        if reg:
            print(f"      regressions={reg}")


if __name__ == "__main__":
    main()
