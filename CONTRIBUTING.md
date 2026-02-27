# Contributing

## Branches and PRs

- Open feature branches from `main`.
- Keep PRs scoped to one change theme (for example: PR6 RAG traceability).
- Link related issue/task context in the PR description.

## Commit Style

Use Conventional Commits where possible:

- `feat: ...` for new user-facing capability
- `fix: ...` for bug fixes
- `refactor: ...` for non-behavioral code changes
- `test: ...` for tests only
- `docs: ...` for documentation only
- `chore: ...` for tooling/maintenance

Use `!` for breaking changes, for example:

- `feat(api)!: rename /status/{job_id}/critic field`

## Local Checks Before Push

```bash
python -m pytest -c grantflow/pytest.ini grantflow/tests/ -v --tb=short
ruff check grantflow
isort grantflow
black grantflow
mypy grantflow/api grantflow/core/stores.py grantflow/swarm/versioning.py
```

Or use pre-commit:

```bash
pre-commit run --all-files
```

## Changelog Rule

- For user-visible behavior changes, update `CHANGELOG.md` under `Unreleased`.
- On release, move `Unreleased` entries into the new version section.

## API Stability

- Review `docs/api-stability-policy.md` before changing endpoint paths, payload fields, or status semantics.
- Breaking API changes require:
  - SemVer major version bump
  - changelog entry with migration note
  - explicit reviewer sign-off in PR

