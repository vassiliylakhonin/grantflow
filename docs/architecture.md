# Architecture Overview

This document describes the current backend execution shape without product redesign assumptions.

## Request and Orchestration Path

```mermaid
flowchart LR
  C["Client"] --> API["FastAPI Routes"]
  API --> PRE["Preflight / Validation"]
  PRE --> DISC["discovery"]
  DISC --> ARCH["architect"]
  ARCH --> MEL["mel"]
  MEL --> CRIT["critic"]
  CRIT --> DONE["Terminal Job State"]
```

## HITL and Resume Path

```mermaid
flowchart LR
  ARCH["architect"] --> CP1["HITL checkpoint (ToC)"]
  MEL["mel"] --> CP2["HITL checkpoint (LogFrame)"]
  CP1 --> DEC1["approve/reject"]
  CP2 --> DEC2["approve/reject"]
  DEC1 --> RES["/resume/{job_id}"]
  DEC2 --> RES
  RES --> NEXT["continue graph from stage"]
```

## Export Path

```mermaid
flowchart LR
  S["/status/{job_id}"] --> P["/status/{job_id}/export-payload"]
  P --> E["POST /export"]
  E --> DOCX["docx"]
  E --> XLSX["xlsx"]
  E --> ZIP["both (zip)"]
```

## Runtime Topologies

- Local/dev default:
  - API in `background_tasks` mode
  - in-memory stores allowed
- Recommended production:
  - API in `redis_queue` dispatcher mode
  - dedicated worker process (`python -m grantflow.worker`)
  - persistent sqlite stores

See `README.md` for quick-start and `docs/operations-runbook.md` for operational checks.
