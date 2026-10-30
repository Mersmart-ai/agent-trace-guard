from pathlib import Path
import os, subprocess, sys

for task in sorted(Path("tasks").iterdir()):#文件夹tasks里面的每一个文件先排序再提出来作为task
    if not (task / "src").is_dir():#task/src如果不是个目录，跳过
        continue

    env = dict(os.environ)#操作系统的环境变量复制出一份作为字典格式
    env["PYTHONPATH"] = str((task / "src").resolve())#task/src的相对路径变成绝对路径再变为字符串赋给PYTHONPATH键作为值

    r = subprocess.run(#subprocess.run启动另一个进程pytest
        [sys.executable, "-m", "pytest", str(task / "tests"), "-q"],
        env=env, capture_output=True, text=True,#把刚刚的env赋给env，捕获子进程打印的东西，以文本格式输出。
    )
#返回的对象r有三个属性：r.returncode：退出码；r.stdout：它打印的正常输出；r.stderr：它打印的错误输出
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""#如果打印的正常输出不为空拿到最后一行的结果作为last，如果为空就用空字符串
    print(f"{task.name:12} exit={r.returncode}  {last}")
