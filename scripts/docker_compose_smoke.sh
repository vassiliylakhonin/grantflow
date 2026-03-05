#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is not available"
  exit 1
fi

# shellcheck disable=SC2329 # Invoked indirectly via trap.
cleanup() {
  # shellcheck disable=SC2317 # Executed via trap on EXIT.
  "${COMPOSE_CMD[@]}" logs api >/tmp/grantflow-docker-compose-api.log 2>&1 || true
  # shellcheck disable=SC2317 # Executed via trap on EXIT.
  "${COMPOSE_CMD[@]}" down -v --remove-orphans || true
}
trap cleanup EXIT

"${COMPOSE_CMD[@]}" down -v --remove-orphans || true
"${COMPOSE_CMD[@]}" up -d --build

for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  sleep 2
done
curl -fsS http://127.0.0.1:8000/health >/dev/null

ready_payload=""
for _ in $(seq 1 90); do
  ready_payload="$(curl -sS http://127.0.0.1:8000/ready || true)"
  if [[ -n "${ready_payload}" ]] && python3 -c '
import json,sys
payload=json.loads(sys.stdin.read())
checks=payload.get("checks") or {}
job_runner=checks.get("job_runner") or {}
worker_heartbeat=job_runner.get("queue", {}).get("worker_heartbeat")
ok=(
    payload.get("status")=="ready"
    and str(job_runner.get("mode") or "")=="redis_queue"
    and bool(job_runner.get("ready")) is True
    and isinstance(worker_heartbeat, dict)
    and bool(worker_heartbeat.get("healthy")) is True
)
raise SystemExit(0 if ok else 1)
' <<<"${ready_payload}"; then
    break
  fi
  sleep 2
done

python3 -c '
import json,sys
payload=json.loads(sys.stdin.read())
checks=payload.get("checks") or {}
job_runner=checks.get("job_runner") or {}
worker_heartbeat=job_runner.get("queue", {}).get("worker_heartbeat")
ok=(
    payload.get("status")=="ready"
    and str(job_runner.get("mode") or "")=="redis_queue"
    and bool(job_runner.get("ready")) is True
    and isinstance(worker_heartbeat, dict)
    and bool(worker_heartbeat.get("healthy")) is True
)
if not ok:
    raise SystemExit("docker-compose smoke: /ready did not confirm redis_queue + healthy external worker heartbeat")
' <<<"${ready_payload}"

generate_payload='{"donor_id":"usaid","input_context":{"project":"Docker Smoke Proposal","country":"Kenya"},"llm_mode":false,"hitl_enabled":false}'
generate_response="$(curl -fsS -X POST http://127.0.0.1:8000/generate -H 'Content-Type: application/json' -d "${generate_payload}")"
job_id="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["job_id"])' <<<"${generate_response}")"

terminal_status=""
for _ in $(seq 1 90); do
  status_payload="$(curl -fsS "http://127.0.0.1:8000/status/${job_id}")"
  terminal_status="$(python3 -c 'import json,sys; print((json.loads(sys.stdin.read()).get("status") or "").strip())' <<<"${status_payload}")"
  if [[ "${terminal_status}" == "done" ]]; then
    echo "docker-compose smoke: job ${job_id} completed"
    exit 0
  fi
  if [[ "${terminal_status}" == "error" || "${terminal_status}" == "canceled" ]]; then
    echo "docker-compose smoke: job ${job_id} terminal status=${terminal_status}"
    exit 1
  fi
  sleep 2
done

echo "docker-compose smoke: timeout waiting for terminal success (last_status=${terminal_status:-unknown})"
exit 1
