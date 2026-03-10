# Pilot Role Mapping Worksheet

Use this worksheet before a bounded GrantFlow pilot to map customer-side people to the operating roles the current product expects.

This is not in-app RBAC. It is a pilot planning aid that should line up with the gateway/policy model in `/Users/vassiliylakhonin/Documents/aidgraph-prod/docs/enterprise-access-layer.md`.

## Goal

Before day 1 of the pilot, decide:
- who can run drafts
- who can review and triage findings/comments
- who can approve HITL checkpoints
- who can ingest donor/source material
- who owns pilot success metrics

If this stays vague, the pilot usually turns into shared inbox chaos.

## GrantFlow Pilot Roles

### Pilot Owner

Use for:
- overall pilot success criteria
- go/no-go decisions
- escalation point for blocked reviews

Usually maps to:
- proposal operations lead
- digital transformation lead
- PMO/program delivery lead

Should have access to:
- read-only portfolio views
- executive packs
- pilot evidence pack

### Operator

Use for:
- running `generate`
- managing draft iterations
- exporting review packages
- assembling the current working state

Usually maps to:
- proposal manager
- bid manager
- grants manager

Should have access to:
- `POST /generate`
- `POST /generate/from-preset`
- `POST /export`
- read-only status/review views

### Reviewer

Use for:
- triaging critic findings
- adding/acknowledging/resolving comments
- deciding whether a draft is review-ready

Usually maps to:
- technical lead
- sector lead
- MEL lead
- external proposal reviewer

Should have access to:
- `GET /status/*`
- `GET /portfolio/*`
- review mutation routes
- `/demo` review workflow tools if used

### Approver

Use for:
- HITL checkpoint decisions
- formal continue/hold decisions at architect or MEL checkpoints

Usually maps to:
- proposal director
- capture director
- designated approval authority

Should have access to:
- reviewer routes
- `POST /hitl/approve`
- `POST /resume/{job_id}`

### Ingest Admin

Use for:
- corpus upload
- namespace inventory checks
- donor evidence readiness

Usually maps to:
- knowledge manager
- research lead
- platform operator

Should have access to:
- `/ingest*`
- readiness and inventory endpoints

## Customer Mapping Table

Fill this before the pilot starts.

| GrantFlow role | Customer name | Team/title | Primary responsibilities | Needed access | Backup person | Assigned? |
| --- | --- | --- | --- | --- | --- | --- |
| Pilot owner |  |  |  | portfolio + packs |  |  |
| Operator |  |  |  | generate/export/review-read |  |  |
| Reviewer |  |  |  | review read/write |  |  |
| Approver |  |  |  | HITL approve/resume |  |  |
| Ingest admin |  |  |  | ingest/inventory |  |  |

## Minimum Pilot Team

For a credible bounded pilot, do not start with fewer than:
- `1` pilot owner
- `1` operator
- `1` reviewer
- `1` approver

`Ingest admin` can be shared with operator for a very small pilot, but only if donor corpus prep is light.

## Route Family Mapping

Use this when configuring gateway or reverse-proxy policy.

| Route family | Viewer | Operator | Reviewer | Approver | Ingest admin |
| --- | --- | --- | --- | --- | --- |
| `/health`, `/ready`, `/status/*`, `/portfolio/*` | yes | yes | yes | yes | yes |
| `/generate*`, `/export`, `/cancel/*` | no | yes | no | optional | no |
| `/status/{job_id}/critic/*` | read | read | write | write | no |
| `/status/{job_id}/comments*` | read | optional | write | write | no |
| `/status/{job_id}/review/workflow*` | read | read | read/write | read/write | no |
| `/hitl/approve`, `/resume/*` | no | no | optional | yes | no |
| `/ingest*` | no | optional | no | no | yes |

## Pilot Readiness Questions

Ask these before kickoff:
- Who owns the decision that a case is worth pursuing?
- Who is allowed to trigger a new draft run?
- Who resolves content disagreements when reviewer comments conflict?
- Who approves an HITL checkpoint?
- Who loads donor/source documents into the grounding namespace?
- Who owns baseline capture for pilot metrics?

If more than one answer is "everyone", the pilot role model is not ready.

## Recommended Day-1 Assignment

For a first pilot, keep it narrow:
- one operator
- one primary reviewer
- one approver
- one ingest admin
- one pilot owner

Expand only after the workflow is stable.

## Output To Keep

Save the completed worksheet alongside pilot docs, for example:
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack/customer-role-mapping.md`
- or in the customer's internal pilot folder

This becomes the reference when access, ownership, or queue responsibility gets confused.
