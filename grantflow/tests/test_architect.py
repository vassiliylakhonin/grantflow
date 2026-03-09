from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes import architect_generation as architect_generation_module
from grantflow.swarm.nodes import architect_retrieval as architect_retrieval_module
from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes.architect_generation import (
    _architect_grounded_confidence_bonus,
    _extract_claim_strings,
    _fallback_structured_toc,
    build_architect_claim_citations,
    extract_architect_claim_records,
    generate_toc_under_contract,
    summarize_architect_claim_citations,
)
from grantflow.swarm.nodes.architect_policy import architect_claim_confidence_threshold
from grantflow.swarm.nodes.architect_retrieval import (
    pick_best_architect_evidence_hit,
    retrieve_architect_evidence,
    score_architect_evidence_hit,
)


def test_architect_generates_contract_validated_toc_with_optional_retrieval_disabled():
    strategy = DonorFactory.get_strategy("usaid")
    state = {
        "donor": "usaid",
        "donor_id": "usaid",
        "strategy": strategy,
        "donor_strategy": strategy,
        "input": {"project": "Water Sanitation", "country": "Kenya"},
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": False,
        "architect_rag_enabled": False,
        "iteration": 0,
        "iteration_count": 0,
        "critic_notes": {},
        "errors": [],
    }

    out = draft_toc(state)
    assert out["toc"]
    assert out["toc_draft"]["toc"]

    validation = out.get("toc_validation") or {}
    assert validation.get("valid") is True
    assert validation.get("schema_name")

    retrieval = out.get("architect_retrieval") or {}
    assert retrieval.get("enabled") is False
    assert retrieval.get("namespace") == strategy.get_rag_collection()
    assert retrieval.get("namespace_normalized") == strategy.get_rag_collection()
    assert retrieval.get("hits_count") == 0

    generation_meta = out.get("toc_generation_meta") or {}
    assert generation_meta.get("llm_used") is False
    assert generation_meta.get("retrieval_used") is False
    assert str(generation_meta.get("engine") or "").startswith("deterministic:")
    assert generation_meta.get("llm_requested") is False
    assert generation_meta.get("llm_available") in {True, False}
    assert generation_meta.get("llm_attempted") is False
    assert generation_meta.get("fallback_used") is False
    assert generation_meta.get("fallback_class") == "deterministic_mode"
    assert generation_meta.get("architect_mode") == "deterministic"
    claim_coverage = generation_meta.get("claim_coverage") or {}
    assert isinstance(claim_coverage, dict)
    assert int(claim_coverage.get("claims_total") or 0) >= 1
    assert int(claim_coverage.get("claim_citation_count") or 0) >= 0

    citations = out.get("citations") or []
    architect_citations = [c for c in citations if isinstance(c, dict) and c.get("stage") == "architect"]
    assert architect_citations
    assert any(c.get("statement_path") for c in architect_citations)
    assert all(c.get("result_level") in {"impact", "outcome", "output", "general"} for c in architect_citations)
    assert any("citation_confidence" in c for c in architect_citations)
    assert all(0.0 <= float(c.get("citation_confidence", 0.0)) <= 1.0 for c in architect_citations)


def test_architect_evidence_ranking_prefers_more_relevant_hit():
    statement = "Improve water sanitation outcomes in Kenya through community systems"
    hits = [
        {
            "rank": 1,
            "label": "Generic donor guide",
            "excerpt": "Procurement and reporting templates",
            "source": "a.pdf",
        },
        {
            "rank": 2,
            "label": "WASH technical guidance",
            "excerpt": "Kenya water sanitation outcomes and community systems strengthening guidance",
            "source": "b.pdf",
            "page": 12,
        },
    ]
    best_hit, confidence = pick_best_architect_evidence_hit(statement, hits)
    assert best_hit["source"] == "b.pdf"
    assert confidence > 0.3


