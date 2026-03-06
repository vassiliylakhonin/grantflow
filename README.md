# GrantFlow

Proposal operations platform for high-stakes donor workflows. GrantFlow is a compliance-aware, agentic backend that turns raw program intent into reviewable draft artifacts with governance, traceability, and export-ready outputs.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11--3.13-blue.svg)](https://www.python.org/)

## Start Here

- Local dev (fastest path):
  1. `pip install ".[dev]"`
  2. `uvicorn grantflow.api.app:app --reload`
  3. `curl -s http://127.0.0.1:8000/health && curl -s http://127.0.0.1:8000/ready`
- Recommended production path:
  - API in `redis_queue` dispatcher mode + dedicated `grantflow.worker` process
  - Redis queue enabled
  - persistent stores (`GRANTFLOW_JOB_STORE=sqlite`, `GRANTFLOW_HITL_STORE=sqlite`, `GRANTFLOW_INGEST_STORE=sqlite`)
  - API key auth enabled (`GRANTFLOW_API_KEY`)
- Operator docs:
  - `docs/operations-runbook.md`
  - `docs/demo-runbook.md`
  - `docs/troubleshooting.md`
  - `docs/architecture.md`
  - `docs/contributor-map.md`
  - `docs/buyer-one-pager.md`
  - `SECURITY.md`

## What It Is

GrantFlow is an API-first backend for institutional proposal workflows.

It orchestrates proposal drafting as a process, not as a single text generation call.

Current focus:
- structured draft pipeline (ToC + MEL/LogFrame)
- donor strategy routing (specialized + generic)
- critic loop with structured findings entities (`id`, `severity`, `section`, `status`, remediation fields)
- SLA-aware review workflow (`due_at`, `sla_hours`, `pending/overdue` filters for findings and comments)
- human-in-the-loop pause/approve/resume
- citation + version traceability
- export to `.docx` / `.xlsx` / ZIP

## Who It Is For

- NGOs and implementing organizations
- consulting firms managing donor submissions
- program/MEL teams handling institutional compliance workflows

## Who It Is Not For

- teams looking for a general-purpose grant-writing chatbot
- individual fundraising use cases (for example, ad-hoc small grant copywriting)
- organizations that only need plain text generation without review controls or audit traces

## Why Not Just Use Generic AI Tools?

Generic LLM tools generate text. Proposal operations teams need controlled workflow.

What GrantFlow adds on top of generic AI writing:
- stage-based pipeline with explicit transitions (`discovery -> architect -> mel -> critic`)
- donor strategy routing and schema-bound draft structures
- HITL pause/approve/resume controls
- structured critic findings + comment workflows
- traceability endpoints (citations, versions, events, quality, metrics)
- export payload flow and review-package artifact generation (`.docx`, `.xlsx`, ZIP)

## How This Fits Real Proposal Workflows

Typical operating model in proposal teams:
- capture/program team submits core concept + constraints
- drafting engine produces structured ToC/LogFrame/MEL artifacts
- reviewers triage findings and comments
- designated approvers control pause/resume checkpoints (HITL)
- finalized package is exported for downstream submission workflow

GrantFlow covers the drafting-control-review-export layer. Final donor compliance sign-off remains a human responsibility.

## Architecture (Current)

Pipeline:

`discovery -> architect -> mel -> critic`

With optional HITL checkpoints and resume control.

Architect generation modes:
- `llm_mode=false`: `deterministic:contract_synthesizer` (schema-valid non-LLM draft)
- `llm_mode=true`: LLM structured output via strategy `Architect` prompt + `get_toc_schema()`
- emergency fallback to `fallback:contract_synthesizer` only when LLM mode is requested but unavailable/invalid

Execution flow snapshot:
- Request entry:
  - job submit: `POST /generate` or `POST /generate/from-preset`
  - preflight/readiness: `POST /generate/preflight`, `GET /ready`
- Orchestration path:
  - discovery normalizes contract + donor strategy
  - architect drafts ToC
  - mel builds indicators/logframe
  - critic emits structured findings and quality signals
- Review/HITL path:
  - optional pause after architect and/or mel
  - reviewer action via `POST /hitl/approve`
  - continuation via `POST /resume/{job_id}`
- Export path:
  - fetch sanitized payload: `GET /status/{job_id}/export-payload`
  - generate artifacts: `POST /export`

Technical evaluator quick view:
- API surface is split by route domain (`jobs`, `review`, `ingest`, `exports`, `system`, `portfolio`)
- runtime supports local mode and queue-backed mode (`redis_queue` + worker)
- readiness includes policy-aware checks (`/ready`) and diagnostics snapshot (`/health`)
- contract-heavy test coverage exists in `grantflow/tests/*` (integration, exporters, critic/findings, state contract, eval harness)

## Operating Paths

`Golden path` (recommended production):
- `GRANTFLOW_JOB_RUNNER_MODE=redis_queue`
- API dispatcher (`GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=false`) + separate `python -m grantflow.worker`
- persistent sqlite stores for job/hitl/ingest
- API key configured

`Supported local/dev path`:
- `GRANTFLOW_JOB_RUNNER_MODE=background_tasks`
- in-memory stores allowed
- optional API key

`Advanced / non-default path`:
- `GRANTFLOW_JOB_RUNNER_MODE=inmemory_queue` for local queue behavior testing
- usable, but not recommended as primary production mode (no durable queue backend)

## Donor Coverage

Specialized strategies:
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (alias: `state_department`)

Generic strategy:
- broader donor catalog via `GET /donors`

## Recommended Demo Flow

Use this path for pilot conversations and technical evaluation:

1. Start API (`uvicorn grantflow.api.app:app --reload`) and open `GET /demo`.
2. Generate from an existing preset (`POST /generate/from-preset` or Demo Console preset selector).
3. Inspect draft status and quality signals:
   - `GET /status/{job_id}`
   - `GET /status/{job_id}/quality`
   - `GET /status/{job_id}/critic`
4. Show review traceability:
   - `GET /status/{job_id}/citations`
   - `GET /status/{job_id}/versions`
   - `GET /status/{job_id}/events`
5. (Optional) Show HITL governance:
   - run with `hitl_enabled=true`
   - approve with `POST /hitl/approve`
   - continue with `POST /resume/{job_id}`
6. Export review package:
   - `GET /status/{job_id}/export-payload`
   - `POST /export`

For ready-made example artifacts, use files in `docs/samples/` and `docs/pilot_runs/2026-02-27/`.

One-command local bundle generation:

```bash
make demo-pack
make pilot-pack
make buyer-brief
make buyer-brief-refresh
make pilot-metrics
make pilot-metrics-refresh
make pilot-scorecard
make pilot-scorecard-refresh
make case-study-pack
make case-study-pack-refresh
make executive-pack
make executive-pack-refresh
make oem-pack
make oem-pack-refresh
make pilot-archive
make pilot-archive-refresh
make diligence-index
make diligence-index-refresh
make baseline-fill-template
make baseline-fill-template-refresh
make clean-demo-artifacts-dry-run
make clean-demo-artifacts
make latest-links
make latest-links-refresh
make pilot-handout
make pilot-handout-refresh
make smoke-demo-refresh
make latest-open-order
make latest-open-order-refresh
make pilot-refresh-fast
make verify-latest-stack
make verify-latest-stack-refresh
make release-demo-bundle
make release-demo-bundle-fast
make send-bundle-index
make send-bundle-index-refresh
make open-latest-send
make open-latest-send-refresh
make open-latest-send-fast
make open-latest-send-fast-refresh
make buyer-demo-open
make buyer-demo-open-refresh
make ci-demo-smoke
```

Default output: `build/demo-pack/` with per-case JSON traces plus `.docx` / `.xlsx` / ZIP artifacts. The target expects a running local API at `http://127.0.0.1:8000`.
`make pilot-pack` wraps the live demo evidence into `build/pilot-pack/` with a top-level pilot README plus buyer/demo guidance docs.
`make buyer-brief` turns an existing pilot pack into a short executive summary markdown for sponsor or buyer review.
`make buyer-brief-refresh` rebuilds the pilot pack first and then writes the brief.
`make pilot-metrics` builds `csv` + `md` metric tables from an existing pilot pack.
`make pilot-metrics-refresh` rebuilds the pilot pack first and then writes the metric tables.
`make pilot-scorecard` builds a buyer-facing go/no-go memo from an existing pilot pack.
`make pilot-scorecard-refresh` rebuilds the pilot pack, metrics, and brief first, then writes the scorecard.
`make case-study-pack` builds a compact single-case buyer/demo pack from an existing pilot pack.
`make case-study-pack-refresh` rebuilds the pilot pack, metrics, brief, and scorecard first, then writes the case pack.
`make executive-pack` builds a short send-ready folder from an existing pilot pack plus one case-study pack.
`make executive-pack-refresh` rebuilds the full chain first, then writes the executive pack.
`make oem-pack` builds a technical partner diligence folder from an existing pilot pack and executive pack.
`make oem-pack-refresh` rebuilds the full chain first, then writes the OEM pack.
`make pilot-archive` zips the pilot, executive, and optional OEM packs into a sendable archive.
`make pilot-archive-refresh` rebuilds the full chain first, then writes the archive.
`make diligence-index` builds a single local index of generated packs and archives under `build/`.
`make diligence-index-refresh` rebuilds the full chain first, then writes the index.
`make baseline-fill-template` builds a fillable baseline worksheet from an existing `pilot-metrics.csv`.
`make baseline-fill-template-refresh` rebuilds pilot metrics first, then writes the baseline worksheet.
`make clean-demo-artifacts-dry-run` lists generated demo/commercial bundles that would be removed from `build/`.
`make clean-demo-artifacts` removes only those generated bundles via an allowlist.
`make latest-links` creates stable `build/latest-*` symlinks to the newest generated packs, including fast/full send bundles and their zip files.
`make latest-links-refresh` rebuilds the full chain first, then refreshes those symlinks.
`make pilot-handout` builds a short one-file summary from an existing pilot pack and executive pack.
`make pilot-handout-refresh` rebuilds the full chain first, then writes the handout.
`make smoke-demo-refresh` runs the full default smoke demo chain through handout generation.
`make latest-open-order` writes a short guide describing what to open in `build/latest-*` and in what order.
`make latest-open-order-refresh` rebuilds the chain first, then writes the guide.
`make pilot-refresh-fast` rebuilds the buyer-facing chain quickly without OEM pack, archive, or diligence index.
`make verify-latest-stack` verifies that `build/latest-*` links and key files are present.
`make verify-latest-stack-refresh` rebuilds the chain first, then verifies the latest stack.
`make release-demo-bundle` rebuilds and packages the current latest stack into a send-ready folder plus zip.
`make release-demo-bundle-fast` rebuilds only the fast buyer path, then packages `pilot-handout`, `latest-open-order`, and the current `executive-pack` into a lighter send-ready folder plus zip.
`make send-bundle-index` writes a short markdown telling you which current bundle to send in which scenario.
`make send-bundle-index-refresh` rebuilds the fast send bundle first, then writes that send index.
`make open-latest-send` prints the current send-oriented open order from the latest fast/full bundle links. Set `OPEN_LATEST_SEND_MODE=open` on macOS to open them directly.
`make open-latest-send-refresh` rebuilds the fast send layer first, then prints or opens those artifacts.
`make open-latest-send-fast` prints only the fast send path artifacts.
`make open-latest-send-fast-refresh` rebuilds the fast send layer first, then prints or opens only those fast artifacts.
`make buyer-demo-open` prints the buyer-facing file open order from the current `build/latest-*` stack. Set `BUYER_DEMO_OPEN_MODE=open` on macOS to open them directly.
`make buyer-demo-open-refresh` rebuilds the fast buyer path first, then prints or opens that stack.
`make ci-demo-smoke` runs a one-preset buyer-chain smoke check and verifies the expected demo artifacts exist. It expects a local API on `http://127.0.0.1:8000`.

## Quick Start

### 1) Install

Recommended runtime: Python `3.11` to `3.13`.

```bash
pip install .
```

For local development tooling (`pytest`, `mypy`, `ruff`, `black`, pre-commit):

```bash
pip install ".[dev]"
```

Local quality gates (run before push):

```bash
make qa-fast
make qa-hitl
```

Notes:
- `make qa-hitl` is the focused HITL integration smoke gate (pause/reject/resume/export/history).
- `make qa-fast` includes `qa-hitl` plus core unit/contract checks and mypy baseline.

Dependency policy:
- canonical source of truth: `pyproject.toml`
- compatibility shims: `requirements.txt`, `requirements-dev.txt`, `grantflow/requirements.txt`

### 2) Run API

```bash
uvicorn grantflow.api.app:app --reload
```

OpenAPI:
- `http://127.0.0.1:8000/docs`

If you use remote Chroma via `CHROMA_HOST`, keep `CHROMA_PORT` separate from API port (`8000`), for example:

```bash
export CHROMA_HOST=127.0.0.1
export CHROMA_PORT=8001
```

### 3) Health / readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

`/ready` now includes `checks.preflight_grounding_policy`, `checks.runtime_grounded_quality_gate`, `checks.runtime_compatibility_policy`, and `checks.tenant_authz_configuration_policy` with active modes and thresholds/status, plus `checks.configuration_warnings` for setup risks (for example Chroma/API port conflicts).

### Common Setup Mistakes

- API/Chroma port collision:
  - if `CHROMA_HOST` is set and `CHROMA_PORT=8000`, it may conflict with API port `8000`
  - use `CHROMA_PORT=8001` or run API on another port
- Diverged store backends:
  - `GRANTFLOW_JOB_STORE` and `GRANTFLOW_HITL_STORE` must match
  - startup fails if they differ
- Production without persistence:
  - in `prod|production`, startup fails by default if job/hitl/ingest stores are not sqlite
- Production without API key:
  - in `prod|production`, startup fails by default if `GRANTFLOW_API_KEY` is not set
- Redis dispatcher without live worker:
  - with strict heartbeat policy, `/ready` degrades when worker heartbeat is missing/stale

### 4) (Optional) Configure preflight grounding thresholds

```bash
export GRANTFLOW_GROUNDING_GATE_MODE=warn
export GRANTFLOW_GROUNDING_MIN_RETRIEVAL_METADATA_COMPLETE_RATE=0.60
export GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE=warn
export GRANTFLOW_PREFLIGHT_GROUNDING_HIGH_RISK_COVERAGE_THRESHOLD=0.50
export GRANTFLOW_PREFLIGHT_GROUNDING_MEDIUM_RISK_COVERAGE_THRESHOLD=0.80
export GRANTFLOW_PREFLIGHT_GROUNDING_MIN_UPLOADS=3
```

Notes:
- `GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE` controls preflight block behavior (`off|warn|strict`) and is separate from pipeline critic gate mode.
- If `GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE` is not set, it falls back to `GRANTFLOW_GROUNDING_GATE_MODE`.
- `GRANTFLOW_GROUNDING_MIN_RETRIEVAL_METADATA_COMPLETE_RATE` controls how strict critic grounding is about retrieval metadata completeness (`doc_id` + rank + confidence on retrieval-grounded citations).
- `strict_preflight=true` blocks when either readiness risk or grounding risk is `high`.

### 4.1) (Optional) Configure runtime grounded quality gate

```bash
export GRANTFLOW_RUNTIME_GROUNDED_QUALITY_GATE_MODE=strict
export GRANTFLOW_RUNTIME_GROUNDED_QUALITY_GATE_MIN_CITATIONS=5
export GRANTFLOW_RUNTIME_GROUNDED_QUALITY_GATE_MAX_NON_RETRIEVAL_CITATION_RATE=0.35
export GRANTFLOW_RUNTIME_GROUNDED_QUALITY_GATE_MIN_RETRIEVAL_GROUNDED_CITATIONS=2
export GRANTFLOW_EXPORT_REQUIRE_GROUNDED_GATE_PASS=false
```

Notes:
- Applies only to `llm_mode=true` with `architect_rag_enabled=true`.
- In `strict` mode, job finalization is blocked when grounded signals are below threshold.
- Gate outcome is exposed in `GET /status/{job_id}/quality` as `grounded_gate`.
- `GET /status/{job_id}/grounding-gate` returns runtime/preflight/mel grounding policies with structured `reason_details`, `failed_sections`, and sample evidence rows for triage.
- If `GRANTFLOW_EXPORT_REQUIRE_GROUNDED_GATE_PASS=true`, `/export` returns `409` when runtime grounded gate did not pass (unless `allow_unsafe_export=true`).

### 4.1.1) (Optional) Configure runtime compatibility policy

```bash
export GRANTFLOW_RUNTIME_COMPATIBILITY_POLICY_MODE=warn   # off | warn | strict
```

Notes:
- `warn` keeps `/ready` non-blocking but reports compatibility risk when Python is outside validated runtime range.
- `strict` fails startup and degrades `/ready` when runtime Python is outside `3.11-3.13`.

### 4.2) (Optional) Configure pipeline runner mode

```bash
export GRANTFLOW_JOB_RUNNER_MODE=background_tasks   # or inmemory_queue / redis_queue
export GRANTFLOW_JOB_RUNNER_WORKER_COUNT=2
export GRANTFLOW_JOB_RUNNER_QUEUE_MAXSIZE=200
export GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=true
export GRANTFLOW_JOB_RUNNER_REDIS_URL=redis://127.0.0.1:6379/0
export GRANTFLOW_JOB_RUNNER_REDIS_QUEUE_NAME=grantflow:jobs
export GRANTFLOW_JOB_RUNNER_REDIS_POP_TIMEOUT_SECONDS=1.0
export GRANTFLOW_JOB_RUNNER_REDIS_MAX_ATTEMPTS=3
export GRANTFLOW_JOB_RUNNER_REDIS_DEAD_LETTER_QUEUE_NAME=grantflow:jobs:dead
export GRANTFLOW_JOB_RUNNER_REDIS_WORKER_HEARTBEAT_KEY=grantflow:jobs:worker_heartbeat
export GRANTFLOW_JOB_RUNNER_REDIS_WORKER_HEARTBEAT_TTL_SECONDS=45
export GRANTFLOW_JOB_RUNNER_REDIS_WORKER_HEARTBEAT_INTERVAL_SECONDS=10
export GRANTFLOW_JOB_RUNNER_REDIS_WORKER_HEARTBEAT_POLICY_MODE=strict
export GRANTFLOW_JOB_RUNNER_DEAD_LETTER_ALERT_THRESHOLD=0
export GRANTFLOW_JOB_RUNNER_DEAD_LETTER_ALERT_BLOCKING=false
```

Notes:
- `background_tasks` keeps existing FastAPI per-request scheduling behavior.
- `inmemory_queue` runs pipeline jobs on internal worker threads and can return `503` when queue is full.
- `redis_queue` uses Redis LIST/BLPOP for queue persistence and worker coordination; requires a reachable Redis instance.
- `redis_queue` retries transient task failures up to `GRANTFLOW_JOB_RUNNER_REDIS_MAX_ATTEMPTS`; exhausted jobs are moved to dead-letter queue.
- Use `GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=false` on API when running a dedicated worker process.
- In dispatcher mode (`redis_queue` + `...CONSUMER_ENABLED=false`), heartbeat behavior is controlled by `GRANTFLOW_JOB_RUNNER_REDIS_WORKER_HEARTBEAT_POLICY_MODE` (`off|warn|strict`).
- `strict` degrades `/ready` when external worker heartbeat is missing (`REDIS_DISPATCHER_WORKER_HEARTBEAT_MISSING`).
- `warn` keeps `/ready` green but surfaces alert in `checks.job_runner.alerts`.
- `/health` includes `diagnostics.job_runner.dispatcher_worker_heartbeat` with `age_seconds`/`source` when available.
- Dead-letter ops (redis mode only):
  - `GET /queue/worker-heartbeat`
  - `GET /queue/dead-letter?limit=50`
  - `GET /queue/dead-letter/export?limit=500&format=json` (or `format=csv`)
  - `POST /queue/dead-letter/requeue?limit=10&reset_attempts=true`
  - `DELETE /queue/dead-letter?limit=100`
- `/ready` includes `checks.job_runner.dead_letter_alert`; set `...ALERT_THRESHOLD` to enable and `...ALERT_BLOCKING=true` to fail readiness when threshold is exceeded.

Dedicated worker process (for `redis_queue`):

```bash
python -m grantflow.worker
```

### 4.3) (Optional) Configure persistent stores

```bash
export GRANTFLOW_JOB_STORE=sqlite
export GRANTFLOW_HITL_STORE=sqlite
export GRANTFLOW_INGEST_STORE=sqlite
export GRANTFLOW_SQLITE_PATH=./.data/grantflow_state.db
```

Notes:
- Keep `GRANTFLOW_JOB_STORE` and `GRANTFLOW_HITL_STORE` aligned (`inmem` with `inmem`, or `sqlite` with `sqlite`).
- On startup, GrantFlow fails fast when these two backends differ to prevent orphaned HITL/job state.
- If `GRANTFLOW_ENV` is `prod` or `production`, startup also fails by default when any of `GRANTFLOW_JOB_STORE`, `GRANTFLOW_HITL_STORE`, `GRANTFLOW_INGEST_STORE` is non-persistent (`inmem`).
- Recommended production baseline: `GRANTFLOW_JOB_RUNNER_MODE=redis_queue` with `GRANTFLOW_JOB_STORE=sqlite`, `GRANTFLOW_HITL_STORE=sqlite`, and `GRANTFLOW_INGEST_STORE=sqlite`.

### 4.4) (Optional) Security defaults for production

```bash
export GRANTFLOW_ENV=production
export GRANTFLOW_API_KEY=change-me
export GRANTFLOW_REQUIRE_API_KEY_ON_STARTUP=true
export GRANTFLOW_REQUIRE_PERSISTENT_STORES_ON_STARTUP=true
```

Notes:
- If `GRANTFLOW_ENV` is `prod` or `production`, startup now fails when `GRANTFLOW_API_KEY` is missing.
- If `GRANTFLOW_ENV` is `prod` or `production`, startup also fails when in-memory stores are configured.
- Override only for controlled environments with `GRANTFLOW_REQUIRE_API_KEY_ON_STARTUP=false` and/or `GRANTFLOW_REQUIRE_PERSISTENT_STORES_ON_STARTUP=false`.

### 5) (Optional) Run preflight readiness check

```bash
curl -s -X POST http://127.0.0.1:8000/generate/preflight \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "usaid"
  }'
```

### 6) Start a job

```bash
curl -s -X POST http://127.0.0.1:8000/generate/from-preset \
  -H 'Content-Type: application/json' \
  -d '{
    "preset_key": "usaid_gov_ai_kazakhstan",
    "preset_type": "auto",
    "llm_mode": false,
    "hitl_enabled": false,
    "architect_rag_enabled": true,
    "input_context_patch": {
      "project": "Youth Employment Initiative",
      "country": "Kenya"
    }
  }'
```

`architect_rag_enabled` controls Architect retrieval behavior per request (default: `true`).

`/generate/from-preset` is async and returns `job_id`.

### 7) (Optional) Enforce strict preflight gate

```bash
curl -s -X POST http://127.0.0.1:8000/generate/from-preset \
  -H 'Content-Type: application/json' \
  -d '{
    "preset_key": "usaid_gov_ai_kazakhstan",
    "preset_type": "auto",
    "llm_mode": false,
    "hitl_enabled": false,
    "strict_preflight": true,
    "input_context_patch": {
      "project": "Youth Employment Initiative",
      "country": "Kenya"
    }
  }'
```

Direct payload mode (`POST /generate`) is still supported for advanced/custom integrations.

If strict preflight blocks, API returns `409`:

```json
{
  "detail": {
    "reason": "preflight_high_risk_block",
    "message": "Generation blocked by strict_preflight because donor readiness risk is high.",
    "preflight": {
      "risk_level": "high"
    }
  }
}
```

If preflight grounding policy itself is strict-blocking, API returns:

```json
{
  "detail": {
    "reason": "preflight_grounding_policy_block"
  }
}
```

### 8) Poll result

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

### 9) (Optional) Tenant isolation / authz

Enable tenant-aware access control:

```bash
export GRANTFLOW_TENANT_AUTHZ_ENABLED=true
export GRANTFLOW_ALLOWED_TENANTS=tenant_a,tenant_b
export GRANTFLOW_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE=warn   # off | warn | strict
```

Send tenant in request body (`tenant_id`) or header:

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: tenant_a' \
  -d '{
    "donor_id": "usaid",
    "tenant_id": "tenant_a",
    "input_context": {"project": "Water", "country": "Kenya"},
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

With tenant authz enabled:
- read endpoints (`/status/*`, `/portfolio/*`, `/hitl/pending`, `/ingest/*`) are tenant-scoped
- access is denied (`403`) for cross-tenant reads
- RAG namespace becomes tenant-aware: `{tenant}/{donor_namespace}` (example: `tenant_a/usaid_ads201`)
- keep `GRANTFLOW_ALLOWED_TENANTS` non-empty when authz is enabled; `/health` and `/ready` emit warning `TENANT_AUTHZ_ENABLED_WITHOUT_ALLOWLIST` if allowlist is empty
- if `GRANTFLOW_DEFAULT_TENANT` is set, include it in `GRANTFLOW_ALLOWED_TENANTS`; otherwise `/health` and `/ready` emit warning `TENANT_DEFAULT_NOT_IN_ALLOWLIST`
- set `GRANTFLOW_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE=strict` to fail startup and degrade `/ready` on invalid tenant authz config (empty allowlist or default tenant mismatch)

### 10) Export artifacts

```bash
# 1) Fetch server-generated export payload (safe JSON)
curl -s http://127.0.0.1:8000/status/<JOB_ID>/export-payload \
  -o export_payload.json

# 2) Submit payload to export endpoint
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  --data-binary @export_payload.json \
  -o grantflow_export.zip
```

Do not build export JSON via shell substitution; use `GET /status/{job_id}/export-payload` and pass the file directly.

If runtime grounded gate export pass policy is enabled (`GRANTFLOW_EXPORT_REQUIRE_GROUNDED_GATE_PASS=true`), blocked exports return:

```json
{
  "detail": {
    "reason": "runtime_grounded_quality_gate_block"
  }
}
```

## Core API

- `GET /health`, `GET /ready`, `GET /donors`
- `GET /generate/presets`
  - unified generate preset catalog (`legacy` + `rbm`) with ready-to-send `generate_payload`
  - Demo Console generate preset loading uses this endpoint (or bundled `/demo/presets` when available)
- `GET /generate/presets/{preset_key}`
  - unified generate preset detail with optional runtime overrides: `llm_mode`, `hitl_enabled`, `architect_rag_enabled`, `strict_preflight`
- `GET /ingest/presets`, `GET /ingest/presets/{preset_key}`
  - Demo Console loads ingest preset metadata/checklists from these endpoints at runtime
- `GET /demo/presets`
  - bundled payload for Demo Console (`generate_presets` + `ingest_presets`) to reduce startup round-trips
- `POST /generate/preflight`, `POST /generate`, `POST /generate/from-preset`, `POST /generate/from-preset/batch`, `POST /cancel/{job_id}`, `POST /resume/{job_id}`
  - `tenant_id` supported on `generate/preflight`, `generate`, and `generate/from-preset`
  - `generate/from-preset` supports `preset_type=auto|legacy|rbm`, optional runtime overrides, and `input_context_patch`
  - `generate/from-preset/batch` accepts up to 25 preset jobs in one call and returns per-item results (`accepted` / `error`)
  - lifecycle idempotency via `request_id` (query/body) or `X-Request-Id` is supported for `generate`, `cancel`, `resume`, and `hitl/approve`
- `GET /status/{job_id}` plus:
  - `/citations`, `/versions`, `/diff`, `/events`, `/events/export`, `/hitl/history`, `/hitl/history/export`, `/metrics`, `/quality`, `/grounding-gate`, `/critic`, `/comments`, `/comments/export`
  - `/review/workflow`, `/review/workflow/export`, `/review/workflow/trends`, `/review/workflow/trends/export`
  - `/review/workflow/sla`, `/review/workflow/sla/export`, `/review/workflow/sla/trends`, `/review/workflow/sla/trends/export`
  - `/review/workflow/sla/hotspots`, `/review/workflow/sla/hotspots/export`, `/review/workflow/sla/hotspots/trends`, `/review/workflow/sla/hotspots/trends/export`
  - `GET /status/{job_id}/review/workflow/sla/profile`
  - `POST /status/{job_id}/review/workflow/sla/recompute`
    - optional body: `finding_sla_hours` (`high|medium|low`), `default_comment_sla_hours`, `use_saved_profile`
    - applied profile is stored in `client_metadata.sla_profile`
  - `POST /status/{job_id}/critic/findings/{finding_id}/ack|open|resolve`
  - `POST /status/{job_id}/critic/findings/bulk-status`
  - `GET /status/{job_id}/events/export` supports `format=csv|json`, `gzip=true|false`
  - `GET /status/{job_id}/hitl/history/export` supports `event_type`, `checkpoint_id`, `format=csv|json`, `gzip=true|false`
  - `GET /status/{job_id}/comments/export` supports `section`, `status`, `version_id`, `format=csv|json`, `gzip=true|false`
  - `GET /status/{job_id}/review/workflow` filters: `event_type`, `finding_id`, `comment_status`, `workflow_state (pending|overdue)`, `overdue_after_hours`
  - `GET /status/{job_id}/review/workflow/sla/hotspots` and `/status/{job_id}/review/workflow/sla/hotspots/trends` filters: `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours`, `top_limit`, `hotspot_kind`, `hotspot_severity`, `min_overdue_hours`
- `GET /portfolio/metrics` and `/portfolio/metrics/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`
- `GET /portfolio/quality` and `/portfolio/quality/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `finding_status`, `finding_severity`
- `GET /portfolio/review-workflow` and `/portfolio/review-workflow/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `toc_text_risk_level`, `event_type`, `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours`
- `GET /portfolio/review-workflow/sla` and `/portfolio/review-workflow/sla/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `toc_text_risk_level`, `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours`, `top_limit`
- `GET /portfolio/review-workflow/sla/hotspots` and `/portfolio/review-workflow/sla/hotspots/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `toc_text_risk_level`, `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours`, `top_limit`, `hotspot_kind`, `hotspot_severity`, `min_overdue_hours`
- `GET /portfolio/review-workflow/sla/hotspots/trends` and `/portfolio/review-workflow/sla/hotspots/trends/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `toc_text_risk_level`, `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours`, `top_limit`, `hotspot_kind`, `hotspot_severity`, `min_overdue_hours`
- `GET /portfolio/review-workflow/trends`, `/portfolio/review-workflow/trends/export`, `/portfolio/review-workflow/sla/trends`, `/portfolio/review-workflow/sla/trends/export` support filters:
  - `donor_id`, `tenant_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `toc_text_risk_level`, `finding_id`, `finding_code`, `finding_section`, `comment_status`, `workflow_state`, `overdue_after_hours` (`event_type` is available on review-workflow trends)
- `POST /hitl/approve`, `GET /hitl/pending` (`tenant_id` supported)
- `POST /ingest`, `GET /ingest/recent`, `GET /ingest/inventory`, `GET /ingest/inventory/export`
  - `tenant_id` supported on ingest and ingest read endpoints
- `POST /export`

## API Reference (Advanced)

- `GET /generate/presets/legacy`, `GET /generate/presets/legacy/{preset_key}`
  - legacy preset catalog and detailed payload lookup
- `GET /generate/presets/rbm`, `GET /generate/presets/rbm/{sample_id}`
  - RBM sample catalog and detailed payload lookup
  - optional runtime flags on detail endpoint: `llm_mode`, `hitl_enabled`, `architect_rag_enabled`, `strict_preflight`

## Evaluation

Run baseline + grounded deterministic eval locally:

```bash
mkdir -p eval-artifacts

# Baseline suite + regression comparison
python -m grantflow.eval.harness \
  --text-out eval-artifacts/eval-report.txt \
  --json-out eval-artifacts/eval-report.json \
  --compare-to-baseline grantflow/eval/fixtures/baseline_regression_snapshot.json \
  --comparison-text-out eval-artifacts/eval-comparison.txt \
  --comparison-json-out eval-artifacts/eval-comparison.json

# Grounded deterministic suite
python -m grantflow.eval.harness \
  --cases-file grantflow/eval/cases/grounded_cases.json \
  --seed-rag-manifest docs/rag_seed_corpus/ingest_manifest.jsonl \
  --suite-label grounded-eval \
  --text-out eval-artifacts/grounded-eval-report.txt \
  --json-out eval-artifacts/grounded-eval-report.json \
  --compare-to-baseline grantflow/eval/fixtures/grounded_regression_snapshot.json \
  --comparison-text-out eval-artifacts/grounded-regression-comparison.txt \
  --comparison-json-out eval-artifacts/grounded-regression-comparison.json

# Grounded tail suite (EU/GIZ/UN agencies)
python -m grantflow.eval.harness \
  --cases-file grantflow/eval/cases/grounded_tail_cases.json \
  --seed-rag-manifest docs/rag_seed_corpus/ingest_manifest.jsonl \
  --suite-label grounded-tail-eval \
  --text-out eval-artifacts/grounded-tail-eval-report.txt \
  --json-out eval-artifacts/grounded-tail-eval-report.json \
  --compare-to-baseline grantflow/eval/fixtures/grounded_tail_regression_snapshot.json \
  --comparison-text-out eval-artifacts/grounded-tail-regression-comparison.txt \
  --comparison-json-out eval-artifacts/grounded-tail-regression-comparison.json

# grounded_cases.json is a strict gate:
# high quality/critic minima + zero fallback namespace citations + low non-retrieval and traceability-gap limits.
# the run also performs trend-regression check versus `grounded_regression_snapshot.json`.

# Grounded A/B (architect RAG on vs off, metrics-only)
python -m grantflow.eval.harness \
  --cases-file grantflow/eval/cases/grounded_cases.json \
  --seed-rag-manifest docs/rag_seed_corpus/ingest_manifest.jsonl \
  --suite-label grounded-ab-a \
  --skip-expectations \
  --text-out eval-artifacts/grounded-ab-a-report.txt \
  --json-out eval-artifacts/grounded-ab-a-report.json

python -m grantflow.eval.harness \
  --cases-file grantflow/eval/cases/grounded_cases.json \
  --seed-rag-manifest docs/rag_seed_corpus/ingest_manifest.jsonl \
  --suite-label grounded-ab-b \
  --skip-expectations \
  --force-no-architect-rag \
  --text-out eval-artifacts/grounded-ab-b-report.txt \
  --json-out eval-artifacts/grounded-ab-b-report.json

python scripts/eval_ab_diff.py \
  --a-json eval-artifacts/grounded-ab-a-report.json \
  --b-json eval-artifacts/grounded-ab-b-report.json \
  --a-label architect_rag_on \
  --b-label architect_rag_off \
  --guard-donors usaid,eu,worldbank,state_department \
  --max-a-non-retrieval-rate 0.25 \
  --min-a-retrieval-grounded-rate 0.75 \
  --max-a-traceability-gap-rate 0.10 \
  --min-a-non-retrieval-improvement-vs-b 0.25 \
  --min-a-retrieval-grounded-improvement-vs-b 0.25 \
  --text-out eval-artifacts/grounded-ab-diff.txt \
  --json-out eval-artifacts/grounded-ab-diff.json

python scripts/build_grounded_gate_summary.py \
  --grounded-json eval-artifacts/grounded-eval-report.json \
  --grounded-comparison-json eval-artifacts/grounded-regression-comparison.json \
  --ab-diff-json eval-artifacts/grounded-ab-diff.json \
  --expected-donors usaid,eu,worldbank,state_department \
  --min-seeded-total 1 \
  --out eval-artifacts/grounded-gate-summary.md
```

One-command variant:

```bash
make eval-grounded-ab
make eval-grounded-tail
```

For live Docker runtime checks against the running `grantflow_api` container:

```bash
# seed only the donors you want to verify against the live API/Chroma runtime
make seed-live-corpus LIVE_SEED_DONORS=eu,worldbank,giz,state_department

# run a targeted strict grounded check inside the container runtime
make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/grounded_cases.json \
  GROUNDED_TARGET_CASE_IDS="state_department_media_georgia_grounded"

# strict donor-specific case from the LLM grounded suite (still works in deterministic mode if case llm_mode=false)
make eval-grounded-target-live \
  GROUNDED_TARGET_CASES_FILE=grantflow/eval/cases/llm_grounded_strict_cases.json \
  GROUNDED_TARGET_CASE_IDS="giz_sme_resilience_jordan_grounded_strict"
```

`seed-live-corpus` uses `docs/rag_seed_corpus/bulk_ingest_seed_corpus.sh` and respects `LIVE_SEED_DONORS` as a comma-separated donor filter. `eval-grounded-target-live` writes `eval-artifacts/grounded-target-live.txt` and `.json` by default using the actual container runtime rather than the local Python environment.

A compact live verification summary for the currently checked donor paths is in `docs/grounded-donor-scoreboard.md`.
A compact live export verification summary is in `docs/export-readiness-scoreboard.md`.

`--seed-rag-manifest` resolves each manifest `donor_id` via `DonorFactory` and ingests into the donor strategy RAG namespace (for example, `usaid -> usaid_ads201`, `state_department -> us_state_department_guidance`).
Use `scripts/check_seeded_corpus.py` to fail fast when seeded artifacts are missing:

```bash
python scripts/check_seeded_corpus.py \
  --json eval-artifacts/grounded-eval-report.json \
  --expected-donors usaid,eu,worldbank,state_department \
  --min-seeded-total 1
```

Low-budget LLM exploratory run (subset only, deterministic sample):

```bash
python -m grantflow.eval.harness \
  --suite-label llm-eval-sampled \
  --force-llm \
  --force-architect-rag \
  --skip-expectations \
  --max-cases 2 \
  --sample-seed 42 \
  --text-out eval-artifacts/llm-eval-sampled.txt \
  --json-out eval-artifacts/llm-eval-sampled.json
```

One-command variant:

```bash
make eval-llm-sampled
```

Strict grounded LLM gate (all specialized donors; seeded corpus readiness required before run):

```bash
python -m grantflow.eval.harness \
  --suite-label llm-eval-grounded-strict \
  --cases-file grantflow/eval/cases/llm_grounded_strict_cases.json \
  --donor-id usaid,eu,worldbank,giz,state_department \
  --force-llm \
  --force-architect-rag \
  --seed-rag-manifest docs/rag_seed_corpus/ingest_manifest.jsonl \
  --require-seed-readiness \
  --seed-readiness-min-per-family 1 \
  --compare-to-baseline grantflow/eval/fixtures/llm_grounded_strict_regression_snapshot.json \
  --comparison-text-out eval-artifacts/llm-eval-grounded-strict-comparison.txt \
  --comparison-json-out eval-artifacts/llm-eval-grounded-strict-comparison.json \
  --text-out eval-artifacts/llm-eval-grounded-strict-report.txt \
  --json-out eval-artifacts/llm-eval-grounded-strict-report.json
```

One-command variant:

```bash
make eval-llm-grounded-strict
```

`make eval-llm-grounded-strict` also runs donor-specific aggregate quality gate thresholds from
`grantflow/eval/fixtures/llm_grounded_strict_donor_gate_thresholds.json` and writes:
- `eval-artifacts/llm-eval-grounded-strict-donor-gate.json`
- `eval-artifacts/llm-eval-grounded-strict-donor-gate.txt`
- `eval-artifacts/llm-eval-grounded-strict-comment.md`
- `eval-artifacts/llm-eval-grounded-strict-summary.md` (unified donor table + gate/comparison status)

GitHub workflow `.github/workflows/llm-eval-grounded-strict.yml` enforces strict mode:
it does not expose `skip_expectations` input; strict lane runs with expectations enabled only.
For filtered manual runs (subset `donor_ids` or explicit `case_ids`), workflow auto-enables
`--baseline-ignore-missing-current-cases` to suppress expected baseline "missing case" warnings.
Local `make eval-llm-grounded-strict` enforces the same policy via donor gate check.

`LLM Eval (Grounded)` workflow also publishes unified summary (`llm-eval-grounded-summary.md`) and supports
optional trend comparison via workflow input `compare_to_baseline`; subset runs auto-enable
`--baseline-ignore-missing-current-cases` for cleaner comparison output.

`llm_grounded_strict_cases.json` includes explicit `expected_doc_families` per donor.
When `--require-seed-readiness` is enabled, harness fails before case execution if required
doc families are missing in seeded corpus.

Run bundled RBM sample presets (from `docs/samples/*.json`) with explicit sample IDs:

```bash
python -m grantflow.eval.harness \
  --suite-label rbm-sample-eval \
  --sample-id rbm-usaid-ai-civil-service-kazakhstan,rbm-eu-youth-employment-jordan \
  --skip-expectations \
  --text-out eval-artifacts/rbm-sample-eval.txt \
  --json-out eval-artifacts/rbm-sample-eval.json
```

One-command variant:

```bash
make eval-rbm-samples
```

Tune guard via environment variables if needed:

```bash
GROUNDED_GUARD_DONORS=usaid,worldbank GROUNDED_MAX_NON_RETRIEVAL=0.25 GROUNDED_MIN_RETRIEVAL_GROUNDED=0.75 GROUNDED_MAX_TRACEABILITY_GAP=0.10 GROUNDED_MIN_NON_RETRIEVAL_IMPROVEMENT=0.25 GROUNDED_MIN_RETRIEVAL_GROUNDED_IMPROVEMENT=0.25 make eval-grounded-ab
```

CI uploads `eval-report`; grounded tail artifacts (`grounded-tail-eval-report`) are published by nightly workflow `.github/workflows/nightly-grounded-tail.yml` (or manual dispatch).
Strict grounded LLM gate artifacts (`llm-eval-grounded-strict-report` + `llm-eval-grounded-strict-comparison`) are published by `.github/workflows/llm-eval-grounded-strict.yml` (nightly + manual dispatch).

Refresh grounded trend baseline intentionally after expected quality changes:

```bash
ALLOW_BASELINE_REFRESH=1 make refresh-grounded-baseline
```

## Deployment

```bash
git clone https://github.com/vassiliylakhonin/grantflow.git
cd grantflow
docker-compose up --build
```

By default, compose starts `api + worker + redis + chroma`.
The bundled compose profile is demo/dev-oriented (`GRANTFLOW_ENV=dev`) and is not a hardened production deployment template.

Production rollout checklist:
- `docs/deployment-checklist.md`

Production preflight checks:

```bash
make preflight-prod-api
make preflight-prod-worker
```

## Reality Check

GrantFlow is production-oriented backend infrastructure, but not a “one-click donor submission” system.

Current constraints:
- final compliance sign-off remains human responsibility
- grounded quality depends on uploaded corpus relevance
- background_tasks is still the default local mode; recommended production mode is redis queue + worker

## Sample Outputs

- Sample artifacts index: `docs/samples/README.md`
- Sample ToC export (`.docx`): `docs/samples/grantflow-sample-toc-review-package.docx`
- Sample LogFrame export (`.xlsx`): `docs/samples/grantflow-sample-logframe-review-package.xlsx`
- Sample export payload (`.json`): `docs/samples/grantflow-sample-export-payload.json`
- Sample RBM logic model (`.md`): `docs/samples/rbm-logic-model-ai-civil-service-kazakhstan.md`
- Sample RBM logic model (`.md`): `docs/samples/rbm-logic-model-eu-youth-employment-jordan.md`
- Sample RBM payloads (`.json`): `docs/samples/rbm-sample-usaid-ai-civil-service-kazakhstan.json`, `docs/samples/rbm-sample-eu-youth-employment-jordan.json`

## Documentation

- Full guide: `docs/full-guide.md`
- Buyer one-pager: `docs/buyer-one-pager.md`
- Architecture overview: `docs/architecture.md`
- Deployment checklist: `docs/deployment-checklist.md`
- Pilot evaluation checklist: `docs/pilot-evaluation-checklist.md`
- Troubleshooting guide: `docs/troubleshooting.md`
- Contributor map: `docs/contributor-map.md`
- Operator runbook: `docs/operations-runbook.md`
- Demo runbook + 5-minute founder script: `docs/demo-runbook.md`
- Productization gaps memo: `docs/productization-gaps-memo.md`
- Security policy: `SECURITY.md`
- Contribution process: `CONTRIBUTING.md`
- Git/PR process: `docs/git-process.md`
- API stability policy: `docs/api-stability-policy.md`
- Release process: `docs/release-process.md`
- Release guard script: `scripts/release_guard.py`
- Runtime version source: `grantflow/core/version.py`
- Changelog: `CHANGELOG.md`

## License

MIT (`LICENSE`).
