from __future__ import annotations

from enum import Enum
from typing import Any, Dict


def sanitize_for_public_response(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): sanitize_for_public_response(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_public_response(item) for item in value]
    return str(value)


def public_state_snapshot(state: Any) -> Any:
    if not isinstance(state, dict):
        return sanitize_for_public_response(state)

    redacted_state = {}
    for key, value in state.items():
        if key in {"strategy", "donor_strategy"}:
            continue
        redacted_state[str(key)] = sanitize_for_public_response(value)
    return redacted_state


def public_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    public_job: Dict[str, Any] = {}
    for key, value in job.items():
        if key in {"webhook_url", "webhook_secret"}:
            continue
        if key == "state":
            public_job[key] = public_state_snapshot(value)
            continue
        public_job[str(key)] = sanitize_for_public_response(value)
    public_job["webhook_configured"] = bool(job.get("webhook_url"))
    return public_job


def public_job_citations_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    citations = []
    if isinstance(state, dict):
        raw = state.get("citations")
        if isinstance(raw, list):
            citations = [sanitize_for_public_response(item) for item in raw if isinstance(item, dict)]
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "citation_count": len(citations),
        "citations": citations,
    }


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
