# Component view

What the implementation consists of and how the parts call each other. The code is in the fork under `.github/` (copy in `workflow/`).

```mermaid
flowchart LR
  M((Maintainer)) -->|"label autose / comment /autose"| ISS["Issue"]
  subgraph RUN["autose.yml (one Actions run per trigger)"]
    G["Gate job (no LLM)<br/>trigger, permission, sanitised snapshot"]
    subgraph BJ["Build / rework job (contents, PR, issues, actions: write)"]
      O["Orchestrator<br/>state machine, budgets"]
      PL["Planner agent<br/>stages 1-2"]
      JD["Judge model<br/>testability"]
      IM["Implementer agent<br/>stage 3"]
      TA["Test-author agent<br/>stage 4"]
      CK["Deterministic checks<br/>AST, pytest JUnit, fail-to-pass,<br/>path policy, build"]
      RL["Release step (no LLM)<br/>commit, push, PR, CI"]
    end
    subgraph RJ["Review job (contents: read, PR: write, actions: read)"]
      PRE["Prepare (read-only token)"]
      DF["Harness Diff-Facts & Base Rebuild<br/>(AST diff facts, pre-change tree, compare.sh)"]
      RA["Reviewer agent v2 (no token)<br/>differential probes, checklist"]
      PG["Probe Evidence Gate<br/>approval requires ran probe"]
      POST["Post review (COMMENT)"]
    end
    REP["Report job"]
  end
  ISS --> G -->|"issue snapshot artifact"| O
  O --> PL & IM & TA
  PL -.-> JD
  O --> CK
  O --> RL -->|"push autose/issue-N"| PR["Pull request"]
  RL -->|"workflow_dispatch"| CI["ci.yml"]
  PR --> PRE --> DF --> RA --> PG --> POST --> PR
  POST -.->|"request_changes + target stage<br/>(next rework job)"| O
  REP -->|"final summary, labels"| ISS
  H((Human)) -->|"merge or close"| PR
```

## Agents, tools and permissions

| Component | Model (default) | Tools | May write | GitHub token |
|---|---|---|---|---|
| Gate | none | GitHub REST | status comment, labels | job token, step env |
| Planner (stages 1-2) | gemini-3.5-flash-lite | list_files, read_file, search_code, run_command, read_skill_file / read_artifact, submit_spec, cannot_specify, submit_design, cannot_design | nothing (work tree reset after each session) | none |
| Judge | gemini-3.1-flash-lite | none | nothing | none |
| Implementer (stage 3) | gemini-3.5-flash-lite | read tools, write_file, edit_file, run_command, read_artifact, finish_implementation, request_redesign, dispute_test | `tinydb/**`, `docs/**`, `README.rst` | none |
| Test author (stage 4) | gemini-3.1-flash-lite | read tools, write_file, edit_file, run_command, read_artifact, submit_tests | only `tests/test_issue_<N>.py` | none |
| Orchestrator + checks + release | none | git, pytest, GitHub REST | commits on `autose/*` branches, PR, CI dispatch | in memory, from a deleted file |
| Reviewer v2 (stage 6) | gemini-3.1-flash-lite | read tools, run_command, write_file/edit_file (scratch only), get_diff, submit_review | `scratch/` outside the repo | none (job token is read-only) |
| Report | none | GitHub REST | status comment, labels | job token |

## Reviewer v2 Architecture

Reviewer v2 (introduced in PR #25 and codified in ADR-013) augments the independent review stage with differential verification capabilities:

1. **AST Diff-Facts (`difffacts.py`)**: The harness parses the PR diff using Python's AST to compute objective facts injected directly into the reviewer's initial prompt:
   - Functions and classes added, modified, or removed by the diff.
   - Existing test cases altered or removed by the change.
   - Any touched functions in the implementation that were not referenced in the PR description or issue.
2. **Pre-Change Code Rebuild (`difffacts.py::build_base_tree`)**: Rebuilds the exact repository state immediately prior to the change into a scratch directory outside the checkout using reverse patch application (`git apply -R`), hardened against parent git repositories (PR #37).
3. **Differential Probing (`compare.sh`)**: The harness provides `$SCRATCH/compare.sh <probe_script.py>`, which executes the probe against both the pre-change code tree and the PR head, outputting a side-by-side diff of behaviors and return values.
4. **Mandatory Probe Evidence Gate**: The harness strictly rejects an `approve` verdict if the reviewer has not executed at least one probe script, ensuring claims of correctness are empirically tested rather than assumed.

Enforcement points (code): `autose/tools.py` (path policy), `autose/sandbox.py` (scrubbed environment, deny rules, timeouts), `autose/stages/__init__.py::enforce` (reverts out-of-policy changes made by any means), `autose/secretstore.py` (credentials from files that are deleted before agents start), `autose/difffacts.py` (AST facts, base tree rebuild, and probe runner), job-level `permissions:` in the workflow files.
