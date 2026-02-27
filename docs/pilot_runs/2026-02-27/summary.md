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

## QA Findings (compact)

### P1 — Citation source paths are not reviewer-friendly
- Scope: all donors (`usaid`, `eu`, `worldbank`)
- Symptom: `citations.json` and exports show temp filesystem paths in `source` (for example `/var/folders/.../grantflow_ingest_*.pdf`) rather than stable human-readable document names.
- Why it matters: traceability is harder to validate in real review workflows and exported artifacts.
- Suggested fix: persist/display original upload filename (and optional logical source title) in citation metadata at ingest time; keep temp path internal only.

### P2 — EU citations include mixed support/low-confidence records for the same statement path
- Scope: `eu`
- Symptom: `toc.overall_objective.title` and `toc.overall_objective.rationale` each have both `rag_claim_support` and `rag_low_confidence` entries.
- Why it matters: contradictory evidence signals inflate citation counts and make quality interpretation noisy.
- Suggested fix: per-claim citation consolidation (select best evidence per `statement_path`), then emit one canonical citation record per claim.

### P2 — World Bank has low average citation confidence despite `rag_low=0`
- Scope: `worldbank`
- Symptom: many `rag_claim_support` records are at `citation_confidence=0.25`; `architect_threshold_hit_rate=1.0` is achieved because thresholds are relaxed for these claims.
- Why it matters: quality signals can look stronger than underlying confidence suggests.
- Suggested fix: report a separate metric for `low_confidence_claim_support_count` (or tighten confidence floor for claim support labels) so confidence and support are not conflated.

### P3 — Review comments sheet absent in pilot exports
- Scope: all donors (this pack)
- Symptom: `.xlsx` files include `LogFrame`, `Citations`, `Critic Findings` sheets, but no `Review Comments` sheet.
- Why it matters: not a product bug in this run, but a reviewer may interpret it as missing feature if comments were expected.
- Suggested fix: for pilot demonstrations, add at least one comment per run (or note explicitly in summary that `review_comments=0`).

## Recommended next fix order
1. P1 source-name traceability fix (highest impact on reviewer trust)
2. P2 EU per-claim citation consolidation
3. P2 World Bank confidence/support metric split
