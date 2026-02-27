# Pilot Validation Pack — 2026-02-27

Generated at: 2026-02-27T03:23:55.535658+00:00

## Scope
- Mode: `llm_mode=true` (grounded via default architect retrieval)
- Donors: `usaid`, `eu`, `worldbank`
- Corpus: seeded donor/context corpus (`docs/rag_seed_corpus`)

## Benchmark Summary

| Donor | Job ID | Quality | Critic | Retrieval hits | Citations | Fallback NS | RAG low | Conf avg | Threshold hit | Readiness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| usaid | `b58cdba5-a12c-4a8a-898e-04a7501d49f0` | 8.5 | 8.5 | 3 | 8 | 0 | 1 | 0.6266 | 0.8 | 4/4 |
| eu | `3b811b56-2381-4286-9873-011f0356084e` | 8.5 | 8.5 | 3 | 7 | 0 | 2 | 0.5951 | 0.5 | 4/4 |
| worldbank | `521b1728-df21-4d67-b52a-8f1f4dd572b0` | 8.5 | 8.5 | 3 | 13 | 0 | 0 | 0.3769 | 1.0 | 4/4 |

## Files
- `usaid/status.json`, `usaid/quality.json`, `usaid/critic.json`, `usaid/citations.json`
- `usaid/export-payload.json`, `usaid/review-package.zip`, `usaid/toc-review-package.docx`, `usaid/logframe-review-package.xlsx`
- `eu/status.json`, `eu/quality.json`, `eu/critic.json`, `eu/citations.json`
- `eu/export-payload.json`, `eu/review-package.zip`, `eu/toc-review-package.docx`, `eu/logframe-review-package.xlsx`
- `worldbank/status.json`, `worldbank/quality.json`, `worldbank/critic.json`, `worldbank/citations.json`
- `worldbank/export-payload.json`, `worldbank/review-package.zip`, `worldbank/toc-review-package.docx`, `worldbank/logframe-review-package.xlsx`

## Notes
- These runs are sanitized pilot snapshots and not final donor submissions.
- Grounding quality remains corpus-dependent; use `quality.json` and `citations.json` for case-level inspection.
