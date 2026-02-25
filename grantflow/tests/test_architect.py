from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes import architect_generation as architect_generation_module
from grantflow.swarm.nodes.architect_generation import (
    _fallback_structured_toc,
    build_architect_claim_citations,
    generate_toc_under_contract,
)
from grantflow.swarm.nodes.architect_retrieval import pick_best_architect_evidence_hit


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
        {"rank": 1, "label": "Generic donor guide", "excerpt": "Procurement and reporting templates", "source": "a.pdf"},
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


def test_architect_claim_citation_policy_marks_low_confidence_hits():
    toc_payload = {"project_goal": "Improve water sanitation outcomes", "objectives": []}
    citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace="usaid_ads201",
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
    assert 0.0 <= float(citations[0]["citation_confidence"]) <= 1.0
    if citations[0]["citation_type"] == "rag_low_confidence":
        assert float(citations[0]["citation_confidence"]) < 0.35


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
