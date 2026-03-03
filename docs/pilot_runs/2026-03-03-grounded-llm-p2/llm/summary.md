# Pilot Validation Pack — llm

Generated at: 2026-03-03T06:04:29.180253+00:00

## Scope
- Mode: `llm_mode=true` (grounded via default architect retrieval)
- Donors: `usaid`, `state_department`
- Source benchmark: `benchmark-results.json`

## Benchmark Summary

| Donor | Job ID | Quality | Critic | Retrieval hits | Citations | Fallback NS | RAG low | Conf avg | Threshold hit | Readiness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| usaid | `6d2e5c7c-4deb-4970-a63d-da295edca06f` | 9.25 | 9.25 | 3 | 18 | 0 | 0 | 0.5571 | 1.0 | 4/4 |
| state_department | `91c5e14f-97ef-419c-8e89-6fa233b5416c` | 9.25 | 9.25 | 3 | 10 | 0 | 0 | 0.5297 | 1.0 | 4/4 |

## Files
- `usaid/status.json`, `usaid/quality.json`, `usaid/critic.json`, `usaid/citations.json`
- `usaid/export-payload.json`, `usaid/review-package.zip`, `usaid/toc-review-package.docx`, `usaid/logframe-review-package.xlsx`
- `state_department/status.json`, `state_department/quality.json`, `state_department/critic.json`, `state_department/citations.json`
- `state_department/export-payload.json`, `state_department/review-package.zip`, `state_department/toc-review-package.docx`, `state_department/logframe-review-package.xlsx`

## Notes
- These runs are sanitized pilot snapshots and not final donor submissions.
- Grounding quality remains corpus-dependent; inspect per-donor `quality.json` and `citations.json`.
