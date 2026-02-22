# AidGraph v2.0

Enterprise-grade grant proposal automation for USAID, EU, World Bank.

[![CI](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml)

## Overview

Traditional grant writing takes weeks and costs tens of thousands of dollars in consulting fees. General-purpose LLMs fail at strict donor compliance and hallucinate indicators. AidGraph solves this by combining isolated donor rulebases (RAG) with an adversarial AI Red Team that forces the output to be logically flawless and 100% compliant before a human ever sees it.

## Features

- **Donor Strategies**: USAID, EU, World Bank with isolated RAG namespaces
- **LangGraph State Machine**: Cyclical Red Teaming (max 3 iterations)
- **HITL**: Human-in-the-Loop approval points
- **Exporters**: .docx (ToC) and .xlsx (LogFrame)
- **ChromaDB RAG**: Namespace-isolated vector store
    Note: ChromaDB collections are pre-populated with official, parsed documentation including USAID ADS 201, Standard Foreign Assistance Indicators, and EU INTPA Logical Framework guidelines.

## Quickstart

### Local Development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r aidgraph/requirements.txt
cp .env.example .env
uvicorn aidgraph.api.app:app --reload
```

### Production (Docker)
```bash
cp .env.example .env
# Edit .env with your API keys
./deploy.sh
```

## API Endpoints

### Generate Proposal
Start proposal generation. Requires donor ID and input context. Returns a job ID for status tracking.

POST `/generate`
```json
{
  "donor_id": "usaid",
  "input_context": {
    "strategic_goal": "Improve WASH infrastructure and local governance in rural Kenya",
    "target_beneficiaries": "50,000 women and children",
    "budget_usd": 5000000,
    "duration_months": 36
  },
  "llm_mode": true,
  "hitl_enabled": true
}
```
**Why it Matters**: This more specific input context helps the AI generate a more targeted and compliant proposal, reducing manual refinement and saving significant time and resources.

### Other Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/donors` | GET | List supported donors |
| `/hitl/approve` | POST | Approve/reject checkpoint |
| `/hitl/pending` | GET | List pending HITL |
| `/export` | POST | Export to .docx/.xlsx |

## Test

```bash
pytest aidgraph/tests -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIDGRAPH_API_HOST` | `0.0.0.0` | API host |
| `AIDGRAPH_API_PORT` | `8000` | API port |
| `AIDGRAPH_DEBUG` | `false` | Debug mode |
| `AIDGRAPH_HITL_ENABLED` | `true` | Enable HITL |
| `OPENAI_API_KEY` | - | OpenAI API key |

## License

Proprietary — All rights reserved