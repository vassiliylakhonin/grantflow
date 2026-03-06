# Operations Runbook

This runbook is for operators of GrantFlow API and worker processes.

For code-specific error catalog entries, see `docs/troubleshooting.md`.

## 1) Startup Checklist

Before startup, verify:

1. Python runtime is `3.11` to `3.13`.
2. Environment is explicit:
   - local/dev: `GRANTFLOW_ENV=dev`
   - production: `GRANTFLOW_ENV=production`
3. Queue mode is intentional:
   - dev: `background_tasks` is acceptable
   - production: `redis_queue` recommended
4. Stores are configured as expected:
   - production baseline: `GRANTFLOW_JOB_STORE=sqlite`, `GRANTFLOW_HITL_STORE=sqlite`, `GRANTFLOW_INGEST_STORE=sqlite`
5. API auth posture is explicit:
   - production baseline: `GRANTFLOW_API_KEY` set

Optional fast pre-check before boot:

```bash
make preflight-prod-api
make preflight-prod-worker
```

Startup guards already enforce critical misconfigurations:
- job/hitl store mismatch blocks startup
- in production, missing API key blocks startup (unless explicitly disabled)
- in production, non-persistent stores block startup by default (unless explicitly disabled)

## 2) Health vs Readiness

Use both endpoints; they answer different questions.

- `GET /health`
  - process-level diagnostics snapshot
  - includes store modes, auth flags, queue diagnostics, policy configs, and configuration warnings
- `GET /ready`
  - admission gate for serving traffic
  - returns `200` when `status=ready`
  - returns `503` when `status=degraded` (with structured `detail`)

Rule of thumb:
- `health` tells you what the process sees.
- `ready` tells you if this instance should receive production traffic.

## 3) Common Failure Scenarios

### A) Startup fails immediately

Check logs for:
- `Store backend mismatch`
- `Security defaults violation` (API key/persistent stores)
- `Runtime compatibility misconfiguration`
- `Tenant authz misconfiguration`

Fix env values and restart. These are hard-fail guards by design.

### B) `/ready` returns `503`

Inspect:
1. `GET /ready` JSON:
   - `checks.vector_store`
   - `checks.job_runner`
   - `checks.runtime_compatibility_policy`
   - `checks.tenant_authz_configuration_policy`
2. `checks.job_runner.alerts` codes:
   - `REDIS_DISPATCHER_WORKER_HEARTBEAT_MISSING`
   - `DEAD_LETTER_QUEUE_THRESHOLD_EXCEEDED`

Typical causes:
- Redis unavailable
- worker heartbeat missing in dispatcher mode with strict policy
- strict runtime compatibility policy on unsupported Python
- strict tenant authz policy with invalid allowlist/default tenant

### C) Jobs stall (`accepted`/`running` does not progress)

Inspect in order:
1. `GET /status/{job_id}`
2. `GET /status/{job_id}/events`
3. if HITL enabled:
   - `GET /hitl/pending`
   - `GET /status/{job_id}/hitl/history`
4. queue diagnostics:
   - `GET /health` -> `diagnostics.job_runner.queue`
   - `GET /queue/worker-heartbeat` (redis mode)

Frequent root causes:
- job is actually waiting in `pending_hitl` and needs approve/reject + resume
- dispatcher mode enabled but worker not running
- queue full / dead-letter accumulation

### D) Export fails or is blocked

Inspect:
1. `GET /status/{job_id}/quality`
2. `GET /status/{job_id}/grounding-gate`
3. export request flags (`production_export`, `allow_unsafe_export`)

Frequent root causes:
- strict grounded/export policy gates failed
- export contract policy strict and required sections/headers are missing

## 4) Readiness Triage Cheat Sheet

If `/ready` is degraded:

1. Confirm runtime and env profile.
2. Confirm queue mode and worker topology.
3. Confirm Redis reachability (if redis mode).
4. Confirm tenant authz configuration when strict mode is enabled.
5. Review `configuration_warnings` in `/ready` and `/health`.

Helpful warning codes:
- `CHROMA_PORT_MAY_CONFLICT_WITH_API_DEFAULT`
- `TENANT_AUTHZ_ENABLED_WITHOUT_ALLOWLIST`
- `TENANT_DEFAULT_NOT_IN_ALLOWLIST`
- `PRODUCTION_NON_PERSISTENT_STORES_ACTIVE`
- `PERSISTENT_STORE_STARTUP_GUARD_DISABLED_IN_PRODUCTION`

## 5) Minimal Production Baseline

Recommended baseline:

- API:
  - `GRANTFLOW_ENV=production`
  - `GRANTFLOW_API_KEY=<secret>`
  - `GRANTFLOW_JOB_RUNNER_MODE=redis_queue`
  - `GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=false`
- Worker:
  - `python -m grantflow.worker`
- Stores:
  - `GRANTFLOW_JOB_STORE=sqlite`
  - `GRANTFLOW_HITL_STORE=sqlite`
  - `GRANTFLOW_INGEST_STORE=sqlite`
  - `GRANTFLOW_SQLITE_PATH=<persistent path>`

This keeps queueing, state persistence, and auth posture aligned with the current backend design.
