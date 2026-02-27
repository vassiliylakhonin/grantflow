# grantflow/tests/test_integration.py

import gzip
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
    assert diagnostics["ingest_store"]["mode"] in {"inmem", "sqlite"}
    assert isinstance(diagnostics["auth"]["api_key_configured"], bool)
    assert isinstance(diagnostics["auth"]["read_auth_required"], bool)
    assert diagnostics["vector_store"]["backend"] in {"chroma", "memory"}
    assert diagnostics["vector_store"]["collection_prefix"]
    preflight_policy = diagnostics["preflight_grounding_policy"]
    assert preflight_policy["mode"] in {"warn", "strict", "off"}
    thresholds = preflight_policy["thresholds"]
    assert 0.0 <= float(thresholds["high_risk_coverage_threshold"]) <= 1.0
    assert 0.0 <= float(thresholds["medium_risk_coverage_threshold"]) <= 1.0
    assert int(thresholds["min_uploads"]) >= 1


def test_demo_console_page_loads():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "GrantFlow Demo Console" in body
    assert "generatePresetSelect" in body
    assert "applyPresetBtn" in body
    assert "clearPresetContextBtn" in body
    assert "generatePresetReadinessPill" in body
    assert "generatePresetReadinessText" in body
    assert "generatePresetReadinessHint" in body
    assert "syncGenerateReadinessBtn" in body
    assert "Sync Readiness Now" in body
    assert "Missing doc_family:" in body
    assert "skipZeroReadinessWarningCheckbox" in body
    assert "grantflow_demo_zero_readiness_warning_prefs" in body
    assert "Don't ask again for this preset" in body
    assert "RAG Readiness (for selected preset)" in body
    assert "Generate anyway?" in body
    assert "strictPreflight" in body
    assert "Strict Preflight" in body
    assert "Preflight risk" in body
    assert "Strict preflight" in body
    assert "inputContextJson" in body
    assert "usaid_gov_ai_kazakhstan" in body
    assert "worldbank_public_sector_uzbekistan" in body
    assert "ingestPresetSelect" in body
    assert "applyIngestPresetBtn" in body
    assert "syncIngestDonorBtn" in body
    assert "ingestFileInput" in body
    assert "ingestMetadataJson" in body
    assert "ingestBtn" in body
    assert "ingestPresetGuidanceList" in body
    assert "ingestChecklistSummary" in body
    assert "ingestChecklistProgressList" in body
    assert "resetIngestChecklistBtn" in body
    assert "syncIngestChecklistServerBtn" in body
    assert "copyIngestInventoryJsonBtn" in body
    assert "downloadIngestInventoryJsonBtn" in body
    assert "downloadIngestInventoryCsvBtn" in body
    assert "ingestInventoryJson" in body
    assert "grantflow_demo_ingest_checklist_progress" in body
    assert "doc_family=" in body
    assert "/ingest" in body
    assert "/ingest/inventory?" in body
    assert "/ingest/inventory/export?" in body
    assert "/status/${encodeURIComponent(jobId)}/metrics" in body
    assert "/status/${encodeURIComponent(jobId)}/quality" in body
    assert "/status/${encodeURIComponent(jobId)}/critic" in body
    assert "/status/${encodeURIComponent(jobId)}/export-payload" in body
    assert "/export" in body
    assert "criticSeverityFilter" in body
    assert "criticCitationConfidenceFilter" in body
    assert "criticAdvisorySummaryList" in body
    assert "criticAdvisoryLabelsList" in body
    assert "criticAdvisoryNormalizationList" in body
    assert "Jump to Diff" in body
    assert "Create Comment" in body
    assert "criticContextList" in body
    assert "llm_advisory_diagnostics" in body
    assert "conf " in body
    assert "thr " in body
    assert "architect_threshold_hit_rate" in body
    assert "qualityBtn" in body
    assert "qualityCards" in body
    assert "qualityPreflightMetaLine" in body
    assert "qualityJson" in body
    assert "exportPayloadBtn" in body
    assert "copyExportPayloadBtn" in body
    assert "exportZipFromPayloadBtn" in body
    assert "exportPayloadJson" in body
    assert "commentsFilterStatus" in body
    assert "commentsFilterVersionId" in body
    assert "grantflow_demo_diff_section" in body
    assert "grantflow_demo_strict_preflight" in body
    assert "grantflow_demo_portfolio_warning_level" in body
    assert "grantflow_demo_portfolio_grounding_risk_level" in body
    assert "grantflow_demo_portfolio_finding_status" in body
    assert "grantflow_demo_portfolio_finding_severity" in body
    assert "grantflow_demo_export_gzip_enabled" in body
    assert "generatePreflightAlert" in body
    assert "generatePreflightAlertTitle" in body
    assert "generatePreflightAlertBody" in body
    assert "portfolioBtn" in body
    assert "portfolioClearBtn" in body
    assert "portfolioWarningLevelFilter" in body
    assert "portfolioGroundingRiskLevelFilter" in body
    assert "portfolioFindingStatusFilter" in body
    assert "portfolioFindingSeverityFilter" in body
    assert "/portfolio/quality" in body
    assert "/portfolio/metrics/export" in body
    assert "/portfolio/quality/export" in body
    assert "portfolioMetricsCards" in body
    assert "portfolioQualityCards" in body
    assert "portfolioMetricsWarningLevelsList" in body
    assert "portfolioMetricsGroundingRiskLevelsList" in body
    assert "portfolioQualityRiskList" in body
    assert "portfolioQualityOpenFindingsList" in body
    assert "portfolioQualityWarningLevelsList" in body
    assert "portfolioQualityGroundingRiskLevelsList" in body
    assert "portfolioQualityFindingStatusList" in body
    assert "portfolioQualityFindingSeverityList" in body
    assert "portfolioQualityGroundingRiskList" in body
    assert "portfolioQualityPrioritySignalsList" in body
    assert "portfolioQualityWeightedDonorsList" in body
    assert "% High-warning Jobs" in body
    assert "% Medium-warning Jobs" in body
    assert "% Low-warning Jobs" in body
    assert "% No-warning Jobs" in body
    assert "Fallback Dominance" in body
    assert "High-Risk Donors" in body
    assert "portfolioWarningMetaLine" in body
    assert "qualityLlmFindingLabelsList" in body
    assert "qualityAdvisoryBadgeList" in body
    assert "qualityReadinessWarningLevelPill" in body
    assert "portfolioQualityLlmLabelCountsList" in body
    assert "portfolioQualityTopDonorLlmLabelCountsList" in body
    assert "portfolioQualityTopDonorAdvisoryRejectedReasonsList" in body
    assert "portfolioQualityTopDonorAdvisoryAppliedList" in body
    assert "portfolioQualityFocusedDonorSummaryList" in body
    assert "portfolioQualityFocusedDonorAdvisoryPill" in body
    assert "portfolioQualityFocusedDonorAdvisoryPillText" in body
    assert "portfolioQualityFocusedDonorLlmLabelCountsList" in body
    assert "portfolioQualityFocusedDonorAdvisoryRejectedReasonsList" in body
    assert "portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList" in body
    assert "portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList" in body
    assert "portfolioQualityAdvisoryAppliedList" in body
    assert "portfolioQualityAdvisoryRejectedReasonsList" in body
    assert "portfolioQualityJson" in body
    assert 'params.set("finding_status",' in body
    assert 'params.set("finding_severity",' in body
    assert "copyPortfolioMetricsJsonBtn" in body
    assert "downloadPortfolioMetricsJsonBtn" in body
    assert "downloadPortfolioMetricsCsvBtn" in body
    assert "exportGzipEnabled" in body
    assert "exportInventoryJsonBtn" in body
    assert "exportInventoryCsvBtn" in body
    assert "exportPortfolioMetricsJsonBtn" in body
    assert "exportPortfolioMetricsCsvBtn" in body
    assert "exportPortfolioQualityJsonBtn" in body
    assert "exportPortfolioQualityCsvBtn" in body
    assert "Export (Server-side)" in body
    assert 'params.set("gzip", "true")' in body
    assert "grantflow_portfolio_metrics.csv" in body
    assert "copyPortfolioQualityJsonBtn" in body
    assert "downloadPortfolioQualityJsonBtn" in body
    assert "downloadPortfolioQualityCsvBtn" in body
    assert "grantflow_portfolio_quality.csv" in body
    assert "portfolioStatusCountsList" in body
    assert "portfolioDonorCountsList" in body
    assert "Click to filter" in body
    assert "clearFiltersBtn" in body
    assert "Acknowledge" in body
    assert "Resolve Finding" in body
    assert "Reopen Finding" in body
    assert "linkedFindingId" in body
    assert "reviewWorkflowBtn" in body
    assert "reviewWorkflowSummaryLine" in body
    assert "reviewWorkflowTimelineList" in body
    assert "reviewWorkflowJson" in body
    assert "reviewWorkflowEventTypeFilter" in body
    assert "reviewWorkflowFindingIdFilter" in body
    assert "reviewWorkflowCommentStatusFilter" in body
    assert "reviewWorkflowClearFiltersBtn" in body
    assert "reviewWorkflowExportJsonBtn" in body
    assert "reviewWorkflowExportCsvBtn" in body
    assert "grantflow_demo_review_workflow_event_type" in body
    assert "grantflow_demo_review_workflow_finding_id" in body
    assert "grantflow_demo_review_workflow_comment_status" in body
    assert "/status/${encodeURIComponent(jobId)}/review/workflow" in body
    assert "/status/${encodeURIComponent(jobId)}/review/workflow/export" in body


def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    checks = body["checks"]
    assert checks["vector_store"]["backend"] in {"chroma", "memory"}
    assert checks["vector_store"]["ready"] is True
    preflight_policy = checks["preflight_grounding_policy"]
    assert preflight_policy["mode"] in {"warn", "strict", "off"}
    thresholds = preflight_policy["thresholds"]
    assert 0.0 <= float(thresholds["high_risk_coverage_threshold"]) <= 1.0
    assert 0.0 <= float(thresholds["medium_risk_coverage_threshold"]) <= 1.0
    assert int(thresholds["min_uploads"]) >= 1


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
    preflight_policy = body["detail"]["checks"]["preflight_grounding_policy"]
    assert preflight_policy["mode"] in {"warn", "strict", "off"}


def test_ready_endpoint_reflects_preflight_grounding_threshold_overrides(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "grounding_gate_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_high_risk_coverage_threshold", 0.42)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_medium_risk_coverage_threshold", 0.91)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_min_uploads", 7)

    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    policy = body["checks"]["preflight_grounding_policy"]
    assert policy["mode"] == "strict"
    thresholds = policy["thresholds"]
    assert thresholds["high_risk_coverage_threshold"] == 0.42
    assert thresholds["medium_risk_coverage_threshold"] == 0.91
    assert thresholds["min_uploads"] == 7


