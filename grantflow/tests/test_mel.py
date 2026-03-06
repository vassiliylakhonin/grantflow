from __future__ import annotations

from pydantic import BaseModel, Field

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


def test_mel_grounded_confidence_bonus_rewards_complete_rank1_hits():
    bonus = mel_module._mel_grounded_confidence_bonus(
        {
            "rank": 1,
            "retrieval_rank": 1,
            "retrieval_confidence": 0.46,
            "doc_id": "doc-1",
            "chunk_id": "chunk-1",
        },
        traceability_status="complete",
    )
    assert 0.0 < bonus <= 0.1


def test_mel_deterministic_mode_generates_logframe_and_citations(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["USAID indicator guidance for water service quality"]],
            "metadatas": [
                [
                    {
                        "doc_id": "usaid_ads201_p12_c0",
                        "chunk_id": "usaid_ads201_p12_c0",
                        "page": 12,
                        "indicator_code": "EG.3.2-27",
                        "frequency": "quarterly",
                        "formula": "(Numerator / Denominator) * 100",
                        "data_source": "PMP indicator tracking dataset",
                    }
                ]
            ],
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
    assert str(citations[0]["toc_statement_path"]).startswith("toc.")
    assert str(citations[0]["statement_path"]).startswith("toc.")
    assert str(citations[0]["result_level"]) in {"impact", "outcome", "output"}
    assert indicators[0]["indicator_code"] == "EG.3.2-27"
    assert indicators[0]["frequency"] == "quarterly"
    assert indicators[0]["formula"] == "(Numerator / Denominator) * 100"
    assert indicators[0]["data_source"] == "PMP indicator tracking dataset"
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
    assert all(str(c.get("toc_statement_path") or "").startswith("toc.") for c in citations)
    assert all(str(c.get("statement_path") or "").startswith("toc.") for c in citations)


def test_mel_deterministic_mode_builds_multiple_indicators_from_toc_results(monkeypatch):
    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    state = _base_state(llm_mode=False)
    state["toc_draft"] = {
        "toc": {
            "project_goal": "Improve digital service quality in municipal agencies.",
            "development_objectives": [
                {
                    "description": "Civil servants apply AI-assisted service workflows in daily operations.",
                },
                {
                    "description": "Municipal service turnaround time is reduced for priority services.",
                },
            ],
        }
    }

    out = mel_module.mel_assign_indicators(state)
    indicators = out["logframe_draft"]["indicators"]
    citations = [c for c in (out.get("citations") or []) if isinstance(c, dict) and c.get("stage") == "mel"]
    generation = out.get("mel_generation_meta") or {}

    assert len(indicators) >= 2
    assert all(str(item.get("toc_statement_path") or "").startswith("toc.") for item in indicators)
    assert all(str(item.get("result_level") or "") in {"impact", "outcome", "output"} for item in indicators)
    assert all(str(item.get("frequency") or "") for item in indicators)
    assert all(str(item.get("formula") or "") for item in indicators)
    assert all(str(item.get("definition") or "") for item in indicators)
    assert all(str(item.get("data_source") or "") for item in indicators)
    assert all(isinstance(item.get("disaggregation"), list) for item in indicators)
    assert all(c.get("citation_type") == "strategy_reference" for c in citations)
    assert all(str(c.get("toc_statement_path") or "").startswith("toc.") for c in citations)
    assert all(str(c.get("statement_path") or "").startswith("toc.") for c in citations)
    assert all(str(c.get("result_level") or "") in {"impact", "outcome", "output"} for c in citations)
    assert generation.get("engine") == "deterministic:toc_results_template"
    assert generation.get("deterministic_source") == "toc_results_template"


def test_mel_formula_prefers_institution_logic_over_people_logic():
    assert (
        mel_module._default_indicator_formula(
            "Strengthen institutional capacity for youth employment and SME skills delivery",
            result_level="outcome",
        )
        == "Count of institutions/organizations meeting defined performance or adoption criteria"
    )


def test_mel_deterministic_justification_is_donor_shaped():
    eu_text = mel_module._deterministic_indicator_justification(
        donor_id="eu",
        statement_path="toc.specific_objectives[0].title",
    )
    wb_text = mel_module._deterministic_indicator_justification(
        donor_id="worldbank",
        statement_path="toc.objectives[0].title",
    )

    assert "eu intervention-logic indicator" in eu_text.lower()
    assert "world bank-style results framework indicator" in wb_text.lower()


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


