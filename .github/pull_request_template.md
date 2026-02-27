## Summary

- What changed?
- Why now?
- Suggested Conventional Commit title (`type(scope): summary`):

## Scope

- [ ] API behavior
- [ ] Graph/pipeline behavior
- [ ] RAG/retrieval behavior
- [ ] Export format/layout
- [ ] Tooling/CI/docs only

## Validation

- [ ] `pytest` run locally (or targeted suite with rationale)
- [ ] `ruff` clean
- [ ] `black` clean
- [ ] `mypy` clean (targeted baseline)

## Changelog

- [ ] `CHANGELOG.md` updated (or not needed, explain below)

## API Stability Checklist

- [ ] No breaking public API changes
- [ ] If breaking: SemVer major bump planned
- [ ] If breaking: migration notes included

## Git Process

- [ ] PR title follows Conventional Commit style (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- [ ] If release-impacting: runtime version in `grantflow/core/version.py` and `CHANGELOG.md` are aligned

## Release Notes Draft (if user-visible)

- 1.
- 2.
- 3.
