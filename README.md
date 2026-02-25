# GrantFlow

Compliance-aware, agentic proposal drafting engine for institutional funding workflows (FastAPI + LangGraph + donor strategies + HITL).

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful%20Agents-black.svg)](https://www.langchain.com/langgraph)

GrantFlow helps NGOs, consultants, and program teams convert structured project ideas into donor-aligned drafts (ToC, LogFrame, MEL), with critique loops, citations, exportable artifacts, and human-in-the-loop checkpoints.

## Table of Contents

- [What GrantFlow Solves](#what-grantflow-solves)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Donor Coverage](#donor-coverage)
- [Quick Start](#quick-start)
- [API Overview](#api-overview)
- [Demo Console (Optional)](#demo-console-optional)
- [Human-in-the-Loop Checkpoints (MVP)](#human-in-the-loop-checkpoints-mvp)
- [RAG / Knowledge Ingestion](#rag--knowledge-ingestion)
- [Exporters](#exporters)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [Security Notes](#security-notes)
- [Roadmap](#roadmap)
- [License](#license)

## What GrantFlow Solves

GrantFlow reduces the time and effort required to turn a raw project concept into donor-aligned proposal artifacts.

It is designed for implementing organizations (e.g. DAI, Chemonics, Tetra Tech), NGOs, and program teams that need structured, reviewable drafts for institutional funding workflows.

### Outputs
- Theory of Change (ToC)
- Logical Framework / LogFrame
- MEL plan artifacts
- Exportable `.docx` / `.xlsx` (or both as ZIP)

### Estimated ROI (Early)

GrantFlow is designed to reduce drafting and review-loop overhead, not replace human review or compliance sign-off.

A practical early estimate is **~25-40% time savings** on draft/rework cycles, especially when teams repeatedly reshape the same project idea into donor-aligned formats (ToC / LogFrame / MEL).

#### Typical savings by proposal complexity (illustrative)

- **Smaller NGO / single-team proposal**: ~`8-20` drafting+rework hours baseline -> **~2-8 hours saved**
- **Multi-reviewer proposal (program + MEL + management)**: ~`20-40` hours baseline -> **~5-16 hours saved**
- **Consortium / partner-heavy / federal-style application**: ~`40+` hours baseline -> **materially higher savings**, especially in coordination and revision cycles

#### Where the savings usually come from

- faster conversion of project ideas into donor-aligned structures
- less manual reformatting/rephrasing across review rounds
- quicker internal review handoffs with HITL checkpoints
- exportable draft artifacts ready for substantive review earlier

> These are directional estimates for planning/ROI discussions. Actual savings depend on donor requirements, team maturity, and how much of the workflow is standardized.

## Key Features

- Donor strategy isolation (U.S. State Department, USAID, EU, World Bank, GIZ, plus generic donor coverage)
- Agentic workflow orchestration with LangGraph
- Critic loop for iterative quality improvement
- Human-in-the-loop checkpoints (pause/approve/resume)
- RAG-ready donor knowledge namespaces (ChromaDB)
- FastAPI backend for integration into web apps or internal tools

## Architecture Overview

GrantFlow uses a stateful graph pipeline to orchestrate specialized drafting steps:

`discovery -> architect -> mel -> critic -> (loop if needed)`

### Design principles
- Compliance-aware donor logic via Strategy Pattern
- Deterministic orchestration via LangGraph
- Explicit state transitions and job status tracking
- Review checkpoints for human governance

## Donor Coverage

GrantFlow currently supports a broad donor catalog via canonical `donor_id` values and aliases (see `GET /donors`), with two levels of support:

### Specialized strategies (donor-specific prompts / rules / schemas)
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (alias: `state_department`)

### Generic strategy coverage (catalog + aliases, shared drafting behavior)
Examples:
- `un_agencies` (aliases include `undp`, `unicef`, `unhcr`, `wfp`, `unwomen`, `unfpa`)
- `fcdo`
- `gavi`
- `global_fund`
- `gates_foundation`
- and additional bilateral / multilateral / foundation donors from the catalog

### Notes for integrators
- Use `GET /donors` to fetch the full supported list and aliases at runtime.
- Prefer canonical `donor_id` values in client integrations.
- Specialized donors provide stronger donor-specific behavior than generic donors.

## Quick Start

### 1) Install dependencies

```bash
pip install -r grantflow/requirements.txt
```

### 2) (Optional) Configure environment

```bash
export OPENAI_API_KEY=your_key_here
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export CHROMA_COLLECTION_PREFIX=grantflow
# Optional API auth (enables X-API-Key on write endpoints)
# export GRANTFLOW_API_KEY=change-me
# Optional persistence (default is in-memory)
# export GRANTFLOW_JOB_STORE=sqlite
# export GRANTFLOW_HITL_STORE=sqlite
# export GRANTFLOW_SQLITE_PATH=./grantflow_state.db
```

### 3) Run the API

```bash
uvicorn grantflow.api.app:app --reload
```

API will start on `http://127.0.0.1:8000`.

### 4) Health and readiness checks

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### 5) Generate a draft (USAID example)

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "usaid",
    "input_context": {
      "project": "Water Sanitation",
      "country": "Kenya"
    },
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

If `GRANTFLOW_API_KEY` is configured, add `-H 'X-API-Key: <your-key>'` to write requests (`/generate`, `/resume`, `/hitl/approve`, `/export`).

### 5b) Generate with webhooks (optional)

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "usaid",
    "input_context": {
      "project": "Water Sanitation",
      "country": "Kenya"
    },
    "llm_mode": false,
    "hitl_enabled": true,
    "webhook_url": "https://example.com/grantflow-webhook",
    "webhook_secret": "replace-me"
  }'
```

### 6) Check job status

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

### 7) Export artifacts (`docx`, `xlsx`, or `both`)

```bash
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  -d "{
    \"payload\": $(curl -s http://127.0.0.1:8000/status/<JOB_ID> | python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)[\"state\"]))'),
    \"format\": \"both\"
  }" \
  -o grantflow_export.zip
```

### Additional donor examples

#### GIZ (specialized strategy)

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "giz",
    "input_context": {
      "project": "Youth Employment and SME Skills",
      "country": "Jordan"
    },
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

#### U.S. Department of State (alias: `state_department`)

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "state_department",
    "input_context": {
      "project": "Independent Media Resilience",
      "country": "Georgia"
    },
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

## API Overview

Core endpoints:

- `GET /health` - service health/status
- `GET /ready` - readiness check for API + vector store backend
- `GET /donors` - supported donor catalog and aliases
- `POST /generate` - start async drafting job
- `POST /cancel/{job_id}` - cancel an accepted/running/pending HITL job (best-effort)
- `GET /status/{job_id}` - poll job status/state
- `GET /status/{job_id}/citations` - retrieve typed citation/traceability records for the job
- `GET /status/{job_id}/versions` - retrieve typed draft version history snapshots (`toc` / `logframe`)
- `GET /status/{job_id}/diff` - retrieve a unified diff between draft versions (optionally filtered by section)
- `GET /status/{job_id}/comments` - retrieve typed reviewer comments (filterable by section/status/version)
- `POST /status/{job_id}/comments` - add a reviewer comment for `toc`, `logframe`, or `general`
- `POST /status/{job_id}/comments/{comment_id}/resolve` - mark a reviewer comment as resolved
- `POST /status/{job_id}/comments/{comment_id}/reopen` - reopen a resolved reviewer comment
- `GET /status/{job_id}/events` - retrieve typed job timeline/audit trail events
- `GET /status/{job_id}/metrics` - retrieve derived workflow/ROI metrics from the job timeline
- `GET /portfolio/metrics` - retrieve aggregated ROI/ops metrics across jobs (with filters)
- `POST /resume/{job_id}` - resume a HITL-paused job
- `GET /hitl/pending` - list pending checkpoints
- `POST /hitl/approve` - approve/reject checkpoint
- `POST /ingest` - upload PDF donor guidance into donor namespace (RAG ingestion)
- `POST /export` - export outputs as `docx`, `xlsx`, or ZIP

## Demo Console (Optional)

GrantFlow includes a built-in operator/demo UI at `GET /demo` for testing the end-to-end workflow in a browser.

### What it supports

- Generate jobs and poll status
- HITL approve/reject/resume/cancel actions
- Critic findings review (fatal flaws, rule checks, citation context)
- Draft versions and diffs (with jump-to-diff shortcuts)
- Review comments (create, resolve/reopen, list filters)
- Job events and metrics
- Portfolio metrics dashboard (filters + click-to-filter counts)

### Run and open

Start the API and open:

```bash
uvicorn grantflow.api.app:app --reload
# then open http://127.0.0.1:8000/demo
```

If API auth is enabled, paste the `X-API-Key` value into the demo toolbar once and all requests will use it.

### Webhook events (optional)

When `webhook_url` is provided in `POST /generate`, GrantFlow sends job lifecycle events:

- `job.started`
- `job.pending_hitl`
- `job.completed`
- `job.failed`
- `job.canceled`

Webhook payload shape:

```json
{
  "event": "job.completed",
  "job_id": "uuid",
  "status": "done",
  "job": {
    "status": "done",
    "state": { "...": "..." },
    "hitl_enabled": false,
    "webhook_configured": true
  }
}
```

If `webhook_secret` is provided, requests include `X-GrantFlow-Signature` with an HMAC SHA-256 signature of the raw request body:

```text
X-GrantFlow-Signature: sha256=<hex_digest>
```

Webhook retries/backoff (optional env vars):

- `GRANTFLOW_WEBHOOK_MAX_ATTEMPTS` (default `3`)
- `GRANTFLOW_WEBHOOK_TIMEOUT_S` (default `5.0`)
- `GRANTFLOW_WEBHOOK_BACKOFF_BASE_MS` (default `250`)
- `GRANTFLOW_WEBHOOK_BACKOFF_MAX_MS` (default `2000`)

### Citation traceability (optional)

`GET /status/{job_id}/citations` returns a typed, integration-friendly view of citation traces collected during drafting (for example, RAG hits used by the MEL step).

Example response shape:

```json
{
  "job_id": "uuid",
  "status": "done",
  "citation_count": 2,
  "citations": [
    {
      "stage": "mel",
      "citation_type": "rag_result",
      "namespace": "usaid_ads201",
      "source": "/path/to/usaid_guidance.pdf",
      "page": 12,
      "chunk": 3,
      "chunk_id": "usaid_ads201_p12_c0",
      "used_for": "EG.3.2-1",
      "label": "USAID ADS 201 p.12",
      "excerpt": "..."
    }
  ]
}
```

### Draft version history and diffs (optional)

GrantFlow records draft snapshots during the pipeline (for example, ToC drafts from `architect` and logframe drafts from `mel`), which makes review loops easier to audit.

List versions:

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/versions
curl -s "http://127.0.0.1:8000/status/<JOB_ID>/versions?section=toc"
```

Get a diff (latest two versions in a section by default):

```bash
curl -s "http://127.0.0.1:8000/status/<JOB_ID>/diff?section=toc"
curl -s "http://127.0.0.1:8000/status/<JOB_ID>/diff?from_version_id=toc_v1&to_version_id=toc_v2"
```

Example diff response shape:

```json
{
  "job_id": "uuid",
  "status": "done",
  "section": "toc",
  "from_version_id": "toc_v1",
  "to_version_id": "toc_v2",
  "has_diff": true,
  "diff_text": "--- toc_v1\n+++ toc_v2\n@@ ...",
  "diff_lines": ["--- toc_v1", "+++ toc_v2", "@@ ..."]
}
```

### Review comments (optional)

GrantFlow supports lightweight reviewer comments tied to a job and optionally to a specific draft version (`version_id`) for `toc` / `logframe` sections.

If `GRANTFLOW_API_KEY` is configured, send `X-API-Key` on comment write actions (`POST /status/{job_id}/comments`, `resolve`, `reopen`).

List comments (with optional filters):

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/comments
curl -s "http://127.0.0.1:8000/status/<JOB_ID>/comments?section=toc&status=open"
```

Add a comment:

```bash
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments \
  -H 'Content-Type: application/json' \
  -d '{
    "section": "toc",
    "message": "Please tighten assumptions and clarify beneficiary targeting.",
    "author": "reviewer-1",
    "version_id": "toc_v2"
  }'
```

Resolve / reopen a comment:

```bash
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments/<COMMENT_ID>/resolve
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments/<COMMENT_ID>/reopen
```

Example comment response shape:

```json
{
  "comment_id": "uuid",
  "ts": "2026-02-24T12:00:00+00:00",
  "section": "toc",
  "status": "open",
  "message": "Please tighten assumptions and clarify beneficiary targeting.",
  "author": "reviewer-1",
  "version_id": "toc_v2"
}
```

### Job timeline and metrics (optional)

GrantFlow also exposes a typed job timeline (`events`) and derived workflow metrics (`metrics`) for auditability and ROI tracking.

Get timeline events:

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/events
```

Get derived metrics:

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/metrics
```

Get aggregated portfolio metrics (optional filters):

```bash
curl -s http://127.0.0.1:8000/portfolio/metrics
curl -s "http://127.0.0.1:8000/portfolio/metrics?donor_id=usaid&status=done&hitl_enabled=true"
```

Example metrics response shape:

```json
{
  "job_id": "uuid",
  "status": "done",
  "event_count": 12,
  "status_change_count": 8,
  "pause_count": 1,
  "resume_count": 1,
  "time_to_first_draft_seconds": 42.7,
  "time_to_terminal_seconds": 185.3,
  "time_in_pending_hitl_seconds": 96.2,
  "terminal_status": "done"
}
```

Example portfolio metrics response shape:

```json
{
  "job_count": 24,
  "filters": {
    "donor_id": "usaid",
    "status": "done",
    "hitl_enabled": true
  },
  "status_counts": {
    "done": 24
  },
  "donor_counts": {
    "usaid": 24
  },
  "terminal_job_count": 24,
  "hitl_job_count": 24,
  "total_pause_count": 24,
  "total_resume_count": 24,
  "avg_time_to_first_draft_seconds": 48.2,
  "avg_time_to_terminal_seconds": 210.4,
  "avg_time_in_pending_hitl_seconds": 102.7
}
```

## Human-in-the-Loop Checkpoints (MVP)

GrantFlow supports pause/approve/resume checkpoints in the drafting flow.

- ToC checkpoint after architect step
- LogFrame checkpoint after MEL step
- Resume behavior depends on approval vs rejection
- Job status transitions include `pending_hitl`

## RAG / Knowledge Ingestion

GrantFlow is RAG-ready and uses ChromaDB namespaces for donor knowledge.

- Namespace isolation via collection prefix (`CHROMA_COLLECTION_PREFIX`)
- Persistent Chroma client by default (`./chroma_db`)
- In-memory fallback behavior for local/offline smoke tests
- Donor strategies can map to donor-specific knowledge collections

## Exporters

Current exporters generate:

- `.docx` from ToC content
- `.xlsx` from LogFrame content
- ZIP bundle when `format="both"`

## Project Structure

```text
grantflow/
  api/              FastAPI app and endpoints
  core/             config + donor strategy logic
  exporters/        Word/Excel artifact builders
  memory_bank/      Chroma wrapper / vector store
  swarm/            LangGraph pipeline + nodes + HITL
  tests/            pytest suite
```

Top-level scripts:

- `deploy.sh` - local/production Docker deployment helper
- `backup.sh` - ChromaDB backup rotation helper

## Development

Local development loop:

```bash
pip install -r grantflow/requirements.txt
uvicorn grantflow.api.app:app --reload
```

Optional dev tooling (format/lint hooks):

```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
```

Manual formatting/lint commands (if you prefer running tools directly):

```bash
ruff check grantflow
isort grantflow
black grantflow
mypy grantflow/api grantflow/core/stores.py grantflow/swarm/versioning.py
```

Optional environment variables:

- `OPENAI_API_KEY`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_COLLECTION_PREFIX`
- `CHROMA_PERSIST_DIRECTORY`
- `GRANTFLOW_API_KEY` (if set, write endpoints require `X-API-Key`)
- `GRANTFLOW_REQUIRE_AUTH_FOR_READS` (`true` to require `X-API-Key` for `/status` and `/hitl/pending`)
- `GRANTFLOW_JOB_STORE` (`inmem` or `sqlite`)
- `GRANTFLOW_HITL_STORE` (`inmem` or `sqlite`, defaults to job store mode)
- `GRANTFLOW_SQLITE_PATH` (SQLite file path for job/HITL persistence)
- `GRANTFLOW_WEBHOOK_MAX_ATTEMPTS`
- `GRANTFLOW_WEBHOOK_TIMEOUT_S`
- `GRANTFLOW_WEBHOOK_BACKOFF_BASE_MS`
- `GRANTFLOW_WEBHOOK_BACKOFF_MAX_MS`

### Docker Compose persistence/auth notes

- `docker-compose.yml` is configured to use SQLite-backed job/HITL persistence by default.
- API state DB is stored in the `grantflow_state` volume (`/data/grantflow_state.db` in the container).
- To protect write endpoints in deployment, set `GRANTFLOW_API_KEY` in your `.env` and send `X-API-Key` from clients.
- If you use webhooks, prefer HTTPS endpoints and set `webhook_secret` to verify `X-GrantFlow-Signature`.

## Testing

Run tests:

```bash
python -m pytest -c grantflow/pytest.ini grantflow/tests/ -v --tb=short
```

Shell checks:

```bash
bash -n deploy.sh
bash -n backup.sh
shellcheck deploy.sh backup.sh
```

CI runs Python tests, shell script lint/syntax checks, and a targeted `mypy` baseline (`grantflow/api`, `grantflow/core/stores.py`, `grantflow/swarm/versioning.py`).

If you enable local pre-commit hooks, they will also run `ruff`, `isort`, and `black` before commit.

## Security Notes

- Do not commit real API keys in `.env`
- Review generated proposal content before external submission
- Treat donor guidance and uploaded source materials as sensitive
- Validate exported artifacts in your internal QA/compliance workflow

## Roadmap

- Expand donor-specific strategies, schemas, and validation rules
- Improve citation grounding quality (ranking, confidence, and evidence fidelity)
- Evolve the review UI beyond the demo console (section comments, diff navigation, reviewer workflows)
- Strengthen donor-ready export templates and formatting controls
- Broaden reliability/test coverage for concurrency, persistence, and failure recovery edge cases

## License

MIT. See `LICENSE` for the full license text.
