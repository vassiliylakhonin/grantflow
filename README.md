# GrantFlow

Proposal operations platform for high-stakes donor workflows.

GrantFlow helps proposal teams turn program intent into reviewable draft packages with controlled stages, human approvals, traceability, and export-ready outputs. It is built for governed drafting and review workflows, not for generic grant-chatbot use.

[![CI](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/vassiliylakhonin/grantflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11--3.13-blue.svg)](https://www.python.org/)

## Why Not Generic AI

Most proposal teams do not need more text generation. They need:
- a faster path to a reviewable first draft
- less review chaos across multiple contributors
- clearer approvals and ownership
- traceable claims, findings, and revisions
- outputs that fit real submission workflows

GrantFlow is designed around that operating problem.

## Who It Is For

- implementing organizations and NGOs running donor-funded proposals
- grant consulting firms managing multi-review submissions
- program, MEL, and proposal operations teams that need governed drafting

## Who It Is Not For

- a general-purpose grant-writing chatbot
- small ad-hoc fundraising copy generation
- teams that only need raw text without review controls or audit traces

## What Is Real Today

- staged workflow engine: `discovery -> architect -> mel -> critic`
- donor routing with specialized strategies for `usaid`, `eu`, `worldbank`, `giz`, `state_department`
- HITL pause/approve/resume controls
- findings and comments as structured review objects
- traceability endpoints for citations, versions, events, quality, and workflow state
- export to `.docx`, `.xlsx`, and ZIP review packages
- bounded `evaluation_rfq` mode for consultancy-style technical responses

## 5-Minute Proof

Canonical buyer proof path:
1. run the API and open `GET /demo` (`Reviewer Console`)
2. generate a preset case with `POST /generate/from-preset`
3. inspect:
   - `GET /status/{job_id}/quality`
   - `GET /status/{job_id}/critic`
   - `GET /status/{job_id}/review/workflow`
4. export:
   - `GET /status/{job_id}/export-payload`
   - `POST /export`

Start here:
- `docs/buyer-one-pager.md`
- `docs/five-minute-demo.md`
- `docs/samples/`

## Production Boundary

GrantFlow currently covers the drafting-control-review-export layer.

It does not claim:
- in-app SSO or full RBAC
- fully automated donor submission
- full procurement-suite pricing automation
- replacement of human compliance sign-off

For enterprise-style deployment, the intended pattern is:
- gateway or SSO in front
- API key at the GrantFlow boundary
- queue-backed API plus worker
- Redis and Chroma kept private

Details:
- `docs/production-boundaries.md`
- `docs/reference-topology.md`
- `docs/enterprise-access-layer.md`
- `docs/audit-story.md`
- `SECURITY.md`

## Quickstart

Local developer path:

```bash
pip install ".[dev]"
uvicorn grantflow.api.app:app --reload
curl -s http://127.0.0.1:8000/health && curl -s http://127.0.0.1:8000/ready
```

Opinionated shared-eval path:

```bash
cp .env.enterprise.example .env.enterprise
make enterprise-eval-up
make enterprise-eval-check
```

## Evaluation RFQ Mode

GrantFlow includes a bounded `evaluation_rfq` mode for technical-response workflows such as performance evaluation RFQs.

What it currently supports:
- technical proposal backbone
- methodology, deliverables, and workplan structure
- compliance matrix
- staffing and CV readiness
- financial proposal companion summary
- submission package checklist
- attachment manifest and annex-packer artifacts in ZIP export

What it does not yet fully automate:
- detailed pricing workbook logic
- full annex file assembly without supplied file paths
- end-to-end procurement submission packaging

## Docs By Audience

Buyer or partner:
- `docs/buyer-one-pager.md`
- `docs/five-minute-demo.md`
- `docs/proof-summary.md`
- `docs/oem-one-pager.md`

Operator or reviewer:
- `docs/demo-runbook.md`
- `docs/operations-runbook.md`
- `docs/pilot-day1-checklist.md`

Engineer:
- `docs/README.md`
- `docs/architecture.md`
- `docs/contributor-map.md`
- `docs/api-stability-policy.md`

Enterprise or trust review:
- `docs/enterprise-quickstart.md`
- `docs/reference-topology.md`
- `docs/enterprise-access-layer.md`
- `docs/gateway-policy-example.md`
- `docs/enterprise-access-checklist.md`
- `docs/identity-rbac-roadmap.md`
- `docs/audit-story.md`

Customer-specific pilot materials are intentionally kept out of this public repository.
