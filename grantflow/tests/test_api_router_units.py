from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from grantflow.api.routers.comments_write import configure_comments_write_router, router as comments_router
from grantflow.api.routers.critic_write import configure_critic_write_router, router as critic_router
from grantflow.api.routers.health import configure_health_router, router as health_router
from grantflow.api.routers.ingest import configure_ingest_router, router as ingest_router
from grantflow.api.routers.review_workflow_read import (
    configure_review_workflow_read_router,
    router as review_router,
)
from grantflow.api.routers.status_read import configure_status_read_router, router as status_router


def test_health_router_ready_degraded_and_healthy_payloads() -> None:
    configure_health_router(
        health_diagnostics_fn=lambda: {"db": "ok"},
        vector_store_readiness_fn=lambda: {"ready": False, "backend": "chroma", "error": "offline"},
        preflight_mode_fn=lambda: "warn",
        preflight_thresholds_fn=lambda: {"min_uploads": 3},
        mel_mode_fn=lambda: "strict",
        mel_thresholds_fn=lambda: {"min_mel_citations": 2},
        export_mode_fn=lambda: "off",
        export_thresholds_fn=lambda: {"min_architect_citations": 3},
        version_value="9.9.9",
    )

    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "9.9.9"
    assert health.json()["diagnostics"] == {"db": "ok"}

    ready = client.get("/ready")
    assert ready.status_code == 503
    assert ready.json()["detail"]["status"] == "degraded"


