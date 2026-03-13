# grantflow/api/app.py Decomposition Plan (PR-ready)

Goal: split monolithic `grantflow/api/app.py` into router modules without breaking public API contracts.

## Target structure

- `grantflow/api/routers/health.py`
- `grantflow/api/routers/generate.py`
- `grantflow/api/routers/status.py`
- `grantflow/api/routers/review.py`
- `grantflow/api/routers/portfolio.py`
- `grantflow/api/routers/ingest.py`
- `grantflow/api/routers/export.py`
- `grantflow/api/deps.py` (shared authz/deps)
- `grantflow/api/models.py` (request/response pydantic models)

## Migration order (safe)

1. Extract `health` + `ready` endpoints (low risk).
2. Extract `ingest` endpoints + tests.
3. Extract `status` read endpoints + tests.
4. Extract `review`/comments endpoints + tests.
5. Extract `portfolio` endpoints + tests.
6. Extract `generate` + preflight + cancel/resume.
7. Extract export routes and final cleanup.

## Non-breaking rules

- Keep paths/methods/response shapes unchanged.
- Preserve auth behavior (same `require_api_key_if_configured` calls).
- Preserve OpenAPI security annotations.
- Keep legacy env aliases working.

## Per-PR checklist

- [ ] Move only one domain area per PR.
- [ ] Add/adjust tests for moved routes.
- [ ] Verify OpenAPI diff has no breaking path/schema changes.
- [ ] Run CI + smoke benchmark.
- [ ] Include rollback note (revert router import wiring).
