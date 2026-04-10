# Pilot Go/No-Go Quickcheck (5-minute gate)

Use this right before demo or pilot handoff.

One-command option:

```bash
make pilot-quickcheck
```

Auto-create and validate one preset job end-to-end:

```bash
make pilot-quickcheck-auto
```

Artifacts:
- `build/pilot-quickcheck/report.json`
- `build/pilot-quickcheck/report.md`
- with `JOB_ID` (or `AUTO_JOB=1`): `build/pilot-quickcheck/report_api.json` + `build/pilot-quickcheck/report_api.md`

## 1) Runtime up and healthy

```bash
make pilot-stack-check
```

Expected:
- `/health` returns 200
- `/ready` returns 200

## 2) Fast engineering gate

```bash
make qa-fast
```

Expected:
- tests pass
- `qa-hitl` pass
- mypy clean

## 3) Demo chain works end-to-end

```bash
make ci-demo-smoke
```

Expected:
- smoke artifacts created
- no blocker in summary

## 4) Export contract/readiness visible

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/quality | jq '.export_contract.submission_readiness_summary'
```

Expected:
- `readiness_status` present (`ready|partial|weak|missing`)
- `completeness_score` present
- `top_gap` present

## 5) Reviewer flow check

```bash
curl -s http://127.0.0.1:8000/status/<JOB_ID>/review/workflow | jq '.summary'
```

Expected:
- workflow summary present
- no unexpected stale/overdue spike before demo

---

## Decision rule

- **Go**: steps 1-3 pass, and steps 4-5 show expected structured output.
- **Conditional Go**: steps 1-3 pass but step 4 or 5 shows manageable warnings with owner/date.
- **No-Go**: step 1, 2, or 3 fails.
