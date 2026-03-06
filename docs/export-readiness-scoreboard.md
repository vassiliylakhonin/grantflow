# Export Readiness Scoreboard

As of March 6, 2026, export generation has been spot-checked in the live Docker runtime for the donor cases below.

This scoreboard is based on real `docx/xlsx` generation, not only unit tests.

## Verified Live Export Cases

| Donor | Case ID | Result | DOCX Size | XLSX Size | Verified DOCX Sections | Verified XLSX Sheets |
| --- | --- | --- | --- | --- | --- | --- |
| `usaid` | `usaid_ai_civil_service_kazakhstan_grounded` | PASS | `38679` bytes | `12545` bytes | `USAID Results Framework`, `Critical Assumptions` | `LogFrame`, `USAID_RF`, `Quality Summary`, `Citations` |
| `eu` | `eu_youth_employment_jordan_grounded` | PASS | `38436` bytes | `11635` bytes | `EU Intervention Logic`, `Overall Objective`, `Specific Objectives`, `Expected Outcomes` | `LogFrame`, `EU_Intervention`, `EU_Assumptions_Risks`, `Quality Summary`, `Citations` |
| `worldbank` | `worldbank_public_sector_performance_uzbekistan_grounded` | PASS | `38389` bytes | `11217` bytes | `World Bank Results Framework`, `Project Development Objective (PDO)`, `Results Chain` | `LogFrame`, `WB_Results`, `Quality Summary`, `Citations` |
| `giz` | `giz_sme_resilience_jordan_grounded_strict` | PASS | `38158` bytes | `10752` bytes | `GIZ Results & Sustainability Logic`, `Programme Objective`, `Sustainability Factors` | `LogFrame`, `GIZ_Results`, `Quality Summary`, `Citations` |
| `state_department` | `state_department_media_georgia_grounded` | PASS | `38375` bytes | `10914` bytes | `U.S. Department of State Program Logic`, `Strategic Context`, `Risk Mitigation` | `LogFrame`, `StateDept_Results`, `Quality Summary`, `Citations` |
| `un_agencies` | `generic_un_agencies_education_nepal_grounded_tail` | PASS | `38004` bytes | `9489` bytes | `Theory of Change`, `MEL Indicator Summary` | `LogFrame`, `Quality Summary`, `Citations` |

## What Was Checked

- the case produced a non-empty `.docx`
- the case produced a non-empty `.xlsx`
- expected donor-specific headings were present in the Word export
- expected donor-specific or core workbook sheets were present in the Excel export
- exports were generated from live graph state in the running container runtime

## Artifacts

Latest checked artifacts from the run above were written to:

- `eval-artifacts/export-readiness-live.md`
- `eval-artifacts/export-readiness-live.json`
- `eval-artifacts/export-readiness-live-artifacts/`

Per-case files currently include:

- `eval-artifacts/export-readiness-live-artifacts/usaid-usaid_ai_civil_service_kazakhstan_grounded.docx`
- `eval-artifacts/export-readiness-live-artifacts/eu-eu_youth_employment_jordan_grounded.docx`
- `eval-artifacts/export-readiness-live-artifacts/worldbank-worldbank_public_sector_performance_uzbekistan_grounded.docx`
- `eval-artifacts/export-readiness-live-artifacts/giz-giz_sme_resilience_jordan_grounded_strict.docx`
- `eval-artifacts/export-readiness-live-artifacts/state_department-state_department_media_georgia_grounded.docx`
- `eval-artifacts/export-readiness-live-artifacts/un_agencies-generic_un_agencies_education_nepal_grounded_tail.docx`

and matching `.xlsx` files for each case.

## Reproduce

Run the live export check across the same donor set:

```bash
make export-target-live \
  EXPORT_TARGET_CASE_SPECS="grantflow/eval/cases/grounded_cases.json:usaid_ai_civil_service_kazakhstan_grounded \
grantflow/eval/cases/grounded_cases.json:eu_youth_employment_jordan_grounded \
grantflow/eval/cases/grounded_cases.json:worldbank_public_sector_performance_uzbekistan_grounded \
grantflow/eval/cases/grounded_cases.json:state_department_media_georgia_grounded \
grantflow/eval/cases/llm_grounded_strict_cases.json:giz_sme_resilience_jordan_grounded_strict \
grantflow/eval/cases/grounded_tail_cases.json:generic_un_agencies_education_nepal_grounded_tail" \
  EXPORT_TARGET_ARTIFACT_PREFIX=eval-artifacts/export-readiness-live \
  EXPORT_TARGET_ARTIFACT_DIR=eval-artifacts/export-readiness-live-artifacts
```

## Scope Limits

- This is an export readiness spot-check, not a guarantee that every donor template is complete for every submission workflow.
- It verifies current donor-specific sections/sheets that already exist in code.
- It does not prove donor-native formatting parity with every real funding call package.
