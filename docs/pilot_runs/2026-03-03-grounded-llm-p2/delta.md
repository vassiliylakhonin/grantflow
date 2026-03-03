# Delta — Deterministic vs LLM (Grounded)

Run date: 2026-03-03

| Donor | q_det | q_llm | critic_det | critic_llm | citations_det | citations_llm | rag_low_det | rag_low_llm | fallback_det | fallback_llm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| state_department | 9.25 | 9.25 | 9.25 | 9.25 | 10 | 10 | 0 | 0 | 0 | 0 |
| usaid | 9.25 | 9.25 | 9.25 | 9.25 | 18 | 18 | 0 | 0 | 0 | 0 |

## Takeaways
- В этом прогоне метрики deterministic и llm совпали для обоих доноров.
- После калибровки confidence у `state_department` больше нет `rag_low_confidence` в deterministic lane.
- Оба режима показали `readiness=4/4` и `fallback_namespace=0`.
