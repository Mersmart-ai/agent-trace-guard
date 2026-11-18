# 代码审计与项目状态

- 日期：2026-11-18
- 方式：只读审计，未改动代码
- 结论：**当前是检测原型，不是错误控制系统；长程干预从未被有效验证。**

## 0. 核心问题（用户指出的）

1. 我们只证明了“规则能报警”，没有证明“报警后干预能改善长程任务”。
2. Django 20/60 步的真实失败模式是“一直读、不写、最后红”，
   监控器能报 `long_gap`，但没有在报警后做任何控制。
3. 之前的干预 A/B 用的是短任务 `no_verify`，
   而且 harness 强制判分让“跳过测试”不影响正确性，实验目标选错了。
4. 因此，如果长程干预仍然无效，这个项目就只能定位为“过程检测 + 负结果”，
   不能声称“错误控制”。

## 1. P0：影响正确性/有效性的问题

### P0-1 规则逻辑两份且已分叉

- 正式版：`src/fbs/analysis/monitor.py:19`，包含 `long_gap`、`unverified_write`
- 实验版：`experiments/cv_calibration.py:44 static_rules`，**没有**这两条
- `heldout_anomalies.py`、`cv_calibration.py` 的规则基线是旧的
- 后果：报告里“规则 vs Fisher”和正式 monitor 不是同一套规则
- 修改方向：`static_rules` 直接调用 `monitor.rule_alarms`，删掉重复实现

### P0-2 `delta` 只看失败数量，漏掉“同数量替换”

- `src/fbs/analysis/features.py:122`：`delta = fails - last_fails`
- `src/fbs/analysis/monitor.py:54`：`delta` 规则只看这个数量差
- 如果一步里修好 test_a、又弄坏 test_b，数量不变，监控器不报
- `src/fbs/legacy/locate.py:131` 的 `regressions` 用集合差，能抓到
- 修改方向：增加 `new_red` 集合差特征，`delta` 规则改为看新红集合

### P0-3 `cli.py` 没接入新的 judge gating

- `src/fbs/cli.py:72` 只拷贝 `python / visible_command / judge_command`
- 没有 `fast_judge_command / judge_timeout / fast_judge_timeout / visible_timeout / max_turns`
- 后果：`python run.py` 跑 Django 时每个 bash/write 都跑完整判据，10 秒超时
- `experiments/real_runs.py` 是对的，两条入口行为不一致
- 修改方向：`cli.py` 读取并透传这些 meta 键

### P0-4 `llm.py` 默认模型写错

- `src/fbs/llm.py:23` 后端默认 `deepseek-flash`
- `src/fbs/llm.py:40` 实际默认 `deepseek-chat`
- `src/fbs/llm.py:34` 注释还写“默认 dashscope”，已过期
- 后果：不显式设置 `FBS_MODEL` 时，用的不是 flash
- 修改方向：默认统一为 `deepseek-flash`，清理注释

### P0-5 最终判分有两个来源

- `experiments/real_runs.py:149` 写入 `final_test_state`（完整判据）
- `src/fbs/data/audit.py:169` 只用 `steps` 里的 `test_state`
- `src/fbs/analysis/monitor.py` 也只读 steps
- Django r01：steps 最后一次快速判据 5 红，`final_test_state` 7 红
- 修改方向：明确权威来源；或两者都保留并注明用途

### P0-6 `blind` 规则仍会误报终端任务

- `src/fbs/analysis/monitor.py:96`：第一次 `write_file` 前没有 `read_file`
- 终端任务可能用 `bash cat/grep` 检查文件，然后 `write_file`
- `tb_regex_log` 的 full 规则报警就是这种情况
- 不在 strict 里，但 full 规则仍有误报
- 修改方向：按目标文件判断“写它之前有没有读过它”，而不是全局计数

## 2. P1：影响可信度/可复现性

