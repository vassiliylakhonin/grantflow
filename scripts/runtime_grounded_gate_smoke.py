#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


def _json_request(
    method: str,
    url: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {method} {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {method} {url}: {exc}") from exc

    if not body.strip():
        return {}
    parsed = json.loads(body)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError(f"Expected JSON object from {method} {url}, got: {type(parsed).__name__}")


def _wait_terminal_status(
    *,
    api_base: str,
    job_id: str,
    api_key: Optional[str],
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> Dict[str, Any]:
    status_url = f"{api_base}/status/{urllib.parse.quote(job_id)}"
    deadline = time.time() + timeout_seconds
    last_body: Dict[str, Any] = {}

    while time.time() < deadline:
        last_body = _json_request("GET", status_url, api_key=api_key)
        status = str(last_body.get("status") or "")
        if status in {"done", "error", "canceled"}:
            return last_body
        time.sleep(poll_interval_seconds)

    raise RuntimeError(f"Timed out waiting terminal status for job {job_id}. Last response: {last_body}")


def _start_job(
    *,
    api_base: str,
    donor_id: str,
    project: str,
    country: str,
    llm_mode: bool,
    architect_rag_enabled: bool,
    api_key: Optional[str],
) -> str:
    payload = {
        "donor_id": donor_id,
        "input_context": {
            "project": project,
            "country": country,
        },
        "llm_mode": llm_mode,
        "hitl_enabled": False,
        "architect_rag_enabled": architect_rag_enabled,
    }
    response = _json_request("POST", f"{api_base}/generate", payload=payload, api_key=api_key)
    job_id = str(response.get("job_id") or "").strip()
    if not job_id:
        raise RuntimeError(f"/generate did not return job_id: {response}")
    return job_id


def _grounding_gate_payload(*, api_base: str, job_id: str, api_key: Optional[str]) -> Dict[str, Any]:
    encoded_job = urllib.parse.quote(job_id)
    return _json_request("GET", f"{api_base}/status/{encoded_job}/grounding-gate", api_key=api_key)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime grounded quality gate smoke checks against live API.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--donor-id", default="usaid")
    parser.add_argument("--country", default="Kenya")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.5)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    api_base = str(args.api_base).rstrip("/")
    api_key = str(args.api_key or "").strip() or None

    pass_job_id = _start_job(
        api_base=api_base,
        donor_id=str(args.donor_id),
        project="Runtime gate smoke pass case",
        country=str(args.country),
        llm_mode=True,
        architect_rag_enabled=False,
        api_key=api_key,
    )
    pass_status = _wait_terminal_status(
        api_base=api_base,
        job_id=pass_job_id,
        api_key=api_key,
        timeout_seconds=float(args.timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
    )
    pass_gate_payload = _grounding_gate_payload(api_base=api_base, job_id=pass_job_id, api_key=api_key)
    pass_gate = pass_gate_payload.get("grounded_gate") if isinstance(pass_gate_payload, dict) else {}
    if not isinstance(pass_gate, dict):
        pass_gate = {}

    _expect(str(pass_status.get("status") or "") == "done", f"Pass scenario status expected done: {pass_status}")
    _expect(pass_gate.get("applicable") is False, f"Pass scenario should be not applicable: {pass_gate_payload}")
    _expect(pass_gate.get("blocking") is False, f"Pass scenario should not block: {pass_gate_payload}")
    _expect(pass_gate.get("passed") is True, f"Pass scenario should pass: {pass_gate_payload}")

    block_job_id = _start_job(
        api_base=api_base,
        donor_id=str(args.donor_id),
        project="Runtime gate smoke block case",
        country=str(args.country),
        llm_mode=True,
        architect_rag_enabled=True,
        api_key=api_key,
    )
    block_status = _wait_terminal_status(
        api_base=api_base,
        job_id=block_job_id,
        api_key=api_key,
        timeout_seconds=float(args.timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
    )
    block_gate_payload = _grounding_gate_payload(api_base=api_base, job_id=block_job_id, api_key=api_key)
    block_gate = block_gate_payload.get("grounded_gate") if isinstance(block_gate_payload, dict) else {}
    if not isinstance(block_gate, dict):
        block_gate = {}

    _expect(str(block_status.get("status") or "") == "error", f"Block scenario status expected error: {block_status}")
    _expect(block_gate.get("applicable") is True, f"Block scenario should be applicable: {block_gate_payload}")
    _expect(block_gate.get("blocking") is True, f"Block scenario should block: {block_gate_payload}")
    _expect(block_gate.get("passed") is False, f"Block scenario should fail gate: {block_gate_payload}")

    output = {
        "pass_job_id": pass_job_id,
        "pass_status": pass_status.get("status"),
        "pass_gate": pass_gate,
        "block_job_id": block_job_id,
        "block_status": block_status.get("status"),
        "block_gate": block_gate,
    }
    rendered = json.dumps(output, ensure_ascii=True, indent=2)
    print(rendered)
    json_out = str(args.json_out or "").strip()
    if json_out:
        with open(json_out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
