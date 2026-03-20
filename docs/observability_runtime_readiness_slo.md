# Runtime Readiness + Safeguarding Observability SLOs

Related: #60 (follow-up to #56, #58)

## Scope
This SLO pack covers the production-critical path introduced by runtime readiness gates and safeguarding annex checks:
- `/ready` admission checks (readiness path)
- EU safeguarding annex generation + critic validation path

Measurement cadence: 5-minute windows, rolled up to 30-day objective windows.

## SLI Definitions

### SLI-1: Readiness Success Rate
- **Definition:** fraction of `/ready` probes returning HTTP `200` with `status=ready`
- **Formula:** `ready_success / ready_total`
- **Target:** **>= 99.5%** over 30 days
- **Error budget:** 0.5% (about 3h 36m degraded across 30 days)

### SLI-2: Readiness Latency p95
- **Definition:** p95 of `/ready` request duration
- **Formula:** `histogram_quantile(0.95, rate(grantflow_ready_request_duration_seconds_bucket[15m]))`
- **Target:** **<= 1.0s** for 99% of 15m windows
- **Error budget:** 1% of windows can exceed 1.0s

### SLI-3: Safeguarding Path Failure Rate
- **Definition:** failures in EU safeguarding annex generation + validation path per generation request
- **Formula:** `safeguarding_path_failures / safeguarding_path_total`
- **Target:** **<= 1.0%** over 30 days
- **Error budget:** 1.0%

### SLI-4: Safeguarding Path Latency p95
- **Definition:** p95 end-to-end duration from generation start to safeguarding verdict emitted
- **Target:** **<= 15s** for 99% of 15m windows

### SLI-5: Safeguarding Quality-State Drift Rate
- **Definition:** fraction of jobs where safeguarding quality-state regresses after retries (example: pass→fail or non-critical→critical)
- **Formula:** `safeguarding_quality_drift_events / safeguarding_path_total`
- **Target:** **<= 0.5%** over 30 days

## Alert Policy (Low-Noise Defaults)
- Warning alerts require sustained breach for 15m.
- Critical alerts require sustained breach for 30m or severe immediate condition.
- Page only on user-impacting symptoms (availability, high failure rate, severe drift).
- High-cardinality dimensions are excluded from alert labels to avoid alert storms.

See concrete Prometheus rules in: `monitoring/alerts/runtime_readiness_safeguarding.rules.yml`.

## Burn-Rate Guardrails
- Fast burn: budget consumption >14x over 15m (critical)
- Slow burn: budget consumption >2x over 6h (warning)

## Ownership + On-call
- **Primary owner:** Engineering Lead
- **Secondary owner:** QA Lead (safeguarding quality-state triage)
- **Escalation:** PM on duty if incident exceeds 30 minutes

Runbook: `docs/operations-runbook.md` (section "Runtime Readiness + Safeguarding Alert Triage").
