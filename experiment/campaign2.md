# Campaign 2: reviewer v2 against the first campaign's reviewer, on a held-out set

## Why

In campaign 1 the independent reviewer approved all three defective seeded PRs (S2, S3, S4); with the implementer's rationale it caught one of three. The suite was green on every seeded PR, so a reviewer that only reruns the author's tests cannot catch these defects.

## What changed (design-change PR in the fork)

Reviewer v2 keeps the same model (`gemini-3.1-flash-lite`) and the same independence (issue, diff and repository at the PR head only; no implementer context; no GitHub token):

- **Facts from the diff.** Before the reviewer starts, the harness lists the functions the diff changes, adds or removes (by comparing ASTs), the existing tests it edits, and changed functions the issue text never names. These are computed, not claimed by anyone.
- **The code before the change, rebuilt from the diff.** The harness copies the PR head and reverse-applies the PR diff, so no other commit is checked out and the reviewer still sees only the diff and the head. `bash $SCRATCH/compare.sh probe.py` runs one of the reviewer's probe scripts on both versions.
- **Probe before approving.** The evidence gate now also requires at least one probe of the reviewer's own, on top of its own passing test run.
- **Prompt.** Differential probing: every difference in behaviour between the two versions must be one the issue asks for; an edited existing test is a blocker unless the issue requires it.

## How it is measured

| | |
|---|---|
| Variants | `baseline` = reviewer v2; `reviewer-v1` = campaign 1's reviewer (old prompt, no facts, no pre-change code, no probe requirement), same model. v1 runs on account A's quota and v2 on account B's; the account does not change the model. |
| Dev set | S1–S5, used in campaign 1 and known while v2 was designed. Results here may flatter v2. |
| Held-out set | S6–S10, written after v2, with kinds of defect that do not occur in S1–S5. This is the fair comparison. |
| Repeats | Every (seeded PR, variant) pair is reviewed twice: all pairs once, then all pairs again. |
| Also | The red-team issue three times on the final workflow (documentation-only plans, 80-minute budget, reviewer v2); optionally one more D1 repetition (baseline vs single-agent) on the five issues. |

Tables in `results/summary.md` label every group as `variant · campaign` (`c1`, `c2`; `manual` = the two confirmation runs outside the plan).

## Held-out seeded PRs

| PR | Issue | Expected | Planted defect (not mentioned in the PR description) |
|---|---|---|---|
| S6 | issue_2 | approve | none: minimal correct fix plus a regression test |
| S7 | issue_4 | request changes | requirement violated: a non-list field is silently wrapped in a list instead of raising `TypeError`; the PR's own test enshrines it |
| S8 | issue_3 | request changes | stale cache: cached table instances are not dropped after a rename |
| S9 | issue_5 | request changes | out-of-scope behaviour change: `Document` equality starts comparing `doc_id` |
| S10 | issue_3 | approve | none: complete fix with tests (including caching) and docs |

Validation against the pinned commit (`validate_seeded_prs.py`):

| PR | Suite | Hidden tests | Defect present |
|---|---|---|---|
| S6 | 230/230 | 4/4 | no |
| S7 | 234/234 | 3/4 | yes |
| S8 | 234/234 | 3/4 | yes |
| S9 | 230/230 | 4/4 | yes |
| S10 | 236/236 | 4/4 | no |

The rebuilt pre-change code was checked to be identical to the pinned commit for all ten seeded PRs.
