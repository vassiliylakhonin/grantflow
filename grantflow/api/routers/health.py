from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException

router = APIRouter()

_health_diagnostics_fn: Callable[[], dict[str, Any]] | None = None
_vector_store_readiness_fn: Callable[[], dict[str, Any]] | None = None
_preflight_mode_fn: Callable[[], str] | None = None
_preflight_thresholds_fn: Callable[[], dict[str, Any]] | None = None
_mel_mode_fn: Callable[[], str] | None = None
_mel_thresholds_fn: Callable[[], dict[str, Any]] | None = None
_export_mode_fn: Callable[[], str] | None = None
_export_thresholds_fn: Callable[[], dict[str, Any]] | None = None
_version_value: str = "unknown"


def configure_health_router(
    *,
    health_diagnostics_fn: Callable[[], dict[str, Any]],
    vector_store_readiness_fn: Callable[[], dict[str, Any]],
    preflight_mode_fn: Callable[[], str],
    preflight_thresholds_fn: Callable[[], dict[str, Any]],
    mel_mode_fn: Callable[[], str],
    mel_thresholds_fn: Callable[[], dict[str, Any]],
    export_mode_fn: Callable[[], str],
    export_thresholds_fn: Callable[[], dict[str, Any]],
    version_value: str,
) -> None:
    global _health_diagnostics_fn
    global _vector_store_readiness_fn
    global _preflight_mode_fn
    global _preflight_thresholds_fn
    global _mel_mode_fn
    global _mel_thresholds_fn
    global _export_mode_fn
    global _export_thresholds_fn
    global _version_value

    _health_diagnostics_fn = health_diagnostics_fn
    _vector_store_readiness_fn = vector_store_readiness_fn
    _preflight_mode_fn = preflight_mode_fn
    _preflight_thresholds_fn = preflight_thresholds_fn
    _mel_mode_fn = mel_mode_fn
    _mel_thresholds_fn = mel_thresholds_fn
    _export_mode_fn = export_mode_fn
    _export_thresholds_fn = export_thresholds_fn
    _version_value = version_value


@router.get("/health")
def health_check():
    diagnostics = _health_diagnostics_fn() if _health_diagnostics_fn else {}
    return {"status": "healthy", "version": _version_value, "diagnostics": diagnostics}


@router.get("/ready")
def readiness_check():
    vector_ready = _vector_store_readiness_fn() if _vector_store_readiness_fn else {"ready": False, "error": "router_not_configured"}
    ready = bool(vector_ready.get("ready"))

    payload = {
        "status": "ready" if ready else "degraded",
        "checks": {
            "vector_store": vector_ready,
            "preflight_grounding_policy": {
                "mode": _preflight_mode_fn() if _preflight_mode_fn else "unknown",
                "thresholds": _preflight_thresholds_fn() if _preflight_thresholds_fn else {},
            },
            "mel_grounding_policy": {
                "mode": _mel_mode_fn() if _mel_mode_fn else "unknown",
                "thresholds": _mel_thresholds_fn() if _mel_thresholds_fn else {},
            },
            "export_grounding_policy": {
                "mode": _export_mode_fn() if _export_mode_fn else "unknown",
                "thresholds": _export_thresholds_fn() if _export_thresholds_fn else {},
            },
        },
    }
    if not ready:
        raise HTTPException(status_code=503, detail=payload)
    return payload
