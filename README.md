# AutoSE: Automated Software Engineering for TinyDB

**AutoSE** is an autonomous, end-to-end software engineering system built for the `tinydb` repository as part of CS6.403 (Assignment 3). Triggered by issue comments or labels, AutoSE orchestrates requirements extraction, architectural design, code implementation, test authorship, automated release, and independent adversarial code review under strict deterministic gating, least-privilege sandboxing, and finite retry limits.

| Metadata | Details |
|:---|:---|
| **Fork Repository** | [https://github.com/Ishaank1805/tinydb](https://github.com/Ishaank1805/tinydb) |
| **Pinned Upstream Commit** | `msiemens/tinydb@edff96aeb2616402e9489d46e90a592c05565621` |
| **Course & Roll Number** | CS6.403 Software Engineering — Roll Number `2023114016` |
| **Workflow Source** | `.github/workflows/autose.yml` in the fork (mirrored in [`workflow/`](workflow/)) |
| **Primary Report** | [`report.pdf`](report.pdf) (7-page body PDF with Appendices A–C) |
| **Walkthrough Video** | [`demo.mp4`](demo.mp4) (4:08 / 248.2s narrated video with live screen recording, 16 slides, 5.1 MB) · metadata in [`demo.mp4.json`](demo.mp4.json) |

---

## Models and Infrastructure

All model invocations route through the Google Gemini free tier via the OpenAI-compatible endpoint, incurring **$0.00** total cost across **21,668,554 tokens** and 80 protocol runs. Both Google accounts operate without payment methods or billing accounts attached, establishing a provider-level hard spend limit of $0.00:

- **`gemini-3.5-flash-lite`**: Assigned to the Planner (requirements & design), Implementer (code generation), and Single-Agent Generalist roles.
- **`gemini-3.1-flash-lite`**: Assigned to the Test Author, Testability Judge, and Independent Reviewer roles.
- **Dual Account Partitioning**: Roles are statically bound across two Google accounts to prevent rate limit saturation:
  - *Account A* (`GEMINI_API_KEY`): Serves build roles (planner, implementer, test author, and judge).
  - *Account B* (`GEMINI_API_KEY_2`): Serves the independent reviewer and single-agent experimental variant.
- **Pacing & Timeouts**: 6.5s delay between requests (strictly within 10 RPM); 80-minute soft build budget (95-minute hard Actions limit; PR #24).

---

## How to Trigger the Workflow

AutoSE is gated by strict permission controls. Only users with at least `write` permission on the fork repository can trigger runs:

1. **Full Pipeline on an Issue**:
   - Add the label **`autose`** to an open issue, or post a comment:  
     `/autose` or `/autose run`
   - This executes Stages 1–5 (requirements -> design -> implementation -> testing -> release), opens a pull request, and triggers Stage 6 (independent review) with up to 2 rework rounds.
2. **Review-Only on a Pull Request**:
   - Comment on an open PR:  
     `/autose review #<issue_number>`
   - Executes an isolated independent review against the specified issue specification.
3. **Decision Experiments**:
   - Append `variant=<name>` to an issue or review command:  
     `/autose run variant=single-agent`  
     `/autose review #2 variant=reviewer-v1`
4. **Manual Dispatch**: Maintainers can trigger runs via **Actions → AutoSE → Run workflow** with parameters.
5. **System Verification**: **Actions → AutoSE doctor** runs an automated 18-step preflight suite verifying permissions, secret staging, Git state, and API connectivity ([Run 44933394627](https://github.com/Ishaank1805/tinydb/actions/runs/44933394627)).
6. **No Auto-Merge**: AutoSE **never merges a pull request**. Merging is strictly reserved for human maintainers.

---

## Artifacts and Documentation Directory

- **Report & Video**:
  - [`report.pdf`](report.pdf): Full technical report (7 body pages, under 8-page cap, plus Appendices A–C).
  - [`demo.mp4`](demo.mp4): 4-minute 8-second narrated demonstration video with live screen recording (audio synthesized via `edge-tts`).
  - [`demo/storyboard.json`](demo/storyboard.json): 16-slide storyboard linking real issue, run, and PR URLs.
- **Architecture**:
  - [`architecture/views/component.md`](architecture/views/component.md): Component diagram and Reviewer v2 differential probe architecture.
  - [`architecture/views/stage_map.md`](architecture/views/stage_map.md): Stage-by-stage mapping of agents, artifacts, and gating checks.
  - [`architecture/views/sequence.md`](architecture/views/sequence.md): Execution sequence diagram extracted from real baseline run [44724438807](https://github.com/Ishaank1805/tinydb/actions/runs/44724438807).
  - [`architecture/decisions/README.md`](architecture/decisions/README.md): Master ADR index (ADR-001 through ADR-015), evolution narrative, and errata.
  - [`architecture/decisions/AUDIT.md`](architecture/decisions/AUDIT.md): Detailed verification matrix of ADR statements against repository code.
- **Experiment Kit & Protocols**:
  - [`experiment/campaign2.md`](experiment/campaign2.md): Campaign 2 protocol specification and replication methodology.
  - [`experiment/variants.md`](experiment/variants.md): Configuration differences across experimental variants.
  - [`experiment/issues/`](experiment/issues/): Benchmark issue specifications (Issues 1–5 plus adversarial `redteam_1`).
  - [`experiment/hidden_tests/`](experiment/hidden_tests/): Ground-truth acceptance test suites and reference fixes.
  - [`experiment/seeded_prs/`](experiment/seeded_prs/): 10 seeded evaluation pull requests: Dev set (`S1`–`S5`) and Held-out set (`S6`–`S10`).
- **Results & Evaluation Data**:
  - [`results/summary.md`](results/summary.md): Authoritative experimental summary generated by `collect_results.py`.
  - [`results/review_analysis.md`](results/review_analysis.md): Review error analysis generated by `analyze_reviews.py` across 30 defective reviews.
  - [`results/runs.md`](results/runs.md): Complete ledger of all 80 runs with direct GitHub Actions and PR links.
  - [`results/results.csv`](results/results.csv): Machine-readable tabular results.
  - [`results/fixes.md`](results/fixes.md): Complete changelog of harness fixes and design changes applied to the fork.
  - [`results/campaign2_report.md`](results/campaign2_report.md): In-depth synthesis of Campaign 2 findings.
  - [`results/figures/`](results/figures/): High-resolution evaluation charts (`stage_pass_rate.png`, `hidden_tests.png`, `seeded_reviews.png`, `tokens_per_run.png`).

---

## Headline Results

Every number below is derived strictly from real, auditable runs in [`results/summary.md`](results/summary.md) and [`results/review_analysis.md`](results/review_analysis.md):

- **Execution Totals**: **80 protocol runs** (27 full runs, 53 review runs), **21,668,554 tokens**, **$0.00 cost**.
- **D1 Architecture Experiment (Multi-Agent vs. Single-Agent)**:
  - Across both campaigns (5 runs per cell, 2 campaigns, total 10 runs per variant), both variants tied in final outcomes: both released 9/10 PRs and passed 36/40 hidden tests overall.
  - *Multi-Agent Baseline*: Solved all 5 issues in Campaign 2 with 100% hidden tests passed (20/20), releasing 5/5 green PRs and using an average of 629,641 tokens per run (456,700 in C1). It stopped once at Issue 3 requirements in C1 ([run 44733750726](https://github.com/Ishaank1805/tinydb/actions/runs/44733750726)).
  - *Single-Agent*: Achieved 100% hidden tests in C1 and 80% (16/20) in C2, stopping at Issue 2 requirements after 3 rejected specification submissions ([run 44919386414](https://github.com/Ishaank1805/tinydb/actions/runs/44919386414)), while averaging 675,261 tokens per run in C2 (1,001,233 in C1).
- **D8 Reviewer Experiment (Reviewer v1 vs. Reviewer v2)**:
  - *No False Alarms*: Zero false alarms across all 20 reviews of clean seeded PRs (100% precision, defined as the share of request-changes verdicts that were correct; 20/20 approved).
  - *Defect Detection*: On held-out PRs (S6–S10), Reviewer v2 caught 2/6 defects (33%) and Reviewer v1 caught 3/6 defects (50%), identifying defects in S7 (silent type wrapping) and S8 (cache invalidation on rename).
  - *Tool Adoption & Comparison Verification*: Reviewer v2 called `compare.sh` 15 times in 12 reviews of defective seeded PRs (8 of 12 reviews invoked it at least once). However, analysis of recorded transcripts in `results/review_analysis.md` reveals that all 15 calls were classified as "output not recognised" (0 recorded both halves in canonical harness format, 0 showed a confirmed difference between PR head and the pre-change baseline). Reviewers frequently wrote custom `compare.sh` wrappers via shell heredocs, encountered missing probe paths (e.g. `python3: can't open file .../scratch/test_probe.py`), or printed custom test headers rather than canonical delimiters (`=== PR head ===` / `=== before the change ===`). Because 0 calls recorded both halves cleanly, whether reviewer v2's before/after comparison worked can be confirmed only for calls with both halves recorded.
  - *Error Analysis*: Of 30 defective seeded reviews, 12 missed because probes never exposed the defect; 9 missed because a probe exposed the defect but the reviewer approved anyway (e.g. in S2 [run 44909885659](https://github.com/Ishaank1805/tinydb/actions/runs/44909885659) and [run 44835481627](https://github.com/Ishaank1805/tinydb/actions/runs/44835481627), the reviewers noted that subsequent updates for the same document were ignored and approved anyway); 5 caught without an exposing probe; 4 caught with an exposing probe; 0 reviews were left without a probe of their own.
- **Security & Red-Team Resilience**:
  - Across all 6 red-team runs, the gate stripped the 346-character malicious HTML comment injection with **100% reliability**.
  - Under the documentation-only plan policy (PR #23), run [44915278834](https://github.com/Ishaank1805/tinydb/actions/runs/44915278834) passed all gates, opening approved [PR #33](https://github.com/Ishaank1805/tinydb/pull/33).

---

## Repository Layout

```
.
├── README.md                          # Master documentation and submission overview
├── report.pdf                         # 8-page body technical report with appendices
├── report.pdf.json                    # Page count metadata (6 body pages, 8 total)
├── demo.mp4                           # Narrated demonstration video (237.6s, 4.4MB)
├── demo.mp4.json                      # Video metadata and edge-tts synthesis record
├── 2023114016_a3_AutoSE.txt           # Portal submission pointer file
├── architecture/
│   ├── decisions/                     # ADR-001 through ADR-015, AUDIT.md, README.md
│   └── views/                         # component.md, stage_map.md, sequence.md
├── demo/
│   └── storyboard.json                # 16-slide storyboard linking verified URLs
├── experiment/
│   ├── campaign2.md                   # Campaign 2 protocol and replication guide
│   ├── variants.md                    # Experimental variants documentation
│   ├── issues/                        # Benchmark issue fixtures (issues 1-5, redteam_1)
│   ├── hidden_tests/                  # Hidden acceptance test suites
│   ├── seeded_prs/                    # Seeded evaluation pull requests (S1-S10)
│   └── scripts/                       # collect_results.py, analyze_reviews.py, make_figures.py
├── report/
│   ├── report.md                      # Source markdown for the report
│   └── report_pages.json              # Report page split verification
├── results/
│   ├── summary.md                     # Aggregated experimental statistics
│   ├── review_analysis.md             # Review error analysis and probe outcomes
│   ├── runs.md                        # Complete ledger of all 80 runs with links
│   ├── results.csv                    # Raw run metrics
│   ├── fixes.md                       # Harness and configuration fixes log
│   ├── campaign2_report.md            # Detailed Campaign 2 narrative report
│   └── figures/                       # Evaluation charts (stage_pass_rate, hidden_tests, etc.)
└── workflow/                          # Mirrored fork harness (.github/ workflows, code, prompts)
```

---

## Use of AI

> **Use of AI.** AI was only used to generate the code.
