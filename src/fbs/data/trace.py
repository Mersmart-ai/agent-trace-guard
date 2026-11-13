"""落盘：准备 workspace、组装每一步、保存 trace、自检。

agent_loop 只关心"跑"，这个模块关心"记"。
"""
import json
import shutil
from datetime import datetime
from pathlib import Path


def prepare_workspace(task_dir, run_dir):
    """
    复制任务的 src 生成副本，作为 agent 的工作区。

    数据流：
        tasks/<task>/src/  --复制-->  runs/<task>/workspace/
        tasks/<task>/tests/ 不复制（agent 永远接触不到判据）

    :param task_dir: 任务根目录，里面必须有 src/ 子目录；
                     例如 tasks/task_0001
    :param run_dir:  本次运行专用目录，函数会在它下面创建 workspace/；
                     例如 runs/task_0001
    :return: run_dir/workspace 的 Path；task_dir 或 src 不存在时返回 None

    为什么每次都要先删除旧 workspace：
      - 上一次运行的修改、临时文件、__pycache__ 会残留
      - agent 可能看到它没有创建过的文件，之后 trace 的因果解释就不可信
      - 正常轨迹分布必须从"干净副本"开始

    为什么 run_dir 必须是本次运行专用：
      - 如果多个 run 共用一个目录，删除会互相影响
      - 多轮任务（multi_0001）只在任务开始时 prepare 一次，
        同一任务的多轮共用这个干净 workspace，这是有意设计

    为什么复制时忽略缓存：
      - __pycache__ / *.pyc / .pytest_cache 是生成物，不是题目源码
      - 复制它们会让工作区变脏，也会让不同 run 的起点不一致
    """
    task_dir = Path(task_dir)
    run_dir = Path(run_dir)
    if not task_dir.is_dir():
        return None
    src = task_dir / "src"
    if not src.is_dir():
        return None

    dst = run_dir / "workspace"
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    return dst


def make_step(step, tool, args, result, ok=True, test_state=None, judge=None):
    """
    格式化 history 里的一步。

    :param step:轮次
    :param tool:本次调用的工具
    :param args:工具参数
    :param result:工具返回的结果
    :param ok:调用是否成功拿到数据
    :param test_state:这一步的测试状态（只有 write / run_tests 才有值）
    :param judge:这一步用的是哪套判据（目录名）。多轮任务里每轮判据不同，
                 不记这个的话，regressions 会把"换了一套判据"误当成"某条测试变红"。
    :return:可以序列化成 json 的字典
    """
    return {
        "step": step,
        "tool": tool,
        "args": args,
        "result": result,
        "ok": ok,
        "test_state": test_state,
        "judge": judge,
    }


def save_run(task_name, history, reason):
    """
    把一次运行写进 data/traces/<task>/rNN.json。

    :param task_name: 任务目录名，决定 data/traces/<task>/ 和 run_id 前缀；
                      例如 "task_0001"
    :param history:   本次运行的全部 step 记录
    :param reason:    结束原因：
                        "right exit"     = 模型自己调用了 finish
                        "Hit max_turns"  = 撞到轮数上限
    :return: run_id，例如 "task_0001_r01"
    """
    folder = Path("data/traces") / task_name
    folder.mkdir(parents=True, exist_ok=True)

    nums = [int(p.stem[1:]) for p in folder.glob("r*.json")]
    n = 1 if not nums else max(nums) + 1

    path = folder / f"r{n:02d}.json"
    run_id = f"{task_name}_r{n:02d}"

    data = {
        "run_id": run_id,
        "task": task_name,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "steps": history,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_id


def check_trace(history):
    """自检：每个 write_file 步都必须带 test_state。

    这是「强制判分生效」的标志。locate() 的正确性依赖这一条——
    它把 test_state=None 理解成「这步不改变状态」，而只有强制判分存在时，
    这个理解才成立（write 步一定是非 None）。
    哪天强制判分被拆掉，这个函数会立刻报出异常步号，
    而不是让 locate 的结果悄悄变错。

    :return: 缺测试状态的 write_file 步号列表，空列表表示正常
    """
    from fbs.actions import is_write

    # 不能只看 write_file：bash 用重定向 / mv 也能改文件，那些步同样该有状态
    return [h["step"] for h in history
            if is_write(h) and h["test_state"] is None]
