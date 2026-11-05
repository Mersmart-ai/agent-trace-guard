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


def _state(x):
    """兼容两种输入：dict（含 test_state + judge）或裸的 list。"""
    return x.get("test_state") if isinstance(x, dict) else x


def build_states(history):
    """每步取出 test_state 和它用的是哪套判据。

    返回 dict 而不是裸列表，是因为多轮任务里判据会换：
    不记 judge 的话，"换了一套判据"会被误当成"某条测试变红"。
    """
    return [{"test_state": h.get("test_state"), "judge": h.get("judge")} for h in history]


def render(states):
    """一行看全：. 这步没测 / P 全过 / F 有没过。

    只在显示的时候压成 P/F，数据本身不压——压了就丢"坏了几条"的信息。
    """
    out = []
    for s in states:
        s = _state(s)
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
        v = _state(s)
        if v is not None:
            final = set(v)
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
            v = _state(s)
            if v is None:
                continue
            cur_in = name in v
            if cur_in and prev_in is None:
                result[name] = 0         # 第一次测就坏 → 基线
            elif cur_in and prev_in is False:
                result[name] = i + 1     # 之前不在，现在在 → 这步弄坏的
            prev_in = cur_in

    return result


def regressions(states):
    """找所有「本来没红、这一步变红」的位置。

    和 locate 的区别：
        locate       只看最终状态。最终全绿就返回 {}，中间翻车一概不管。
        regressions  看过程。只要某条测试从「不在名单里」变成「在名单里」，
                     就记一步——不管它后来修没修好。

    为什么要这个：agent 会反复改，通常最后能改到全绿。
    这时候 locate 永远是 {}，但它过程中可能把原本好的东西弄坏了又修回来。
    那种「弄坏了又修好」的代价，只有 regressions 看得到。

    :return: {步号: [测试名, ...]}，只记新变红的那些
    """
    out = {}
    prev = None      # 上一步的失败集合；None 表示还没测过
    prev_judge = None
    for i, h in enumerate(states, 1):
        if isinstance(h, dict):
            s, judge = h.get("test_state"), h.get("judge")
        else:
            s, judge = h, None

        if s is None:
            continue

        cur = set(s)
        # 判据换了一套（多轮任务），"新出现的红"不代表是这一步弄坏的，
        # 只是这套判据里本来就有这条测试。此时重置基线。
        if prev is None or judge != prev_judge:
            prev = cur
            prev_judge = judge
            continue

        new_red = cur - prev
        if new_red:
            out[i] = sorted(new_red)
        prev = cur
    return out
