# Kazakhstan NGO Pilot Role Mapping

Customer:
- Kazakhstan NGO pilot

## Assigned Role Map

| GrantFlow role | Customer name | Team/title | Primary responsibilities | Needed access | Backup person | Assigned? |
| --- | --- | --- | --- | --- | --- | --- |
| Pilot owner | Timur | Head of Programs | pilot success criteria, scope decisions, escalation point | portfolio + packs | Aidana | yes |
| Operator | Ruslan | Grants / Proposal Manager | run drafts, coordinate deadlines, export packages, manage working state | generate/export/review-read | Program Officer | yes |
| Reviewer | Zhanna | MEL Lead | MEL / LogFrame review, findings/comments triage | review read/write | Technical Lead | yes |
| Reviewer | Asel | Finance & Compliance reviewer | compliance and budget-side review, blocker flagging | review read/write | Finance delegate | yes |
| Approver | Aidana | Executive Director | checkpoint release, continue/hold decisions | HITL approve/resume | Board Liaison | yes |
| Ingest admin | Ruslan | Grants / Proposal Manager | donor docs, past proposals, context data, evaluations | ingest/inventory | Program Officer | yes |

## Review Pattern

Primary review sequence recommended for this account:

1. Operator assembles case and triggers draft
2. MEL reviewer checks results logic and indicators
3. Finance / compliance reviewer checks late-stage risk earlier than current practice
4. Approver handles continue / hold decisions at defined checkpoints

## Specific Note For This Account

The customer already identified a current failure mode:
- finance / compliance enters too late

Pilot design implication:
- include finance / compliance review earlier than in current workflow
- do not wait until the package is "almost final"

## Baseline Ownership

Measured baseline owner:
- Ruslan

Support:
- Zhanna for MEL rework counts and quality notes

## Go-Live Trigger

First live case:
- `2026-03-16`

Do not start before:
- the measured baseline template is populated for the selected three cases
- donor/source corpus is loaded for `un_agencies`, `eu`, and `usaid`
