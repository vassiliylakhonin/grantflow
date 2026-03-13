# Security Policy

## Reporting a Vulnerability

Please do not open public GitHub issues for suspected vulnerabilities.

Preferred disclosure path:

1. Use GitHub Security Advisories (private report) for this repository.
2. Include:
   - affected component/file
   - reproduction steps
   - impact assessment
   - suggested fix (if available)

You can expect an acknowledgment and triage update as quickly as maintainers are available.

## Supported Deployment Assumptions

GrantFlow is a backend API service. Security posture assumes:

- service is deployed behind standard network controls (reverse proxy, firewall, TLS termination)
- environment variables and secrets are managed by deployment platform (not hardcoded in repo)
- production uses explicit auth and persistent state configuration

Current recommended production baseline:

- `GRANTFLOW_ENV=production`
- `GRANTFLOW_API_KEY` configured
- `GRANTFLOW_JOB_RUNNER_MODE=redis_queue`
- persistent stores (`GRANTFLOW_JOB_STORE=sqlite`, `GRANTFLOW_HITL_STORE=sqlite`, `GRANTFLOW_INGEST_STORE=sqlite`)

## Secret and Config Handling

- Never commit real secrets (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GRANTFLOW_API_KEY`, provider tokens).
- Use `.env.example` as template only.
- Rotate secrets if exposure is suspected.
- Prefer dedicated credentials per environment (dev/staging/prod), not shared keys.

## Authentication Posture (Current Reality)

Current API auth model is API key based:

- write endpoints require `X-API-Key` when `GRANTFLOW_API_KEY` is configured
- read endpoints can also be protected depending on runtime configuration
- startup guards can enforce API key presence in production

GrantFlow does not claim built-in enterprise IAM features (OIDC/SAML/RBAC) in this repository.
If those controls are required, enforce them at the platform or gateway layer.

## Scope Notes

- This repository contains backend orchestration and operational controls, not final donor submission workflows.
- Human review is still expected for compliance-critical outputs.
- Security controls should be layered with infrastructure controls (network policy, secrets manager, monitoring, backups).
