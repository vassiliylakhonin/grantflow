from __future__ import annotations

from fastapi import HTTPException, Query, Request

from grantflow.api.diagnostics_service import _dispatcher_worker_heartbeat_policy_mode
from grantflow.api.queue_admin_service import _redis_queue_admin_runner
from grantflow.api.routers import queue_router
from grantflow.api.schemas import (
    DeadLetterQueueListPublicResponse,
    DeadLetterQueueMutationPublicResponse,
    QueueWorkerHeartbeatPublicResponse,
)
from grantflow.api.security import require_api_key_if_configured


@queue_router.get(
    "/queue/worker-heartbeat",
    response_model=QueueWorkerHeartbeatPublicResponse,
    response_model_exclude_none=True,
)
def get_queue_worker_heartbeat(
    request: Request,
):
    require_api_key_if_configured(request, for_read=True)
    runner = _redis_queue_admin_runner(("worker_heartbeat_status",))
    status_payload = runner.worker_heartbeat_status()
    if not isinstance(status_payload, dict):
        status_payload = {"present": False, "healthy": False, "error": "invalid_worker_heartbeat_payload"}
    return {
        "mode": "redis_queue",
        "policy": {"mode": _dispatcher_worker_heartbeat_policy_mode()},
        "consumer_enabled": bool(getattr(runner, "consumer_enabled", True)),
        "heartbeat": status_payload,
    }


@queue_router.get(
    "/queue/dead-letter",
    response_model=DeadLetterQueueListPublicResponse,
    response_model_exclude_none=True,
)
def get_dead_letter_queue(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
):
    require_api_key_if_configured(request, for_read=True)
    runner = _redis_queue_admin_runner(("list_dead_letters",))
    try:
        return runner.list_dead_letters(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@queue_router.post(
    "/queue/dead-letter/requeue",
    response_model=DeadLetterQueueMutationPublicResponse,
    response_model_exclude_none=True,
)
def requeue_dead_letter_queue(
    request: Request,
    limit: int = Query(default=10, ge=1, le=500),
    reset_attempts: bool = Query(default=True),
):
    require_api_key_if_configured(request)
    runner = _redis_queue_admin_runner(("requeue_dead_letters",))
    try:
        return runner.requeue_dead_letters(limit=limit, reset_attempts=reset_attempts)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@queue_router.delete(
    "/queue/dead-letter",
    response_model=DeadLetterQueueMutationPublicResponse,
    response_model_exclude_none=True,
)
def purge_dead_letter_queue(
    request: Request,
    limit: int = Query(default=100, ge=1, le=5000),
):
    require_api_key_if_configured(request)
    runner = _redis_queue_admin_runner(("purge_dead_letters",))
    try:
        return runner.purge_dead_letters(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
