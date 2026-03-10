# GrantFlow Buyer One-Pager

## Positioning

GrantFlow is a proposal operations platform for institutional funding workflows. It is built for teams that need controlled drafting, structured review, and traceable outputs, not just text generation.

## Who This Is For

- Proposal and capture teams inside implementing organizations
- Grant consulting firms managing multi-review donor submissions
- Program and MEL teams producing donor-aligned draft packages

## Core Workflow Pain It Solves

Large proposal teams usually have:
- fragmented drafting in docs/slides/chat tools
- inconsistent donor structure across teams
- review chaos across comments, versions, and approvals
- weak traceability from claims to supporting references
- high operational risk near submission deadlines

GrantFlow addresses this by making drafting and review a controlled system with explicit state transitions and audit-friendly traces.

## What Is Real Today (Verified in Repo)

- API-first workflow engine with staged pipeline:
  - `discovery -> architect -> mel -> critic`
- Donor strategy routing with specialized strategies:
  - `usaid`, `eu`, `worldbank`, `giz`, `us_state_department`
- Human-in-the-loop controls:
  - checkpoint approval (`POST /hitl/approve`) and resume (`POST /resume/{job_id}`)
- Traceability endpoints:
  - citations, versions, events, quality, review workflow views
- Export path:
  - `GET /status/{job_id}/export-payload` + `POST /export`
  - outputs: `.docx`, `.xlsx`, or ZIP
- Demo and sample artifacts:
  - Reviewer Console: `GET /demo`
  - sample exports in `docs/samples/`
  - pilot pack snapshots in `docs/pilot_runs/2026-02-27/`

## What This Is Not

- Not a grant chatbot
- Not a generic fundraising AI writer
- Not an automated donor submission system

Final compliance decisions remain human-owned.

## Why Teams Choose This Over Generic AI Tooling

Generic AI tools optimize for text speed. Proposal organizations optimize for delivery control and review quality.

GrantFlow provides:
- workflow governance (stage transitions, HITL pause/resume)
- structured findings workflow (severity/status/remediation metadata)
- traceability for reviewer and audit contexts
- reusable API workflows for internal proposal operations tooling

## Pilot Model (Practical)

Scope a pilot to 2-3 donors and 5-10 representative cases.

Use `docs/pilot-evaluation-checklist.md` as the default pilot execution and acceptance template.

Pilot acceptance signals:
- lower time-to-first-reviewable draft
- fewer review loop cycles to terminal status
- higher traceability coverage in citations/versions/events
- predictable export package quality for reviewer handoff

## Commercial Fit

Strong fit for organizations that run high-volume, high-stakes institutional proposals and need repeatable workflow infrastructure rather than ad-hoc drafting.
