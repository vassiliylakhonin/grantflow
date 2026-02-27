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
pip install -r grantflow/requirements.txt
```

### 2) Run API

```bash
uvicorn grantflow.api.app:app --reload
```

OpenAPI:
- `http://127.0.0.1:8000/docs`

### 3) Health / readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

`/ready` now includes `checks.preflight_grounding_policy` with active mode and thresholds.

### 4) (Optional) Configure preflight grounding thresholds

```bash
export GRANTFLOW_GROUNDING_GATE_MODE=warn
export GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE=warn
export GRANTFLOW_PREFLIGHT_GROUNDING_HIGH_RISK_COVERAGE_THRESHOLD=0.50
export GRANTFLOW_PREFLIGHT_GROUNDING_MEDIUM_RISK_COVERAGE_THRESHOLD=0.80
export GRANTFLOW_PREFLIGHT_GROUNDING_MIN_UPLOADS=3
```

Notes:
- `GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE` controls preflight block behavior (`off|warn|strict`) and is separate from pipeline critic gate mode.
- If `GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE` is not set, it falls back to `GRANTFLOW_GROUNDING_GATE_MODE`.
- `strict_preflight=true` blocks when either readiness risk or grounding risk is `high`.

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
    "hitl_enabled": false
  }'
```

`/generate` is async and returns `job_id`.

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

### 9) Export artifacts

```bash
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  -d '{"payload": {"state": {/* status.state */}}, "format": "both"}' \
  -o grantflow_export.zip
```

## Core API

- `GET /health`, `GET /ready`, `GET /donors`
- `POST /generate/preflight`, `POST /generate`, `POST /cancel/{job_id}`, `POST /resume/{job_id}`
- `GET /status/{job_id}` plus:
  - `/citations`, `/versions`, `/diff`, `/events`, `/metrics`, `/quality`, `/critic`, `/comments`, `/review/workflow`
- `GET /portfolio/metrics` and `/portfolio/metrics/export` support filters:
  - `donor_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`
- `GET /portfolio/quality` and `/portfolio/quality/export` support filters:
  - `donor_id`, `status`, `hitl_enabled`, `warning_level`, `grounding_risk_level`, `finding_status`, `finding_severity`
- `POST /hitl/approve`, `GET /hitl/pending`
- `POST /ingest`, `GET /ingest/recent`, `GET /ingest/inventory`, `GET /ingest/inventory/export`
- `POST /export`

## Deployment

```bash
git clone https://github.com/vassiliylakhonin/grantflow.git
cd grantflow
docker-compose up --build
```

## Reality Check

GrantFlow is production-oriented backend infrastructure, but not a “one-click donor submission” system.

Current constraints:
- final compliance sign-off remains human responsibility
- grounded quality depends on uploaded corpus relevance
- queue-backed worker scaling is not yet the default runtime mode

## Documentation

- Full guide: `docs/full-guide.md`
- Contribution process: `CONTRIBUTING.md`
- API stability policy: `docs/api-stability-policy.md`
- Release process: `docs/release-process.md`
- Changelog: `CHANGELOG.md`

## License

MIT (`LICENSE`).
