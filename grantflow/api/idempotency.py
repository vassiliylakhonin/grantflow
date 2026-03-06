from __future__ import annotations

import json
import re
import threading
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
MAX_IDEMPOTENCY_RECORDS = 300
MAX_GLOBAL_IDEMPOTENCY_RECORDS = 1000
GLOBAL_IDEMPOTENCY_RECORDS: Dict[str, Dict[str, Any]] = {}
GLOBAL_IDEMPOTENCY_LOCK = threading.Lock()


def _app_module():
    from grantflow.api import app as api_app_module

    return api_app_module


def _normalize_request_id(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    if not REQUEST_ID_RE.fullmatch(token):
        raise HTTPException(
            status_code=400,
            detail="Invalid request_id (allowed: letters, numbers, ., _, :, -, length 1..120)",
        )
    return token


def _resolve_request_id(request: Request, explicit_request_id: Optional[str] = None) -> Optional[str]:
    return _normalize_request_id(explicit_request_id) or _normalize_request_id(request.headers.get("x-request-id"))


def _idempotency_fingerprint(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _idempotency_record_key(scope: str, request_id: str) -> str:
    return f"{scope}:{request_id}"


def _idempotency_records(job: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = job.get("idempotency_records")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        out[key] = dict(value)
    return out


def _idempotency_replay_response(
    job: Dict[str, Any],
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    token = _normalize_request_id(request_id)
    if not token:
        return None
    key = _idempotency_record_key(scope, token)
    record = _idempotency_records(job).get(key)
    if not isinstance(record, dict):
        return None
    record_fingerprint = str(record.get("fingerprint") or "")
    if record_fingerprint and record_fingerprint != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "request_id_reused_with_different_payload",
                "message": "request_id is already used for a different action payload.",
                "request_id": token,
                "scope": scope,
            },
        )
    response_payload = record.get("response")
    if isinstance(response_payload, dict):
        replay = dict(response_payload)
    else:
        replay = {}
    replay["request_id"] = token
    replay["idempotent_replay"] = True
    replay["persisted"] = bool(record.get("persisted", True))
    return replay


def _store_idempotency_response(
    job_id: str,
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    token = _normalize_request_id(request_id)
    if not token:
        return
    job = _app_module()._get_job(job_id)
    if not job:
        return
    records = _idempotency_records(job)
    key = _idempotency_record_key(scope, token)
    stored_response = dict(response)
    stored_response.pop("idempotent_replay", None)
    stored_response["request_id"] = token
    records[key] = {
        "scope": scope,
        "request_id": token,
        "fingerprint": fingerprint,
        "persisted": bool(persisted),
        "ts": _app_module()._utcnow_iso(),
        "response": stored_response,
    }
    while len(records) > MAX_IDEMPOTENCY_RECORDS:
        oldest_key = next(iter(records))
        records.pop(oldest_key, None)
    _app_module()._update_job(job_id, idempotency_records=records)


def _global_idempotency_record_key(scope: str, request_id: str) -> str:
    return f"{scope}:{request_id}"


def _global_idempotency_replay_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    token = _normalize_request_id(request_id)
    if not token:
        return None
    key = _global_idempotency_record_key(scope, token)
    with GLOBAL_IDEMPOTENCY_LOCK:
        record = dict(GLOBAL_IDEMPOTENCY_RECORDS.get(key) or {})
    if not record:
        return None
    record_fingerprint = str(record.get("fingerprint") or "")
    if record_fingerprint and record_fingerprint != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "request_id_reused_with_different_payload",
                "message": "request_id is already used for a different action payload.",
                "request_id": token,
                "scope": scope,
            },
        )
    response_payload = record.get("response")
    if isinstance(response_payload, dict):
        replay = dict(response_payload)
    else:
        replay = {}
    replay["request_id"] = token
    replay["idempotent_replay"] = True
    replay["persisted"] = bool(record.get("persisted", True))
    return replay


def _store_global_idempotency_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    token = _normalize_request_id(request_id)
    if not token:
        return
    key = _global_idempotency_record_key(scope, token)
    stored_response = dict(response)
    stored_response.pop("idempotent_replay", None)
    stored_response["request_id"] = token
    with GLOBAL_IDEMPOTENCY_LOCK:
        GLOBAL_IDEMPOTENCY_RECORDS[key] = {
            "scope": scope,
            "request_id": token,
            "fingerprint": fingerprint,
            "persisted": bool(persisted),
            "ts": _app_module()._utcnow_iso(),
            "response": stored_response,
        }
        while len(GLOBAL_IDEMPOTENCY_RECORDS) > MAX_GLOBAL_IDEMPOTENCY_RECORDS:
            oldest_key = next(iter(GLOBAL_IDEMPOTENCY_RECORDS))
            GLOBAL_IDEMPOTENCY_RECORDS.pop(oldest_key, None)
