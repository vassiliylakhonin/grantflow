# Enterprise-Style Quickstart

This is the shortest credible path to run GrantFlow in an enterprise-style evaluation posture without changing the core application model.

It uses the existing opinionated stack in `docker-compose.pilot.yml` with a separate env file for enterprise-facing evaluation.

## What This Path Assumes

- gateway or reverse proxy handles user authentication
- gateway injects `X-API-Key` downstream
- GrantFlow remains a protected backend service
- Redis and Chroma stay private

Read with:
- `docs/enterprise-access-layer.md`
- `docs/gateway-policy-example.md`
- `docs/enterprise-access-checklist.md`
- `docs/reference-topology.md`

## 1. Create The Eval Config

```bash
cp .env.enterprise.example .env.enterprise
```

Minimum required edits in `.env.enterprise`:
- `GRANTFLOW_API_KEY`
- `OPENAI_API_KEY`

Optional:
- `GRANTFLOW_TENANT_AUTHZ_ENABLED=true`
- `GRANTFLOW_ALLOWED_TENANTS=tenant_a`
- `GRANTFLOW_DEFAULT_TENANT=tenant_a`

## 2. Start The Stack

```bash
make enterprise-eval-up
```

This starts:
- API
- worker
- Redis
- Chroma

## 3. Check Readiness

```bash
make enterprise-eval-check
```

Expected result:
- `/health` returns OK
- `/ready` returns OK without critical startup-policy failures

If it fails:
- `docs/operations-runbook.md`
- `docs/troubleshooting.md`

## 4. Seed Grounding Corpus

```bash
make seed-live-corpus LIVE_SEED_DONORS=usaid,eu,worldbank
```

Adjust donor list to the workflow you want to evaluate.

## 5. Run The Fast Evaluation Path

```bash
make pilot-refresh-fast DEMO_PACK_API_BASE=http://127.0.0.1:8000
```

This rebuilds the fast buyer path and produces:
- pilot pack
- buyer brief
- pilot scorecard
- executive pack
- latest-open-order

## 6. Build A Buyer-Safe Bundle

```bash
make release-demo-bundle-fast
```

Primary output:
- `build/send-bundle-index.md`
- `build/latest-open-order.md`

## 7. Stop The Stack

```bash
make enterprise-eval-down
```

## One-Day Checklist

A credible first-day enterprise-style evaluation should end with:
- stack up and healthy
- corpus seeded for target donors
- one successful generate/review/export cycle
- one buyer-safe evaluation bundle
- route policy agreed at the gateway layer

## What This Is Not

This path does not add:
- in-app SSO
- in-app RBAC
- per-user audit inside GrantFlow state

It is a deployment and access wrapper around the current backend, not a new identity model.
