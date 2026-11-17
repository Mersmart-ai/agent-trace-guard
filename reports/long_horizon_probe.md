# 长程故障注入：规则在长 trace 上还灵不灵

- 日期：2026-11-17
- 成本：0 元，不调用模型
- 脚本：`experiments/long_horizon_probe.py`
- 长程定义：>=10 步的单轮 clean trace

## 1. 数据

来源：

- `data/raw_v1` 里 >=10 步的 `clean_success`
- `data/traces/real` 里 >=10 步的真实 trace

共 9 条长程 source，覆盖：

- `amb_*` 歧义任务
- `term_0001` 终端任务
- `couple_0001`、`req_0001` 多文件任务

多轮任务（`multi_0001`）先跳过。

## 2. 注入的偏离

| 变体 | 做法 |
|---|---|
| `skip_verify` | 删掉最后一次 `run_tests` |
| `skip_final_verify` | 删掉最后一次写之后的所有 `run_tests` |
| `loop_read` | 第一次读重复 4 次 |
| `repeat_write` | 第一次写重复 3 次 |
| `regression` | 写坏、测试红、再修好 |

全部通过 `run_task` 真实执行，0 API。

## 3. 结果

| 变体 | n | 严格规则检出 | Fisher q=0.95 | 中位延迟 | 主要规则 |
|---|---:|---:|---:|---:|---|
| `skip_verify` | 9 | **9/9** | 3/9 | 0 | `unverified_write` |
| `skip_final_verify` | 1 | **1/1** | 0/1 | 0 | `unverified_write` |
| `loop_read` | 9 | **9/9** | 9/9 | 1 | `dup2` |
| `repeat_write` | 1 | **1/1** | 1/1 | 1 | `dup2` |
| `regression` | 0 | - | - | - | 没有可用长程 source |

说明：

- 长程 trace 里 `write_file` 很少，终端任务多用 bash，所以 `repeat_write`/`regression` 样本很少。
- `skip_verify` 最初只有 1/9，因为只看 `no_verify`（整条 trace 一次没测）。
- 新增 `unverified_write`（最后一次写之后没有 `run_tests`）后，长程 `skip_verify` 变成 9/9。

## 4. 新规则

`src/fbs/analysis/monitor.py`：

```
unverified_write：最后一次写之后没有 run_tests
```

- 加入 strict 规则
- 在 56 条 clean_success 上 0 误报
- 在 21 条真实 trace 上 0 误报
- 长程 `skip_verify` 从 1/9 提升到 9/9

## 5. Fisher 对比

- `skip_verify`：规则 9/9，Fisher 只有 3/9
- `loop_read`：两边都是 9/9
- 长程上 Fisher 没有超过规则

## 6. 结论

1. **长程监控在受控故障上成立**
   - 漏验证：`unverified_write` 9/9
   - 打转：`dup2` 9/9
   - 重复写：1/1

2. **长程自然数据仍然太干净**
   - 21 条真实 trace 里只有 4 条触发规则，全部是真实工具错误
   - 没有自然发生的打转/回退/漏验证

3. **下一步要更多“难”的长程任务**
   - 现有任务正常 prompt 下基本都能做对
   - 要高难任务或受控压力测试，才有更多真实异常

## 7. 当前定位

- 规则监控是正式产物
- 长程故障注入证明规则在长 trace 上仍然有效
- Fisher 仍留在实验脚本，作为负结果
