# data 目录说明

## 布局

```
data/
├── raw_v1/              # 冻结归档（2026-11-13）
│   ├── run_traces/      # 80 条旧 trace，一条运行一个 JSON
│   └── manifest.csv     # 归档清单 + SHA256
├── traces/              # 新跑的 trace（代码写这里；已被 .gitignore）
└── labels/
    └── healthy.csv      # 审计标签（从 raw_v1 生成）
```

## 两个 CSV 分别是什么

### `raw_v1/manifest.csv`

- **来源**：归档 `run_traces/` 时生成
- **一行**：一条 trace 文件
- **列**：`path`, `sha256`, `bytes`, `task`, `run_id`, `ts`, `reason`, `steps`, `final_test_state`
- **用途**：证明归档完整、冻结数据版本；不是模型输入
- **行数**：80

### `labels/healthy.csv`

- **来源**：`python -m fbs.audit --traces data/raw_v1/run_traces ...`
- **一行**：一条 trace
- **列**：`task`, `run_id`, `ts`, `reason`, `steps`, `navigate`, `read`, `write`, `verify`, `other`, `regressions`, `duplicate_rate`, `final_test_state`, `valid_env`, `env_invalid_reason`, `tests_touched`, `missing_test_state_steps`, `healthy_class`, `kind`
- **用途**：给正常轨迹建模挑 `clean_success`；不是原始数据
- **行数**：80

## 生成/复现

```bash
# 审计旧归档，生成健康标签（先 pip install -e .）
python -m fbs.data.audit \
  --traces data/raw_v1/run_traces \
  --out-csv data/labels/healthy.csv

# 如果还没 pip install -e .：
# PYTHONPATH=src python -m fbs.data.audit ...
```

## 不放在 data 里的

- `runs/`：agent 工作区副本，不是 trace；已被 `.gitignore`
- `tasks/`：题目本身
- `docs/`：计划和日志

## 当前约定

- `data/raw_v1/`：**冻结，不改**；旧 80 条 trace 只读
- `data/traces/`：**新运行写这里**；每次跑任务前由 `save_run` 创建
- 旧的根目录 `run_traces/` 已删除；代码里的路径已改为 `data/traces/`
