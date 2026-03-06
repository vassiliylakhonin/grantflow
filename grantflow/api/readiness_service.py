from __future__ import annotations

from typing import Any


def _build_readiness_payload() -> dict[str, Any]:
    from grantflow.api import app as api_app_module

    vector_ready = api_app_module._vector_store_readiness()
    job_runner_mode = api_app_module._job_runner_mode()
    job_runner_diag = api_app_module.JOB_RUNNER.diagnostics()
    runtime_compatibility_policy_mode = api_app_module._configured_runtime_compatibility_policy_mode()
    runtime_compatibility_status = api_app_module._python_runtime_compatibility_status()
    tenant_authz_status = api_app_module._tenant_authz_configuration_status()
    tenant_authz_policy_mode = api_app_module._configured_tenant_authz_configuration_policy_mode()
    dispatcher_heartbeat_status = (
        job_runner_diag.get("worker_heartbeat") if isinstance(job_runner_diag.get("worker_heartbeat"), dict) else None
    )
    dispatcher_heartbeat_policy_mode = api_app_module._dispatcher_worker_heartbeat_policy_mode()
    alerts: list[dict[str, Any]] = []
    dead_letter_threshold = api_app_module._dead_letter_alert_threshold()
    dead_letter_queue_size_raw = job_runner_diag.get("dead_letter_queue_size")
    try:
        dead_letter_queue_size = int(dead_letter_queue_size_raw)
    except (TypeError, ValueError):
        dead_letter_queue_size = -1
    dead_letter_alert_triggered = (
        api_app_module._uses_redis_queue_runner()
        and dead_letter_threshold > 0
        and dead_letter_queue_size >= 0
        and dead_letter_queue_size >= dead_letter_threshold
    )
    job_runner_ready = True
    if api_app_module._uses_inmemory_queue_runner():
        job_runner_ready = bool(job_runner_diag.get("running"))
    elif api_app_module._uses_redis_queue_runner():
        consumer_enabled = bool(job_runner_diag.get("consumer_enabled", True))
        running_ok = bool(job_runner_diag.get("running")) if consumer_enabled else True
        job_runner_ready = running_ok and bool(job_runner_diag.get("redis_available"))
        if not consumer_enabled and dispatcher_heartbeat_policy_mode != "off":
            heartbeat_healthy = (
                bool(dispatcher_heartbeat_status.get("healthy"))
                if isinstance(dispatcher_heartbeat_status, dict)
                else False
            )
            if not heartbeat_healthy:
                blocking = dispatcher_heartbeat_policy_mode == "strict"
                alerts.append(
                    {
                        "code": "REDIS_DISPATCHER_WORKER_HEARTBEAT_MISSING",
                        "severity": "high" if blocking else "medium",
                        "message": (
                            "Redis dispatcher mode is enabled with local consumer disabled, "
                            "but no healthy external worker heartbeat was detected."
                        ),
                        "blocking": blocking,
                    }
                )
                if blocking:
                    job_runner_ready = False
    if dead_letter_alert_triggered and api_app_module._dead_letter_alert_blocking():
        job_runner_ready = False
    runtime_compatibility_supported = bool(runtime_compatibility_status.get("supported"))
    runtime_compatibility_blocking = runtime_compatibility_policy_mode == "strict" and not runtime_compatibility_supported
    runtime_compatibility_alerts: list[dict[str, Any]] = []
    if not runtime_compatibility_supported:
        runtime_compatibility_alerts.append(
            {
                "code": "PYTHON_RUNTIME_COMPATIBILITY_RISK",
                "severity": "high" if runtime_compatibility_blocking else "medium",
                "message": ("Runtime Python version is outside validated range 3.11-3.13 for current dependency set."),
                "blocking": runtime_compatibility_blocking,
            }
        )
    tenant_authz_valid = bool(tenant_authz_status.get("valid"))
    tenant_authz_blocking = tenant_authz_policy_mode == "strict" and not tenant_authz_valid
    tenant_authz_issues = {
        str(item).strip().lower() for item in (tenant_authz_status.get("issues") or []) if str(item).strip()
    }
    tenant_authz_alerts: list[dict[str, Any]] = []
    if not tenant_authz_valid:
        if "allowlist_empty" in tenant_authz_issues:
            tenant_authz_message = "Tenant authz is enabled but allowlist is empty; configure GRANTFLOW_ALLOWED_TENANTS."
        elif "default_tenant_not_in_allowlist" in tenant_authz_issues:
            tenant_authz_message = (
                "Tenant authz default tenant is not in allowlist; align GRANTFLOW_DEFAULT_TENANT with "
                "GRANTFLOW_ALLOWED_TENANTS."
            )
        else:
            tenant_authz_message = "Tenant authz configuration is invalid."
        tenant_authz_alerts.append(
            {
                "code": "TENANT_AUTHZ_CONFIGURATION_RISK",
                "severity": "high" if tenant_authz_blocking else "medium",
                "message": tenant_authz_message,
                "blocking": tenant_authz_blocking,
            }
        )
    ready = (
        bool(vector_ready.get("ready"))
        and job_runner_ready
        and not runtime_compatibility_blocking
        and not tenant_authz_blocking
    )
    preflight_grounding_thresholds = api_app_module._preflight_grounding_policy_thresholds()
    runtime_grounded_quality_gate_thresholds = api_app_module._runtime_grounded_quality_gate_thresholds()
    mel_grounding_thresholds = api_app_module._mel_grounding_policy_thresholds()
    export_grounding_thresholds = api_app_module._export_grounding_policy_thresholds()
    dead_letter_alert = {
        "enabled": bool(api_app_module._uses_redis_queue_runner() and dead_letter_threshold > 0),
        "threshold": dead_letter_threshold,
        "queue_size": dead_letter_queue_size,
        "triggered": bool(dead_letter_alert_triggered),
        "blocking": bool(api_app_module._dead_letter_alert_blocking()),
    }
    if dead_letter_alert_triggered:
        alerts.append(
            {
                "code": "DEAD_LETTER_QUEUE_THRESHOLD_EXCEEDED",
                "severity": "high" if api_app_module._dead_letter_alert_blocking() else "medium",
                "message": (
                    "Dead-letter queue size exceeded configured alert threshold "
                    f"({dead_letter_queue_size}/{dead_letter_threshold})."
                ),
                "blocking": bool(api_app_module._dead_letter_alert_blocking()),
            }
        )
    return {
        "status": "ready" if ready else "degraded",
        "checks": {
            "vector_store": vector_ready,
            "job_runner": {
                "mode": job_runner_mode,
                "ready": job_runner_ready,
                "queue": job_runner_diag,
                "dispatcher_worker_heartbeat_policy": {
                    "mode": dispatcher_heartbeat_policy_mode,
                },
                "dispatcher_worker_heartbeat": dispatcher_heartbeat_status,
                "dead_letter_alert": dead_letter_alert,
                "alerts": alerts,
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
                "mode": runtime_compatibility_policy_mode,
                "status": runtime_compatibility_status,
                "blocking": runtime_compatibility_blocking,
                "alerts": runtime_compatibility_alerts,
            },
            "tenant_authz_configuration_policy": {
                "mode": tenant_authz_policy_mode,
                "status": tenant_authz_status,
                "blocking": tenant_authz_blocking,
                "alerts": tenant_authz_alerts,
            },
            "configuration_warnings": api_app_module._configuration_warnings(),
        },
    }
