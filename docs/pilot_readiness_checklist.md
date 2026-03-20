# Pilot Readiness Checklist (Go/No-Go)

Related: #41, #52, #44, #53

## Decision Rule
- **Go**: all Required gates pass (`✅`) and at most one Optional gate fails.
- **Conditional Go**: all Required gates pass, but >=2 Optional gates fail (requires mitigation owner/date).
- **No-Go**: any Required gate fails.

## Numeric Gates

| # | Gate | Threshold | Type | Data Source | Owner |
|---|------|-----------|------|-------------|-------|
| G1 | End-to-end draft success rate | >= 95% over last 50 runs | Required | CI `demo-smoke` + `/generate/from-preset` logs | Eng |
| G2 | P95 generation latency | <= 120 sec over last 50 runs | Required | app metrics: `generation_duration_seconds` | Eng |
| G3 | Queue wait p95 | <= 15 sec over last 100 jobs | Required | worker metric: `queue_wait_seconds` | Eng |
| G4 | Export success rate (`docx/xlsx/zip`) | >= 98% over last 100 exports | Required | `/export` events | Eng |
| G5 | Citation completeness | >= 90% sections with citation links | Required | critic findings + quality endpoint | QA |
| G6 | Critical compliance findings | 0 open critical findings | Required | critic severity report | QA |
| G7 | HITL SLA adherence | >= 90% approvals within 24h (last 20) | Optional | review workflow events | PM |
| G8 | Donor template readiness (pilot set) | 100% full coverage for selected pilot donors | Required | donor coverage matrix | PM |

## Sign-off
- Product/Delivery: **PM**
- Technical readiness: **Engineering lead**
- Quality/compliance: **QA lead**

## Top-5 Risk Register

| Risk | Probability | Impact | Trigger | Mitigation | Owner |
|------|-------------|--------|---------|------------|-------|
| Donor-specific section mismatch | Medium | High | >2 critic failures for donor-specific requirements in a week | Complete donor matrix + pre-submit checklist | PM |
| Latency regressions under burst load | Medium | High | P95 latency >120s for 2 consecutive days | Queue tuning + worker autoscaling profile | Eng |
| Export failures in docx/xlsx | Low | High | Export success drops below 98% | Add contract tests for exporters + rollback template set | Eng |
| Review bottleneck (HITL delays) | High | Medium | >20% approvals exceed 24h | Backup reviewer rota + escalation in 8h | PM |
| Source traceability gaps | Medium | High | Citation completeness <90% | Enforce citation gate before export | QA |

## Week 0–4 Plan

### Week 0 (setup)
- Freeze pilot donor set (2-3 donors)
- Confirm checklist gate owners
- Baseline metrics snapshot

### Week 1
- Run 10 controlled pilot jobs
- Validate Go/No-Go gates with real artifacts
- Fix blocker defects only

### Week 2
- Expand to 20 jobs
- Enforce review SLA + escalation path
- Verify exporter reliability thresholds

### Week 3
- Dry-run partner-facing workflow
- Measure donor-template fit on full pack
- Close all Required gate gaps

### Week 4 (decision)
- Final gate evaluation
- Go / Conditional Go / No-Go decision memo
- If Go: cut pilot-ready release and runbook handoff

## Exit Criteria
- All Required gates passing for 3 consecutive days
- No critical compliance findings
- Risk register has active mitigation owner/date for each open risk
