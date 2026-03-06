from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from grantflow.api.diagnostics_service import (
    _configured_runtime_compatibility_policy_mode,
    _tenant_authz_configuration_status,
)
from grantflow.api.security import api_key_configured
from grantflow.core.config import config
from grantflow.core.job_runner import InMemoryJobRunner, RedisJobRunner

JOB_RUNNER_MODES = {"background_tasks", "inmemory_queue", "redis_queue"}
PRODUCTION_ENV_TOKENS = {"prod", "production"}


def _app_module():
    from grantflow.api import app as api_app_module

    return api_app_module


def _job_store():
    return _app_module().JOB_STORE


def _hitl_manager():
    return _app_module().hitl_manager


def _ingest_audit_store():
    return _app_module().INGEST_AUDIT_STORE


def _job_runner():
    return _app_module().JOB_RUNNER


def _job_runner_mode() -> str:
    raw_mode = str(getattr(config.job_runner, "mode", "background_tasks") or "background_tasks").strip().lower()
    if raw_mode not in JOB_RUNNER_MODES:
        return "background_tasks"
    return raw_mode


def _uses_inmemory_queue_runner() -> bool:
    return _job_runner_mode() == "inmemory_queue"


def _uses_redis_queue_runner() -> bool:
    return _job_runner_mode() == "redis_queue"


def _uses_queue_runner() -> bool:
    return _uses_inmemory_queue_runner() or _uses_redis_queue_runner()


def _build_job_runner():
    worker_count = int(getattr(config.job_runner, "worker_count", 2) or 2)
    queue_maxsize = int(getattr(config.job_runner, "queue_maxsize", 200) or 200)
    consumer_enabled = bool(getattr(config.job_runner, "consumer_enabled", True))
    if _uses_redis_queue_runner():
        return RedisJobRunner(
            worker_count=worker_count,
            queue_maxsize=queue_maxsize,
            redis_url=str(getattr(config.job_runner, "redis_url", "redis://127.0.0.1:6379/0") or ""),
            queue_name=str(getattr(config.job_runner, "redis_queue_name", "grantflow:jobs") or ""),
            pop_timeout_seconds=float(getattr(config.job_runner, "redis_pop_timeout_seconds", 1.0) or 1.0),
            max_attempts=int(getattr(config.job_runner, "redis_max_attempts", 3) or 3),
            dead_letter_queue_name=str(getattr(config.job_runner, "redis_dead_letter_queue_name", "") or ""),
            worker_heartbeat_key=str(getattr(config.job_runner, "redis_worker_heartbeat_key", "") or ""),
            worker_heartbeat_ttl_seconds=float(
                getattr(config.job_runner, "redis_worker_heartbeat_ttl_seconds", 45.0) or 45.0
            ),
            consumer_enabled=consumer_enabled,
        )
    return InMemoryJobRunner(worker_count=worker_count, queue_maxsize=queue_maxsize)


def _job_store_mode() -> str:
    return "sqlite" if getattr(_job_store(), "db_path", None) else "inmem"


def _hitl_store_mode() -> str:
    return "sqlite" if bool(getattr(_hitl_manager(), "_use_sqlite", False)) else "inmem"


def _ingest_store_mode() -> str:
    return "sqlite" if getattr(_ingest_audit_store(), "db_path", None) else "inmem"


def _validate_store_backend_alignment() -> None:
    job_store_mode = _job_store_mode()
    hitl_store_mode = _hitl_store_mode()
    if job_store_mode == hitl_store_mode:
        return
    raise RuntimeError(
        "Store backend mismatch: "
        f"JOB_STORE={job_store_mode} while HITL_STORE={hitl_store_mode}. "
        "Use matching backends for GRANTFLOW_JOB_STORE and GRANTFLOW_HITL_STORE."
    )


