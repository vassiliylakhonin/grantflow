# Pilot In 1 Day

This is the fastest opinionated path to a bounded GrantFlow pilot on a single host.

## Scope

Use this path when you need:
- one API host
- one worker
- Redis queue
- Chroma grounding store
- API-key protected access
- a pilot-ready stack in less than a day

This is a pilot profile, not a hardened multi-environment production platform.

## What Is Verified In Repo

- queue-backed API + worker path exists
- persistent sqlite state is supported
- readiness and health checks exist
- pilot/demo bundle generation already exists
- current auth model is API key based

## 1. Prepare Secrets And Config

```bash
cp .env.pilot.example .env.pilot
```

Fill at minimum:
- `GRANTFLOW_API_KEY`
- `OPENAI_API_KEY` or your OpenAI-compatible provider config

If you want tenant gating for the pilot, also fill:
- `GRANTFLOW_TENANT_AUTHZ_ENABLED=true`
- `GRANTFLOW_ALLOWED_TENANTS=tenant_a`
- `GRANTFLOW_DEFAULT_TENANT=tenant_a`

Before anyone logs in or hits the API, fill:
- `docs/pilot-role-mapping-worksheet.md`
- optionally start from `docs/pilot-role-mapping-example.md`

That prevents ambiguity around:
- who runs drafts
- who reviews findings/comments
- who approves HITL checkpoints
- who owns ingest and pilot metrics

## 2. Start The Opinionated Pilot Stack

```bash
make pilot-stack-up
```

This uses:
- `docker-compose.pilot.yml`
- `.env.pilot`

What it gives you:
- API in `redis_queue` dispatcher mode
- dedicated worker
- persistent sqlite state
- Redis and Chroma bound to localhost only
- API key required at startup

## 3. Check Runtime Health

```bash
make pilot-stack-check
```

Minimum expected result:
- `/health` responds
- `/ready` responds
- no startup failure on missing API key or persistent store guards

If something looks wrong:
- `make pilot-stack-status`
- `make pilot-stack-logs`
- `docs/operations-runbook.md`
- `docs/troubleshooting.md`

## 4. Seed Grounding Corpus For Pilot Donors

Example:

```bash
make seed-live-corpus LIVE_SEED_DONORS=usaid,eu,worldbank
```

For a broader pilot:

```bash
make seed-live-corpus LIVE_SEED_DONORS=usaid,eu,worldbank,giz,state_department,un_agencies
```

## 5. Generate A Pilot Evidence Packet

Fast buyer-facing path:

```bash
make pilot-refresh-fast DEMO_PACK_API_BASE=http://127.0.0.1:8000
make release-demo-bundle-fast
```

Outputs to inspect:
- `build/send-bundle-index.md`
- `build/latest-open-order.md`
- `build/executive-pack/README.md`
- `build/pilot-evidence-pack/README.md`

## 6. Minimum Pilot Decision Check

Before showing this to an external pilot partner, check:
- API is healthy
- readiness is green or intentionally `attention`
- grounding is seeded for the pilot donors
- `send-bundle-index.md` does not say `internal-only`
- reviewer queue is not obviously stale

## 7. What To Use For A Real Pilot

Start with:
- 2-3 donors
- 5-10 representative proposal cases
- one pilot owner
- one proposal manager
- one reviewer/approver

Then use:
- `docs/pilot-evaluation-checklist.md`
- `docs/pilot-role-mapping-worksheet.md`
- `docs/pilot-kickoff-agenda.md`
- `docs/pilot-user-roles.md`
- `docs/role-based-demo-script.md`

## 8. What This Profile Does Not Solve

- enterprise IAM inside the app
- customer-specific measured baseline capture
- multi-host orchestration
- hardened secret management

Those are addressed at the platform/gateway layer or in a later deployment phase.