def test_architect_evidence_scoring_penalizes_generic_excerpt_and_rewards_worldbank_tokens():
    statement = "Improve public service delivery performance through results framework indicators"
    generic_hit = {
        "rank": 1,
        "label": "Implementation templates",
        "excerpt": "Budget templates procurement reporting compliance annex and finance forms",
        "source": "generic.pdf",
    }
    wb_hit = {
        "rank": 2,
        "label": "World Bank results framework guide",
        "excerpt": "Results framework indicators for public service delivery performance monitoring",
        "source": "wb.pdf",
        "page": 5,
    }
    generic_score = score_architect_evidence_hit(
        statement,
        generic_hit,
        donor_id="worldbank",
        statement_path="toc.results[0].description",
    )
    wb_score = score_architect_evidence_hit(
        statement,
        wb_hit,
        donor_id="worldbank",
        statement_path="toc.results[0].description",
    )
    assert wb_score > generic_score
    best_hit, confidence = pick_best_architect_evidence_hit(
        statement,
        [generic_hit, wb_hit],
        donor_id="worldbank",
        statement_path="toc.results[0].description",
    )
    assert best_hit["source"] == "wb.pdf"
    assert confidence == wb_score


def test_retrieve_architect_evidence_normalizes_traceability_and_deduplicates_hits(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Relevant donor paragraph", "Duplicate entry"]],
            "metadatas": [
                [
                    {"source": "guide.pdf", "chunk_id": "ch_1", "page": 2},
                    {"source": "guide.pdf", "chunk_id": "ch_1", "page": 2},
                ]
            ],
            "ids": [["id_1", "id_1"]],
            "distances": [[0.1, 0.2]],
        }

    monkeypatch.setattr(architect_retrieval_module.vector_store, "query", fake_query)

    summary, hits = retrieve_architect_evidence(
        {"donor_id": "usaid", "input_context": {"project": "Water", "country": "Kenya"}},
        "usaid_ads201",
    )
    assert len(hits) == 1
    hit = hits[0]
    assert hit["doc_id"]
    assert hit["chunk_id"] == "ch_1"
    assert hit["traceability_status"] == "complete"
    assert hit["traceability_complete"] is True
    assert hit["namespace_normalized"] == "usaid_ads201"
    assert summary["traceability_counts"]["complete"] == 1
    assert summary["namespace_normalized"] == "usaid_ads201"
    assert summary.get("collection", "").startswith("grantflow_")
    assert summary["hits"][0]["traceability_complete"] is True


def test_architect_claim_citation_policy_marks_low_confidence_hits():
    toc_payload = {"project_goal": "Improve water sanitation outcomes", "objectives": []}
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
        donor_id="usaid",
        evidence_hits=[
            {
                "rank": 1,
                "retrieval_rank": 1,
                "retrieval_confidence": 0.62,
                "doc_id": "usaid_ads201_p3_c0",
                "chunk_id": "usaid_ads201_p3_c0",
                "label": "Unrelated guidance",
                "source": "a.pdf",
                "excerpt": "Procurement templates and financial reporting annexes only",
            }
        ],
    )
    assert citations
    assert citations[0]["citation_type"] in {"rag_low_confidence", "fallback_namespace", "rag_claim_support"}
    assert "citation_confidence" in citations[0]
    assert "confidence_threshold" in citations[0]
    assert "doc_id" in citations[0]
    assert "retrieval_rank" in citations[0]
    assert "retrieval_confidence" in citations[0]
    assert "evidence_signal" in citations[0]
    assert "review_hint" in citations[0]
    assert 0.0 <= float(citations[0]["citation_confidence"]) <= 1.0
    assert 0.0 < float(citations[0]["confidence_threshold"]) < 1.0
    if citations[0]["citation_type"] == "rag_low_confidence":
        assert float(citations[0]["citation_confidence"]) < float(citations[0]["confidence_threshold"])


