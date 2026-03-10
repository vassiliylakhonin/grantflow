# Five-Minute Demo

Use this path when you need to explain GrantFlow quickly to a buyer, partner, or technical evaluator.

## Demo Goal

Show that GrantFlow is a proposal operations platform, not a grant chatbot.

The proof points are:
- structured first draft
- reviewer workflow and approval control
- traceability and grounding
- export-ready handoff artifacts

## What To Open

1. `GET /demo` (`Reviewer Console`)
2. `docs/buyer-one-pager.md`
3. `build/release-demo-bundle-6d-buyer/grantflow-demo-bundle-6d-buyer.zip` if a local bundle is available

## Five-Minute Narrative

### Minute 1: Positioning

Use this line:

`GrantFlow is a proposal operations platform for high-stakes donor workflows. It helps teams move from raw concept to reviewable draft package with workflow control, traceability, and export-ready outputs.`

### Minute 2: Generate A Draft

Show:
- `POST /generate/from-preset`
- or the generate controls in `GET /demo`

Explain:
- `discovery -> architect -> mel -> critic`
- output is structured, not just free text

### Minute 3: Show Review Control

In `GET /demo`, show:
- findings and comments
- next primary action
- queue counters
- pause/approve/resume if relevant

Explain:
- the value is lower review chaos and cleaner ownership, not just faster text generation

### Minute 4: Show Traceability

Show:
- `GET /status/{job_id}/citations`
- `GET /status/{job_id}/versions`
- `GET /status/{job_id}/review/workflow`

Explain:
- claims, revisions, and review state are inspectable
- this is why the system is useful for serious proposal teams

### Minute 5: Show Export And Production Boundary

Show:
- `GET /status/{job_id}/export-payload`
- `POST /export`
- `.docx`, `.xlsx`, ZIP

Then state the boundary clearly:
- GrantFlow controls drafting, review, and export
- final donor compliance sign-off stays human-owned

## Best Demo Cases

Use these when available:
- `usaid_gov_ai_kazakhstan`
- `eu_digital_governance_moldova`
- `worldbank_public_sector_uzbekistan`
- `un_agencies_katch_evaluation_kyrgyzstan` for evaluation RFQ mode

## What Not To Claim

Do not say:
- it fully automates proposal writing
- it replaces human compliance review
- it is already a full enterprise IAM product
- it fully automates procurement submissions end-to-end
