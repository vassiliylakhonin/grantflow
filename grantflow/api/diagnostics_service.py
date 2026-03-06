from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from grantflow.api.constants import GROUNDING_POLICY_MODES
from grantflow.api.security import api_key_configured, read_auth_required
from grantflow.api.tenant import _allowed_tenant_tokens, _default_tenant_token, _tenant_authz_enabled
from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store


def _normalize_grounding_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in GROUNDING_POLICY_MODES:
        return "warn"
    return mode


def _dead_letter_alert_threshold() -> int:
    raw = getattr(config.job_runner, "dead_letter_alert_threshold", 0)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _dead_letter_alert_blocking() -> bool:
    return bool(getattr(config.job_runner, "dead_letter_alert_blocking", False))


def _dispatcher_worker_heartbeat_policy_mode() -> str:
    token = str(getattr(config.job_runner, "redis_worker_heartbeat_policy_mode", "strict") or "strict").strip().lower()
    if token not in GROUNDING_POLICY_MODES:
        return "strict"
    return token


def _configured_tenant_authz_configuration_policy_mode() -> str:
    raw_mode = os.getenv(
        "GRANTFLOW_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE",
        os.getenv("AIDGRAPH_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE", "warn"),
    )
    return _normalize_grounding_policy_mode(raw_mode)


def _tenant_authz_configuration_status() -> dict[str, Any]:
    enabled = _tenant_authz_enabled()
    allowed_tenants = _allowed_tenant_tokens()
    default_tenant = _default_tenant_token()
    issues: list[str] = []
    if enabled and len(allowed_tenants) == 0:
        issues.append("allowlist_empty")
    if enabled and default_tenant and allowed_tenants and default_tenant not in allowed_tenants:
        issues.append("default_tenant_not_in_allowlist")
    valid = len(issues) == 0
    return {
        "enabled": enabled,
        "allowed_tenant_count": len(allowed_tenants),
        "default_tenant": default_tenant,
        "issues": issues,
        "valid": valid,
        "policy_mode": _configured_tenant_authz_configuration_policy_mode(),
    }


def _configured_runtime_compatibility_policy_mode() -> str:
    policy_mode = getattr(config.graph, "runtime_compatibility_policy_mode", None)
    if str(policy_mode or "").strip():
        return _normalize_grounding_policy_mode(policy_mode)
    return "warn"


def _python_runtime_compatibility_status() -> Dict[str, Any]:
    from grantflow.api import app as api_app_module

    runtime_sys = getattr(api_app_module, "sys", sys)
    version_info = getattr(runtime_sys, "version_info", sys.version_info)
    python_major = int(version_info[0])
    python_minor = int(version_info[1])
    supported = python_major == 3 and 11 <= python_minor <= 13
    return {
        "python_version": f"{python_major}.{python_minor}",
        "supported": supported,
        "supported_range": "3.11-3.13",
    }


def _configuration_warnings() -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    from grantflow.api import app as api_app_module

    runtime_sys = getattr(api_app_module, "sys", sys)
    version_info = getattr(runtime_sys, "version_info", sys.version_info)
    python_major = int(version_info[0])
    python_minor = int(version_info[1])
    if python_major == 3 and python_minor >= 14:
        warnings.append(
            {
                "code": "PYTHON_VERSION_MAY_BE_UNSUPPORTED_BY_CHROMADB",
                "severity": "medium",
                "message": (
                    "Python >= 3.14 may be unstable with current Chroma dependency chain. "
                    "Use Python 3.11-3.13 for production reliability."
                ),
                "details": {
                    "python_version": f"{python_major}.{python_minor}",
                    "recommended": "3.11-3.13",
                },
            }
        )

    chroma_host = str(getattr(vector_store, "_chroma_host", "") or "").strip()
    chroma_port_raw: object = getattr(vector_store, "_chroma_port", None)
    chroma_port: Optional[int]
    if isinstance(chroma_port_raw, int):
        chroma_port = chroma_port_raw
    elif isinstance(chroma_port_raw, str):
        try:
            chroma_port = int(chroma_port_raw.strip())
        except ValueError:
            chroma_port = None
    else:
        chroma_port = None

    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if chroma_host.lower() in local_hosts and chroma_port == 8000:
        warnings.append(
            {
                "code": "CHROMA_PORT_MAY_CONFLICT_WITH_API_DEFAULT",
                "severity": "medium",
                "message": (
                    "CHROMA_PORT=8000 with CHROMA_HOST set may conflict with uvicorn default API port 8000. "
                    "Use CHROMA_PORT=8001 or run API on a different port."
                ),
                "details": {"chroma_host": chroma_host, "chroma_port": chroma_port},
            }
        )
    tenant_authz_status = _tenant_authz_configuration_status()
    tenant_authz_enabled = bool(tenant_authz_status.get("enabled"))
    allowed_tenant_count = int(tenant_authz_status.get("allowed_tenant_count") or 0)
    default_tenant = str(tenant_authz_status.get("default_tenant") or "").strip() or None
    issues = {str(item).strip().lower() for item in (tenant_authz_status.get("issues") or []) if str(item).strip()}
    if tenant_authz_enabled and "allowlist_empty" in issues:
        warnings.append(
            {
                "code": "TENANT_AUTHZ_ENABLED_WITHOUT_ALLOWLIST",
                "severity": "high",
                "message": (
                    "Tenant authz is enabled but GRANTFLOW_ALLOWED_TENANTS is empty. "
                    "Set explicit tenant allowlist to avoid unintended tenant access scope."
                ),
                "details": {"tenant_authz_enabled": True, "allowed_tenant_count": 0},
            }
        )
    if tenant_authz_enabled and "default_tenant_not_in_allowlist" in issues:
        warnings.append(
            {
                "code": "TENANT_DEFAULT_NOT_IN_ALLOWLIST",
                "severity": "medium",
                "message": (
                    "Tenant authz is enabled and GRANTFLOW_DEFAULT_TENANT is not included in allowlist. "
                    "Use an allowed default tenant to avoid implicit 403 failures."
                ),
                "details": {
                    "tenant_authz_enabled": True,
                    "default_tenant": default_tenant,
                    "allowed_tenant_count": allowed_tenant_count,
                },
            }
        )
    return warnings


