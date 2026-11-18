# Third-party tasks and licenses

The **code** in this repository is MIT (see `LICENSE`).
The **task content** under `tasks/` comes from several upstream projects and keeps
its original license. Do not relicense third-party code.

| Source | Where | Upstream license | Upstream |
|---|---|---|---|
| QuixBugs | `tasks/task_0001` ... (QuixBugs subset) | MIT | https://github.com/jkoppel/QuixBugs |
| requests | `tasks/req_0001` ... `req_0003` | Apache-2.0 | https://github.com/psf/requests |
| boltons | `tasks/boltons_0001`, `boltons_0002` | BSD-3-Clause (LICENSE text; GitHub API reports NOASSERTION) | https://github.com/mahmoud/boltons |
| Django | `tasks/django_16820` | BSD-3-Clause | https://github.com/django/django |
| Terminal-Bench 2.1 | `tasks/tb_regex_log` | Apache-2.0 | https://github.com/harbor-framework/terminal-bench-2-1 |
| Self-made probes | `tasks/amb_*`, `tasks/term_*`, `tasks/couple_0001`, `tasks/multi_0001` | MIT (this repository) | — |

Verified 2026-11-18 via the GitHub license API and the upstream `LICENSE` text.
The task directories contain modified subsets; keep the upstream copyright
notices and do not relicense them.

## Before publishing

1. [x] Check each upstream `LICENSE` and record the exact license name/version.
2. Include required `NOTICE`/attribution files if the upstream license asks for it.
3. If a task cannot be redistributed, exclude it from the public repo and keep it local.
4. `data/raw_v1/` contains model outputs and code snippets derived from these tasks;
   treat it under the same upstream licenses.
5. Review `docs/` for private content before making the repository public.