def test_architect_claim_citations_without_hits_emit_per_claim_fallback_records():
    toc_payload = {
        "project_goal": "Improve water sanitation outcomes",
        "development_objectives": [
            {"description": "Improve governance and service quality"},
            {"description": "Improve coverage and reliability"},
        ],
    }
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
        donor_id="usaid",
        evidence_hits=[],
    )
    assert len(citations) >= 3
    assert all(c["citation_type"] == "fallback_namespace" for c in citations)
    assert all(c.get("used_for") == "toc_claim" for c in citations)
    assert all(str(c.get("statement_path") or "").strip() for c in citations)
    assert all(c.get("result_level") in {"impact", "outcome", "output", "general"} for c in citations)
    assert all(c.get("traceability_status") == "missing" for c in citations)
    assert all(c.get("traceability_complete") is False for c in citations)
    assert all(c.get("evidence_signal") == "fallback namespace only" for c in citations)
    assert all(str(c.get("review_hint") or "").strip() for c in citations)
    assert all("no retrieved evidence" in str(c.get("label") or "").lower() for c in citations)
    assert all(0.0 < float(c.get("confidence_threshold") or 0.0) < 1.0 for c in citations)


def test_architect_claim_citations_without_hits_use_strategy_reference_when_retrieval_disabled():
    toc_payload = {
        "project_goal": "Improve water sanitation outcomes",
        "development_objectives": [
            {"description": "Improve governance and service quality"},
            {"description": "Improve coverage and reliability"},
        ],
    }
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
        donor_id="usaid",
        evidence_hits=[],
        retrieval_expected=False,
    )
    assert len(citations) >= 3
    assert all(c["citation_type"] == "strategy_reference" for c in citations)
    assert all(c.get("used_for") == "toc_claim" for c in citations)
    assert all(str(c.get("statement_path") or "").strip() for c in citations)
    assert all(c.get("result_level") in {"impact", "outcome", "output", "general"} for c in citations)
    assert all(c.get("traceability_status") == "complete" for c in citations)
    assert all(c.get("traceability_complete") is True for c in citations)
    assert all(c.get("evidence_signal") == "strategy reference" for c in citations)
    assert all(str(c.get("doc_id") or "").startswith("strategy::") for c in citations)
    assert all(str(c.get("source") or "").startswith("strategy::") for c in citations)
    assert all(float(c.get("citation_confidence") or 0.0) >= 0.7 for c in citations)


def test_architect_claim_support_requires_traceable_hit_even_when_overlap_is_high():
    statement = "Improve water sanitation outcomes in Kenya through community systems"
    toc_payload = {"project_goal": statement}
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
        donor_id="usaid",
        evidence_hits=[
            {
                "rank": 1,
                "retrieval_rank": 1,
                "label": "Untyped fragment",
                "excerpt": statement,
                "source": None,
                "doc_id": None,
                "chunk_id": None,
            }
        ],
    )
    assert citations
    citation = citations[0]
    assert citation["citation_type"] == "rag_low_confidence"
    assert citation["traceability_complete"] is False
    assert citation["traceability_status"] == "missing"


def test_architect_grounded_confidence_bonus_rewards_complete_rank1_hits():
    bonus = _architect_grounded_confidence_bonus(
        {
            "rank": 1,
            "retrieval_rank": 1,
            "retrieval_confidence": 0.87,
            "doc_id": "doc-1",
            "chunk_id": "chunk-1",
        },
        traceability_status="complete",
    )
    assert 0.0 < bonus <= 0.06


def test_extract_claim_strings_skips_identifier_fields():
    toc_payload = {
        "project_goal": "Improve services",
        "development_objectives": [
            {
                "do_id": "DO 1",
                "description": "Institutional capacity improves",
                "intermediate_results": [{"ir_id": "IR 1", "description": "Teams apply SOPs"}],
            }
        ],
    }
    claims = _extract_claim_strings(toc_payload, "toc")
    paths = [p for p, _ in claims]
    assert "toc.development_objectives[0].do_id" not in paths
    assert "toc.development_objectives[0].intermediate_results[0].ir_id" not in paths
    assert "toc.development_objectives[0].description" in paths


