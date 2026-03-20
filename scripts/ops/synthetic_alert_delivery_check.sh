#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ALERT_WEBHOOK_URL:-}" ]]; then
  echo "ALERT_WEBHOOK_URL is required"
  exit 2
fi

now_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

payload=$(cat <<JSON
[
  {
    "status": "firing",
    "labels": {
      "alertname": "GrantFlowSyntheticAlertDeliveryCheck",
      "severity": "info",
      "service": "grantflow",
      "check": "synthetic-e2e"
    },
    "annotations": {
      "summary": "Synthetic alert delivery check",
      "description": "End-to-end webhook delivery test for GrantFlow observability alerts.",
      "runbook": "docs/operations-runbook.md#11-runtime-readiness--safeguarding-alert-triage"
    },
    "startsAt": "${now_utc}",
    "generatorURL": "https://github.com/vassiliylakhonin/grantflow/actions"
  }
]
JSON
)

http_code="$(curl -sS -o /tmp/grantflow-alert-webhook-response.txt -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST \
  --data "$payload" \
  "$ALERT_WEBHOOK_URL")"

if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
  echo "Synthetic alert delivery failed (HTTP ${http_code})."
  echo "Response:"
  cat /tmp/grantflow-alert-webhook-response.txt
  exit 1
fi

echo "Synthetic alert delivery succeeded (HTTP ${http_code})."
