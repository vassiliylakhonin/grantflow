from __future__ import annotations

from grantflow.swarm.grounding_gate import evaluate_grounding_gate


def test_grounding_gate_passes_when_mode_off_even_with_weak_signals():
    state = {
        "citations": [
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
        ],
        "architect_retrieval": {"enabled": True, "hits_count": 0},
    }
    gate = evaluate_grounding_gate(state, mode="off", min_citations_for_calibration=1)
    assert gate["mode"] == "off"
    assert gate["passed"] is True
    assert gate["blocking"] is False
    assert gate["reasons"]


def test_grounding_gate_warn_mode_flags_fallback_dominance_without_blocking():
    state = {
        "citations": [
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_claim_support", "citation_confidence": 0.9},
        ],
        "architect_retrieval": {"enabled": True, "hits_count": 0},
    }
    gate = evaluate_grounding_gate(state, mode="warn", min_citations_for_calibration=5)
    assert gate["mode"] == "warn"
    assert gate["passed"] is False
    assert gate["blocking"] is False
    assert "architect_retrieval_no_hits" in gate["reasons"]
    assert "fallback_or_low_rag_citations_dominate" in gate["reasons"]


def test_grounding_gate_strict_blocks_on_weak_signals():
    state = {
        "citations": [
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
        ],
        "architect_retrieval": {"enabled": True, "hits_count": 0},
    }
    gate = evaluate_grounding_gate(state, mode="strict", min_citations_for_calibration=5)
    assert gate["mode"] == "strict"
    assert gate["passed"] is False
    assert gate["blocking"] is True
    assert gate["severity"] == "high"
