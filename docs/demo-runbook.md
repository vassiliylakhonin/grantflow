# Demo Runbook

This runbook is the recommended way to demo GrantFlow with existing repository capabilities.

## 1) Demo Objective

Show that GrantFlow is a controlled proposal workflow system:
- generate structured draft artifacts
- inspect review and quality traces
- optionally run HITL approve/resume
- export review-ready files

## 2) Prerequisites

- Python `3.11-3.13`
- dependencies installed (`pip install ".[dev]"` or `pip install .`)
- API running:

```bash
uvicorn grantflow.api.app:app --reload
```

Optional:
- open Demo Console at `http://127.0.0.1:8000/demo`

Fastest reproducible bundle path:

```bash
make demo-pack
make pilot-pack
make buyer-brief
make buyer-brief-refresh
make pilot-metrics
make pilot-metrics-refresh
```

This writes a ready-to-review bundle to `build/demo-pack/` using live API runs and auto-drains one HITL case by default.
`make pilot-pack` additionally assembles a stakeholder-facing folder in `build/pilot-pack/` with the live run evidence plus buyer and pilot evaluation docs.
`make buyer-brief` writes a concise executive summary markdown from an existing pilot pack.
`make buyer-brief-refresh` rebuilds the pilot pack first, then writes the brief.
`make pilot-metrics` writes metric tables from an existing pilot pack.
`make pilot-metrics-refresh` rebuilds the pilot pack first, then writes the metric tables.

## 3) Operator Demo Flow (API-first)

### Step A: health/readiness

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### Step B: generate from preset

```bash
curl -s -X POST http://127.0.0.1:8000/generate/from-preset \
  -H 'Content-Type: application/json' \
  -d '{
    "preset_key": "usaid_gov_ai_kazakhstan",
    "preset_type": "auto",
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

Save returned `job_id`.

### Step C: inspect status and quality

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>
curl -s http://127.0.0.1:8000/status/<JOB_ID>/quality
curl -s http://127.0.0.1:8000/status/<JOB_ID>/critic
```

### Step D: show traceability

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/citations
curl -s http://127.0.0.1:8000/status/<JOB_ID>/versions
curl -s http://127.0.0.1:8000/status/<JOB_ID>/events
```

### Step E: export review package

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/export-payload -o export_payload.json
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  --data-binary @export_payload.json \
  -o grantflow_export.zip
```

## 4) Optional HITL Segment

Run a second job with `hitl_enabled=true` and use:

```bash
curl -s -X POST http://127.0.0.1:8000/hitl/approve \
  -H 'Content-Type: application/json' \
  -d '{"checkpoint_id":"<CHECKPOINT_ID>","approved":true,"feedback":"approved for continuation"}'

curl -s -X POST http://127.0.0.1:8000/resume/<JOB_ID> \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Then show:

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/hitl/history
```

## 5) Buyer-Friendly Narrative (Short)

1. We start from a donor-specific preset, not a blank prompt.
2. The system runs a staged drafting pipeline, not one-shot text generation.
3. Reviewers get structured quality and critic signals, not free-form output only.
4. We can pause and resume with explicit human approvals.
5. We export review-ready artifacts for downstream submission workflow.

## 6) 5-Minute Founder Demo Script

### Minute 0-1: framing

- “This is not a grant chatbot. It is workflow control for proposal operations.”
- “We optimize for reviewability, governance, and traceability under donor constraints.”

### Minute 1-2: generate

- Trigger `POST /generate/from-preset`.
- Show returned `job_id` and status progression in `/status/{job_id}` or Demo Console.

### Minute 2-3: quality and review traces

- Open `/status/{job_id}/quality` and `/status/{job_id}/critic`.
- Highlight structured findings and quality score context.

### Minute 3-4: traceability and governance

- Show `/status/{job_id}/citations`, `/versions`, `/events`.
- If HITL is enabled, show approve/resume flow and `/hitl/history`.

### Minute 4-5: export and commercial close

- Export payload + `/export`.
- Close with: “GrantFlow gives teams a repeatable proposal operations layer, not just generated text.”

## 7) Honest Rough Edges to Mention in Demos

- Grounding quality is corpus-dependent; ingestion quality affects citation quality.
- Final donor compliance sign-off remains human responsibility.
- Built-in auth is API-key based; enterprise IAM is expected at platform/gateway layer.

## 8) Make Target Options

Useful overrides:

```bash
make demo-pack DEMO_PACK_DIR=build/demo-pack-llm DEMO_PACK_LLM_MODE=1 DEMO_PACK_ARCHITECT_RAG_ENABLED=1
make demo-pack DEMO_PACK_PRESET_KEYS=usaid_gov_ai_kazakhstan,worldbank_public_sector_uzbekistan
make demo-pack DEMO_PACK_API_KEY=change-me
make pilot-pack PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make buyer-brief BUYER_BRIEF_OUT=build/pilot-pack/buyer-brief-custom.md
make buyer-brief-refresh PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make pilot-metrics PILOT_METRICS_PILOT_DIR=build/pilot-pack-smoke
make pilot-metrics-refresh PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
```