def test_ready_endpoint_preflight_policy_mode_can_differ_from_pipeline_mode(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "grounding_gate_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "warn")

    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"]["preflight_grounding_policy"]["mode"] == "warn"


def test_list_donors():
    response = client.get("/donors")
    assert response.status_code == 200
    donors = response.json()["donors"]
    donor_ids = [d["id"] for d in donors]
    assert "usaid" in donor_ids
    assert "eu" in donor_ids
    assert "worldbank" in donor_ids


def test_generate_preflight_reports_high_risk_when_namespace_empty():
    api_app_module.INGEST_AUDIT_STORE.clear()

    response = client.post("/generate/preflight", json={"donor_id": "usaid"})
    assert response.status_code == 200
    body = response.json()
    assert body["donor_id"] == "usaid"
    assert body["namespace_empty"] is True
    assert body["risk_level"] == "high"
    assert body["grounding_risk_level"] == "high"
    grounding_policy = body.get("grounding_policy") or {}
    assert grounding_policy["mode"] in {"warn", "strict", "off"}
    assert grounding_policy["risk_level"] == "high"
    assert grounding_policy["go_ahead"] in {True, False}
    assert isinstance(grounding_policy.get("reasons"), list)
    thresholds = grounding_policy.get("thresholds") or {}
    assert 0.0 <= float(thresholds.get("high_risk_coverage_threshold") or 0.0) <= 1.0
    assert 0.0 <= float(thresholds.get("medium_risk_coverage_threshold") or 0.0) <= 1.0
    assert float(thresholds.get("medium_risk_coverage_threshold") or 0.0) >= float(
        thresholds.get("high_risk_coverage_threshold") or 0.0
    )
    assert int(thresholds.get("min_uploads") or 0) >= 1
    assert body["go_ahead"] is False
    assert body["loaded_count"] == 0
    assert body["expected_count"] >= 1
    warning_codes = {row.get("code") for row in body["warnings"] if isinstance(row, dict)}
    assert "NAMESPACE_EMPTY" in warning_codes


def test_generate_response_and_status_include_preflight_payload():
    api_app_module.INGEST_AUDIT_STORE.clear()

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
    data = response.json()
    assert data["status"] == "accepted"
    preflight = data.get("preflight")
    assert isinstance(preflight, dict)
    assert preflight["donor_id"] == "usaid"
    assert preflight["risk_level"] == "high"
    assert preflight["grounding_risk_level"] == "high"
    assert isinstance(preflight.get("grounding_policy"), dict)

    status = _wait_for_terminal_status(data["job_id"])
    assert status["generate_preflight"] == preflight
    assert status["state"]["generate_preflight"] == preflight
    assert status["strict_preflight"] is False
    assert status["state"]["strict_preflight"] is False


def test_generate_strict_preflight_blocks_when_risk_is_high():
    api_app_module.INGEST_AUDIT_STORE.clear()

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Water Sanitation", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
            "strict_preflight": True,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["reason"] == "preflight_high_risk_block"
    assert detail["preflight"]["risk_level"] == "high"
    assert detail["preflight"]["grounding_risk_level"] == "high"
    assert "strict_reasons" in detail
    assert detail["preflight"]["go_ahead"] is False


def test_generate_strict_preflight_allows_when_risk_is_not_high(monkeypatch):
    monkeypatch.setattr(
        api_app_module,
        "_build_generate_preflight",
        lambda donor_id, strategy, client_metadata: {
            "donor_id": donor_id,
            "risk_level": "medium",
            "go_ahead": True,
            "warning_count": 1,
            "retrieval_namespace": "usaid_ads201",
            "namespace_empty": False,
            "warnings": [{"code": "LOW_DOC_COVERAGE", "severity": "medium"}],
        },
    )
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Water Sanitation", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
            "strict_preflight": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_generate_strict_preflight_blocks_when_grounding_risk_is_high(monkeypatch):
    monkeypatch.setattr(
        api_app_module,
        "_build_generate_preflight",
        lambda donor_id, strategy, client_metadata: {
            "donor_id": donor_id,
            "risk_level": "medium",
            "grounding_risk_level": "high",
            "go_ahead": True,
            "warning_count": 1,
            "retrieval_namespace": "usaid_ads201",
            "namespace_empty": False,
            "warnings": [{"code": "LOW_DOC_COVERAGE", "severity": "medium"}],
            "grounding_policy": {
                "mode": "warn",
                "risk_level": "high",
                "blocking": False,
                "go_ahead": True,
                "summary": "namespace_empty_or_low_coverage",
                "reasons": ["coverage_below_50pct"],
            },
        },
    )
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Water Sanitation", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
            "strict_preflight": True,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["reason"] == "preflight_high_risk_block"
    assert "grounding_risk_high" in (detail.get("strict_reasons") or [])
    assert detail["preflight"]["risk_level"] == "medium"
    assert detail["preflight"]["grounding_risk_level"] == "high"


def test_generate_blocks_when_preflight_grounding_policy_is_strict(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "grounding_gate_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "strict")
    api_app_module.INGEST_AUDIT_STORE.clear()

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Water Sanitation", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
            "strict_preflight": False,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["reason"] == "preflight_grounding_policy_block"
    assert detail["preflight"]["grounding_policy"]["mode"] == "strict"
    assert detail["preflight"]["grounding_policy"]["blocking"] is True
    assert detail["preflight"]["go_ahead"] is False


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


def test_generate_llm_mode_false_uses_non_llm_toc_engine():
    payload = {
        "donor_id": "usaid",
        "input_context": {"project": "Public Administration", "country": "Kazakhstan"},
        "llm_mode": False,
        "hitl_enabled": False,
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    generation_meta = state.get("toc_generation_meta") or {}
    assert generation_meta.get("llm_used") is False
    assert str(generation_meta.get("engine") or "").startswith("deterministic:")
    assert generation_meta.get("llm_requested") is False
    assert generation_meta.get("llm_attempted") is False
    assert generation_meta.get("fallback_used") is False
    assert generation_meta.get("fallback_class") == "deterministic_mode"


def test_strict_grounding_gate_blocks_job_finalization(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "grounding_gate_mode", "strict")
    monkeypatch.setattr(
        api_app_module,
        "_build_generate_preflight",
        lambda donor_id, strategy, client_metadata: {
            "donor_id": donor_id,
            "risk_level": "low",
            "grounding_risk_level": "low",
            "go_ahead": True,
            "warning_count": 0,
            "warnings": [],
            "retrieval_namespace": "usaid_ads201",
            "namespace_empty": False,
            "grounding_policy": {
                "mode": "strict",
                "risk_level": "low",
                "blocking": False,
                "go_ahead": True,
                "summary": "readiness_signals_ok",
                "reasons": ["sufficient_readiness_signals"],
            },
        },
    )
    monkeypatch.setattr(
        api_app_module.vector_store,
        "query",
        lambda namespace, query_texts, n_results=5, where=None, top_k=None: {
            "documents": [[]],
            "metadatas": [[]],
            "ids": [[]],
        },
    )

    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Gov services modernization", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    terminal = _wait_for_terminal_status(job_id)
    assert terminal["status"] == "error"
    assert "Grounding gate (strict) blocked finalization" in str(terminal.get("error") or "")
    state = terminal.get("state") or {}
    gate = state.get("grounding_gate") or {}
    assert gate.get("mode") == "strict"
    assert gate.get("blocking") is True
    assert gate.get("passed") is False


def test_export_endpoint_blocks_when_strict_grounding_gate_failed_unless_overridden():
    payload = {
        "state": {
            "donor_id": "usaid",
            "toc_draft": {"toc": {"brief": "Sample ToC"}},
            "logframe_draft": {"indicators": []},
            "grounding_gate": {
                "mode": "strict",
                "passed": False,
                "blocking": True,
                "summary": "fallback_or_low_rag_citations_dominate",
                "reasons": ["fallback_or_low_rag_citations_dominate"],
            },
        }
    }

    blocked = client.post("/export", json={"payload": payload, "format": "docx"})
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["reason"] == "grounding_gate_strict_block"

    allowed = client.post("/export", json={"payload": payload, "format": "docx", "allow_unsafe_export": True})
    assert allowed.status_code == 200
    assert allowed.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


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
        assert "id" in flaw and flaw["id"]
        assert "finding_id" in flaw and flaw["finding_id"]
        assert flaw["id"] == flaw["finding_id"]
        assert flaw.get("status") in {"open", "acknowledged", "resolved"}
        assert "code" in flaw
        assert "severity" in flaw
        assert "section" in flaw
        assert "message" in flaw


def test_status_critic_findings_can_be_acknowledged_resolved_and_linked_to_comments():
    job_id = "critic-findings-linkage-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "state": {
                "quality_score": 6.5,
                "critic_score": 6.5,
                "needs_revision": True,
                "critic_notes": {
                    "engine": "rules",
                    "rule_score": 6.5,
                    "llm_score": None,
                    "llm_advisory_diagnostics": {
                        "llm_finding_count": 1,
                        "candidate_label_counts": {"TOY_LABEL": 1},
                        "advisory_candidate_count": 0,
                        "advisory_candidate_labels": [],
                        "advisory_applies": False,
                        "advisory_rejected_reason": "non_advisory_llm_finding_present",
                    },
                    "revision_instructions": "Fix ToC and indicators.",
                    "fatal_flaws": [
                        {
                            "code": "TOC_SCHEMA_INVALID",
                            "severity": "high",
                            "section": "general",
                            "message": "Theory of Change draft does not match expected donor schema.",
                            "fix_hint": "Regenerate ToC with valid structured output.",
                            "source": "rules",
                        }
                    ],
                    "fatal_flaw_messages": ["Theory of Change draft does not match expected donor schema."],
                    "rule_checks": [{"code": "TOC_SCHEMA_VALID", "status": "fail", "section": "toc"}],
                },
            },
            "review_comments": [],
        },
    )

    critic_resp = client.get(f"/status/{job_id}/critic")
    assert critic_resp.status_code == 200
    critic_body = critic_resp.json()
    assert critic_body["fatal_flaws"]
    assert critic_body["llm_advisory_diagnostics"]["llm_finding_count"] == 1
    assert critic_body["llm_advisory_diagnostics"]["advisory_rejected_reason"] == "non_advisory_llm_finding_present"
    finding = critic_body["fatal_flaws"][0]
    finding_id = finding["finding_id"]

    ack_resp = client.post(
        f"/status/{job_id}/critic/findings/{finding_id}/ack",
        headers={"X-Reviewer": "qa_reviewer"},
    )
    assert ack_resp.status_code == 200
    ack_body = ack_resp.json()
    assert ack_body["id"] == finding_id
    assert ack_body["finding_id"] == finding_id
    assert ack_body["status"] == "acknowledged"
    assert ack_body.get("acknowledged_at")
    assert ack_body.get("updated_at")
    assert ack_body.get("updated_by") == "qa_reviewer"
    assert ack_body.get("acknowledged_by") == "qa_reviewer"

    comment_resp = client.post(
        f"/status/{job_id}/comments",
        json={
            "section": ack_body["section"],
            "message": "Acknowledged by reviewer; will revise next iteration.",
            "linked_finding_id": finding_id,
        },
    )
    assert comment_resp.status_code == 200
    comment_body = comment_resp.json()
    assert comment_body["linked_finding_id"] == finding_id

    critic_resp_2 = client.get(f"/status/{job_id}/critic")
    assert critic_resp_2.status_code == 200
    critic_body_2 = critic_resp_2.json()
    linked_finding = next(f for f in critic_body_2["fatal_flaws"] if f["finding_id"] == finding_id)
    assert comment_body["comment_id"] in (linked_finding.get("linked_comment_ids") or [])

    resolve_resp = client.post(
        f"/status/{job_id}/critic/findings/{finding_id}/resolve",
        headers={"X-User": "qa_resolver"},
    )
    assert resolve_resp.status_code == 200
    resolve_body = resolve_resp.json()
    assert resolve_body["id"] == finding_id
    assert resolve_body["finding_id"] == finding_id
    assert resolve_body["status"] == "resolved"
    assert resolve_body.get("resolved_at")
    assert resolve_body.get("updated_at")
    assert resolve_body.get("updated_by") == "qa_resolver"
    assert resolve_body.get("acknowledged_by") == "qa_reviewer"
    assert resolve_body.get("resolved_by") == "qa_resolver"

    reopen_resp = client.post(
        f"/status/{job_id}/critic/findings/{finding_id}/open",
        headers={"X-Actor": "qa_reopener"},
    )
    assert reopen_resp.status_code == 200
    reopen_body = reopen_resp.json()
    assert reopen_body["id"] == finding_id
    assert reopen_body["finding_id"] == finding_id
    assert reopen_body["status"] == "open"
    assert reopen_body.get("updated_at")
    assert reopen_body.get("updated_by") == "qa_reopener"
    assert reopen_body.get("acknowledged_at") is None
    assert reopen_body.get("acknowledged_by") is None
    assert reopen_body.get("resolved_at") is None
    assert reopen_body.get("resolved_by") is None


def test_status_critic_normalizes_legacy_string_findings_into_entities():
    job_id = "critic-findings-legacy-string-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "state": {
                "quality_score": 5.0,
                "critic_score": 5.0,
                "needs_revision": True,
                "critic_notes": {
                    "engine": "rules",
                    "fatal_flaws": [
                        "Missing indicator baseline and target for key outcome.",
                    ],
                    "fatal_flaw_messages": ["Missing indicator baseline and target for key outcome."],
                    "rule_checks": [],
                },
            },
        },
    )

    critic_resp = client.get(f"/status/{job_id}/critic")
    assert critic_resp.status_code == 200
    critic_body = critic_resp.json()
    assert critic_body["fatal_flaw_count"] == 1
    flaw = critic_body["fatal_flaws"][0]
    assert flaw["id"] == flaw["finding_id"]
    assert flaw["finding_id"]
    assert flaw["code"] == "LEGACY_UNSTRUCTURED_FINDING"
    assert flaw["status"] == "open"
    assert flaw["source"] == "rules"
    assert flaw["message"].startswith("Missing indicator baseline")
    assert flaw.get("fix_suggestion")

    ack_resp = client.post(f"/status/{job_id}/critic/findings/{flaw['finding_id']}/ack")
    assert ack_resp.status_code == 200
    ack_body = ack_resp.json()
    assert ack_body["status"] == "acknowledged"
    assert ack_body.get("acknowledged_at")


