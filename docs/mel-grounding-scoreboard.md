# MEL Grounding Scoreboard

This is a compact live verification summary for MEL-stage grounding in the Docker runtime. It is a targeted spot-check against the current live pilot pack, not blanket proof for every preset or donor path.

Verified on `March 9, 2026` from `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack/live-runs`.

| Donor | Case | Namespace | Retrieval Hits | Grounded Citations | Grounded Rate | Fallback Citations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `usaid` | `usaid_gov_ai_kazakhstan` | `usaid_ads201` | `3` | `3` | `1.0` | `0` |
| `eu` | `eu_digital_governance_moldova` | `eu_intpa` | `3` | `3` | `1.0` | `0` |
| `worldbank` | `worldbank_public_sector_uzbekistan` | `worldbank_ads301` | `3` | `3` | `1.0` | `0` |

## Evidence Path

- `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack/live-runs`

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
```

Then inspect `quality.json` for each live run and read:

- `mel.retrieval_hits_count`
- `citations.mel_retrieval_grounded_citation_count`
- `citations.mel_retrieval_grounded_citation_rate`
- `citations.mel_fallback_namespace_citation_count`
