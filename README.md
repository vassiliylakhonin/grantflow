# GrantFlow

**GrantFlow is a workflow engine for institutional proposal operations.**

It helps proposal teams turn raw program intent into reviewable draft packages with controlled stages, human approvals, traceability, and export-ready outputs.

Built for organizations that need governed drafting and review workflows, not a generic grant-writing chatbot.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11--3.13-blue.svg)](https://www.python.org/)

## Why Teams Use It

- turn drafting into a controlled multi-stage workflow
- route work by donor strategy and proposal mode
- pause for human approval at critical checkpoints
- track findings, comments, versions, and citations
- export review-ready `.docx`, `.xlsx`, and ZIP packages

## Why This Exists

Generic AI tools generate text.

Proposal operations teams need something different:
- explicit workflow stages
- review and remediation loops
- human approval controls
- traceability for citations, versions, and events
- exportable artifacts for downstream submission work

GrantFlow covers the drafting-control-review-export layer.
Final donor compliance sign-off remains a human responsibility.

## Who It Is For

- NGOs and implementing organizations
- consulting firms managing donor submissions
- program and MEL teams handling institutional compliance workflows

## Who It Is Not For

- teams looking for a general-purpose grant-writing chatbot
- ad-hoc individual fundraising use cases
- organizations that only need plain text generation without review controls or audit traces

## What Is Real Today

- structured draft pipeline for proposal artifacts
- donor strategy routing
- critic loop with structured findings
- SLA-aware review workflow
- human-in-the-loop pause / approve / resume
- citation, version, and event traceability
- export to `.docx`, `.xlsx`, and ZIP
- queue-backed runtime with separate worker path
- bounded `evaluation_rfq` mode for consultancy-style technical responses

## See It In 5 Minutes

1. Start the API.
2. Open `/demo`.
3. Generate from a preset.
4. Inspect draft status, findings, and review workflow.
5. Export the review package.

Core demo path:
- `GET /demo`
- `POST /generate/from-preset`
- `GET /status/{job_id}`
- `GET /status/{job_id}/critic`
- `GET /status/{job_id}/review/workflow`
- `POST /export`

Start here:
- `docs/buyer-one-pager.md`
- `docs/five-minute-demo.md`
- `docs/samples/`

## What Production Means Today

Recommended deployment profile:
- API in queue-backed mode
- dedicated worker process
- persistent stores enabled
- API key auth enabled
- private network for backing services

Current repository scope:
- built-in auth is API-key based
- native OIDC / SAML / RBAC is not claimed in-repo
- enterprise access control is expected at the gateway or platform layer

See:
- `docs/production-boundaries.md`
- `docs/reference-topology.md`
- `docs/enterprise-access-layer.md`
- `docs/enterprise-quickstart.md`
- `docs/audit-story.md`
- `SECURITY.md`

## Quickstart

```bash
pip install ".[dev]"
uvicorn grantflow.api.app:app --reload
curl -s http://127.0.0.1:8000/health
```

Then open:

`http://127.0.0.1:8000/demo`

## Docs By Audience

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

**Security / Enterprise Review**
- `docs/enterprise-access-layer.md`
- `docs/enterprise-access-checklist.md`
- `docs/gateway-policy-example.md`
- `docs/identity-rbac-roadmap.md`

Customer-specific pilot materials are intentionally kept out of this public repository.
