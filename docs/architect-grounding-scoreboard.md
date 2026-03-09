# Architect Grounding Scoreboard

This is a compact live verification summary for architect-stage grounding in the Docker runtime. It is a targeted spot-check, not blanket proof for all presets or all corpora.

Verified on `March 9, 2026` against live namespaces after reseeding Chroma.

| Donor | Case | Namespace | Hits | Candidate Hits | Citation Type | Evidence Signals |
| --- | --- | --- | ---: | ---: | --- | --- |
| `usaid` | `usaid_gov_ai_kazakhstan` | `usaid_ads201` | `3` | `22` | `rag_claim_support` | `USAID donor guidance evidence` |
| `eu` | `eu_digital_governance_moldova` | `eu_intpa` | `3` | `23` | `rag_claim_support` | `EU donor guidance evidence`, `intervention-logic evidence` |
| `worldbank` | `worldbank_public_sector_uzbekistan` | `worldbank_ads301` | `3` | `19` | `rag_claim_support` | `World Bank implementation evidence` |
| `giz` | `giz_sme_resilience_ukraine` | `giz_guidance` | `3` | `6` | `rag_claim_support` | `GIZ delivery evidence`, `sustainability and partner-validation evidence` |
| `state_department` | `state_department_media_georgia` | `us_state_department_guidance` | `3` | `4` | `rag_claim_support` | `State Department program evidence` |
| `un_agencies` | `generic_un_agencies_education_nepal` | `un_agencies_guidance` | `3` | `4` | `rag_claim_support` | `retrieved donor evidence` |

## Evidence Paths

- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/live-architect-signals-check-nohitl`
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/live-architect-signals-gsu-rerun`

## Reproduce

```bash
make dev-runtime-refresh
make seed-live-corpus LIVE_API_BASE=http://127.0.0.1:8000 LIVE_SEED_DONORS=usaid,eu,worldbank,giz,state_department,un_agencies
```

Then rerun targeted architect checks through the live API. The verified output directories above contain the saved `status.json`, `quality.json`, `citations.json`, and export artifacts used for this summary.
