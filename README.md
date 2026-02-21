# AidGraph v2.0

**Enterprise-grade grant proposal automation for international donors**

[![CI](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/aidgraph-prod/actions/workflows/ci.yml)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

---

## 🎯 Overview

AidGraph automates the creation of grant proposals for major international donors:

- **USAID** (ADS 201 compliant)
- **European Union** (INTPA guidelines)
- **World Bank** (ADS 301 framework)
- **United Nations** (coming soon)

Built with **LangGraph** for stateful orchestration, **ChromaDB** for RAG-based document retrieval, and **FastAPI** for production-ready APIs.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Donor Strategy Pattern** | Isolated logic per donor with dedicated RAG namespaces |
| **LangGraph State Machine** | Cyclical Red Teaming (max 3 iterations, quality threshold ≥8.0) |
| **Human-in-the-Loop (HITL)** | Approval checkpoints after ToC and LogFrame generation |
| **RAG Integration** | ChromaDB with namespace isolation (`usaid_ads201`, `eu_intpa`, `worldbank_ads301`) |
| **Export Engines** | `.docx` (Theory of Change) and `.xlsx` (LogFrame with indicators) |
| **Production Ready** | Docker, CI/CD, health checks, automated backups |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AidGraph API                            │
│                    (FastAPI + LangGraph)                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Discovery   │───▶│   Architect   │───▶│     MEL       │
│   (Validate)  │    │   (ToC Draft) │    │  (Indicators) │
└───────────────┘    └───────────────┘    └───────────────┘
                             │                     │
                             └──────────┬──────────┘
                                        ▼
                               ┌───────────────┐
                               │     Critic    │
                               │ (Red Team QA) │
                               └───────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                   Score < 8.0                   Score ≥ 8.0
                          │                           │
                          ▼                           ▼
                   (Loop back)                 (Export/ HITL)
```

---

## 🚀 Quickstart

### Local Development

```bash
# Clone repository
git clone https://github.com/vassiliylakhonin/aidgraph-prod.git
cd aidgraph-prod

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r aidgraph/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY, etc.)

# Run API server
uvicorn aidgraph.api.app:app --reload --host 0.0.0.0 --port 8000

# Open Swagger UI
open http://localhost:8000/docs
```

### Production (Docker)

```bash
# Build and deploy
./deploy.sh

# View logs
docker-compose logs -f aidgraph-api

# Stop services
docker-compose down
```

---

## 📡 API Endpoints

### Core

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | `GET` | Health check |
| `/donors` | `GET` | List supported donors |
| `/generate` | `POST` | Start proposal generation |
| `/export` | `POST` | Export to `.docx` / `.xlsx` |

### HITL (Human-in-the-Loop)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hitl/pending` | `GET` | List pending approval checkpoints |
| `/hitl/approve` | `POST` | Approve or reject a checkpoint |

---

## 📋 Example Usage

### 1. Generate Proposal

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "donor_id": "USAID",
    "input_context": {
      "project": "Water Sanitation in Kenya",
      "budget": 5000000,
      "duration_months": 36,
      "target_beneficiaries": 50000
    },
    "llm_mode": true,
    "hitl_enabled": true
  }'
```

### 2. Approve HITL Checkpoint

```bash
curl -X POST http://localhost:8000/hitl/approve \
  -H "Content-Type: application/json" \
  -d '{
    "checkpoint_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true,
    "feedback": "ToC looks good, proceed to LogFrame"
  }'
```

### 3. Export Artifacts

```bash
curl -X POST http://localhost:8000/export \
  -H "Content-Type: application/json" \
  -d '{
    "toc_draft": {...},
    "logframe_draft": {...},
    "donor_id": "USAID",
    "format": "both"
  }' \
  --output proposal.zip
```

---

## 🧪 Testing

```bash
# Run all tests
pytest aidgraph/tests -v

# Run specific test file
pytest aidgraph/tests/test_integration.py -v

