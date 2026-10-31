import os,subprocess, sys
from pathlib import Path
import shutil
import json
from my_llm import call_model
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
    print(r.stdout)
    return {"exit_code":r.returncode,"output":r.stdout,"error":r.stderr}
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
        history_text = json.dumps(history, ensure_ascii=False)
        #模型只能读文本，所以输入给模型的消息和模型输出的消息全是字符串，也就是content中必须是字符串
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"任务：\n{task_md}\n\n"
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
def judge_state(result):
    """判断pytest的结果的状态，return的结果要赋给test_state,这里的result输入是run_tests运行的结果"""
    if result.get('exit_code')==0:
        return 'pass'
    if result.get('exit_code')==1:
        return 'fail'
    return 'error'
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
    for step in range(1,11):
        action = {}#如果model_policy接不住异常，让action起码有值后面异常会被接住
        try:
            action = policy(step, history)
            if action["tool"] == "finish":
                history.append(make_step(step,action["tool"],action["args"],"right_finish"))
                break
            if action["tool"] == "list_files":
                result = list_files(workspace)
            elif action["tool"] == "read_file":
                result = read_file(workspace, action["args"]["path"])
            elif action["tool"] == "write_file":
                result = write_file(workspace, action["args"]["path"], action["args"]["content"])
            elif action["tool"] == "run_tests":
                result = run_tests(workspace, tests)
            else:
                result = f"【错误】：未知工具{action['tool']}"
            ok = judge_ok(result)
            test_state = judge_state(result) if action["tool"] == "run_tests" else None
            history.append(make_step(step,action["tool"],action["args"],result,ok,test_state))
        except Exception as e:
            result=f"【错误】：{e}"
            history.append(make_step(step,action.get("tool"),action.get("args") or {},result,False))
    if history[-1]['tool'] == "finish":
        reason="right exit"
    else:
        reason="Hit max_turns"
    return history,reason

if __name__ == "__main__":
    # workspace = prepare_workspace(Path("tasks/task_0003"), Path("runs/task_0003"))
    # policy=model_policy(Path("tasks/task_0003/task.md").read_text(encoding="utf-8"))
    # history,f_reason = agent_loop(workspace, Path("tasks/task_0003/tests"),policy)
    # print(history)
    # print(f_reason)
    for task in sorted(Path("tasks").iterdir()):
        if not (task / "src").is_dir():
            continue
        workspace=prepare_workspace(task,Path('runs')/task.name)
        task_md=(task / "task.md").read_text(encoding="utf-8")
        if workspace is None:
            continue
        policy=model_policy(task_md)
        history,f_reason = agent_loop(workspace, task / 'tests',policy)
        print(history)
        print(type(history))
        print(f_reason)

