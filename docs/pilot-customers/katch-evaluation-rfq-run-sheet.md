# KATCH Evaluation RFQ Run Sheet

Use this sheet for the first live KATCH-style RFQ response run in GrantFlow.

## Run Intent

- Case ID: `KATCH-RFQ-01`
- Proposal mode: `evaluation_rfq`
- RFQ profile: `katch_final_assessment`
- Donor track: `un_agencies`
- Goal: produce a grounded, reviewable technical response package with exportable annex-control artifacts

## Required Inputs Before Generate

### 1. Source RFQ Package

Confirm the working source package contains:
- RFQ / solicitation PDF
- annexes / appendices
- submission instructions
- any evaluation criteria or scoring guidance
- any internal notes on expected team composition, LOE, or pricing assumptions

### 2. Ingest Readiness

The RFQ should already be ingested into the live namespace used for the run.

Minimum live readiness checks:
- namespace is not empty
- RFQ PDF is present in corpus
- appendices are present if available
- preflight shows retrieval enabled

Recommended verification:
- `GET /ready`
- `GET /ingest/inventory?donor_id=un_agencies`

### 3. Workflow Roles

Assign at minimum:
- pilot owner
- operator
- technical reviewer
- MEL / evaluation methods reviewer
- finance / compliance reviewer
- approver
- ingest owner

## Recommended `input_context`

Use this as the minimum live payload shape.

```json
{
  "project": "Kyrgyzstan final performance evaluation for youth employability and resilience programming",
  "country": "Kyrgyzstan",
  "organization_name": "KATCH",
  "rfq_title": "Project Performance Evaluation",
  "proposal_mode": "evaluation_rfq",
  "rfq_profile": "katch_final_assessment",
  "assignment_summary": "Independent final performance evaluation for a youth employability and resilience project in Kyrgyzstan.",
  "evaluation_purpose": "Assess project performance, outcomes, and lessons learned for future programming and accountability.",
  "evaluation_questions": [
    "To what extent did the project achieve intended youth employability outcomes?",
    "What implementation factors most influenced performance and adaptation?",
    "What lessons should inform future programme design and donor reporting?"
  ],
  "methods": [
    "Outcome Harvesting",
    "Social Media Analysis",
    "Focus group discussions",
    "Survey of beneficiaries"
  ],
  "deliverables": [
    "Inception Report",
    "Draft Evaluation Report",
    "Final Evaluation Report"
  ],
  "team_roles": [
    "Team Lead",
    "Evaluation Analyst",
    "Field Coordinator"
  ]
}
```

Notes:
- the KATCH profile backfills required deliverables automatically if the input only contains a partial list
- keeping the deliverables list short is acceptable for first-run validation
- if real staffing names or LOE are known, include them later in a second pass

## Recommended Generate Call

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "un_agencies",
    "input_context": {
      "project": "Kyrgyzstan final performance evaluation for youth employability and resilience programming",
      "country": "Kyrgyzstan",
      "organization_name": "KATCH",
      "rfq_title": "Project Performance Evaluation",
      "proposal_mode": "evaluation_rfq",
      "rfq_profile": "katch_final_assessment",
      "assignment_summary": "Independent final performance evaluation for a youth employability and resilience project in Kyrgyzstan.",
      "evaluation_purpose": "Assess project performance, outcomes, and lessons learned for future programming and accountability.",
      "evaluation_questions": [
        "To what extent did the project achieve intended youth employability outcomes?",
        "What implementation factors most influenced performance and adaptation?",
        "What lessons should inform future programme design and donor reporting?"
      ],
      "methods": [
        "Outcome Harvesting",
        "Social Media Analysis",
        "Focus group discussions",
        "Survey of beneficiaries"
      ],
      "deliverables": [
        "Inception Report",
        "Draft Evaluation Report",
        "Final Evaluation Report"
      ],
      "team_roles": [
        "Team Lead",
        "Evaluation Analyst",
        "Field Coordinator"
      ]
    },
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

## Minimum Evidence To Save

After the run completes, save:
- `status.json`
- `quality.json`
- `critic.json`
- `citations.json`
- `export-payload.json`
- `proposal.docx`
- `mel.xlsx`
- ZIP export with:
  - `annex_packer/annex_manifest.json`
  - `annex_packer/submission_readiness.md`
  - `submission_package/`

## What Reviewers Should Check

### Technical Reviewer

Confirm the package includes:
- assignment background
- evaluation purpose
- evaluation questions matrix
- methods coverage matrix
- deliverables schedule table
- workplan summary

### Compliance / Submission Reviewer

Confirm the package includes:
- procurement compliance matrix
- submission package checklist
- attachment manifest
- financial companion summary
- top readiness gap from `submission_package_readiness`

### Approver

Confirm:
- package is reviewable without rebuilding the structure manually
- package readiness is at least `partial`, ideally `ready`
- no fatal RFQ completeness flaw remains

## Expected Good First-Run Output

Treat the run as strong if all of the following are true:
- `quality_score >= 8`
- `critic_score >= 8`
- `fatal_flaw_count = 0`
- `architect grounded citation rate = 1`
- `mel grounded citation rate = 1`
- `submission_package_readiness.readiness_status = ready` or `partial`
- ZIP includes annex-packer artifacts and `submission_package/`

## Most Likely First-Run Gaps

If the run is weak, the most likely causes are:
- RFQ or appendices not fully ingested
- methods or evaluation questions too thin in input
- staffing or annex readiness under-specified
- package/control layer present but evidence grounding is still weak

## First Decision After Run

Choose one:
- `continue`
- `continue_with_conditions`
- `hold`

Use `hold` only if:
- fatal critic flaws remain
- submission package readiness is `weak` or `missing`
- core RFQ sections are still absent from the technical response
