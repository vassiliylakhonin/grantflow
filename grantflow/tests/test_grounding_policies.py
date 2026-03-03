import grantflow.api.app as api_app_module


def test_mel_grounding_policy_strict_blocks_on_traceability_gap(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "mel_grounding_policy_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "mel_grounding_min_mel_citations", 1)
    monkeypatch.setattr(api_app_module.config.graph, "mel_grounding_min_claim_support_rate", 0.0)
    monkeypatch.setattr(api_app_module.config.graph, "mel_grounding_min_traceability_complete_rate", 1.0)
    monkeypatch.setattr(api_app_module.config.graph, "mel_grounding_max_traceability_gap_rate", 0.0)

    state = {
        "citations": [
            {"stage": "mel", "citation_type": "rag_result"},
            {"stage": "mel", "citation_type": "rag_support"},
        ]
    }
    policy = api_app_module._evaluate_mel_grounding_policy_from_state(state)
    assert policy["mode"] == "strict"
    assert policy["mel_citation_count"] == 2
    assert policy["mel_traceability_complete_citation_count"] == 0
    assert policy["mel_traceability_gap_citation_count"] == 2
    assert policy["mel_traceability_complete_rate"] == 0.0
    assert policy["mel_traceability_gap_rate"] == 1.0
    assert policy["blocking"] is True
    assert "mel_traceability_complete_rate_below_min" in (policy.get("reasons") or [])
    assert "mel_traceability_gap_rate_above_max" in (policy.get("reasons") or [])


def test_export_grounding_policy_strict_blocks_on_traceability_gap(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "export_grounding_policy_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "export_grounding_min_architect_citations", 1)
    monkeypatch.setattr(api_app_module.config.graph, "export_grounding_min_claim_support_rate", 0.0)
    monkeypatch.setattr(api_app_module.config.graph, "export_grounding_min_traceability_complete_rate", 1.0)
    monkeypatch.setattr(api_app_module.config.graph, "export_grounding_max_traceability_gap_rate", 0.0)

    policy = api_app_module._evaluate_export_grounding_policy(
        [
            {"stage": "architect", "citation_type": "rag_claim_support"},
            {"stage": "architect", "citation_type": "rag_claim_support"},
        ]
    )
    assert policy["mode"] == "strict"
    assert policy["architect_citation_count"] == 2
    assert policy["architect_traceability_complete_citation_count"] == 0
    assert policy["architect_traceability_gap_citation_count"] == 2
    assert policy["architect_traceability_complete_rate"] == 0.0
    assert policy["architect_traceability_gap_rate"] == 1.0
    assert policy["blocking"] is True
    assert "traceability_complete_rate_below_min" in (policy.get("reasons") or [])
    assert "traceability_gap_rate_above_max" in (policy.get("reasons") or [])


def test_preflight_grounding_policy_strict_blocks_on_architect_claim_thresholds(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_high_risk_coverage_threshold", 0.5)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_medium_risk_coverage_threshold", 0.8)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_high_risk_depth_coverage_threshold", 0.2)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_medium_risk_depth_coverage_threshold", 0.5)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_min_uploads", 3)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_min_key_claim_coverage_rate", 0.6)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_max_fallback_claim_ratio", 0.8)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_max_traceability_gap_rate", 0.6)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_min_threshold_hit_rate", 0.4)

    policy = api_app_module._build_preflight_grounding_policy(
        coverage_rate=1.0,
        depth_coverage_rate=1.0,
        namespace_empty=False,
        inventory_total_uploads=8,
        missing_doc_families=[],
        depth_gap_doc_families=[],
        architect_claims={
            "available": True,
            "claim_citation_count": 4,
            "key_claim_coverage_ratio": 0.25,
            "fallback_claim_ratio": 0.95,
            "traceability_gap_rate": 0.9,
            "threshold_hit_rate": 0.1,
        },
    )
    assert policy["mode"] == "strict"
    assert policy["risk_level"] == "high"
    assert policy["blocking"] is True
    reasons = policy.get("reasons") or []
    assert "architect_key_claim_coverage_below_min" in reasons
    assert "architect_fallback_claim_ratio_above_max" in reasons
    assert "architect_traceability_gap_rate_above_max" in reasons
    assert "architect_threshold_hit_rate_below_min" in reasons


def test_preflight_grounding_policy_warns_when_architect_claims_not_evaluated(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "warn")

    policy = api_app_module._build_preflight_grounding_policy(
        coverage_rate=1.0,
        depth_coverage_rate=1.0,
        namespace_empty=False,
        inventory_total_uploads=8,
        missing_doc_families=[],
        depth_gap_doc_families=[],
        architect_claims={"available": False, "reason": "input_context_missing"},
    )
    assert policy["mode"] == "warn"
    assert policy["risk_level"] == "medium"
    assert policy["blocking"] is False
    assert "architect_claim_policy_not_evaluated" in (policy.get("reasons") or [])


def test_preflight_grounding_policy_strict_blocks_on_depth_coverage(monkeypatch):
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_policy_mode", "strict")
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_high_risk_depth_coverage_threshold", 0.4)
    monkeypatch.setattr(api_app_module.config.graph, "preflight_grounding_medium_risk_depth_coverage_threshold", 0.7)

    policy = api_app_module._build_preflight_grounding_policy(
        coverage_rate=1.0,
        depth_coverage_rate=0.2,
        namespace_empty=False,
        inventory_total_uploads=8,
        missing_doc_families=[],
        depth_gap_doc_families=["donor_policy"],
        architect_claims=None,
    )
    assert policy["mode"] == "strict"
    assert policy["risk_level"] == "high"
    assert policy["blocking"] is True
    assert "depth_coverage_below_high_threshold" in (policy.get("reasons") or [])
