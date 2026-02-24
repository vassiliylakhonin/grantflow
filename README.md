# GrantFlow

**Compliance-aware, agentic proposal drafting engine for institutional funding workflows**

GrantFlow is a FastAPI + LangGraph backend that helps proposal teams convert structured project input into donor-aligned draft artifacts for institutional funders.

It combines donor-specific strategy isolation, stateful orchestration, critique loops, and exportable outputs to reduce proposal preparation time and review cycles.

## What Problem It Solves

Teams writing grants for major donors often lose time on the same expensive steps:

- translating raw project ideas into donor-specific structure
- aligning ToC / LogFrame logic with compliance expectations
- drafting MEL indicators with traceable justification and citations
- iterating across reviewers when logic gaps are discovered late

General-purpose LLMs can draft text, but they often fail on donor-specific structure, auditability, and consistency. GrantFlow is designed to be a **compliance-aware orchestration backend**, not a one-shot text generator.

## What GrantFlow Produces

- Theory of Change (ToC) draft
- LogFrame / MEL indicators draft
- Export files for review (`docx`, `xlsx`, or ZIP bundle)

## Positioning (Product)

GrantFlow can be described as:

- **AI-assisted grant proposal orchestration platform**
- **Agentic workflow for donor-compliant proposal drafting**
- **Multi-agent grant drafting backend (LangGraph + FastAPI)**

Practical note:
- This is an AI-assisted system with human review, not a claim of fully autonomous proposal writing.

## Architecture (MVP)

- `FastAPI` API for job orchestration and export
- `LangGraph` workflow: `discovery -> architect -> mel -> critic`
- Critic loop with quality threshold and max iterations
- Donor-specific strategy classes for prompt isolation + RAG namespace isolation
- `ChromaDB` vector store wrapper with namespace isolation
- Fallback in-memory vector backend when Chroma is unavailable (useful in local/sandboxed environments)

## Donor Coverage

GrantFlow currently supports a **catalog of 45 donors / donor groups** via `GET /donors`.

This includes:

- intergovernmental / supranational donors (EU, UN agencies cluster, World Bank/IFC, AfDB, ADB, IDB, EBRD, Global Fund, Gavi)
- major bilateral donors and agencies (USAID, U.S. Department of State, FCDO, GIZ, JICA, Sida, Norad, SDC, GAC, AFD, and others)
- private foundations and philanthropic funders (Gates Foundation, Open Society Foundations, Rockefeller Foundation, Ford Foundation, Wellcome Trust, etc.)

### Strategy Types

GrantFlow supports two levels of donor handling:

- **Specialized strategies** (custom prompts/schema today): `usaid`, `eu`, `worldbank`, `giz`, `us_state_department`
- **Generic donor strategy** (catalog-backed, donor-specific metadata + RAG namespace): all other catalog entries

Canonical donor IDs and aliases are exposed by `GET /donors`.

### Quick Reference for Integrators

| Tier | Canonical `donor_id` | Example aliases | Notes |
|------|----------------------|-----------------|-------|
| Specialized | `usaid` | `usaid.gov` | Custom strategy + donor-specific prompts/schema |
| Specialized | `eu` | `european-union`, `ec` | Custom strategy + EU-specific prompts/schema |
| Specialized | `worldbank` | `world_bank`, `ifc` | Custom strategy + World Bank prompts/schema |
| Specialized | `giz` | `deutsche_gesellschaft_fur_internationale_zusammenarbeit` | Custom GIZ strategy |
| Specialized | `us_state_department` | `state_department`, `us_department_of_state` | Custom U.S. State Department strategy |
| Generic (catalog-backed) | `un_agencies` | `undp`, `unicef`, `wfp`, `unhcr`, `unwomen`, `unfpa` | Shared UN agencies strategy metadata + namespace |
| Generic (catalog-backed) | `fcdo` | `ukaid`, `foreign_commonwealth_development_office` | Generic strategy with donor-specific metadata |
| Generic (catalog-backed) | `gavi` | `gavi_vaccine_alliance` | Generic strategy with donor-specific metadata |
| Generic (catalog-backed) | `global_fund` | `globalfund`, `the_global_fund` | Generic strategy with donor-specific metadata |
| Generic (catalog-backed) | `gates_foundation` | `gates`, `bill_and_melinda_gates_foundation` | Generic strategy with donor-specific metadata |

