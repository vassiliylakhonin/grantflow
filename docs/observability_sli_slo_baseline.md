# Observability Baseline + SLOs (Pilot)

Related: #43, #54, #45, #55

See also: `docs/observability_dashboard_source_of_truth.md` for panel mapping and ownership.

## Core SLIs (Formulas)
- **Generation latency p95** = p95(`generation_duration_seconds`) over 1h window
- **Job error rate** = failed_jobs / total_jobs over 1h window
- **Queue delay p95** = p95(`queue_wait_seconds`) over 1h window
- **Export success rate** = successful_exports / total_exports over 1h window

## Initial SLO Targets
- Latency p95 <= 120s (monthly objective: 95% of 1h windows)
- Job error rate <= 2% (monthly objective: 99% of 1h windows)
- Queue delay p95 <= 15s (monthly objective: 95% of 1h windows)
- Export success >= 98% (monthly objective: 99% of 1h windows)

## Alert Thresholds
- **Warning**: one 1h window breach
- **Critical**: three consecutive 1h window breaches

## Ownership
- Primary: Engineering lead
- Secondary: On-duty reviewer (pilot week rota)

## Incident Runbook (minimum)
1. Triage failing SLI + impacted job IDs
2. Decide: rollback recent change vs isolate queue/export path
3. Post incident note in pilot run log
4. Add follow-up issue with metric snapshot