# Run with coverage
pytest aidgraph/tests --cov=aidgraph --cov-report=html
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIDGRAPH_API_HOST` | `0.0.0.0` | API bind host |
| `AIDGRAPH_API_PORT` | `8000` | API port |
| `AIDGRAPH_DEBUG` | `false` | Debug mode (auto-reload) |
| `AIDGRAPH_HITL_ENABLED` | `true` | Enable HITL checkpoints |
| `AIDGRAPH_MAX_ITERATIONS` | `3` | Max Red Team cycles |
| `AIDGRAPH_CRITIC_THRESHOLD` | `8.0` | Quality score threshold |
| `AIDGRAPH_CHROMA_DIR` | `./chroma_db` | ChromaDB persist directory |
| `AIDGRAPH_TOP_K` | `5` | Default RAG results |
| `AIDGRAPH_CHEAP_MODEL` | `gpt-4o-mini` | Model for drafting |
| `AIDGRAPH_REASONING_MODEL` | `gpt-4o` | Model for critique |
| `OPENAI_API_KEY` | — | OpenAI API key (required) |

---

## 📦 Project Structure

```
aidgraph-prod/
├── aidgraph/
│   ├── core/                  # Core logic
│   │   ├── donor_strategy.py  # Abstract base strategy
│   │   ├── state.py           # LangGraph state definition
│   │   ├── config.py          # Configuration loader
│   │   └── strategies/        # Donor implementations
│   │       ├── usaid.py
│   │       ├── eu.py
│   │       ├── worldbank.py
│   │       └── factory.py
│   ├── swarm/                 # LangGraph orchestration
│   │   ├── graph.py           # StateGraph builder
│   │   ├── hitl.py            # HITL checkpoint manager
│   │   └── nodes/             # Graph nodes
│   │       ├── discovery.py
│   │       ├── architect.py
│   │       ├── mel_specialist.py
│   │       └── critic.py
│   ├── memory_bank/           # RAG layer
│   │   ├── vector_store.py    # ChromaDB wrapper
│   │   └── ingest.py          # PDF ingestion script
│   ├── exporters/             # Output generators
│   │   ├── word_builder.py    # .docx exporter
│   │   └── excel_builder.py   # .xlsx exporter
│   ├── api/                   # FastAPI application
│   │   └── app.py
│   ├── tests/                 # Test suite
│   │   ├── test_integration.py
│   │   ├── test_strategies.py
│   │   └── test_vector_store.py
│   ├── requirements.txt
│   ├── pytest.ini
│   └── README.md
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── deploy.sh                  # Deployment script
├── backup.sh                  # Backup script
├── .env.example
└── README.md                  # This file
```

---

## 🔒 Security

- **No secrets in code** — Use `.env` or environment variables
- **Weekly security scans** — GitHub Actions + `safety` + `bandit`
- **Isolated RAG namespaces** — Donor data separation
- **HITL approval required** — Human oversight for critical outputs

---

## 📊 Monitoring

```bash
# Health check
curl http://localhost:8000/health

# View Docker logs
docker-compose logs -f aidgraph-api

# Check ChromaDB stats (Python)
python -c "from aidgraph.memory_bank.vector_store import vector_store; print(vector_store.get_stats('usaid_ads201'))"
```

---

## 🔄 CI/CD Pipeline

```yaml
Push to main → CI (pytest) → Build Docker → Push to GHCR → Deploy notification
```

Automated on every push to `main` branch.

---

## 📝 License

**Proprietary** — All rights reserved.

---

## 🤝 Contributing

This is a private repository. For access requests, contact the maintainer.

---

## 📞 Support

- **Issues:** https://github.com/vassiliylakhonin/aidgraph-prod/issues
- **Repository:** https://github.com/vassiliylakhonin/aidgraph-prod

---

**Built with ❤️ by AidGraph Team**

*Version 2.0 — February 2026*
