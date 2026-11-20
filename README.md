# AutoSE: issue in, tested and reviewed pull request out (Assignment 3)

| | |
|---|---|
| Fork | https://github.com/Ishaank1805/tinydb |
| Pinned upstream commit | `msiemens/tinydb@edff96aeb2616402e9489d46e90a592c05565621` |
| Workflow | `.github/workflows/autose.yml` in the fork (copy in [`workflow/`](workflow/)) |
| Models | Gemini API free tier. Planner and implementer: `gemini-3.5-flash-lite` · test author, reviewer and testability judge: `gemini-3.1-flash-lite` on two team members' Google accounts: the build roles on one, the reviewer and the single-agent variant on the other (see `autose.config.yml`) |
| Report | [`report.pdf`](report.pdf) |
| Demo video | DEMO-LINK |

## How to trigger the workflow

People with write access to the fork can:

- add the label **`autose`** to an issue, or comment **`/autose`** on it: full pipeline (requirements, design, implementation, testing, release, independent review, up to two rework rounds);
- comment **`/autose review #<issue>`** on an open pull request: one independent review of its current head;
- add `variant=<name>` to either command for the decision experiments ([`experiment/variants.md`](experiment/variants.md));
- or start **Actions → AutoSE → Run workflow** with the same inputs.

**Actions → AutoSE doctor** checks the configuration, secrets, model access and repository settings. The workflow never merges: a person decides.

## Repository layout

```
README.md            this file
report.pdf
architecture/views/  component view, sequence view (from a real run), stage map
architecture/decisions/  ADR-001.md ... (Nygard format; superseded ones kept)
workflow/            copy of the fork's .github/ (workflows, agent code, prompts, config)
experiment/issues/   the five issue texts (+ optional red-team issue)
experiment/hidden_tests/  hidden acceptance tests and the reference fixes that validate them
experiment/seeded_prs/    five reviewer-check PRs: diffs, descriptions, ground truth
experiment/variants.md    what each decision-experiment variant changes
results/results.csv  one row per run
results/runs.md      links to every Actions run, PR and review
```

## Results and token usage

See [`results/summary.md`](results/summary.md) (stage pass rates, the decision experiments side by side, hidden tests, reviewer accuracy and consistency, tokens by role, the prompt-injection check), [`results/runs.md`](results/runs.md) (every run, PR, review and CI run) and [`results/figures/`](results/figures/). Total tokens used: 8,512,395 (estimated cost $0.00).

## AI assistance (course policy)

> DRAFT: check every sentence and rewrite it so that it is true for your team before submitting.

The workflow code, agent prompts, configuration, experiment kit (issue texts, hidden tests, seeded PRs, scripts) and the component view and stage map were generated with Claude (Anthropic); the architecture was designed by the assistant together with the code. Setup, runs and result collection were carried out with Google Antigravity following `ANTIGRAVITY_PROMPT.md`; every change it made to the provided code is listed in `results/fixes.md`. We reviewed the generated code and documents.
