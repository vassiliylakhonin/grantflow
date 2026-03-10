# KATCH Evaluation RFQ Pilot Execution Checklist

Use this checklist for a bounded pilot or live response run against the KATCH-style evaluation RFQ workflow in GrantFlow.

## Pilot Scope

- Proposal mode: `evaluation_rfq`
- RFQ profile: `katch_final_assessment`
- Primary donor track: `un_agencies`
- Core output path:
  - technical response backbone
  - compliance matrix
  - key personnel and CV readiness
  - financial companion
  - submission package checklist
  - attachment manifest
  - annex packer ZIP artifacts

## Success Criteria

- faster time to first reviewable technical draft
- fewer review loops before a submission-ready technical package
- fewer duplicate or conflicting comments across technical, MEL, compliance, and leadership review
- stronger methodology completeness against RFQ requirements
- cleaner submission package readiness with fewer missing annexes or package gaps

## Before First Live Run

### 1. Source Package Preparation

Confirm the working folder for the RFQ includes:
- RFQ / solicitation PDF
- annexes / appendices
- submission instructions
- existing concept or technical notes
- team CV references and staffing notes
- internal past performance references
- budget or pricing assumptions notes

### 2. Corpus Preparation

Ingest the RFQ package into a dedicated namespace before drafting.

Minimum recommended corpus:
- RFQ PDF
- appendices / annexes
- any evaluation criteria or scoring notes
- historical evaluation proposal examples if allowed
- prior evaluation reports or sample outputs if allowed

Definition of ready:
- RFQ ingested successfully
- appendices ingested successfully
- at least one donor/policy or reference source present
- retrieval namespace confirmed in preflight

### 3. Workflow Roles

Assign at minimum:
- pilot owner
- operator
- technical reviewer
- MEL / evaluation methods reviewer
- finance / compliance reviewer
- approver
- ingest owner

### 4. First-Run Controls

Before generating the first draft, confirm:
- `proposal_mode=evaluation_rfq`
- `rfq_profile=katch_final_assessment`
- evaluation questions are present
- methods list is present
- team roles are present
- deliverables are present
- LLM / deterministic mode choice is explicit

## First Live Run

### Operator

- run the RFQ case
- capture `status`, `quality`, `critic`, `citations`, and `export-payload`
- export `docx`, `xlsx`, and `both`
- confirm ZIP contains:
  - `proposal.docx`
  - `mel.xlsx`
  - `annex_packer/annex_manifest.json`
  - `annex_packer/submission_readiness.md`
  - `submission_package/`

### Technical Reviewer

Check whether the draft covers:
- assignment background
- evaluation purpose
- evaluation questions matrix
- methods coverage matrix
- deliverables schedule table
- team composition
- key personnel and CV readiness

### Compliance / Submission Reviewer

Check whether the package covers:
- procurement compliance matrix
- submission package checklist
- attachment manifest
- financial companion summary
- top readiness gap from `submission_package_readiness`

## Required Runtime Evidence

Save per case:
- `status.json`
- `quality.json`
- `critic.json`
- `citations.json`
- `export-payload.json`
- `toc-review-package.docx`
- `logframe-review-package.xlsx`
- ZIP export

## Exit Gate For First RFQ Cycle

Classify one of:
- `continue`
- `continue_with_conditions`
- `hold`

Use `hold` only if one of these remains true:
- fatal critic flaws remain open
- submission package readiness is not `ready` or `partial`
- exact RFQ sections are missing from the technical proposal backbone
- annex/package structure cannot support submission handoff
