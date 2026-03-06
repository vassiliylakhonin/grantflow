# Grounded Donor Scoreboard

As of March 6, 2026, the live Docker runtime (`grantflow_api` + Chroma) has been spot-checked with seeded donor corpus for the core donor paths below.

This is a targeted verification scoreboard, not a claim that every case in every suite is green.

## Verified Live Cases

| Donor | Case ID | Cases File | Result | Notes |
| --- | --- | --- | --- | --- |
| `usaid` | `usaid_ai_civil_service_kazakhstan_grounded` | `grantflow/eval/cases/grounded_cases.json` | PASS | `q=8.75`, `critic=8.75`, `citations=18`, `fallback_ns=0`, `non_retrieval=0` |
| `eu` | `eu_youth_employment_jordan_grounded` | `grantflow/eval/cases/grounded_cases.json` | PASS | `q=9.25`, `critic=9.25`, `citation_confidence_avg=0.5874`, `fallback_ns=0` |
| `worldbank` | `worldbank_public_sector_performance_uzbekistan_grounded` | `grantflow/eval/cases/grounded_cases.json` | PASS | `q=9.25`, `critic=9.25`, `citation_confidence_avg=0.5873`, `fallback_ns=0` |
| `giz` | `giz_sme_resilience_jordan_grounded_strict` | `grantflow/eval/cases/llm_grounded_strict_cases.json` | PASS | `q=9.25`, `critic=9.25`, `citations=12`, `fallback_ns=0`, `non_retrieval=0` |
| `state_department` | `state_department_media_georgia_grounded` | `grantflow/eval/cases/grounded_cases.json` | PASS | `q=9.25`, `critic=9.25`, `citations=10`, `fallback_ns=0`, `non_retrieval=0` |
| `un_agencies` | `generic_un_agencies_education_nepal_grounded_tail` | `grantflow/eval/cases/grounded_tail_cases.json` | PASS | `q=9.25`, `critic=9.25`, `citations=8`, `fallback_ns=0`, `non_retrieval=0` |

## Runtime Assumptions

- These checks were run against the live container runtime, not the host Python 3.14 environment.
- Chroma-backed namespaces were populated before evaluation using `POST /ingest`.
- The scorecard is only meaningful when the live runtime reports `vector_store.backend=chroma` on `/health`.

## Seeded Namespaces Used

| Donor | Strategy Namespace |
| --- | --- |
| `usaid` | `usaid_ads201` |
| `eu` | `eu_intpa` |
| `worldbank` | `worldbank_ads301` |
| `giz` | `giz_guidance` |
| `state_department` | `us_state_department_guidance` |
| `un_agencies` | `un_agencies_guidance` |

## Reproduce

Seed the live API/Chroma runtime:

```bash
make seed-live-corpus LIVE_SEED_DONORS=usaid,eu,worldbank,giz,state_department,un_agencies
```

Run one targeted grounded check:

```bash
make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/grounded_cases.json \
  GROUNDED_TARGET_CASE_IDS="state_department_media_georgia_grounded"
```

Examples for other donors:

```bash
make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/grounded_cases.json \
  GROUNDED_TARGET_CASE_IDS="usaid_ai_civil_service_kazakhstan_grounded"

make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/grounded_tail_cases.json \
  GROUNDED_TARGET_CASE_IDS="generic_un_agencies_education_nepal_grounded_tail"

make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/llm_grounded_strict_cases.json \
  GROUNDED_TARGET_CASE_IDS="giz_sme_resilience_jordan_grounded_strict"
```

## Artifact Paths

Typical outputs land in `eval-artifacts/`:

- `eval-artifacts/usaid-grounded-live.txt`
- `eval-artifacts/state-grounded-live.txt`
- `eval-artifacts/giz-grounded-live.txt`
- `eval-artifacts/unagencies-grounded-live.txt`

## What This Does Not Prove

- It does not prove that every donor path is equally mature.
- It does not prove that arbitrary uploaded corpora will perform the same way.
- It does not replace the full suite runs in `make eval-grounded-ab`, `make eval-grounded-tail`, or `make eval-llm-grounded-strict`.
