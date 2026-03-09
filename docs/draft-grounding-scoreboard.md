# Draft Grounding Scoreboard

This page combines the two main grounding layers in GrantFlow:

- `architect` grounding for Theory of Change / structured draft claims
- `mel` grounding for indicator and LogFrame evidence

It is a compact buyer/operator summary, not a blanket certification of all presets or all donor corpora.

Verified on `March 9, 2026`.

## Architect Stage

Architect live grounding is currently verified for six donor paths:

| Donor | Case | Namespace | Hits | Candidate Hits | Grounded Citation Type |
| --- | --- | --- | ---: | ---: | --- |
| `usaid` | `usaid_gov_ai_kazakhstan` | `usaid_ads201` | `3` | `22` | `rag_claim_support` |
| `eu` | `eu_digital_governance_moldova` | `eu_intpa` | `3` | `23` | `rag_claim_support` |
| `worldbank` | `worldbank_public_sector_uzbekistan` | `worldbank_ads301` | `3` | `19` | `rag_claim_support` |
| `giz` | `giz_sme_resilience_ukraine` | `giz_guidance` | `3` | `6` | `rag_claim_support` |
| `state_department` | `state_department_media_georgia` | `us_state_department_guidance` | `3` | `4` | `rag_claim_support` |
| `un_agencies` | `generic_un_agencies_education_nepal` | `un_agencies_guidance` | `3` | `4` | `rag_claim_support` |

Reference: `/Users/vassiliylakhonin/Documents/aidgraph-prod/docs/architect-grounding-scoreboard.md`

## MEL Stage

MEL live grounding is currently verified on the active buyer demo pilot pack:

| Donor | Case | Namespace | Retrieval Hits | Grounded Citations | Grounded Rate | Fallback Citations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `usaid` | `usaid_gov_ai_kazakhstan` | `usaid_ads201` | `3` | `3` | `1.0` | `0` |
| `eu` | `eu_digital_governance_moldova` | `eu_intpa` | `3` | `3` | `1.0` | `0` |
| `worldbank` | `worldbank_public_sector_uzbekistan` | `worldbank_ads301` | `3` | `3` | `1.0` | `0` |

Reference: `/Users/vassiliylakhonin/Documents/aidgraph-prod/docs/mel-grounding-scoreboard.md`

## Current Read

- Architect grounding is now verified across the six core donor paths used for demos and live checks.
- MEL grounding is verified on the current three-donor buyer demo pack.
- The current pilot artifacts surface both layers in:
  - `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack/pilot-metrics.md`
  - `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/pilot-pack/buyer-brief.md`
  - `/Users/vassiliylakhonin/Documents/aidgraph-prod/build/executive-pack/README.md`

## Reproduce

```bash
make dev-runtime-refresh
make seed-live-corpus LIVE_API_BASE=http://127.0.0.1:8000 LIVE_SEED_DONORS=usaid,eu,worldbank,giz,state_department,un_agencies
make pilot-refresh-fast \
  DEMO_PACK_API_BASE=http://127.0.0.1:8000 \
  DEMO_PACK_PRESET_KEYS=usaid_gov_ai_kazakhstan,eu_digital_governance_moldova,worldbank_public_sector_uzbekistan \
  DEMO_PACK_HITL_PRESET_KEY=usaid_gov_ai_kazakhstan \
  CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan \
  PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan
```