def test_status_critic_accepts_id_only_finding_entities():
    job_id = "critic-findings-id-only-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "state": {
                "quality_score": 6.0,
                "critic_score": 6.0,
                "needs_revision": True,
                "critic_notes": {
                    "engine": "rules",
                    "fatal_flaws": [
                        {
                            "id": "finding-id-only-1",
                            "code": "TOC_SCHEMA_INVALID",
                            "severity": "high",
                            "section": "toc",
                            "status": "open",
                            "message": "Theory of Change draft does not match expected donor schema.",
                            "fix_suggestion": "Regenerate ToC with valid structured output.",
                            "source": "rules",
                        }
                    ],
                    "fatal_flaw_messages": ["Theory of Change draft does not match expected donor schema."],
                    "rule_checks": [{"code": "TOC_SCHEMA_VALID", "status": "fail", "section": "toc"}],
                },
            },
            "review_comments": [],
        },
    )

    critic_resp = client.get(f"/status/{job_id}/critic")
    assert critic_resp.status_code == 200
    flaw = critic_resp.json()["fatal_flaws"][0]
    assert flaw["id"] == "finding-id-only-1"
    assert flaw["finding_id"] == "finding-id-only-1"

    ack_resp = client.post(f"/status/{job_id}/critic/findings/{flaw['id']}/ack")
    assert ack_resp.status_code == 200
    ack_body = ack_resp.json()
    assert ack_body["id"] == "finding-id-only-1"
    assert ack_body["finding_id"] == "finding-id-only-1"
    assert ack_body["status"] == "acknowledged"


def test_status_export_payload_endpoint_returns_review_ready_payload():
    job_id = "export-payload-1"
    api_app_module.INGEST_AUDIT_STORE.clear()
    api_app_module.INGEST_AUDIT_STORE.append(
        {
            "event_id": "ing-exp-1",
            "ts": "2026-02-24T09:00:00+00:00",
            "donor_id": "usaid",
            "namespace": "usaid_ads201",
            "filename": "ads.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "donor_policy", "source_type": "donor_guidance"},
            "result": {"chunks_ingested": 4},
        }
    )
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "strict_preflight": True,
            "generate_preflight": {
                "donor_id": "usaid",
                "risk_level": "medium",
                "go_ahead": True,
                "warning_count": 1,
                "warnings": [{"code": "LOW_DOC_COVERAGE", "severity": "medium"}],
            },
            "client_metadata": {
                "demo_generate_preset_key": "usaid_gov_ai_kazakhstan",
                "rag_readiness": {
                    "expected_doc_families": ["donor_policy", "country_context"],
                    "donor_id": "usaid",
                },
            },
            "state": {
                "donor_id": "usaid",
                "toc_draft": {"toc": {"brief": "Sample ToC"}},
                "logframe_draft": {"indicators": [{"indicator_id": "IND_001"}]},
                "citations": [{"stage": "mel", "label": "USAID ADS 201 p.12"}],
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "finding-1",
                            "status": "acknowledged",
                            "severity": "high",
                            "section": "toc",
                            "code": "TOC_SCHEMA_INVALID",
                            "message": "Schema mismatch",
                            "fix_hint": "Fix objective structure",
                            "source": "rules",
                        }
                    ]
                },
                "strategy": object(),
                "donor_strategy": object(),
            },
            "review_comments": [
                {
                    "comment_id": "comment-1",
                    "status": "open",
                    "section": "toc",
                    "message": "Please revise objective hierarchy",
                    "linked_finding_id": "finding-1",
                    "version_id": "toc_v1",
                }
            ],
        },
    )

    response = client.get(f"/status/{job_id}/export-payload")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"
    payload = body["payload"]
    assert isinstance(payload, dict)
    assert isinstance(payload["state"], dict)
    assert "strategy" not in payload["state"]
    assert "donor_strategy" not in payload["state"]
    assert payload["state"]["toc_draft"]["toc"]["brief"] == "Sample ToC"
    assert isinstance(payload["critic_findings"], list)
    assert payload["critic_findings"][0]["id"] == "finding-1"
    assert payload["critic_findings"][0]["finding_id"] == "finding-1"
    assert payload["critic_findings"][0]["linked_comment_ids"] == ["comment-1"]
    assert isinstance(payload["review_comments"], list)
    assert payload["review_comments"][0]["linked_finding_id"] == "finding-1"
    assert payload["readiness"]["preset_key"] == "usaid_gov_ai_kazakhstan"
    assert payload["readiness"]["expected_doc_families"] == ["donor_policy", "country_context"]
    assert payload["readiness"]["present_doc_families"] == ["donor_policy"]
    assert payload["readiness"]["missing_doc_families"] == ["country_context"]
    assert payload["readiness"]["coverage_rate"] == 0.5


def test_status_includes_citations_traceability(monkeypatch):
    def fake_query(namespace, query_texts, n_results=5, where=None, top_k=None):
        return {
            "documents": [["Official indicator guidance excerpt"]],
            "ids": [["usaid_ads201_p12_c0"]],
            "distances": [[0.18]],
            "metadatas": [
                [
                    {
                        "source": "/tmp/usaid_guide.pdf",
                        "uploaded_filename": "usaid_guide.pdf",
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
    assert citation["source"] == "usaid_guide.pdf"
    assert citation["page"] == 12
    assert citation["chunk"] == 3
    assert citation["doc_id"] == "usaid_ads201_p12_c0"
    assert citation["chunk_id"] == "usaid_ads201_p12_c0"
    assert citation["used_for"] == "EG.3.2-1"
    assert citation["retrieval_rank"] == 1
    assert citation["retrieval_confidence"] > 0.0
    assert "excerpt" in citation and citation["excerpt"]

    architect_citations = [c for c in citations if c.get("stage") == "architect"]
    assert architect_citations
    assert any(c.get("statement_path") for c in architect_citations)
    assert any(
        c.get("citation_type") in {"rag_claim_support", "rag_low_confidence", "fallback_namespace"}
        for c in architect_citations
    )
    assert any(c.get("doc_id") == "usaid_ads201_p12_c0" for c in architect_citations)
    assert any(c.get("retrieval_rank") == 1 for c in architect_citations)
    for c in citations:
        source = str(c.get("source") or "")
        assert "grantflow_ingest_" not in source

    citations_response = client.get(f"/status/{job_id}/citations")
    assert citations_response.status_code == 200
    citations_body = citations_response.json()
    assert citations_body["job_id"] == job_id
    assert citations_body["status"] == "done"
    assert citations_body["citation_count"] >= 1
    assert isinstance(citations_body["citations"], list)
    assert citations_body["citations"][0]["stage"]
    assert any("statement_path" in c for c in citations_body["citations"])
    assert any("citation_confidence" in c for c in citations_body["citations"])
    assert any("doc_id" in c for c in citations_body["citations"])
    assert any("retrieval_rank" in c for c in citations_body["citations"])
    for c in citations_body["citations"]:
        if c.get("citation_confidence") is not None:
            assert 0.0 <= float(c["citation_confidence"]) <= 1.0
        if c.get("retrieval_confidence") is not None:
            assert 0.0 <= float(c["retrieval_confidence"]) <= 1.0


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
    retrieval_hits = (state.get("architect_retrieval") or {}).get("hits")
    if isinstance(retrieval_hits, list) and retrieval_hits:
        assert "doc_id" in retrieval_hits[0]
        assert "retrieval_rank" in retrieval_hits[0]
        assert "retrieval_confidence" in retrieval_hits[0]
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


def test_status_review_workflow_endpoint_aggregates_findings_comments_and_timeline():
    job_id = "review-workflow-job-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "state": {
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "finding-1",
                            "code": "TOC_SCHEMA_INVALID",
                            "severity": "high",
                            "section": "toc",
                            "status": "resolved",
                            "message": "ToC schema mismatch.",
                            "resolved_at": "2026-02-27T10:12:00+00:00",
                        },
                        {
                            "finding_id": "finding-2",
                            "code": "MEL_BASELINE_MISSING",
                            "severity": "low",
                            "section": "logframe",
                            "status": "open",
                            "message": "Baseline is missing for one indicator.",
                        },
                    ]
                }
            },
            "review_comments": [
                {
                    "comment_id": "comment-1",
                    "ts": "2026-02-27T10:00:00+00:00",
                    "section": "toc",
                    "status": "resolved",
                    "message": "Reviewed and addressed in v2.",
                    "author": "reviewer-1",
                    "linked_finding_id": "finding-1",
                },
                {
                    "comment_id": "comment-2",
                    "ts": "2026-02-27T10:01:00+00:00",
                    "section": "general",
                    "status": "open",
                    "message": "Need sign-off from program manager.",
                    "author": "reviewer-2",
                    "linked_finding_id": "missing-finding",
                },
            ],
            "job_events": [
                {
                    "event_id": "rwf-1",
                    "ts": "2026-02-27T10:00:00+00:00",
                    "type": "review_comment_added",
                    "comment_id": "comment-1",
                    "section": "toc",
                    "author": "reviewer-1",
                },
                {
                    "event_id": "rwf-2",
                    "ts": "2026-02-27T10:05:00+00:00",
                    "type": "critic_finding_status_changed",
                    "finding_id": "finding-1",
                    "status": "acknowledged",
                    "section": "toc",
                    "severity": "high",
                    "actor": "qa-reviewer",
                },
                {
                    "event_id": "rwf-3",
                    "ts": "2026-02-27T10:10:00+00:00",
                    "type": "review_comment_status_changed",
                    "comment_id": "comment-1",
                    "status": "resolved",
                    "section": "toc",
                    "actor": "qa-reviewer",
                },
                {
                    "event_id": "rwf-4",
                    "ts": "2026-02-27T10:12:00+00:00",
                    "type": "critic_finding_status_changed",
                    "finding_id": "finding-1",
                    "status": "resolved",
                    "section": "toc",
                    "severity": "high",
                    "actor": "qa-reviewer",
                },
                {
                    "event_id": "rwf-ignore",
                    "ts": "2026-02-27T10:15:00+00:00",
                    "type": "status_changed",
                    "to_status": "done",
                },
            ],
        },
    )

    response = client.get(f"/status/{job_id}/review/workflow")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"
    assert body.get("filters", {}).get("event_type") is None
    assert body.get("filters", {}).get("finding_id") is None
    assert body.get("filters", {}).get("comment_status") is None
    assert len(body["findings"]) == 2
    assert len(body["comments"]) == 2

    summary = body["summary"]
    assert summary["finding_count"] == 2
    assert summary["comment_count"] == 2
    assert summary["linked_comment_count"] == 2
    assert summary["orphan_linked_comment_count"] == 1
    assert summary["open_finding_count"] == 1
    assert summary["acknowledged_finding_count"] == 0
    assert summary["resolved_finding_count"] == 1
    assert summary["open_comment_count"] == 1
    assert summary["resolved_comment_count"] == 1
    assert summary["finding_status_counts"]["open"] == 1
    assert summary["finding_status_counts"]["resolved"] == 1
    assert summary["finding_severity_counts"]["high"] == 1
    assert summary["finding_severity_counts"]["low"] == 1
    assert summary["comment_status_counts"]["open"] == 1
    assert summary["comment_status_counts"]["resolved"] == 1
    assert summary["timeline_event_count"] == 4
    assert summary["last_activity_at"] == "2026-02-27T10:12:00+00:00"

    timeline = body["timeline"]
    assert len(timeline) == 4
    assert timeline[0]["ts"] == "2026-02-27T10:12:00+00:00"
    assert timeline[-1]["ts"] == "2026-02-27T10:00:00+00:00"
    timeline_types = {row["type"] for row in timeline}
    assert timeline_types == {
        "critic_finding_status_changed",
        "review_comment_added",
        "review_comment_status_changed",
    }

    finding_filtered = client.get(f"/status/{job_id}/review/workflow", params={"finding_id": "finding-1"})
    assert finding_filtered.status_code == 200
    finding_filtered_body = finding_filtered.json()
    assert finding_filtered_body["filters"]["finding_id"] == "finding-1"
    assert len(finding_filtered_body["findings"]) == 1
    assert all((row.get("finding_id") or row.get("id")) == "finding-1" for row in finding_filtered_body["findings"])
    assert all(str(row.get("linked_finding_id") or "") == "finding-1" for row in finding_filtered_body["comments"])

    event_type_filtered = client.get(
        f"/status/{job_id}/review/workflow",
        params={"event_type": "review_comment_status_changed"},
    )
    assert event_type_filtered.status_code == 200
    event_type_filtered_body = event_type_filtered.json()
    assert event_type_filtered_body["filters"]["event_type"] == "review_comment_status_changed"
    assert event_type_filtered_body["timeline"]
    assert all(row["type"] == "review_comment_status_changed" for row in event_type_filtered_body["timeline"])

    comment_status_filtered = client.get(
        f"/status/{job_id}/review/workflow",
        params={"comment_status": "resolved"},
    )
    assert comment_status_filtered.status_code == 200
    comment_status_filtered_body = comment_status_filtered.json()
    assert comment_status_filtered_body["filters"]["comment_status"] == "resolved"
    assert len(comment_status_filtered_body["comments"]) == 1
    assert all(str(row.get("status") or "") == "resolved" for row in comment_status_filtered_body["comments"])


