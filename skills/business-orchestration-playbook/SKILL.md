---
name: business-orchestration-playbook
description: Orchestrate business idea analysis with strict flow: ask 2-3 clarifying questions, run strategy+market+finance+commercial in parallel, then synthesize one decision memo with risks, verdict, and 30/60/90 plan. Use when the user asks for startup/business evaluation, go-to-market viability, market+financial assessment, or a Go/No-Go recommendation.
---

# Business Orchestration Playbook

Enforce this exact sequence:
1. Ask 2-3 clarifying questions (only missing high-impact inputs).
2. Spawn four specialists in parallel: strategy, market, finance, commercial.
3. Synthesize into one memo with contradictions resolved.

Required input schema before spawning:
- objective
- horizon_days
- budget_range
- geography
- target_ICP
- constraints
- success_criteria

Required specialist output schema:
- thesis (1-2 lines)
- assumptions (explicit)
- evidence (with source quality)
- numbers (ranges)
- top_3_risks
- next_5_actions
- confidence (0-100 + why)

Required final memo sections:
- Executive summary
- Verdict: Go / Conditional Go / No-Go
- Why now / why not now
- Gate conditions (numbers + date)
- Top risks and mitigations
- 30/60/90 day action plan
- Data gaps to validate next

Always include:
- conflict table (conflict, why it differs, 1-2 week validation test)
- explicit uncertainty and assumptions
- no fake precision
