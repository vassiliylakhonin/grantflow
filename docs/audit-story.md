# Audit Story

GrantFlow is designed to make proposal workflow state inspectable even before it has full in-app identity and RBAC.

## What Is Auditable Today

Inside GrantFlow:
- job status and lifecycle
- citations
- versions and diffs
- critic findings
- review comments
- review workflow summaries
- export payloads and export readiness signals

At the platform layer:
- gateway access logs
- user identity from SSO
- route authorization decisions
- request timestamps and source IPs

## Recommended Audit Split

Use the gateway for:
- who accessed the system
- who was allowed to hit which route family
- which protected backend service key was used

Use GrantFlow for:
- what happened to the draft and review workflow
- which findings/comments were opened, acknowledged, resolved, or exported
- which evidence and versions were attached to the work product

## What This Means Practically

A bounded enterprise deployment can already answer:
- who entered the protected environment
- which role path they were allowed to use
- what happened inside the proposal workflow after that

## What Is Not Claimed Yet

GrantFlow does not yet claim:
- person-level identity embedded in every workflow event
- in-app RBAC decisions per object
- full immutable audit ledger semantics

Those remain future product work.
