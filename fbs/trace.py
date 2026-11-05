"""落盘：准备 workspace、组装每一步、保存 trace、自检。

agent_loop 只关心"跑"，这个模块关心"记"。
trace 是后面做归因的唯一原料，所以格式要稳定。
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def prepare_workspace(task_dir, run_dir):
    """
    复制任务的 src 生成副本，作为 agent 的工作区。
    tests 不在 src 里，所以 agent 永远接触不到测试。

    :param task_dir:任务目录
    :param run_dir:副本要放的地方
    :return:工作区路径；没有 src 就返回 None
    """
    if not os.path.isdir(task_dir):
        return None
    src = task_dir / "src"
    if src.is_dir():
        dst = run_dir / "workspace"
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return dst
    return None


def make_step(step, tool, args, result, ok=True, test_state=None):
    """
    格式化 history 里的一步。

    :param step:轮次
    :param tool:本次调用的工具
    :param args:工具参数
    :param result:工具返回的结果
    :param ok:调用是否成功拿到数据
    :param test_state:这一步的测试状态（只有 write / run_tests 才有值）
    :return:可以序列化成 json 的字典
    """
    return {
        "step": step,
        "tool": tool,
        "args": args,
        "result": result,
        "ok": ok,
        "test_state": test_state,
    }


def save_run(task_name, history, reason):
    """
    把一次运行写进 run_traces/<task>/rNN.json。

    :param task_name:任务名
    :param history:这次运行的 history
    :param reason:结束原因（right exit / Hit max_turns）
    :return:run_id
    """
    folder = Path("run_traces") / task_name
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
