# What Production Means

This document defines the public production posture for GrantFlow.

## What Production Means Today

A credible bounded production deployment means:
- queue-backed execution (`redis_queue` + dedicated worker)
- persistent state stores
- API key enforcement at startup
- private network boundaries for Redis and Chroma
- gateway-enforced authentication and route authorization
- operator access to health, readiness, review workflow, and export paths

## What Production Does Not Mean Yet

GrantFlow does not currently claim:
- built-in SSO or OIDC login
- in-app RBAC
- person-level audit trail inside application state
- full procurement-suite automation
- automatic final submission to donor portals

## Recommended Production Shape

Use:
- `docs/reference-topology.md`
- `docs/enterprise-access-layer.md`
- `docs/enterprise-quickstart.md`

Recommended runtime:
- API in dispatcher mode
- dedicated worker process
- sqlite persistence for bounded deployments
- gateway or reverse proxy as the trust boundary

## What Stays Human-Owned

Even in a strong deployment, these remain human responsibilities:
- donor compliance sign-off
- pricing approval
- attachment completeness validation for final submission
- final approval to send externally

## What Buyers Should Infer Correctly

GrantFlow is ready to run as protected proposal-operations infrastructure.

It is not yet a full identity platform or full procurement submission platform.
