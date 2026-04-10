#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
JOB_ID="${JOB_ID:-}"

printf "[1/4] Health check: %s\n" "$API_BASE"
curl -fsS "$API_BASE/health" >/dev/null
curl -fsS "$API_BASE/ready" >/dev/null

printf "[2/4] Local fast gate (qa-fast)\n"
make qa-fast >/dev/null

printf "[3/4] Demo smoke artifacts\n"
make ci-demo-smoke >/dev/null

if [[ -n "$JOB_ID" ]]; then
  printf "[4/4] Job contract spot-check for %s\n" "$JOB_ID"
  curl -fsS "$API_BASE/status/$JOB_ID/quality" | python3 -c 'import json,sys;d=json.load(sys.stdin);s=((d.get("export_contract") or {}).get("submission_readiness_summary") or {});assert s.get("readiness_status") in {"ready","partial","weak","missing"};print("quality_ok")' >/dev/null
  curl -fsS "$API_BASE/status/$JOB_ID/review/workflow" | python3 -c 'import json,sys;d=json.load(sys.stdin);assert isinstance(d.get("summary"),dict);print("workflow_ok")' >/dev/null
fi

echo "pilot_quickcheck: PASS"
