from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Request

from grantflow.api.schemas import HITLPendingListPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_hitl_manager: Any = None
_hitl_status_pending: Any = None
_public_checkpoint_payload: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def configure_hitl_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    hitl_manager: Any,
    hitl_status_pending: Any,
    public_checkpoint_payload: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    global _require_api_key_if_configured
    global _hitl_manager
    global _hitl_status_pending
    global _public_checkpoint_payload

    _require_api_key_if_configured = require_api_key_if_configured
    _hitl_manager = hitl_manager
    _hitl_status_pending = hitl_status_pending
    _public_checkpoint_payload = public_checkpoint_payload


@router.post("/hitl/approve")
def approve_checkpoint(req: Any, request: Request):
    _require_api_key_if_configured(request)
    checkpoint = _hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if req.approved:
        _hitl_manager.approve(req.checkpoint_id, req.feedback)
        return {"status": "approved", "checkpoint_id": req.checkpoint_id}

    _hitl_manager.reject(req.checkpoint_id, req.feedback or "Rejected")
    return {"status": "rejected", "checkpoint_id": req.checkpoint_id}


@router.get("/hitl/pending", response_model=HITLPendingListPublicResponse, response_model_exclude_none=True)
def list_pending_hitl(request: Request, donor_id: Optional[str] = None):
    _require_api_key_if_configured(request, for_read=True)
    pending = _hitl_manager.list_pending(donor_id)
    return {
        "pending_count": len(pending),
        "checkpoints": [_public_checkpoint_payload(cp) for cp in pending],
    }
