import os,subprocess, sys
from pathlib import Path
import shutil
import json
from datetime import datetime
from my_llm import call_model
from locate import build_states, locate, render


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


def run_tests(workspace,tests):
    """
    此函数用来检验agent修改后的结果是否正确
    :param workspace:agent工作区的路径
    :param tests:pytest测试的路径，是task原文件下的，agent接触不到
    :return:返回退出码，也就是pytest的结果的退出码，不是0就说明出错
    """
    env = dict(os.environ)
    env["PYTHONPATH"]=str(Path(workspace).resolve())#相对路径变为绝对路径再化为字符串
    r = subprocess.run(  # subprocess.run启动另一个进程pytest
        [sys.executable, "-m", "pytest", str(tests), "-q"],
        env=env, capture_output=True, text=True,  # 把刚刚的env赋给env，捕获子进程打印的东西，以文本格式输出。
    )
    return {"exit_code":r.returncode,"output":r.stdout,"error":r.stderr,
            "failed_tests":parse_failed(r.stdout)}
def prepare_workspace(task_dir, run_dir):
    """
    用来复制原来的文件生成副本作为agent工作区，准备工作
    :param task_dir:要复制的任务路径位置
    :param run_dir: 要生成的副本路径位置
    :return:返回工作区的路径也就是workspace
    """
    if not os.path.isdir(task_dir):
        return None#原路径文件不存在或不是目录
    # 如果有src文件将该task+src作为路径赋给src，src作为要复制的任务路径，不会碰到tests
    src = task_dir / "src"
    #如果源路径文件存在且是目录，检验是否有src文件
    if src.is_dir():
        #将要生成的副本路径变为run_dir+workspace
        dst=run_dir / "workspace"
        #复制一整个src下面的文件树，复制到dst，如果dst已经存在就覆盖
        shutil.copytree(src, dst,dirs_exist_ok=True)
        #返回的是dst，用于后续的pytest
        return dst
    else:
        return None
def read_file(workspace,path):
    """
    agent用来读文件的函数
    :param workspace:在自己的工作区里面读，接触不到tests，并且该参数是工作区路径
    :param path:相对路径，用来找到具体的模块来读，需要拼接在work space后面
    :return:文本字符串，交给大模型看的，大模型读不了文件，只能读文本
    """
    root = Path(workspace).resolve()#workspace路径解析
    full = (root / path).resolve()#解析后的workspace与path拼接后再整体解析
    if not full.is_relative_to(root):#判断full在不在root这个目录下，防止agent写多个..回到根目录找到tests
        return "【错误】：路径越界"
    if not full.is_file():#如果模型返回的path不是list_files里面的就会被这里截住返回给模型
        return f"【错误】：该文件不存在，可用文件：{'\n'.join(list_files(workspace))}"
    #如果走到这里说明安全，之后可以开始读取文件
    return full.read_text(encoding="utf-8")
def write_file(workspace,path,content):
    """
    agent用来改写文件的函数
    :param workspace:工作区里进行改写接触不到tests，并且该参数是工作区路径
    :param path:相对路径，用来找到具体的模块来读，需要拼接在work space后面
    :param content:改写的内容
    :return:文本字符串，反应是否写入成功
    """
    root = Path(workspace).resolve()
    full = (root / path).resolve()
    if not full.is_relative_to(root):
        return "【错误】：路径越界"
    if not full.is_file():#如果模型返回的path不是list_files里面的就会被这里截住返回给模型
        return f"【错误】：该文件不存在，可用文件：{'\n'.join(list_files(workspace))}"
    #走到这里说明安全
    full.write_text(content,encoding="utf-8")
    return "写入成功"
