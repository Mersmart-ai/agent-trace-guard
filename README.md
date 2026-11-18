# first-bad-step

Process-conformance monitoring for coding agents.

> 当前状态：**pilot / rules-only + dsh 集成**。统计模型（Fisher）没有证明稳定的
> 增量价值，正式监控器采用可解释的过程规则；已把监控和 turn-stopping 干预接到
> DeepSeek Harness。小任务上干预不改变结果；描述不全的 boltons 探针有 1 个
> 正结果（单 seed）；同一 Django 长任务上 dsh 43 步完成，自研 harness
> 30/60 步失败。实验与负结果见 `reports/`。

## 这是什么

- 一个 agent harness：让模型在隔离工作区里读/改代码、跑测试，并记录每一步。
- 一个数据审计层：从 trace 里标出健康成功、环境异常、失败和作弊样本。
- 一个规则监控器：判断过程偏离（不验证、回退、打转、工具错误、盲写）。

**当前不做**：不再扩展"哪一步弄坏了"的失败归因；`src/fbs/legacy/` 只是标签工具。

## 目录

```
src/fbs/
├── cli.py              # 入口（python run.py 或 fbs 命令）
├── actions.py          # is_write / tool_kind
├── llm.py              # DeepSeek / DashScope 客户端
├── agent/              # loop / policy / tools / judge
├── data/               # trace 落盘 / audit 标签
├── analysis/           # features.py / monitor.py（规则监控）
└── legacy/             # locate / classify / report（标签与旧报告）

tests/                  # 项目单测（不跑 tasks/ 里的题目）
data/raw_v1/            # 冻结的 80 条旧 trace + manifest.csv
data/labels/            # audit 输出的健康标签
data/traces/            # 新 trace（gitignored）
tasks/                  # 题库
docs/                   # 预注册、日志、文献
scripts/                # 开发脚本
integrations/           # dsh 插件：observe / turn-stopping guard
experiments/            # 零成本实验、dsh_adapter.py
```

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env        # Windows: Copy-Item .env.example .env
# 在 .env 里填 DEEPSEEK_API_KEY（或 DASHSCOPE_API_KEY）

pytest -q
python -m fbs.data.audit \
  --traces data/raw_v1/run_traces \
  --out-csv data/labels/healthy.csv
```

运行任务会调用模型、产生费用：

```bash
python run.py
```

`FBS_ONLY=tasks/task_0001 python run.py` 只跑一个任务；`FBS_ONLY=all`
跑全部；不设置时跑默认的 6 个歧义任务（避免误跑全部花钱）。

## 规则监控

```python
from fbs.analysis.monitor import rule_alarms, strict_alarms

alarms = rule_alarms(trace["steps"])
# [{"rule": "delta", "step": 5, "detail": "new_red=test_x"}, ...]
```

- **strict**：`no_verify / delta / dup2 / error / long_gap / unverified_write`
- **full**：strict + `blind`
- 最终评估：`reports/final_eval.md`
- Fisher 负结果：`reports/fisher_value.md`
- 长程故障注入：`reports/long_horizon_probe.md`

## dsh 集成

把监控层接到 DeepSeek Harness（dsh），不依赖本项目较弱的 harness：

- `experiments/dsh_adapter.py`：把 dsh 的 JSONL 事件映射成我们的 step history；
- `integrations/dsh-monitor/`：observe-only 插件，只写事件日志，不改变行为；
- `integrations/dsh-intervene/`：turn-stopping guard；`shadow` 只记录，
  `guard` 在 agent 想结束时检查“最后一次写之后有没有测试”，没有就 steer；
- 结果与缺口：`reports/dsh_integration_status.md`；
- 描述不全的 boltons 探针（第一例正结果）：
  `reports/dsh_intervention_probe.md`；
- 同一 Django 长任务（2746 个文件）：自研 harness 30/60 步失败，
  dsh 43 步、2 次写、**217/217 通过**；见 `reports/dsh_django_probe.md`。

## 数据

- `data/raw_v1/`：冻结的 80 条旧 trace，不回写；`manifest.csv` 记录 SHA256。
- `data/labels/healthy.csv`：`audit` 输出，一行一条 trace，含 `healthy_class` / `valid_env` / `env_invalid_reason`。
- `data/traces/`：新 trace 写这里；不进 Git。
- `runs/`：工作区副本，运行时自动重建。

## 当前进度

- [x] harness（loop / tools / policy / judge / trace）
- [x] trace 审计与环境异常标记
- [x] workspace 每次运行前清理
- [x] 正常轨迹特征（`analysis/features.py`）
- [x] 规则监控（`analysis/monitor.py`）
- [ ] 正常模型 + conformal（Fisher 未证明增量价值，暂不进入主线）
- [x] 长程运行时干预：dsh turn-stopping（单 seed 正结果，见 `reports/dsh_intervention_probe.md`）
- [x] 同一 Django 长任务的运行时对照（dsh 43 步完成，自研 30/60 步失败）
- [ ] Django 上的 `shadow` vs `guard` A/B
- [ ] 自然长任务的 2–3 seed 复现
- [ ] 评估与论文/简历材料

## 开源说明

- 代码：MIT，见 [`LICENSE`](LICENSE)。
- 第三方任务（QuixBugs / requests / boltons / Django / Terminal-Bench）：保留原许可证，见 [`THIRD_PARTY.md`](THIRD_PARTY.md)。发布前请核对每个来源的 license。
- 不要把 `.env`、模型 key 或未脱敏的私人日志提交到仓库。

## License

MIT
