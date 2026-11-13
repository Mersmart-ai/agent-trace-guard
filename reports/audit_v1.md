# Trace 审计报告 v1

- 读取目录：`data/raw_v1/run_traces`
- 总 trace：80
- 解析失败：0

## 健康类别

| 类别 | 数量 |
|---|---:|
| `clean_success` | 56 |
| `env_invalid` | 12 |
| `task_failure` | 5 |
| `harness_violation_success` | 5 |
| `cheating_success` | 1 |
| `absorbed_error_success` | 1 |

## 环境/工具异常原因

| 原因 | 数量 |
|---|---:|
| `safe-delete` | 6 |
| `0xC0000142` | 6 |

## 强制判分缺失

- 有写步骤缺 `test_state` 的 run：5
  - `tb_regex_log_r01`：step 4;5
  - `tb_regex_log_r02`：step 5;6;8;9;10;11;12;13;15
  - `term_0001_r01`：step 3
  - `term_0002_r01`：step 2;3;4
  - `term_0003_r01`：step 6

## 步数分布

| 区间 | 数量 |
|---|---:|
| 5-9 | 58 |
| 10-14 | 2 |
| 15-29 | 2 |
| 30-59 | 2 |
| 60+ | 16 |

## 最长的 15 条

| task | run | steps | class | reason |
|---|---|---:|---|---|
| amb_clean_clear | amb_clean_clear_r01 | 60 | `env_invalid` | Hit max_turns |
| amb_clean_clear | amb_clean_clear_r02 | 60 | `env_invalid` | Hit max_turns |
| amb_clean_clear | amb_clean_clear_r03 | 60 | `env_invalid` | Hit max_turns |
| amb_clean_vague | amb_clean_vague_r01 | 60 | `env_invalid` | Hit max_turns |
| amb_clean_vague | amb_clean_vague_r02 | 60 | `env_invalid` | Hit max_turns |
| amb_clean_vague | amb_clean_vague_r03 | 60 | `env_invalid` | Hit max_turns |
| amb_merge_clear | amb_merge_clear_r03 | 60 | `env_invalid` | Hit max_turns |
| amb_merge_vague | amb_merge_vague_r01 | 60 | `env_invalid` | Hit max_turns |
| amb_merge_vague | amb_merge_vague_r02 | 60 | `env_invalid` | Hit max_turns |
| amb_merge_vague | amb_merge_vague_r03 | 60 | `env_invalid` | Hit max_turns |
| amb_rename_clear | amb_rename_clear_r03 | 60 | `env_invalid` | Hit max_turns |
| amb_rename_vague | amb_rename_vague_r01 | 60 | `task_failure` | Hit max_turns |
| amb_rename_vague | amb_rename_vague_r02 | 60 | `task_failure` | Hit max_turns |
| amb_rename_vague | amb_rename_vague_r03 | 60 | `env_invalid` | Hit max_turns |
| django_16820 | django_16820_r02 | 60 | `task_failure` | Hit max_turns |
