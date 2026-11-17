"""agent 能用的工具：列文件、读文件、写文件、跑测试、搜文本。

这些函数都是"纯操作"——不碰模型，也不碰判分。
agent_loop 根据模型选的工具名，来这里调对应的函数。
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT_SEC = 10
BASH_TIMEOUT = 30

# 必须显式找 bash。Windows 上 shell=True 默认用 cmd.exe，
# 那样 mkdir -p 会被 cmd 的 mkdir 解释（它不认 -p），
# grep/find/tar 的行为也不一样。所以命令要交给 bash 执行。
BASH = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"

# bash 工具只允许这些命令。加不进来的一律拒绝。
# 特别注意：不能放 python / sh / bash / eval / sudo / curl / wget
# —— 它们能绕过下面所有的防护。
ALLOWED = {
    # 看
    "ls", "cat", "head", "tail", "grep", "find", "wc", "sort", "uniq",
    "diff", "tree", "file", "stat", "du", "pwd", "echo",
    # 改
    "cp", "mv", "mkdir", "rm", "touch", "ln",
    # 压缩
    "tar", "gzip", "gunzip", "zip", "unzip",
    # 权限
    "chmod",
}

# 这些命令一出现就拒绝（哪怕在白名单里）
DENY_FLAGS = {"-f", "--force", "-rf", "-fr"}


def _check_command(command):
    """检查一条 shell 命令能不能跑。返回 (ok, 原因)。

    三道防线：
      1. 不许出现 ..            → 挡住 cat ../../tests/x.py
      2. 不许出现绝对路径        → 挡住 cat /etc/passwd（/dev/null 例外）
      3. 每一段的第一个词必须在白名单 → 按 | && || ; 切开逐段查
    """
    if ".." in command:
        return False, "命令里不能出现 ..（会跳出工作区）"

    for token in command.split():
        if token.startswith("/") and token != "/dev/null":
            return False, f"不能使用绝对路径：{token}"

    for seg in re.split(r"\|\||&&|[|;]", command):
        seg = seg.strip()
        if not seg:
            continue
        first = seg.split()[0]
        if first not in ALLOWED:
            return False, f"不允许的命令：{first}"

    for bad in DENY_FLAGS:
        if re.search(rf"(^|\s){re.escape(bad)}(\s|$)", command):
            return False, f"不允许的参数：{bad}"

    return True, ""


def _clip(text, limit=3000):
    """截断过长输出，保留开头（文件名列表这类信息都在开头）。

    text 可能是 None：子进程解码失败时 stderr 会是 None，不能直接 len()。
    """
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...（已截断，原文共 {len(text)} 字符）"


def bash(workspace, command):
    """在工作区里执行一条 shell 命令。

    cwd 固定在 workspace，所以相对路径都落在工作区里面。
    配合 _check_command 的禁 .. 和禁绝对路径，模型跳不出去。

    :param command:模型给的命令字符串，可以带管道、重定向
    :return:{"exit_code": 退出码, "stdout": ..., "stderr": ...}
    """
    ok, reason = _check_command(command)
    if not ok:
        return {"exit_code": 126, "stdout": "", "stderr": f"【拒绝】{reason}"}

    try:
        r = subprocess.run(
            [BASH, "-c", command], cwd=str(Path(workspace).resolve()),
            capture_output=True, text=True, timeout=BASH_TIMEOUT,
            # Windows 上子进程输出不一定是 UTF-8，不加 errors="replace"
            # 会在解码时抛 UnicodeDecodeError，stderr 变成 None，后面崩。
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "",
                "stderr": f"【超时】命令超过 {BASH_TIMEOUT} 秒没结束"}
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": f"【错误】{e}"}

    return {"exit_code": r.returncode,
            "stdout": _clip(r.stdout),
            "stderr": _clip(r.stderr)}


def parse_failed(output):
    """从 pytest 输出里取出没通过的测试名。
    pytest 的 -q 模式不列通过的测试，只列 FAILED / ERROR，所以只能拿到失败的。
    """
    names = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            node = line.split(None, 1)[1]        # 去掉开头的 FAILED/ERROR
            node = node.split(" - ")[0]          # 去掉后面的错误详情
            names.append(node.split("::")[-1])   # 只留测试函数名
    return names


def parse_unittest_failed(output):
    """从 unittest / django runtests.py 的输出里抓失败的测试。

    格式是：
        FAIL: test_add_index (migrations.test_optimizer.OptimizerTests.test_add_index)
        ERROR: test_x (module.Class.test_x)

    用括号里的完整路径，因为它唯一——括号前面那个短名字可能重名。
    """
    names = []
    for line in output.splitlines():
        m = re.match(r"^(?:FAIL|ERROR): (\S+) \((.+)\)\s*$", line)
        if m:
            test_name, where = m.group(1), m.group(2)
            # 两种格式都要处理：
            #   unittest 默认：test_x (module.Class.test_x)  —— 括号里已含方法名
            #   django 用的  ：test_x (module.Class)         —— 括号里只有类，得补上
            if not where.endswith("." + test_name) and where != test_name:
                where = f"{where}.{test_name}"
            names.append(where)
    return names


LIST_FILES_LIMIT = 200


def list_files(workspace):
    """列出工作区里的 .py 文件，最多 LIST_FILES_LIMIT 条。

    必须有上限：django 有 2746 个 py 文件，全列出来是 27k token，
    而且每一步都跟着 history 重发一遍——60 步就是 160 万 token，几块钱。
    真实工具（Cursor 的 glob、grep）都有 limit，这里也一样。

    超了就在最后加一行，告诉模型"还有多少个没显示、换 grep 更省"。
    """
    root = Path(workspace).resolve()
    all_files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if "__pycache__" in f.parts:
            continue
        if f.suffix != ".py":
            continue
        all_files.append(f.relative_to(root).as_posix())

    if len(all_files) <= LIST_FILES_LIMIT:
        return all_files

    shown = all_files[:LIST_FILES_LIMIT]
    shown.append(
        f"...（共 {len(all_files)} 个 .py 文件，只列了前 {LIST_FILES_LIMIT} 个。"
        f"找具体内容请用 grep，别靠这个列表）"
    )
    return shown


def read_file(workspace, path):
    """
    agent用来读文件的函数
    :param workspace:工作区路径，agent 接触不到 tests
    :param path:相对路径，拼在工作区后面
    :return:文本字符串，交给大模型看的
    """
    root = Path(workspace).resolve()
    full = (root / path).resolve()
    # 判断 full 在不在 root 下面，防止 agent 用 ../ 跑出去找到 tests
    if not full.is_relative_to(root):
        return "【错误】：路径越界"
    if not full.is_file():
        return f"【错误】：该文件不存在，可用文件：{'\n'.join(list_files(workspace))}"
    return full.read_text(encoding="utf-8")


def write_file(workspace, path, content):
    """
    agent用来改写文件的函数
    :param workspace:工作区路径，agent 接触不到 tests
    :param path:相对路径
    :param content:改写后的完整文件内容
    :return:文本字符串，说明是否写入成功
    """
    root = Path(workspace).resolve()
    full = (root / path).resolve()
    if not full.is_relative_to(root):
        return "【错误】：路径越界"
    if not full.is_file():
        return f"【错误】：该文件不存在，可用文件：{'\n'.join(list_files(workspace))}"
    full.write_text(content, encoding="utf-8")
    return "写入成功"


def grep(workspace, pattern, path="."):
    """在工作区里搜文本，返回 "文件:行号: 内容"。

    :param pattern:按正则解释；写不成正则就按字面量搜
    :param path:限定在哪个子目录里搜，默认整个工作区
    :return:最多 100 条，超了截断
    """
    ws = Path(workspace).resolve()
    target = (ws / path).resolve()
    if not target.is_relative_to(ws):
        return "【错误】：路径越界"
    try:
        rx = re.compile(pattern)
    except re.error:
        rx = re.compile(re.escape(pattern))

    hits = []
    # path 可以是目录也可以是单个文件。rglob 在文件上会返回空，
    # 所以文件要单独处理——模型经常直接把路径指到某个文件上。
    files = [target] if target.is_file() else sorted(target.rglob("*.py"))
    for f in files:
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{f.relative_to(ws).as_posix()}:{i}: {line.strip()[:160]}")
                if len(hits) >= 100:
                    return "\n".join(hits) + "\n...（超过 100 条，已截断）"
    return "\n".join(hits) if hits else "（没有匹配）"


def run_tests(workspace, tests, python=None, command=None, timeout=None):
    """
    此函数用来检验agent修改后的结果是否正确
    :param workspace:agent工作区的路径
    :param tests:pytest测试的路径，是task原文件下的，agent接触不到
    :param timeout:秒；None 表示用默认的 TIMEOUT_SEC。
                   Django 这类完整判据需要更长时间。
    :return:退出码 + 没通过的测试名

    必须带超时：被测代码可能死循环（比如把 n &= n-1 写成 n ^= n-1），
    没有 timeout 的话 subprocess.run 会永久阻塞，整批跑卡死在这里。
    """
    ws = Path(workspace).resolve()
    env = dict(os.environ)
    py = python or sys.executable

    if command:
        # 自定义命令：给 django 的 tests/runtests.py 这类非 pytest 的入口用。
        # 同时把 workspace 和 workspace/tests 都加进 PYTHONPATH，
        # 因为 runtests.py 需要能 import 到 django 包和测试模块。
        env["PYTHONPATH"] = os.pathsep.join([str(ws), str(ws / "tests")])
        args = [BASH, "-c", command.replace("{python}", py)]
        run_cwd = str(ws)          # 命令要在工作区里跑
        parse = parse_unittest_failed
    else:
        env["PYTHONPATH"] = str(ws)
        # tests 是相对项目根的路径，所以这里不能改 cwd，
        # 一改（比如 cwd=workspace）就变成 workspace/tasks/xxx/tests，找不到。
        args = [py, "-m", "pytest", str(tests), "-q"]
        run_cwd = None
        parse = parse_failed

    try:
        r = subprocess.run(
            args, **({"cwd": run_cwd} if run_cwd else {}), env=env,
            capture_output=True, text=True, timeout=timeout or TIMEOUT_SEC,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "failed_tests": ["<timeout>"]}
    # 故意不返回 output / error。
    # pytest 失败时会把测试源码打出来，形如：
    #     >  assert list(strutils.iter_splitlines(text)) == ['', 'first', ...]
    # 函数名、调用方式、期望值全在里面，等于把答案直接给模型。
    # 真实场景里报 bug 的用户只会说"结果不对"，不会给你测试源码。
    # unittest 把失败信息写到 stderr，pytest 写在 stdout，合起来解析最稳
    return {"exit_code": r.returncode,
            "failed_tests": parse(r.stdout + r.stderr)}
