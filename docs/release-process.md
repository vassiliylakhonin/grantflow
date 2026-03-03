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

## 4) Cut Tag (Recommended: CI)

Use CI workflow `.github/workflows/release-cut.yml` with manual approval gate:

- workflow: `Release Cut`
- inputs:
  - `version` (e.g. `2.1.1`)
  - `target_commitish` (default `main`)
  - optional `dry_run=true`
- approval: job `cut-tag` runs in GitHub Environment `release` (configure required reviewers there)

This flow:

- validates SemVer input and tag uniqueness
- runs `scripts/release_guard.py --tag vX.Y.Z`
- creates and pushes annotated tag `vX.Y.Z`
- triggers `.github/workflows/release.yml` automatically via tag push

Optional local fallback:

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

For pull requests, CI also enforces Conventional Commit PR titles via:

```bash
python scripts/pr_title_guard.py --title "feat(scope): summary"
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

## 7) Release Drafting

The repository uses Release Drafter:

- workflow: `.github/workflows/release-drafter.yml`
- config: `.github/release-drafter.yml`
- updates a draft GitHub release automatically on PR/push events
- resolves proposed next version from labels (`semver:major|minor|patch`, plus `feat/fix/...`)

## 8) GitHub Release

- Create release from tag `vX.Y.Z`.
- Use the changelog section as release notes.
- Include any migration notes and rollout caveats.

## 9) Post-Release

- Create next `Unreleased` section if needed.
- Monitor CI and key runtime endpoints:
  - `/health`
  - `/ready`
  - `/status/{job_id}`
  - `/status/{job_id}/quality`
