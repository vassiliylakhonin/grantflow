# Release Process

## 1) Prepare

- Ensure `main` is green in CI.
- Confirm changelog entries exist under `Unreleased`.
- Confirm README/docs reflect shipped behavior.

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

## 5) GitHub Release Automation

The repository includes `.github/workflows/release.yml`:

- auto-runs on pushed tags matching `v*.*.*`
- extracts release notes for that version from `CHANGELOG.md`
- publishes a GitHub Release with the extracted notes

Manual runs are also supported via `workflow_dispatch`:

- set `tag_name` (required)
- optional `target_commitish`
- optional `prerelease`
- optional `dry_run=true` to validate changelog extraction without publishing

## 6) GitHub Release

- Create release from tag `vX.Y.Z`.
- Use the changelog section as release notes.
- Include any migration notes and rollout caveats.

## 7) Post-Release

- Create next `Unreleased` section if needed.
- Monitor CI and key runtime endpoints:
  - `/health`
  - `/ready`
  - `/status/{job_id}`
  - `/status/{job_id}/quality`
