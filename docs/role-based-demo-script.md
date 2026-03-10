# Role-Based Demo Script

This script is for internal pilot calls where different roles are present in the same meeting.

Use it to explain GrantFlow in role language, not just system language.

## Demo Goal

Show that GrantFlow is a proposal operations platform:
- not a grant chatbot
- not generic AI writing
- but a controlled draft-review-export workflow for serious proposal teams

## Recommended Audience Mix

- one leader or decision-maker
- one proposal manager
- one program or technical lead
- one MEL or results specialist
- one reviewer or practice lead

## Opening Positioning

Use this opening:

> GrantFlow is not trying to replace proposal teams with text generation.  
> It is trying to make proposal work more controllable, more reviewable, and less chaotic under donor pressure.

## 5-7 Minute Role-Based Demo

### 1. Director view

Say:

> For leadership, the value is not "better text."  
> The value is seeing whether the package is actually progressing, what is still open, and where risk is accumulating.

Show:
- `/status/{job_id}`
- `/status/{job_id}/quality`
- `/status/{job_id}/review/workflow`

Emphasize:
- policy status
- go/no-go
- next operational action
- HITL checkpoints if enabled

### 2. Proposal manager view

Say:

> For the proposal manager, the value is workflow control: the current stage, open findings, open comments, queue burden, and export readiness.

Show:
- `GET /demo`
- critic findings block
- review comments block
- action queue summary
- batch preview/apply controls

Emphasize:
- controlled progression
- fewer "send me the latest version" loops
- visible review queues instead of email chaos

### 3. Program lead view

Say:

> For the technical lead, the value is starting from a structured donor-shaped draft instead of a blank page.

Show:
- ToC snapshot in buyer artifacts
- structured objectives / outcomes in exported files

Reference:
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack-6d-buyer/buyer-brief.md`
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/executive-pack-6d-buyer/README.md`

Emphasize:
- structured first draft
- donor-shaped sections
- reviewable logic before narrative polishing

### 4. MEL specialist view

Say:

> For MEL, the value is that indicators, ownership, and verification logic are generated as part of the workflow, not bolted on at the end.

Show:
- LogFrame snapshot in buyer artifacts
- exported `.xlsx`

Emphasize:
- baseline / target
- formula
- owner
- means of verification

### 5. Reviewer view

Say:

> For reviewers, the key value is structured review work: severity, section, status, next action, and comment queues.

Show:
- `/status/{job_id}/critic`
- `/status/{job_id}/review/workflow`
- Demo Console `Suggested Ops Actions`

Emphasize:
- findings as entities
- comments as workflow
- next action, not just problem lists

### 6. Operations / submission view

Say:

> For operations, the value is a working export package in familiar formats, with less last-minute manual assembly.

Show:
- `GET /status/{job_id}/export-payload`
- `POST /export`
- resulting `.docx`, `.xlsx`, ZIP

Emphasize:
- review package
- send classification
- downstream submission readiness

## Suggested Talk Track By Role

### If leadership is skeptical

Say:

> You should evaluate this as a control layer for proposal preparation, not as an AI writer.

### If the proposal manager is skeptical

Say:

> The main question is whether this reduces review chaos and version drift, not whether every sentence is perfect on first pass.

### If the program lead is skeptical

Say:

> Treat the system as a structured first draft and review scaffold, not as a replacement for technical judgment.

### If MEL is skeptical

Say:

> The test is whether the generated LogFrame gets you to a reviewable starting point faster, not whether it removes MEL work entirely.

### If reviewers are skeptical

Say:

> The value is that review becomes trackable and prioritizable instead of being scattered across channels.

## Honest Caveats To State

- Final donor compliance sign-off remains human-owned.
- Grounding quality depends on the available donor corpus.
- Some pilot evidence is still illustrative rather than measured.
- The strongest current value is workflow control plus reviewable draft artifacts.

## Closing

Use this close:

> If you pilot this, the test is simple: do you get to a reviewable donor-shaped package faster, with less review chaos and better visibility into risk?