def test_status_review_workflow_export_supports_csv_json_and_gzip():
    job_id = "review-workflow-export-job-1"
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "state": {
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "finding-export-1",
                            "code": "TOC_SCHEMA_INVALID",
                            "severity": "high",
                            "section": "toc",
                            "status": "open",
                            "message": "ToC schema mismatch.",
                        }
                    ]
                }
            },
            "review_comments": [
                {
                    "comment_id": "comment-export-1",
                    "ts": "2026-02-27T11:00:00+00:00",
                    "section": "toc",
                    "status": "open",
                    "message": "Need update before submission.",
                    "linked_finding_id": "finding-export-1",
                }
            ],
            "job_events": [
                {
                    "event_id": "rwf-exp-1",
                    "ts": "2026-02-27T11:00:00+00:00",
                    "type": "review_comment_added",
                    "comment_id": "comment-export-1",
                    "section": "toc",
                },
                {
                    "event_id": "rwf-exp-2",
                    "ts": "2026-02-27T11:01:00+00:00",
                    "type": "critic_finding_status_changed",
                    "finding_id": "finding-export-1",
                    "status": "acknowledged",
                    "section": "toc",
                    "severity": "high",
                },
            ],
        },
    )

    csv_resp = client.get(
        f"/status/{job_id}/review/workflow/export",
        params={"finding_id": "finding-export-1", "comment_status": "open", "format": "csv"},
    )
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    csv_disposition = csv_resp.headers.get("content-disposition", "")
    assert f"grantflow_review_workflow_{job_id}.csv" in csv_disposition
    csv_text = csv_resp.text
    assert csv_text.startswith("field,value\n")
    assert "filters.finding_id,finding-export-1" in csv_text
    assert "filters.comment_status,open" in csv_text
    assert "summary.finding_count,1" in csv_text

    json_resp = client.get(
        f"/status/{job_id}/review/workflow/export",
        params={"event_type": "critic_finding_status_changed", "format": "json"},
    )
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")
    json_payload = json_resp.json()
    assert json_payload["filters"]["event_type"] == "critic_finding_status_changed"
    assert json_payload["timeline"]
    assert all(row["type"] == "critic_finding_status_changed" for row in json_payload["timeline"])

    gzip_resp = client.get(
        f"/status/{job_id}/review/workflow/export",
        params={"finding_id": "finding-export-1", "format": "json", "gzip": "true"},
    )
    assert gzip_resp.status_code == 200
    assert gzip_resp.headers["content-type"].startswith("application/gzip")
    gzip_disposition = gzip_resp.headers.get("content-disposition", "")
    assert f"grantflow_review_workflow_{job_id}.json.gz" in gzip_disposition
    gzip_payload = json.loads(gzip.decompress(gzip_resp.content).decode("utf-8"))
    assert gzip_payload["filters"]["finding_id"] == "finding-export-1"


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


def test_quality_summary_endpoint_aggregates_quality_signals():
    job_id = "quality-job-1"
    api_app_module.INGEST_AUDIT_STORE.clear()
    api_app_module.INGEST_AUDIT_STORE.append(
        {
            "event_id": "ing-q-1",
            "ts": "2026-02-24T09:55:00+00:00",
            "donor_id": "usaid",
            "namespace": "usaid_ads201",
            "filename": "ads-guidance.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "donor_policy", "source_type": "donor_guidance"},
            "result": {"chunks_ingested": 10},
        }
    )
    api_app_module.INGEST_AUDIT_STORE.append(
        {
            "event_id": "ing-q-2",
            "ts": "2026-02-24T09:56:00+00:00",
            "donor_id": "usaid",
            "namespace": "usaid_ads201",
            "filename": "kz-context.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "country_context", "source_type": "country_context"},
            "result": {"chunks_ingested": 8},
        }
    )
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "strict_preflight": True,
            "generate_preflight": {
                "donor_id": "usaid",
                "risk_level": "medium",
                "go_ahead": True,
                "warning_count": 1,
                "warnings": [{"code": "LOW_DOC_COVERAGE", "severity": "medium"}],
            },
            "client_metadata": {
                "demo_generate_preset_key": "usaid_gov_ai_kazakhstan",
                "rag_readiness": {
                    "expected_doc_families": [
                        "donor_policy",
                        "responsible_ai_guidance",
                        "country_context",
                    ],
                    "donor_id": "usaid",
                },
            },
            "state": {
                "donor_id": "usaid",
                "quality_score": 9.1,
                "critic_score": 8.9,
                "needs_revision": False,
                "toc_validation": {"valid": True, "schema_name": "USAID_TOC"},
                "toc_generation_meta": {
                    "engine": "fallback:contract_synthesizer",
                    "llm_used": False,
                    "retrieval_used": True,
                    "citation_policy": {"threshold_mode": "donor_section"},
                },
                "architect_retrieval": {"enabled": True, "hits_count": 3, "namespace": "usaid_ads201"},
                "critic_notes": {
                    "engine": "rules",
                    "rule_score": 8.9,
                    "llm_score": None,
                    "rule_checks": [
                        {"code": "TOC_SCHEMA_VALID", "status": "pass", "section": "toc"},
                        {"code": "TOC_CLAIM_CITATIONS", "status": "warn", "section": "toc"},
                        {"code": "LOGFRAME_CITATIONS_PRESENT", "status": "fail", "section": "logframe"},
                    ],
                    "fatal_flaws": [
                        {
                            "finding_id": "f1",
                            "status": "open",
                            "severity": "high",
                            "section": "toc",
                            "code": "X",
                            "message": "m",
                        },
                        {
                            "finding_id": "f2",
                            "status": "acknowledged",
                            "severity": "medium",
                            "section": "logframe",
                            "code": "Y",
                            "message": "m",
                            "source": "llm",
                            "label": "BASELINE_TARGET_MISSING",
                        },
                        {
                            "finding_id": "f3",
                            "status": "resolved",
                            "severity": "low",
                            "section": "toc",
                            "code": "Z",
                            "message": "m",
                        },
                    ],
                },
                "citations": [
                    {
                        "stage": "architect",
                        "citation_type": "rag_claim_support",
                        "citation_confidence": 0.81,
                        "confidence_threshold": 0.42,
                    },
                    {
                        "stage": "architect",
                        "citation_type": "rag_low_confidence",
                        "citation_confidence": 0.22,
                        "confidence_threshold": 0.42,
                    },
                    {
                        "stage": "architect",
                        "citation_type": "fallback_namespace",
                        "citation_confidence": 0.1,
                        "confidence_threshold": 0.42,
                    },
                    {"stage": "mel", "citation_type": "rag_result", "citation_confidence": 0.73},
                ],
            },
            "job_events": [
                {
                    "event_id": "q1",
                    "ts": "2026-02-24T10:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "q2",
                    "ts": "2026-02-24T10:00:05+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "q3",
                    "ts": "2026-02-24T10:01:00+00:00",
                    "type": "status_changed",
                    "to_status": "done",
                    "status": "done",
                },
            ],
        },
    )

    response = client.get(f"/status/{job_id}/quality")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"
    assert body["quality_score"] == 9.1
    assert body["critic_score"] == 8.9
    assert body["needs_revision"] is False
    assert body["strict_preflight"] is True
    assert body["terminal_status"] == "done"
    assert body["critic"]["fatal_flaw_count"] == 3
    assert body["critic"]["open_finding_count"] == 1
    assert body["critic"]["acknowledged_finding_count"] == 1
    assert body["critic"]["resolved_finding_count"] == 1
    assert body["critic"]["high_severity_fatal_flaw_count"] == 1
    assert body["critic"]["failed_rule_check_count"] == 1
    assert body["critic"]["warned_rule_check_count"] == 1
    assert body["critic"]["llm_finding_label_counts"]["BASELINE_TARGET_MISSING"] == 1
    assert body["citations"]["citation_count"] == 4
    assert body["citations"]["architect_citation_count"] == 3
    assert body["citations"]["mel_citation_count"] == 1
    assert body["citations"]["high_confidence_citation_count"] == 2
    assert body["citations"]["low_confidence_citation_count"] == 2
    assert body["citations"]["architect_rag_low_confidence_citation_count"] == 1
    assert body["citations"]["mel_rag_low_confidence_citation_count"] == 0
    assert body["citations"]["rag_low_confidence_citation_count"] == 1
    assert body["citations"]["fallback_namespace_citation_count"] == 1
    assert body["citations"]["fallback_namespace_citation_rate"] == 0.25
    assert body["citations"]["grounding_risk_level"] == "low"
    assert body["citations"]["traceability_complete_citation_count"] == 0
    assert body["citations"]["traceability_partial_citation_count"] == 0
    assert body["citations"]["traceability_missing_citation_count"] == 4
    assert body["citations"]["traceability_gap_citation_count"] == 4
    assert body["citations"]["traceability_gap_citation_rate"] == 1.0
    assert body["citations"]["architect_threshold_hit_rate"] == 0.3333
    assert body["architect"]["retrieval_enabled"] is True
    assert body["architect"]["retrieval_hits_count"] == 3
    assert body["architect"]["toc_schema_valid"] is True
    assert body["architect"]["citation_policy"]["threshold_mode"] == "donor_section"
    assert body["preflight"]["risk_level"] == "medium"
    assert body["preflight"]["warning_count"] == 1
    assert body["preflight"]["warnings"][0]["code"] == "LOW_DOC_COVERAGE"
    assert body["readiness"]["preset_key"] == "usaid_gov_ai_kazakhstan"
    assert body["readiness"]["donor_id"] == "usaid"
    assert body["readiness"]["expected_doc_families"] == [
        "donor_policy",
        "responsible_ai_guidance",
        "country_context",
    ]
    assert body["readiness"]["present_doc_families"] == ["donor_policy", "country_context"]
    assert body["readiness"]["missing_doc_families"] == ["responsible_ai_guidance"]
    assert body["readiness"]["expected_count"] == 3
    assert body["readiness"]["loaded_count"] == 2
    assert body["readiness"]["coverage_rate"] == 0.6667
    assert body["readiness"]["inventory_total_uploads"] == 2
    assert body["readiness"]["inventory_family_count"] == 2


def test_quality_summary_readiness_emits_namespace_empty_and_low_coverage_warnings():
    job_id = "quality-job-readiness-warn"
    api_app_module.INGEST_AUDIT_STORE.clear()
    api_app_module.JOB_STORE.set(
        job_id,
        {
            "status": "done",
            "client_metadata": {
                "demo_generate_preset_key": "usaid_gov_ai_kazakhstan",
                "rag_readiness": {
                    "expected_doc_families": [
                        "donor_policy",
                        "responsible_ai_guidance",
                        "country_context",
                    ],
                    "donor_id": "usaid",
                },
            },
            "state": {
                "donor_id": "usaid",
                "quality_score": 8.0,
                "critic_score": 8.0,
                "needs_revision": False,
                "toc_validation": {"valid": True, "schema_name": "USAID_TOC"},
                "toc_generation_meta": {"engine": "fallback:contract_synthesizer"},
                "architect_retrieval": {"enabled": True, "hits_count": 0, "namespace": "usaid_ads201"},
                "critic_notes": {"fatal_flaws": [], "rule_checks": []},
                "citations": [],
            },
            "job_events": [
                {
                    "event_id": "rw1",
                    "ts": "2026-02-24T10:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                    "status": "accepted",
                },
                {
                    "event_id": "rw2",
                    "ts": "2026-02-24T10:00:05+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                    "status": "running",
                },
                {
                    "event_id": "rw3",
                    "ts": "2026-02-24T10:01:00+00:00",
                    "type": "status_changed",
                    "to_status": "done",
                    "status": "done",
                },
            ],
        },
    )

    response = client.get(f"/status/{job_id}/quality")
    assert response.status_code == 200
    body = response.json()
    readiness = body.get("readiness") or {}
    assert readiness["namespace_empty"] is True
    assert readiness["low_doc_coverage"] is True
    assert readiness["architect_retrieval_enabled"] is True
    assert readiness["architect_retrieval_hits_count"] == 0
    assert readiness["retrieval_namespace"] == "usaid_ads201"
    assert readiness["warning_count"] >= 2
    assert readiness["warning_level"] in {"high", "medium"}
    warning_codes = {str(row.get("code") or "") for row in (readiness.get("warnings") or []) if isinstance(row, dict)}
    assert "NAMESPACE_EMPTY" in warning_codes
    assert "LOW_DOC_COVERAGE" in warning_codes
    assert "ARCHITECT_RETRIEVAL_NO_HITS" in warning_codes


