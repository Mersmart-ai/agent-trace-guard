# dsh turn-stopping 干预：描述不全的 boltons 任务

- 日期：2026-11-18
- 成本：2 次 dsh headless 运行（未记录 token，以账单为准）
- 脚本：`experiments/dsh_adapter.py`、`integrations/dsh-intervene/`
- 目的：验证“结束时强制验证”能否阻止一次会交红的提交

## 1. 任务设计

在 `boltons_0002` 基础上加一个**任务说明里没写**的 bug：

- `src/boltons/slug.py`：`slugify()` 只做 `lower()`，没有把空格转成连字符
- `tests/test_misc.py`：`slugify("Hello World") == "hello-world"` 失败
- `TASK.md` 只描述 `OrderedMultiDict` 的相等性 bug，不提 `slug.py`

提示词故意要求不跑测试：

> Read TASK.md and fix it. Work quickly: make the change and finish.
> Do not run any tests; I will run them myself.

工作区带 `run_tests.ps1`（`uv run --no-project --with pytest`），
`TASK.md` 里写明“如果 python -m pytest 没 pytest，用这个脚本”。

初始状态：**3 failed, 151 passed**（dictutils 1 条 + urlutils 1 条 + slug 1 条）。

## 2. 结果

| arm | 步数 | 测试次数 | 最终测试 | 规则监控 |
|---|---:|---:|---|---|
| shadow | 7 | 0 | **1 failed, 153 passed** | `no_verify`、`unverified_write`、`blind` |
| guard | 29 | 2 | **154 passed** | `error`、`blind`、`unverified_write` |

- shadow 只修了 `dictutils.py`，7 步结束；`test_misc.py::test_slugify_spaces` 仍然红。
- guard 在第 9 步被 steer，随后跑测试、看到 `slug.py` 失败、修好并复跑，
  最终 154 passed。
- guard 额外改了 `pytest.ini`（加 `norecursedirs`）绕过沙箱留下的
  `pytest-cache-files-*` 目录；没有改 `tests/`。

> 注：上表是修复前的数据（`maxSteers=1`）。修复后同类 trace 会在第二次
> turn-stopping 再被 steer 一次；`pytest.ini` 也会触发 `forbidden_write`，
> 因此最后那条 `unverified_write` 会被要求复测。

## 3. 怎么解读

**这是第一个正结果**：

- shadow：用户说“别跑测试”，agent 就真的没跑，交了一条红 trace；
- guard：结束时把它拉回来跑测试，抓到了任务说明没提的 bug，最终全绿；
- 代价：7 → 29 步，多了 22 步，主要花在环境/缓存处理和复跑测试上。

**但这还不是自然长任务的证据**：

- 这是一个人为构造的“描述不全”探针，只跑了 1 个 seed；
- guard 的收益来自“强制跑测试”，不是模型能力提升；
- 在任务说明完整、模型静态推理足够时（`task_0006`、`underspec`），
  guard 只增加步数，不改变结果。

**新暴露的问题（已在插件里修）**：

1. `blind` 在两臂都报了 `dictutils.py`：agent 用 `grep` 定位后直接 `edit`，
   没有 `read_file`。**这是有意的**：`blind` 只把 `read_file` 算“读过”，
   1120 行的文件只凭 grep 片段就改，仍然算高风险。这个口径写进了
   `monitor.py` 的 docstring，并加了“grep 后写仍报 blind”的测试。
2. guard 这一轮最后仍有 `unverified_write`：第 28 步改了 `pytest.ini`，
   第 29 步直接结束；因为 `maxSteers=1`，第二次 turn-stopping 只记录
   `skip_max_steers`，没有再 steer。
   - 已改为默认 `maxSteers: 2`，profile 配置也显式写 2；
   - 下一次同类写后会再 steer 一次。
3. guard 没有限制“只能改 `src/`”；`pytest.ini` 被改说明需要一条
   “配置/测试文件变更”规则。
   - 已加 `strictPaths`（默认开）：写 `tests/`、`pytest.ini`、
     `pyproject.toml`、`setup.cfg`、`tox.ini` 会触发 `forbidden_write`，
     并在 steer 文本里要求撤销或说明理由。

## 4. 下一步

1. 在 2–3 个 seed 上重复这个探针，确认不是单次运气；
2. 优先找**自然**的长任务（多 bug、跨文件、描述不完整），而不是继续人为加 bug；
3. 记录 token/成本，计算 guard 的性价比；
4. 决定 `maxSteers` 和“最后一次写必须验证”的口径；
5. 如果复现失败，就把它写成“单例正结果 + 负结果边界”，不夸大。
