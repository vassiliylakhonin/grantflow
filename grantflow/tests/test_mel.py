from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes import mel_specialist as mel_module


def _base_state(*, llm_mode: bool) -> dict:
    strategy = DonorFactory.get_strategy("usaid")
    return {
        "donor": "usaid",
        "donor_id": "usaid",
        "strategy": strategy,
        "donor_strategy": strategy,
        "input": {"project": "Water Sanitation", "country": "Kenya"},
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "toc_draft": {"toc": {"project_goal": "Improve water and sanitation outcomes"}},
        "llm_mode": llm_mode,
        "iteration": 1,
        "iteration_count": 1,
        "critic_notes": {},
        "errors": [],
    }


def test_mel_deterministic_mode_generates_logframe_and_citations(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["USAID indicator guidance for water service quality"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p12_c0", "chunk_id": "usaid_ads201_p12_c0", "page": 12}]],
            "ids": [["usaid_ads201_p12_c0"]],
            "distances": [[0.05]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=False)

    out = mel_module.mel_assign_indicators(state)
    indicators = out["logframe_draft"]["indicators"]
    citations = [c for c in (out.get("citations") or []) if isinstance(c, dict) and c.get("stage") == "mel"]
    generation = out.get("mel_generation_meta") or {}

    assert indicators
    assert citations
    assert generation.get("llm_requested") is False
    assert generation.get("llm_used") is False
    assert str(generation.get("engine") or "").startswith("deterministic:")
    assert out["logframe_draft"]["rag_trace"]["used_results"] == 1
    assert citations[0]["citation_type"] in {"rag_result", "rag_low_confidence"}
    assert citations[0]["used_for"]
    assert out.get("draft_versions")


def test_mel_llm_mode_without_api_key_uses_emergency_fallback(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: False)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=True)

    out = mel_module.mel_assign_indicators(state)
    indicators = out["logframe_draft"]["indicators"]
    generation = out.get("mel_generation_meta") or {}
    citations = [c for c in (out.get("citations") or []) if isinstance(c, dict) and c.get("stage") == "mel"]

    assert indicators
    assert indicators[0]["indicator_id"] == "IND_001"
    assert generation.get("llm_requested") is True
    assert generation.get("llm_used") is False
    assert generation.get("fallback_used") is True
    assert generation.get("fallback_class") == "emergency"
    assert "OPENAI_API_KEY / OPENROUTER_API_KEY missing" in str(generation.get("llm_fallback_reason") or "")
    assert citations
    assert citations[0]["citation_type"] == "fallback_namespace"


def test_mel_llm_mode_uses_structured_output_when_available(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: True)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Official donor indicator guidance excerpt"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p10_c1", "chunk_id": "usaid_ads201_p10_c1", "page": 10}]],
            "ids": [["usaid_ads201_p10_c1"]],
            "distances": [[0.1]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    monkeypatch.setattr(
        mel_module,
        "_llm_structured_mel",
        lambda **kwargs: (
            {
                "indicators": [
                    {
                        "indicator_id": "IND_101",
                        "name": "Officials trained on AI governance",
                        "justification": "Directly tracks workforce upskilling objective.",
                        "citation": "USAID ADS 201 p.10",
                        "baseline": "0",
                        "target": "250",
                        "evidence_excerpt": "Official donor indicator guidance excerpt",
                    },
                    {
                        "indicator_id": "IND_102",
                        "name": "Policies updated with AI safeguards",
                        "justification": "Tracks policy institutionalization results.",
                        "citation": "USAID ADS 201 p.10",
                        "baseline": "0",
                        "target": "6",
                        "evidence_excerpt": "Official donor indicator guidance excerpt",
                    },
                ]
            },
            "llm:stub-mel-model",
            None,
        ),
    )

    state = _base_state(llm_mode=True)
    out = mel_module.mel_assign_indicators(state)
    indicators = out["logframe_draft"]["indicators"]
    generation = out.get("mel_generation_meta") or {}
    citations = [c for c in (out.get("citations") or []) if isinstance(c, dict) and c.get("stage") == "mel"]

    assert len(indicators) == 2
    assert indicators[0]["indicator_id"] == "IND_101"
    assert indicators[1]["indicator_id"] == "IND_102"
    assert generation.get("llm_requested") is True
    assert generation.get("llm_used") is True
    assert generation.get("fallback_used") is False
    assert generation.get("engine") == "llm:stub-mel-model"
    assert len(citations) == 2
    assert all(c.get("citation_type") in {"rag_result", "rag_low_confidence", "fallback_namespace"} for c in citations)
