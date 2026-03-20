# Post-Merge Smoke Checklist + Definition of Done (Pilot)

Related: #61 (covers #35-#39 and #58)

Goal: verify critical pilot paths after merge in **< 20 minutes** with explicit go/no-go release gates.

## Time Budget (target: 15–20 min)

- 0–3 min: boot + health/readiness
- 3–12 min: bid/no-bid API smoke (#35-#39)
- 12–17 min: safeguarding annex readiness smoke (#58)
- 17–20 min: release gate + rollback decision

## Preconditions

```bash
pip install -r requirements-dev.lock
uvicorn grantflow.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
export API_BASE=http://127.0.0.1:8000
```

## 1) API Health/Readiness Gate (Required)

```bash
curl -sS "$API_BASE/health"
curl -sS "$API_BASE/ready"
```

Pass criteria:
- `/health` responds 200
- `/ready` responds 200 with `"status":"ready"`

Fail criteria:
- `/ready` is degraded (`503`) or reports blocking checks

---

## 2) Seed One Job (Shared Fixture for smoke)

```bash
GEN=$(curl -sS -X POST "$API_BASE/generate/from-preset" \
  -H 'Content-Type: application/json' \
  -d '{
    "preset_key": "eu_digital_governance_moldova",
    "preset_type": "auto",
    "llm_mode": false,
    "hitl_enabled": false
  }')

echo "$GEN"
JOB_ID=$(python3 - <<'PY'
import json,sys
print(json.loads(sys.stdin.read()).get("job_id",""))
PY
<<<"$GEN")

echo "JOB_ID=$JOB_ID"
```

Pass criteria:
- `JOB_ID` is non-empty

---

## 3) Bid/No-Bid Core Endpoint Smoke (#35)

```bash
curl -sS -X POST "$API_BASE/decision/bid-no-bid" \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_fit": 8,
    "strategic_alignment": 7,
    "delivery_capacity": 8,
    "compliance_readiness": 7,
    "budget_viability": 7,
    "competition_position": 6,
    "risk_exposure": 5,
    "donor_profile": "eu"
  }'
```

Pass criteria:
- response includes `verdict`, `weighted_score`
- response includes `preset_profile` when donor profile is provided

---

## 4) Job-Scoped Decision + Auto-Refresh Drift Smoke (#37)

```bash
curl -sS -X POST "$API_BASE/status/$JOB_ID/decision/bid-no-bid" \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_fit": 8,
    "strategic_alignment": 7,
    "delivery_capacity": 8,
    "compliance_readiness": 7,
    "budget_viability": 7,
    "competition_position": 6,
    "risk_exposure": 5,
    "donor_profile": "eu"
  }'

curl -sS "$API_BASE/status/$JOB_ID/quality"
```

Pass criteria:
- decision write succeeds (`200`)
- quality payload includes bid/no-bid block (no 5xx, no schema break)

---

## 5) Decision Trail Smoke (#38)

```bash
curl -sS "$API_BASE/status/$JOB_ID/decision/bid-no-bid/trail"
```

Pass criteria:
- returns trail array/object with at least one decision event

---

## 6) What-If Simulation Smoke (#39)

```bash
curl -sS -X POST "$API_BASE/decision/bid-no-bid/simulate" \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_fit": 8,
    "strategic_alignment": 7,
    "delivery_capacity": 8,
    "compliance_readiness": 7,
    "budget_viability": 7,
    "competition_position": 6,
    "risk_exposure": 5,
    "step": 10,
    "max_scenarios": 3,
    "donor_profile": "eu"
  }'
```

Pass criteria:
- response contains `baseline`
- response contains non-empty `scenarios`

---

## 7) Safeguarding Annex Readiness Smoke (#58)

```bash
curl -sS "$API_BASE/status/$JOB_ID" > /tmp/grantflow-status.json
python3 - <<'PY'
import json
p=json.load(open('/tmp/grantflow-status.json'))
state=p.get('state') or {}
toc=state.get('toc') or {}
annex=toc.get('safeguarding_annex') or []
print('annex_items=', len([x for x in annex if str(x).strip()]))
print('has_annex=', bool([x for x in annex if str(x).strip()]))
PY
```

Pass criteria:
- `has_annex=True` for EU preset flow
- annex has at least one non-empty item

---

## Definition of Done (DoD) — Pilot Post-Merge Gate

A merge is **Done** only when all required gates pass:

1. ✅ CI on merge commit is green
2. ✅ `/health` and `/ready` pass locally/integration env
3. ✅ Bid/no-bid smoke path passes (#35, #37, #38, #39)
4. ✅ EU safeguarding annex readiness smoke passes (#58)
5. ✅ No critical finding/regression introduced in smoke outputs
6. ✅ Checklist execution time is <= 20 minutes

If any required gate fails: **Do not release**.

## Rollback Criteria (Immediate)

Trigger rollback to previous known-good release/commit when any of these occur:

- `/ready` degraded or unstable after merge
- any bid/no-bid endpoint in smoke path returns 5xx or malformed schema
- decision trail endpoint fails or returns invalid structure
- EU safeguarding annex missing in EU preset readiness flow
- CI green but smoke reveals critical path regression

## Release Gate Decision

- **GO**: all required gates pass
- **NO-GO**: one or more required gates fail

Record result in PR comment using this template:

```text
Post-merge smoke (docs/post-merge-smoke-checklist.md):
- health/ready: PASS|FAIL
- bid/no-bid core: PASS|FAIL
- job decision + quality: PASS|FAIL
- decision trail: PASS|FAIL
- simulation: PASS|FAIL
- safeguarding annex: PASS|FAIL
- runtime: <N> min
Release gate: GO|NO-GO
```
