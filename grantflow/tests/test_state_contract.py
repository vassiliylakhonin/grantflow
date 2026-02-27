from __future__ import annotations

from grantflow.swarm.nodes.discovery import validate_input_richness
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id, state_input_context


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
    }

    assert state_donor_id(state) == "eu"
    assert state_input_context(state) == {"project": "Digital Governance"}


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
