# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Graph-level HITL pause/resume gates with checkpoint-driven continuation.
- Donor-specific export templates/sheets for USAID, EU, and World Bank.
- RAG traceability enrichment: `doc_id`, retrieval rank/confidence, and stronger namespace normalization.
- Golden contract tests for donor resolution, public redaction, versioning/citation behavior, and non-LLM lane coverage.
- Readiness endpoint (`/ready`) and ingest inventory/export endpoints for RAG operations.
- GitHub release workflow (`.github/workflows/release.yml`) that extracts versioned notes from `CHANGELOG.md` and publishes releases for `v*.*.*` tags.
- Grounding Gate policy (`off|warn|strict`) with strict-mode finalization/export blocking on weak grounding signals.

### Changed
- README expanded with execution modes, grounding caveats, sample artifacts, and quality/readiness guidance.
- Critic findings normalized into typed entities with lifecycle status (`open`, `acknowledged`, `resolved`).
- Tooling baseline formalized with `black`, `ruff`, `isort`, `mypy`, and pre-commit hooks.

## [2.0.0] - 2026-02-24

### Added
- FastAPI + LangGraph proposal drafting backend with donor strategy routing.
- HITL checkpoint API, async job lifecycle, and export package generation.
- Chroma-backed RAG ingestion and retrieval paths with in-memory fallback.
