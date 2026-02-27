from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes import architect_generation as architect_generation_module
from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes.architect_generation import (
    _extract_claim_strings,
    _fallback_structured_toc,
    build_architect_claim_citations,
    generate_toc_under_contract,
)
from grantflow.swarm.nodes.architect_policy import architect_claim_confidence_threshold
from grantflow.swarm.nodes.architect_retrieval import pick_best_architect_evidence_hit, score_architect_evidence_hit


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
    assert retrieval.get("hits_count") == 0

    generation_meta = out.get("toc_generation_meta") or {}
    assert generation_meta.get("llm_used") is False
    assert generation_meta.get("retrieval_used") is False
    assert str(generation_meta.get("engine") or "").startswith("fallback:")

    citations = out.get("citations") or []
    architect_citations = [c for c in citations if isinstance(c, dict) and c.get("stage") == "architect"]
    assert architect_citations
    assert any(c.get("statement_path") for c in architect_citations)
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


def test_architect_claim_citation_policy_marks_low_confidence_hits():
    toc_payload = {"project_goal": "Improve water sanitation outcomes", "objectives": []}
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
        donor_id="usaid",
        evidence_hits=[
            {
                "rank": 1,
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
    assert 0.0 <= float(citations[0]["citation_confidence"]) <= 1.0
    assert 0.0 < float(citations[0]["confidence_threshold"]) < 1.0
    if citations[0]["citation_type"] == "rag_low_confidence":
        assert float(citations[0]["citation_confidence"]) < float(citations[0]["confidence_threshold"])


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
        "risks": ["Policy turnover delays adoption"],
    }
    claims = _extract_claim_strings(toc_payload, "toc")
    paths = [p for p, _ in claims]
    assert "toc.project_goal" in paths
    assert "toc.critical_assumptions[0]" not in paths
    assert "toc.risks[0]" not in paths


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