#下面将上面的函数写成循环自动调用
def run_agent():
    """
    此函数用于启动agent循环执行任务
    """
    results={}
    for task in sorted(Path("tasks").iterdir()):
        workspace=prepare_workspace(task,Path('runs')/task.name)
        if workspace is None:
            continue
        #workspace是具体task的目录，下面要让agent读里面所有的具体文件,但是一次只能读一个
        root=Path(workspace).resolve()
        for f in sorted(root.rglob("*")):
            if not f.is_file():#f是不是一个文件
                continue
            #__pycache__ 是 Python 自动生成的字节码缓存目录。每次 import calc，Python 都会把编译后的结果存成 .pyc 放在里面，下次导入更快。
            if "__pycache__" in f.parts:#parts是Path对象的一个属性，返回一个元组，他将路径切成每一片作为元组的元素
                continue
            if f.suffix != ".py":#如果文件的后缀名不是.py就跳过
                continue
            #走到这里的文件满足agent要操作的文件
            rel=f.relative_to(root)#只要文件路径的workspace里面文件的路径，方便传入参数给prepare_workspace
            content = read_file(workspace,rel)
            content = content.replace("\r","")
            #接下来开始写文件，一次只能写读的这一个
            write_file(workspace,rel,content)#这里的content应该是模型返回的东西
        results[task.name]=run_tests(workspace, Path(task / 'tests'))#将这个任务的退出码返回到result里，key是这个任务名，value是这个任务的退出码
    print(results)
    #只要返回码里面有一个没通过，就以1退出，如果全部测试都通过就以0通过
    if any(code != 0 for code in results.get("exit_code").values()):
        sys.exit(1)
    sys.exit(0)
#接下来要写policy，由于模型的操作顺序不是固定的，模型可能会重复修改，所以要由policy决定下一步模型的动作，依据是当前的状态
def fixed_policy(step, history):
    """
    假大脑，不会用到
    该函数根据step返回下一步要做的动作,0表示读文件，1表示写文件，2表示运行，3及以上表示结束
    :param step:靠step知道模型用来返回哪个动作
    :param history:
    :return:返回的是一个字典，里面表示了要调用的工具和要输入的参数
    """
    if step == 0:
        return {"tool": "read_file", "args": {"path": "calc.py"}}
    if step == 1:
        content = history[0]["result"]
        fixed = content.replace("old","new")
        return {"tool": "write_file", "args": {"path": "calc.py", "content": fixed}}
    if step == 2:
        return {"tool": "run_tests", "args": {}}
    return {"tool": "finish", "args": {}}
#系统提示词
SYSTEM_PROMPT = """你是一个修 bug 的 agent。把给定的代码改对，让测试全部通过。

工作流程（按顺序做）：
1. list_files 看有哪些文件
2. read_file 读有关的文件
3. 用 write_file 把改好的完整文件写回去
4. run_tests 验证；通过了就 finish，没通过回到第 2 步

只能用 list_files 列出来的路径。只能修改已经存在的文件。
"""

#这里是要交给API的TOOLS
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
#模型的model_policy，为了解决不同task.md需要同步到相应的任务中，使用闭包的方式
def model_policy(task_md):
    def fn_inner(step, history):
        # 给模型看的那份 history 要剥掉 test_state。
        # 原因：write_file 这一步的 test_state 是 harness 强制判分算出来的，
        #      不是模型自己测的。要是让它看见，它就永远不需要主动 run_tests，
        #      "未验证就提交"这一类就统计不出来了。
        # 模型自己调 run_tests 的那一步不受影响——测试结果在 result 里，照样看得到。
        visible = []
        for h in history:
            h2 = dict(h)                    # 复制一份，别动原对象
            h2.pop("test_state", None)      # 删掉这个键；不存在也不报错
            visible.append(h2)
        history_text = json.dumps(visible, ensure_ascii=False)
        #模型只能读文本，所以输入给模型的消息和模型输出的消息全是字符串，也就是content中必须是字符串
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"任务：\n{task_md}\n\n"
                #发现如果没有下面这两个提醒模型分不清历史是自己做的还是用户做的，导致一直list_files达到max_turns
                f"以下是你自己刚才已经执行过的动作和结果：\n{history_text}\n\n"
                f"不要重复执行这些动作，直接做下一个还没做的。"
            )},
        ]
        #多传入进来一个tools，是为了让模型的回答格式让API方去规范他，额外写一个TOOLS规范
        msg = call_model(messages, tools=TOOLS)
        if not msg.tool_calls:#模型这次没调用工具，可能只是输出了句话
            return {"tool": "bad_output", "args": {"raw": (msg.content or "")[:200]}}
        tc = msg.tool_calls[0]#msg是一个对象，tc是一个字典，键是function，value有name、arguments
        args = json.loads(tc.function.arguments) if tc.function.arguments else {}#arguments对应path相对路径，如果没有，输出空字典
        return {"tool": tc.function.name, "args": args}
    return fn_inner


