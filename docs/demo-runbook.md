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
make pilot-scorecard
make pilot-scorecard-refresh
make case-study-pack
make case-study-pack-refresh
make executive-pack
make executive-pack-refresh
make oem-pack
make oem-pack-refresh
make pilot-archive
make pilot-archive-refresh
make diligence-index
make diligence-index-refresh
make baseline-fill-template
make baseline-fill-template-refresh
make clean-demo-artifacts-dry-run
make clean-demo-artifacts
make latest-links
make latest-links-refresh
make pilot-handout
make pilot-handout-refresh
make smoke-demo-refresh
make latest-open-order
make latest-open-order-refresh
make pilot-refresh-fast
make verify-latest-stack
make verify-latest-stack-refresh
make release-demo-bundle
make release-demo-bundle-fast
make send-bundle-index
make send-bundle-index-refresh
make open-latest-send
make open-latest-send-refresh
make open-latest-send-fast
make open-latest-send-fast-refresh
make buyer-demo-open
make buyer-demo-open-refresh
make ci-demo-smoke
make dev-runtime-refresh
```

This writes a ready-to-review bundle to `build/demo-pack/` using live API runs and auto-drains one HITL case by default.
It also seeds a synthetic reviewer comment workflow into the saved demo artifacts unless you set `DEMO_PACK_SEED_REVIEW_COMMENTS=0`.
`make pilot-pack` additionally assembles a stakeholder-facing folder in `build/pilot-pack/` with the live run evidence plus buyer and pilot evaluation docs.
`make buyer-brief` writes a concise executive summary markdown from an existing pilot pack.
`make buyer-brief-refresh` rebuilds the pilot pack first, then writes the brief.
`make pilot-metrics` writes metric tables from an existing pilot pack.
`make pilot-metrics-refresh` rebuilds the pilot pack first, then writes the metric tables.
`make pilot-scorecard` writes a short go/no-go memo from an existing pilot pack.
`make pilot-scorecard-refresh` rebuilds the pilot pack, metrics, and brief first, then writes the scorecard.
`make case-study-pack` writes a compact single-case pack from an existing pilot pack.
`make case-study-pack-refresh` rebuilds the pilot pack, metrics, brief, and scorecard first, then writes the case pack.
`make executive-pack` writes a send-ready buyer folder from an existing pilot pack and case-study pack.
`make executive-pack-refresh` rebuilds the full chain first, then writes the executive pack.
`make oem-pack` writes a technical partner diligence folder from an existing pilot pack and executive pack.
`make oem-pack-refresh` rebuilds the full chain first, then writes the OEM pack.
`make pilot-archive` writes a zip-ready archive from the pilot, executive, and optional OEM packs.
`make pilot-archive-refresh` rebuilds the full chain first, then writes the archive.
`make diligence-index` writes a single markdown index over generated local packs and archives.
`make diligence-index-refresh` rebuilds the full chain first, then writes the index.
`make baseline-fill-template` writes a fillable baseline worksheet from `pilot-metrics.csv`.
`make baseline-fill-template-refresh` rebuilds pilot metrics first, then writes the baseline worksheet.
`make clean-demo-artifacts-dry-run` lists generated bundles slated for cleanup.
`make clean-demo-artifacts` removes generated bundles and leaves unrelated files alone.
`make latest-links` writes stable `build/latest-*` symlinks to the newest generated bundles, including fast/full send bundles and their zip files.
`make latest-links-refresh` rebuilds the full chain first, then refreshes those symlinks.
`make pilot-handout` writes a short single-file pilot summary.
`make pilot-handout-refresh` rebuilds the full chain first, then writes the handout.
`make smoke-demo-refresh` runs the default full smoke chain through handout generation.
`make latest-open-order` writes a short "what to open next" guide for `build/latest-*`.
`make latest-open-order-refresh` rebuilds the chain first, then writes that guide.
`make pilot-refresh-fast` runs the buyer-facing refresh path without OEM pack, archive, or diligence index.
`make verify-latest-stack` verifies that `build/latest-*` symlinks and key files exist.
`make verify-latest-stack-refresh` rebuilds the chain first, then verifies the latest stack.
`make release-demo-bundle` rebuilds and packages the latest stack into a send-ready folder plus zip.
`make release-demo-bundle-fast` rebuilds only the fast buyer path, then packages `pilot-handout`, `latest-open-order`, and the current `executive-pack` into a lighter send-ready folder plus zip.
`make send-bundle-index` writes a short markdown describing which current bundle to send and when.
`make send-bundle-index-refresh` rebuilds the fast send bundle first, then writes that send index.
`make open-latest-send` prints the current send-oriented open order from the latest fast/full bundle links. Set `OPEN_LATEST_SEND_MODE=open` on macOS to open the files directly.
`make open-latest-send-refresh` rebuilds the fast send layer first, then prints or opens those artifacts.
`make open-latest-send-fast` prints only the fast send path artifacts.
`make open-latest-send-fast-refresh` rebuilds the fast send layer first, then prints or opens only those fast artifacts.
`make buyer-demo-open` prints the buyer-facing open order from the current `build/latest-*` stack. Set `BUYER_DEMO_OPEN_MODE=open` on macOS to open the files directly.
`make buyer-demo-open-refresh` rebuilds the fast buyer path first, then prints or opens that stack.
`make ci-demo-smoke` runs the minimal buyer-chain smoke path on a single preset and asserts that the key demo artifacts exist.
`make dev-runtime-refresh` rebuilds local Docker `api` and `worker` services when live `/status/*` payloads lag behind the current checkout.

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
curl -s http://127.0.0.1:8000/status/<JOB_ID>/review/workflow
```

In `/review/workflow`, use:
- `summary.reviewer_workflow_summary` for open vs acknowledged vs resolved review load
- `summary.action_queue_summary` for the next operational move (`ack_finding`, `resolve_finding`, `ack_comment`, `resolve_comment`, `reopen_comment`)

### Step D: show traceability

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/citations
curl -s http://127.0.0.1:8000/status/<JOB_ID>/versions
curl -s http://127.0.0.1:8000/status/<JOB_ID>/events
curl -s http://127.0.0.1:8000/status/<JOB_ID>/comments
```

Optional review mutations:

```bash
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments/<COMMENT_ID>/ack
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments/<COMMENT_ID>/resolve
curl -s -X POST http://127.0.0.1:8000/status/<JOB_ID>/comments/<COMMENT_ID>/reopen
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
make demo-pack DEMO_PACK_SEED_REVIEW_COMMENTS=0
make pilot-pack PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make buyer-brief BUYER_BRIEF_OUT=build/pilot-pack/buyer-brief-custom.md
make buyer-brief-refresh PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make pilot-metrics PILOT_METRICS_PILOT_DIR=build/pilot-pack-smoke
make pilot-metrics-refresh PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make pilot-scorecard PILOT_SCORECARD_PILOT_DIR=build/pilot-pack-smoke
make pilot-scorecard-refresh PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make case-study-pack CASE_STUDY_PILOT_DIR=build/pilot-pack-smoke CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan
make case-study-pack-refresh CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make executive-pack EXECUTIVE_PACK_PILOT_DIR=build/pilot-pack-smoke EXECUTIVE_PACK_CASE_STUDY_DIR=build/case-study-pack-smoke EXECUTIVE_PACK_PRESET_KEY=usaid_gov_ai_kazakhstan EXECUTIVE_PACK_OUT_DIR=build/executive-pack-smoke
make executive-pack-refresh CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make oem-pack OEM_PACK_PILOT_DIR=build/pilot-pack-smoke OEM_PACK_EXECUTIVE_DIR=build/executive-pack-smoke OEM_PACK_PRESET_KEY=usaid_gov_ai_kazakhstan OEM_PACK_OUT_DIR=build/oem-pack-smoke
make oem-pack-refresh CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1
make pilot-archive PILOT_ARCHIVE_PILOT_DIR=build/pilot-pack-smoke PILOT_ARCHIVE_EXECUTIVE_DIR=build/executive-pack-smoke PILOT_ARCHIVE_OEM_DIR=build/oem-pack-smoke PILOT_ARCHIVE_OUT_DIR=build/pilot-archive-smoke PILOT_ARCHIVE_NAME=grantflow-smoke PILOT_ARCHIVE_INCLUDE_OEM=1
make pilot-archive-refresh CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1 PILOT_ARCHIVE_NAME=grantflow-pilot
make diligence-index DILIGENCE_INDEX_BUILD_DIR=build DILIGENCE_INDEX_OUT=build/diligence-index.md
make diligence-index-refresh CASE_STUDY_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO=1 PILOT_ARCHIVE_NAME=grantflow-pilot
make baseline-fill-template BASELINE_TEMPLATE_PILOT_DIR=build/pilot-pack-smoke
make baseline-fill-template-refresh BASELINE_TEMPLATE_PILOT_DIR=build/pilot-pack-smoke
make clean-demo-artifacts-dry-run CLEAN_DEMO_ARTIFACTS_BUILD_DIR=build
make clean-demo-artifacts CLEAN_DEMO_ARTIFACTS_BUILD_DIR=build
make latest-links LATEST_LINKS_BUILD_DIR=build
make latest-links-refresh LATEST_LINKS_BUILD_DIR=build
make pilot-handout PILOT_HANDOUT_PILOT_DIR=build/pilot-pack-smoke PILOT_HANDOUT_EXECUTIVE_DIR=build/executive-pack-smoke PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_HANDOUT_OUT=build/pilot-handout-smoke.md
make pilot-handout-refresh PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_HANDOUT_OUT=build/pilot-handout.md
make smoke-demo-refresh PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_ARCHIVE_NAME=grantflow-pilot
make latest-open-order LATEST_OPEN_ORDER_BUILD_DIR=build LATEST_OPEN_ORDER_OUT=build/latest-open-order.md
make latest-open-order-refresh LATEST_OPEN_ORDER_BUILD_DIR=build LATEST_OPEN_ORDER_OUT=build/latest-open-order.md
make pilot-refresh-fast PILOT_HANDOUT_PRESET_KEY=usaid_gov_ai_kazakhstan PILOT_HANDOUT_OUT=build/pilot-handout.md
make verify-latest-stack VERIFY_LATEST_STACK_BUILD_DIR=build
make verify-latest-stack-refresh VERIFY_LATEST_STACK_BUILD_DIR=build
make release-demo-bundle RELEASE_DEMO_BUNDLE_BUILD_DIR=build RELEASE_DEMO_BUNDLE_OUT_DIR=build/release-demo-bundle RELEASE_DEMO_BUNDLE_NAME=grantflow-demo-bundle
make release-demo-bundle-fast RELEASE_DEMO_BUNDLE_BUILD_DIR=build RELEASE_DEMO_BUNDLE_FAST_OUT_DIR=build/release-demo-bundle-fast RELEASE_DEMO_BUNDLE_FAST_NAME=grantflow-demo-bundle-fast
make send-bundle-index SEND_BUNDLE_INDEX_BUILD_DIR=build SEND_BUNDLE_INDEX_OUT=build/send-bundle-index.md
make send-bundle-index-refresh SEND_BUNDLE_INDEX_BUILD_DIR=build SEND_BUNDLE_INDEX_OUT=build/send-bundle-index.md
make open-latest-send OPEN_LATEST_SEND_BUILD_DIR=build OPEN_LATEST_SEND_MODE=print
make open-latest-send-refresh OPEN_LATEST_SEND_BUILD_DIR=build OPEN_LATEST_SEND_MODE=open
make open-latest-send-fast OPEN_LATEST_SEND_BUILD_DIR=build OPEN_LATEST_SEND_MODE=print
make open-latest-send-fast-refresh OPEN_LATEST_SEND_BUILD_DIR=build OPEN_LATEST_SEND_MODE=open
make buyer-demo-open BUYER_DEMO_OPEN_BUILD_DIR=build BUYER_DEMO_OPEN_MODE=print
make buyer-demo-open-refresh BUYER_DEMO_OPEN_BUILD_DIR=build BUYER_DEMO_OPEN_MODE=open
make ci-demo-smoke CI_DEMO_SMOKE_ROOT=build/ci-demo-smoke CI_DEMO_SMOKE_PRESET_KEY=usaid_gov_ai_kazakhstan
```