def _validate_tenant_authz_configuration() -> None:
    status = _tenant_authz_configuration_status()
    policy_mode = str(status.get("policy_mode") or "warn")
    enabled = bool(status.get("enabled"))
    allowed_tenant_count = int(status.get("allowed_tenant_count") or 0)
    default_tenant = str(status.get("default_tenant") or "").strip()
    issues = {str(item).strip().lower() for item in (status.get("issues") or []) if str(item).strip()}
    valid = bool(status.get("valid"))
    if policy_mode != "strict":
        return
    if valid:
        return
    if enabled and "allowlist_empty" in issues:
        raise RuntimeError(
            "Tenant authz misconfiguration: GRANTFLOW_TENANT_AUTHZ_ENABLED=true but tenant allowlist is empty. "
            "Set GRANTFLOW_ALLOWED_TENANTS or disable strict policy "
            "(GRANTFLOW_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE=warn|off)."
        )
    if enabled and "default_tenant_not_in_allowlist" in issues:
        raise RuntimeError(
            "Tenant authz misconfiguration: GRANTFLOW_DEFAULT_TENANT is not included in GRANTFLOW_ALLOWED_TENANTS "
            f"(default={default_tenant}, allowed_count={allowed_tenant_count}). "
            "Set a matching default tenant or disable strict policy "
            "(GRANTFLOW_TENANT_AUTHZ_CONFIGURATION_POLICY_MODE=warn|off)."
        )


def _validate_runtime_compatibility_configuration() -> None:
    from grantflow.api.diagnostics_service import _python_runtime_compatibility_status

    status = _python_runtime_compatibility_status()
    policy_mode = _configured_runtime_compatibility_policy_mode()
    supported = bool(status.get("supported"))
    if policy_mode != "strict":
        return
    if supported:
        return
    raise RuntimeError(
        "Runtime compatibility misconfiguration: Python "
        f"{status.get('python_version')} is outside validated range {status.get('supported_range')}. "
        "Use Python 3.11-3.13 or set GRANTFLOW_RUNTIME_COMPATIBILITY_POLICY_MODE=warn|off."
    )


def _deployment_environment() -> str:
    return str(os.getenv("GRANTFLOW_ENV", "dev") or "dev").strip().lower()


def _is_production_environment() -> bool:
    return _deployment_environment() in PRODUCTION_ENV_TOKENS


def _require_api_key_on_startup() -> bool:
    """Resolve whether startup must fail when API key auth is not configured."""
    explicit = os.getenv("GRANTFLOW_REQUIRE_API_KEY_ON_STARTUP")
    if explicit is None or not str(explicit).strip():
        return _is_production_environment()
    return str(explicit).strip().lower() == "true"


def _require_persistent_stores_on_startup() -> bool:
    """Resolve whether startup must fail when non-persistent stores are configured."""
    explicit = os.getenv("GRANTFLOW_REQUIRE_PERSISTENT_STORES_ON_STARTUP")
    if explicit is None or not str(explicit).strip():
        return _is_production_environment()
    return str(explicit).strip().lower() == "true"


def _validate_api_key_startup_security() -> None:
    """Enforce API auth startup guardrails for secure-by-default deployments."""
    if not _require_api_key_on_startup():
        return
    if api_key_configured():
        return
    raise RuntimeError(
        "Security defaults violation: API key auth is required at startup but GRANTFLOW_API_KEY is not set. "
        "Set GRANTFLOW_API_KEY or disable this guard with GRANTFLOW_REQUIRE_API_KEY_ON_STARTUP=false."
    )


def _validate_persistent_store_startup_security() -> None:
    """Enforce persistent-state startup guardrails in production-oriented environments."""
    if not _require_persistent_stores_on_startup():
        return
    store_modes = {
        "GRANTFLOW_JOB_STORE": _job_store_mode(),
        "GRANTFLOW_HITL_STORE": _hitl_store_mode(),
        "GRANTFLOW_INGEST_STORE": _ingest_store_mode(),
    }
    non_persistent = {name: mode for name, mode in store_modes.items() if mode != "sqlite"}
    if not non_persistent:
        return
    details = ", ".join(f"{name}={mode}" for name, mode in non_persistent.items())
    raise RuntimeError(
        "Security defaults violation: persistent stores are required at startup but non-sqlite backends are active "
        f"({details}). Set GRANTFLOW_JOB_STORE=sqlite, GRANTFLOW_HITL_STORE=sqlite, "
        "GRANTFLOW_INGEST_STORE=sqlite (and GRANTFLOW_SQLITE_PATH), or disable this guard with "
        "GRANTFLOW_REQUIRE_PERSISTENT_STORES_ON_STARTUP=false."
    )


@asynccontextmanager
async def _app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    _validate_store_backend_alignment()
    _validate_tenant_authz_configuration()
    _validate_runtime_compatibility_configuration()
    _validate_api_key_startup_security()
    _validate_persistent_store_startup_security()
    if _uses_queue_runner():
        _job_runner().start()
    try:
        yield
    finally:
        if _uses_queue_runner():
            _job_runner().stop()