1. `long_gap=15` 硬编码（`monitor.py:21`），只基于当前 56 条 clean
2. Fisher 5 折结论不在 `fisher_value_probe.py` 里，是手工补跑
3. 长程 Fisher 对比存在窗口问题：`T_MAX=8` 校准，完整 trace 打分
4. `clean_success` 与“过程规范”不是同一个标签；`task_0012_r01` 是例子
5. `docs/prereg.md` 和 `pyproject.toml:8` 仍以 one-class/conformal 为主线
6. `THIRD_PARTY.md` 的 license 仍是 TODO
7. `docs/日志/` 可能含私人内容，开源前要检查

## 3. P2：工程卫生

- `monitor.py` docstring 的 strict 列表漏了 `long_gap`
- `policy.py:124` 只剥 `test_state`，没剥 `judge`；模型能看到 `fast/full`
- `cli.py:27` 的 `ONLY` 写死，`python run.py` 只跑 6 个歧义任务
- `run_tests` 的 `command.replace("{python}", py)` 没加引号
- `llm.py` 没有重试/退避；一次 429 就中断
- 没有成本上限，只有 `OutOfCredit`
- `save_run` 与 `real_runs.save_trace` schema 不一致
- `reports/long_horizon_probe.md` 有两个 `## 6`
- 测试没覆盖 `fast_judge_command/max_turns`、`run_tests` 超时、
  `audit.classify_run`、`real_runs` 最终判据

### 2026-11-18 已处理

- P1-5：README / prereg / pyproject 已改为“规则监控 + turn-stopping 干预”主线；
  prereg 顶部保留历史说明。
- P1-6：`THIRD_PARTY.md` 已核对 QuixBugs / requests / boltons / Django /
  Terminal-Bench 2.1 的上游 license。
- P1-7：检查过 `docs/日志/`，未发现 key/密码；内容仍是个人开发记录，
  发布前由用户决定是否保留。
- P2：`monitor.py` docstring、`policy.py` 的 `judge` 泄漏、
  `run_tests` 的 `{python}` 引号、`ONLY` 写死（改为 `FBS_ONLY`）已修；
  新增 `test_policy`、`test_tools`、`test_cli`、`test_audit`。
- 未处理：LLM 重试/退避、成本上限、`save_run` schema、
  报告编号、`fast_judge_command/max_turns` 的行为测试。

## 4. 站得住的部分

- `agent_loop` 的强制判分、workspace 重置、隐藏测试、bash 白名单
- `features.py` 只读 history，在线/离线口径一致
- `monitor.py` 规则可解释，主要分支有测试
- `audit.py` 的数据卫生和解析失败处理
- 长程受控故障：漏验证 9/9、打转 9/9
- Django 真实失败：20/60 步，0/1 次写，最终 7 条红
- Git 已打标签，工作区干净

## 5. 当前研究结论

| 目标 | 判断 |
|---|---|
| 开源 GitHub artifact | 可以，先修 P0/P1 + license |
| 简历 | 可以，讲规则监控 + 长程故障注入 + 负结果 |
| 毕业设计/workshop | 可以，但必须如实写规则优先、Fisher 负结果 |
| 主会论文 | 现在不行 |
| 错误控制系统 | **未验证**；这是当前最大缺口 |

## 6. 修改清单（按顺序）

- [x] P0-1 统一规则：`cv_calibration.static_rules` 调用 `monitor.rule_alarms`
- [x] P0-2 `delta` 改为看新增红测试集合
- [x] P0-3 `cli.py` 透传 fast judge / timeout / max_turns
- [x] P0-4 `llm.py` 默认模型统一为 `deepseek-flash`
- [x] P0-5 明确 `final_test_state` 与 `locate(steps)` 的权威关系
- [x] P0-6 `blind` 改为按目标文件判断

