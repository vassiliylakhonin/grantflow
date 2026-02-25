from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes.architect import draft_toc
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
