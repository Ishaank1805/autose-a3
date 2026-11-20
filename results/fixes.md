# Fixes made during setup and runs

Every change to the provided code or configuration after it was first installed. Configuration placeholders (OWNER, model IDs for your provider) are listed too.

| Date | What failed (link) | Change (PR/commit) | Why |
|---|---|---|---|
| 2026-11-20 | Configuration setup | [commit 8a315ce](https://github.com/Ishaank1805/autose-a3/commit/8a315ce) | Filled `OWNER/tinydb` with `Ishaank1805/tinydb` in config and ADRs |
| 2026-11-20 | Doctor run [44722135182](https://github.com/Ishaank1805/tinydb/actions/runs/44722135182) | [PR #1](https://github.com/Ishaank1805/tinydb/pull/1) | Added `-o addopts=` to pytest invocation in `doctor.py` to prevent picking up root `pytest.ini` coverage arguments |
| 2026-11-20 | `open_seeded_prs.py` | Local script fix | Changed `gh pr edit` to `gh issue edit` for adding labels to avoid deprecated GitHub GraphQL Projects (classic) query error |
| 2026-11-20 | `autopilot.py` `GH.run` | Local script fix | Added transient network retry with backoff in `GH.run` to handle intermittent connection drops |
| 2026-11-20 | Build run reporting | [PR #22](https://github.com/Ishaank1805/tinydb/pull/22) | Expose `stopped_stage` and `stopped_reason` from build workflow to report job in `autose-build.yml` and `report.py` |
| 2026-11-20 | Red-team run [44741723040](https://github.com/Ishaank1805/tinydb/actions/runs/44741723040) | [PR #23](https://github.com/Ishaank1805/tinydb/pull/23) | Design change after the experiments (not a defect): let documentation-only plans pass the design check, reset documentation files in fail-to-pass probe, and record workflow commit in run summaries |
| 2026-11-20 | Confirmation run [44790093537](https://github.com/Ishaank1805/tinydb/actions/runs/44790093537) | [PR #24](https://github.com/Ishaank1805/tinydb/pull/24) | Design change after confirmation run 44751912678 hit the 55-minute budget (not a defect) |
| 2026-11-21 | Reviewer smoke run [44829639910](https://github.com/Ishaank1805/tinydb/actions/runs/44829639910) | [PR #31](https://github.com/Ishaank1805/tinydb/pull/31) | `compare.sh` did not handle leading `python`/`python3` argument or probe scripts passed with `scratch/` prefix |
| 2026-11-21 | Reviewer run [44832255390](https://github.com/Ishaank1805/tinydb/actions/runs/44832255390) | [PR #32](https://github.com/Ishaank1805/tinydb/pull/32) | Rewrite relative `scratch/` paths to `$SCRATCH` in command handler and accept `scratch/` probe markers in review evidence gate |
