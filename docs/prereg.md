# 预注册：正常轨迹分布与长程错误控制

- 日期：2026-11-13
- 数据快照：`data/raw_v1/`（80 条 trace，SHA256 见 `data/raw_v1/manifest.csv`）
- 版本：v1（在任何新模型/新检测器实验之前冻结）
- 状态：300 元简历/开源版 pilot 预注册；默认用现有 80 条 + 20–30 条新跑，SWE-bench/Terminal-Bench 为 stretch

> **2026-11-18 方向说明**：Fisher/conformal 未证明稳定的增量价值，主线已改为
> “规则过程监控 + 拒绝结束式干预（dsh turn-stopping）”。本文件保留为历史预注册，
> 不再按 RQ1/RQ2 的 one-class 路线执行；最新结果见 `reports/final_eval.md`、
> `reports/fisher_value.md`、`reports/dsh_intervention_probe.md`。

## 1. 研究问题

- **RQ1**：只用健康成功（`clean_success`）轨迹，低维正常模型能否区分正常成功 / 异常成功 / 失败？
- **RQ2**：序贯 conformal + alpha-spending 能否把整条轨迹的误报率控制在给定 α 内？检测延迟多大？
- **RQ3**：检测触发的运行时干预能否改善长程任务的成功率或成本？
- **RQ4**：结果对任务类型、轨迹长度、`test_state` 信号、模型强度有多敏感？

## 2. 假设

- **H1**：在留出任务上，正常模型的 pooled AUROC ≥ 0.7（pilot 的最低可用信号）。
- **H2**：在 α=0.1 时，`clean_success` 的 `FAR_traj` 的经验值不超过 0.2（α + 预设容差）。
- **H3**：至少一种检测触发干预，在长程任务上使成功率提高或成本/步数下降，且 95% CI 不含 0；若没有，则如实报告 null result。
- **H4**：去掉 `test_state` 特征后，检测性能显著下降；这验证执行信号（而非纯文本/步数）是主要信号来源。

## 3. 数据与标签

**数据快照：**

- `data/raw_v1/` 是 2026-11-13 之前的 80 条 trace，作为 300 元简历/开源版的主数据。
- 默认新增：20–30 条新跑（10–20 条短任务 + 3–5 条长程任务 + 1–2 条 benchmark 案例；Django 最多 1 条）。
- SWE-bench/Terminal-Bench 是 stretch：只做 1–2 条案例，不做统计样本；扩到 10–15 条需追加预算和新版预注册。
- 现有 QuixBugs/boltons/requests/自造终端任务保留为 pilot/对照，不扩。
- 歧义/矛盾/作弊任务作为受控探针，单独统计，不混入主 benchmark。

**标签定义：**

| 标签 | 定义 | 用途 |
|---|---|---|
| `clean_success` | finish + 最终 `test_state=[]` + 无 regression + 无违规 + 环境有效 | 正常模型训练/校准 |
| `inefficient_success` | 最终 `[]`，但步数/重复动作明显偏多 | 对照组；不能算异常失败 |
| `absorbed_error_success` | 最终 `[]`，但中间出现过 regression | 异常正样本 |
| `harness_violation_success` | 最终 `[]`，但违反 harness 约束（改测试、越界、作弊） | 异常正样本 |
| `cheating_success` | 测试绿，但通过状态依赖/特判/改判据 | 异常正样本，单独分析 |
| `task_failure` | 最终非空，或 max turns 未通过 | 检测负样本 |
| `env_invalid` | `0xC0000142`、safe-delete、timeout、`NO_CASE`、judge 崩溃、编码失败 | 排除，不参与训练/校准/主指标 |

**排除规则：**

- 任何 `env_invalid` 轨迹不得进入 `clean_success`。
- 写步骤缺 `test_state` 的轨迹不得进入正常训练/校准（`fbs/trace.py:check_trace`）。
- Django 等测试在 workspace 内的任务，若测试文件被修改，标为 `harness_violation_success`，不进正常集。
- 旧版 trace 的 schema 差异（`judge` 缺失、`run_tests` 旧字段）只做兼容读取，不参与主校准。

## 4. 切分

