# grantflow/tests/test_integration.py

import json
import time
from fastapi.testclient import TestClient

import grantflow.api.app as api_app_module
from grantflow.api.app import app

client = TestClient(app)


def _wait_for_terminal_status(job_id: str, timeout_s: float = 3.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        response = client.get(f"/status/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"done", "error", "pending_hitl"}:
            return body
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for job completion")


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["version"]
    diagnostics = body["diagnostics"]
    assert diagnostics["job_store"]["mode"] in {"inmem", "sqlite"}
    assert diagnostics["hitl_store"]["mode"] in {"inmem", "sqlite"}
    assert isinstance(diagnostics["auth"]["api_key_configured"], bool)
    assert isinstance(diagnostics["auth"]["read_auth_required"], bool)
    assert diagnostics["vector_store"]["backend"] in {"chroma", "memory"}
    assert diagnostics["vector_store"]["collection_prefix"]


def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    checks = body["checks"]
    assert checks["vector_store"]["backend"] in {"chroma", "memory"}
    assert checks["vector_store"]["ready"] is True


def test_ready_endpoint_returns_503_when_vector_store_unavailable(monkeypatch):
    class BrokenClient:
        def heartbeat(self):
            raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(api_app_module.vector_store, "client", BrokenClient())

    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["status"] == "degraded"
    assert body["detail"]["checks"]["vector_store"]["backend"] == "chroma"
    assert body["detail"]["checks"]["vector_store"]["ready"] is False
    assert "chroma unavailable" in body["detail"]["checks"]["vector_store"]["error"]


def test_list_donors():
    response = client.get("/donors")
    assert response.status_code == 200
    donors = response.json()["donors"]
    donor_ids = [d["id"] for d in donors]
    assert "usaid" in donor_ids
    assert "eu" in donor_ids
    assert "worldbank" in donor_ids


def test_generate_basic_async_job_flow():
    payload = {
        "donor_id": "usaid",
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": False,
        "hitl_enabled": False,
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data

    status = _wait_for_terminal_status(data["job_id"])
    assert status["status"] == "done"
    state = status["state"]
    assert state["toc_draft"]
    assert state["logframe_draft"]
    assert state["quality_score"] >= 0


def test_status_redacts_internal_strategy_objects():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Governance Support", "country": "Ukraine"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    assert "donor_strategy" not in state
    assert "strategy" not in state
    assert state["donor_id"] == "usaid"
    assert state["toc_draft"]


def test_status_includes_citations_traceability(monkeypatch):
    def fake_query(namespace, query_texts, n_results=5, where=None, top_k=None):
        return {
            "documents": [["Official indicator guidance excerpt"]],
            "metadatas": [[{
                "source": "/tmp/usaid_guide.pdf",
                "page": 12,
                "page_start": 12,
                "page_end": 12,
                "chunk": 3,
                "chunk_id": "usaid_ads201_p12_c0",
                "indicator_id": "EG.3.2-1",
                "citation": "USAID ADS 201 p.12",
                "name": "Households with improved access",
            }]],
        }

    monkeypatch.setattr(api_app_module.vector_store, "query", fake_query)

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Water Sanitation", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    citations = state.get("citations")
    assert isinstance(citations, list)
    assert citations

    mel_citations = [c for c in citations if c.get("stage") == "mel"]
    assert mel_citations
    citation = mel_citations[0]
    assert citation["citation_type"] == "rag_result"
    assert citation["namespace"] == "usaid_ads201"
    assert citation["source"] == "/tmp/usaid_guide.pdf"
    assert citation["page"] == 12
    assert citation["chunk"] == 3
    assert citation["chunk_id"] == "usaid_ads201_p12_c0"
    assert citation["used_for"] == "EG.3.2-1"
    assert "excerpt" in citation and citation["excerpt"]


def test_generate_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("GRANTFLOW_API_KEY", "test-secret")

    payload = {
        "donor_id": "usaid",
        "input_context": {"project": "Public Health", "country": "Kenya"},
        "llm_mode": False,
        "hitl_enabled": False,
    }

    response = client.post("/generate", json=payload)
    assert response.status_code == 401

    response = client.post("/generate", json=payload, headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_read_endpoints_require_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("GRANTFLOW_API_KEY", "test-secret")
    monkeypatch.setenv("GRANTFLOW_REQUIRE_AUTH_FOR_READS", "true")

    gen = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Health Systems", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
        headers={"X-API-Key": "test-secret"},
    )
    assert gen.status_code == 200
    job_id = gen.json()["job_id"]

    status_unauth = client.get(f"/status/{job_id}")
    assert status_unauth.status_code == 401

    status_auth = client.get(f"/status/{job_id}", headers={"X-API-Key": "test-secret"})
    assert status_auth.status_code == 200

    pending_unauth = client.get("/hitl/pending")
    assert pending_unauth.status_code == 401

    pending_auth = client.get("/hitl/pending", headers={"X-API-Key": "test-secret"})
    assert pending_auth.status_code == 200


def test_openapi_declares_api_key_security_scheme():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    schemes = ((spec.get("components") or {}).get("securitySchemes") or {})
    assert "ApiKeyAuth" in schemes
    assert schemes["ApiKeyAuth"]["type"] == "apiKey"
    assert schemes["ApiKeyAuth"]["in"] == "header"
    assert schemes["ApiKeyAuth"]["name"] == "X-API-Key"

    generate_security = (((spec.get("paths") or {}).get("/generate") or {}).get("post") or {}).get("security")
    ingest_security = (((spec.get("paths") or {}).get("/ingest") or {}).get("post") or {}).get("security")
    cancel_security = (((spec.get("paths") or {}).get("/cancel/{job_id}") or {}).get("post") or {}).get("security")
    status_security = (((spec.get("paths") or {}).get("/status/{job_id}") or {}).get("get") or {}).get("security")
    status_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    pending_response_schema = (
        ((((spec.get("paths") or {}).get("/hitl/pending") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    assert generate_security == [{"ApiKeyAuth": []}]
    assert ingest_security == [{"ApiKeyAuth": []}]
    assert cancel_security == [{"ApiKeyAuth": []}]
    assert status_security == [{"ApiKeyAuth": []}]
    assert status_response_schema == {"$ref": "#/components/schemas/JobStatusPublicResponse"}
    assert pending_response_schema == {"$ref": "#/components/schemas/HITLPendingListPublicResponse"}

    schemas = (spec.get("components") or {}).get("schemas") or {}
    assert "JobStatusPublicResponse" in schemas
    assert "HITLPendingListPublicResponse" in schemas


def test_ingest_endpoint_uploads_to_donor_namespace(monkeypatch):
    calls = {}

    def fake_ingest(pdf_path: str, namespace: str, metadata=None):
        calls["pdf_path"] = pdf_path
        calls["namespace"] = namespace
        calls["metadata"] = metadata or {}
        return {
            "namespace": namespace,
            "source": pdf_path,
            "chunks_ingested": 3,
            "stats": {"namespace": namespace, "document_count": 3},
        }

    monkeypatch.setattr(api_app_module, "ingest_pdf_to_namespace", fake_ingest)

    response = client.post(
        "/ingest",
        data={"donor_id": "usaid", "metadata_json": json.dumps({"source_type": "manual_upload"})},
        files={"file": ("sample.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ingested"
    assert body["donor_id"] == "usaid"
    assert body["namespace"] == "usaid_ads201"
    assert body["filename"] == "sample.pdf"
    assert body["result"]["chunks_ingested"] == 3

    assert calls["namespace"] == "usaid_ads201"
    assert calls["metadata"]["uploaded_filename"] == "sample.pdf"
    assert calls["metadata"]["donor_id"] == "usaid"
    assert calls["metadata"]["source_type"] == "manual_upload"


def test_ingest_endpoint_validates_pdf_extension():
    response = client.post(
        "/ingest",
        data={"donor_id": "usaid"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF uploads are supported"


def test_ingest_endpoint_requires_api_key_when_configured(monkeypatch):
    def fake_ingest(pdf_path: str, namespace: str, metadata=None):
        return {"namespace": namespace, "source": pdf_path, "chunks_ingested": 1, "stats": {}}

    monkeypatch.setattr(api_app_module, "ingest_pdf_to_namespace", fake_ingest)
    monkeypatch.setenv("GRANTFLOW_API_KEY", "test-secret")

    response = client.post(
        "/ingest",
        data={"donor_id": "usaid"},
        files={"file": ("sample.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 401

    response = client.post(
        "/ingest",
        data={"donor_id": "usaid"},
        files={"file": ("sample.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200


def test_generate_dispatches_webhook_events(monkeypatch):
    events = []

    def fake_send_job_webhook_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(api_app_module, "send_job_webhook_event", fake_send_job_webhook_event)

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Livelihoods", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
            "webhook_url": "https://example.com/webhook",
            "webhook_secret": "secret123",
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"

    event_names = [evt["event"] for evt in events]
    assert "job.started" in event_names
    assert "job.completed" in event_names

    completed = [evt for evt in events if evt["event"] == "job.completed"][-1]
    assert completed["job_id"] == job_id
    assert completed["url"] == "https://example.com/webhook"
    assert completed["secret"] == "secret123"
    assert completed["job"]["status"] == "done"
    assert completed["job"]["webhook_configured"] is True
    assert "webhook_url" not in completed["job"]
    assert "webhook_secret" not in completed["job"]


def test_cancel_pending_hitl_job_and_cleanup_checkpoint(monkeypatch):
    events = []

    def fake_send_job_webhook_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(api_app_module, "send_job_webhook_event", fake_send_job_webhook_event)

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Education", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": True,
            "webhook_url": "https://example.com/webhook",
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "pending_hitl"
    checkpoint_id = status["checkpoint_id"]

    cancel = client.post(f"/cancel/{job_id}")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "canceled"
    assert cancel.json()["previous_status"] == "pending_hitl"

    status_after = client.get(f"/status/{job_id}")
    assert status_after.status_code == 200
    body = status_after.json()
    assert body["status"] == "canceled"
    assert body["webhook_configured"] is True
    assert "webhook_url" not in body
    assert "webhook_secret" not in body

    checkpoint = api_app_module.hitl_manager.get_checkpoint(checkpoint_id)
    assert checkpoint is not None
    cp_status = checkpoint["status"]
    assert getattr(cp_status, "value", cp_status) == "canceled"

    pending = client.get("/hitl/pending")
    assert pending.status_code == 200
    assert all(cp["id"] != checkpoint_id for cp in pending.json()["checkpoints"])

    event_names = [evt["event"] for evt in events]
    assert "job.pending_hitl" in event_names
    assert "job.canceled" in event_names


def test_hitl_pause_resume_flow():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Education", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": True,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "pending_hitl"
    assert status["checkpoint_stage"] == "toc"

    cp_id = status["checkpoint_id"]
    approve = client.post(
        "/hitl/approve",
        json={"checkpoint_id": cp_id, "approved": True, "feedback": "TOC approved"},
    )
    assert approve.status_code == 200

    resume = client.post(f"/resume/{job_id}", json={})
    assert resume.status_code == 200
    assert resume.json()["resuming_from"] == "mel"

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "pending_hitl"
    assert status["checkpoint_stage"] == "logframe"

    cp_id = status["checkpoint_id"]
    approve = client.post(
        "/hitl/approve",
        json={"checkpoint_id": cp_id, "approved": True, "feedback": "Logframe approved"},
    )
    assert approve.status_code == 200

    resume = client.post(f"/resume/{job_id}", json={})
    assert resume.status_code == 200
    assert resume.json()["resuming_from"] == "critic"

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    assert state["toc_draft"]
    assert state["logframe_draft"]
    assert (state.get("critic_notes") or {}).get("engine") in {"fallback", None} or str((state.get("critic_notes") or {}).get("engine", "")).startswith("llm:")


def test_generate_rejects_old_contract_shape():
    response = client.post(
        "/generate",
        json={"donor": "usaid", "input": {"project": "Water"}},
    )
    assert response.status_code == 422


def test_export_both_zip():
    gen = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Health", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    job_id = gen.json()["job_id"]
    status = _wait_for_terminal_status(job_id)
    state = status["state"]

    export = client.post("/export", json={"payload": state, "format": "both"})
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/zip")
    assert b"PK" == export.content[:2]


def test_hitl_checkpoint_endpoints():
    from grantflow.swarm.hitl import hitl_manager

    checkpoint_id = hitl_manager.create_checkpoint(
        stage="toc",
        state={"test": "data"},
        donor_id="USAID",
    )

    response = client.get("/hitl/pending")
    assert response.status_code == 200
    assert response.json()["pending_count"] >= 1
    checkpoints = response.json()["checkpoints"]
    matching = [cp for cp in checkpoints if cp["id"] == checkpoint_id]
    assert matching
    assert "state_snapshot" not in matching[0]
    assert matching[0]["has_state_snapshot"] is True

    response = client.post(
        "/hitl/approve",
        json={
            "checkpoint_id": checkpoint_id,
            "approved": True,
            "feedback": "Looks good",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