def to_text(x):
    """工具结果转成字符串：list / dict 用 json 表示，模型看得懂。"""
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


# ===== 方案 B：标准 assistant / tool 对话 =====
# 和 model_policy 的区别：
#   model_policy        —— 每轮把 history 拼成一段文字，塞进 user 消息里
#   model_policy_structured —— 把 history 拆成 assistant(我调了什么) + tool(返回了什么)
#                              交替的消息，模型能"认出"那是自己的动作
#
# 代价：必须关 thinking。否则 API 要求回传 reasoning_content，SDK 取不到，多轮会 400。
# 用法：__main__ 里把 policy 换成 model_policy_structured(task_md) 即可，agent_loop 不用改。
def model_policy_structured(task_md):
    convo = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"任务：\n{task_md}"},
    ]
    pending = {"cid": None}  # 上一条 assistant 的 tool_call_id，等 loop 把结果还回来

    def fn_inner(step, history):
        # 上一轮的 assistant 已经发出去了，这里把它对应的工具结果补进对话
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

#补一个工具list_files用来让模型知道相对路径有哪些
def list_files(workspace):
    root = Path(workspace).resolve()
    out=[]
    for f in sorted(root.rglob("*")):
        if not f.is_file():  # f是不是一个文件
            continue
        # __pycache__ 是 Python 自动生成的字节码缓存目录。每次 import calc，Python 都会把编译后的结果存成 .pyc 放在里面，下次导入更快。
        if "__pycache__" in f.parts:  # parts是Path对象的一个属性，返回一个元组，他将路径切成每一片作为元组的元素
            continue
        if f.suffix != ".py":  # 如果文件的后缀名不是.py就跳过
            continue
        # 走到这里的文件满足agent要操作的文件
        rel = f.relative_to(root).as_posix()  # 只要文件路径的workspace里面文件的路径，方便传入参数给prepare_workspace
        out.append(rel)
    return out
#补一个方法用于格式化history便于后续的统计
def make_step(step,tool,args,result,ok=True,test_state=None):
    """
    此方法用于便于格式化history，记录每次大模型调用工具的轮次、工具、参数、结果、是否正常调用工具以及测试结果是否通过
    :param step:轮次
    :param tool:本次所选择调用的工具
    :param args:所选择工具后填入的参数:即选择查看的具体模块的相对路径
    :param result:本次调用工具所产生的具体结果，用于返回给模型便于下一轮思考
    :param ok:本次调用工具是否成功拿到数据，布尔值
    :param test_state:本次的测试结果如何（只有调用run_tests时才有意义）
    :return:可以解析成json的数据格式
    """
    return {
        "step": step,
        "tool": tool,
        "args": args,
        "result": result,
        "ok": ok,
        "test_state": test_state,
    }
NO_CASE = "<pytest_no_case>"


def judge_state(result):
    """把 run_tests 的结果翻成 test_state。只有两种取值：
        None  —— 这步没测（由 agent_loop 决定，不是这里返回的）
        list  —— 没通过的测试名；[] 表示全过

    以前这里会返回 "error" 字符串表示"导入失败"，导致 test_state 一会儿是字符串
    一会儿是列表，下游每处都要先判断类型。现在统一成列表。

    exit_code 非 0 却一条 FAILED/ERROR 都没抓到（pytest 自己崩了，或者
    tests/ 里根本没有用例），返回 [NO_CASE] 而不是 []——否则会被误读成"全过"。
    "跑不起来"变成"全部通过"，是最坏的一种静默错误。
    """
    if result.get("exit_code") == 0:
        return []
    failed = result.get("failed_tests", [])
    return failed if failed else [NO_CASE]
def judge_ok(result):
    """判断模型调用工具时是否成功接收了数据，return的结果要赋给ok，这里的result输入是read_file和write_file运行的结果"""
    if isinstance(result,str):
        if result.startswith('【错误】'):
            return False
        return True
    return True
