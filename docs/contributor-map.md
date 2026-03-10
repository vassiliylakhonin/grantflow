# Contributor Map

This is the shortest path to navigate the codebase without guessing.

## API Surface

- App bootstrap and compatibility exports:
  - `grantflow/api/app.py`
  - `grantflow/api/compat_exports.py`
- Router registration:
  - `grantflow/api/routers.py`
- Route handlers by domain:
  - jobs/status: `grantflow/api/routes/jobs.py`
  - ingest/readiness: `grantflow/api/routes/ingest.py`
  - review/HITL/comments/findings: `grantflow/api/routes/review.py`
  - export/portfolio export: `grantflow/api/routes/exports.py`
  - queue admin: `grantflow/api/routes/queue_admin.py`
  - health/readiness: `grantflow/api/routes/system.py`
  - presets/donor catalog/demo page: `grantflow/api/routes/presets.py`
  - read-only portfolio views: `grantflow/api/routes/portfolio_read.py`

## Product and Demo Assets

- Product overview (buyer-facing):
  - `docs/buyer-one-pager.md`
- Demo operator script + 5-minute narrative:
  - `docs/demo-runbook.md`
- Productization gap analysis:
  - `docs/productization-gaps-memo.md`
- Pilot acceptance template:
  - `docs/pilot-evaluation-checklist.md`
- Sample artifacts for demos:
  - `docs/samples/`

## Schemas and Contracts

- Request/response schemas:
  - `grantflow/api/schemas.py`
- Public response shaping:
  - `grantflow/api/public_views.py`
- API stability policy:
  - `docs/api-stability-policy.md`

## Runtime and Execution

- Startup/runtime guards (store alignment, auth, env safety):
  - `grantflow/api/runtime_service.py`
- Diagnostics and readiness inputs:
  - `grantflow/api/diagnostics_service.py`
  - `grantflow/api/readiness_service.py`
- Pipeline dispatch and queue task wiring:
  - `grantflow/api/pipeline_jobs.py`
  - `grantflow/core/job_runner.py`
  - worker entrypoint: `grantflow/worker.py`

## Orchestration and Domain Logic

- Orchestration/service glue:
  - `grantflow/api/orchestrator_service.py`
  - `grantflow/api/preflight_service.py`
- Graph and HITL:
  - `grantflow/swarm/graph.py`
  - `grantflow/swarm/hitl.py`
  - `grantflow/swarm/state_contract.py`
- Critic/findings:
  - `grantflow/swarm/critic_rules.py`
  - `grantflow/swarm/critic_donor_policy.py`
  - `grantflow/swarm/findings.py`
- LLM/retrieval:
  - `grantflow/swarm/llm_provider.py`
  - `grantflow/swarm/retrieval_query.py`
  - `grantflow/memory_bank/vector_store.py`
  - `grantflow/memory_bank/ingest.py`

## Review and Export Logic

- Review workflow helpers/mutations:
  - `grantflow/api/review_service.py`
  - `grantflow/api/review_mutations.py`
  - `grantflow/api/review_helpers.py`
- Export builders/contracts:
  - `grantflow/exporters/word_builder.py`
  - `grantflow/exporters/excel_builder.py`
  - `grantflow/exporters/donor_contracts.py`

## Tests and Smoke Gates

- Integration contract tests (API behavior):
  - `grantflow/tests/test_integration.py`
- Focused domain tests:
  - architect: `grantflow/tests/test_architect.py`
  - mel: `grantflow/tests/test_mel.py`
  - critic: `grantflow/tests/test_critic.py`
  - exporters: `grantflow/tests/test_exporters.py`
  - stores: `grantflow/tests/test_stores.py`
- Local gates:
  - `make qa-fast`
  - `make qa-hitl`
- CI workflows:
  - `.github/workflows/ci.yml`
  - `.github/workflows/llm-eval*.yml`
