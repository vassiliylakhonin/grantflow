# Gateway Policy Example

This document shows a concrete, bounded way to front GrantFlow with enterprise access controls without changing the core application model.

Use this with:
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/docs/enterprise-access-layer.md`
- `/Users/vassiliylakhonin/Documents/aidgraph-prod/docs/pilot-role-mapping-worksheet.md`

## Target Posture

Public path:
- enterprise user -> IdP / SSO -> gateway -> GrantFlow API

Private path:
- gateway -> GrantFlow API
- GrantFlow API -> Redis / Chroma / worker

Do not expose Redis or Chroma publicly.

## Minimal Gateway Responsibilities

The gateway should do four things:
1. authenticate the user against enterprise SSO
2. map the user into one GrantFlow operating role
3. enforce route-family authorization
4. inject the shared `X-API-Key` toward GrantFlow

## Role Mapping

Suggested external groups:
- `grantflow-viewers`
- `grantflow-operators`
- `grantflow-reviewers`
- `grantflow-approvers`
- `grantflow-ingest-admins`

Suggested mapping:
- `grantflow-viewers` -> read-only routes
- `grantflow-operators` -> generate/export + read routes
- `grantflow-reviewers` -> comment/finding mutation + read routes
- `grantflow-approvers` -> reviewer routes + HITL approve/resume
- `grantflow-ingest-admins` -> ingest and inventory routes

## Route Family Authorization

### Read-only
Allow:
- `GET /health`
- `GET /ready`
- `GET /status/*`
- `GET /portfolio/*`
- `GET /donors`
- `GET /demo` only for internal eval environments

Groups:
- viewers
- operators
- reviewers
- approvers
- ingest admins

### Draft / Run
Allow:
- `POST /generate`
- `POST /generate/from-preset`
- `POST /generate/from-preset/batch`
- `POST /generate/preflight`
- `POST /export`
- `POST /cancel/*`

Groups:
- operators
- approvers if needed

### Review Operations
Allow:
- `POST /status/{job_id}/critic/findings/*`
- `POST /status/{job_id}/comments/*`
- `POST /status/{job_id}/comments/bulk-status`
- `POST /status/{job_id}/critic/findings/bulk-status`
- `GET /status/{job_id}/review/workflow*`

Groups:
- reviewers
- approvers
- operators if they own triage

### HITL Approvals
Allow:
- `POST /hitl/approve`
- `POST /resume/{job_id}`

Groups:
- approvers
- operators only if your process explicitly allows it

### Corpus Administration
Allow:
- `POST /ingest`
- `GET /ingest/*`

Groups:
- ingest admins
- operators only if corpus ownership is delegated

## Tenant Header Pattern

If tenant authz is enabled in GrantFlow, the gateway should inject one tenant consistently:
- `X-Tenant-ID: <tenant>`

Do not let external callers choose arbitrary tenant IDs on a shared endpoint.

Recommended pattern:
- map user/group -> tenant at the gateway
- inject fixed tenant header downstream
- block cross-tenant access before request reaches GrantFlow

## Shared API Key Pattern

GrantFlow's built-in auth is API-key based.

Recommended pattern:
- store one shared downstream API key in the gateway secret store
- inject it as:
  - `X-API-Key: <secret>`
- do not distribute the downstream API key directly to end users

## Example Reverse Proxy Rules (Pseudo Policy)

```text
if not authenticated(user):
  deny

if path in READ_ONLY and user in any grantflow group:
  allow

if path in DRAFT_RUN and user in operators or approvers:
  allow

if path in REVIEW_OPERATIONS and user in reviewers or approvers or operators:
  allow

if path in HITL_APPROVALS and user in approvers:
  allow

if path in CORPUS_ADMIN and user in ingest_admins:
  allow

otherwise:
  deny
```

## Recommended Pilot Defaults

For a bounded enterprise-style pilot:
- enable `GRANTFLOW_API_KEY`
- enable tenant authz if multiple customer teams share one environment
- expose only the gateway publicly
- keep `/demo` internal only
- keep queue admin routes internal only

## What To Log At The Gateway

Log at least:
- authenticated user id
- mapped role/group
- mapped tenant
- method + path
- response code
- request timestamp

This gives you person-level audit outside GrantFlow without changing GrantFlow core state.
