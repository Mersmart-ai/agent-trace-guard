"""判断一步动作是"读"还是"写"。

单独一个模块，因为 report（出报告）和 classify（归因分类）都要用，
放其中任何一个里都会循环导入。

为什么需要它：
    只数 write_file 会把 "echo 'x' > a.py" 当成没动手。
    django 那两条 trace 里，bash 全只读，所以那次判断碰巧对了；
    但只要 agent 用重定向改代码，旧逻辑就会误判成 "gave_up"。
"""

import re

# 一出现就算"改了文件系统"的命令
WRITE_CMDS = {
    "mv", "cp", "rm", "touch", "mkdir", "rmdir", "ln", "chmod", "chown",
    "patch", "tee", "dd", "unzip", "zip", "gzip", "gunzip",
}

# 只读命令
READ_CMDS = {
    "cat", "head", "tail", "less", "more", "grep", "rg", "find", "wc",
    "sort", "uniq", "diff", "tree", "file", "stat", "du", "pwd", "ls",
    "echo", "which", "whoami",
}

# 重定向：> 或 >>，但不匹配 2>&1、>=
REDIRECT = re.compile(r"(^|[^\d&])>{1,2}(?!&)")


def segments(cmd):
    """把一条 shell 命令按 | && || ; 切开。"""
    return [s.strip() for s in re.split(r"\|\||&&|[|;]", cmd) if s.strip()]


def is_write(step):
    """这一步有没有改文件系统。

    write_file 算改。
    bash 要看命令：
      · 有重定向（> / >>）就算改
      · 某段第一个词是 mv/cp/rm/... 就算改
      · sed -i 算改（原地编辑）
      · tar -c 算改（生成压缩包）
      · git commit/add/checkout/reset/apply/clean 算改
    """
    tool = step.get("tool")

    if tool == "write_file":
        return True
    if tool != "bash":
        return False

    cmd = (step.get("args") or {}).get("command", "")
    if REDIRECT.search(cmd):
        return True

    for seg in segments(cmd):
        first = seg.split()[0]
        if first in WRITE_CMDS:
            return True
        if first == "sed" and re.search(r"(^|\s)-i", seg):
            return True
        if first == "tar" and re.search(r"(^|\s)-?[a-zA-Z]*c", seg):
            return True
        if first == "git" and re.search(r"\s(commit|add|checkout|reset|apply|clean)\b", seg):
            return True
    return False


def tool_kind(step):
    """这一步属于哪类：navigate / read / write / verify / other。"""
    tool = step.get("tool")
    if tool == "run_tests":
        return "verify"
    if is_write(step):
        return "write"
    if tool in ("list_files", "grep"):
        return "navigate"
    if tool in ("read_file", "bash"):
        return "read"
    return "other"