- 锁定 12–15 个任务作为 test，按 `kind` 和 horizon 分层；test 任务不参与特征选择、模型选择、校准、阈值调参。
- 开发集：其余任务；用任务级 5-fold 交叉验证，同一任务的 trace 不跨折。
- 主校准：每个 `clean_success` 任务取一条轨迹；稳健性分析用所有重复轨迹，报告任务级 bootstrap。
- 校准与训练任务不重叠；校准集只放 `clean_success`。
- 主实验数据接入后，切分在 v2 预注册里冻结。

## 5. 主指标与 α

**主指标（预注册）：**

- α=0.1 时的 `FAR_traj`（至少一次报警的 clean success 比例）。
- 中位检测延迟（报警步 - onset 步）。
- AUPRC（step-level，onset 为正）。
- 干预成功率（干预组 vs shadow 组的最终成功率差）。

**次指标：**

- `FAR_step`、AUROC、time-to-detection、coverage、alarms per healthy trajectory。
- 步数、token、cost、每类异常的检测率。

**统计：**

- 任务级 bootstrap 2000 次；比例用 Clopper-Pearson；AUROC 用 DeLong 或 bootstrap。
- 配对成功率用 McNemar；延迟/步数/成本用 Wilcoxon。
- 多重比较用 Holm-Bonferroni；报告效应量和 95% CI，不只报 p 值。

## 6. 模型与基线

**正常模型：**

- 基线：per-task/kind robust z-score（median/MAD）。
- Mahalanobis（Ledoit-Wolf 收缩），主模型只用 8–12 个特征。
- IsolationForest、OCSVM。
- tool n-gram / Markov / HMM 的 log-likelihood surprise。

**序贯检测：**

- 主方法：step-index conformal p 值 + alpha-spending（uniform 和 early-heavy 两种 schedule，预注册）。
- 次方法：e-process / ACI / conformal risk control；明确假设，不做无条件定理声明。

**基线：**

- 无监控。
- 静态阈值（同一分数）。
- OAT 风格 one-class（在特征上复现，引用 OAT）。
- 监督分类器（只用开发集负样本，作为上界，不作为主方法）。
- PNR oracle（用最终 `locate` 的 onset 作为上界）。

## 7. 干预

- 干预类型：`re_read`、`force_tests`、`context_reset/summarize`、`ask_user`、`stop`、`escalate_model`。
- 报警触发；冷却至少 5 步；每轨迹最多 3 次；token/cost 上限。
- 报警时随机分到 intervention vs shadow（只记录），按任务/seed 配对分析。
- 主要比较：最终成功率、恢复率、步数、token、cost、不必要的干预次数。

## 8. Pilot go/no-go

只有全部满足才进入 Month 2 全量：

- 至少 10 任务 × 3 seed 端到端跑通。
- 0 条 `env_invalid` 被标成 healthy；0 个写步骤缺 `test_state`。
- α=0.1 时，留出 `clean_success` 的 `FAR_traj ≤ 0.2`。
- ≥5/15 个失败在 onset 后、最终失败前被检测到；中位检测延迟 ≤5 步或 ≤30% 轨迹长度。
- pooled negatives AUROC ≥ 0.7。
- 监控开销 < 20 ms/step。

未达标：降维、增加校准数据、简化成单一分数，或把主线降级为“作弊/吸收错误检测”。

## 9. 偏差与变更记录

- 任何偏离本预注册的改动（特征、切分、α、指标、排除规则）都必须记录在这里，并说明原因。
- 不得在锁定 test 上调参；不得根据 test 结果修改主指标。
- 负样本稀缺是本研究的设计约束；报告时必须如实说明，不得用弱模型“制造”失败来冒充真实失败。

## 10. 当前快照摘要

| 项目 | 数值 |
|---|---:|
| trace 总数 | 80 |
| `right exit` | 62 |
| `Hit max_turns` | 18 |
| 任务数 | 58 |
| 全成功任务 | 49 |
| 全失败任务 | 6 |
| 长程（≥15 步）轨迹 | 约 20（含失败/循环） |
| 归档校验 | `data/raw_v1/manifest.csv` |
