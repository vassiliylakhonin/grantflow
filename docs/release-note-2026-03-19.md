# Release Note — 2026-03-19

## Summary
This release cycle focused on engineering hardening: CI quality governance, security remediation, dependency reproducibility, performance guardrails, API contract checks, and contribution governance.

## What shipped

### 1) Quality gate hardening
- Nightly grounded-tail gate now splits regressions by severity:
  - hard-fail metrics
  - warn-only metrics
- Added clearer gate summary output for triage.
- Added auto-triage issue creation on repeated nightly failures.

### 2) Security and supply-chain improvements
- Added supply-chain workflow with:
  - `pip-audit`
  - CycloneDX SBOM artifact generation
- Remediated dependency vulnerabilities in runtime-critical packages.
- Completed deferred formatter-security maintenance (`black` upgrade + format pass).

### 3) Reproducibility improvements
- Introduced hash-locked dependency snapshots:
  - `requirements.lock`
  - `requirements-dev.lock`
- CI supply-chain scanning now runs against deterministic lockfile inputs.

### 4) Performance guardrails
- Added grounded smoke performance budget gate in CI:
  - latency budget
  - throughput budget
- Added benchmark timing and performance summary artifacts for triage.

### 5) API compatibility guard
- Added lightweight OpenAPI contract guard in CI for critical paths/methods/security scheme/schema expectations.
- Wired into `dependency-contract` job for fast compatibility drift detection.

### 6) Documentation and governance updates
- README refreshed for clearer positioning and current-state accuracy.
- Added public roadmap: `docs/public-roadmap.md`.
- Added coverage policy: `docs/coverage-threshold-policy.md`.
- Added `good-first-issue` template and issue template config.
- Upgraded PR template with quality/risk checklist (eval, security, performance, API impact).

## Result
- CI signal quality improved (fewer false blockers, better triage paths).
- Security posture improved with explicit scanning and remediation.
- Dependency and scan behavior became more deterministic.
- Governance baseline now clearer for maintainers and contributors.
