from __future__ import annotations

from grantflow.swarm.nodes.discovery import validate_input_richness
from grantflow.swarm.state_contract import (
    normalize_state_contract,
    set_state_donor_strategy,
    state_donor_id,
    state_donor_strategy,
    state_input_context,
    state_iteration,
    state_rag_namespace,
)


def test_normalize_state_contract_unifies_aliases_and_defaults():
    state = {
        "donor": "USAID",
        "input": {"project": "AI upskilling"},
        "critic_score": "4.5",
        "llm_mode": "true",
        "needs_revision": "0",
        "critic_notes": [],
    }

    out = normalize_state_contract(state)
    assert out["donor_id"] == "usaid"
    assert out["donor"] == "usaid"
    assert out["input_context"] == {"project": "AI upskilling"}
    assert out["input"] == {"project": "AI upskilling"}
    assert out["critic_score"] == 4.5
    assert out["quality_score"] == 4.5
    assert out["llm_mode"] is True
    assert out["needs_revision"] is False
    assert out["critic_notes"] == {}
    assert out["errors"] == []


def test_state_helpers_prefer_canonical_fields():
    state = {
        "donor_id": "eu",
        "donor": "usaid",
        "input_context": {"project": "Digital Governance"},
        "input": {"project": "Legacy Value"},
        "iteration_count": "3",
        "iteration": "99",
    }

    assert state_donor_id(state) == "eu"
    assert state_input_context(state) == {"project": "Digital Governance"}
    assert state_iteration(state) == 3


def test_state_strategy_helpers_prefer_canonical_field():
    state = {"donor_strategy": "canonical", "strategy": "legacy"}
    assert state_donor_strategy(state) == "canonical"

    state = {"strategy": "legacy_only"}
    assert state_donor_strategy(state) == "legacy_only"

    set_state_donor_strategy(state, "normalized")
    assert state["donor_strategy"] == "normalized"
    assert state["strategy"] == "normalized"


def test_discovery_normalizes_state_contract_for_legacy_inputs():
    state = {
        "donor": "USAID",
        "input": {"project": "Water Sanitation", "country": "Kenya"},
        "critic_notes": [],
    }

    out = validate_input_richness(state)
    assert out["donor_id"] == "usaid"
    assert out["donor"] == "usaid"
    assert out["input_context"]["project"] == "Water Sanitation"
    assert out["input"]["country"] == "Kenya"
    assert isinstance(out["critic_notes"], dict)


def test_normalize_state_contract_coerces_string_lists_and_max_iterations():
    state = {
        "donor": "USAID",
        "input": {"project": "Water Sanitation"},
        "critic_feedback_history": ["ok", 123, None],
        "errors": "single error",
        "max_iterations": "0",
    }

    out = normalize_state_contract(state)
    assert out["critic_feedback_history"] == ["ok", "123"]
    assert out["errors"] == ["single error"]
    assert out["max_iterations"] == 1


def test_state_rag_namespace_prefers_canonical_field_and_normalizes_alias():
    state = {"rag_namespace": "tenant_a/usaid_ads201", "retrieval_namespace": "legacy/value"}
    assert state_rag_namespace(state) == "tenant_a/usaid_ads201"

    alias_only = {"retrieval_namespace": "tenant_b/eu_intpa"}
    out = normalize_state_contract(alias_only)
    assert out["rag_namespace"] == "tenant_b/eu_intpa"
    assert out["retrieval_namespace"] == "tenant_b/eu_intpa"