def test_portfolio_metrics_endpoint_aggregates_jobs_and_filters():
    api_app_module.JOB_STORE.set(
        "portfolio-job-1",
        {
            "status": "done",
            "hitl_enabled": True,
            "generate_preflight": {"warning_level": "medium", "risk_level": "medium"},
            "state": {
                "donor_id": "usaid",
                "citations": [
                    {"citation_type": "fallback_namespace"},
                    {"citation_type": "fallback_namespace"},
                    {"citation_type": "fallback_namespace"},
                ],
            },
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
            "generate_preflight": {"warning_level": "high", "risk_level": "high"},
            "state": {
                "donor_id": "eu",
                "citations": [
                    {"citation_type": "rag_source"},
                    {"citation_type": "rag_source"},
                    {"citation_type": "rag_source"},
                    {"citation_type": "rag_source"},
                ],
            },
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
    assert body["warning_level_counts"]["medium"] >= 1
    assert body["warning_level_counts"]["high"] >= 1
    assert body["warning_level_job_counts"]["high"] >= 1
    assert body["warning_level_job_counts"]["medium"] >= 1
    assert "low" in body["warning_level_job_counts"]
    assert "none" in body["warning_level_job_counts"]
    assert sum(int(v or 0) for v in body["warning_level_job_counts"].values()) == body["job_count"]
    assert body["warning_level_job_rates"]["high"] is not None
    assert body["warning_level_job_rates"]["medium"] is not None
    assert body["warning_level_job_rates"]["low"] is not None
    assert body["warning_level_job_rates"]["none"] is not None
    assert body["grounding_risk_counts"]["high"] >= 1
    assert body["grounding_risk_counts"]["low"] >= 1
    assert body["grounding_risk_job_counts"]["high"] >= 1
    assert body["grounding_risk_job_counts"]["low"] >= 1
    assert body["grounding_risk_job_counts"]["unknown"] >= 0
    assert sum(int(v or 0) for v in body["grounding_risk_job_counts"].values()) == body["job_count"]
    assert body["grounding_risk_job_rates"]["high"] is not None
    assert body["grounding_risk_job_rates"]["medium"] is not None
    assert body["grounding_risk_job_rates"]["low"] is not None
    assert body["grounding_risk_job_rates"]["unknown"] is not None
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
    assert filtered_body["warning_level_counts"]["medium"] >= 1
    assert filtered_body["warning_level_job_counts"]["medium"] >= 1

    warning_filtered = client.get("/portfolio/metrics", params={"warning_level": "high"})
    assert warning_filtered.status_code == 200
    warning_filtered_body = warning_filtered.json()
    assert warning_filtered_body["filters"]["warning_level"] == "high"
    assert warning_filtered_body["job_count"] >= 1
    assert warning_filtered_body["warning_level_counts"] == {"high": warning_filtered_body["job_count"]}
    assert warning_filtered_body["warning_level_job_counts"]["high"] == warning_filtered_body["job_count"]
    assert warning_filtered_body["warning_level_job_counts"]["medium"] == 0

    grounding_filtered = client.get("/portfolio/metrics", params={"grounding_risk_level": "high"})
    assert grounding_filtered.status_code == 200
    grounding_filtered_body = grounding_filtered.json()
    assert grounding_filtered_body["filters"]["grounding_risk_level"] == "high"
    assert grounding_filtered_body["job_count"] >= 1
    assert grounding_filtered_body["grounding_risk_counts"] == {"high": grounding_filtered_body["job_count"]}
    assert grounding_filtered_body["grounding_risk_job_counts"]["high"] == grounding_filtered_body["job_count"]
    assert grounding_filtered_body["grounding_risk_job_counts"]["low"] == 0


def test_portfolio_quality_endpoint_aggregates_quality_signals():
    api_app_module.JOB_STORE.set(
        "portfolio-quality-job-1",
        {
            "status": "done",
            "hitl_enabled": True,
            "generate_preflight": {"warning_level": "medium", "risk_level": "medium"},
            "state": {
                "donor_id": "usaid",
                "quality_score": 8.5,
                "critic_score": 8.0,
                "needs_revision": True,
                "toc_validation": {"valid": True, "schema_name": "UsaidTocSchema"},
                "toc_generation_meta": {
                    "engine": "fallback:contract_synthesizer",
                    "citation_policy": {"threshold_mode": "donor_section"},
                },
                "architect_retrieval": {"enabled": True, "hits_count": 2, "namespace": "usaid_ads201"},
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "f1",
                            "severity": "high",
                            "status": "open",
                            "section": "toc",
                            "code": "CAUSAL_LINK_DETAIL",
                            "message": "Causal links are underspecified for core pathway.",
                            "source": "llm",
                            "label": "CAUSAL_LINK_DETAIL",
                        },
                        {
                            "finding_id": "f2",
                            "severity": "low",
                            "status": "resolved",
                            "section": "general",
                            "code": "GENERAL_NOTE",
                            "message": "Minor editorial improvement.",
                        },
                    ],
                    "rule_checks": [
                        {"code": "toc.complete", "status": "fail"},
                        {"code": "toc.assumptions", "status": "warn"},
                    ],
                    "llm_advisory_diagnostics": {
                        "advisory_applies": True,
                        "advisory_candidate_count": 1,
                        "candidate_label_counts": {"CAUSAL_LINK_DETAIL": 1},
                    },
                },
                "citations": [
                    {
                        "stage": "architect",
                        "citation_type": "rag_claim_support",
                        "citation_confidence": 0.9,
                        "confidence_threshold": 0.7,
                    },
                    {
                        "stage": "architect",
                        "citation_type": "rag_low_confidence",
                        "citation_confidence": 0.2,
                        "confidence_threshold": 0.5,
                    },
                    {"stage": "mel", "citation_type": "rag_support", "citation_confidence": 0.6},
                ],
            },
            "job_events": [
                {
                    "event_id": "qa1",
                    "ts": "2026-02-24T10:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                },
                {
                    "event_id": "qa2",
                    "ts": "2026-02-24T10:00:05+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                },
                {
                    "event_id": "qa3",
                    "ts": "2026-02-24T10:00:20+00:00",
                    "type": "status_changed",
                    "to_status": "pending_hitl",
                },
                {"event_id": "qa4", "ts": "2026-02-24T10:01:20+00:00", "type": "resume_requested"},
                {"event_id": "qa5", "ts": "2026-02-24T10:01:30+00:00", "type": "status_changed", "to_status": "done"},
            ],
        },
    )
    api_app_module.JOB_STORE.set(
        "portfolio-quality-job-2",
        {
            "status": "done",
            "hitl_enabled": True,
            "generate_preflight": {"warning_level": "low", "risk_level": "low"},
            "state": {
                "donor_id": "usaid",
                "quality_score": 6.5,
                "critic_score": 6.0,
                "needs_revision": False,
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "f3",
                            "severity": "medium",
                            "status": "acknowledged",
                            "section": "logframe",
                            "code": "BASELINE_TARGET_MISSING",
                            "message": "Indicators are missing complete baseline and target fields.",
                            "source": "llm",
                            "label": "BASELINE_TARGET_MISSING",
                        }
                    ],
                    "rule_checks": [{"code": "logframe.complete", "status": "pass"}],
                    "llm_advisory_diagnostics": {
                        "advisory_applies": False,
                        "advisory_candidate_count": 1,
                        "advisory_rejected_reason": "grounding_threshold_not_met",
                        "candidate_label_counts": {"BASELINE_TARGET_MISSING": 1},
                    },
                },
                "citations": [
                    {
                        "stage": "architect",
                        "citation_type": "rag_claim_support",
                        "citation_confidence": 0.8,
                        "confidence_threshold": 0.7,
                    }
                ],
            },
            "job_events": [
                {
                    "event_id": "qb1",
                    "ts": "2026-02-24T11:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                },
                {
                    "event_id": "qb2",
                    "ts": "2026-02-24T11:00:03+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                },
                {"event_id": "qb3", "ts": "2026-02-24T11:00:25+00:00", "type": "status_changed", "to_status": "done"},
            ],
        },
    )
    api_app_module.JOB_STORE.set(
        "portfolio-quality-job-3",
        {
            "status": "error",
            "hitl_enabled": False,
            "generate_preflight": {"warning_level": "high", "risk_level": "high"},
            "state": {"donor_id": "eu", "quality_score": 4.0, "critic_score": 3.0, "needs_revision": True},
            "job_events": [
                {
                    "event_id": "qc1",
                    "ts": "2026-02-24T12:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                },
                {
                    "event_id": "qc2",
                    "ts": "2026-02-24T12:00:02+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                },
                {"event_id": "qc3", "ts": "2026-02-24T12:00:10+00:00", "type": "status_changed", "to_status": "error"},
            ],
        },
    )
    api_app_module.JOB_STORE.set(
        "portfolio-quality-job-4",
        {
            "status": "done",
            "hitl_enabled": True,
            "generate_preflight": {"warning_level": "medium", "risk_level": "medium"},
            "state": {
                "donor_id": "usaid",
                "quality_score": 6.0,
                "critic_score": 5.5,
                "needs_revision": True,
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "f4",
                            "severity": "medium",
                            "status": "open",
                            "section": "toc",
                            "code": "GROUNDING_WEAK",
                            "message": "Grounding evidence is mostly fallback.",
                        }
                    ],
                    "rule_checks": [{"code": "toc.grounding", "status": "warn"}],
                },
                "citations": [
                    {"stage": "architect", "citation_type": "fallback_namespace", "citation_confidence": 0.2},
                    {"stage": "mel", "citation_type": "fallback_namespace", "citation_confidence": 0.2},
                ],
            },
            "job_events": [
                {"event_id": "qd1", "ts": "2026-02-24T13:00:00+00:00", "type": "status_changed", "to_status": "done"}
            ],
        },
    )

    response = client.get("/portfolio/quality", params={"donor_id": "usaid", "status": "done", "hitl_enabled": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["donor_id"] == "usaid"
    assert body["filters"]["status"] == "done"
    assert body["filters"]["hitl_enabled"] is True
    assert body["filters"].get("finding_status") is None
    assert body["filters"].get("finding_severity") is None
    assert body["warning_level_counts"]["medium"] >= 1
    assert body["warning_level_counts"]["low"] >= 1
    assert body["warning_level_high_job_count"] >= 0
    assert body["warning_level_medium_job_count"] >= 1
    assert body["warning_level_low_job_count"] >= 1
    assert body["warning_level_none_job_count"] >= 0
    assert body["warning_level_high_rate"] is not None
    assert body["warning_level_medium_rate"] is not None
    assert body["warning_level_low_rate"] is not None
    assert body["warning_level_none_rate"] is not None
    assert body["warning_level_job_counts"]["high"] >= 0
    assert body["warning_level_job_counts"]["medium"] >= 1
    assert body["warning_level_job_counts"]["low"] >= 1
    assert body["warning_level_job_counts"]["none"] >= 0
    assert sum(int(v or 0) for v in body["warning_level_job_counts"].values()) == body["job_count"]
    assert body["warning_level_job_rates"]["medium"] is not None
    assert body["warning_level_job_rates"]["low"] is not None
    assert body["grounding_risk_counts"]["high"] >= 1
    assert body["grounding_risk_counts"]["low"] >= 1
    assert body["grounding_risk_job_counts"]["high"] >= 1
    assert body["grounding_risk_job_counts"]["low"] >= 1
    assert sum(int(v or 0) for v in body["grounding_risk_job_counts"].values()) == body["job_count"]
    assert body["grounding_risk_job_rates"]["high"] is not None
    assert body["donor_grounding_risk_counts"]["high"] >= 0
    assert body["donor_grounding_risk_counts"]["medium"] >= 0
    assert body["donor_grounding_risk_counts"]["low"] >= 0
    assert body["donor_grounding_risk_counts"]["unknown"] >= 0
    assert body["high_grounding_risk_donor_count"] >= 0
    assert body["medium_grounding_risk_donor_count"] >= 0
    assert body["job_count"] >= 2
    assert body["avg_quality_score"] is not None
    assert body["avg_critic_score"] is not None
    assert body["severity_weighted_risk_score"] >= 1
    assert body["high_priority_signal_count"] >= 1
    assert body["critic"]["open_findings_total"] >= 1
    assert body["critic"]["high_severity_findings_total"] >= 1
    assert body["critic"]["needs_revision_job_count"] >= 1
    assert body["critic"]["needs_revision_rate"] is not None
    assert body["critic"]["llm_finding_label_counts"]["CAUSAL_LINK_DETAIL"] >= 1
    assert body["critic"]["llm_finding_label_counts"]["BASELINE_TARGET_MISSING"] >= 1
    assert body["critic"]["llm_advisory_diagnostics_job_count"] >= 2
    assert body["critic"]["llm_advisory_applied_job_count"] >= 1
    assert body["critic"]["llm_advisory_applied_rate"] is not None
    assert body["critic"]["llm_advisory_candidate_finding_count"] >= 2
    assert body["critic"]["llm_advisory_rejected_reason_counts"]["grounding_threshold_not_met"] >= 1
    assert body["citations"]["citation_count_total"] >= 4
    assert body["citations"]["citation_confidence_avg"] is not None
    assert body["citations"]["low_confidence_citation_count"] >= 1
    assert body["citations"]["architect_rag_low_confidence_citation_count"] >= 1
    assert "mel_rag_low_confidence_citation_count" in body["citations"]
    assert body["citations"]["rag_low_confidence_citation_count"] >= 1
    assert "architect_rag_low_confidence_citation_rate" in body["citations"]
    assert "mel_rag_low_confidence_citation_rate" in body["citations"]
    assert "fallback_namespace_citation_count" in body["citations"]
    assert "fallback_namespace_citation_rate" in body["citations"]
    assert body["citations"]["grounding_risk_level"] in {"high", "medium", "low", "unknown"}
    assert "traceability_gap_citation_count" in body["citations"]
    assert "traceability_gap_citation_rate" in body["citations"]
    assert body["citations"]["architect_threshold_hit_rate_avg"] is not None
    assert body["priority_signal_breakdown"]["high_severity_findings_total"]["weight"] >= 1
    assert body["priority_signal_breakdown"]["open_findings_total"]["weighted_score"] >= 1
    assert body["donor_weighted_risk_breakdown"]["usaid"]["weighted_score"] >= 1
    assert body["donor_weighted_risk_breakdown"]["usaid"]["high_priority_signal_count"] >= 1
    assert "architect_rag_low_confidence_citation_count" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "mel_rag_low_confidence_citation_count" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "traceability_gap_citation_count" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "llm_finding_label_counts" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "citation_count_total" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "fallback_namespace_citation_rate" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert body["donor_weighted_risk_breakdown"]["usaid"]["grounding_risk_level"] in {
        "high",
        "medium",
        "low",
        "unknown",
    }
    assert body["donor_weighted_risk_breakdown"]["usaid"]["llm_finding_label_counts"]["CAUSAL_LINK_DETAIL"] >= 1
    assert "llm_advisory_rejected_reason_counts" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "llm_advisory_applied_label_counts" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert "llm_advisory_rejected_label_counts" in body["donor_weighted_risk_breakdown"]["usaid"]
    assert body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_diagnostics_job_count"] >= 2
    assert body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_applied_job_count"] >= 1
    assert body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_applied_rate"] is not None
    assert body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_candidate_finding_count"] >= 2
    assert (
        body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_applied_label_counts"]["CAUSAL_LINK_DETAIL"] >= 1
    )
    assert (
        body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_rejected_label_counts"]["BASELINE_TARGET_MISSING"]
        >= 1
    )
    assert (
        body["donor_weighted_risk_breakdown"]["usaid"]["llm_advisory_rejected_reason_counts"][
            "grounding_threshold_not_met"
        ]
        >= 1
    )
    assert "usaid" in body["donor_grounding_risk_breakdown"]
    assert body["donor_grounding_risk_breakdown"]["usaid"]["citation_count_total"] >= 1
    assert body["donor_grounding_risk_breakdown"]["usaid"]["fallback_namespace_citation_count"] >= 0
    if body["donor_grounding_risk_breakdown"]["usaid"]["citation_count_total"] > 0:
        assert body["donor_grounding_risk_breakdown"]["usaid"]["fallback_namespace_citation_rate"] is not None
    assert body["donor_grounding_risk_breakdown"]["usaid"]["grounding_risk_level"] in {
        "high",
        "medium",
        "low",
        "unknown",
    }
    assert body["donor_needs_revision_counts"]["usaid"] >= 1
    assert body["donor_open_findings_counts"]["usaid"] >= 1
    assert body["finding_status_counts"]["open"] >= 1
    assert body["finding_status_counts"]["acknowledged"] >= 0
    assert body["finding_status_counts"]["resolved"] >= 0
    assert body["finding_severity_counts"]["high"] >= 1
    assert body["finding_severity_counts"]["medium"] >= 1
    assert body["finding_severity_counts"]["low"] >= 0
    assert "eu" not in body["donor_counts"]

    warning_filtered = client.get("/portfolio/quality", params={"warning_level": "high"})
    assert warning_filtered.status_code == 200
    warning_filtered_body = warning_filtered.json()
    assert warning_filtered_body["filters"]["warning_level"] == "high"
    assert warning_filtered_body["job_count"] >= 1
    assert warning_filtered_body["warning_level_counts"] == {"high": warning_filtered_body["job_count"]}
    assert warning_filtered_body["warning_level_job_counts"]["high"] == warning_filtered_body["job_count"]
    assert warning_filtered_body["warning_level_job_counts"]["none"] == 0

    grounding_filtered = client.get("/portfolio/quality", params={"grounding_risk_level": "high"})
    assert grounding_filtered.status_code == 200
    grounding_filtered_body = grounding_filtered.json()
    assert grounding_filtered_body["filters"]["grounding_risk_level"] == "high"
    assert grounding_filtered_body["job_count"] >= 1
    assert grounding_filtered_body["grounding_risk_job_counts"]["high"] == grounding_filtered_body["job_count"]
    assert grounding_filtered_body["grounding_risk_job_counts"]["medium"] == 0
    assert grounding_filtered_body["grounding_risk_job_counts"]["low"] == 0

    finding_status_filtered = client.get("/portfolio/quality", params={"finding_status": "acknowledged"})
    assert finding_status_filtered.status_code == 200
    finding_status_filtered_body = finding_status_filtered.json()
    assert finding_status_filtered_body["filters"]["finding_status"] == "acknowledged"
    assert finding_status_filtered_body["job_count"] >= 1
    assert finding_status_filtered_body["finding_status_counts"]["acknowledged"] >= 1

    finding_severity_filtered = client.get("/portfolio/quality", params={"finding_severity": "high"})
    assert finding_severity_filtered.status_code == 200
    finding_severity_filtered_body = finding_severity_filtered.json()
    assert finding_severity_filtered_body["filters"]["finding_severity"] == "high"
    assert finding_severity_filtered_body["job_count"] >= 1
    assert finding_severity_filtered_body["finding_severity_counts"]["high"] >= 1


def test_portfolio_quality_export_endpoint_returns_csv():
    response = client.get(
        "/portfolio/quality/export",
        params={
            "donor_id": "usaid",
            "status": "done",
            "grounding_risk_level": "high",
            "finding_status": "open",
            "finding_severity": "high",
            "format": "csv",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers.get("content-disposition", "")
    assert "attachment;" in disposition
    assert "grantflow_portfolio_quality_usaid_done" in disposition

    body = response.text
    assert body.startswith("field,value\n")
    assert "filters.donor_id,usaid" in body
    assert "filters.status,done" in body
    assert "filters.grounding_risk_level,high" in body
    assert "filters.finding_status,open" in body
    assert "filters.finding_severity,high" in body
    assert "severity_weighted_risk_score," in body
    assert "priority_signal_breakdown.high_severity_findings_total.weight," in body


def test_portfolio_quality_export_csv_flattens_donor_advisory_label_mix():
    api_app_module.JOB_STORE.set(
        "portfolio-quality-export-job-seeded",
        {
            "status": "done",
            "hitl_enabled": True,
            "state": {
                "donor_id": "usaid",
                "quality_score": 8.0,
                "critic_score": 7.5,
                "needs_revision": False,
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "seed-f1",
                            "severity": "medium",
                            "status": "open",
                            "section": "toc",
                            "source": "llm",
                            "label": "CAUSAL_LINK_DETAIL",
                        }
                    ],
                    "llm_advisory_diagnostics": {
                        "advisory_applies": False,
                        "advisory_candidate_count": 2,
                        "advisory_rejected_reason": "grounding_threshold_not_met",
                        "candidate_label_counts": {
                            "CAUSAL_LINK_DETAIL": 1,
                            "BASELINE_TARGET_MISSING": 1,
                        },
                    },
                },
                "citations": [
                    {"stage": "architect", "citation_type": "rag_low_confidence", "citation_confidence": 0.2},
                    {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.9},
                ],
            },
            "job_events": [
                {
                    "event_id": "pqx1",
                    "ts": "2026-02-24T12:00:00+00:00",
                    "type": "status_changed",
                    "to_status": "accepted",
                },
                {
                    "event_id": "pqx2",
                    "ts": "2026-02-24T12:00:01+00:00",
                    "type": "status_changed",
                    "to_status": "running",
                },
                {"event_id": "pqx3", "ts": "2026-02-24T12:00:10+00:00", "type": "status_changed", "to_status": "done"},
            ],
        },
    )

    response = client.get("/portfolio/quality/export", params={"donor_id": "usaid", "status": "done", "format": "csv"})
    assert response.status_code == 200
    body = response.text
    assert "donor_weighted_risk_breakdown.usaid.llm_advisory_rejected_label_counts.CAUSAL_LINK_DETAIL," in body
    assert "donor_weighted_risk_breakdown.usaid.llm_advisory_rejected_label_counts.BASELINE_TARGET_MISSING," in body


def test_portfolio_quality_export_endpoint_supports_json_and_gzip():
    json_resp = client.get("/portfolio/quality/export", params={"donor_id": "usaid", "format": "json"})
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")
    json_disposition = json_resp.headers.get("content-disposition", "")
    assert "grantflow_portfolio_quality_usaid.json" in json_disposition
    payload = json_resp.json()
    assert "severity_weighted_risk_score" in payload
    assert "priority_signal_breakdown" in payload

    csv_gzip_resp = client.get(
        "/portfolio/quality/export", params={"donor_id": "usaid", "format": "csv", "gzip": "true"}
    )
    assert csv_gzip_resp.status_code == 200
    assert csv_gzip_resp.headers["content-type"].startswith("application/gzip")
    csv_gzip_disposition = csv_gzip_resp.headers.get("content-disposition", "")
    assert "grantflow_portfolio_quality_usaid.csv.gz" in csv_gzip_disposition
    csv_text = gzip.decompress(csv_gzip_resp.content).decode("utf-8")
    assert csv_text.startswith("field,value\n")
    assert "severity_weighted_risk_score," in csv_text

    json_gzip_resp = client.get(
        "/portfolio/quality/export", params={"donor_id": "usaid", "format": "json", "gzip": "true"}
    )
    assert json_gzip_resp.status_code == 200
    assert json_gzip_resp.headers["content-type"].startswith("application/gzip")
    json_gzip_disposition = json_gzip_resp.headers.get("content-disposition", "")
    assert "grantflow_portfolio_quality_usaid.json.gz" in json_gzip_disposition
    json_text = gzip.decompress(json_gzip_resp.content).decode("utf-8")
    parsed = json.loads(json_text)
    assert "filters" in parsed
    assert parsed["filters"]["donor_id"] == "usaid"


def test_portfolio_metrics_export_endpoint_supports_csv_json_and_gzip():
    csv_resp = client.get(
        "/portfolio/metrics/export",
        params={"donor_id": "usaid", "status": "done", "grounding_risk_level": "high", "format": "csv"},
    )
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    csv_disposition = csv_resp.headers.get("content-disposition", "")
    assert "grantflow_portfolio_metrics_usaid_done.csv" in csv_disposition
    csv_text = csv_resp.text
    assert csv_text.startswith("field,value\n")
    assert "filters.donor_id,usaid" in csv_text
    assert "filters.status,done" in csv_text
    assert "filters.grounding_risk_level,high" in csv_text
    assert "avg_time_to_terminal_seconds," in csv_text

    json_resp = client.get(
        "/portfolio/metrics/export",
        params={"donor_id": "usaid", "grounding_risk_level": "high", "format": "json"},
    )
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")
    json_disposition = json_resp.headers.get("content-disposition", "")
    assert "grantflow_portfolio_metrics_usaid.json" in json_disposition
    payload = json_resp.json()
    assert "job_count" in payload
    assert payload["filters"]["donor_id"] == "usaid"
    assert payload["filters"]["grounding_risk_level"] == "high"

    csv_gzip_resp = client.get(
        "/portfolio/metrics/export", params={"donor_id": "usaid", "format": "csv", "gzip": "true"}
    )
    assert csv_gzip_resp.status_code == 200
    assert csv_gzip_resp.headers["content-type"].startswith("application/gzip")
    assert "grantflow_portfolio_metrics_usaid.csv.gz" in (csv_gzip_resp.headers.get("content-disposition") or "")
    csv_gzip_text = gzip.decompress(csv_gzip_resp.content).decode("utf-8")
    assert "field,value\n" in csv_gzip_text

    json_gzip_resp = client.get(
        "/portfolio/metrics/export", params={"donor_id": "usaid", "format": "json", "gzip": "true"}
    )
    assert json_gzip_resp.status_code == 200
    assert json_gzip_resp.headers["content-type"].startswith("application/gzip")
    assert "grantflow_portfolio_metrics_usaid.json.gz" in (json_gzip_resp.headers.get("content-disposition") or "")
    json_gzip_payload = json.loads(gzip.decompress(json_gzip_resp.content).decode("utf-8"))
    assert json_gzip_payload["filters"]["donor_id"] == "usaid"


def test_ingest_inventory_export_endpoint_supports_csv_json_and_gzip(monkeypatch):
    api_app_module.INGEST_AUDIT_STORE.clear()

    def fake_ingest(pdf_path: str, namespace: str, metadata=None):
        return {"namespace": namespace, "source": pdf_path, "chunks_ingested": 1, "stats": {}}

    monkeypatch.setattr(api_app_module, "ingest_pdf_to_namespace", fake_ingest)

    client.post(
        "/ingest",
        data={
            "donor_id": "usaid",
            "metadata_json": json.dumps({"doc_family": "donor_policy", "source_type": "donor_guidance"}),
        },
        files={"file": ("ads.pdf", b"%PDF-1.4 a", "application/pdf")},
    )
    client.post(
        "/ingest",
        data={
            "donor_id": "usaid",
            "metadata_json": json.dumps({"doc_family": "country_context", "source_type": "country_context"}),
        },
        files={"file": ("kz-context.pdf", b"%PDF-1.4 b", "application/pdf")},
    )

    csv_resp = client.get("/ingest/inventory/export", params={"donor_id": "usaid", "format": "csv"})
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert "grantflow_ingest_inventory_usaid.csv" in (csv_resp.headers.get("content-disposition") or "")
    csv_text = csv_resp.text
    assert csv_text.startswith("field,value\n")
    assert "donor_id,usaid" in csv_text
    assert "doc_family_counts.donor_policy,1" in csv_text
    assert "doc_family_counts.country_context,1" in csv_text

    json_resp = client.get("/ingest/inventory/export", params={"donor_id": "usaid", "format": "json"})
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")
    assert "grantflow_ingest_inventory_usaid.json" in (json_resp.headers.get("content-disposition") or "")
    json_body = json_resp.json()
    assert json_body["donor_id"] == "usaid"
    assert json_body["doc_family_counts"]["donor_policy"] == 1

    csv_gzip_resp = client.get(
        "/ingest/inventory/export", params={"donor_id": "usaid", "format": "csv", "gzip": "true"}
    )
    assert csv_gzip_resp.status_code == 200
    assert csv_gzip_resp.headers["content-type"].startswith("application/gzip")
    assert "grantflow_ingest_inventory_usaid.csv.gz" in (csv_gzip_resp.headers.get("content-disposition") or "")
    csv_gzip_text = gzip.decompress(csv_gzip_resp.content).decode("utf-8")
    assert "doc_family_counts.donor_policy,1" in csv_gzip_text

    json_gzip_resp = client.get(
        "/ingest/inventory/export", params={"donor_id": "usaid", "format": "json", "gzip": "true"}
    )
    assert json_gzip_resp.status_code == 200
    assert json_gzip_resp.headers["content-type"].startswith("application/gzip")
    assert "grantflow_ingest_inventory_usaid.json.gz" in (json_gzip_resp.headers.get("content-disposition") or "")
    json_gzip_body = json.loads(gzip.decompress(json_gzip_resp.content).decode("utf-8"))
    assert json_gzip_body["family_count"] == 2


def test_generate_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("GRANTFLOW_API_KEY", "test-secret")

    preflight_response = client.post("/generate/preflight", json={"donor_id": "usaid"})
    assert preflight_response.status_code == 401

    preflight_response = client.post(
        "/generate/preflight",
        json={"donor_id": "usaid"},
        headers={"X-API-Key": "test-secret"},
    )
    assert preflight_response.status_code == 200
    assert preflight_response.json()["donor_id"] == "usaid"

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

    export_payload_unauth = client.get(f"/status/{job_id}/export-payload")
    assert export_payload_unauth.status_code == 401

    export_payload_auth = client.get(f"/status/{job_id}/export-payload", headers={"X-API-Key": "test-secret"})
    assert export_payload_auth.status_code == 200

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

    quality_unauth = client.get(f"/status/{job_id}/quality")
    assert quality_unauth.status_code == 401

    quality_auth = client.get(f"/status/{job_id}/quality", headers={"X-API-Key": "test-secret"})
    assert quality_auth.status_code == 200

    critic_unauth = client.get(f"/status/{job_id}/critic")
    assert critic_unauth.status_code == 401

    critic_auth = client.get(f"/status/{job_id}/critic", headers={"X-API-Key": "test-secret"})
    assert critic_auth.status_code == 200
    critic_finding_id = None
    if critic_auth.json().get("fatal_flaws"):
        critic_finding_id = critic_auth.json()["fatal_flaws"][0].get("finding_id")

    if critic_finding_id:
        ack_finding_unauth = client.post(f"/status/{job_id}/critic/findings/{critic_finding_id}/ack")
        assert ack_finding_unauth.status_code == 401

        ack_finding_auth = client.post(
            f"/status/{job_id}/critic/findings/{critic_finding_id}/ack",
            headers={"X-API-Key": "test-secret"},
        )
        assert ack_finding_auth.status_code == 200

        resolve_finding_unauth = client.post(f"/status/{job_id}/critic/findings/{critic_finding_id}/resolve")
        assert resolve_finding_unauth.status_code == 401

        resolve_finding_auth = client.post(
            f"/status/{job_id}/critic/findings/{critic_finding_id}/resolve",
            headers={"X-API-Key": "test-secret"},
        )
        assert resolve_finding_auth.status_code == 200

        reopen_finding_unauth = client.post(f"/status/{job_id}/critic/findings/{critic_finding_id}/open")
        assert reopen_finding_unauth.status_code == 401

        reopen_finding_auth = client.post(
            f"/status/{job_id}/critic/findings/{critic_finding_id}/open",
            headers={"X-API-Key": "test-secret"},
        )
        assert reopen_finding_auth.status_code == 200

    comments_unauth = client.get(f"/status/{job_id}/comments")
    assert comments_unauth.status_code == 401

    comments_auth = client.get(f"/status/{job_id}/comments", headers={"X-API-Key": "test-secret"})
    assert comments_auth.status_code == 200

    review_workflow_unauth = client.get(f"/status/{job_id}/review/workflow")
    assert review_workflow_unauth.status_code == 401

    review_workflow_auth = client.get(f"/status/{job_id}/review/workflow", headers={"X-API-Key": "test-secret"})
    assert review_workflow_auth.status_code == 200

    review_workflow_export_unauth = client.get(f"/status/{job_id}/review/workflow/export")
    assert review_workflow_export_unauth.status_code == 401

    review_workflow_export_auth = client.get(
        f"/status/{job_id}/review/workflow/export",
        headers={"X-API-Key": "test-secret"},
    )
    assert review_workflow_export_auth.status_code == 200

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

    portfolio_metrics_export_unauth = client.get("/portfolio/metrics/export")
    assert portfolio_metrics_export_unauth.status_code == 401

    portfolio_metrics_export_auth = client.get("/portfolio/metrics/export", headers={"X-API-Key": "test-secret"})
    assert portfolio_metrics_export_auth.status_code == 200

    portfolio_quality_unauth = client.get("/portfolio/quality")
    assert portfolio_quality_unauth.status_code == 401

    portfolio_quality_auth = client.get("/portfolio/quality", headers={"X-API-Key": "test-secret"})
    assert portfolio_quality_auth.status_code == 200

    portfolio_quality_export_unauth = client.get("/portfolio/quality/export")
    assert portfolio_quality_export_unauth.status_code == 401

    portfolio_quality_export_auth = client.get("/portfolio/quality/export", headers={"X-API-Key": "test-secret"})
    assert portfolio_quality_export_auth.status_code == 200

    ingest_recent_unauth = client.get("/ingest/recent")
    assert ingest_recent_unauth.status_code == 401

    ingest_recent_auth = client.get("/ingest/recent", headers={"X-API-Key": "test-secret"})
    assert ingest_recent_auth.status_code == 200

    ingest_inventory_unauth = client.get("/ingest/inventory")
    assert ingest_inventory_unauth.status_code == 401

    ingest_inventory_auth = client.get("/ingest/inventory", headers={"X-API-Key": "test-secret"})
    assert ingest_inventory_auth.status_code == 200

    ingest_inventory_export_unauth = client.get("/ingest/inventory/export")
    assert ingest_inventory_export_unauth.status_code == 401

    ingest_inventory_export_auth = client.get("/ingest/inventory/export", headers={"X-API-Key": "test-secret"})
    assert ingest_inventory_export_auth.status_code == 200

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
    generate_preflight_security = (((spec.get("paths") or {}).get("/generate/preflight") or {}).get("post") or {}).get(
        "security"
    )
    ingest_security = (((spec.get("paths") or {}).get("/ingest") or {}).get("post") or {}).get("security")
    ingest_recent_security = (((spec.get("paths") or {}).get("/ingest/recent") or {}).get("get") or {}).get("security")
    ingest_inventory_security = (((spec.get("paths") or {}).get("/ingest/inventory") or {}).get("get") or {}).get(
        "security"
    )
    ingest_inventory_export_security = (
        ((spec.get("paths") or {}).get("/ingest/inventory/export") or {}).get("get") or {}
    ).get("security")
    cancel_security = (((spec.get("paths") or {}).get("/cancel/{job_id}") or {}).get("post") or {}).get("security")
    status_security = (((spec.get("paths") or {}).get("/status/{job_id}") or {}).get("get") or {}).get("security")
    status_citations_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/citations") or {}).get("get") or {}
    ).get("security")
    status_export_payload_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/export-payload") or {}).get("get") or {}
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
    status_quality_security = (((spec.get("paths") or {}).get("/status/{job_id}/quality") or {}).get("get") or {}).get(
        "security"
    )
    status_critic_security = (((spec.get("paths") or {}).get("/status/{job_id}/critic") or {}).get("get") or {}).get(
        "security"
    )
    status_critic_finding_ack_security = (
        (((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/ack") or {}).get("post") or {})
    ).get("security")
    status_critic_finding_open_security = (
        (((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/open") or {}).get("post") or {})
    ).get("security")
    status_critic_finding_resolve_security = (
        (
            ((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/resolve") or {}).get("post")
            or {}
        )
    ).get("security")
    status_comments_get_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("get") or {}
    ).get("security")
    status_review_workflow_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/review/workflow") or {}).get("get") or {}
    ).get("security")
    status_review_workflow_export_security = (
        ((spec.get("paths") or {}).get("/status/{job_id}/review/workflow/export") or {}).get("get") or {}
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
    portfolio_metrics_export_security = (
        ((spec.get("paths") or {}).get("/portfolio/metrics/export") or {}).get("get") or {}
    ).get("security")
    portfolio_quality_security = (((spec.get("paths") or {}).get("/portfolio/quality") or {}).get("get") or {}).get(
        "security"
    )
    portfolio_quality_export_security = (
        ((spec.get("paths") or {}).get("/portfolio/quality/export") or {}).get("get") or {}
    ).get("security")
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
    status_export_payload_response_schema = (
        (
            (((spec.get("paths") or {}).get("/status/{job_id}/export-payload") or {}).get("get") or {}).get("responses")
            or {}
        )
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
    status_quality_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/quality") or {}).get("get") or {}).get("responses") or {})
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
    status_critic_finding_ack_response_schema = (
        (
            (
                ((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/ack") or {}).get("post")
                or {}
            ).get("responses")
            or {}
        )
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_critic_finding_open_response_schema = (
        (
            (
                ((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/open") or {}).get("post")
                or {}
            ).get("responses")
            or {}
        )
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_critic_finding_resolve_response_schema = (
        (
            (
                (
                    ((spec.get("paths") or {}).get("/status/{job_id}/critic/findings/{finding_id}/resolve") or {}).get(
                        "post"
                    )
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
    status_comments_response_schema = (
        ((((spec.get("paths") or {}).get("/status/{job_id}/comments") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    status_review_workflow_response_schema = (
        (((spec.get("paths") or {}).get("/status/{job_id}/review/workflow") or {}).get("get") or {})
        .get("responses", {})
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
    portfolio_quality_response_schema = (
        ((((spec.get("paths") or {}).get("/portfolio/quality") or {}).get("get") or {}).get("responses") or {})
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
    ingest_recent_response_schema = (
        ((((spec.get("paths") or {}).get("/ingest/recent") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    ingest_inventory_response_schema = (
        ((((spec.get("paths") or {}).get("/ingest/inventory") or {}).get("get") or {}).get("responses") or {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    assert generate_security == [{"ApiKeyAuth": []}]
    assert generate_preflight_security == [{"ApiKeyAuth": []}]
    assert ingest_security == [{"ApiKeyAuth": []}]
    assert ingest_recent_security == [{"ApiKeyAuth": []}]
    assert ingest_inventory_security == [{"ApiKeyAuth": []}]
    assert ingest_inventory_export_security == [{"ApiKeyAuth": []}]
    assert cancel_security == [{"ApiKeyAuth": []}]
    assert status_security == [{"ApiKeyAuth": []}]
    assert status_citations_security == [{"ApiKeyAuth": []}]
    assert status_export_payload_security == [{"ApiKeyAuth": []}]
    assert status_versions_security == [{"ApiKeyAuth": []}]
    assert status_diff_security == [{"ApiKeyAuth": []}]
    assert status_events_security == [{"ApiKeyAuth": []}]
    assert status_metrics_security == [{"ApiKeyAuth": []}]
    assert status_quality_security == [{"ApiKeyAuth": []}]
    assert status_critic_security == [{"ApiKeyAuth": []}]
    assert status_critic_finding_ack_security == [{"ApiKeyAuth": []}]
    assert status_critic_finding_open_security == [{"ApiKeyAuth": []}]
    assert status_critic_finding_resolve_security == [{"ApiKeyAuth": []}]
    assert status_comments_get_security == [{"ApiKeyAuth": []}]
    assert status_review_workflow_security == [{"ApiKeyAuth": []}]
    assert status_review_workflow_export_security == [{"ApiKeyAuth": []}]
    assert status_comments_post_security == [{"ApiKeyAuth": []}]
    assert status_comments_resolve_security == [{"ApiKeyAuth": []}]
    assert status_comments_reopen_security == [{"ApiKeyAuth": []}]
    assert portfolio_metrics_security == [{"ApiKeyAuth": []}]
    assert portfolio_metrics_export_security == [{"ApiKeyAuth": []}]
    assert portfolio_quality_security == [{"ApiKeyAuth": []}]
    assert portfolio_quality_export_security == [{"ApiKeyAuth": []}]
    assert status_response_schema == {"$ref": "#/components/schemas/JobStatusPublicResponse"}
    assert status_citations_response_schema == {"$ref": "#/components/schemas/JobCitationsPublicResponse"}
    assert status_export_payload_response_schema == {"$ref": "#/components/schemas/JobExportPayloadPublicResponse"}
    assert status_versions_response_schema == {"$ref": "#/components/schemas/JobVersionsPublicResponse"}
    assert status_diff_response_schema == {"$ref": "#/components/schemas/JobDiffPublicResponse"}
    assert status_events_response_schema == {"$ref": "#/components/schemas/JobEventsPublicResponse"}
    assert status_metrics_response_schema == {"$ref": "#/components/schemas/JobMetricsPublicResponse"}
    assert status_quality_response_schema == {"$ref": "#/components/schemas/JobQualitySummaryPublicResponse"}
    assert status_critic_response_schema == {"$ref": "#/components/schemas/JobCriticPublicResponse"}
    assert status_critic_finding_ack_response_schema == {"$ref": "#/components/schemas/CriticFatalFlawPublicResponse"}
    assert status_critic_finding_open_response_schema == {"$ref": "#/components/schemas/CriticFatalFlawPublicResponse"}
    assert status_critic_finding_resolve_response_schema == {
        "$ref": "#/components/schemas/CriticFatalFlawPublicResponse"
    }
    assert status_comments_response_schema == {"$ref": "#/components/schemas/JobCommentsPublicResponse"}
    assert status_review_workflow_response_schema == {"$ref": "#/components/schemas/JobReviewWorkflowPublicResponse"}
    assert status_comments_post_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert status_comments_resolve_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert status_comments_reopen_response_schema == {"$ref": "#/components/schemas/ReviewCommentPublicResponse"}
    assert portfolio_metrics_response_schema == {"$ref": "#/components/schemas/PortfolioMetricsPublicResponse"}
    assert portfolio_quality_response_schema == {"$ref": "#/components/schemas/PortfolioQualityPublicResponse"}
    assert pending_response_schema == {"$ref": "#/components/schemas/HITLPendingListPublicResponse"}
    assert ingest_recent_response_schema == {"$ref": "#/components/schemas/IngestRecentListPublicResponse"}
    assert ingest_inventory_response_schema == {"$ref": "#/components/schemas/IngestInventoryPublicResponse"}

    schemas = (spec.get("components") or {}).get("schemas") or {}
    assert "JobStatusPublicResponse" in schemas
    assert "JobCitationsPublicResponse" in schemas
    assert "JobExportPayloadPublicResponse" in schemas
    assert "CitationPublicResponse" in schemas
    assert "JobVersionsPublicResponse" in schemas
    assert "DraftVersionPublicResponse" in schemas
    assert "JobDiffPublicResponse" in schemas
    assert "JobEventsPublicResponse" in schemas
    assert "JobEventPublicResponse" in schemas
    assert "JobMetricsPublicResponse" in schemas
    assert "JobQualitySummaryPublicResponse" in schemas
    assert "JobCriticPublicResponse" in schemas
    assert "JobReviewWorkflowPublicResponse" in schemas
    assert "JobReviewWorkflowFiltersPublicResponse" in schemas
    assert "JobReviewWorkflowSummaryPublicResponse" in schemas
    assert "ReviewWorkflowTimelineEventPublicResponse" in schemas
    assert "CriticRuleCheckPublicResponse" in schemas
    assert "CriticFatalFlawPublicResponse" in schemas
    assert "JobCommentsPublicResponse" in schemas
    assert "ReviewCommentPublicResponse" in schemas
    assert "PortfolioMetricsPublicResponse" in schemas
    assert "PortfolioQualityPublicResponse" in schemas
    assert "PortfolioQualityWeightedSignalPublicResponse" in schemas
    assert "PortfolioQualityDonorWeightedRiskPublicResponse" in schemas
    assert "PortfolioQualityCriticSummaryPublicResponse" in schemas
    assert "PortfolioQualityCitationSummaryPublicResponse" in schemas
    assert "PortfolioMetricsFiltersPublicResponse" in schemas
    assert "HITLPendingListPublicResponse" in schemas
    assert "IngestRecentListPublicResponse" in schemas
    assert "IngestRecentRecordPublicResponse" in schemas
    assert "IngestInventoryPublicResponse" in schemas
    assert "IngestInventoryDocFamilyPublicResponse" in schemas


def test_ingest_endpoint_uploads_to_donor_namespace(monkeypatch):
    api_app_module.INGEST_AUDIT_STORE.clear()
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


def test_ingest_recent_endpoint_returns_records(monkeypatch):
    api_app_module.INGEST_AUDIT_STORE.clear()

    def fake_ingest(pdf_path: str, namespace: str, metadata=None):
        return {"namespace": namespace, "source": pdf_path, "chunks_ingested": 1, "stats": {}}

    monkeypatch.setattr(api_app_module, "ingest_pdf_to_namespace", fake_ingest)

    r1 = client.post(
        "/ingest",
        data={
            "donor_id": "usaid",
            "metadata_json": json.dumps({"doc_family": "donor_policy", "source_type": "donor_guidance"}),
        },
        files={"file": ("ads.pdf", b"%PDF-1.4 a", "application/pdf")},
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/ingest",
        data={
            "donor_id": "eu",
            "metadata_json": json.dumps({"doc_family": "country_context", "source_type": "country_context"}),
        },
        files={"file": ("eu-context.pdf", b"%PDF-1.4 b", "application/pdf")},
    )
    assert r2.status_code == 200

    r3 = client.post(
        "/ingest",
        data={
            "donor_id": "usaid",
            "metadata_json": json.dumps({"doc_family": "country_context", "source_type": "country_context"}),
        },
        files={"file": ("kz-context.pdf", b"%PDF-1.4 c", "application/pdf")},
    )
    assert r3.status_code == 200

    recent = client.get("/ingest/recent", params={"donor_id": "usaid", "limit": 10})
    assert recent.status_code == 200
    body = recent.json()
    assert body["donor_id"] == "usaid"
    assert body["count"] == 2
    assert len(body["records"]) == 2
    assert body["records"][0]["donor_id"] == "usaid"
    assert body["records"][0]["filename"] == "kz-context.pdf"
    assert body["records"][0]["metadata"]["doc_family"] == "country_context"
    assert body["records"][1]["filename"] == "ads.pdf"
    assert body["records"][1]["metadata"]["doc_family"] == "donor_policy"


def test_ingest_inventory_endpoint_aggregates_doc_families(monkeypatch):
    api_app_module.INGEST_AUDIT_STORE.clear()

    def fake_ingest(pdf_path: str, namespace: str, metadata=None):
        return {"namespace": namespace, "source": pdf_path, "chunks_ingested": 1, "stats": {}}

    monkeypatch.setattr(api_app_module, "ingest_pdf_to_namespace", fake_ingest)

    uploads = [
        ("usaid", "ads201.pdf", {"doc_family": "donor_policy", "source_type": "donor_guidance"}),
        ("usaid", "kazakhstan-context.pdf", {"doc_family": "country_context", "source_type": "country_context"}),
        ("usaid", "ads-addendum.pdf", {"doc_family": "donor_policy", "source_type": "donor_guidance"}),
        ("eu", "eu-guide.pdf", {"doc_family": "donor_policy", "source_type": "donor_guidance"}),
    ]
    for donor_id, filename, metadata in uploads:
        response = client.post(
            "/ingest",
            data={"donor_id": donor_id, "metadata_json": json.dumps(metadata)},
            files={"file": (filename, b"%PDF-1.4 x", "application/pdf")},
        )
        assert response.status_code == 200

    response = client.get("/ingest/inventory", params={"donor_id": "usaid"})
    assert response.status_code == 200
    body = response.json()
    assert body["donor_id"] == "usaid"
    assert body["total_uploads"] == 3
    assert body["family_count"] == 2
    assert body["doc_family_counts"]["donor_policy"] == 2
    assert body["doc_family_counts"]["country_context"] == 1
    families = {row["doc_family"]: row for row in body["doc_families"]}
    assert families["donor_policy"]["count"] == 2
    assert families["donor_policy"]["latest_filename"] in {"ads-addendum.pdf", "ads201.pdf"}
    assert families["country_context"]["count"] == 1
    assert families["country_context"]["latest_filename"] == "kazakhstan-context.pdf"


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
    assert status["state"]["hitl_pending"] is True
    assert status["state"]["toc_draft"]
    assert "logframe_draft" not in status["state"]

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
    assert status["state"]["hitl_pending"] is True
    assert status["state"]["logframe_draft"]

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
    assert state["hitl_pending"] is False
    assert state["toc_draft"]
    assert state["logframe_draft"]
    engine = str((state.get("critic_notes") or {}).get("engine", "") or "")
    assert engine in {"rules", ""} or engine.startswith("rules+llm:")


def test_resume_requires_checkpoint_decision_before_running_again():
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

    resume = client.post(f"/resume/{job_id}", json={})
    assert resume.status_code == 409
    assert "pending approval" in resume.json()["detail"]


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
