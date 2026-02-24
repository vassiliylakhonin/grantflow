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

It is designed for NGOs, consultants, and program teams that need structured, reviewable drafts for institutional funding workflows.

### Outputs
- Theory of Change (ToC)
- Logical Framework / LogFrame
- MEL plan artifacts
- Exportable `.docx` / `.xlsx` (or both as ZIP)

## Key Features

- Donor strategy isolation (USAID, EU, World Bank, GIZ, U.S. State Department, plus generic donor coverage)
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
