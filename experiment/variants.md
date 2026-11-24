# Decision-Experiment Variants

Each variant is a named overlay in `.github/autose/autose.config.yml`. The table below lists all variants supported by the harness and evaluated in our experimental campaigns. Full runs of a variant get their own branch (`autose/issue-<N>-<variant>`) and pull request, ensuring they never overwrite baseline runs.

| Variant | Configuration Overlay | Decision Area | Purpose & Protocol |
|---|---|---|---|
| `baseline` | Standard harness configuration | Reference | Multi-agent modular pipeline (Stages 1–5) and Reviewer v2 (AST diff-facts, differential probing). Triggered via label `autose` or `/autose`. |
| `single-agent` | `pipeline: {shared_context: true}` | D1 (Work Splitting) | Single generalist agent session handles requirements, design, implementation, and test generation in a continuous context. Evaluated across all 5 benchmark issues in Campaign 1 and replicated in Campaign 2. |
| `no-review-loop` | `pipeline: {max_change_requests: 0}` | D2 (Control Flow) | Single review pass with no rework allowed (`max_change_requests: 0`). Evaluates failure progression when revision cycles are disabled. |
| `reviewer-v1` | `review: {prompt: reviewer_v1, diff_facts: false, base_tree: false, require_probe: false}` | D8 (Reviewer Architecture) | Uses the original Campaign 1 reviewer prompt without AST diff-facts, pre-change baseline tree, or differential probing. Evaluated across 40 seeded PR reviews in Campaign 2. |
| `reviewer-sees-rationale` | `review: {withhold_rationale: false}` | D8 / D3 (Information Hiding) | Reviewer receives author rationale (`design.md`, `pr.md`, or seeded PR narrative) alongside diff. Evaluated in Campaign 1 on seeded PRs S1–S5. |
| `reviewer-same-model` | `agents: {reviewer: {model: gemini-3.5-flash-lite}}` | D6 (Model Allocation) | Assigns the reviewer to the implementer's model (`gemini-3.5-flash-lite`) instead of `gemini-3.1-flash-lite`. |

---

## Executed Decision Experiments

The test runner script (`experiment/scripts/autopilot.py`) executes evaluation runs in ordered batches with transient network retries and automated rate-limit pacing (6.5s delay). We conducted two primary architectural experiments across 80 protocol runs:

### Experiment 1: Modular Multi-Agent vs. Single-Agent Architecture (D1)
- **Hypothesis**: Decomposing software maintenance into specialized roles (Planner, Implementer, Test Author) with strict stage gating will reduce self-reinforcing author bias and improve hidden test pass rates compared to a single generalist agent.
- **Protocol**: 5 benchmark issues (Issues 1–5) evaluated across two full campaigns (10 full runs per variant).
- **Observed Results**:
  - *Functional Outcomes*: Both variants tied, releasing 9/10 PRs and passing 36/40 hidden tests each. Baseline multi-agent solved all 5 issues in Campaign 2 with 100% hidden tests (20/20). Single-agent solved all 5 issues in Campaign 1 (20/20) but stopped at Issue 2 requirements in Campaign 2 due to testability judge rejections.
  - *Token Consumption*: Multi-agent baseline averaged 456,700 tokens/run in C1 and 629,641 tokens/run in C2. Single-agent averaged 1,001,233 tokens/run in C1 and 675,261 tokens/run in C2.
  - *Architectural Trade-off*: While single-agent generalist eliminates inter-stage serialization overhead, modular multi-agent provides stricter process privilege boundaries (ADR-005, ADR-015) and per-stage timeout isolation.

### Experiment 2: Reviewer Architecture Evolution — Reviewer v1 vs. Reviewer v2 (D8)
- **Hypothesis**: Providing an independent reviewer with AST diff-facts, an isolated pre-change baseline repository tree, and differential probing (`compare.sh`) will increase defect detection on subtle bugs without generating false alarms on clean code.
- **Protocol**: 10 seeded PRs (Dev set `S1`–`S5`, Held-out set `S6`–`S10`) evaluated across two independent repetitions per variant (40 total seeded PR reviews).
- **Observed Results**:
  - *Precision*: Both versions achieved 100% precision with 0 false alarms across all 20 clean code reviews (S1, S5, S9, S10 $\times$ 2 repeats).
  - *Defect Recall*: On held-out PRs (S6–S10), Reviewer v2 caught 2/6 defects (33%) in each repeat (catching S7 and S8), whereas Reviewer v1 caught 3/6 defects (50%) in repeat 1 and 2/6 in repeat 2. Across all 30 defective reviews, v2 invoked `compare.sh` 15 times across 12 reviews.
  - *Failure Mode*: In 9 of 30 defective reviews, the reviewer executed a probe that observed the bug but approved anyway, treating behavioral changes as benign or intentional optimizations.
