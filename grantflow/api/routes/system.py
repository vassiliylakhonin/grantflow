from __future__ import annotations

from fastapi import HTTPException

from grantflow.api import app as api_app_module
from grantflow.api.readiness_service import _build_readiness_payload
from grantflow.api.routers import system_router


@system_router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": api_app_module.__version__,
        "diagnostics": api_app_module._health_diagnostics(),
    }


@system_router.get("/ready")
def readiness_check():
    payload = _build_readiness_payload()
    if str(payload.get("status") or "").strip().lower() != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload
