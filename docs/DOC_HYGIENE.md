# Documentation Hygiene (Safe Cleanup)

This file tracks low-risk cleanup opportunities **without deleting content**.

## Rules

- Do not delete docs directly unless explicitly approved.
- Prefer reclassification first: active / reference / archive-candidate.
- Keep customer-facing and onboarding docs easy to find via `docs/README.md`.

## Current archive candidates (manual review)

These files may be moved later to `docs/archive/` after explicit approval:

1. `audit-story.md` (if superseded by newer enterprise audit package)
2. `productization-gaps-memo.md` (if gaps are already resolved)
3. `reference-topology.md` (if merged into `architecture.md`)
4. `identity-rbac-roadmap.md` (if outdated roadmap)
5. `pilot-role-mapping-example.md` (if duplicated by worksheet)
6. `pilot-proof-outreach-template.md` (if not currently used)

## Recommended next cleanup pass

1. Add `Last reviewed:` date at top of each doc.
2. Tag each doc with one of:
   - `Status: active`
   - `Status: reference`
   - `Status: archive-candidate`
3. Move approved archive-candidates into `docs/archive/` (single commit with migration note).

## Why this approach

- Minimizes risk of deleting needed operational knowledge.
- Keeps docs discoverable for new contributors.
- Supports incremental cleanup with clear audit trail.
