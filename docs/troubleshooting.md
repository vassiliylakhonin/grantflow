# Troubleshooting

Quick reference for common runtime issues.

## Startup Errors

### `Store backend mismatch`

Meaning:
- `GRANTFLOW_JOB_STORE` and `GRANTFLOW_HITL_STORE` are configured with different backends.

Fix:
1. Set both to `sqlite` (recommended) or both to `inmem` (dev only).
2. Restart API process.

### `Security defaults violation` (API key)

Meaning:
- production startup guard requires API key auth, but `GRANTFLOW_API_KEY` is missing.

Fix:
1. Set `GRANTFLOW_API_KEY`.
2. Keep `GRANTFLOW_REQUIRE_API_KEY_ON_STARTUP=true` in production.

### `Security defaults violation` (persistent stores)

Meaning:
- production startup guard requires persistent stores, but one or more stores are non-sqlite.

Fix:
1. Set `GRANTFLOW_JOB_STORE=sqlite`
2. Set `GRANTFLOW_HITL_STORE=sqlite`
3. Set `GRANTFLOW_INGEST_STORE=sqlite`
4. Set `GRANTFLOW_SQLITE_PATH`

### `Runtime compatibility misconfiguration`

Meaning:
- strict runtime compatibility policy is enabled and Python is outside `3.11-3.13`.

Fix:
1. Use Python `3.11-3.13`.
2. Keep strict policy only when runtime is compliant.

## Readiness Degraded (`GET /ready` => 503)

Inspect:
1. `checks.job_runner.alerts`
2. `checks.runtime_compatibility_policy`
3. `checks.tenant_authz_configuration_policy`
4. `checks.vector_store`

### `REDIS_DISPATCHER_WORKER_HEARTBEAT_MISSING`

Meaning:
- API is in redis dispatcher mode and no healthy external worker heartbeat is available (strict policy blocks readiness).

Fix:
1. Ensure worker process is running: `python -m grantflow.worker`
2. Verify Redis connectivity.
3. Check worker heartbeat settings in env.

### `DEAD_LETTER_QUEUE_THRESHOLD_EXCEEDED`

Meaning:
- dead-letter queue size exceeded configured alert threshold.

Fix:
1. Inspect dead letters: `GET /queue/dead-letter`
2. Requeue failed items if safe: `POST /queue/dead-letter/requeue`
3. Purge only if reviewed: `DELETE /queue/dead-letter`

### `TENANT_AUTHZ_CONFIGURATION_RISK`

Meaning:
- tenant authz strict mode with invalid allowlist/default tenant config.

Fix:
1. Set non-empty `GRANTFLOW_ALLOWED_TENANTS` when authz enabled.
2. Ensure `GRANTFLOW_DEFAULT_TENANT` is in allowlist.

### `PYTHON_RUNTIME_COMPATIBILITY_RISK`

Meaning:
- runtime Python is outside validated range.

Fix:
1. Move runtime to Python `3.11-3.13`.

## Jobs Stall or Do Not Complete

Checklist:
1. `GET /status/{job_id}` for current state.
2. `GET /status/{job_id}/events` for event progression.
3. If `pending_hitl`:
   - `POST /hitl/approve`
   - `POST /resume/{job_id}`
4. In redis mode:
   - `GET /queue/worker-heartbeat`
   - `GET /health` and inspect `diagnostics.job_runner.queue`

## Useful Warning Codes (`/health` and `/ready`)

- `CHROMA_PORT_MAY_CONFLICT_WITH_API_DEFAULT`
- `TENANT_AUTHZ_ENABLED_WITHOUT_ALLOWLIST`
- `TENANT_DEFAULT_NOT_IN_ALLOWLIST`
- `PRODUCTION_NON_PERSISTENT_STORES_ACTIVE`
- `PERSISTENT_STORE_STARTUP_GUARD_DISABLED_IN_PRODUCTION`

These are warnings, not always blockers, but should be resolved before production rollout.
