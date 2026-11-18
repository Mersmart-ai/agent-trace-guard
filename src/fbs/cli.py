"""入口：挑任务 → 跑一轮 → 存 trace。

其余都在别的模块里：
    policy.py   给模型看什么（提示词、工具清单）
    loop.py     怎么循环
    tools.py    能做什么操作
    judge.py    测试结果怎么判
    trace.py    怎么记录（写 data/traces/）
    locate.py   旧的标签工具：算最终判分/翻转点，不是当前主线

跑法：python run.py（或 PYTHONPATH=src python -m fbs.cli）
注意要在项目根目录下运行，tasks/ runs/ data/ 都是相对路径。
"""
import json
from pathlib import Path

from fbs.agent.loop import agent_loop
from fbs.agent.policy import model_policy
from fbs.data.trace import check_trace, prepare_workspace, save_run
from fbs.llm import OutOfCredit

# meta.json 里允许透传给 agent_loop 的键。
# 漏一个就会出现“real_runs 跑得对、python run.py 跑得不对”的两套行为。
OPT_KEYS = (
    "python", "visible_command", "judge_command", "fast_judge_command",
    "judge_timeout", "fast_judge_timeout", "visible_timeout", "max_turns",
)


def opts_from_meta(meta):
    """从 meta.json 取出 agent_loop 需要的配置；空值不传。"""
    return {key: meta[key] for key in OPT_KEYS if meta.get(key)}


def main():
    # 只跑一个任务：填相对路径，比如 "tasks/boltons_0002"
    # 跑全部：改成 None
    # 可以填一个路径、一个路径列表，或者 None（跑全部）
    ONLY = ["tasks/amb_rename_vague", "tasks/amb_rename_clear", "tasks/amb_merge_vague", "tasks/amb_merge_clear", "tasks/amb_clean_vague", "tasks/amb_clean_clear"]

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
        # 有三种情况允许 tests/ 为空：配了命令、配了多轮（测试在 roundN/tests 里）
        _has_cmd = bool(_meta.get("visible_command") or _meta.get("judge_command")
                        or _meta.get("rounds"))
        if not _has_cmd and not list((task / "tests").glob("test_*.py")):
            print(f"⚠️  {task.name}: tests/ 里没有 test_*.py，跳过")
            continue

        workspace = prepare_workspace(task, Path("runs") / task.name)
        if workspace is None:
            continue
        # 多轮任务的说明在 roundN/task.md 里，没有顶层 task.md
        task_md = ""
        if (task / "task.md").exists():
            task_md = (task / "task.md").read_text(encoding="utf-8")

        # 方案 A 用 model_policy；方案 B 换成 model_policy_structured
        policy = model_policy(task_md)

        # 有 tests_hidden/ 就用它当判据，没有就用 tests/
        hidden = task / "tests_hidden"
        judge_tests = hidden if hidden.is_dir() else None
        if judge_tests:
            print(f"   隐藏测试已启用：{len(list(hidden.glob('test_*.py')))} 个文件")

        # meta.json 里可以指定解释器、测试命令、judge 超时和轮数
        meta = {}
        meta_file = task / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        opts = opts_from_meta(meta)
        if opts.get("judge_command"):
            judge_tests = None          # 用命令判据，就不用目录了
        if opts:
            print(f"   自定义测试配置：{sorted(opts)}")

        rounds = meta.get("rounds")   # ["round1", "round2"] 这样的目录名

        try:
            if rounds:
                # 多轮：同一个 workspace，每轮换一份任务说明和一套可见测试。
                # 判据始终是 tests_hidden/，模型看不到。
                history, f_reason = [], "right exit"
                offset = 0
                for i, r in enumerate(rounds, 1):
                    # rounds 的元素可以是字符串（用全局判据），
                    # 也可以是 {"dir": "round2", "judge": "hidden2"}，
                    # 后者让每轮用自己的判据——否则第 1 轮会被第 2 轮的测试拖红。
                    if isinstance(r, str):
                        rdir, rjudge = task / r, judge_tests
                    else:
                        rdir = task / r["dir"]
                        rjudge = task / r["judge"] if r.get("judge") else judge_tests

                    r_md = (rdir / "task.md").read_text(encoding="utf-8")
                    r_policy = model_policy(r_md)
                    h, r_reason = agent_loop(workspace, rdir / "tests", r_policy,
                                             judge_tests=rjudge, opts=opts)
                    # 步号接着上一轮，否则合并后 step 会重复
                    for x in h:
                        x["step"] += offset
                    offset += len(h)
                    history.extend(h)
                    print(f"   第 {i} 轮（{rdir.name}）：{len(h)} 步  {r_reason}")
                    if r_reason != "right exit":
                        f_reason = r_reason
                        break
            else:
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

if __name__ == "__main__":
    main()
