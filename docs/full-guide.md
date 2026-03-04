# GrantFlow Full Guide

## 1) Product Scope

GrantFlow is an API-first backend for institutional proposal operations.

It is designed to support drafting workflows where teams need:
- structure (ToC / LogFrame / MEL artifacts)
- auditability (citations, versions, events)
- review control (HITL checkpoints)

It does not replace formal donor compliance review.

## 2) Pipeline Model

Execution graph:

`discovery -> architect -> mel -> critic`

Behavior:
- `discovery`: validates and normalizes input contract
- `architect`: drafts structured ToC under donor strategy contract
- `mel`: builds indicators and logframe-oriented artifacts
- `critic`: scores and reports structured findings

With HITL enabled, graph pauses at:
- ToC checkpoint (after architect)
- LogFrame checkpoint (after mel)

Resume requires explicit checkpoint decision.

## 3) Donor Strategy Model

Specialized strategies:
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (`state_department` alias)

Other catalog donors use generic strategy with shared drafting behavior.

Use `GET /donors` to resolve canonical IDs and aliases at runtime.

## 4) Run Modes

### Deterministic lane
- `llm_mode=false`
- best for CI, regression, and reproducible smoke checks

### LLM lane
- `llm_mode=true`
- quality depends on model/provider + prompts + corpus

### RAG grounding
- RAG quality is corpus-dependent
- without relevant ingest corpus, citation quality can degrade to fallback/low-confidence
- grounding gate policy can be configured with `GRANTFLOW_GROUNDING_GATE_MODE=off|warn|strict`
- in `strict` mode, weak grounding signals can block job finalization and `/export` (override via `allow_unsafe_export=true`)

## 5) Quick Start

### Install

```bash
pip install .
```

Development setup (tests/type checks/formatters):

```bash
pip install ".[dev]"
```

### Start API

```bash
uvicorn grantflow.api.app:app --reload
```

Optional queue mode (`redis_queue`):

```bash
export GRANTFLOW_JOB_RUNNER_MODE=redis_queue
export GRANTFLOW_JOB_RUNNER_CONSUMER_ENABLED=false
export GRANTFLOW_JOB_RUNNER_REDIS_URL=redis://127.0.0.1:6379/0
python -m grantflow.worker
```

This runs API as dispatcher-only and executes pipeline tasks in a dedicated worker process.

### Health/readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### Start job

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
    "hitl_enabled": false
  }'
```

### Poll status

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

### Export

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

Avoid inline shell interpolation for export payloads; use `GET /status/{job_id}/export-payload` + `--data-binary @file`.

## 6) HITL Workflow

### Step 1: Run with HITL enabled

Set `"hitl_enabled": true` in `/generate`.

### Step 2: Wait for checkpoint

Status becomes `pending_hitl` with `checkpoint_id` and `checkpoint_stage`.

### Step 3: Approve or reject checkpoint

```bash
curl -s -X POST http://127.0.0.1:8000/hitl/approve \
  -H 'Content-Type: application/json' \
  -d '{"checkpoint_id":"<CP_ID>","approved":true,"feedback":"ok"}'
```

### Step 4: Resume

```bash
curl -s -X POST http://127.0.0.1:8000/resume/<JOB_ID>
```

## 7) RAG Ingestion

Upload donor/context PDF to donor namespace:

```bash
curl -s -X POST http://127.0.0.1:8000/ingest \
  -F donor_id=usaid \
  -F file=@./ads201.pdf
```

Inventory endpoints:
- `GET /ingest/recent`
- `GET /ingest/inventory`
- `GET /ingest/inventory/export`

## 8) Export Layer

Supported export formats:
- `docx`
- `xlsx`
- `both` (ZIP)

Current donor-specific export mapping:
- USAID
- EU
- World Bank

Artifacts can include:
- citations
- critic findings
- review comments

## 9) Core Endpoints

System:
- `GET /health`
- `GET /ready`
- `GET /donors`

Jobs:
- `POST /generate`
- `POST /cancel/{job_id}`
- `POST /resume/{job_id}`
- `GET /status/{job_id}`

Review/traceability:
- `GET /status/{job_id}/citations`
- `GET /status/{job_id}/versions`
- `GET /status/{job_id}/diff`
- `GET /status/{job_id}/events`
- `GET /status/{job_id}/metrics`
- `GET /status/{job_id}/quality`
- `GET /status/{job_id}/critic`
- `POST /status/{job_id}/critic/findings/{finding_id}/ack`
- `POST /status/{job_id}/critic/findings/{finding_id}/resolve`
- `GET /status/{job_id}/comments`
- `POST /status/{job_id}/comments`
- `POST /status/{job_id}/comments/{comment_id}/resolve`
- `POST /status/{job_id}/comments/{comment_id}/reopen`

HITL:
- `POST /hitl/approve`
- `GET /hitl/pending`

RAG ingest:
- `POST /ingest`
- `GET /ingest/recent`
- `GET /ingest/inventory`
- `GET /ingest/inventory/export`

Export:
- `POST /export`

Portfolio:
- `GET /portfolio/metrics`
- `GET /portfolio/metrics/export`
- `GET /portfolio/quality`
- `GET /portfolio/quality/export`

## 10) Configuration

Common env vars:
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- `GRANTFLOW_LLM_BASE_URL`
- `OPENROUTER_HTTP_REFERER`, `OPENROUTER_X_TITLE`
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_COLLECTION_PREFIX`
- `GRANTFLOW_API_KEY`
- `GRANTFLOW_REQUIRE_AUTH_FOR_READS`
- `GRANTFLOW_JOB_STORE`, `GRANTFLOW_HITL_STORE`, `GRANTFLOW_INGEST_STORE`
- `GRANTFLOW_SQLITE_PATH`

Store alignment rule:
- `GRANTFLOW_JOB_STORE` and `GRANTFLOW_HITL_STORE` must match (`inmem` or `sqlite`).
- App startup fails fast on mismatch to prevent divergent job/HITL state after restart.

## 11) Deployment

### Docker Compose

```bash
git clone https://github.com/vassiliylakhonin/grantflow.git
cd grantflow
docker-compose up --build
```

Open:
- `http://localhost:8000/docs`
- Compose starts `api + worker + redis + chroma` by default.

## 12) Development

### Tests

```bash
python -m pytest -c grantflow/pytest.ini grantflow/tests/ -v --tb=short
```

### Lint/format/type

```bash
ruff check grantflow
isort grantflow
black grantflow
mypy grantflow/api grantflow/core/stores.py grantflow/swarm/versioning.py
```

## 13) Release and Governance

- Changelog: `CHANGELOG.md`
- Release process: `docs/release-process.md`
- API stability policy: `docs/api-stability-policy.md`
- PR/commit conventions: `CONTRIBUTING.md`

## 14) Known Limits

Current known product limits:
- final donor compliance decision is external to the system
- grounded quality requires relevant uploaded corpus
- queue-backed worker architecture is not default runtime path yet

## 15) License

MIT (`LICENSE`).
