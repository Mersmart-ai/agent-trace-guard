# 最小干预 A/B：强制验证 vs 影子

- 日期：2026-11-15
- 模型：`deepseek-flash`
- 成本：约 15 万 token，预计 1–2 元
- 脚本：`experiments/negatives/intervention_ab.py`
- trace：`data/traces/intervention/`（不进 Git）

## 1. 设计

触发条件（模型想 `finish` 时）：

- 整条 trace 一次 `run_tests` 都没调（`no_verify`）
- 或最后一次测试状态是红的（`final_red`）

两个 arm：

| arm | 行为 |
|---|---|
| `guardrail` | 不执行 finish，改为执行一次 `run_tests` |
| `shadow` | 只记录，不改变模型行为 |

任务：`task_0001`、`task_0004`、`task_0005`、`couple_0001`
每任务各跑一次 guardrail 和 shadow，共 8 条。

## 2. 第一轮：speed prompt（没有触发）

prompt 只是“尽量少测”，模型仍然主动测了。

| arm | 成功 | 触发 | 平均步数 |
|---|---:|---:|---:|
| guardrail | 4/4 | 0 | 6.8 |
| shadow | 4/4 | 0 | 7.0 |

没有触发，无法比较干预效果。

## 3. 第二轮：no_tests prompt（全部触发）

prompt 明确禁止调用 `run_tests`。

| arm | 成功 | 触发 | 平均步数 |
|---|---:|---:|---:|
| guardrail | 4/4 | 4 | **9.0** |
| shadow | 4/4 | 4 | **6.8** |

- 触发机制正确：8 条全部识别出 `no_verify`
- guardrail 确实强制执行了 `run_tests`
- **但成功率没有区别：两边都是 4/4**
- guardrail 平均多 2.2 步

## 4. 为什么没有效果

因为 harness 在每次写之后**强制判分**：

```
write_file → harness 自动 run_tests → test_state 记录
```

所以模型即使不主动 `run_tests`，代码仍然被验证过。
在这个 harness 里，“跳过验证”不会导致错误代码被提交。

结果是：

- 干预改变了过程（多了一次测试）
- 但没有改变结果
- 只增加了步数

## 5. 这说明了什么

1. **`no_verify` 不是结果相关的偏离**
   在这个 harness 下，跳过主动验证不会伤害正确性。

2. **干预要针对真正影响结果的偏离**
   - 打转/重复（浪费步数）
   - 盲写（写错文件/写坏）
   - 工具错误后不恢复
   - 隐藏测试/多轮任务里漏验证

3. **规则层仍然有效**
   规则能识别这些过程偏离；问题在于干预的价值需要选对目标。

## 6. 下一步候选

### A. 错误恢复提醒

bad prompt 曾让模型猜错路径（`src/calc.py`）。
触发 `error` 时，提醒“先 list_files 看可用文件”。
测量：错误次数、步数、成功率。

### B. 打转/重复提醒

触发 `dup2` 时，提醒“换一个方法，不要重复同一动作”。
需要一个能稳定产生打转的任务/prompt。

### C. 隐藏测试/多轮任务

在 `multi_0001`、`couple_0001` 这类任务里，主动验证可能影响隐藏测试。
需要支持多轮 A/B。

## 7. 结论

这次干预是**负结果**：

- 机制正确
- 触发正确
- 但没有成功率收益
- 原因是 harness 的强制判分掩盖了“跳过验证”的后果

项目仍然可以作为“过程监控 + 规则” artifact；
但“干预提高成功率”目前没有证据。
