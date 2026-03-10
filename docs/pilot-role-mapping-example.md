# Pilot Role Mapping Example

This is a filled starter example for a bounded GrantFlow pilot inside a large implementing organization or proposal consultancy.

Use it as a kickoff reference, then replace titles and names with the actual customer team.

Related:
- `docs/pilot-role-mapping-worksheet.md`
- `docs/enterprise-access-layer.md`

## Example Team Shape

Assumed pilot scope:
- `3-6` donor cases
- one shared proposal operations owner
- one day-to-day operator
- one primary reviewer
- one approval authority
- one corpus / knowledge owner

## Example Assignment

| GrantFlow role | Example customer title | What they actually do in the pilot | Needed access | Backup role |
| --- | --- | --- | --- | --- |
| Pilot owner | Director of Proposal Operations | Owns pilot scope, success criteria, and go/no-go at the end of the trial | portfolio views, executive pack, pilot evidence pack | PMO lead |
| Operator | Proposal Manager | Runs draft generation, refreshes cases, exports review packages, keeps pilot moving day to day | generate, export, review-read | Senior grants manager |
| Reviewer | Technical / Program Lead | Reviews ToC, logic, content quality, and donor fit; triages findings and comments | review read/write, comments, critic workflow | MEL lead |
| Approver | Capture Director or Country Director | Approves HITL checkpoints and decides whether a case proceeds after review | reviewer routes plus HITL approve/resume | Deputy director |
| Ingest admin | Knowledge Manager / Research Lead | Uploads donor documents, checks namespace inventory, owns grounding readiness | ingest and inventory routes | Platform operator |

## Example Working Agreement

### Pilot owner

Expected behavior:
- joins kickoff and weekly check-in
- does not operate daily review queues
- decides whether the pilot moves from evaluation to broader use

### Operator

Expected behavior:
- creates or refreshes runs
- tracks queue status
- assembles `pilot-pack`, `executive-pack`, and evidence bundles
- escalates when review queues stall

### Reviewer

Expected behavior:
- acknowledges or resolves findings/comments
- pushes content issues back to operator/program owner
- uses review queue and exported artifacts, not email sprawl

### Approver

Expected behavior:
- only steps in at explicit checkpoints
- can hold, resume, or redirect a case
- does not become the bottleneck for every minor comment

### Ingest admin

Expected behavior:
- validates that the donor namespace is usable before live pilot review
- owns donor/source document hygiene
- is responsible for explaining empty or weak grounding states

## Example Gateway Role Mapping

If the customer is fronting GrantFlow with an SSO/gateway layer, a practical first mapping looks like this:

| Customer group | GrantFlow pilot role | Access policy |
| --- | --- | --- |
| `proposal-ops-admins` | Pilot owner | read-only portfolio + bundle access |
| `proposal-ops-operators` | Operator | generate/export plus read review state |
| `proposal-reviewers` | Reviewer | review mutations and workflow reads |
| `proposal-approvers` | Approver | reviewer routes plus HITL approve/resume |
| `proposal-knowledge-admins` | Ingest admin | ingest and namespace inventory |

## Example Decision Model

Use this on day 1 so the pilot does not drift:

- Pilot owner decides:
  - whether the pilot is successful
  - whether to expand donor coverage
  - whether to move toward a paid or production pilot
- Operator decides:
  - which case gets refreshed next
  - when exports are ready for review
- Reviewer decides:
  - whether a draft is logically reviewable
  - which findings/comments should stay open
- Approver decides:
  - whether a paused case can continue
  - whether a case should be stopped or redirected
- Ingest admin decides:
  - whether the donor corpus is good enough for grounded runs

## Example Risks If Roles Are Not Assigned

- no single operator:
  - runs happen ad hoc and no one owns the current state
- no clear reviewer:
  - comments move back to Word/email and queue signals become meaningless
- no approver:
  - HITL checkpoints stall
- no ingest admin:
  - weak grounding gets blamed on the product instead of missing corpus
- no pilot owner:
  - no one owns final success criteria

## Recommended Day-1 Rule

For the first two weeks, do not assign multiple primary operators or multiple approval owners.

One primary person per role is the fastest path to a clean pilot signal.
