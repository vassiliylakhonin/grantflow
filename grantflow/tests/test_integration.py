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


def test_demo_console_page_loads():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "GrantFlow Demo Console" in body
    assert "/status/${encodeURIComponent(jobId)}/metrics" in body
    assert "/status/${encodeURIComponent(jobId)}/critic" in body
    assert "criticSeverityFilter" in body
    assert "Jump to Diff" in body
    assert "Create Comment" in body
    assert "criticContextList" in body
    assert "commentsFilterStatus" in body
    assert "commentsFilterVersionId" in body
    assert "grantflow_demo_diff_section" in body


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
    critic_notes = state.get("critic_notes") or {}
    assert isinstance(critic_notes.get("fatal_flaws"), list)
    if critic_notes.get("fatal_flaws"):
        flaw = critic_notes["fatal_flaws"][0]
        assert isinstance(flaw, dict)
        assert "code" in flaw
        assert "section" in flaw
        assert "message" in flaw
    assert isinstance(critic_notes.get("rule_checks"), list)


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


def test_status_critic_endpoint_returns_typed_payload():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Maternal Health", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    terminal = _wait_for_terminal_status(job_id)
    assert terminal["status"] == "done"

    critic_resp = client.get(f"/status/{job_id}/critic")
    assert critic_resp.status_code == 200
    body = critic_resp.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"
    assert isinstance(body["fatal_flaw_count"], int)
    assert isinstance(body["fatal_flaws"], list)
    assert isinstance(body["fatal_flaw_messages"], list)
    assert isinstance(body["rule_check_count"], int)
    assert isinstance(body["rule_checks"], list)
    assert body["rule_check_count"] == len(body["rule_checks"])
    assert body["fatal_flaw_count"] == len(body["fatal_flaws"])
    if body["rule_checks"]:
        check = body["rule_checks"][0]
        assert "code" in check
        assert "status" in check
        assert "section" in check
    if body["fatal_flaws"]:
        flaw = body["fatal_flaws"][0]
        assert "code" in flaw
        assert "severity" in flaw
        assert "section" in flaw
        assert "message" in flaw