def _health_diagnostics() -> dict[str, Any]:
    from grantflow.api import app as api_app_module

    job_store_mode = api_app_module._job_store_mode()
    hitl_store_mode = api_app_module._hitl_store_mode()
    ingest_store_mode = api_app_module._ingest_store_mode()
    sqlite_path = getattr(api_app_module.JOB_STORE, "db_path", None) or (
        getattr(api_app_module.hitl_manager, "_sqlite_path", None) if hitl_store_mode == "sqlite" else None
    )
    if not sqlite_path and ingest_store_mode == "sqlite":
        sqlite_path = getattr(api_app_module.INGEST_AUDIT_STORE, "db_path", None)

    vector_backend = "chroma" if getattr(vector_store, "client", None) is not None else "memory"
    preflight_grounding_thresholds = api_app_module._preflight_grounding_policy_thresholds()
    runtime_grounded_quality_gate_thresholds = api_app_module._runtime_grounded_quality_gate_thresholds()
    mel_grounding_thresholds = api_app_module._mel_grounding_policy_thresholds()
    export_grounding_thresholds = api_app_module._export_grounding_policy_thresholds()
    runtime_compatibility_status = _python_runtime_compatibility_status()
    tenant_authz_status = _tenant_authz_configuration_status()
    job_runner_diag = api_app_module.JOB_RUNNER.diagnostics()
    dispatcher_heartbeat_status = (
        job_runner_diag.get("worker_heartbeat") if isinstance(job_runner_diag.get("worker_heartbeat"), dict) else None
    )
    diagnostics: dict[str, Any] = {
        "job_store": {"mode": job_store_mode},
        "hitl_store": {"mode": hitl_store_mode},
        "ingest_store": {"mode": ingest_store_mode},
        "job_runner": {
            "mode": api_app_module._job_runner_mode(),
            "queue_enabled": api_app_module._uses_queue_runner(),
            "queue": job_runner_diag,
            "dispatcher_worker_heartbeat_policy": {
                "mode": _dispatcher_worker_heartbeat_policy_mode(),
            },
            "dispatcher_worker_heartbeat": dispatcher_heartbeat_status,
        },
        "auth": {
            "api_key_configured": bool(api_key_configured()),
            "read_auth_required": bool(read_auth_required()),
            "tenant_authz_enabled": bool(tenant_authz_status.get("enabled")),
            "allowed_tenant_count": int(tenant_authz_status.get("allowed_tenant_count") or 0),
        },
        "tenant_authz_configuration_policy": {
            "mode": _configured_tenant_authz_configuration_policy_mode(),
            "status": tenant_authz_status,
        },
        "vector_store": {
            "backend": vector_backend,
            "collection_prefix": getattr(vector_store, "prefix", "grantflow"),
        },
        "preflight_grounding_policy": {
            "mode": api_app_module._configured_preflight_grounding_policy_mode(),
            "thresholds": preflight_grounding_thresholds,
        },
        "runtime_grounded_quality_gate": {
            "mode": api_app_module._configured_runtime_grounded_quality_gate_mode(),
            "thresholds": runtime_grounded_quality_gate_thresholds,
        },
        "mel_grounding_policy": {
            "mode": api_app_module._configured_mel_grounding_policy_mode(),
            "thresholds": mel_grounding_thresholds,
        },
        "export_grounding_policy": {
            "mode": api_app_module._configured_export_grounding_policy_mode(),
            "thresholds": export_grounding_thresholds,
        },
        "export_contract_policy": {
            "mode": api_app_module._configured_export_contract_policy_mode(),
        },
        "export_runtime_grounded_gate_policy": {
            "require_pass": api_app_module._configured_export_require_grounded_gate_pass(),
        },
        "runtime_compatibility_policy": {
            "mode": _configured_runtime_compatibility_policy_mode(),
            "status": runtime_compatibility_status,
        },
        "configuration_warnings": _configuration_warnings(),
    }
    if sqlite_path and (job_store_mode == "sqlite" or hitl_store_mode == "sqlite" or ingest_store_mode == "sqlite"):
        diagnostics["sqlite"] = {"path": str(sqlite_path)}
    client_init_error = getattr(vector_store, "_client_init_error", None)
    if client_init_error:
        diagnostics["vector_store"]["client_init_error"] = str(client_init_error)
    return diagnostics


def _vector_store_readiness() -> dict[str, Any]:
    client = getattr(vector_store, "client", None)
    backend = "chroma" if client is not None else "memory"

    if backend == "memory":
        return {"ready": True, "backend": "memory", "reason": "in-memory fallback backend active"}

    try:
        heartbeat = getattr(client, "heartbeat", None)
        if callable(heartbeat):
            hb_value = heartbeat()
            return {"ready": True, "backend": "chroma", "heartbeat": str(hb_value)}

        list_collections = getattr(client, "list_collections", None)
        if callable(list_collections):
            list_collections()
        return {"ready": True, "backend": "chroma"}
    except Exception as exc:
        return {"ready": False, "backend": "chroma", "error": str(exc)}
