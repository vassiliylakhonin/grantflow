# Pilot Validation Pack — deterministic

Generated at: 2026-03-03T06:04:28.860275+00:00

## Scope
- Mode: `llm_mode=true` (grounded via default architect retrieval)
- Donors: `usaid`, `state_department`
- Source benchmark: `benchmark-results.json`

## Benchmark Summary

| Donor | Job ID | Quality | Critic | Retrieval hits | Citations | Fallback NS | RAG low | Conf avg | Threshold hit | Readiness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| usaid | `2bd47a59-492a-4b20-8b75-8bd66d1ffec0` | 9.25 | 9.25 | 3 | 18 | 0 | 0 | 0.5571 | 1.0 | 4/4 |
| state_department | `518a6032-1966-480e-9527-b245d2b80ec9` | 9.25 | 9.25 | 3 | 10 | 0 | 0 | 0.5297 | 1.0 | 4/4 |

## Files
- `usaid/status.json`, `usaid/quality.json`, `usaid/critic.json`, `usaid/citations.json`
- `usaid/export-payload.json`, `usaid/review-package.zip`, `usaid/toc-review-package.docx`, `usaid/logframe-review-package.xlsx`
- `state_department/status.json`, `state_department/quality.json`, `state_department/critic.json`, `state_department/citations.json`
- `state_department/export-payload.json`, `state_department/review-package.zip`, `state_department/toc-review-package.docx`, `state_department/logframe-review-package.xlsx`

## Notes
- These runs are sanitized pilot snapshots and not final donor submissions.
- Grounding quality remains corpus-dependent; inspect per-donor `quality.json` and `citations.json`.
