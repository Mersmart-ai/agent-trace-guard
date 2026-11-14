# first-bad-step

Positive-only normal-trace monitoring and long-horizon error control for coding agents.

> 当前状态：**pilot**。主线已从"失败归因"转为"正常轨迹分布 + 长程错误控制"。
> 旧的归因方案文档已删除，当前计划见 [`docs/prereg.md`](docs/prereg.md)。

## 这是什么

- 一个 agent harness：让模型在隔离工作区里读/改代码、跑测试，并记录每一步。
- 一个数据审计层：从 trace 里标出健康成功、环境异常、失败和作弊样本。
- 下一阶段：只用健康成功轨迹建模"正常过程"，用 conformal/序贯方法控制误报率，并在长程任务里做检测和干预。

**当前不做**：不再扩展"哪一步弄坏了"的失败归因；`src/fbs/legacy/` 只是标签工具。

## 目录

```
src/fbs/
├── cli.py              # 入口（python run.py 或 fbs 命令）
├── actions.py          # is_write / tool_kind
├── llm.py              # DeepSeek / DashScope 客户端
├── agent/              # loop / policy / tools / judge
├── data/               # trace 落盘 / audit 标签
├── analysis/           # 评测分析（features/normal/... 待建）
└── legacy/             # locate / classify / report（标签与旧报告）

tests/                  # 项目单测（不跑 tasks/ 里的题目）
data/raw_v1/            # 冻结的 80 条旧 trace + manifest.csv
data/labels/            # audit 输出的健康标签
data/traces/            # 新 trace（gitignored）
tasks/                  # 题库
docs/                   # 预注册、日志、文献
scripts/                # 开发脚本
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

`ONLY` 在 `src/fbs/cli.py` 里，用于单任务调试。

## 数据

- `data/raw_v1/`：冻结的 80 条旧 trace，不回写；`manifest.csv` 记录 SHA256。
- `data/labels/healthy.csv`：`audit` 输出，一行一条 trace，含 `healthy_class` / `valid_env` / `env_invalid_reason`。
- `data/traces/`：新 trace 写这里；不进 Git。
- `runs/`：工作区副本，运行时自动重建。

## 当前进度

- [x] harness（loop / tools / policy / judge / trace）
- [x] trace 审计与环境异常标记
- [x] workspace 每次运行前清理
- [ ] 正常轨迹特征（`analysis/features.py`）
- [ ] 正常模型 + conformal 序贯检测
- [ ] 长程运行时干预
- [ ] 评估与论文/简历材料

## 开源说明

- 代码：MIT，见 [`LICENSE`](LICENSE)。
- 第三方任务（QuixBugs / requests / boltons / Django / Terminal-Bench）：保留原许可证，见 [`THIRD_PARTY.md`](THIRD_PARTY.md)。发布前请核对每个来源的 license。
- 不要把 `.env`、模型 key 或未脱敏的私人日志提交到仓库。

## License

MIT
