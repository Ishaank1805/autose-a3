# Decision-experiment variants

Each variant is a named overlay in `.github/autose/autose.config.yml`. Choose the
two ADRs you want to test; the variants below are what the code supports. Full
runs of a variant get their own branch (`autose/issue-<N>-<variant>`) and PR, so
they never overwrite the baseline.

| Variant | What it changes | Decision it informs | How to run |
|---|---|---|---|
| `baseline` | nothing | reference | label `autose`, or `/autose` |
| `single-agent` | One shared agent session (`generalist`) does stages 1-4 instead of planner, implementer and test author; checks, release and reviewer are unchanged | D1 | `/autose variant=single-agent` on each of the five issues |
| `no-review-loop` | `max_change_requests: 0`: one review, no rework | D2 | `/autose variant=no-review-loop` on the issues |
| `reviewer-sees-rationale` | The reviewer also receives the implementer's `design.md` and `pr.md` (or, on seeded PRs, the persuasive PR description) | D8 / D3 | `/autose review #<issue> variant=reviewer-sees-rationale` on the seeded PRs (and/or full runs) |
| `reviewer-same-model` | The reviewer uses the implementer's model (`gemini-3.5-flash-lite`) instead of `gemini-3.1-flash-lite` | D6 | `/autose review #<issue> variant=reviewer-same-model` on the seeded PRs |

The autonomous prompt runs `single-agent` (D1) and `reviewer-sees-rationale` (D8) by default, through
`experiment/scripts/autopilot.py`. Each seeded-PR review is run twice (`REVIEW_REPEATS`) so the reviewer's
consistency can be measured, and the red-team issue is run once as prompt-injection evidence (`REDTEAM`).
The plan is ordered so that every prefix holds complete baseline/variant pairs: a smoke run, then the
reviewer experiment, then the full runs issue by issue. Change `EXPERIMENTS` in the prompt's Settings block to
test other decisions.

Model outputs vary between runs, so one run per cell is weak evidence. If the
budget allows, repeat each cell 2-3 times (comment the command again) and
report the spread. `results/summary.md` groups the numbers by variant.

Record here which two variants you ran, why, and anything you changed in the
design afterwards (that is your own analysis):

- Experiment 1: ...
- Experiment 2: ...
