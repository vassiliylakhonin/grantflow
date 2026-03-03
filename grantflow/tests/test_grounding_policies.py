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
