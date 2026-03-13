# GrantFlow

Institutional proposal operating system: an API-first, compliance-aware workflow engine for donor-funded programs with strategy-driven drafting, HITL governance, citation traceability, and export-ready artifacts.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![Security](https://github.com/vassiliylakhonin/grantflow/actions/workflows/security.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

---

## What GrantFlow does

GrantFlow orchestrates proposal drafting as a **process**, not a single text-generation call.

Core capabilities:
- Strategy-driven drafting pipeline (ToC + MEL/LogFrame)
- Critic loop with structured findings (`id`, `severity`, `section`, `status`)
- SLA-aware review workflow (`due_at`, `sla_hours`, pending/overdue views)
- Human-in-the-loop pause/approve/resume
- Citation + version traceability
- Export to `.docx`, `.xlsx`, or ZIP bundle

---

## Who it is for

- NGOs and implementing organizations
- Consulting firms managing donor submissions
- Program/MEL teams handling institutional compliance workflows

---

## Architecture snapshot

Pipeline:

`discovery -> architect -> mel -> critic`

Optional HITL checkpoints and resume control are supported throughout.

Architect generation modes:
- `llm_mode=false`: deterministic contract synthesizer
- `llm_mode=true`: LLM structured output via donor strategy prompts + schema
- Fallback to deterministic synthesizer only when LLM mode fails/unavailable

---

## Donor coverage

Specialized strategies:
- `usaid`
- `eu`
- `worldbank`
- `giz`
- `us_state_department` (alias: `state_department`)

Generic strategy:
- broader donor catalog via `GET /donors`

---

## Quick start

### 1) Install

```bash
pip install .
```

Dev tooling:

```bash
pip install ".[dev]"
```

Recommended reproducible setup:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install ".[dev]"
```

### 2) Run API

```bash
uvicorn grantflow.api.app:app --reload
```

OpenAPI:
- http://127.0.0.1:8000/docs

### 3) Health / readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

`/ready` includes active grounding policy mode/threshold checks.

### 4) Preflight (optional but recommended)

```bash
curl -s -X POST http://127.0.0.1:8000/generate/preflight \
  -H 'Content-Type: application/json' \
  -d '{"donor_id":"usaid"}'
```

### 5) Start generation job

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

### 6) Poll status

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

### 7) Export artifacts

```bash
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  -d '{"payload": {"state": {}}, "format": "both"}' \
  -o grantflow_export.zip
```

---

## Security defaults

Production auth-by-default:
- In production (`GRANTFLOW_ENV=production`), API key is required.
- Configure `GRANTFLOW_API_KEY` (or `API_KEY`) and send `X-API-Key`.
- Break-glass override exists for exceptional cases only: `GRANTFLOW_ALLOW_NO_AUTH=true`.

Optional preflight grounding policy:

```bash
export GRANTFLOW_GROUNDING_GATE_MODE=warn
export GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE=warn
export GRANTFLOW_PREFLIGHT_GROUNDING_HIGH_RISK_COVERAGE_THRESHOLD=0.50
export GRANTFLOW_PREFLIGHT_GROUNDING_MEDIUM_RISK_COVERAGE_THRESHOLD=0.80
export GRANTFLOW_PREFLIGHT_GROUNDING_MIN_UPLOADS=3
```

---

## Core API surface

- System:
  - `GET /health`, `GET /ready`, `GET /donors`, `GET /demo`
- Generation lifecycle:
  - `POST /generate/preflight`, `POST /generate`
  - `POST /cancel/{job_id}`, `POST /resume/{job_id}`
- Job status:
  - `GET /status/{job_id}`
  - `GET /status/{job_id}/citations|versions|diff|events|metrics|quality|critic|comments`
  - `GET /status/{job_id}/export-payload`
- Review workflow:
  - `GET /status/{job_id}/review/workflow`
  - `GET /status/{job_id}/review/workflow/sla`
  - `GET /status/{job_id}/review/workflow/sla/profile`
  - `GET /status/{job_id}/review/workflow/export`
  - `POST /status/{job_id}/review/workflow/sla/recompute`
- Critic findings:
  - `POST /status/{job_id}/critic/findings/{finding_id}/ack|open|resolve`
  - `POST /status/{job_id}/critic/findings/bulk-status`
- Review comments:
  - `POST /status/{job_id}/comments`
  - `POST /status/{job_id}/comments/{comment_id}/resolve|reopen`
- Portfolio:
  - `GET /portfolio/metrics`, `GET /portfolio/metrics/export`
  - `GET /portfolio/quality`, `GET /portfolio/quality/export`
- HITL:
  - `POST /hitl/approve`, `GET /hitl/pending`
- Ingest:
  - `POST /ingest`, `GET /ingest/recent`, `GET /ingest/inventory`, `GET /ingest/inventory/export`
- Export:
  - `POST /export`

---

## Deployment

```bash
git clone https://github.com/vassiliylakhonin/grantflow.git
cd grantflow
docker-compose up --build
```

---

## Reality check

GrantFlow is production-oriented backend infrastructure, not a one-click donor submission tool.

Current constraints:
- Final compliance sign-off remains human responsibility.
- Grounded quality depends on uploaded corpus relevance.
- Queue-backed worker scaling is not yet default runtime mode.

---

## Documentation

- Full guide: `docs/full-guide.md`
- Refactor completion summary: `docs/REFACTOR_SUMMARY.md`
- Security runbook: `docs/security-ops-runbook.md`
- Container hardening runbook: `docs/container-hardening-runbook.md`
- Deployment checklist: `docs/deployment-checklist.md`
- API stability policy: `docs/api-stability-policy.md`
- Release process: `docs/release-process.md`
- Git/PR process: `docs/git-process.md`
- Contributing: `CONTRIBUTING.md`
- Changelog: `CHANGELOG.md`

---

## License

MIT (`LICENSE`).