def test_mel_query_variants_include_eu_and_worldbank_specific_terms():
    eu_state = {
        "donor_id": "eu",
        "input_context": {"project": "Digital Governance", "country": "Moldova"},
        "toc_draft": {
            "toc": {
                "overall_objective": {"title": "Improve digital governance performance"},
                "specific_objectives": [{"title": "Strengthen institutional capacity"}],
                "expected_outcomes": [{"expected_change": "Institutions demonstrate measurable improvements"}],
            }
        },
    }
    wb_state = {
        "donor_id": "worldbank",
        "input_context": {"project": "Public Sector Performance", "country": "Uzbekistan"},
        "toc_draft": {
            "toc": {
                "project_development_objective": "Improve service delivery performance",
                "objectives": [{"title": "Strengthen institutional performance"}],
                "results_chain": [{"description": "Agencies implement workflow improvements"}],
            }
        },
    }

    eu_query = mel_module._build_query_text(eu_state)
    wb_query = mel_module._build_query_text(wb_state)
    eu_variants = mel_module._query_variants(eu_state, eu_query, max_variants=6)
    wb_variants = mel_module._query_variants(wb_state, wb_query, max_variants=6)

    eu_combined = " || ".join(eu_variants).lower()
    wb_combined = " || ".join(wb_variants).lower()
    assert "means of verification" in eu_combined
    assert "specific objectives" in eu_combined
    assert "expected outcomes" in eu_combined
    assert "pdo indicators" in wb_combined
    assert "intermediate results indicators" in wb_combined
    assert "implementation status results report" in wb_combined


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


