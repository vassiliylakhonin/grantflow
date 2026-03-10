# Enterprise Access Checklist

Use this checklist when moving from a bounded pilot posture to a more credible enterprise-facing access posture.

## 1. Identity Front Door

Confirm:
- enterprise SSO / IdP chosen
- gateway or API management layer chosen
- GrantFlow API is not directly exposed to the public internet

## 2. Shared Backend Auth

Confirm:
- `GRANTFLOW_API_KEY` is set
- gateway injects `X-API-Key`
- downstream API key is stored in gateway secrets, not shared with end users

## 3. Role Mapping

Confirm role owners:
- viewer
- operator
- reviewer
- approver
- ingest admin

Confirm external group mapping exists for each role.

## 4. Route Authorization

Confirm route-family policy exists for:
- read-only
- draft/run
- review operations
- HITL approvals
- ingest administration
- queue admin routes kept internal only

## 5. Tenant Controls

If multi-tenant:
- `GRANTFLOW_TENANT_AUTHZ_ENABLED=true`
- `GRANTFLOW_ALLOWED_TENANTS` is non-empty
- `GRANTFLOW_DEFAULT_TENANT` is valid
- gateway injects fixed `X-Tenant-ID`
- callers cannot override tenant arbitrarily

## 6. Network Boundaries

Confirm:
- Redis private only
- Chroma private only
- worker private only
- GrantFlow API reachable from gateway only where possible

## 7. Internal-Only Surfaces

Keep internal-only unless there is a strong reason otherwise:
- `/demo`
- `/queue/*`
- dead-letter inspection routes
- raw review workflow debug paths if exposed in a shared environment

## 8. Logging / Audit

At gateway or platform layer, log:
- user id
- tenant id
- role/group
- method/path
- response code
- timestamp

## 9. Production Guards

Confirm `/ready` shows no critical auth/config warnings.

At minimum check:
- API key configured
- tenant authz config valid if enabled
- persistent stores enabled
- queue mode aligned with deployment posture

## 10. Minimum Acceptable Enterprise-Style Posture

A credible enterprise access posture for GrantFlow does not require in-app SSO.

It does require:
- gateway-enforced authentication
- gateway-enforced route authorization
- protected backend network
- explicit tenant policy when shared
- operational ownership of roles and route families