#下面写agent循环
def agent_loop(workspace,tests,policy):
    """
    该函数是agent的循环核心
    :param workspace:agent的工作区路径
    :param tests:所要进行的测试，agent看不到
    :return:返回的是history用于下一步交付给model_policy，然后再传入模型
    """
    history = []
    for step in range(1,21):
        action = {}#如果model_policy接不住异常，让action起码有值后面异常会被接住
        try:
            action = policy(step, history)
            if action["tool"] == "finish":
                history.append(make_step(step,action["tool"],action["args"],"right_finish"))
                break
            test_state = None
            if action["tool"] == "list_files":
                result = list_files(workspace)
            elif action["tool"] == "read_file":
                result = read_file(workspace, action["args"]["path"])
            elif action["tool"] == "write_file":
                result = write_file(workspace, action["args"]["path"], action["args"]["content"])
                # 强制判分：写完由循环自动测一次，状态记在这一步上。
                # 注意 result 仍然是"写入成功"，模型看不到这次测试的结果——
                # 这样它自己调 run_tests 的记录还留着，可以统计"它有没有主动验证"。
                test_state = judge_state(run_tests(workspace, tests))
            elif action["tool"] == "run_tests":
                result = run_tests(workspace, tests)
                test_state = judge_state(result)
            else:
                result = f"【错误】：未知工具{action['tool']}"
            ok = judge_ok(result)
            history.append(make_step(step,action["tool"],action["args"],result,ok,test_state))
        except Exception as e:
            result=f"【错误】：{e}"
            history.append(make_step(step,action.get("tool"),action.get("args") or {},result,False))
    if history[-1]['tool'] == "finish":
        reason="right exit"
    else:
        reason="Hit max_turns"
    return history,reason
def save_run(task_name,history,reason):
    """
    每一次的运行结果记录在相应的task内，与workspace平级
    :param task_name:这次任务的名
    :param history:这次任务运行的history
    :param reason:这次任务结束的原因
    :return:返回一个编号run_id
    """
    folder = Path("run_traces") / task_name  # ← 多了 / task_name
    folder.mkdir(parents=True, exist_ok=True)  # ← 现在真要 parents 了

    nums = []
    for p in folder.glob("r*.json"):
        nums.append(int(p.stem[1:]))  # "r01" → 1

    if len(nums) == 0:
        n = 1
    else:
        n = max(nums) + 1

    path = folder / f"r{n:02d}.json"
    run_id = f"{task_name}_r{n:02d}"  # 全局唯一的名字

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
    return [h["step"] for h in history
            if h["tool"] == "write_file" and h["test_state"] is None]


if __name__ == "__main__":
    # workspace = prepare_workspace(Path("tasks/task_0003"), Path("runs/task_0003"))
    # policy=model_policy(Path("tasks/task_0003/task.md").read_text(encoding="utf-8"))
    # history,f_reason = agent_loop(workspace, Path("tasks/task_0003/tests"),policy)
    # print(history)
    # print(f_reason)
    for task in sorted(Path("tasks").iterdir()):
        if not (task / "src").is_dir():
            continue
        # 没有测试文件的 task 是"题目配错了"，不该产出一条 trace。
        # 让脏数据进 trace，比不跑更糟——以后分析时会把"没测"当成"通过了"。
        if not list((task / "tests").glob("test_*.py")):
            print(f"⚠️  {task.name}: tests/ 里没有 test_*.py，跳过")
            continue
        workspace=prepare_workspace(task,Path('runs')/task.name)
        task_md=(task / "task.md").read_text(encoding="utf-8")
        if workspace is None:
            continue
        policy=model_policy(task_md)   # 换回方案 A 就改成 model_policy(task_md)；方案B改成model_policy_structured
        history,f_reason = agent_loop(workspace, task / 'tests',policy)

        bad = check_trace(history)
        if bad:
            print(f"⚠️  {task.name}: 第 {bad} 步写了文件却没有测试状态，强制判分可能没生效")

        run_id = save_run(task.name, history, f_reason)
        print(f"[saved] {run_id}  {f_reason}  {len(history)} 步")

        # 归因：先把每步的测试状态摊成一串，再分别看形状和结论
        states = build_states(history)
        print(f"  {render(states)}  ->  {locate(states)}")

