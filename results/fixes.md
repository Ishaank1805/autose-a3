# Fixes made during setup and runs

Every change to the provided code or configuration after it was first installed. Configuration placeholders (OWNER, model IDs for your provider) are listed too.

| Date | What failed (link) | Change (PR/commit) | Why |
|---|---|---|---|
| 2026-11-20 | Configuration setup | [commit 8a315ce](https://github.com/Ishaank1805/autose-a3/commit/8a315ce) | Filled `OWNER/tinydb` with `Ishaank1805/tinydb` in config and ADRs |
| 2026-11-20 | Doctor run [44722135182](https://github.com/Ishaank1805/tinydb/actions/runs/44722135182) | [PR #1](https://github.com/Ishaank1805/tinydb/pull/1) | Added `-o addopts=` to pytest invocation in `doctor.py` to prevent picking up root `pytest.ini` coverage arguments |
| 2026-11-20 | `open_seeded_prs.py` | Local script fix | Changed `gh pr edit` to `gh issue edit` for adding labels to avoid deprecated GitHub GraphQL Projects (classic) query error |
| 2026-11-20 | `autopilot.py` `GH.run` | Local script fix | Added transient network retry with backoff in `GH.run` to handle intermittent connection drops |
| 2026-11-20 | Build run reporting | [PR #22](https://github.com/Ishaank1805/tinydb/pull/22) | Expose `stopped_stage` and `stopped_reason` from build workflow to report job in `autose-build.yml` and `report.py` |
