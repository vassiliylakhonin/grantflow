# Pilot Kickoff Agenda

Use this for the first working session with a pilot customer.

Target duration:
- `45-60 minutes`

Goal:
- leave the meeting with a named pilot owner, operator, reviewer, approver, ingest admin, pilot scope, and first success criteria

Related documents:
- `docs/pilot-day1-checklist.md`
- `docs/pilot-role-mapping-worksheet.md`
- `docs/pilot-role-mapping-example.md`
- `docs/pilot-evaluation-checklist.md`
- `docs/role-based-demo-script.md`

## Who Should Attend

Minimum:
- pilot owner
- primary operator
- primary reviewer
- approver

Strongly recommended:
- ingest admin or knowledge manager
- one program or MEL lead

Do not run kickoff with only technical staff. The pilot will drift without workflow owners.

## Pre-Read To Send Before The Meeting

Send these in advance:
- `docs/buyer-one-pager.md`
- `docs/pilot-user-roles.md`
- `docs/pilot-role-mapping-example.md`

If the customer is security-sensitive, also send:
- `docs/enterprise-access-layer.md`

## Agenda

### 1. Frame The Pilot

Time:
- `5 minutes`

Decide:
- why this pilot exists
- which workflow pain is in scope
- what is explicitly out of scope

Prompt:
- Which part of proposal work hurts most today: first draft time, review chaos, weak traceability, or final packaging?

## 2. Confirm Pilot Roles

Time:
- `10 minutes`

Open:
- `docs/pilot-role-mapping-worksheet.md`

Decide:
- who is pilot owner
- who is operator
- who is reviewer
- who is approver
- who is ingest admin

Exit condition:
- one named person per role

## 3. Confirm Pilot Cases

Time:
- `10 minutes`

Decide:
- which donors are in scope
- how many cases are in scope
- which cases are representative enough to judge value

Recommended first pilot:
- `2-3` donors
- `3-6` cases

Avoid:
- "everything current in the pipeline"
- cases with no source material at all

## 4. Confirm Access And Deployment Model

Time:
- `5 minutes`

Open:
- `docs/pilot-day1-checklist.md`
- `docs/enterprise-access-layer.md`

Decide:
- where the stack will run
- who owns `.env.pilot`
- whether gateway/SSO fronting is needed for the pilot

Exit condition:
- one agreed deployment pattern

## 5. Confirm Success Criteria

Time:
- `10 minutes`

Open:
- `docs/pilot-evaluation-checklist.md`

Decide:
- what counts as a successful pilot
- what evidence will be considered credible
- what metrics matter most

Minimum success criteria should include:
- reviewable draft produced
- exporter package usable
- reviewer workflow understandable
- grounding acceptable for in-scope donors

## 6. Confirm Baseline Capture

Time:
- `10 minutes`

Decide:
- who fills baseline data
- which cases will have measured baseline
- when baseline will be captured

Minimum baseline for each selected case:
- time to first reviewable draft
- time to terminal review-ready state
- review loops

If no one owns this, the pilot will stay anecdotal.

## 7. Confirm First Demo And First Review Cycle

Time:
- `5 minutes`

Decide:
- first demo date
- first live case date
- first reviewer checkpoint date
- first pilot check-in date

## What To Show During Kickoff

Keep the live walkthrough short.

Recommended artifacts:
- `build/executive-pack-6d-buyer/README.md`
- `build/pilot-evidence-pack-6d-buyer/README.md`
- `build/pilot-pack-6d-buyer/buyer-brief.md`

If the customer wants process detail:
- open `/demo`
- show queue/review workflow
- show one export package

Do not try to explain every route in kickoff.

## Decisions To Record Before Ending The Meeting

Write these down before the call ends:
- pilot owner
- operator
- reviewer
- approver
- ingest admin
- selected donors
- selected cases
- deployment owner
- baseline owner
- pilot success criteria
- first demo date
- first check-in date

## Fast Post-Meeting Follow-Up

Send within the same day:
- completed role mapping
- agreed pilot scope
- agreed first case list
- agreed baseline owner
- agreed first next step

If that follow-up is late, pilot momentum usually drops immediately.
