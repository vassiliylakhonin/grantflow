from __future__ import annotations

import logging
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _max_attempts() -> int:
    return max(1, _env_int("GRANTFLOW_WEBHOOK_MAX_ATTEMPTS", 3))


def _timeout_seconds() -> float:
    return max(0.1, _env_float("GRANTFLOW_WEBHOOK_TIMEOUT_S", 5.0))


def _backoff_base_seconds() -> float:
    base_ms = max(0, _env_int("GRANTFLOW_WEBHOOK_BACKOFF_BASE_MS", 250))
    return base_ms / 1000.0


def _backoff_max_seconds() -> float:
    max_ms = max(0, _env_int("GRANTFLOW_WEBHOOK_BACKOFF_MAX_MS", 2000))
    return max_ms / 1000.0


def _retryable_status_code(status_code: int) -> bool:
    return status_code == 429 or status_code == 408 or 500 <= status_code <= 599


def _backoff_delay_s(attempt_number: int) -> float:
    # attempt_number is 1-based failure count.
    base = _backoff_base_seconds()
    if base <= 0:
        return 0.0
    delay = base * (2 ** max(0, attempt_number - 1))
    return min(delay, _backoff_max_seconds())


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

    attempts = _max_attempts()
    timeout_s = _timeout_seconds()
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(url, content=body, headers=headers, timeout=timeout_s)
            if 200 <= response.status_code < 300:
                logger.info(
                    "Webhook delivery succeeded (event=%s job_id=%s status=%s attempt=%s code=%s)",
                    event,
                    job_id,
                    payload["status"],
                    attempt,
                    response.status_code,
                )
                return

            retryable = _retryable_status_code(response.status_code)
            message = (
                f"Webhook delivery returned HTTP {response.status_code}"
                f" (event={event} job_id={job_id} attempt={attempt}/{attempts})"
            )
            if retryable and attempt < attempts:
                logger.warning("%s; retrying", message)
                delay_s = _backoff_delay_s(attempt)
                if delay_s > 0:
                    time.sleep(delay_s)
                continue

            logger.warning("%s; giving up", message)
            response.raise_for_status()
            return
        except httpx.RequestError as exc:
            last_error = exc
            if attempt < attempts:
                logger.warning(
                    "Webhook delivery failed (event=%s job_id=%s attempt=%s/%s): %s; retrying",
                    event,
                    job_id,
                    attempt,
                    attempts,
                    exc,
                )
                delay_s = _backoff_delay_s(attempt)
                if delay_s > 0:
                    time.sleep(delay_s)
                continue

            logger.warning(
                "Webhook delivery failed (event=%s job_id=%s attempt=%s/%s): %s; giving up",
                event,
                job_id,
                attempt,
                attempts,
                exc,
            )
            raise

    if last_error is not None:
        raise last_error
