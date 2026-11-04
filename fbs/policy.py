"""给模型看的那一层：系统提示词、工具清单、把 history 拼成对话。

改动这里会直接改变模型的行为，所以和其它模块分开——
出问题时能一眼看出是"模型的问题"还是"工具的问题"。
"""
import json

from fbs.my_llm import call_model

SYSTEM_PROMPT = """你是一个修 bug 的 agent。把给定的代码改对，让测试全部通过。

工作流程（按顺序做）：
1. list_files 看有哪些文件
2. read_file 读有关的文件；不确定某个名字/函数在哪，用 grep 搜
3. 用 write_file 把改好的完整文件写回去
4. run_tests 验证；通过了就 finish，没通过回到第 2 步

只能用 list_files 列出来的路径。只能修改已经存在的文件。
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "列出工作区里所有可读的 .py 文件（相对路径）。任务开始时调用一次即可。",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "读取工作区里一个文件的完整内容。修改代码之前必须先读，不要凭猜测改。",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "相对路径，如 calc.py"}},
            "required": ["path"],
        },
    }},
    {"type": "function", "function": {
        "name": "grep",
        "description": "在工作区里搜文本，返回 文件:行号: 内容。想知道某个函数/变量在哪些地方被用到，用这个，比一个个读文件快得多。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "要搜的文本，按正则解释"},
                "path": {"type": "string", "description": "限定子目录，默认整个工作区"},
            },
            "required": ["pattern"],
        },
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "用新内容整体覆盖工作区里一个已存在的文件。content 必须是修改后的完整文件，不能只写改动的那几行。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "修改后的完整文件内容"},
            },
            "required": ["path", "content"],
        },
    }},
    {"type": "function", "function": {
        "name": "run_tests",
        "description": "运行本任务的测试。改完代码后必须调用，看到通过才能 finish。",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "finish",
        "description": "确认测试全部通过后调用，表示任务完成。",
        "parameters": {"type": "object", "properties": {}},
    }},
]


def model_policy(task_md):
    """方案 A：每轮把 history 拼成一段文字，塞进 user 消息里。"""
    def fn_inner(step, history):
        # 给模型看的那份 history 要剥掉 test_state。
        # 原因：write_file 这一步的 test_state 是 harness 强制判分算出来的，
        #      不是模型自己测的。要是让它看见，它就永远不需要主动 run_tests，
        #      "未验证就提交"这一类就统计不出来了。
        visible = []
        for h in history:
            h2 = dict(h)                    # 复制一份，别动原对象
            h2.pop("test_state", None)      # 删掉这个键；不存在也不报错
            visible.append(h2)
        history_text = json.dumps(visible, ensure_ascii=False)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"任务：\n{task_md}\n\n"
                # 不强调"这是你自己做的"，模型分不清历史是谁的，
                # 会一直 list_files 直到 max_turns
                f"以下是你自己刚才已经执行过的动作和结果：\n{history_text}\n\n"
                f"不要重复执行这些动作，直接做下一个还没做的。"
            )},
        ]
        msg = call_model(messages, tools=TOOLS)
        if not msg.tool_calls:      # 模型这次没调工具，可能只说了句话
            return {"tool": "bad_output", "args": {"raw": (msg.content or "")[:200]}}
        tc = msg.tool_calls[0]
        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        return {"tool": tc.function.name, "args": args}
    return fn_inner


def to_text(x):
    """工具结果转成字符串：list / dict 用 json 表示，模型看得懂。"""
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


def model_policy_structured(task_md):
    """方案 B：把 history 拆成 assistant(我调了什么) + tool(返回了什么) 交替的消息。

    和方案 A 的区别：模型能"认出"那是自己的动作。
    代价：必须关 thinking。否则 API 要求回传 reasoning_content，
    SDK 取不到，多轮会 400。
    """
    convo = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"任务：\n{task_md}"},
    ]
    pending = {"cid": None}  # 上一条 assistant 的 tool_call_id，等 loop 把结果还回来

    def fn_inner(step, history):
        if pending["cid"] and history:
            convo.append({
                "role": "tool",
                "tool_call_id": pending["cid"],
                "content": to_text(history[-1]["result"]),
            })
            pending["cid"] = None

        msg = call_model(convo, tools=TOOLS, thinking_off=True)

        if not msg.tool_calls:
            return {"tool": "bad_output", "args": {"raw": (msg.content or "")[:200]}}

        tc = msg.tool_calls[0]
        cid = f"call_{step}"
        convo.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": cid,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }],
        })
        pending["cid"] = cid

        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        return {"tool": tc.function.name, "args": args}
    return fn_inner
