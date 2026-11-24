# Architecture Decision Records (ADRs)

This directory documents the architectural and design decisions governing the AutoSE automated software engineering system for TinyDB. Decisions follow the Nygard format.

## Index of Decisions

| ADR | Title | Decision Area | Status | Supersedes / Superseded By |
|:---|:---|:---|:---|:---|
| [ADR-001](ADR-001.md) | Divide workflow into five model roles, with one planner for requirements and design | D1 Splitting the work | Accepted — baseline | — *(Errata noted below)* |
| [ADR-002](ADR-002.md) | Use a deterministic controller: state machine for stages 1–5 plus unrolled Actions review DAG | D2 Control flow | Accepted — baseline | — *(Errata noted below)* |
| [ADR-003](ADR-003.md) | Pass structured, sanitised artifacts between stages and withhold implementer reasoning | D3 Hand-offs | Accepted — baseline | — |
| [ADR-004](ADR-004.md) | Store cross-job state as GitHub Actions artifacts and live issue comment; no automatic resume | D4 State | Accepted — baseline | — |
| [ADR-005](ADR-005.md) | Enforce least privilege at job, process, tool, command, and path boundaries | D5 Tools / Security | Accepted — baseline | — *(Errata noted below)* |
| [ADR-006](ADR-006.md) | Allocate model capability by role and evaluate reviewer diversity experimentally | D6 Models | **Superseded** | Superseded by [ADR-012](ADR-012.md) |
| [ADR-007](ADR-007.md) | Gate stages with deterministic checks; use LLM judgement only as bounded supporting evidence | D7 Checks | **Superseded** | Superseded by [ADR-011](ADR-011.md) |
| [ADR-008](ADR-008.md) | Make review independent through fresh execution, minimal context, credential-free model step | D8 Reviewer independence | **Superseded** | Superseded by [ADR-013](ADR-013.md) |
| [ADR-009](ADR-009.md) | Treat issues, comments, PR text, and tool output as hostile data; stop safely | D9 Safety and failures | Accepted — baseline | Complemented by [ADR-014](ADR-014.md) |
| [ADR-010](ADR-010.md) | Restrict triggers to trusted actors, protect target repository, serialize per issue | D10 Triggers | Accepted — baseline | — |
| [ADR-011](ADR-011.md) | Enforce deterministic stage gates with documentation-only plan exceptions and blocking LLM judge verdicts | D7 Checks | **Accepted** | Supersedes [ADR-007](ADR-007.md) |
| [ADR-012](ADR-012.md) | Allocate dual Flash-Lite models on two Gemini API accounts with 6.5s pacing and 80m build budget | D6 Models | **Accepted** | Supersedes [ADR-006](ADR-006.md) |
| [ADR-013](ADR-013.md) | Deploy Reviewer v2 with AST diff facts, pre-change tree rebuild, differential probes, and mandatory probe gate | D8 Reviewer independence | **Accepted** | Supersedes [ADR-008](ADR-008.md) |
| [ADR-014](ADR-014.md) | Enforce strict autonomous operator protocols for provider quota resets and documented design-change PRs | D9 Safety / Governance | **Accepted** | — |

---

## How Decisions Changed

Across Campaign 1 and Campaign 2, operational data and empirical evaluations forced revisions to three foundational decisions:

1. **Stage Check Flexibility (ADR-007 → ADR-011)**: Campaign 1 red-team run [44741723040](https://github.com/Ishaank1805/tinydb/actions/runs/44741723040) stopped because the design gate strictly demanded Python AST functions in all plans, rejecting documentation-only fixes. In addition, auditing revealed that the testability judge in `requirements.py` is actively blocking rather than purely advisory when online. [PR #23](https://github.com/Ishaank1805/tinydb/pull/23) introduced documentation-only plan exceptions, codified in ADR-011, enabling clean completion of documentation issues (e.g. [PR #33](https://github.com/Ishaank1805/tinydb/pull/33)).
2. **Model Provider and Execution Budgets (ADR-006 → ADR-012)**: The pipeline migrated from commercial Claude models to the Google Gemini free tier (`gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`) partitioned across two accounts. Strict 10 RPM rate limits necessitated 6.5s pacing, which caused run [44751912678](https://github.com/Ishaank1805/tinydb/actions/runs/44751912678) to time out after 58 minutes. [PR #24](https://github.com/Ishaank1805/tinydb/pull/24) expanded the build budget to 80 minutes soft (95 hard), codified in ADR-012, reducing spend to $0.00 across 21.67M tokens without further timeouts.
3. **Reviewer Architecture (ADR-008 → ADR-013)**: The baseline reviewer approved 100% of defective seeded PRs in Campaign 1 (0/3 caught). [PR #25](https://github.com/Ishaank1805/tinydb/pull/25) introduced Reviewer v2, providing AST diff facts, pre-change code rebuilding, `compare.sh` differential probing, and a mandatory probe gate. While Campaign 2 showed modest recall improvements (33% on held-out PRs) constrained by model capacity, precision remained 100% across all 40 reviews.
4. **Operational Protocol (ADR-014)**: An unplanned model switch during a quota pause ([PR #35](https://github.com/Ishaank1805/tinydb/pull/35), reverted in [PR #36](https://github.com/Ishaank1805/tinydb/pull/36)) demonstrated the necessity of strict autonomous operator protocols: pausing for daily resets rather than altering live configurations.

---

## Errata from Audit

The comprehensive codebase audit documented in [AUDIT.md](AUDIT.md) identified the following discrepancies in original ADRs:

- **ADR-001 (Session Independence)**: ADR-001 implied that the Planner maintains a single continuous conversation across requirements and design. In the implementation, requirements and design run in distinct agent invocations with independent context windows, handing off state strictly through `spec.md`.
- **ADR-002 (Controller File Path)**: ADR-002 references `workflow/controller.py`. The controller is implemented in `.github/autose/autose/orchestrator.py`; no `workflow/` directory exists in the fork.
- **ADR-004 (Resume Command)**: ADR-004 correctly states that automatic resume is not promised, but references an `/autose resume` command in discussion; `autose/gate.py` does not parse or support `/autose resume`.
- **ADR-005 (Job vs. Process Privilege Separation)**: ADR-005 states that write permissions are separated at the job level. In reality, both agent stages (1–4) and deterministic release (stage 5) execute within the single `build` job in `autose-build.yml`. Write privilege separation is enforced at the process and filesystem sandbox level via `autose/secretstore.py`, rather than through separate runner jobs.
