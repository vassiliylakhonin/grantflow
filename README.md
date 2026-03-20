# GrantFlow

**GrantFlow is a workflow engine for institutional proposal operations.**

It helps proposal teams turn raw program intent into reviewable draft packages with controlled stages, human approvals, traceability, and export-ready outputs.

Built for governed drafting and review workflows — not a generic grant-writing chatbot.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11--3.13-blue.svg)](https://www.python.org/)

---

## At a Glance

### What it is
- controlled multi-stage proposal drafting workflow
- donor-aware routing and mode selection
- human approval checkpoints (pause / approve / resume)
- traceability for findings, citations, versions, and events
- export-ready `.docx`, `.xlsx`, and ZIP deliverables

### Who it is for
- NGOs and implementing organizations
- consulting firms managing donor submissions
- program and MEL teams running institutional compliance workflows

### What it is not
- a general-purpose grant-writing chatbot
- ad-hoc individual fundraising tooling
- plain text generation without governed review controls

---

## Current Status (What Is Real Today)

### Core workflow capabilities
- structured draft pipeline for proposal artifacts
- donor strategy routing
- critic loop with structured findings
- SLA-aware review workflow
- human-in-the-loop pause / approve / resume
- citation, version, and event traceability
- export to `.docx`, `.xlsx`, and ZIP
- queue-backed runtime with separate worker path
- bounded `evaluation_rfq` mode for consultancy-style technical responses

### Engineering guardrails now in CI
- quality gate split by severity (hard-fail vs warn-only)
- nightly auto-triage issue creation on repeated failures
- supply-chain scanning with `pip-audit` + CycloneDX SBOM artifacts
- deterministic dependency scanning from hash-locked lockfiles
- grounded smoke performance budget guard (latency + throughput)

---

## 5-Minute Demo Path

1. Start API locally.
2. Open `/demo`.
3. Generate from a preset.
4. Inspect status, critic findings, and review workflow.
5. Export package.

Core demo endpoints:
- `GET /demo`
- `POST /generate/from-preset`
- `GET /status/{job_id}`
- `GET /status/{job_id}/critic`
- `GET /status/{job_id}/review/workflow`
- `POST /export`

Grounding Trust Score (MVP):
- `GET /status/{job_id}/metrics` returns `grounding_trust_summary`.
- `GET /status/{job_id}/quality` and `POST /export` include the same summary.
- Interpret with component scores:
  - `confidence_score`
  - `traceability_score`
  - `diagnostic_risk_score`

One-command buyer conversion flow (live API required):
```bash
make pilot-conversion-layer DEMO_PACK_API_BASE=http://127.0.0.1:8000
```
Expected outputs:
- `build/demo-pack/summary.md`
- `build/executive-pack/README.md`
- `build/pilot-evidence-pack/README.md`
- `build/buyer-facing-artifacts-index.md`

Start here:
- `docs/buyer-one-pager.md`
- `docs/five-minute-demo.md`
- `docs/samples/`

---

## Quickstart

### Fast local run
```bash
pip install ".[dev]"
uvicorn grantflow.api.app:app --reload
curl -s http://127.0.0.1:8000/health
```

Then open: `http://127.0.0.1:8000/demo`

### E2E regression checks (bid/no-bid)
```bash
make test-e2e
```
Runs `grantflow/tests/test_bid_no_bid_e2e.py` with deterministic fixture payloads from `grantflow/tests/fixtures/bid_no_bid_e2e_payloads.json`.

### Reproducible dependency workflow (recommended)
```bash
pip install -r requirements.lock
# or for local dev tooling:
pip install -r requirements-dev.lock
```

`pyproject.toml` remains source-of-truth; lockfiles are operational reproducibility artifacts.

---

## Production Boundaries

Recommended deployment profile:
- API in queue-backed mode
- dedicated worker process
- persistent stores enabled
- API key auth enabled
- private network for backing services

Repository scope (explicit):
- built-in auth is API-key based
- native OIDC / SAML / RBAC is not claimed in-repo
- enterprise access control is expected at gateway/platform layer

See:
- `docs/production-boundaries.md`
- `docs/reference-topology.md`
- `docs/enterprise-access-layer.md`
- `docs/enterprise-quickstart.md`
- `docs/audit-story.md`
- `SECURITY.md`

---

## Docs by Audience

**Buyers**
- `docs/buyer-one-pager.md`
- `docs/pilot-evaluation-checklist.md`
- `docs/proof-summary.md`

**Operators**
- `docs/demo-runbook.md`
- `docs/operations-runbook.md`
- `docs/pilot-day1-checklist.md`

**Engineers**
- `docs/README.md`
- `docs/architecture.md`
- `docs/contributor-map.md`
- `docs/api-stability-policy.md`
- `docs/public-roadmap.md`
- `docs/coverage-threshold-policy.md`

**Security / Enterprise Review**
- `docs/enterprise-access-layer.md`
- `docs/enterprise-access-checklist.md`
- `docs/gateway-policy-example.md`
- `docs/identity-rbac-roadmap.md`

Customer-specific pilot materials are intentionally kept out of this public repository.
