"""判分：把工具结果翻成"这一步的测试状态"。

和 tools.py 分开，因为这是"解释结果"，不是"操作世界"。
"""

NO_CASE = "<pytest_no_case>"


def judge_state(result):
    """把 run_tests 的结果翻成 test_state。只有两种取值：
        None  —— 这步没测（由 agent_loop 决定，不是这里返回的）
        list  —— 没通过的测试名；[] 表示全过

    exit_code 非 0 却一条 FAILED/ERROR 都没抓到（pytest 自己崩了，或者
    tests/ 里根本没有用例），返回 [NO_CASE] 而不是 []——否则会被误读成"全过"。
    "跑不起来"变成"全部通过"，是最坏的一种静默错误。
    """
    if result.get("exit_code") == 0:
        return []
    failed = result.get("failed_tests", [])
    return failed if failed else [NO_CASE]


def judge_ok(result):
    """判断模型调用工具时是否成功拿到了数据。

    :param result:read_file / write_file 之类的返回值，可能是字符串也可能 是别的
    :return:布尔值，赋给 history 里的 ok
    """
    if isinstance(result, str):
        return not result.startswith("【错误】")
    return True
