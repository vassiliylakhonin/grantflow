from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from grantflow.api.idempotency import _normalize_request_id
from grantflow.api.review_runtime_helpers import _utcnow_iso
from grantflow.swarm.state_contract import normalize_state_contract


def _job_store():
    from grantflow.api import app as api_app_module

    return api_app_module.JOB_STORE


def _ingest_audit_store():
    from grantflow.api import app as api_app_module

    return api_app_module.INGEST_AUDIT_STORE


def _dispatch_status_webhook(
    job_id: str, previous: Optional[Dict[str, Any]], current: Optional[Dict[str, Any]]
) -> None:
    from grantflow.api.review_service import _dispatch_job_webhook_for_status_change

    _dispatch_job_webhook_for_status_change(job_id, previous, current)


def _append_job_event_records(
    previous: Optional[Dict[str, Any]],
    next_payload: Dict[str, Any],
) -> Dict[str, Any]:
    events = []
    raw_previous_events = (previous or {}).get("job_events")
    if isinstance(raw_previous_events, list):
        events = [e for e in raw_previous_events if isinstance(e, dict)]

    if isinstance(next_payload.get("job_events"), list):
        events = [e for e in next_payload["job_events"] if isinstance(e, dict)]

    prev_status = (previous or {}).get("status")
    next_status = next_payload.get("status")
    if prev_status != next_status and next_status is not None:
        events = list(events)
        events.append(
            {
                "event_id": str(uuid.uuid4()),
                "ts": _utcnow_iso(),
                "type": "status_changed",
                "from_status": None if prev_status is None else str(prev_status),
                "to_status": str(next_status),
                "status": str(next_status),
            }
        )

    if events:
        next_payload["job_events"] = events[-200:]
    return next_payload


def _record_job_event(job_id: str, event_type: str, **fields: Any) -> None:
    store = _job_store()
    job = store.get(job_id)
    if not job:
        return
    existing = job.get("job_events")
    events = [e for e in existing if isinstance(e, dict)] if isinstance(existing, list) else []
    request_id = _normalize_request_id(fields.get("request_id"))
    if request_id:
        for row in reversed(events):
            if not isinstance(row, dict):
                continue
            if str(row.get("type") or "") != event_type:
                continue
            if str(row.get("request_id") or "") != request_id:
                continue
            return
    event: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "ts": _utcnow_iso(),
        "type": event_type,
        "status": str(job.get("status") or ""),
    }
    for key, value in fields.items():
        event[str(key)] = value
    events.append(event)
    store.update(job_id, job_events=events[-200:])


def _record_ingest_event(
    *,
    donor_id: str,
    namespace: str,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "ts": _utcnow_iso(),
        "donor_id": str(donor_id or ""),
        "namespace": str(namespace or ""),
        "filename": str(filename or ""),
        "content_type": str(content_type or ""),
        "metadata": dict(metadata or {}),
        "result": dict(result or {}),
    }
    _ingest_audit_store().append(row)


def _list_ingest_events(
    *,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 50,
) -> list[Dict[str, Any]]:
    return _ingest_audit_store().list_recent(donor_id=donor_id, tenant_id=tenant_id, limit=limit)


def _ingest_inventory(*, donor_id: Optional[str] = None, tenant_id: Optional[str] = None) -> list[Dict[str, Any]]:
    inventory_fn = getattr(_ingest_audit_store(), "inventory", None)
    if callable(inventory_fn):
        rows = inventory_fn(donor_id=donor_id, tenant_id=tenant_id)
        return rows if isinstance(rows, list) else []
    rows = _list_ingest_events(donor_id=donor_id, tenant_id=tenant_id, limit=200)
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        raw_metadata = row.get("metadata")
        metadata: Dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        doc_family = str((metadata or {}).get("doc_family") or "").strip()
        donor = str(row.get("donor_id") or "").strip()
        tenant = str((metadata or {}).get("tenant_id") or "").strip()
        if not doc_family:
            continue
        key = f"{tenant.lower()}::{donor.lower()}::{doc_family}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = {
                "tenant_id": tenant or None,
                "donor_id": donor,
                "doc_family": doc_family,
                "count": 1,
                "latest_ts": row.get("ts"),
                "latest_filename": row.get("filename"),
                "latest_event_id": row.get("event_id"),
                "latest_source_type": metadata.get("source_type"),
            }
        else:
            current["count"] = int(current.get("count") or 0) + 1
    return list(grouped.values())


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    store = _job_store()
    previous = store.get(job_id)
    next_payload = dict(payload)
    state_payload = next_payload.get("state")
    if isinstance(state_payload, dict):
        normalize_state_contract(state_payload)

    if previous and previous.get("status") == "canceled" and next_payload.get("status") != "canceled":
        return

    for key in (
        "webhook_url",
        "webhook_secret",
        "client_metadata",
        "generate_preflight",
        "strict_preflight",
        "idempotency_records",
    ):
        if key not in next_payload and previous and key in previous:
            next_payload[key] = previous.get(key)

    next_payload = _append_job_event_records(previous, next_payload)
    store.set(job_id, next_payload)
    _dispatch_status_webhook(job_id, previous, next_payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    store = _job_store()
    previous = store.get(job_id)
    if previous and previous.get("status") == "canceled" and "status" in patch and patch.get("status") != "canceled":
        return previous
    next_patch = dict(patch)
    state_patch = next_patch.get("state")
    if isinstance(state_patch, dict):
        normalize_state_contract(state_patch)
    merged_preview = dict(previous or {})
    merged_preview.update(next_patch)
    merged_preview = _append_job_event_records(previous, merged_preview)
    if "job_events" in merged_preview:
        next_patch["job_events"] = merged_preview["job_events"]
    updated = store.update(job_id, **next_patch)
    _dispatch_status_webhook(job_id, previous, updated)
    return updated


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _job_store().get(job_id)


def _list_jobs() -> Dict[str, Dict[str, Any]]:
    list_fn = getattr(_job_store(), "list", None)
    if callable(list_fn):
        result = list_fn()
        if isinstance(result, dict):
            return result
    return {}
