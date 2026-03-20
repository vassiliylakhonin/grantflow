# Observability Dashboard Source of Truth (Pilot)

Related: #43, #55

## Dashboard Panels

| Panel | SLI | Query/Metric | Owner | Refresh |
|-------|-----|--------------|-------|---------|
| Generation latency (p50/p95) | Latency | `generation_duration_seconds` | Engineering | 1m |
| Job success vs failure | Error rate | `jobs_total{status}` | Engineering | 1m |
| Queue delay p95 | Queue delay | `queue_wait_seconds` | Engineering | 1m |
| Export success | Export success rate | `exports_total{status}` | Engineering | 1m |
| HITL review SLA | Approval timeliness | `review_approval_duration_seconds` | PM/QA | 5m |
| Critical findings trend | Compliance risk | critic severity counters | QA | 5m |

## Ownership Model
- **Primary owner:** Engineering lead (dashboard integrity)
- **Secondary owner:** PM (weekly pilot review)
- **QA owner:** compliance + critic findings panel

## Update Cadence
- During pilot: daily check-in + weekly trend review
- After pilot: weekly check-in unless alert triggered

## Alert Routing
- Warning: team channel notification
- Critical: direct escalation to Engineering lead + PM
