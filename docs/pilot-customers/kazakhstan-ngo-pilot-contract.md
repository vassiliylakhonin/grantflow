# Kazakhstan NGO Pilot Contract

This document is the fixed working contract for the first Kazakhstan NGO pilot wave.

Current state:
- live phase active
- final readiness gate passed
- all three donor tracks validated
- first `R2` checkpoint completed
- all three cases reached `FINAL_PACKAGE_READY`
- pilot validated with conditions; `USAID` remains the weakest coordination path

## 1. Pilot Scope

- Pilot donors:
  - `un_agencies`
  - `eu`
  - `usaid`
- Pilot cases:
  - `CASE-UN-01` — Youth Employability Concept Note
  - `CASE-EU-01` — Community Resilience Full Proposal
  - `CASE-USAID-01` — Health Systems Strengthening Concept + Annexes
- First live case date:
  - `2026-03-16`
- Timezone:
  - `Asia/Almaty`
- Live status:
  - `ACTIVE`
- Final readiness gate:
  - `PASSED`

## 2. Measured Baseline

Captured on:
- `2026-03-10`

### CASE-UN-01

- donor track: `un_agencies`
- time to first reviewable draft: `46h`
- time to final package: `132h`
- review loops: `4`
- active reviewers: `7`
- major MEL rewrites after `R2`: `2`
- source: `GDocs history + Slack/Email review threads + task tracker + owner interview`
- confidence: `Medium`

### CASE-EU-01

- donor track: `eu`
- time to first reviewable draft: `58h`
- time to final package: `176h`
- review loops: `5`
- active reviewers: `9`
- major MEL rewrites after `R2`: `3`
- source: `Version history + Track Changes + review log + MEL/Finance debrief`
- confidence: `Medium-High`

### CASE-USAID-01

- donor track: `usaid`
- time to first reviewable draft: `64h`
- time to final package: `214h`
- review loops: `6`
- active reviewers: `11`
- major MEL rewrites after `R2`: `4`
- source: `Approval chain + compliance iterations + file timestamps + retrospective`
- confidence: `Medium`

## 3. Corpus Readiness Requirements

Final corpus state:
- `un_agencies` — `VALIDATED`
- `eu` — `VALIDATED`
- `usaid` — `VALIDATED`

Readiness targets used before go-live:
- `un_agencies` by `2026-03-13`
- `eu` by `2026-03-13`
- `usaid` by `2026-03-14`

Definition of ready:
- donor guidelines + templates loaded
- MEL / LogFrame requirements loaded
- compliance / budget constraints loaded
- at least one historical reference package if available
- validator assigned
- `validated=true`

## 4. Review Workflow Policy

### UN agencies

- `R1`:
  - owner
  - operator
  - technical reviewer
  - MEL reviewer
- `R2`:
  - finance / compliance reviewer
  - approver

### EU

- `R1`:
  - owner
  - operator
  - technical reviewer
  - MEL reviewer
- `R2`:
  - finance / compliance reviewer
  - approver

### USAID

- `R1`:
  - owner
  - operator
  - technical reviewer
  - MEL reviewer
  - finance / compliance reviewer
- `R2`:
  - approver

## 5. Required Source Files

Each case must reach `source_files_complete=true` before live run.

Minimum required files:
- donor call docs / NOFO / guidelines
- official templates
- existing drafts / concept notes
- historical proposals if available
- MEL / LogFrame artifacts
- budget / compliance references
- review artifacts: comments, Track Changes, decision emails, or notes

File handling rule:
- no spaces or Cyrillic in filenames
- use date-based versioning in names: `YYYYMMDD`
- do not use `v1`, `v2`, or `final`

Final status:
- source files complete for all three cases
- donor/source files received
- validator confirmation received
- uploader owner confirmed
- working folders and backup ZIPs received

## 6. Case Folder Structure

```text
/pilot
  /CASE-UN-01
    /01_input
    /02_corpus
    /03_drafts
    /04_reviews
    /05_approvals
    /06_exports
  /CASE-EU-01
  /CASE-USAID-01
```

## 7. Status Gates

Each case must move in order:

1. `NOT_READY`
2. `CORPUS_READY`
3. `WORKFLOW_CONFIRMED`
4. `SOURCE_FILES_COMPLETE`
5. `LIVE`
6. `R1_COMPLETE`
7. `R2_COMPLETE`
8. `FINAL_PACKAGE_READY`

Current case status at closeout:
- `CASE-UN-01` -> `FINAL_PACKAGE_READY`
- `CASE-EU-01` -> `FINAL_PACKAGE_READY`
- `CASE-USAID-01` -> `FINAL_PACKAGE_READY`

## 8. Success Criteria

- time to first reviewable draft reduction: `>=25%`
- review loops reduction: `>=1`
- time to final package reduction: `>=20%`
- comment quality: fewer duplicate/conflicting comments
- MEL quality: fewer major rewrites after `R2`

## 9. Operational Rule

Do not classify the pilot as successful from text quality alone.

Success must be evidenced in:
- cycle-time reduction
- review-loop reduction
- cleaner comment flow
- reduced MEL rework
- cleaner export package readiness

## 10. Launch Readout

Launch readout as of `2026-03-16`:

- pre-live requirements completed
- workflow policy active
- KPI monitoring active
- organizational and technical blockers: none

## 11. First R2 Readout

Readout as of `2026-03-22`:

### CASE-UN-01
- donor track: `un_agencies`
- time to first reviewable draft: `32h`
- time to final package: `109h`
- review loops: `3`
- active reviewers: `6`
- major MEL rewrites after `R2`: `1`
- duplicate/conflicting comments: `3`
- decision: `continue`

### CASE-EU-01
- donor track: `eu`
- time to first reviewable draft: `42h`
- time to final package: `149h`
- review loops: `4`
- active reviewers: `8`
- major MEL rewrites after `R2`: `1`
- duplicate/conflicting comments: `6`
- decision: `continue`

### CASE-USAID-01
- donor track: `usaid`
- time to first reviewable draft: `52h`
- time to final package: `186h`
- review loops: `5`
- active reviewers: `9`
- major MEL rewrites after `R2`: `2`
- duplicate/conflicting comments: `8`
- decision: `continue_with_conditions`

Pilot interpretation:
- `UN` and `EU` progressed through `R2` without extra intervention and remain on target
- `USAID` improved after corrective actions, but still carries the highest coordination load and stays under conditions
- overall pilot direction remains positive and should continue

## 12. Closeout Readout

Readout as of `2026-03-27`:

- `CASE-UN-01` closed strongly and can be used as an external proof path
- `CASE-EU-01` closed strongly and confirms value on a full proposal workflow
- `CASE-USAID-01` reached final package materially faster than baseline, but should remain under conditions for broader rollout claims

Closeout decision:
- `continue_with_conditions`

Pilot interpretation:
- strongest proof donor paths: `un_agencies`, `eu`
- remaining weak donor path: `usaid`
- overall pilot hypothesis confirmed, with clearer proof on UN/EU than on USAID
