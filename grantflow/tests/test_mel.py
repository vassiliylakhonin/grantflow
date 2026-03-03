from __future__ import annotations

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.nodes import mel_specialist as mel_module


def _is_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return lowered in {"", "tbd", "to be determined", "placeholder", "n/a", "na", "unknown", "-", "--"}


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
    assert out["logframe_draft"]["rag_trace"]["namespace_normalized"] == "usaid_ads201"
    assert out["logframe_draft"]["rag_trace"]["hits"][0]["traceability_status"] in {"complete", "partial", "missing"}
    assert "traceability_counts" in out["logframe_draft"]["rag_trace"]
    assert citations[0]["citation_type"] in {"rag_result", "rag_low_confidence"}
    assert citations[0]["namespace_normalized"] == "usaid_ads201"
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


def test_mel_deterministic_no_hits_uses_strategy_reference_citations(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=False)

    out = mel_module.mel_assign_indicators(state)
    citations = [c for c in (out.get("citations") or []) if isinstance(c, dict) and c.get("stage") == "mel"]
    assert citations
    assert all(c.get("citation_type") == "strategy_reference" for c in citations)
    assert all(c.get("traceability_status") == "complete" for c in citations)
    assert all(c.get("traceability_complete") is True for c in citations)
    assert all(str(c.get("doc_id") or "").startswith("strategy::") for c in citations)
    assert all(str(c.get("source") or "").startswith("strategy::") for c in citations)
    assert all(float(c.get("citation_confidence") or 0.0) >= 0.7 for c in citations)


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
    assert generation.get("schema_contract_hint_present") is True
    assert generation.get("input_context_key_count") == 2
    assert generation.get("retrieval_prompt_hit_count") == 1
    assert generation.get("retrieval_trace_hint_present") is True
    assert len(citations) == 2
    assert all(
        c.get("citation_type") in {"rag_result", "rag_low_confidence", "fallback_namespace", "strategy_reference"}
        for c in citations
    )


def test_mel_llm_prompt_receives_full_input_context_and_schema_contract(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: True)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Donor indicator guidance excerpt with baseline and target hints"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p5_c1", "chunk_id": "usaid_ads201_p5_c1", "page": 5}]],
            "ids": [["usaid_ads201_p5_c1"]],
            "distances": [[0.08]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    captured: dict[str, object] = {}

    def fake_llm_structured_mel(**kwargs):
        captured["input_context"] = kwargs.get("input_context")
        captured["schema_contract_hint"] = kwargs.get("schema_contract_hint")
        captured["retrieval_trace_hint"] = kwargs.get("retrieval_trace_hint")
        return (
            {
                "indicators": [
                    {
                        "indicator_id": "IND_501",
                        "name": "Civil servants certified on AI policy",
                        "justification": "Tracks capability uptake.",
                        "citation": "usaid_ads201_p5_c1",
                        "baseline": "0",
                        "target": "400",
                        "evidence_excerpt": "Donor indicator guidance excerpt with baseline and target hints",
                    }
                ]
            },
            "llm:stub-mel-model",
            None,
        )

    monkeypatch.setattr(mel_module, "_llm_structured_mel", fake_llm_structured_mel)

    state = _base_state(llm_mode=True)
    state["input_context"] = {
        "project": "AI Civil Service Training",
        "country": "Kazakhstan",
        "sector": "Public Administration",
        "duration_months": 24,
    }
    state["input"] = dict(state["input_context"])
    out = mel_module.mel_assign_indicators(state)
    generation = out.get("mel_generation_meta") or {}

    assert generation.get("llm_used") is True
    assert generation.get("schema_contract_hint_present") is True
    assert generation.get("input_context_key_count") == 4
    assert generation.get("retrieval_prompt_hit_count") == 1
    assert generation.get("retrieval_trace_hint_present") is True
    assert captured.get("input_context") == state["input_context"]
    schema_hint = str(captured.get("schema_contract_hint") or "")
    assert schema_hint
    assert "indicators" in schema_hint
    retrieval_hint = str(captured.get("retrieval_trace_hint") or "")
    assert retrieval_hint
    assert "used_results" in retrieval_hint


def test_mel_deterministic_mode_replaces_placeholder_baseline_target(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Training completion tracking guidance for civil servants"]],
            "metadatas": [
                [
                    {
                        "doc_id": "usaid_ads201_p18_c2",
                        "chunk_id": "usaid_ads201_p18_c2",
                        "page": 18,
                        "name": "Civil servants trained on AI governance",
                        "baseline": "TBD",
                        "target": "",
                    }
                ]
            ],
            "ids": [["usaid_ads201_p18_c2"]],
            "distances": [[0.06]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=False)
    state["input_context"]["duration_months"] = 24
    state["input_context"]["budget"] = 1_800_000

    out = mel_module.mel_assign_indicators(state)
    indicator = out["logframe_draft"]["indicators"][0]

    assert not _is_placeholder(indicator.get("baseline"))
    assert not _is_placeholder(indicator.get("target"))
    assert "tbd" not in str(indicator.get("baseline", "")).lower()
    assert "tbd" not in str(indicator.get("target", "")).lower()


def test_mel_emergency_fallback_indicator_uses_concrete_baseline_target(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: False)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=True)
    state["input_context"]["duration_months"] = 18

    out = mel_module.mel_assign_indicators(state)
    indicator = out["logframe_draft"]["indicators"][0]

    assert not _is_placeholder(indicator.get("baseline"))
    assert not _is_placeholder(indicator.get("target"))
    assert indicator.get("baseline") != indicator.get("target")


def test_mel_preserves_explicit_baseline_target_from_retrieval_metadata(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Operational KPI guidance for turnaround times"]],
            "metadatas": [
                [
                    {
                        "doc_id": "usaid_ads201_p22_c1",
                        "chunk_id": "usaid_ads201_p22_c1",
                        "page": 22,
                        "name": "Case processing time",
                        "baseline": "90 days",
                        "target": "60 days",
                    }
                ]
            ],
            "ids": [["usaid_ads201_p22_c1"]],
            "distances": [[0.04]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=False)

    out = mel_module.mel_assign_indicators(state)
    indicator = out["logframe_draft"]["indicators"][0]

    assert indicator["baseline"] == "90 days"
    assert indicator["target"] == "60 days"
