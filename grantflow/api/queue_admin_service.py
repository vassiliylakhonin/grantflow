from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from grantflow.api.runtime_service import _uses_redis_queue_runner


def _job_runner():
    from grantflow.api import app as api_app_module

    return api_app_module.JOB_RUNNER


def _redis_queue_admin_runner(required_methods: tuple[str, ...]) -> Any:
    """Return redis-backed runner with required admin capabilities or raise HTTP 409."""
    if not _uses_redis_queue_runner():
        raise HTTPException(
            status_code=409,
            detail="Dead-letter queue management requires GRANTFLOW_JOB_RUNNER_MODE=redis_queue",
        )
    runner = _job_runner()
    for method_name in required_methods:
        if not callable(getattr(runner, method_name, None)):
            raise HTTPException(
                status_code=409, detail="Redis queue admin operations are unavailable in current runner"
            )
    return runner