2026-11-18：6 个 P0 已修。验证：`pytest -q` **63 passed**；
`blind` 在 heldout clean 上的误报从 3/16 降到 0/16；
`delta` 增加“同数量替换”测试；`final_test_state` 在 Django 真实 trace 上
取到完整 7 条红。

- [ ] P1 更新 prereg/README/description，记录方向变更
- [ ] P1 补 Fisher 5 折脚本化、长程窗口说明
- [ ] P2 清理注释、ONLY、schema、报告编号
- [ ] P2 补关键单测
- [ ] 公开前核对第三方 license 和 docs/日志

## 7. 长程干预实验（核心缺口）

### 目标

验证“报警 → 干预”能否改变长程任务的结果或成本，而不只是报警。

### 触发

- `long_gap`：连续 `since_test > 15`
- 或连续只读步数超过阈值（例如 12 步没有 write）
- 以 Django 的 20/60 步失败为真实场景

### 两个 arm

- `guardrail`：在报警后的下一次 policy 调用注入提醒：
  > 你已经连续多步只读、没有修改任何文件。不要再继续搜索；
  > 基于当前信息选择一个最可能的文件，做一次最小修改，然后 run_tests。
- `shadow`：只记录，不提醒

### 指标

- 写文件次数
- `run_tests` 次数
- 最终失败测试数
- 步数/token
- 是否从“只读打转”转为“修改+验证”

### 预算

- Django 20 步 × 2 arm × 1–2 个 seed
- 约 2–4 元

### 判定

- 如果干预增加写/测试并减少最终红测试 → 错误控制成立
- 如果没有变化 → 项目只能定位为“检测 + 负结果”，不能声称错误控制

### 2026-11-18 新证据：Django 同任务对照

- 自研 harness：r01 30 步、r02 60 步，0 次写，最终 7 条红；
- dsh shadow：**43 步、2 次写、4 次测试、217/217 OK**，只改
  `django/db/migrations/operations/models.py`，`tests/` 没动；
- 这支持 7.1 的判断：原失败主要是动作空间/定位工具不足，
  不是模型完全不会；
- 但 Django 上的 `shadow` vs `guard` A/B 还没做，
  **“错误控制”仍然没有被验证**。

## 7.1 为什么长程数据退化（2026-11-18 补充）

只读检查证据：

1. `list_files` 上限 200；Django 有 2746 个 py 文件。
   实测返回 201 条，目标文件
   `django/db/migrations/operations/models.py`
   **不在前 200 条里**。
   系统提示词还写着“只能用 list_files 列出来的路径读写代码文件”。
   模型看不到目标，也不敢写。

2. 目标文件 1142 行；`write_file` 要求完整文件内容；
   `bash` 白名单没有 `sed`/`python`；没有 `replace_in_file`/`apply_patch`。
   模型没有可用的局部修改工具，自然回避写。

3. `task.md` 没有失败测试名、报错栈、文件路径提示。
   Django 的定位难度过高，模型 20/60 步都找不到目标。

4. 现有长程数据是双峰的：
   - 简单任务 5–9 步一次过，没有过程信号
   - Django 只读打转，没有“写-测-修”过程
   中间难度、能失败再恢复的任务缺失。

结论：

- 当前长程数据只能分析“定位失败”，不能分析“错误控制”
- 在修好动作空间和任务信息之前，继续跑 Django seed 没有意义

改进顺序：

1. `list_files` 分页/过滤，保证目标可见；取消“只能写列表路径”的软限制
2. 新增 `replace_in_file` 或 `apply_patch`；`read_file` 支持行号范围
3. `task.md` 提供失败测试名/报错栈/文件级提示
4. 增加 10–30 步、可写可测可失败的中间难度任务
5. 定义“有效长程 run”：≥1 次写、写后 ≥1 次测试、有失败→修改→再测

## 8. 预算状态

- 已用约 3–5 元（以 DeepSeek 账单为准）
- 剩余约 5–7 元
- 长程干预实验预算 2–4 元，可控
