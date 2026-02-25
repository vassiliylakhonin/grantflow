# LLM Eval Review Template

Use this template after each manual/nightly `LLM Eval` workflow run to compare `llm-eval-report` artifacts against the deterministic baseline `eval` artifacts.

Note: the default `LLM Eval` workflow runs in exploratory mode (`--skip-expectations`), so `PASS/FAIL` counts are not the primary signal. Focus on metric deltas and donor breakdown.

## 1) Run Summary

- **Date / Run ID**: `<example: 22395096012>`
- **LLM model / config**: `<model + key settings>`
- **OPENAI_API_KEY secret configured**: `yes / no`
- **Outcome**: `pass / mixed / fail`
- **One-line takeaway**: `<main conclusion>`

## 2) Suite-Level Summary

| Metric | Baseline CI (`eval`) | LLM Eval | Delta | Verdict |
|---|---:|---:|---:|---|
| `case_count` |  |  |  |  |
| `failed_count` |  |  |  |  |
| `toc_schema_valid` failures |  |  |  |  |
| `avg quality_score` |  |  |  |  |
| `avg critic_score` |  |  |  |  |
| `total fatal_flaw_count` |  |  |  |  |
| `total high_severity_fatal_flaw_count` |  |  |  |  |
| `avg citation_confidence_avg` |  |  |  |  |
| `total low_confidence_citation_count` |  |  |  |  |
| `total rag_low_confidence_citation_count` |  |  |  |  |
| `avg architect_threshold_hit_rate` |  |  |  |  |

`Verdict`: `better / neutral / worse`

## 3) Donor Breakdown (Most Important)

| Donor | Cases | Baseline avg_q | LLM avg_q | Delta | Baseline high_flaws | LLM high_flaws | Baseline low_conf | LLM low_conf | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `usaid` |  |  |  |  |  |  |  |  |  |
| `eu` |  |  |  |  |  |  |  |  |  |
| `worldbank` |  |  |  |  |  |  |  |  |  |
| `giz` |  |  |  |  |  |  |  |  |  |
| `state_department` |  |  |  |  |  |  |  |  |  |
| `un_agencies` |  |  |  |  |  |  |  |  |  |

Focus first on donors marked `worse`, then on mixed donors where quality improved but risk also increased.

## 4) Case-Level Exceptions (Only Problematic / Interesting Cases)

| Case ID | Donor | What improved | What regressed | Hypothesis | Next action |
|---|---|---|---|---|---|
| `usaid_ai_civil_service_kazakhstan` | `usaid` |  |  |  |  |
| `usaid_concept_note_weak_brief_sparse_input` | `usaid` |  |  |  |  |
| `eu_digital_governance_services_moldova` | `eu` |  |  |  |  |
| `<other case>` | `<donor>` |  |  |  |  |

## 5) Red Flags Checklist (Go / No-Go)

- [ ] `toc_schema_valid` did **not** regress materially
- [ ] `high_severity_fatal_flaw_count` did **not** increase materially
- [ ] `architect_threshold_hit_rate` is stable or improved
- [ ] `rag_low_confidence_citation_count` is stable or lower
- [ ] Weak-brief diagnostic still works (not falsely over-optimistic)

If 2+ checks fail, treat the run as **no-go for broader LLM rollout** and do a narrow tuning PR before the next run.

## 6) Next Tuning PR (One Narrow Hypothesis)

- **Target area**: `Architect prompt` / `repair loop` / `critic severity` / `donor checklist`
- **Target donor(s)**: `<usaid/eu/...>`
- **Success metric for next run**: `<example: usaid avg_q +0.3 with no high_flaw increase>`
- **What to avoid changing in same PR**: `<keep scope narrow>`

## 7) Notes / Decisions

- **Decision after this run**: `continue tuning / pause LLM lane / safe for limited pilot use`
- **Follow-up owner**: `<name>`
- **Follow-up ETA**: `<date>`

## Quick Fill Workflow

1. Open baseline `eval-report.txt` artifact from CI.
2. Open `llm-eval-report.txt` artifact from `LLM Eval`.
3. Fill **Suite-Level Summary**.
4. Fill **Donor Breakdown**.
5. Record only the most important cases in **Case-Level Exceptions**.
6. Choose exactly one tuning hypothesis for the next run.