For the complete list (45 records), query `GET /donors`.

## Human-in-the-Loop Checkpoints (MVP)

GrantFlow currently includes **Human-in-the-Loop Checkpoints (MVP)** at the API level:

- checkpoint creation when `hitl_enabled=true`
- job status transition to `pending_hitl`
- approval/rejection endpoints for review workflows
- explicit resume endpoint (`POST /resume/{job_id}`) to continue execution after review

Current scope:
- staged pause/resume is implemented at the API/job runner level (`/generate` -> `pending_hitl` -> `/resume/{job_id}`)
- full graph-native pause/resume inside LangGraph itself is still a planned next step

This is the recommended wording for public materials today:
- **Human-in-the-loop checkpoints (MVP) for review and approval**

## API Contract (Current)

`POST /generate` expects a strict payload:

```json
{
  "donor_id": "usaid",
  "input_context": {
    "project": "Water Sanitation",
    "country": "Kenya"
  },
  "llm_mode": false,
  "hitl_enabled": false
}
```

Notes:

- `donor_id` + `input_context` are required
- older shapes such as `donor` / `input` are intentionally rejected (`422`) to keep the public contract stable
- if `llm_mode=true` but `OPENAI_API_KEY` is not set, the critic falls back to a deterministic local evaluator instead of failing the job
- donor aliases are supported (for example `state_department`, `undp`, `giz`)

## Quickstart (Local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r grantflow/requirements.txt

cp .env.example .env
# Add OPENAI_API_KEY if you want live LLM critique

uvicorn grantflow.api.app:app --reload
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

## Example Flow

Create a generation job:

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

Poll job status:

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
```

Example (specialized donor: GIZ):

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "giz",
    "input_context": {
      "project": "TVET and SME support",
      "country": "Kenya"
    },
    "llm_mode": false,
    "hitl_enabled": true
  }'
```

Example (specialized donor via alias: U.S. Department of State):

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "state_department",
    "input_context": {
      "project": "Civil society resilience",
      "country": "Georgia"
    },
    "llm_mode": false,
    "hitl_enabled": true
  }'
```

Export both artifacts as ZIP:

```bash
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  -d '{"payload": {"state": {}}, "format": "both"}'
```

(For a real export call, pass the `state` object returned by `/status/<JOB_ID>`.)

## Docker / Compose

Minimal local stack (API + Chroma) is provided:

- `Dockerfile`
- `docker-compose.yml`

Run:

```bash
docker-compose up --build
```

API will be available on `:8000`, Chroma on host `:8001`.

## Ingesting Donor Documents (RAG)

Ingest a single PDF into a donor namespace:

```bash
python -m grantflow.memory_bank.ingest /path/to/file.pdf usaid_ads201
```

Ingest all PDFs in a folder:

```bash
python -m grantflow.memory_bank.ingest /path/to/folder usaid_ads201 --folder
```

## Repository Layout

```text
grantflow/
├── api/               # FastAPI app
├── core/              # config, state, donor strategies
├── exporters/         # docx/xlsx builders
├── memory_bank/       # vector store + ingestion tools
├── swarm/             # LangGraph graph + nodes + HITL
└── tests/             # integration / strategy / vector store tests
```

## Security / Publishing Notes

- Do not commit `.env` files or provider keys
- `OPENAI_API_KEY` is expected from environment variables only
- generated local data (`chroma_db/`, `backups/`) is ignored by `.gitignore`

## Project Status

This is an actively evolving MVP backend. The current implementation prioritizes:

- stable API contract
- deterministic workflow execution
- donor strategy isolation
- export pipeline reliability
- staged review checkpoints with resume (HITL MVP)
- broad donor catalog coverage with incremental specialization

Next likely steps:

- graph-native HITL pause/resume (inside LangGraph runtime)
- more specialized strategies for priority donors (e.g. UN agencies, FCDO, Gavi, Global Fund, Gates)
- stronger typed graph state across nodes
- production job store (Redis/Celery)
- richer donor-specific RAG + LLM drafting nodes