def test_status_includes_citations_traceability(monkeypatch):
    def fake_query(namespace, query_texts, n_results=5, where=None, top_k=None):
        return {
            "documents": [["Official indicator guidance excerpt"]],
            "metadatas": [
                [
                    {
                        "source": "/tmp/usaid_guide.pdf",
                        "page": 12,
                        "page_start": 12,
                        "page_end": 12,
                        "chunk": 3,
                        "chunk_id": "usaid_ads201_p12_c0",
                        "indicator_id": "EG.3.2-1",
                        "citation": "USAID ADS 201 p.12",
                        "name": "Households with improved access",
                    }
                ]
            ],
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

    architect_citations = [c for c in citations if c.get("stage") == "architect"]
    assert architect_citations
    assert any(c.get("statement_path") for c in architect_citations)
    assert any(c.get("citation_type") in {"rag_claim_support", "fallback_namespace"} for c in architect_citations)

    citations_response = client.get(f"/status/{job_id}/citations")
    assert citations_response.status_code == 200
    citations_body = citations_response.json()
    assert citations_body["job_id"] == job_id
    assert citations_body["status"] == "done"
    assert citations_body["citation_count"] >= 1
    assert isinstance(citations_body["citations"], list)
    assert citations_body["citations"][0]["stage"]
    assert any("statement_path" in c for c in citations_body["citations"])


def test_status_includes_draft_versions_traceability():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Livelihoods", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    assert state.get("toc_validation", {}).get("valid") is True
    assert state.get("toc_validation", {}).get("schema_name")
    assert state.get("architect_retrieval", {}).get("namespace")
    assert "hits_count" in (state.get("architect_retrieval") or {})
    assert state.get("toc_generation_meta", {}).get("engine")
    assert isinstance(state.get("toc_draft", {}).get("validation"), dict)
    assert isinstance(state.get("toc_draft", {}).get("architect_retrieval"), dict)
    versions = state.get("draft_versions")
    assert isinstance(versions, list)
    assert len(versions) >= 2
    sections = {v.get("section") for v in versions}
    assert "toc" in sections
    assert "logframe" in sections
    assert "job_events" not in status

    events_resp = client.get(f"/status/{job_id}/events")
    assert events_resp.status_code == 200
    events_body = events_resp.json()
    assert events_body["job_id"] == job_id
    assert events_body["event_count"] >= 3
    event_types = [e["type"] for e in events_body["events"]]
    assert "status_changed" in event_types
    statuses = [e.get("to_status") for e in events_body["events"] if e["type"] == "status_changed"]
    assert "accepted" in statuses
    assert "running" in statuses
    assert "done" in statuses


def test_versions_and_diff_endpoints():
    job_id = "test-job-versions-1"
    api_app_module._set_job(
        job_id,
        {
            "status": "done",
            "hitl_enabled": False,
            "state": {
                "draft_versions": [
                    {
                        "version_id": "toc_v1",
                        "sequence": 1,
                        "section": "toc",
                        "node": "architect",
                        "iteration": 1,
                        "content": {"toc": {"brief": "v1", "project": "Water"}},
                        "content_hash": "hash1",
                    },
                    {
                        "version_id": "toc_v2",
                        "sequence": 2,
                        "section": "toc",
                        "node": "architect",
                        "iteration": 2,
                        "content": {"toc": {"brief": "v2", "project": "Water"}},
                        "content_hash": "hash2",
                    },
                    {
                        "version_id": "logframe_v1",
                        "sequence": 3,
                        "section": "logframe",
                        "node": "mel_specialist",
                        "iteration": 2,
                        "content": {"indicators": [{"indicator_id": "IND_001"}]},
                        "content_hash": "hash3",
                    },
                ]
            },
        },
    )

    versions_resp = client.get(f"/status/{job_id}/versions")
    assert versions_resp.status_code == 200
    versions_body = versions_resp.json()
    assert versions_body["job_id"] == job_id
    assert versions_body["version_count"] == 3
    assert [v["version_id"] for v in versions_body["versions"]] == ["toc_v1", "toc_v2", "logframe_v1"]

    toc_versions_resp = client.get(f"/status/{job_id}/versions", params={"section": "toc"})
    assert toc_versions_resp.status_code == 200
    assert toc_versions_resp.json()["version_count"] == 2

    diff_resp = client.get(f"/status/{job_id}/diff", params={"section": "toc"})
    assert diff_resp.status_code == 200
    diff_body = diff_resp.json()
    assert diff_body["job_id"] == job_id
    assert diff_body["section"] == "toc"
    assert diff_body["from_version_id"] == "toc_v1"
    assert diff_body["to_version_id"] == "toc_v2"
    assert diff_body["has_diff"] is True
    assert "toc_v1" in diff_body["diff_text"]
    assert "toc_v2" in diff_body["diff_text"]
    assert any(line.startswith("-") or line.startswith("+") for line in diff_body["diff_lines"])


def test_status_comments_endpoints_create_list_and_filter():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "WASH", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    _wait_for_terminal_status(job_id)

    versions_resp = client.get(f"/status/{job_id}/versions", params={"section": "toc"})
    assert versions_resp.status_code == 200
    versions = versions_resp.json()["versions"]
    assert versions
    toc_version_id = versions[-1]["version_id"]

    create_resp = client.post(
        f"/status/{job_id}/comments",
        json={
            "section": "toc",
            "message": "Please tighten assumptions and clarify beneficiary targeting.",
            "author": "reviewer-1",
            "version_id": toc_version_id,
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["section"] == "toc"
    assert created["status"] == "open"
    assert created["version_id"] == toc_version_id
    assert created["author"] == "reviewer-1"

    comments_resp = client.get(f"/status/{job_id}/comments")
    assert comments_resp.status_code == 200
    comments_body = comments_resp.json()
    assert comments_body["job_id"] == job_id
    assert comments_body["comment_count"] >= 1
    assert any(c["comment_id"] == created["comment_id"] for c in comments_body["comments"])

    resolve_resp = client.post(f"/status/{job_id}/comments/{created['comment_id']}/resolve")
    assert resolve_resp.status_code == 200
    resolved = resolve_resp.json()
    assert resolved["comment_id"] == created["comment_id"]
    assert resolved["status"] == "resolved"

    resolved_filter_resp = client.get(f"/status/{job_id}/comments", params={"status": "resolved"})
    assert resolved_filter_resp.status_code == 200
    resolved_filter_body = resolved_filter_resp.json()
    assert any(c["comment_id"] == created["comment_id"] for c in resolved_filter_body["comments"])

    reopen_resp = client.post(f"/status/{job_id}/comments/{created['comment_id']}/reopen")
    assert reopen_resp.status_code == 200
    reopened = reopen_resp.json()
    assert reopened["comment_id"] == created["comment_id"]
    assert reopened["status"] == "open"

    filtered_resp = client.get(
        f"/status/{job_id}/comments",
        params={"section": "toc", "status": "open", "version_id": toc_version_id},
    )
    assert filtered_resp.status_code == 200
    filtered_body = filtered_resp.json()
    assert filtered_body["comment_count"] >= 1
    assert all(c["section"] == "toc" for c in filtered_body["comments"])
    assert all(c["status"] == "open" for c in filtered_body["comments"])
    assert all((c.get("version_id") or "") == toc_version_id for c in filtered_body["comments"])

    status_resp = client.get(f"/status/{job_id}")
    assert status_resp.status_code == 200
    assert "review_comments" not in status_resp.json()


def test_status_comments_endpoint_rejects_invalid_section_or_version():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Nutrition", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    _wait_for_terminal_status(job_id)

    bad_section = client.post(
        f"/status/{job_id}/comments",
        json={"section": "budget", "message": "Budget narrative mismatch"},
    )
    assert bad_section.status_code == 400

    bad_version = client.post(
        f"/status/{job_id}/comments",
        json={"section": "toc", "message": "Version mismatch", "version_id": "missing-version"},
    )
    assert bad_version.status_code == 400


def test_metrics_endpoint_derives_timeline_metrics_from_events():
    job_id = "test-job-metrics-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "hitl_enabled": True,
            "job_events": [
                {
                    "event_id": "e1",
                    "ts": "2026-02-24T10:00:00+00:00",
                    "type": "status_changed",
                    "from_status": None,
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "e2",
                    "ts": "2026-02-24T10:00:10+00:00",
                    "type": "status_changed",
                    "from_status": "accepted",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "e3",
                    "ts": "2026-02-24T10:01:00+00:00",
                    "type": "status_changed",
                    "from_status": "running",
                    "to_status": "pending_hitl",
                    "status": "pending_hitl",
                },
                {
                    "event_id": "e4",
                    "ts": "2026-02-24T10:05:00+00:00",
                    "type": "resume_requested",
                    "status": "accepted",
                    "resuming_from": "mel",
                },
                {
                    "event_id": "e5",
                    "ts": "2026-02-24T10:05:05+00:00",
                    "type": "status_changed",
                    "from_status": "pending_hitl",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "e6",
                    "ts": "2026-02-24T10:05:06+00:00",
                    "type": "status_changed",
                    "from_status": "accepted",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "e7",
                    "ts": "2026-02-24T10:06:00+00:00",
                    "type": "status_changed",
                    "from_status": "running",
                    "to_status": "done",
                    "status": "done",
                },
            ],
        },
    )

    response = client.get(f"/status/{job_id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"
    assert body["event_count"] == 7
    assert body["status_change_count"] == 6
    assert body["pause_count"] == 1
    assert body["resume_count"] == 1
    assert body["created_at"] == "2026-02-24T10:00:00+00:00"
    assert body["started_at"] == "2026-02-24T10:00:10+00:00"
    assert body["first_pending_hitl_at"] == "2026-02-24T10:01:00+00:00"
    assert body["terminal_at"] == "2026-02-24T10:06:00+00:00"
    assert body["terminal_status"] == "done"
    assert body["time_to_first_draft_seconds"] == 60.0
    assert body["time_to_terminal_seconds"] == 360.0
    assert body["time_in_pending_hitl_seconds"] == 245.0


def test_portfolio_metrics_endpoint_aggregates_jobs_and_filters():
    api_app_module.JOB_STORE.set(
        "portfolio-job-1",
        {
            "status": "done",
            "hitl_enabled": True,
            "state": {"donor_id": "usaid"},
            "job_events": [
                {
                    "event_id": "a1",
                    "ts": "2026-02-24T10:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "a2",
                    "ts": "2026-02-24T10:00:05+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "a3",
                    "ts": "2026-02-24T10:00:20+00:00",
                    "type": "status_changed",
                    "to_status": "pending_hitl",
                    "status": "pending_hitl",
                },
                {"event_id": "a4", "ts": "2026-02-24T10:01:00+00:00", "type": "resume_requested", "status": "accepted"},
                {
                    "event_id": "a5",
                    "ts": "2026-02-24T10:01:02+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "a6",
                    "ts": "2026-02-24T10:01:03+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "a7",
                    "ts": "2026-02-24T10:02:00+00:00",
                    "type": "status_changed",
                    "to_status": "done",
                    "status": "done",
                },
            ],
        },
    )
    api_app_module.JOB_STORE.set(
        "portfolio-job-2",
        {
            "status": "error",
            "hitl_enabled": False,
            "state": {"donor_id": "eu"},
            "job_events": [
                {
                    "event_id": "b1",
                    "ts": "2026-02-24T11:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "b2",
                    "ts": "2026-02-24T11:00:03+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "b3",
                    "ts": "2026-02-24T11:00:30+00:00",
                    "type": "status_changed",
                    "to_status": "error",
                    "status": "error",
                },
            ],
        },
    )

    response = client.get("/portfolio/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["job_count"] >= 2
    assert body["status_counts"]["done"] >= 1
    assert body["status_counts"]["error"] >= 1
    assert body["donor_counts"]["usaid"] >= 1
    assert body["donor_counts"]["eu"] >= 1
    assert body["terminal_job_count"] >= 2
    assert body["hitl_job_count"] >= 1
    assert body["total_pause_count"] >= 1
    assert body["total_resume_count"] >= 1
    assert body["avg_time_to_terminal_seconds"] is not None

    filtered = client.get("/portfolio/metrics", params={"donor_id": "usaid", "status": "done", "hitl_enabled": "true"})
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["filters"]["donor_id"] == "usaid"
    assert filtered_body["filters"]["status"] == "done"
    assert filtered_body["filters"]["hitl_enabled"] is True
    assert filtered_body["job_count"] >= 1
    assert "error" not in filtered_body["status_counts"]


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

    citations_unauth = client.get(f"/status/{job_id}/citations")
    assert citations_unauth.status_code == 401

    citations_auth = client.get(f"/status/{job_id}/citations", headers={"X-API-Key": "test-secret"})
    assert citations_auth.status_code == 200

    versions_unauth = client.get(f"/status/{job_id}/versions")
    assert versions_unauth.status_code == 401

    versions_auth = client.get(f"/status/{job_id}/versions", headers={"X-API-Key": "test-secret"})
    assert versions_auth.status_code == 200

    diff_unauth = client.get(f"/status/{job_id}/diff")
    assert diff_unauth.status_code == 401

    diff_auth = client.get(f"/status/{job_id}/diff", headers={"X-API-Key": "test-secret"})
    assert diff_auth.status_code == 200

    events_unauth = client.get(f"/status/{job_id}/events")
    assert events_unauth.status_code == 401

    events_auth = client.get(f"/status/{job_id}/events", headers={"X-API-Key": "test-secret"})
    assert events_auth.status_code == 200

    metrics_unauth = client.get(f"/status/{job_id}/metrics")
    assert metrics_unauth.status_code == 401

    metrics_auth = client.get(f"/status/{job_id}/metrics", headers={"X-API-Key": "test-secret"})
    assert metrics_auth.status_code == 200

    critic_unauth = client.get(f"/status/{job_id}/critic")
    assert critic_unauth.status_code == 401

    critic_auth = client.get(f"/status/{job_id}/critic", headers={"X-API-Key": "test-secret"})
    assert critic_auth.status_code == 200

    comments_unauth = client.get(f"/status/{job_id}/comments")
    assert comments_unauth.status_code == 401

    comments_auth = client.get(f"/status/{job_id}/comments", headers={"X-API-Key": "test-secret"})
    assert comments_auth.status_code == 200

    add_comment_unauth = client.post(
        f"/status/{job_id}/comments",
        json={"section": "general", "message": "Needs management review"},
    )
    assert add_comment_unauth.status_code == 401

    add_comment_auth = client.post(
        f"/status/{job_id}/comments",
        json={"section": "general", "message": "Needs management review"},
        headers={"X-API-Key": "test-secret"},
    )
    assert add_comment_auth.status_code == 200
    comment_id = add_comment_auth.json()["comment_id"]

    resolve_comment_unauth = client.post(f"/status/{job_id}/comments/{comment_id}/resolve")
    assert resolve_comment_unauth.status_code == 401

    resolve_comment_auth = client.post(
        f"/status/{job_id}/comments/{comment_id}/resolve",
        headers={"X-API-Key": "test-secret"},
    )
    assert resolve_comment_auth.status_code == 200

    reopen_comment_unauth = client.post(f"/status/{job_id}/comments/{comment_id}/reopen")
    assert reopen_comment_unauth.status_code == 401

    reopen_comment_auth = client.post(
        f"/status/{job_id}/comments/{comment_id}/reopen",
        headers={"X-API-Key": "test-secret"},
    )
    assert reopen_comment_auth.status_code == 200

    portfolio_metrics_unauth = client.get("/portfolio/metrics")
    assert portfolio_metrics_unauth.status_code == 401

    portfolio_metrics_auth = client.get("/portfolio/metrics", headers={"X-API-Key": "test-secret"})
    assert portfolio_metrics_auth.status_code == 200

    pending_unauth = client.get("/hitl/pending")
    assert pending_unauth.status_code == 401

    pending_auth = client.get("/hitl/pending", headers={"X-API-Key": "test-secret"})
    assert pending_auth.status_code == 200


def test_openapi_declares_api_key_security_scheme():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    assert "ApiKeyAuth" in schemes
    assert schemes["ApiKeyAuth"]["type"] == "apiKey"
    assert schemes["ApiKeyAuth"]["in"] == "header"
    assert schemes["ApiKeyAuth"]["name"] == "X-API-Key"

    generate_security = (((spec.get("paths") or {}).get("/generate") or {}).get("post") or {}).get("security")
    ingest_security = (((spec.get("paths") or {}).get("/ingest") or {}).get("post") or {}).get("security")
    cancel_security = (((spec.get("paths") or {}).get("/cancel/{job_id}") or {}).get("post") or {}).get("security")
    status_security = (((spec.get("paths") or {}).get("/status/{job_id}") or {}).get("get") or {}).get("security")
    status_citations_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/citations") or {}).get("get") or {}
    ).get("security")
    status_versions_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/versions") or {}).get("get") or {}
    ).get("security")
    status_diff_security = (((spec.get("paths") or {}).get("/status/{job_id}/diff") or {}).get("get") or {}).get(
        "security"
    )
    status_events_security = (((spec.get("paths") or {}).get("/status/{job_id}/events") or {}).get("get") or {}).get(
        "security"
    )
    status_metrics_security = (((spec.get("paths") or {}).get("/status/{job_id}/metrics") or {}).get("get") or {}).get(
        "security"
    )
    status_critic_security = (((spec.get("paths") or {}).get("/status/{job_id}/critic") or {}).get("get") or {}).get(
        "security"
    )
    status_comments_get_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("get") or {}
    ).get("security")
    status_comments_post_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("post") or {}
    ).get("security")
    status_comments_resolve_security = (
        (((spec.get("paths") or {}).get("/status/{job_id}/comments/{comment_id}/resolve") or {}).get("post") or {})
    ).get("security")
    status_comments_reopen_security = (
        (((spec.get("paths") or {}).get("/status/{job_id}/comments/{comment_id}/reopen") or {}).get("post") or {})
    ).get("security")
    portfolio_metrics_security = (((spec.get("paths") or {}).get("/portfolio/metrics") or {}).get("get") or {}).get(
        "security"
    )
    status_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_citations_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/citations") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_versions_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/versions") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_diff_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/diff") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_events_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/events") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_metrics_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/metrics") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_critic_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/critic") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_comments_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_comments_post_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("post") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_comments_resolve_response_schema = (
        (
            (
                (
                    ((spec.get("paths") or {}).get("/status/{job_id}/comments/{comment_id}/resolve") or {}).get("post")
                    or {}
                ).get("responses")
            )
            or {}
        )
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_comments_reopen_response_schema = (
        (
            (
                (
                    ((spec.get("paths") or {}).get("/status/{job_id}/comments/{comment_id}/reopen") or {}).get("post")
                    or {}
                ).get("responses")
            )
            or {}
        )
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    portfolio_metrics_response_schema = (
        ((((spec.get("paths") or {}).get("/portfolio/metrics") or {}).get("get") or {}).get("responses") or {})
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
    assert status_citations_security == [{"ApiKeyAuth": []}]
    assert status_versions_security == [{"ApiKeyAuth": []}]
    assert status_diff_security == [{"ApiKeyAuth": []}]
    assert status_events_security == [{"ApiKeyAuth": []}]
    assert status_metrics_security == [{"ApiKeyAuth": []}]
    assert status_critic_security == [{"ApiKeyAuth": []}]
    assert status_comments_get_security == [{"ApiKeyAuth": []}]
    assert status_comments_post_security == [{"ApiKeyAuth": []}]
    assert status_comments_resolve_security == [{"ApiKeyAuth": []}]
    assert status_comments_reopen_security == [{"ApiKeyAuth": []}]
    assert portfolio_metrics_security == [{"ApiKeyAuth": []}]
    assert status_response_schema == {"$ref": "#/components/schemas/JobStatusPublicResponse"}
    assert status_citations_response_schema == {"$ref": "#/components/schemas/JobCitationsPublicResponse"}
    assert status_versions_response_schema == {"$ref": "#/components/schemas/JobVersionsPublicResponse"}
    assert status_diff_response_schema == {"$ref": "#/components/schemas/JobDiffPublicResponse"}
    assert status_events_response_schema == {"$ref": "#/components/schemas/JobEventsPublicResponse"}
    assert status_metrics_response_schema == {"$ref": "#/components/schemas/JobMetricsPublicResponse"}
    assert status_critic_response_schema == {"$ref": "#/components/schemas/JobCriticPublicResponse"}
    assert status_comments_response_schema == {"$ref": "#/components/schemas/JobCommentsPublicResponse"}
    assert status_comments_post_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert status_comments_resolve_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert status_comments_reopen_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert portfolio_metrics_response_schema == {"$ref": "#/components/schemas/PortfolioMetricsPublicResponse"}
    assert pending_response_schema == {"$ref": "#/components/schemas/HITLPendingListPublicResponse"}

    schemas = (spec.get("components") or {}).get("schemas") or {}
    assert "JobStatusPublicResponse" in schemas
    assert "JobCitationsPublicResponse" in schemas
    assert "CitationPublicResponse" in schemas
    assert "JobVersionsPublicResponse" in schemas
    assert "DraftVersionPublicResponse" in schemas
    assert "JobDiffPublicResponse" in schemas
    assert "JobEventsPublicResponse" in schemas
    assert "JobEventPublicResponse" in schemas
    assert "JobMetricsPublicResponse" in schemas
    assert "JobCriticPublicResponse" in schemas
    assert "CriticRuleCheckPublicResponse" in schemas
    assert "CriticFatalFlawPublicResponse" in schemas
    assert "JobCommentsPublicResponse" in schemas
    assert "ReviewCommentPublicResponse" in schemas
    assert "PortfolioMetricsPublicResponse" in schemas
    assert "PortfolioMetricsFiltersPublicResponse" in schemas
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
    engine = str((state.get("critic_notes") or {}).get("engine", "") or "")
    assert engine in {"rules", ""} or engine.startswith("rules+llm:")


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
