# MEL Grounding Scoreboard

This is a compact live verification summary for MEL-stage grounding in the Docker runtime. It combines the active live pilot pack with additional targeted donor spot-check runs, not blanket proof for every preset or donor path.

Verified on `March 9, 2026` from:

- `build/pilot-pack/live-runs`
- `build/live-architect-signals-gsu-rerun`

| Donor | Case | Namespace | Retrieval Hits | Grounded Citations | Grounded Rate | Fallback Citations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `usaid` | `usaid_gov_ai_kazakhstan` | `usaid_ads201` | `3` | `3` | `1.0` | `0` |
| `eu` | `eu_digital_governance_moldova` | `eu_intpa` | `3` | `3` | `1.0` | `0` |
| `worldbank` | `worldbank_public_sector_uzbekistan` | `worldbank_ads301` | `3` | `3` | `1.0` | `0` |
| `giz` | `giz_sme_resilience_ukraine` | `giz_guidance` | `3` | `3` | `1.0` | `0` |
| `state_department` | `state_department_media_georgia` | `us_state_department_guidance` | `1` | `3` | `1.0` | `0` |
| `un_agencies` | `generic_un_agencies_education_nepal` | `un_agencies_guidance` | `3` | `3` | `1.0` | `0` |

## Evidence Path

- `build/pilot-pack/live-runs`
- `build/live-architect-signals-gsu-rerun`

## Reproduce

```bash
make dev-runtime-refresh
make seed-live-corpus LIVE_API_BASE=http://127.0.0.1:8000 LIVE_SEED_DONORS=usaid,eu,worldbank
make pilot-refresh-fast \
  DEMO_PACK_API_BASE=http://127.0.0.1:8000 \
  DEMO_PACK_PRESET_KEYS=usaid_gov_ai_kazakhstan,eu_digital_governance_moldova,worldbank_public_sector_uzbekistan \
  DEMO_PACK_HITL_PRESET_KEY=usaid_gov_ai_kazakhstan \
  CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan \
  PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan

make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/grounded_cases.json \
  GROUNDED_TARGET_CASE_IDS="giz_sme_resilience_ukraine_grounded,state_department_media_georgia_grounded,generic_un_agencies_education_nepal_grounded"
```

Then inspect `quality.json` for each live run and read:

- `mel.retrieval_hits_count`
- `citations.mel_retrieval_grounded_citation_count`
- `citations.mel_retrieval_grounded_citation_rate`
- `citations.mel_fallback_namespace_citation_count`