def test_ingest_router_upload_and_inventory_export() -> None:
    calls: dict[str, Any] = {}

    def _export_response(**kwargs: Any) -> dict[str, Any]:
        calls["export"] = kwargs
        return {"ok": True}

    configure_ingest_router(
        require_api_key_if_configured=lambda *args, **kwargs: None,
        resolve_tenant_id=lambda *args, **kwargs: "tenant-a",
        list_ingest_events=lambda **kwargs: [{"event_id": "e1"}],
        ingest_inventory_fn=lambda **kwargs: [{"doc_family": "donor_policy", "count": 1}],
        portfolio_export_response=_export_response,
        public_ingest_recent_payload=lambda rows, donor_id=None: {"rows": rows, "donor_id": donor_id},
        public_ingest_inventory_payload=lambda rows, donor_id=None: {"rows": rows, "donor_id": donor_id},
        public_ingest_inventory_csv_text=lambda payload: "csv",
        donor_get_strategy=lambda donor: type("S", (), {"get_rag_collection": lambda self: f"{donor}_rag"})(),
        tenant_rag_namespace=lambda base, tenant: f"{tenant}/{base}",
        vector_store_normalize_namespace=lambda ns: ns.lower(),
        ingest_pdf_to_namespace_fn=lambda path, namespace, metadata: {
            "chunks": 5,
            "namespace": namespace,
            "tenant": metadata.get("tenant_id"),
        },
        record_ingest_event=lambda **kwargs: calls.setdefault("event", kwargs),
    )

    app = FastAPI()
    app.include_router(ingest_router)
    client = TestClient(app)

    upload = client.post(
        "/ingest",
        data={"donor_id": "usaid", "metadata_json": '{"doc_family":"donor_policy"}'},
        files={"file": ("policy.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["status"] == "ingested"
    assert body["tenant_id"] == "tenant-a"
    assert body["namespace"] == "tenant-a/usaid_rag"

    export = client.get("/ingest/inventory/export", params={"format": "json", "gzip": "true"})
    assert export.status_code == 200
    assert calls["export"]["export_format"] == "json"
    assert calls["export"]["gzip_enabled"] is True


def test_status_router_export_payload_uses_donor_fallback() -> None:
    captured: dict[str, Any] = {}

    configure_status_read_router(
        require_api_key_if_configured=lambda *args, **kwargs: None,
        get_job=lambda job_id: {"state": {}, "client_metadata": {"donor_id": "eu"}},
        normalize_critic_fatal_flaws_for_job=lambda job_id: None,
        ingest_inventory=lambda **kwargs: captured.setdefault("inventory", kwargs) or [],
        public_job_payload=lambda job: {"status": "ok"},
        public_job_citations_payload=lambda job_id, job: {"items": []},
        public_job_export_payload=lambda job_id, job, ingest_inventory_rows=None: {
            "job_id": job_id,
            "status": "accepted",
            "payload": {"inventory_rows": ingest_inventory_rows},
        },
        public_job_versions_payload=lambda *args, **kwargs: {"versions": []},
        public_job_diff_payload=lambda *args, **kwargs: {"diff": []},
        public_job_events_payload=lambda *args, **kwargs: {"events": []},
        public_job_metrics_payload=lambda *args, **kwargs: {"metrics": {}},
        public_job_quality_payload=lambda *args, **kwargs: {"quality": {}},
        public_job_critic_payload=lambda *args, **kwargs: {"critic": {}},
    )

    app = FastAPI()
    app.include_router(status_router)
    client = TestClient(app)

    resp = client.get("/status/job-1/export-payload")
    assert resp.status_code == 200
    assert captured["inventory"]["donor_id"] == "eu"


def test_review_router_rejects_unsupported_workflow_state() -> None:
    configure_review_workflow_read_router(
        require_api_key_if_configured=lambda *args, **kwargs: None,
        normalize_critic_fatal_flaws_for_job=lambda job_id: {"state": {}},
        get_job=lambda job_id: {"state": {}},
        normalize_review_comments_for_job=lambda job_id: None,
        public_job_review_workflow_payload=lambda *args, **kwargs: {"items": []},
        public_job_review_workflow_sla_payload=lambda *args, **kwargs: {"sla": []},
        review_workflow_sla_profile_payload=lambda *args, **kwargs: {"source": "default"},
        portfolio_export_response=lambda **kwargs: {"ok": True},
        public_job_review_workflow_csv_text=lambda payload: "csv",
        review_workflow_overdue_default_hours=72,
        review_workflow_state_filter_values={"open", "resolved"},
    )

    app = FastAPI()
    app.include_router(review_router)
    client = TestClient(app)

    bad = client.get("/status/job-1/review/workflow", params={"workflow_state": "inbox"})
    assert bad.status_code == 400


def test_comments_router_validates_linked_finding_and_calls_append() -> None:
    calls: dict[str, Any] = {}

    configure_comments_write_router(
        require_api_key_if_configured=lambda *args, **kwargs: None,
        get_job=lambda job_id: {"state": {}},
        job_draft_version_exists_for_section=lambda job, section, version_id: True,
        normalize_critic_fatal_flaws_for_job=lambda job_id: {"state": {}},
        find_critic_fatal_flaw=lambda job, finding_id: {"finding_id": "f-1", "severity": "high", "section": "toc"},
        finding_primary_id=lambda finding: finding.get("finding_id"),
        append_review_comment=lambda *args, **kwargs: (
            calls.__setitem__("append", kwargs)
            or {
                "comment_id": "c-1",
                "ts": "2026-03-13T00:00:00Z",
                "section": kwargs["section"],
                "message": kwargs["message"],
                "status": "open",
            }
        ),
        set_review_comment_status=lambda *args, **kwargs: {
            "comment_id": "c-1",
            "ts": "2026-03-13T00:00:00Z",
            "section": "toc",
            "message": "stub",
            "status": kwargs["next_status"],
        },
        review_comment_sections={"toc", "logframe", "general"},
    )

    app = FastAPI()
    app.include_router(comments_router)
    client = TestClient(app)

    resp = client.post(
        "/status/job-1/comments",
        json={"section": "toc", "message": "Fix this", "linked_finding_id": "legacy-id"},
    )
    assert resp.status_code == 200
    assert calls["append"]["linked_finding_id"] == "f-1"
    assert calls["append"]["linked_finding_severity"] == "high"


def test_critic_router_bulk_status_accepts_json_payload() -> None:
    calls: dict[str, Any] = {}

    def _bulk(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls["bulk"] = kwargs
        return {
            "job_id": args[0],
            "status": "running",
            "requested_status": kwargs["next_status"],
            "actor": kwargs["actor"],
            "matched_count": 1,
            "changed_count": 1,
            "unchanged_count": 0,
            "not_found_finding_ids": [],
            "filters": {},
            "updated_findings": [],
        }

    configure_critic_write_router(
        require_api_key_if_configured=lambda *args, **kwargs: None,
        set_critic_fatal_flaw_status=lambda *args, **kwargs: {"id": "f-1", "status": kwargs["next_status"]},
        set_critic_fatal_flaws_status_bulk=_bulk,
        finding_actor_from_request=lambda request: "reviewer@example.com",
    )

    app = FastAPI()
    app.include_router(critic_router)
    client = TestClient(app)

    resp = client.post(
        "/status/job-1/critic/findings/bulk-status",
        json={"next_status": "ACKNOWLEDGED", "apply_to_all": True},
    )
    assert resp.status_code == 200
    assert calls["bulk"]["next_status"] == "acknowledged"
    assert calls["bulk"]["actor"] == "reviewer@example.com"
