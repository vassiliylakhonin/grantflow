# CI Maintenance

## Update policy

- Dependabot creates weekly update PRs for GitHub Actions and pip dependencies.
- Patch/minor Dependabot updates are auto-merged after required checks pass.
- Major updates are left for manual review.

## If CI fails on a dependency PR

1. Open failed job log (`gh pr checks <pr-number>`).
2. Fix forward in the dependency PR branch if change is safe.
3. If unsafe, close the PR and pin version explicitly in `pyproject.toml`/workflow.

## Manual CI trigger

Use workflow_dispatch when PR event CI is stale or needs a clean rerun:

```bash
gh workflow run CI --ref <branch>
```

Then verify:

```bash
gh pr checks <pr-number>
```
