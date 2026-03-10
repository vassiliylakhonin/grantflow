# Identity and RBAC Roadmap

This is the current reality and next-step roadmap for identity and access control.

## Current Reality

Today GrantFlow supports:
- API key auth
- startup security guards
- tenant allowlist controls
- route-family separation that can be enforced at the gateway

Today GrantFlow does not support:
- in-app user login
- in-app role management
- person-level audit history in job state

## Recommended Near-Term Posture

Use the gateway as the enforcement point for:
- reviewer
- operator
- approver
- ingest admin

This is the fastest credible way to close the enterprise trust gap without rewriting the core application.

## Roadmap

### Phase 1: Gateway-Enforced Access
- external SSO
- route authorization
- shared service API key
- gateway audit logs

### Phase 2: Identity Propagation
- trusted user headers from gateway
- actor attribution in review mutations and exports
- clearer audit story per action

### Phase 3: In-App RBAC
- explicit role model in app state
- object-aware permissions
- tenant-aware user/role mapping

## Public Positioning

Do not claim in-app enterprise IAM today.
Claim the honest posture:
- protected backend service
- gateway-enforced access
- clear roadmap for identity propagation and RBAC
