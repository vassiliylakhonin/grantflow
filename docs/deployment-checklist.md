# Deployment Checklist

Short, operator-oriented checklist for production rollout.

## 1) Pre-deploy

1. Confirm target runtime:
   - Python `3.11` to `3.13`
2. Confirm environment profile:
   - `GRANTFLOW_ENV=production`
3. Confirm queue topology:
   - `GRANTFLOW_JOB_RUNNER_MODE=redis_queue`
   - API node: `GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=false`
   - worker node: `GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=true`
4. Confirm persistence:
   - `GRANTFLOW_JOB_STORE=sqlite`
   - `GRANTFLOW_HITL_STORE=sqlite`
   - `GRANTFLOW_INGEST_STORE=sqlite`
   - `GRANTFLOW_SQLITE_PATH` set to persistent path
5. Confirm auth:
   - `GRANTFLOW_API_KEY` configured for API nodes

Run preflight:

```bash
make preflight-prod-api
make preflight-prod-worker
```

## 2) Deploy

1. Deploy API node(s).
2. Deploy worker process(es): `python -m grantflow.worker`.
3. Verify API startup logs contain no startup-guard failures.

## 3) Post-deploy smoke checks

1. Liveness and readiness:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

2. Redis worker heartbeat (redis mode):

```bash
curl -s -H 'X-API-Key: <key>' http://127.0.0.1:8000/queue/worker-heartbeat
```

3. Minimal generate flow:
   - submit `POST /generate` or `POST /generate/from-preset`
   - poll `GET /status/{job_id}`
   - confirm terminal status (`done` or `pending_hitl`)

4. Optional export smoke:
   - `GET /status/{job_id}/export-payload`
   - `POST /export`

## 4) If rollout is degraded

1. Check readiness payload first (`/ready`) and inspect blocking checks.
2. Check `diagnostics.job_runner.queue` and worker heartbeat in `/health`.
3. Check `docs/troubleshooting.md` for mapped failure patterns.
4. If needed, rollback to last known good image/tag.

## 5) Rollback minimums

Before rollback:
1. Preserve relevant logs and `/ready` payload snapshot.
2. Record affected commit/tag and deployment window.

After rollback:
1. Re-run `/health` and `/ready`.
2. Confirm worker heartbeat and queue health.
3. Open follow-up issue with captured diagnostics and timeline.
