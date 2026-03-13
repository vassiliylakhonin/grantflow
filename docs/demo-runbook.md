# Demo Runbook

This is the public demo path for GrantFlow. It is intentionally opinionated.

Use one of two routes:
- `canonical live demo` when you want to show the real workflow on a running API
- `no-risk artifact demo` when you want to show value without touching runtime state

Supporting materials:
- `buyer-one-pager.md`
- `five-minute-demo.md`
- `production-boundaries.md`

## Canonical Live Demo

Use this when you want to prove:
- structured first draft generation
- reviewer workflow and queues
- traceability
- export-ready handoff

### 1. Start the API

```bash
pip install ".[dev]"
uvicorn grantflow.api.app:app --reload
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

Optional UI:
- open `http://127.0.0.1:8000/demo` (`Reviewer Console`)

### 2. Generate one case

Standard proposal path:

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

Evaluation RFQ path:

```bash
curl -s -X POST http://127.0.0.1:8000/generate/from-preset \
  -H 'Content-Type: application/json' \
  -d '{
    "preset_key": "un_agencies_katch_evaluation_kyrgyzstan",
    "preset_type": "auto",
    "llm_mode": false,
    "hitl_enabled": false
  }'
```

Save the returned `job_id`.

### 3. Show workflow control

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/quality
curl -s http://127.0.0.1:8000/status/<JOB_ID>/critic
curl -s http://127.0.0.1:8000/status/<JOB_ID>/review/workflow
```

Focus on:
- `summary.reviewer_workflow_summary`
- `summary.action_queue_summary`
- `next primary action` in the Reviewer Console

### 4. Show traceability

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/citations
curl -s http://127.0.0.1:8000/status/<JOB_ID>/versions
curl -s http://127.0.0.1:8000/status/<JOB_ID>/events
```

### 5. Export the package

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/export-payload -o export_payload.json
curl -s -X POST http://127.0.0.1:8000/export \
  -H 'Content-Type: application/json' \
  --data-binary @export_payload.json \
  -o grantflow_export.zip
```

For RFQ mode, verify:
- `.docx` contains `Evaluation RFQ Technical Proposal`
- `.xlsx` contains `Evaluation_Plan`
- ZIP contains `annex_packer/` and `submission_package/`

## No-Risk Artifact Demo

Use this when you want to show product value without rebuilding or mutating local runtime state.

### 1. Build the buyer-safe artifact path

```bash
make pilot-refresh-fast
make release-demo-bundle-fast
```

Or run the full pilot conversion layer in one command (demo -> review -> export -> executive summary -> evidence pack -> buyer index):

```bash
make pilot-conversion-layer DEMO_PACK_API_BASE=http://127.0.0.1:8000
```

Expected terminal output includes:
- `pilot conversion layer complete`
- `demo summary: build/demo-pack/summary.md`
- `executive summary: build/executive-pack/README.md`
- `evidence pack: build/pilot-evidence-pack/README.md`
- `buyer index: build/buyer-facing-artifacts-index.md`

### 2. Open the canonical outputs

Open in this order:
- `build/send-bundle-index.md`
- `build/latest-open-order.md`
- `build/executive-pack/README.md`
- `build/pilot-pack/buyer-brief.md`

If you want the packaged handoff:
- `build/send-bundle-index.md`

### 3. What to show

- buyer-facing summary
- current review-readiness state
- grounding snapshot
- export-ready package

This is the safest path for partner or buyer conversations when you do not want to depend on live generation in front of them.

## Optional HITL Segment

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

## Honest Rough Edges

- grounding quality depends on corpus quality and coverage
- final donor compliance sign-off remains human-owned
- built-in auth is API-key based; enterprise IAM belongs at the gateway layer

## Deeper Operator Paths

If you need the full artifact, pilot, or diligence machinery, use:
- `full-guide.md`
- `operations-runbook.md`
- `enterprise-quickstart.md`
