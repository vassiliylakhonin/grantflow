# Security Ops Runbook

Practical runbook for ongoing security hygiene in GrantFlow environments.

## Scope

Covers:
- CI security checks (CodeQL, pip-audit, Trivy FS/Image)
- Runtime security baseline verification
- Vulnerability triage and patch workflow

Does not replace host/network hardening (firewall, IAM, TLS termination, secrets manager).

## 1) Weekly security cadence

1. Review GitHub Security tab alerts (CodeQL + Trivy SARIF findings).
2. Review latest `Security` workflow run and failed job logs.
3. Triage by severity:
   - **Critical**: immediate mitigation/rollback/patch.
   - **High**: patch in current sprint.
   - **Medium/Low**: backlog with owner and due date.
4. Re-run security workflow after remediation.

## 2) CI checks included

Current `security.yml` performs:
- `pip-audit` against Python dependencies
- `CodeQL` static analysis
- `Trivy` filesystem scan (`vuln,misconfig,secret`)
- `Trivy` container image scan (built from current `Dockerfile`)

Expected behavior:
- HIGH/CRITICAL findings fail the job.
- Trivy and CodeQL findings are uploaded to GitHub Security as SARIF.

## 3) Runtime verification (post-deploy)

Run after each production rollout:

```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/ready | jq .
```

Checks:
- readiness is `ready`
- no critical `configuration_warnings`
- redis worker heartbeat present when using `redis_queue`

Optional queue heartbeat check:

```bash
curl -s -H 'X-API-Key: <key>' http://127.0.0.1:8000/queue/worker-heartbeat | jq .
```

## 4) Container hardening baseline

Expected defaults in compose:
- `no-new-privileges:true`
- `cap_drop: [ALL]` for API/worker
- `read_only: true` for API/worker with writable volume only for `/data`
- `tmpfs` mount for `/tmp`
- Redis/Chroma bound to localhost unless explicit external need

If any item drifts, open a hardening follow-up before next release.

## 5) Vulnerability response playbook

1. Capture finding details (package/image layer/file path, CVE, severity).
2. Determine exploitability in current deployment.
3. Mitigate quickly:
   - bump dependency
   - rebuild image
   - reduce exposure (disable feature / restrict network)
4. Verify fix:
   - rerun `security.yml`
   - rerun smoke tests (`/health`, `/ready`, minimal generate flow)
5. Document outcome in release notes/changelog.

## 6) Fast incident checklist

1. Freeze deploys if active exploitation suspected.
2. Rotate potentially exposed secrets (`OPENAI_API_KEY`, `GRANTFLOW_API_KEY`, etc.).
3. Rebuild from clean base image and redeploy.
4. Verify audit logs and unusual job activity.
5. Publish internal postmortem with timeline and preventive action.
