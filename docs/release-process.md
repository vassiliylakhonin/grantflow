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

## 5) GitHub Release

- Create release from tag `vX.Y.Z`.
- Use the changelog section as release notes.
- Include any migration notes and rollout caveats.

## 6) Post-Release

- Create next `Unreleased` section if needed.
- Monitor CI and key runtime endpoints:
  - `/health`
  - `/ready`
  - `/status/{job_id}`
  - `/status/{job_id}/quality`

