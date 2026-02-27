# Release Process

## 1) Prepare

- Ensure `main` is green in CI.
- Confirm changelog entries exist under `Unreleased`.
- Confirm README/docs reflect shipped behavior.
- Confirm runtime version in `grantflow/core/version.py` is set to the target release version.

## 2) Choose Version (SemVer)

- `MAJOR`: breaking API/contract changes
- `MINOR`: backward-compatible features
- `PATCH`: fixes only

## 3) Finalize Changelog

- Move relevant entries from `Unreleased` into a new version section:
  - `## [X.Y.Z] - YYYY-MM-DD`
- Keep concise migration notes for breaking changes.

## 4) Tag and Push

```bash
git checkout main
git pull --ff-only
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

## 5) Automated Release Guard

This repository enforces release guardrails with `scripts/release_guard.py`:

- validates SemVer shape of runtime version in `grantflow/core/version.py`
- ensures `CHANGELOG.md` has `[Unreleased]` and current version sections
- checks presence of API stability and release process docs + PR template
- for tag-based release, ensures tag version equals runtime version

Run locally before tagging:

```bash
python scripts/release_guard.py --tag vX.Y.Z
```

## 6) GitHub Release Automation

The repository includes `.github/workflows/release.yml`:

- auto-runs on pushed tags matching `v*.*.*`
- extracts release notes for that version from `CHANGELOG.md`
- publishes a GitHub Release with the extracted notes
- runs release guard validation before release publication

Manual runs are also supported via `workflow_dispatch`:

- set `tag_name` (required)
- optional `target_commitish`
- optional `prerelease`
- optional `dry_run=true` to validate changelog extraction without publishing

## 7) GitHub Release

- Create release from tag `vX.Y.Z`.
- Use the changelog section as release notes.
- Include any migration notes and rollout caveats.

## 8) Post-Release

- Create next `Unreleased` section if needed.
- Monitor CI and key runtime endpoints:
  - `/health`
  - `/ready`
  - `/status/{job_id}`
  - `/status/{job_id}/quality`
