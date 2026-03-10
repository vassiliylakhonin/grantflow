# Pilot Evaluation Checklist

Use this checklist to run a structured GrantFlow pilot with measurable outcomes.

## 1) Pilot Scope Definition

- Choose 2-3 target donors (at least one specialized strategy donor).
- Select 5-10 representative proposal cases.
- Define pilot window (for example, 2-4 weeks).
- Define team roles:
  - draft operator
  - reviewer/compliance lead
  - pilot owner

## 2) Baseline Capture (Before Pilot)

For each case, capture current-state metrics:
- time from intake to first reviewable draft
- review loop count to “submission-ready”
- major compliance/rework issues found in review
- number of artifact handoff steps (ToC, LogFrame, MEL, comments, versions)

Operational workflow:
- generate `baseline-fill-template.csv` from the current pilot pack
- save the completed measured sheet as `measured-baseline.csv`
- record `baseline_method`, `baseline_source`, `baseline_confidence`, `baseline_owner`, and `baseline_capture_date`
- re-run `make pilot-metrics` and `make pilot-scorecard`

## 3) Pilot Execution (During Pilot)

For each case:
- run generation (`/generate` or `/generate/from-preset`)
- collect traceability outputs:
  - `/status/{job_id}/quality`
  - `/status/{job_id}/critic`
  - `/status/{job_id}/citations`
  - `/status/{job_id}/versions`
  - `/status/{job_id}/events`
- if HITL is in scope, record approve/resume path:
  - `/hitl/approve`
  - `/resume/{job_id}`
- export package:
  - `/status/{job_id}/export-payload`
  - `/export`

## 4) Pilot Success Criteria

Define thresholds before pilot start. Suggested default targets:
- `>=20%` faster time-to-first-reviewable draft vs baseline
- fewer review loops to reach terminal draft status
- consistent traceability package available per case (citations/versions/events)
- export package usable without manual artifact reconstruction

## 5) Risk and Trust Checks

- confirm environment posture:
  - `/health` diagnostics
  - `/ready` status and checks
- confirm storage/runner topology matches intended mode
- confirm API key and tenant controls are configured per pilot policy

## 6) Pilot Evidence Pack (Deliver to Stakeholders)

- pilot summary table with baseline vs pilot deltas
- 2-3 representative case packets:
  - status
  - quality
  - critic findings
  - citations
  - export artifacts (`.docx`, `.xlsx`, ZIP)
- explicit list of unresolved blockers and required product changes

## 7) Go / No-Go Decision

Go if:
- measurable cycle-time or review-efficiency gains are demonstrated
- reviewers trust traceability and output structure
- ops posture is stable in chosen runtime mode

No-Go / Extend if:
- gains are inconclusive
- output quality depends on unresolved corpus/process issues
- review/governance controls do not map to operating model
