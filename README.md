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

### 4) Health check

```bash
curl -s http://127.0.0.1:8000/health
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
- `GET /donors` - supported donor catalog and aliases
- `POST /generate` - start async drafting job
- `GET /status/{job_id}` - poll job status/state
- `POST /resume/{job_id}` - resume a HITL-paused job
- `GET /hitl/pending` - list pending checkpoints
- `POST /hitl/approve` - approve/reject checkpoint
- `POST /export` - export outputs as `docx`, `xlsx`, or ZIP

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

Optional environment variables:

- `OPENAI_API_KEY`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_COLLECTION_PREFIX`
- `CHROMA_PERSIST_DIRECTORY`
- `GRANTFLOW_API_KEY` (if set, write endpoints require `X-API-Key`)
- `GRANTFLOW_JOB_STORE` (`inmem` or `sqlite`)
- `GRANTFLOW_HITL_STORE` (`inmem` or `sqlite`, defaults to job store mode)
- `GRANTFLOW_SQLITE_PATH` (SQLite file path for job/HITL persistence)

### Docker Compose persistence/auth notes

- `docker-compose.yml` is configured to use SQLite-backed job/HITL persistence by default.
- API state DB is stored in the `grantflow_state` volume (`/data/grantflow_state.db` in the container).
- To protect write endpoints in deployment, set `GRANTFLOW_API_KEY` in your `.env` and send `X-API-Key` from clients.

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

CI runs both Python tests and shell script lint/syntax checks.

## Security Notes

- Do not commit real API keys in `.env`
- Review generated proposal content before external submission
- Treat donor guidance and uploaded source materials as sensitive
- Validate exported artifacts in your internal QA/compliance workflow

## Roadmap

- Expand donor-specific strategies and schemas
- Improve citation grounding and evidence traceability
- Add richer review UI for HITL checkpoints
- Strengthen export templates and formatting controls
- Broaden test coverage for edge cases and failure modes

## License

MIT. See `LICENSE` for the full license text.