def test_mel_llm_mode_uses_strategy_mel_schema_contract(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: True)

    class DonorSpecificIndicator(BaseModel):
        indicator_id: str
        name: str
        justification: str
        citation: str
        baseline: str = "0"
        target: str = "1"
        evidence_excerpt: str | None = None

    class DonorSpecificMELDraft(BaseModel):
        mel_indicators: list[DonorSpecificIndicator] = Field(default_factory=list)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Donor indicator guidance excerpt"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p10_c1", "chunk_id": "usaid_ads201_p10_c1", "page": 10}]],
            "ids": [["usaid_ads201_p10_c1"]],
            "distances": [[0.1]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(strategy, "get_mel_schema", lambda: DonorSpecificMELDraft)
    captured: dict[str, object] = {}

    def fake_llm_structured_mel(**kwargs):
        captured["schema_cls"] = kwargs.get("schema_cls")
        return (
            {
                "mel_indicators": [
                    {
                        "indicator_id": "IND_777",
                        "name": "Civil servants trained on AI governance",
                        "justification": "Tracks capability development outcome.",
                        "citation": "usaid_ads201_p10_c1",
                        "baseline": "0",
                        "target": "300",
                        "evidence_excerpt": "Donor indicator guidance excerpt",
                    }
                ]
            },
            "llm:stub-mel-model",
            None,
        )

    monkeypatch.setattr(mel_module, "_llm_structured_mel", fake_llm_structured_mel)

    state = _base_state(llm_mode=True)
    state["strategy"] = strategy
    state["donor_strategy"] = strategy
    out = mel_module.mel_assign_indicators(state)
    generation = out.get("mel_generation_meta") or {}
    indicators = out["logframe_draft"]["indicators"]

    assert captured.get("schema_cls") is DonorSpecificMELDraft
    assert generation.get("schema_name") == "DonorSpecificMELDraft"
    assert generation.get("llm_used") is True
    assert len(indicators) == 1
    assert indicators[0]["indicator_id"] == "IND_777"


def test_mel_llm_mode_preserves_strategy_specific_indicator_fields(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: True)

    class DonorSpecificIndicator(BaseModel):
        indicator_id: str
        name: str
        justification: str
        citation: str
        baseline: str = "0"
        target: str = "1"
        indicator_code: str | None = None
        frequency: str | None = None
        evidence_excerpt: str | None = None

    class DonorSpecificMELDraft(BaseModel):
        mel_indicators: list[DonorSpecificIndicator] = Field(default_factory=list)

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Donor indicator guidance excerpt"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p10_c1", "chunk_id": "usaid_ads201_p10_c1", "page": 10}]],
            "ids": [["usaid_ads201_p10_c1"]],
            "distances": [[0.1]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    strategy = DonorFactory.get_strategy("usaid")
    monkeypatch.setattr(strategy, "get_mel_schema", lambda: DonorSpecificMELDraft)

    def fake_llm_structured_mel(**kwargs):  # noqa: ARG001
        return (
            {
                "mel_indicators": [
                    {
                        "indicator_id": "IND_778",
                        "name": "Civil servants trained on AI governance",
                        "justification": "Tracks capability development outcome.",
                        "citation": "usaid_ads201_p10_c1",
                        "baseline": "0",
                        "target": "300",
                        "indicator_code": "EG.3.2-27",
                        "frequency": "quarterly",
                        "evidence_excerpt": "Donor indicator guidance excerpt",
                    }
                ]
            },
            "llm:stub-mel-model",
            None,
        )

    monkeypatch.setattr(mel_module, "_llm_structured_mel", fake_llm_structured_mel)

    state = _base_state(llm_mode=True)
    state["strategy"] = strategy
    state["donor_strategy"] = strategy
    out = mel_module.mel_assign_indicators(state)
    indicators = out["logframe_draft"]["indicators"]

    assert len(indicators) == 1
    assert indicators[0]["indicator_id"] == "IND_778"
    assert indicators[0]["indicator_code"] == "EG.3.2-27"
    assert indicators[0]["frequency"] == "quarterly"


def test_mel_llm_tries_fallback_model_chain_and_selects_first_success(monkeypatch):
    monkeypatch.setattr(mel_module, "openai_compatible_llm_available", lambda: True)
    monkeypatch.setattr(mel_module.config.llm, "mel_model", "model-primary")
    monkeypatch.setattr(mel_module.config.llm, "reasoning_model", "model-secondary")
    monkeypatch.setattr(mel_module.config.llm, "cheap_model", "model-cheap")

    def fake_query(*, namespace, query_texts, n_results):  # noqa: ARG001
        return {
            "documents": [["Official donor indicator guidance excerpt"]],
            "metadatas": [[{"doc_id": "usaid_ads201_p10_c1", "chunk_id": "usaid_ads201_p10_c1", "page": 10}]],
            "ids": [["usaid_ads201_p10_c1"]],
            "distances": [[0.1]],
        }

    monkeypatch.setattr(mel_module.vector_store, "query", fake_query)
    calls: list[str] = []

    def fake_llm_structured_mel(**kwargs):
        model_name = str(kwargs.get("model_name") or "")
        calls.append(model_name)
        if model_name == "model-primary":
            return None, None, "primary model unavailable"
        if model_name == "model-secondary":
            return (
                {
                    "indicators": [
                        {
                            "indicator_id": "IND_201",
                            "name": "Officials trained on AI governance",
                            "justification": "Tracks workforce capability improvements.",
                            "citation": "usaid_ads201_p10_c1",
                            "baseline": "0",
                            "target": "300",
                            "evidence_excerpt": "Official donor indicator guidance excerpt",
                        }
                    ]
                },
                "llm:model-secondary",
                None,
            )
        return None, None, "unexpected model"

    monkeypatch.setattr(mel_module, "_llm_structured_mel", fake_llm_structured_mel)

    state = _base_state(llm_mode=True)
    out = mel_module.mel_assign_indicators(state)
    generation = out.get("mel_generation_meta") or {}

    assert generation.get("llm_used") is True
    assert generation.get("engine") == "llm:model-secondary"
    assert generation.get("llm_selected_model") == "model-secondary"
    assert generation.get("llm_attempt_count") == 2
    assert generation.get("llm_models_tried") == ["model-primary", "model-secondary"]
    assert calls == ["model-primary", "model-secondary"]


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


def test_mel_donor_aware_placeholder_target_profiles():
    usaid_baseline, usaid_target = mel_module._resolve_baseline_target(
        baseline_raw="TBD",
        target_raw="TBD",
        indicator_name="Service coverage rate",
        input_context={},
        idx=0,
        donor_id="usaid",
    )
    eu_baseline, eu_target = mel_module._resolve_baseline_target(
        baseline_raw="TBD",
        target_raw="TBD",
        indicator_name="Service coverage rate",
        input_context={},
        idx=0,
        donor_id="eu",
    )

    assert usaid_baseline == "0%"
    assert eu_baseline == "0%"
    assert usaid_target == "30%"
    assert eu_target == "20%"


def test_mel_donor_aware_institution_and_organization_targets():
    wb_baseline, wb_target = mel_module._resolve_baseline_target(
        baseline_raw="TBD",
        target_raw="TBD",
        indicator_name="Institutional performance score",
        input_context={},
        idx=0,
        donor_id="worldbank",
        result_level="impact",
    )
    state_baseline, state_target = mel_module._resolve_baseline_target(
        baseline_raw="TBD",
        target_raw="TBD",
        indicator_name="Independent media organizations adopting safety protocols",
        input_context={},
        idx=0,
        donor_id="state_department",
        result_level="outcome",
    )

    assert wb_baseline == "0 institutions"
    assert wb_target == "8 institutions"
    assert state_baseline == "0 organizations"
    assert state_target == "6 organizations"


def test_mel_state_department_impact_media_resilience_targets_use_organizations():
    baseline, target = mel_module._resolve_baseline_target(
        baseline_raw="TBD",
        target_raw="TBD",
        indicator_name="Improve Independent Media Resilience outcomes in Georgia.",
        input_context={},
        idx=0,
        donor_id="state_department",
        result_level="impact",
    )

    assert baseline == "0 organizations"
    assert target == "6 organizations"


def test_mel_donor_aware_default_frequency_profiles():
    usaid_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_001",
            "name": "Training completion rate",
            "justification": "Tracks completion performance.",
            "citation": "usaid_ads201",
            "baseline": "0%",
            "target": "30%",
            "result_level": "output",
        },
        idx=0,
        namespace="usaid_ads201",
        donor_id="usaid",
        input_context={},
    )
    eu_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_001",
            "name": "Training completion rate",
            "justification": "Tracks completion performance.",
            "citation": "eu_intpa",
            "baseline": "0%",
            "target": "20%",
            "result_level": "outcome",
        },
        idx=0,
        namespace="eu_intpa",
        donor_id="eu",
        input_context={},
    )

    assert usaid_item is not None
    assert eu_item is not None
    assert usaid_item["frequency"] == "quarterly"
    assert eu_item["frequency"] == "semiannual"
    assert str(usaid_item["formula"])
    assert str(eu_item["data_source"])


