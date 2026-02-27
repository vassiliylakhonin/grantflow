# GrantFlow

Institutional proposal workflow backend for donor-funded programs.

GrantFlow is a compliance-aware, API-first engine that turns raw project intent into structured drafting artifacts with review controls, citation traces, and exportable outputs.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

## What GrantFlow Is

GrantFlow is not a chat assistant UI. It is a backend workflow system for institutional proposal operations.

Current scope:
- Structured draft generation (ToC + MEL/LogFrame artifacts)
- Donor strategy routing (specialized + generic donors)
- Critic loop with structured findings
- Human-in-the-loop pause/approve/resume checkpoints
- Citation and version traceability
- `.docx` / `.xlsx` / ZIP export

## Why It Exists

Institutional proposals are usually:
- compliance-sensitive
- multi-stage review workflows
- evidence and citation sensitive
- high-risk submissions for teams

Most AI tools optimize text generation only. GrantFlow orchestrates the end-to-end drafting workflow.

## What It Does (Today)

- Validates incoming project context
- Selects donor strategy by canonical `donor_id` or alias
- Runs graph pipeline: `discovery -> architect -> mel -> critic`
- Records citations, draft versions, diffs, events, metrics, critic findings
- Supports HITL checkpoints with controlled resume
- Exposes review-friendly API payloads and exports

## What It Does Not Claim (Yet)

- No guarantee of donor compliance sign-off without human review
- No promise of final submission-ready narrative quality in deterministic (`llm_mode=false`) lane
- No built-in queue worker stack (current execution is API background task based)

## Donor Strategy Coverage

Specialized strategies:
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (alias: `state_department`)

Generic strategy:
- broad catalog coverage via `GET /donors` (e.g., `un_agencies`, `fcdo`, `global_fund`, `gates_foundation`, etc.)

## Quick Start

### 1) Install

```bash
pip install -r grantflow/requirements.txt
```

### 2) Run API

```bash
uvicorn grantflow.api.app:app --reload
```

API docs:
- `http://127.0.0.1:8000/docs`

### 3) Health / readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### 4) Generate draft job

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

`/generate` returns `job_id` (async). It does **not** return full artifacts inline.

### 5) Poll status

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

### 6) Export artifacts

```bash
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  -d '{"payload": {"state": {/* status.state */}}, "format": "both"}' \
  -o grantflow_export.zip
```

## Execution Modes (Important)

- `llm_mode=false`: deterministic contract-based lane (useful for CI/regression/smoke)
- `llm_mode=true`: LLM drafting lane (quality depends on model + prompts + corpus)

RAG grounding quality depends on ingest corpus relevance. Without useful donor/context corpus, citations may degrade to low-confidence or fallback namespace signals.

## HITL Flow (Current)

If `hitl_enabled=true`, pipeline pauses at checkpoints:
- after architect (`toc` checkpoint)
- after mel (`logframe` checkpoint)

Resume requires decision:
1. `POST /hitl/approve` (approve/reject)
2. `POST /resume/{job_id}`

## RAG Ingestion (Current)

Upload PDF into donor namespace:

```bash
curl -s -X POST http://127.0.0.1:8000/ingest \
  -F donor_id=usaid \
  -F file=@./ads201.pdf
```

Inventory/readiness endpoints:
- `GET /ingest/recent`
- `GET /ingest/inventory`
- `GET /ingest/inventory/export`

## Export Outputs (Current)

- `.docx` ToC package with traceability sections
- `.xlsx` LogFrame package with citations/findings/comments sheets
- donor-specific export mapping currently implemented for:
  - USAID
  - EU
  - World Bank

## API Surface (Core)

- `GET /health`, `GET /ready`, `GET /donors`
- `POST /generate`, `POST /cancel/{job_id}`, `POST /resume/{job_id}`
- `GET /status/{job_id}` and review endpoints:
  - `/citations`, `/versions`, `/diff`, `/events`, `/metrics`, `/quality`, `/critic`, `/comments`
- `POST /hitl/approve`, `GET /hitl/pending`
- `POST /ingest`, `GET /ingest/recent`, `GET /ingest/inventory`, `GET /ingest/inventory/export`
- `POST /export`

## Deployment

### Docker Compose

```bash
git clone https://github.com/vassiliylakhonin/grantflow.git
cd grantflow
docker-compose up --build
```

API:
- `http://localhost:8000/docs`

## Configuration

Common env vars:
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- `GRANTFLOW_LLM_BASE_URL` (for OpenAI-compatible providers)
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_COLLECTION_PREFIX`
- `GRANTFLOW_API_KEY` (optional endpoint protection)
- `GRANTFLOW_REQUIRE_AUTH_FOR_READS=true` (optional read protection)
- `GRANTFLOW_JOB_STORE`, `GRANTFLOW_HITL_STORE`, `GRANTFLOW_INGEST_STORE` (`inmem` or `sqlite`)
- `GRANTFLOW_SQLITE_PATH`

## Current Product Status

Production-oriented backend foundation is in place.

Still active product work:
- deeper donor-specific logic/schemas beyond current set
- stronger grounding quality and citation confidence policy
- queue-backed execution for higher concurrency/throughput
- richer reviewer UI beyond `/demo`

## Development and Release

- Contribution guide: `CONTRIBUTING.md`
- API stability policy: `docs/api-stability-policy.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`

## License

MIT (`LICENSE`).
