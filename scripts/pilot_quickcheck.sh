#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
JOB_ID="${JOB_ID:-}"
REPORT_DIR="${REPORT_DIR:-build/pilot-quickcheck}"
REPORT_JSON="$REPORT_DIR/report.json"
REPORT_MD="$REPORT_DIR/report.md"

mkdir -p "$REPORT_DIR"

printf "[1/4] Health check: %s\n" "$API_BASE"
curl -fsS "$API_BASE/health" >/dev/null
curl -fsS "$API_BASE/ready" >/dev/null

printf "[2/4] Local fast gate (qa-fast)\n"
make qa-fast >/dev/null

printf "[3/4] Demo smoke artifacts\n"
make ci-demo-smoke >/dev/null

python3 - "$API_BASE" "$JOB_ID" "$REPORT_JSON" "$REPORT_MD" <<'PY'
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

api_base, job_id, report_json_path, report_md_path = sys.argv[1:5]

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "api_base": api_base,
    "job_id": job_id or None,
    "checks": {
        "health": "pass",
        "ready": "pass",
        "qa_fast": "pass",
        "ci_demo_smoke": "pass",
    },
}

if job_id:
    def fetch_json(url: str):
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    quality = fetch_json(f"{api_base}/status/{job_id}/quality")
    metrics = fetch_json(f"{api_base}/status/{job_id}/metrics")
    export_payload = fetch_json(f"{api_base}/status/{job_id}/export-payload")
    workflow = fetch_json(f"{api_base}/status/{job_id}/review/workflow")

    readiness = ((export_payload.get("payload") or {}).get("submission_package_readiness") or {})
    report["checks"]["job_contract"] = "pass"
    report["terminal_status"] = metrics.get("terminal_status")
    report["quality"] = {
        "quality_score": quality.get("quality_score"),
        "critic_score": quality.get("critic_score"),
        "grounded_trust_score": ((metrics.get("grounding_trust_summary") or {}).get("score")),
    }
    report["export_readiness"] = {
        "readiness_status": readiness.get("readiness_status"),
        "completeness_score": readiness.get("completeness_score"),
        "top_gap": readiness.get("top_gap"),
    }
    report["workflow"] = {
        "summary_present": isinstance(workflow.get("summary"), dict),
    }

lines = [
    "# Pilot Quickcheck Report",
    "",
    f"- generated_at: {report.get('generated_at')}",
    f"- api_base: {api_base}",
    f"- job_id: {job_id or '-'}",
    "",
    "## Checks",
]
for key, value in (report.get("checks") or {}).items():
    lines.append(f"- {key}: {value}")

if job_id:
    lines.extend(
        [
            "",
            "## Quality",
            f"- quality_score: {(report.get('quality') or {}).get('quality_score')}",
            f"- critic_score: {(report.get('quality') or {}).get('critic_score')}",
            f"- grounded_trust_score: {(report.get('quality') or {}).get('grounded_trust_score')}",
            "",
            "## Export readiness",
            f"- readiness_status: {(report.get('export_readiness') or {}).get('readiness_status')}",
            f"- completeness_score: {(report.get('export_readiness') or {}).get('completeness_score')}",
            f"- top_gap: {(report.get('export_readiness') or {}).get('top_gap')}",
            "",
            "## Workflow",
            f"- summary_present: {(report.get('workflow') or {}).get('summary_present')}",
        ]
    )

pathlib.Path(report_json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
pathlib.Path(report_md_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

if [[ -n "$JOB_ID" ]]; then
  printf "[4/4] Job contract spot-check for %s\n" "$JOB_ID"
  curl -fsS "$API_BASE/status/$JOB_ID/quality" | python3 -c 'import json,sys;d=json.load(sys.stdin);s=((d.get("export_contract") or {}).get("submission_readiness_summary") or {});assert s.get("readiness_status") in {"ready","partial","weak","missing"};print("quality_ok")' >/dev/null
  curl -fsS "$API_BASE/status/$JOB_ID/review/workflow" | python3 -c 'import json,sys;d=json.load(sys.stdin);assert isinstance(d.get("summary"),dict);print("workflow_ok")' >/dev/null
fi

echo "pilot_quickcheck: PASS ($REPORT_JSON, $REPORT_MD)"
