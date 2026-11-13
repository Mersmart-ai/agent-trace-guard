# Third-party tasks and licenses

The **code** in this repository is MIT (see `LICENSE`).
The **task content** under `tasks/` comes from several upstream projects and keeps
its original license. Do not relicense third-party code.

| Source | Where | Upstream license |
|---|---|---|
| QuixBugs | `tasks/task_0001` ... (QuixBugs subset) | TODO: verify from upstream repository |
| requests | `tasks/req_0001` ... `req_0003` | TODO: verify from upstream repository |
| boltons | `tasks/boltons_0001`, `boltons_0002` | TODO: verify from upstream repository |
| Django | `tasks/django_16820` | TODO: verify from upstream repository |
| Terminal-Bench | `tasks/tb_regex_log` | TODO: verify from upstream repository |
| Self-made probes | `tasks/amb_*`, `tasks/term_*`, `tasks/couple_0001`, `tasks/multi_0001` | MIT (this repository) |

## Before publishing

1. Check each upstream `LICENSE` and record the exact license name/version.
2. Include required `NOTICE`/attribution files if the upstream license asks for it.
3. If a task cannot be redistributed, exclude it from the public repo and keep it local.
4. `data/raw_v1/` contains model outputs and code snippets derived from these tasks;
   treat it under the same upstream licenses.
5. Review `docs/` for private content before making the repository public.