def test_mel_donor_aware_indicator_governance_defaults():
    eu_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_010",
            "name": "Service coverage rate",
            "justification": "Tracks service performance.",
            "citation": "eu_intpa",
            "baseline": "0%",
            "target": "20%",
            "result_level": "outcome",
        },
        idx=0,
        namespace="eu_intpa",
        donor_id="eu",
        input_context={},
    )
    wb_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_011",
            "name": "Institutional performance score",
            "justification": "Tracks agency results performance.",
            "citation": "worldbank_ads301",
            "baseline": "0",
            "target": "8",
            "result_level": "impact",
        },
        idx=0,
        namespace="worldbank_ads301",
        donor_id="worldbank",
        input_context={},
    )

    assert eu_item is not None
    assert wb_item is not None
    assert "means of verification" in str(eu_item["definition"]).lower()
    assert eu_item["owner"] == "Project M&E manager and partner focal points"
    assert "means of verification annexes" in str(eu_item["means_of_verification"]).lower()
    assert eu_item["disaggregation"] == ["location", "service_type"]
    assert wb_item["owner"] == "PIU M&E specialist and implementing agency focal points"
    assert "results framework" in str(wb_item["definition"]).lower()
    assert "national administrative statistics" in str(wb_item["means_of_verification"]).lower()


def test_mel_worldbank_and_state_department_defaults_shape_indicator_targets():
    wb_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_020",
            "name": "Institutional performance score",
            "justification": "Tracks agency performance improvements.",
            "citation": "worldbank_ads301",
            "baseline": "TBD",
            "target": "TBD",
            "result_level": "impact",
        },
        idx=0,
        namespace="worldbank_ads301",
        donor_id="worldbank",
        input_context={},
    )
    state_item = mel_module._normalize_indicator_item(
        {
            "indicator_id": "IND_021",
            "name": "Independent media organizations adopting safety protocols",
            "justification": "Tracks resilience adoption.",
            "citation": "us_state_department_guidance",
            "baseline": "TBD",
            "target": "TBD",
            "result_level": "outcome",
        },
        idx=0,
        namespace="us_state_department_guidance",
        donor_id="state_department",
        input_context={},
    )

    assert wb_item is not None
    assert state_item is not None
    assert wb_item["baseline"] == "0 institutions"
    assert wb_item["target"] == "8 institutions"
    assert state_item["baseline"] == "0 organizations"
    assert state_item["target"] == "6 organizations"


def test_mel_copies_owner_and_means_of_verification_from_retrieval_hit():
    enriched = mel_module._copy_optional_indicator_fields_from_hit(
        {"indicator_id": "IND_100", "name": "Indicator"},
        {
            "owner": "Custom MEL owner",
            "means_of_verification": "Verified registry extract",
        },
    )

    assert enriched["owner"] == "Custom MEL owner"
    assert enriched["means_of_verification"] == "Verified registry extract"
