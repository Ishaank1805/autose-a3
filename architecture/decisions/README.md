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
