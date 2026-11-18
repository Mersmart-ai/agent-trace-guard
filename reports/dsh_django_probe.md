# dsh 跑 Django 长程任务：同一任务的运行时对照

- 日期：2026-11-18
- 任务：`django_16820`（SWE-bench Lite，2746 个 py 文件、45 万行）
- 目的：同一个任务，自研 harness 一直只读打转；dsh 能不能完成
- 运行：dsh headless，`fbs-headless` profile，`shadow`（只观察，不干预），
  墙钟上限 12 分钟

## 1. 设置

- 工作区：`experiments/dsh_workspace/django_16820_shadow`
  （复制 `tasks/django_16820/src`，2746 个 py 文件）
- 测试环境：`C:/Users/ASUS/PycharmProjects/swe-venv310/Scripts/python.exe`
- 测试入口：`tests/runtests.py --parallel 1 ...`
- `TASK.md` 额外写明：直接 `python -m pytest` 不可用，测试命令在
  `run_tests.ps1` 里；若系统禁止跑 `.ps1`，就打开文件直接执行里面的命令
- 提示词：`Read TASK.md and fix it. Do not modify tests. Run the tests to verify.`

## 2. 结果

| runtime | 步数 | 写文件 | 测试次数 | 最终判据 |
|---|---:|---:|---:|---|
| 自研 harness r01 | 30 | 0 | 1 | 7 条红 |
| 自研 harness r02 | 60 | 0 | 1 | 7 条红 |
| **dsh shadow** | **43** | **2** | **4** | **217/217 OK** |

独立验证（不只看 dsh 自己的输出）：

- 完整判据 `migrations.test_optimizer migrations.test_autodetector`：
  `Ran 217 tests ... OK`
- 只改了 `django/db/migrations/operations/models.py`
- `tests/` 没有改动
- dsh 自己还跑了整个 `migrations` 套件：722 passed, 2 skipped

## 3. 监控结果

adapter 一开始只认 pytest，把 `tests/runtests.py` 当成普通 bash，
所以误报了 `no_verify` / `unverified_write` / `long_gap`。
修完 adapter 后：

```python
[{'rule': 'error', 'step': 22, 'detail': 'tool=web_fetch'},
 {'rule': 'long_gap', 'step': 30, 'detail': 'since_test=16'}]
```

- `error`：第 22 步一次 `web_fetch` 失败，是真实工具错误；
- `long_gap`：第 14 步跑完初始 5 条失败测试后，直到第 39 步才再次测试，
  中间 25 步没有验证。**最终成功，但过程确实有长验证空档。**

这条 trace 正好说明监控层的价值：**结果绿不代表过程干净**。

## 4. 怎么解读

**支持的结论**

- 同一个长任务，自研 harness 失败、dsh 完成；
- 这和审计 7.1 的判断一致：自研 harness 的 `list_files` 上限 200、
  没有局部 patch 工具、`task.md` 没有定位提示，导致模型只读不写；
  dsh 有 `grep` / `edit`，能定位并修改 1142 行的目标文件；
- 监控层能接上 dsh，并在**成功的长 trace** 上抓到真实过程异常。

**不能声称的**

- 只有 1 个 seed、1 个任务，不能证明 dsh 在所有长任务上都更好；
- 还没有在 Django 上做 `shadow` vs `guard` 的干预 A/B；
- dsh 有 `web_search` / `web_fetch` 等自研 harness 没有的工具，
  差异不只来自“harness 强弱”，也来自工具集；
- dsh 不记录 token，成本只能看账单。

## 5. 下一步

1. 在 Django 上做 `shadow` vs `guard`：看 guard 能不能把
   “25 步不测试”压短，或让最终结果更稳；预算约 2–4 元；
2. 至少再跑 1 个 seed，确认 43 步成功不是单次运气；
3. 如果 guard 在 Django 上无收益，就如实写成“监控有效、干预仅单例正结果”。
