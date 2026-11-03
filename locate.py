"""失败定位：从一条 trace 里算出「最终没过的测试，分别是被哪一步弄坏的」。

输入是一串 test_state（每步一个），由 build_states(history) 得到。
test_state 只有两种取值（见 agent.judge_state）：
    None        —— 这步没测
    [...]       —— 没通过的测试名，[] 表示全过

locate 返回四种东西，互不重叠：
    None            —— 从头到尾一次都没测过（"未验证就提交"）
    {}              —— 测过，而且最终全过
    {"test_a": 4}   —— test_a 是第 4 步被弄坏的
    {"test_a": 0}   —— test_a 在模型动手之前就是红的（基线就坏），
                       0 表示"第 1 步之前"，不是"它弄坏了"

为什么按测试分组，而不是找"最后一次整体翻转"：
    第3步  []
    第4步  ["a"]         a 坏了
    第5步  ["a", "b"]    b 也坏了
    第6步  ["a"]         b 修好了，a 还坏

    只看整体：P → F → F → F，最后那次翻转在"第4步"，
    但"第5步新坏了 b"这件事被吞掉了，而 b 已经修好，本来就不该算。
    按测试分组才能说出：a 是第 4 步坏的，b 不归因（它好了）。

为什么基线就坏要记 0 而不是第一次测的那一步：
    第5步  ["test_average"]                     ← 第一次测，average 已经红了
    test_average 是题目埋的 bug，第 5 步只是"第一次看见它"。
    记成 5 会让人以为第 5 步把好的改坏了，去查一个可能根本没碰它的步骤。
"""


def build_states(history):
    """把每步的 test_state 按顺序取出来，下标 = 步号 - 1。"""
    return [h["test_state"] for h in history]#这里的返回值赋给states作为render和locate的输入


def render(states):
    """一行看全：. 这步没测 / P 全过 / F 有没过。

    只在显示的时候压成 P/F，数据本身不压——压了就丢"坏了几条"的信息。
    """
    out = []
    for s in states:
        if s is None:
            out.append(".")
        elif not s:
            out.append("P")
        else:
            out.append("F")
    return "".join(out)


def locate(states):
    """返回 {测试名: 步号}，详见模块开头。"""
    # 第一步：最终还剩谁没过 —— 从后往前找最后一个测过的格子
    final = None
    for s in reversed(states):
        if s is not None:
            final = set(s)
            break

    if final is None:
        return None          # 一次都没测过
    if not final:
        return {}            # 全过了

    # 第二步：对每条最终失败的测试，单独扫一遍，
    # 记它"最后一次从不在名单里变成在名单里"的位置
    result = {}
    for name in final:
        prev_in = None       # None=还不知道 / False=不在 / True=在
        for i, s in enumerate(states):
            if s is None:
                continue
            cur_in = name in s
            if cur_in and prev_in is None:
                result[name] = 0         # 第一次测就坏 → 基线
            elif cur_in and prev_in is False:
                result[name] = i + 1     # 之前不在，现在在 → 这步弄坏的
            prev_in = cur_in

    return result
