# Sequence view (one real run)

This view must come from a real run. Every AutoSE run produces `sequence.mmd`
in its `autose-run-summary` artifact, generated from the event logs of all jobs
(`autose/report.py`), and also shows it in the run's summary page.

1. Pick the run you show in the demo video (from `results/runs.md`).
2. `gh run download <run-id> --repo <you>/tinydb --name autose-run-summary`
3. Paste the contents of `sequence.mmd` below, inside a mermaid code block, and add the run link.

Run: _(link)_

_(paste the generated diagram here)_
