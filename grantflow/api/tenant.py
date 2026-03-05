from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.state_contract import normalize_rag_namespace, normalized_state_copy, state_donor_id

TENANT_HEADER = "x-tenant-id"


def _tenant_authz_enabled() -> bool:
    return os.getenv("GRANTFLOW_TENANT_AUTHZ_ENABLED", "false").strip().lower() == "true"


def _allowed_tenant_tokens() -> set[str]:
    raw = os.getenv("GRANTFLOW_ALLOWED_TENANTS", os.getenv("AIDGRAPH_ALLOWED_TENANTS", ""))
    tokens = [part.strip() for part in str(raw or "").split(",") if part.strip()]
    return {vector_store.normalize_namespace(token) for token in tokens if token}


def _default_tenant_token() -> Optional[str]:
    token = str(os.getenv("GRANTFLOW_DEFAULT_TENANT", os.getenv("AIDGRAPH_DEFAULT_TENANT", "")) or "").strip()
    if not token:
        return None
    return vector_store.normalize_namespace(token)


def _normalize_tenant_candidate(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    return vector_store.normalize_namespace(token)


def _resolve_tenant_id(
    request: Request,
    *,
    explicit_tenant: Optional[str] = None,
    client_metadata: Optional[Dict[str, Any]] = None,
    require_if_enabled: bool = True,
) -> Optional[str]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    candidate = (
        _normalize_tenant_candidate(explicit_tenant)
        or _normalize_tenant_candidate(request.headers.get(TENANT_HEADER))
        or _normalize_tenant_candidate(metadata.get("tenant_id"))
        or _normalize_tenant_candidate(metadata.get("tenant"))
        or _default_tenant_token()
    )
    allowed = _allowed_tenant_tokens()
    enforce = _tenant_authz_enabled()
    if require_if_enabled and enforce and not candidate:
        raise HTTPException(status_code=403, detail="tenant_id is required when tenant authz is enabled")
    if candidate and allowed and candidate not in allowed:
        raise HTTPException(status_code=403, detail="tenant_id is not allowed for this server")
    return candidate


def _tenant_rag_namespace(base_namespace: str, tenant_id: Optional[str]) -> str:
    base = normalize_rag_namespace(base_namespace) or "default"
    tenant = normalize_rag_namespace(tenant_id)
    if not tenant:
        return base
    return normalize_rag_namespace(f"{tenant}/{base}") or f"{tenant}/{base}"


def _tenant_from_namespace(namespace: Any) -> Optional[str]:
    raw = str(namespace or "").strip()
    if "/" not in raw:
        return None
    prefix = raw.split("/", 1)[0]
    return _normalize_tenant_candidate(prefix)


def _job_state_dict(job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state") if isinstance(job.get("state"), dict) else {}
    return dict(normalized_state_copy(state))


def _job_donor_id(job: Dict[str, Any], *, default: str = "") -> str:
    state_dict = _job_state_dict(job)
    donor_id = state_donor_id(state_dict, default="")
    if donor_id:
        return donor_id
    metadata_raw = job.get("client_metadata")
    metadata: Dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    token = str(metadata.get("donor_id") or metadata.get("donor") or "").strip().lower()
    return token or default


def _job_tenant_id(job: Dict[str, Any]) -> Optional[str]:
    if not isinstance(job, dict):
        return None
    metadata_raw = job.get("client_metadata")
    state_raw = job.get("state")
    preflight_raw = job.get("generate_preflight")
    metadata: Dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    state: Dict[str, Any] = state_raw if isinstance(state_raw, dict) else {}
    preflight: Dict[str, Any] = preflight_raw if isinstance(preflight_raw, dict) else {}
    candidates = [
        metadata.get("tenant_id"),
        metadata.get("tenant"),
        state.get("tenant_id"),
        preflight.get("tenant_id"),
        state.get("rag_namespace"),
        state.get("retrieval_namespace"),
        preflight.get("retrieval_namespace"),
    ]
    for candidate in candidates:
        normalized = _normalize_tenant_candidate(candidate)
        if normalized:
            if isinstance(candidate, str) and "/" in candidate:
                from_namespace = _tenant_from_namespace(candidate)
                if from_namespace:
                    return from_namespace
            return normalized
    return None


def _checkpoint_tenant_id(checkpoint: Dict[str, Any]) -> Optional[str]:
    if not isinstance(checkpoint, dict):
        return None
    snapshot_raw = checkpoint.get("state_snapshot")
    snapshot: Dict[str, Any] = snapshot_raw if isinstance(snapshot_raw, dict) else {}
    candidates = [
        checkpoint.get("tenant_id"),
        snapshot.get("tenant_id"),
        snapshot.get("rag_namespace"),
        snapshot.get("retrieval_namespace"),
    ]
    for candidate in candidates:
        normalized = _normalize_tenant_candidate(candidate)
        if normalized:
            if isinstance(candidate, str) and "/" in candidate:
                from_namespace = _tenant_from_namespace(candidate)
                if from_namespace:
                    return from_namespace
            return normalized
    return None


def _ensure_job_tenant_read_access(request: Request, job: Dict[str, Any]) -> Optional[str]:
    if not _tenant_authz_enabled():
        return None
    request_tenant = _resolve_tenant_id(request, require_if_enabled=True)
    job_tenant = _job_tenant_id(job)
    if not request_tenant or not job_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested job")
    if request_tenant != job_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested job")
    return request_tenant


def _ensure_job_tenant_write_access(request: Request, job: Dict[str, Any]) -> Optional[str]:
    return _ensure_job_tenant_read_access(request, job)


def _ensure_checkpoint_tenant_write_access(request: Request, checkpoint: Dict[str, Any]) -> Optional[str]:
    if not _tenant_authz_enabled():
        return None
    request_tenant = _resolve_tenant_id(request, require_if_enabled=True)
    checkpoint_tenant = _checkpoint_tenant_id(checkpoint)
    if not request_tenant or not checkpoint_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested checkpoint")
    if request_tenant != checkpoint_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested checkpoint")
    return request_tenant


def _filter_jobs_by_tenant(jobs: Dict[str, Dict[str, Any]], tenant_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    token = _normalize_tenant_candidate(tenant_id)
    if not token:
        return jobs
    filtered: Dict[str, Dict[str, Any]] = {}
    for job_id, job in jobs.items():
        if _job_tenant_id(job) == token:
            filtered[job_id] = job
    return filtered
