# Kazakhstan NGO Live Launch Memo

Date:
- `2026-03-16`

Status:
- live launch complete
- all pre-live requirements completed
- no organizational or technical blockers at launch

## Executive Summary

The GrantFlow pilot has fully completed preparation and has successfully entered live operation across three donor tracks:
- `un_agencies`
- `eu`
- `usaid`

All required conditions were met before launch:
- corpus upload and validation
- source files completeness
- case folder readiness
- workflow policy activation
- baseline capture
- KPI monitoring activation

Current launch status:
- `live_status = ACTIVE`
- `final_readiness_gate = PASSED`

## Case Status

| Case ID | Donor | Corpus Upload | Validation | Source Files Complete | Folder Ready | Workflow Ready | Live |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CASE-UN-01` | `un_agencies` | yes | yes | yes | yes | yes | yes |
| `CASE-EU-01` | `eu` | yes | yes | yes | yes | yes | yes |
| `CASE-USAID-01` | `usaid` | yes | yes | yes | yes | yes | yes |

## Final Contract Status

```json
{
  "contract_id": "grantflow-pilot-2026-q1",
  "corpus_status": {
    "un_agencies": "VALIDATED",
    "eu": "VALIDATED",
    "usaid": "VALIDATED"
  },
  "live_status": "ACTIVE",
  "final_readiness_gate": "PASSED",
  "updated_at": "2026-03-16"
}
```

## Baseline Locked At Start

- `CASE-UN-01`: `46h / 132h / loops=4 / reviewers=7 / MEL rewrites=2`
- `CASE-EU-01`: `58h / 176h / loops=5 / reviewers=9 / MEL rewrites=3`
- `CASE-USAID-01`: `64h / 214h / loops=6 / reviewers=11 / MEL rewrites=4`

## KPI Monitoring Active

Tracked in live phase:
- `time_to_first_reviewable_draft_hours`
- `time_to_final_package_hours`
- `review_loops`
- `active_reviewers`
- `major_mel_rewrites_after_r2`

Success thresholds:
- `>=25%` faster first reviewable draft
- `>=1` fewer review loop
- `>=20%` faster final package
- cleaner comments and findings
- fewer major MEL rewrites after `R2`

## Ready-To-Send Texts

### For leadership

The pilot is live and on plan. All pre-live requirements have been completed across three donor tracks (UN, EU, USAID). Corpus validation, source completeness, workflow activation, and KPI monitoring are all in place. No launch blockers remain.

### For the technical / operating team

Readiness gate is PASS across all three cases. Workflow policy is active, corpus is validated, source files are complete, and case folders are ready. The pilot now moves into regular KPI collection and reporting through `R1` and `R2` review cycles.

### For an external partner

We confirm successful launch of the GrantFlow live pilot across three donor tracks (UN, EU, USAID). Corpus preparation and validation are complete, source materials are complete by case, and the review workflow is structured and active. Interim KPI results against baseline will be shared after the first full review cycle.
