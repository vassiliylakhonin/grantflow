# AidGraph v2.0

Enterprise-grade grant proposal automation for USAID, EU, World Bank.

[![CI](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml)

## Features

- **Donor Strategies**: USAID, EU, World Bank with isolated RAG namespaces
- **LangGraph State Machine**: Cyclical Red Teaming (max 3 iterations)
- **HITL**: Human-in-the-Loop approval points
- **Exporters**: .docx (ToC) and .xlsx (LogFrame)
- **ChromaDB RAG**: Namespace-isolated vector store

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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/donors` | GET | List supported donors |
| `/generate` | POST | Start generation |
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
