# GrantFlow

Institutional proposal operating system: compliance-aware, agentic workflow engine for donor-funded programs with strategy-driven drafting, HITL governance, citation traceability, and export-ready artifacts.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

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

## Architecture (Current)

Pipeline:

`discovery -> architect -> mel -> critic`

With optional HITL checkpoints and resume control.

Architect generation modes:
- `llm_mode=false`: `deterministic:contract_synthesizer` (schema-valid non-LLM draft)
- `llm_mode=true`: LLM structured output via strategy `Architect` prompt + `get_toc_schema()`
- emergency fallback to `fallback:contract_synthesizer` only when LLM mode is requested but unavailable/invalid

## Donor Coverage

Specialized strategies:
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (alias: `state_department`)

Generic strategy:
- broader donor catalog via `GET /donors`

## Quick Start

### 1) Install

```bash
pip install .
```

For local development tooling (`pytest`, `mypy`, `ruff`, `black`, pre-commit):

```bash
pip install ".[dev]"
```

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

`/ready` now includes `checks.preflight_grounding_policy` and `checks.runtime_grounded_quality_gate` with active modes and thresholds, plus `checks.configuration_warnings` for non-blocking setup risks (for example Chroma/API port conflicts).

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
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "usaid",
    "input_context": {
      "project": "Youth Employment Initiative",
      "country": "Kenya"
    },
    "llm_mode": false,
    "architect_rag_enabled": true,
    "hitl_enabled": false
  }'
```

`architect_rag_enabled` controls Architect retrieval behavior per request (default: `true`).

`/generate` is async and returns `job_id`.

Preset-based shortcut (no manual payload assembly):

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
      "country": "Kenya"
    }
  }'
```

### 7) (Optional) Enforce strict preflight gate

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "usaid",
    "input_context": {
      "project": "Youth Employment Initiative",
      "country": "Kenya"
    },
    "llm_mode": false,
    "hitl_enabled": false,
    "strict_preflight": true
  }'
```

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
  - `/citations`, `/versions`, `/diff`, `/events`, `/hitl/history`, `/metrics`, `/quality`, `/grounding-gate`, `/critic`, `/comments`
  - `/review/workflow`, `/review/workflow/export`, `/review/workflow/trends`, `/review/workflow/trends/export`
  - `/review/workflow/sla`, `/review/workflow/sla/export`, `/review/workflow/sla/trends`, `/review/workflow/sla/trends/export`
  - `/review/workflow/sla/hotspots`, `/review/workflow/sla/hotspots/export`, `/review/workflow/sla/hotspots/trends`, `/review/workflow/sla/hotspots/trends/export`
  - `GET /status/{job_id}/review/workflow/sla/profile`
  - `POST /status/{job_id}/review/workflow/sla/recompute`
    - optional body: `finding_sla_hours` (`high|medium|low`), `default_comment_sla_hours`, `use_saved_profile`
    - applied profile is stored in `client_metadata.sla_profile`
  - `POST /status/{job_id}/critic/findings/{finding_id}/ack|open|resolve`
  - `POST /status/{job_id}/critic/findings/bulk-status`
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

## Reality Check

GrantFlow is production-oriented backend infrastructure, but not a “one-click donor submission” system.

Current constraints:
- final compliance sign-off remains human responsibility
- grounded quality depends on uploaded corpus relevance
- queue-backed worker scaling is not yet the default runtime mode

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
- Contribution process: `CONTRIBUTING.md`
- Git/PR process: `docs/git-process.md`
- API stability policy: `docs/api-stability-policy.md`
- Release process: `docs/release-process.md`
- Release guard script: `scripts/release_guard.py`
- Runtime version source: `grantflow/core/version.py`
- Changelog: `CHANGELOG.md`

## License

MIT (`LICENSE`).
