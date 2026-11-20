# Sequence view (one real run)

This view comes from a real baseline run on issue #2 (issue_1), chosen for demonstration.

Run: [44724438807](https://github.com/Ishaank1805/tinydb/actions/runs/44724438807)

```mermaid
sequenceDiagram
  autonumber
  actor M as Maintainer
  participant G as Gate job
  participant H as Harness (orchestrator, checks)
  participant P as Planner agent
  participant I as Implementer agent
  participant T as Test-author agent
  participant C as CI workflow
  participant R as Reviewer agent (own job)
  actor U as Human
  M->>G: full on  2 (baseline)
  G->>H: sanitised issue snapshot
  H->>P: requirements (round 0) 
  P-->>H: submit for the requirements check
  Note over H: requirements check passed
  H->>P: design (round 0) 
  P-->>H: submit for the design check
  Note over H: design check failed
  P-->>H: submit for the design check
  Note over H: design check passed
  H->>I: implementation (round 0) attempt 1/3
  I-->>H: submit for the implementation check
  Note over H: implementation check passed
  H->>T: testing (round 0) 
  T-->>H: submit for the testing check
  Note over H: testing check passed
  H->>H: release (round 0) 
  Note over H: commit and push, open or update the PR
  H->>C: workflow_dispatch on the PR branch
  C-->>H: success
  H->>R: review round 1 (issue + diff + repo only)
  R-->>H: approve target none
  H->>U: ✅ the independent reviewer approved - PR 13
```
