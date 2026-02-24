from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

import httpx


def _signature_header(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def send_job_webhook_event(
    *,
    url: str,
    secret: Optional[str],
    event: str,
    job_id: str,
    job: Dict[str, Any],
) -> None:
    payload = {
        "event": event,
        "job_id": job_id,
        "status": str(job.get("status") or ""),
        "job": job,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GrantFlow-Webhook/1.0",
    }
    if secret:
        headers["X-GrantFlow-Signature"] = _signature_header(secret, body)

    httpx.post(url, content=body, headers=headers, timeout=5.0)
