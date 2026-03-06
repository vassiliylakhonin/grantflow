# GrantFlow OEM / Partner One-Pager

## Positioning

GrantFlow is workflow infrastructure for institutional proposal operations. It is most relevant to software platforms, enterprise workflow vendors, and proposal-response systems that want controlled drafting, review governance, and traceable outputs without building the orchestration layer from scratch.

## Best Fit

- Grant or proposal management platforms
- Enterprise workflow / response-management software
- Digital delivery teams embedding donor-specific drafting workflows into existing systems
- Strategic partners evaluating white-label or embedded proposal operations capabilities

## What Is Verified In Repo Today

- API-first workflow engine with staged orchestration:
  - `discovery -> architect -> mel -> critic`
- Review governance:
  - HITL checkpoint approval and resume
  - structured critic findings and reviewer-facing traces
- Traceability surface:
  - citations, versions, events, quality summaries, portfolio views
- Export path:
  - `.docx`, `.xlsx`, ZIP review packages
- Queue-capable operating mode:
  - API dispatcher + worker separation in `redis_queue` mode
- Local demo and reproducible evidence packs:
  - `make demo-pack`
  - `make pilot-pack`
  - `make executive-pack`

## Why This Matters To OEM / Embedded Buyers

Most platforms do not need another text model wrapper. They need:
- controlled orchestration for high-stakes drafting
- reviewable state transitions
- auditable traces for internal reviewers
- exportable artifacts for downstream workflows
- a product surface they can embed behind their own UI and auth layers

GrantFlow is closer to a proposal workflow control plane than a chatbot backend.

## Recommended Integration Model

- Keep GrantFlow as a backend service behind the partner's existing UI
- Front it with partner auth / gateway controls
- Use GrantFlow APIs for job submission, status, review traces, and exports
- Treat final compliance approval as a partner-side or customer-side governed step

## Current Constraints

- Built-in auth posture is API-key oriented, not enterprise IAM
- Grounding quality is corpus-dependent when retrieval is enabled
- This is workflow infrastructure, not a complete end-user proposal SaaS
- Final donor compliance review remains human-owned

## What A Technical Due-Diligence Review Should Inspect

- `docs/architecture.md`
- `docs/operations-runbook.md`
- `docs/contributor-map.md`
- `SECURITY.md`
- `docs/api-stability-policy.md`
- `grantflow/tests/test_integration.py`
- `build/executive-pack*` or `build/pilot-pack*` outputs