def test_extract_claim_strings_skips_nested_indicator_fields():
    toc_payload = {
        "development_objectives": [
            {
                "intermediate_results": [
                    {
                        "description": "Teams improve delivery practices",
                        "outputs": [
                            {
                                "description": "Training package deployed",
                                "indicators": [
                                    {
                                        "name": "Number of staff trained",
                                        "target": "500",
                                        "justification": "Tracks coverage",
                                        "citation": "usaid",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    }
    claims = _extract_claim_strings(toc_payload, "toc")
    paths = [p for p, _ in claims]
    assert "toc.development_objectives[0].intermediate_results[0].description" in paths
    assert "toc.development_objectives[0].intermediate_results[0].outputs[0].description" in paths
    assert not any(".indicators[" in p for p in paths)


def test_extract_claim_strings_skips_assumptions_and_risks():
    toc_payload = {
        "project_goal": "Improve service delivery",
        "critical_assumptions": ["Leadership support remains stable"],
        "assumptions": ["Local adoption remains strong"],
        "risks": ["Policy turnover delays adoption"],
    }
    claims = _extract_claim_strings(toc_payload, "toc")
    paths = [p for p, _ in claims]
    assert "toc.project_goal" in paths
    assert "toc.critical_assumptions[0]" not in paths
    assert "toc.assumptions[0]" not in paths
    assert "toc.risks[0]" not in paths


def test_extract_architect_claim_records_prioritizes_key_objective_paths():
    toc_payload = {
        "project_goal": "Improve access",
        "objectives": [
            {"objective_id": "OBJ-1", "title": "Title 1", "description": "Description 1"},
            {"objective_id": "OBJ-2", "title": "Title 2", "description": "Description 2"},
        ],
        "assumptions": ["Assumption 1"],
    }
    records = extract_architect_claim_records(toc_payload, max_claims=5, max_high_priority_claims=5)
    assert records
    paths = [str(r.get("statement_path") or "") for r in records]
    assert "toc.project_goal" in paths
    assert any(".objectives[0].description" in p or ".objectives[1].description" in p for p in paths)
    assert all(".assumptions[" not in p for p in paths)
    assert int(records[0].get("priority") or 0) >= int(records[-1].get("priority") or 0)


def test_summarize_architect_claim_citations_reports_coverage_ratios():
    claim_records = [
        {"statement_path": "toc.project_goal", "statement": "Goal", "priority": 5},
        {"statement_path": "toc.objectives[0].description", "statement": "Obj", "priority": 4},
    ]
    citations = [
        {
            "stage": "architect",
            "used_for": "toc_claim",
            "statement_path": "toc.project_goal",
            "citation_type": "rag_claim_support",
        },
        {
            "stage": "architect",
            "used_for": "toc_claim",
            "statement_path": "toc.objectives[0].description",
            "citation_type": "fallback_namespace",
        },
    ]
    stats = summarize_architect_claim_citations(claim_records=claim_records, citations=citations)
    assert stats["claims_total"] == 2
    assert stats["key_claims_total"] == 2
    assert stats["claim_paths_covered"] == 2
    assert stats["confident_claim_paths_covered"] == 1
    assert stats["fallback_claim_count"] == 1
    assert stats["key_claim_coverage_ratio"] == 1.0
    assert stats["fallback_claim_ratio"] == 0.5


def test_architect_claim_threshold_is_tuned_by_donor_and_section():
    default_threshold = architect_claim_confidence_threshold(donor_id="unknown", statement_path="toc.project_goal")
    usaid_goal_threshold = architect_claim_confidence_threshold(donor_id="usaid", statement_path="toc.project_goal")
    usaid_assumption_threshold = architect_claim_confidence_threshold(
        donor_id="usaid", statement_path="toc.critical_assumptions[0]"
    )

    assert default_threshold >= 0.35
    assert usaid_goal_threshold == 0.32
    assert usaid_assumption_threshold > usaid_goal_threshold


def test_architect_llm_validation_failure_retries_once_and_recovers(monkeypatch):
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(architect_generation_module, "openai_compatible_llm_available", lambda: True)
    schema_cls = strategy.get_toc_schema()
    valid_payload, _ = _fallback_structured_toc(
        schema_cls,
        donor_id="usaid",
        project="Water Sanitation",
        country="Kenya",
        revision_hint="",
        evidence_hits=[],
    )

    calls = []

    def fake_llm_structured_toc(*args, **kwargs):
        calls.append(kwargs.get("validation_error_hint"))
        if len(calls) == 1:
            return {"invalid": "payload"}, "llm:mock", None
        return valid_payload, "llm:mock", None

    monkeypatch.setattr(architect_generation_module, "_llm_structured_toc", fake_llm_structured_toc)

    state = {
        "donor": "usaid",
        "donor_id": "usaid",
        "strategy": strategy,
        "donor_strategy": strategy,
        "input": {"project": "Water Sanitation", "country": "Kenya"},
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": True,
        "critic_notes": {},
    }

    toc, validation, generation_meta, claim_citations = generate_toc_under_contract(
        state=state, strategy=strategy, evidence_hits=[]
    )
    assert toc
    assert validation["valid"] is True
    assert generation_meta["llm_used"] is True
    assert generation_meta.get("llm_validation_repair_attempted") is True
    assert len(calls) == 2
    assert calls[0] is None
    assert isinstance(calls[1], str) and calls[1]
    assert isinstance(claim_citations, list)


def test_architect_llm_mode_without_api_key_uses_emergency_fallback(monkeypatch):
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(architect_generation_module, "openai_compatible_llm_available", lambda: False)
    monkeypatch.setattr(architect_generation_module, "_llm_structured_toc", lambda *args, **kwargs: (None, None, None))

    state = {
        "donor": "usaid",
        "donor_id": "usaid",
        "strategy": strategy,
        "donor_strategy": strategy,
        "input": {"project": "Water Sanitation", "country": "Kenya"},
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": True,
        "critic_notes": {},
    }

    toc, validation, generation_meta, _claim_citations = generate_toc_under_contract(
        state=state, strategy=strategy, evidence_hits=[]
    )
    assert toc
    assert validation["valid"] is True
    assert generation_meta.get("llm_used") is False
    assert generation_meta.get("llm_requested") is True
    assert generation_meta.get("llm_available") is False
    assert generation_meta.get("llm_attempted") is False
    assert generation_meta.get("fallback_used") is True
    assert generation_meta.get("fallback_class") == "emergency"
    assert generation_meta.get("architect_mode") == "llm"
    assert str(generation_meta.get("engine") or "").startswith("fallback:")
    assert "missing" in str(generation_meta.get("llm_fallback_reason") or "").lower()


def test_architect_llm_prompt_receives_full_input_context_and_schema_contract(monkeypatch):
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(architect_generation_module, "openai_compatible_llm_available", lambda: True)

    schema_cls = strategy.get_toc_schema()
    valid_payload, _ = _fallback_structured_toc(
        schema_cls,
        donor_id="usaid",
        project="Digital Governance",
        country="Kazakhstan",
        revision_hint="",
        evidence_hits=[],
    )
    captured: dict[str, object] = {}

    def fake_llm_structured_toc(*args, **kwargs):
        captured["input_context"] = kwargs.get("input_context")
        captured["schema_contract_hint"] = kwargs.get("schema_contract_hint")
        captured["schema_json_contract_hint"] = kwargs.get("schema_json_contract_hint")
        return valid_payload, "llm:mock", None

    monkeypatch.setattr(architect_generation_module, "_llm_structured_toc", fake_llm_structured_toc)

    state = {
        "donor_id": "usaid",
        "donor_strategy": strategy,
        "input_context": {
            "project": "Digital Governance",
            "country": "Kazakhstan",
            "sector": "Public Administration",
            "budget_usd": 2500000,
        },
        "llm_mode": True,
        "critic_notes": {},
    }
    _toc, validation, generation_meta, _claim_citations = generate_toc_under_contract(
        state=state,
        strategy=strategy,
        evidence_hits=[],
    )
    assert validation["valid"] is True
    assert generation_meta["llm_used"] is True
    assert generation_meta["schema_contract_hint_present"] is True
    assert generation_meta["schema_json_hint_present"] is True
    assert generation_meta["input_context_key_count"] == 4
    assert isinstance(captured.get("input_context"), dict)
    assert captured["input_context"] == state["input_context"]
    schema_hint = str(captured.get("schema_contract_hint") or "")
    assert schema_hint
    assert "project_goal" in schema_hint
    schema_json_hint = str(captured.get("schema_json_contract_hint") or "")
    assert schema_json_hint
    assert "properties" in schema_json_hint


def test_architect_llm_tries_fallback_model_chain_and_selects_first_success(monkeypatch):
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(architect_generation_module, "openai_compatible_llm_available", lambda: True)
    monkeypatch.setattr(architect_generation_module.config.llm, "architect_model", "model-primary")
    monkeypatch.setattr(architect_generation_module.config.llm, "reasoning_model", "model-secondary")
    monkeypatch.setattr(architect_generation_module.config.llm, "cheap_model", "model-cheap")

    schema_cls = strategy.get_toc_schema()
    valid_payload, _ = _fallback_structured_toc(
        schema_cls,
        donor_id="usaid",
        project="Digital Governance",
        country="Kazakhstan",
        revision_hint="",
        evidence_hits=[],
    )
    calls: list[str] = []

    def fake_llm_structured_toc(*args, **kwargs):
        model_name = str(kwargs.get("model_name") or "")
        calls.append(model_name)
        if model_name == "model-primary":
            return None, None, "primary model unavailable"
        if model_name == "model-secondary":
            return valid_payload, "llm:model-secondary", None
        return None, None, "unexpected model"

    monkeypatch.setattr(architect_generation_module, "_llm_structured_toc", fake_llm_structured_toc)

    state = {
        "donor_id": "usaid",
        "donor_strategy": strategy,
        "input_context": {"project": "Digital Governance", "country": "Kazakhstan"},
        "llm_mode": True,
        "critic_notes": {},
    }
    _toc, validation, generation_meta, _claim_citations = generate_toc_under_contract(
        state=state,
        strategy=strategy,
        evidence_hits=[],
    )
    assert validation["valid"] is True
    assert generation_meta["llm_used"] is True
    assert generation_meta["engine"] == "llm:model-secondary"
    assert generation_meta["llm_selected_model"] == "model-secondary"
    assert generation_meta["llm_attempt_count"] == 2
    assert generation_meta["llm_models_tried"] == ["model-primary", "model-secondary"]
    assert calls[:2] == ["model-primary", "model-secondary"]
    assert len(calls) >= 2


def test_summarize_architect_claim_citations_includes_traceability_and_threshold_stats():
    claim_records = [
        {"statement_path": "toc.project_goal", "statement": "Goal", "priority": 5},
        {"statement_path": "toc.objectives[0].description", "statement": "Objective", "priority": 4},
    ]
    citations = [
        {
            "stage": "architect",
            "used_for": "toc_claim",
            "statement_path": "toc.project_goal",
            "citation_type": "rag_claim_support",
            "traceability_status": "complete",
            "citation_confidence": 0.82,
            "confidence_threshold": 0.6,
        },
        {
            "stage": "architect",
            "used_for": "toc_claim",
            "statement_path": "toc.objectives[0].description",
            "citation_type": "rag_low_confidence",
            "traceability_status": "partial",
            "citation_confidence": 0.31,
            "confidence_threshold": 0.5,
        },
    ]
    stats = summarize_architect_claim_citations(claim_records=claim_records, citations=citations)
    assert stats["traceability_complete_citation_count"] == 1
    assert stats["traceability_partial_citation_count"] == 1
    assert stats["traceability_missing_citation_count"] == 0
    assert stats["traceability_gap_citation_count"] == 1
    assert stats["traceability_gap_rate"] == 0.5
    assert stats["threshold_considered_count"] == 2
    assert stats["threshold_hit_count"] == 1
    assert stats["threshold_hit_rate"] == 0.5


def test_architect_llm_soft_quality_repair_retries_once(monkeypatch):
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(architect_generation_module, "openai_compatible_llm_available", lambda: True)

    schema_cls = strategy.get_toc_schema()
    valid_payload, _ = _fallback_structured_toc(
        schema_cls,
        donor_id="usaid",
        project="Water Sanitation",
        country="Kenya",
        revision_hint="",
        evidence_hits=[],
    )
    placeholder_payload = dict(valid_payload)
    placeholder_payload["project_goal"] = "TBD"

    hints: list[str | None] = []

    def fake_llm_structured_toc(*args, **kwargs):
        hints.append(kwargs.get("validation_error_hint"))
        if len(hints) == 1:
            return placeholder_payload, "llm:mock", None
        return valid_payload, "llm:mock", None

    monkeypatch.setattr(architect_generation_module, "_llm_structured_toc", fake_llm_structured_toc)

    state = {
        "donor_id": "usaid",
        "donor_strategy": strategy,
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": True,
        "critic_notes": {},
    }
    toc, validation, generation_meta, _claim_citations = generate_toc_under_contract(
        state=state,
        strategy=strategy,
        evidence_hits=[],
    )
    assert validation["valid"] is True
    assert toc["project_goal"] != "TBD"
    assert generation_meta["llm_used"] is True
    assert generation_meta.get("llm_quality_repair_attempted") is True
    assert int(generation_meta.get("llm_quality_issue_count") or 0) >= 1
    assert len(hints) == 2
    assert hints[0] is None
    assert isinstance(hints[1], str)
    assert "Soft quality issues detected" in str(hints[1])


def test_fallback_structured_toc_uses_eu_specific_intervention_logic_phrasing():
    strategy = DonorFactory.get_strategy("eu")
    payload, engine = _fallback_structured_toc(
        strategy.get_toc_schema(),
        donor_id="eu",
        project="Digital Governance",
        country="Moldova",
        revision_hint="",
        evidence_hits=[],
    )

    assert engine == "contract_synthesizer"
    assert "digital governance" in payload["overall_objective"]["title"].lower()
    assert "eu intervention logic" in payload["overall_objective"]["rationale"].lower()
    assert payload["specific_objectives"]
    assert any("institutional capacity" in row["title"].lower() for row in payload["specific_objectives"])
    assert payload["expected_outcomes"]
    assert any("measurable improvements" in row["expected_change"].lower() for row in payload["expected_outcomes"])


def test_fallback_structured_toc_uses_worldbank_specific_results_chain_phrasing():
    strategy = DonorFactory.get_strategy("worldbank")
    payload, engine = _fallback_structured_toc(
        strategy.get_toc_schema(),
        donor_id="worldbank",
        project="Public Sector Performance",
        country="Uzbekistan",
        revision_hint="",
        evidence_hits=[],
    )

    assert engine == "contract_synthesizer"
    assert "service delivery performance" in payload["project_development_objective"].lower()
    assert payload["objectives"]
    assert any("institutional performance" in row["title"].lower() for row in payload["objectives"])
    assert payload["results_chain"]
    assert any(
        "participating agencies implement workflow" in row["description"].lower() for row in payload["results_chain"]
    )
    assert any("processing time" in row["indicator_focus"].lower() for row in payload["results_chain"])
