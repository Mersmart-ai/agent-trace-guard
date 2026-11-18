# experiments

按用途分组。除 `eval/real_runs.py` 外，这些脚本不调用模型 API。

## calibration/

| 文件 | 用途 |
|---|---|
| `cv_calibration.py` | 固定切分 + 5 折校准，比较 Fisher 与规则 |
| `signal_probe.py` | 正常轨迹特征、经验尾概率、Fisher 打分 |
| `task_split_eval.py` | 任务级切分与分数评估 |
| `operating_point.py` | 不同阈值下的误报/检出工作点 |
| `fisher_value_probe.py` | Fisher 有没有规则之外的增量价值（结论：没有） |

## negatives/

| 文件 | 用途 |
|---|---|
| `scripted_negatives.py` | 脚本化异常：跳过验证、重复读、重复写、回归 |
| `heldout_anomalies.py` | 留出异常：盲写、越界读 |
| `long_horizon_probe.py` | 长程故障注入：漏验证、打转 |
| `intervention_ab.py` | 早期干预 A/B（负结果） |

## eval/

| 文件 | 用途 |
|---|---|
| `final_eval.py` | 归档 trace + 真实 trace 的最终规则评估 |
| `real_runs.py` | 跑真实模型 trace（会调用 API、产生费用） |

## dsh/

| 文件 | 用途 |
|---|---|
| `dsh_adapter.py` | 把 dsh 的 JSONL 事件映射成统一的 step history |

## 其他

- `splits/task_split_v1.json`：冻结的任务切分，不要改。
- `dsh_workspace/`：本地生成的工作区副本，已 gitignore，不进仓库。
