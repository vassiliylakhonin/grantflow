# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Buyer-facing packaging helper targets: `buyer-facing-pack-refresh` and `buyer-facing-artifacts-index`.
- Generated buyer-facing artifact index output at `build/buyer-facing-artifacts-index.md` to quickly review pilot/customer-ready deliverables.

### Changed
- Review workflow public payload now includes concise reviewer UX signals:
  - finding-level `triage_priority_label`, `reviewer_next_actions`, `reviewer_next_action_short`
  - summary-level `summary.triage_summary.next_priority_label`, `summary.triage_summary.next_action_brief`

### Fixed
- Added integration regression coverage to ensure default DOCX exports remain client-ready (diagnostic sections excluded unless `include_diagnostics=true`).

## [2.1.1] - 2026-03-03

### Changed
- Dependency management moved to `pyproject.toml` as the canonical source of truth (`[project]` + `[project.optional-dependencies]`).
- CI, Docker, and docs install flows updated to `pip install .` / `pip install ".[dev]"`.
- Legacy `requirements` files kept as compatibility shims pointing to the project metadata.
- State contract now exposes canonical helpers for strategy and iteration access; core swarm nodes (`discovery`, `architect`, `mel`, `critic`) now consume those helpers instead of ad-hoc alias reads.
- Critic findings hardened as stable entities: deterministic `finding_id` generation for legacy/unstructured payloads and stricter LLM `fatal_flaws` coercion to object lists.
- Release governance now validates Keep-a-Changelog heading format (`## [X.Y.Z] - YYYY-MM-DD`) for current/tagged versions.
- CI now enforces Conventional Commit PR titles via `scripts/pr_title_guard.py`.
- Added CI-driven tag cutting workflow (`Release Cut`) with manual approval gate through environment `release`.
- Added Release Drafter automation (`.github/release-drafter.yml` + workflow) for continuously updated draft release notes.

## [2.1.0] - 2026-03-03

### Added
- Grounded smoke CI lane that boots API, ingests seed corpus, and validates donor readiness/benchmark status.
- Pilot run artifacts for grounded deterministic and LLM benchmark tracks under `docs/pilot_runs/2026-03-03-grounded-llm-p2/`.

### Changed
- Architect and MEL citation confidence calibration tuned for more stable scoring behavior.
- CI mypy baseline updated for stricter type safety in API preflight and public review SLA payload shaping.
- Eval baseline snapshot aligned with clean no-corpus environment to prevent false CI regressions.

## [2.0.1] - 2026-02-27

### Added
- Graph-level HITL pause/resume gates with checkpoint-driven continuation.
- Donor-specific export templates/sheets for USAID, EU, and World Bank.
- RAG traceability enrichment: `doc_id`, retrieval rank/confidence, and stronger namespace normalization.
- Golden contract tests for donor resolution, public redaction, versioning/citation behavior, and non-LLM lane coverage.
- Readiness endpoint (`/ready`) and ingest inventory/export endpoints for RAG operations.
- GitHub release workflow (`.github/workflows/release.yml`) that extracts versioned notes from `CHANGELOG.md` and publishes releases for `v*.*.*` tags.
- Grounding Gate policy (`off|warn|strict`) with strict-mode finalization/export blocking on weak grounding signals.
- Graph-native HITL checkpoint creation with optional stage selection (`hitl_checkpoints`) in `/generate`.
- Expanded donor-specific exporters for specialized strategies (`usaid`, `eu`, `worldbank`, `giz`, `state_department`).
- Fixture-driven golden snapshots for contract-critical behaviors (donor resolution, citations/versioning, export payload redaction).
- `scripts/release_guard.py` for SemVer/tag/changelog/governance validation.

### Changed
- README expanded with execution modes, grounding caveats, sample artifacts, and quality/readiness guidance.
- Critic findings normalized into typed entities with lifecycle status (`open`, `acknowledged`, `resolved`).
- Tooling baseline formalized with `black`, `ruff`, `isort`, `mypy`, and pre-commit hooks.
- Runtime API version now uses `grantflow/core/version.py` as source of truth.
- CI and release workflows now run release governance checks before merge/release.

## [2.0.0] - 2026-02-24

### Added
- FastAPI + LangGraph proposal drafting backend with donor strategy routing.
- HITL checkpoint API, async job lifecycle, and export package generation.
- Chroma-backed RAG ingestion and retrieval paths with in-memory fallback.
