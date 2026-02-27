# Git Process

## Commit Style

Use Conventional Commit prefixes for PR titles and commit messages when practical:

- `feat:` new backward-compatible functionality
- `fix:` backward-compatible bug fix
- `refactor:` internal code change with no behavior intent change
- `docs:` documentation-only updates
- `test:` test-only updates
- `chore:` maintenance/tooling/infra updates

Examples:

- `feat(api): add logframe-only HITL checkpoint selection`
- `fix(export): preserve finding_id in critic findings sheet`
- `chore(ci): add release governance guard step`

## Branch and PR Expectations

- Keep changes scoped to one logical deliverable.
- Include changelog updates for user-visible behavior changes.
- For release-impacting changes:
  - align `grantflow/core/version.py` with intended release version
  - ensure `CHANGELOG.md` contains the version section before tagging

## Release Safety

- Run release guard locally before creating tags:

```bash
python scripts/release_guard.py --tag vX.Y.Z
```
