# Pilot Validation Pack — 2026-02-27-p1-source-fix

Generated at: 2026-02-27T03:40:57.862133+00:00

## Scope
- Mode: `llm_mode=false` (grounded via default architect retrieval)
- Donors: `usaid`, `eu`, `worldbank`
- Source benchmark: `benchmark-results.json`

## Benchmark Summary

| Donor | Job ID | Quality | Critic | Retrieval hits | Citations | Fallback NS | RAG low | Conf avg | Threshold hit | Readiness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| usaid | `8e5c269e-5ad4-4c26-b02b-89abb040a53e` | 9.25 | 9.25 | 0 | 16 | 16 | 0 | 0.1 | 0.0 | 0/4 |
| eu | `82921e84-fba3-4dfa-a271-ac921a0f7839` | 9.25 | 9.25 | 3 | 5 | 0 | 0 | 0.7467 | 1.0 | 4/4 |
| worldbank | `2ca278ba-f620-48bd-85cc-0a8747d50d86` | 9.25 | 9.25 | 3 | 7 | 0 | 0 | 0.5067 | 1.0 | 4/4 |

## Files
- `usaid/status.json`, `usaid/quality.json`, `usaid/critic.json`, `usaid/citations.json`
- `usaid/export-payload.json`, `usaid/review-package.zip`, `usaid/toc-review-package.docx`, `usaid/logframe-review-package.xlsx`
- `eu/status.json`, `eu/quality.json`, `eu/critic.json`, `eu/citations.json`
- `eu/export-payload.json`, `eu/review-package.zip`, `eu/toc-review-package.docx`, `eu/logframe-review-package.xlsx`
- `worldbank/status.json`, `worldbank/quality.json`, `worldbank/critic.json`, `worldbank/citations.json`
- `worldbank/export-payload.json`, `worldbank/review-package.zip`, `worldbank/toc-review-package.docx`, `worldbank/logframe-review-package.xlsx`

## Notes
- These runs are sanitized pilot snapshots and not final donor submissions.
- Grounding quality remains corpus-dependent; inspect per-donor `quality.json` and `citations.json`.
- P1 source-label check passed: `citations.source` and `citations.label` do not contain temp filesystem paths.
