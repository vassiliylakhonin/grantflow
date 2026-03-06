from __future__ import annotations

from typing import Any, Dict, Optional


def _normalize_request_id(value: Any) -> Optional[str]:
    from grantflow.api.idempotency import _normalize_request_id as _impl

    return _impl(value)


def _resolve_request_id(request: Any, explicit_request_id: Optional[str] = None) -> Optional[str]:
    from grantflow.api.idempotency import _resolve_request_id as _impl

    return _impl(request, explicit_request_id)


def _idempotency_fingerprint(payload: Dict[str, Any]) -> str:
    from grantflow.api.idempotency import _idempotency_fingerprint as _impl

    return _impl(payload)


def _idempotency_record_key(scope: str, request_id: str) -> str:
    from grantflow.api.idempotency import _idempotency_record_key as _impl

    return _impl(scope, request_id)


def _idempotency_records(job: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    from grantflow.api.idempotency import _idempotency_records as _impl

    return _impl(job)


def _idempotency_replay_response(
    job: Dict[str, Any],
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    from grantflow.api.idempotency import _idempotency_replay_response as _impl

    return _impl(job, scope=scope, request_id=request_id, fingerprint=fingerprint)


def _store_idempotency_response(
    job_id: str,
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    from grantflow.api.idempotency import _store_idempotency_response as _impl

    _impl(
        job_id,
        scope=scope,
        request_id=request_id,
        fingerprint=fingerprint,
        response=response,
        persisted=persisted,
    )


def _global_idempotency_record_key(scope: str, request_id: str) -> str:
    from grantflow.api.idempotency import _global_idempotency_record_key as _impl

    return _impl(scope, request_id)


def _global_idempotency_replay_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    from grantflow.api.idempotency import _global_idempotency_replay_response as _impl

    return _impl(scope=scope, request_id=request_id, fingerprint=fingerprint)


def _store_global_idempotency_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    from grantflow.api.idempotency import _store_global_idempotency_response as _impl

    _impl(
        scope=scope,
        request_id=request_id,
        fingerprint=fingerprint,
        response=response,
        persisted=persisted,
    )


def _append_job_event_records(
    previous: Optional[Dict[str, Any]],
    next_payload: Dict[str, Any],
) -> Dict[str, Any]:
    from grantflow.api.job_store_service import _append_job_event_records as _impl

    return _impl(previous, next_payload)


def _record_job_event(job_id: str, event_type: str, **fields: Any) -> None:
    from grantflow.api.job_store_service import _record_job_event as _impl

    _impl(job_id, event_type, **fields)


def _record_ingest_event(
    *,
    donor_id: str,
    namespace: str,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    from grantflow.api.job_store_service import _record_ingest_event as _impl

    _impl(
        donor_id=donor_id,
        namespace=namespace,
        filename=filename,
        content_type=content_type,
        metadata=metadata,
        result=result,
    )


def _list_ingest_events(
    *,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 50,
) -> list[Dict[str, Any]]:
    from grantflow.api.job_store_service import _list_ingest_events as _impl

    return _impl(donor_id=donor_id, tenant_id=tenant_id, limit=limit)


def _ingest_inventory(*, donor_id: Optional[str] = None, tenant_id: Optional[str] = None) -> list[Dict[str, Any]]:
    from grantflow.api.job_store_service import _ingest_inventory as _impl

    return _impl(donor_id=donor_id, tenant_id=tenant_id)


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    from grantflow.api.job_store_service import _set_job as _impl

    _impl(job_id, payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    from grantflow.api.job_store_service import _update_job as _impl

    return _impl(job_id, **patch)


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    from grantflow.api.job_store_service import _get_job as _impl

    return _impl(job_id)


def _list_jobs() -> Dict[str, Dict[str, Any]]:
    from grantflow.api.job_store_service import _list_jobs as _impl

    return _impl()
