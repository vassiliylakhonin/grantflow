# GrantFlow API Refactor Summary

## Scope

This phase focused on decomposing `grantflow/api/app.py` into modular routers/services while preserving public API compatibility.

## Before

- `grantflow/api/app.py` was a large monolithic module mixing:
  - endpoint definitions,
  - orchestration logic,
  - validation/business rules,
  - security/runtime wiring.

## After

`app.py` now acts primarily as a composition root.
Most endpoint domains are extracted into dedicated modules:

### Routers extracted

- `grantflow/api/routers/health.py`
  - `GET /health`
  - `GET /ready`

- `grantflow/api/routers/system_misc.py`
  - `GET /donors`
  - `GET /demo`

- `grantflow/api/routers/ingest.py`
  - `GET /ingest/recent`
  - `GET /ingest/inventory`
  - `GET /ingest/inventory/export`
  - `POST /ingest`

- `grantflow/api/routers/status_read.py`
  - `GET /status/{job_id}`
  - `GET /status/{job_id}/citations`
  - `GET /status/{job_id}/export-payload`
  - `GET /status/{job_id}/versions`
  - `GET /status/{job_id}/diff`
  - `GET /status/{job_id}/events`
  - `GET /status/{job_id}/metrics`
  - `GET /status/{job_id}/quality`
  - `GET /status/{job_id}/critic`

- `grantflow/api/routers/review_workflow_read.py`
  - `GET /status/{job_id}/review/workflow`
  - `GET /status/{job_id}/review/workflow/sla`
  - `GET /status/{job_id}/review/workflow/sla/profile`
  - `GET /status/{job_id}/review/workflow/export`

- `grantflow/api/routers/status_comments_read.py`
  - `GET /status/{job_id}/comments`

- `grantflow/api/routers/comments_write.py`
  - `POST /status/{job_id}/comments`
  - `POST /status/{job_id}/comments/{comment_id}/resolve`
  - `POST /status/{job_id}/comments/{comment_id}/reopen`

- `grantflow/api/routers/critic_write.py`
  - `POST /status/{job_id}/critic/findings/{finding_id}/ack`
  - `POST /status/{job_id}/critic/findings/{finding_id}/open`
  - `POST /status/{job_id}/critic/findings/{finding_id}/resolve`
  - `POST /status/{job_id}/critic/findings/bulk-status`

- `grantflow/api/routers/portfolio_read.py`
  - `GET /portfolio/metrics`
  - `GET /portfolio/metrics/export`
  - `GET /portfolio/quality`
  - `GET /portfolio/quality/export`

- `grantflow/api/routers/hitl.py`
  - `POST /hitl/approve`
  - `GET /hitl/pending`

- `grantflow/api/routers/generate_submit.py`
  - `POST /generate/preflight`
  - `POST /generate`

- `grantflow/api/routers/generate_write.py`
  - `POST /cancel/{job_id}`
  - `POST /resume/{job_id}`

### Service extraction

- `grantflow/api/services/generate_service.py`
  - `handle_generate_preflight(...)`
  - `handle_generate(...)`

This reduces endpoint complexity in `app.py` and isolates orchestration logic for safer testing and future evolution.

## Security/ops improvements bundled in this phase

- Production auth guard (fail-fast if production mode has no API key unless explicit override).
- Security workflow enhancements (dependency, code, filesystem/image scanning coverage improvements).
- Docker/container hardening (non-root runtime, safer defaults, compose hardening runbooks).
- Reproducibility improvements (`.python-version`, coverage tooling updates, docs updates).

## Compatibility guarantees

- Public endpoint paths and HTTP methods were preserved.
- Response models/structures were kept aligned with existing contracts.
- Behavior-preserving refactor approach was used (extract + wire, not redesign).

## Validation performed

- Syntax checks (`py_compile`) on changed API modules.
- Router-focused unit test suite (`grantflow/tests/test_api_router_units.py`) passing.

## Remaining endpoints in app.py (intentional)

- `POST /status/{job_id}/review/workflow/sla/recompute`
- `POST /export`

These are candidates for next extraction cycle if/when needed.

## Risks to keep watching

1. Contract drift on edge responses during future extractions.
2. Incomplete negative-path test coverage for some routers.
3. Environment-specific runtime differences (Python/toolchain) in contributor machines.

## Recommended next milestones

1. Add contract snapshot tests for critical API payloads.
2. Expand negative-path router tests (validation/404/409 flows).
3. Optionally extract the two remaining app-level endpoints into dedicated routers.
4. Add a compact architecture diagram in docs for new contributors.
