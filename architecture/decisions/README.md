# Architecture decision records

Write one ADR per decision in the Nygard format (`TEMPLATE.md`), named
`ADR-001.md`, `ADR-002.md`, ... . **The ADRs and their reasoning must be your own
writing** (course policy). This page only points to where each decision lives in
the code and which knobs and evidence exist, so you can describe, question or
change what was built. When a run shows an ADR was wrong, keep it, mark it
*Superseded by ADR-0XX* and add a new one.

| Area | Where it lives in the code | Knobs | Evidence you can collect |
|---|---|---|---|
| D1 Splitting the work | `autose/context.py` (`run_agent`), `autose/stages/*`, `prompts/*` | variant `single-agent` (`pipeline.shared_context`) | hidden tests, stage pass rates, tokens per variant |
| D2 Control flow | `autose/orchestrator.py` (state machine), `.github/workflows/autose.yml` (unrolled review/rework jobs) | `pipeline.max_*`, variant `no-review-loop` | loops per run (`results.csv`), outcomes |
| D3 Hand-offs | task messages built in `autose/stages/*.py` and `autose/review.py`; `review_feedback()` in `orchestrator.py` | variant `reviewer-sees-rationale` | reviewer accuracy on seeded PRs |
| D4 State | `autose/state.py`, artifacts per job, status comment (`autose/status.py`), branch + PR | artifact retention in the workflows | re-run a failed job and observe |
| D5 Tools | `autose/toolspecs.py`, `autose/tools.py`, `autose/sandbox.py`, REST client `autose/github.py` | `target.*_globs`, `sandbox.deny_patterns` | `policy_revert` and refusal events in the logs |
| D6 Models | `agents:` in `autose.config.yml`, `autose/llm.py` | variant `reviewer-same-model` | reviewer accuracy, cost |
| D7 Checks | `autose/checks.py`, `autose/stages/testing.py`, `autose/stages/release.py`, judge prompt | `judge.*`, `pipeline.fail_to_pass` | `check_stats` per run |
| D8 Reviewer independence | `.github/workflows/autose-review.yml`, `autose/review.py` (evidence gate), `prompts/reviewer.md` | `review.*`, variants `reviewer-sees-rationale`, `reviewer-same-model` | seeded PR confusion table |
| D9 Safety and failures | `autose/untrusted.py`, `autose/secretstore.py`, `autose/usage.py`, timeouts in the workflows | `budgets.*` | red-team issue (optional), budget stops |
| D10 Triggers | `autose.yml` (`on:`, `concurrency:`), `autose/gate.py` | `trigger.*` | gate skips and permission refusals |

## Architecture Decisions

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001.md) | Divide the workflow into five model roles, with one planner covering requirements and design | Accepted — baseline |
| [ADR-002](ADR-002.md) | Use a deterministic controller: a state machine for stages 1–5 plus an unrolled GitHub Actions review DAG | Accepted — baseline |
| [ADR-003](ADR-003.md) | Pass structured, sanitised artifacts between stages and deliberately withhold implementer reasoning from the reviewer | Accepted — baseline |
| [ADR-004](ADR-004.md) | Store cross-job state as GitHub Actions artifacts and a live issue status comment, not in cache or uncommitted workspace state | Accepted — baseline |
| [ADR-005](ADR-005.md) | Enforce least privilege at job, process, tool, command, and path boundaries | Accepted — baseline |
| [ADR-006](ADR-006.md) | Allocate model capability by role and evaluate reviewer diversity experimentally | Accepted — baseline |
| [ADR-007](ADR-007.md) | Gate stages with deterministic checks; use LLM judgement only as bounded supporting evidence | Accepted — baseline |
| [ADR-008](ADR-008.md) | Make review independent through fresh execution, minimal context, a credential-free model step, and an adversarial rubric | Accepted — baseline |
| [ADR-009](ADR-009.md) | Treat issues, comments, PR text, and tool output as hostile data; stop safely on uncertainty or exhausted budget | Accepted — baseline |
| [ADR-010](ADR-010.md) | Restrict triggers to trusted actors, protect the target repository, and serialize work per issue | Accepted — baseline |
