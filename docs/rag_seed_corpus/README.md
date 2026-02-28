# Seed RAG Corpus (Demo / Eval Grounding)

This folder contains generated PDF seed documents for GrantFlow demo presets and LLM grounded eval experiments.

Important
- These are seed/reference documents created for retrieval and workflow testing.
- Replace with official donor/country/agency documents for production use.

## Included presets
- `usaid_gov_ai_kazakhstan`
- `eu_digital_governance_moldova`
- `worldbank_public_sector_uzbekistan`
- `giz_sme_resilience_jordan`
- `state_department_media_georgia`

## Ingest
Use `docs/rag_seed_corpus/ingest_manifest.jsonl` to upload files via `POST /ingest`.

Example (one file):
```bash
curl -s -X POST http://127.0.0.1:8000/ingest \
  -H "X-API-Key: <KEY>" \
  -F donor_id=usaid \
  -F metadata_json='{"source_type":"donor_guidance","doc_family":"donor_policy"}' \
  -F file=@docs/rag_seed_corpus/usaid/01_usaid_donor_policy_ads_program_cycle_seed.pdf
```

## Suggested first grounded eval
Load seed files for all specialized donors, then run `LLM Eval (Grounded)` with donor filters:
`usaid,eu,worldbank,giz,state_department`.

## Local grounded benchmark (API)
Run a quick local benchmark across all specialized donor presets after ingest:

```bash
python3 docs/rag_seed_corpus/local_grounded_benchmark.py --api-base http://127.0.0.1:8000 --llm-mode
```

Optional:
- add `--api-key <KEY>` if API auth is enabled
- limit donors with `--donors usaid` or `--donors usaid,eu`
- write raw results with `--json-out /tmp/grounded-benchmark.json`
