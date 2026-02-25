from __future__ import annotations

from grantflow.swarm.critic_rules import evaluate_rule_based_critic
from grantflow.swarm.nodes.critic import _citation_grounding_context, _combine_critic_scores, red_team_critic


def test_rule_based_critic_emits_structured_flaws_with_section_and_version():
    state = {
        "draft_versions": [
            {"version_id": "toc_v1", "sequence": 1, "section": "toc", "content": {}},
            {"version_id": "logframe_v1", "sequence": 2, "section": "logframe", "content": {}},
        ],
        "toc_validation": {"valid": False, "errors": ["missing field"], "schema_name": "GenericTOC"},
        "toc_draft": {"toc": {"project_goal": "Goal text"}},
        "logframe_draft": {"indicators": []},
        "citations": [],
    }
    report = evaluate_rule_based_critic(state)

    assert report.fatal_flaws
    flaws = [f.model_dump() if hasattr(f, "model_dump") else f.dict() for f in report.fatal_flaws]
    assert any(
        f["code"] == "TOC_SCHEMA_INVALID" and f["section"] == "toc" and f["version_id"] == "toc_v1" for f in flaws
    )
    assert any(
        f["code"] == "LOGFRAME_INDICATORS_MISSING" and f["section"] == "logframe" and f["version_id"] == "logframe_v1"
        for f in flaws
    )
    assert report.score < 8.0
    assert report.checks


def test_red_team_critic_uses_rules_without_llm_and_stores_structured_notes():
    state = {
        "donor_strategy": object(),
        "strategy": object(),
        "llm_mode": False,
        "max_iterations": 3,
        "iteration": 0,
        "iteration_count": 0,
        "toc_draft": {
            "toc": {"project_goal": "Improve access", "objectives": [{"title": "Obj", "description": "Desc"}]}
        },
        "logframe_draft": {"indicators": [{"indicator_id": "IND_001"}]},
        "citations": [
            {"stage": "architect", "statement_path": "toc.project_goal", "label": "doc", "used_for": "toc_claim"},
            {"stage": "mel", "label": "doc", "used_for": "IND_001"},
        ],
        "draft_versions": [
            {"version_id": "toc_v1", "sequence": 1, "section": "toc", "content": {}},
            {"version_id": "logframe_v1", "sequence": 2, "section": "logframe", "content": {}},
        ],
        "toc_validation": {"valid": True, "errors": [], "schema_name": "GenericTOC"},
        "critic_feedback_history": [],
    }

    out = red_team_critic(state)
    notes = out.get("critic_notes") or {}
    assert notes.get("engine") == "rules"
    assert isinstance(notes.get("fatal_flaws"), list)
    if notes.get("fatal_flaws"):
        flaw = notes["fatal_flaws"][0]
        assert flaw.get("finding_id")
        assert flaw.get("status") in {"open", "acknowledged", "resolved"}
    assert isinstance(notes.get("rule_checks"), list)
    assert "revision_instructions" in notes
    assert out.get("next_step") in {"architect", "end"}


def test_rule_based_critic_applies_usaid_donor_specific_checks():
    state = {
        "donor_id": "usaid",
        "draft_versions": [
            {"version_id": "toc_v1", "sequence": 1, "section": "toc", "content": {}},
            {"version_id": "logframe_v1", "sequence": 2, "section": "logframe", "content": {}},
        ],
        "toc_validation": {"valid": True, "errors": [], "schema_name": "USAIDTOC"},
        "toc_draft": {"toc": {"project_goal": "Improve services"}},
        "logframe_draft": {"indicators": [{"indicator_id": "IND_001"}]},
        "citations": [
            {"stage": "architect", "statement_path": "toc.project_goal", "label": "doc", "used_for": "toc_claim"},
            {"stage": "mel", "label": "doc", "used_for": "IND_001"},
        ],
    }

    report = evaluate_rule_based_critic(state)
    checks = [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in report.checks]
    flaws = [f.model_dump() if hasattr(f, "model_dump") else f.dict() for f in report.fatal_flaws]

    assert any(c["code"] == "USAID_DO_PRESENT" and c["status"] == "fail" for c in checks)
    assert any(c["code"] == "USAID_CRITICAL_ASSUMPTIONS_PRESENT" and c["status"] == "warn" for c in checks)
    assert any(f["code"] == "USAID_DO_MISSING" and f["section"] == "toc" for f in flaws)
    assert any(f["code"] == "USAID_ASSUMPTIONS_MISSING" and f["section"] == "toc" for f in flaws)


def test_red_team_critic_marks_sparse_input_brief_for_revision():
    state = {
        "donor_strategy": object(),
        "strategy": object(),
        "llm_mode": False,
        "max_iterations": 3,
        "iteration": 0,
        "iteration_count": 0,
        "input_context": {"project": "AI governance training"},
        "toc_draft": {
            "toc": {"project_goal": "Improve access", "objectives": [{"title": "Obj", "description": "Desc"}]}
        },
        "logframe_draft": {"indicators": [{"indicator_id": "IND_001"}]},
        "citations": [
            {"stage": "architect", "statement_path": "toc.project_goal", "label": "doc", "used_for": "toc_claim"},
            {"stage": "mel", "label": "doc", "used_for": "IND_001"},
        ],
        "draft_versions": [
            {"version_id": "toc_v1", "sequence": 1, "section": "toc", "content": {}},
            {"version_id": "logframe_v1", "sequence": 2, "section": "logframe", "content": {}},
        ],
        "toc_validation": {"valid": True, "errors": [], "schema_name": "GenericTOC"},
        "critic_feedback_history": [],
    }

    out = red_team_critic(state)
    notes = out.get("critic_notes") or {}
    flaws = notes.get("fatal_flaws") or []
    assert any((f or {}).get("code") == "INPUT_BRIEF_TOO_SPARSE" for f in flaws)
    assert out.get("needs_revision") is True
    assert out.get("next_step") == "architect"


def test_citation_grounding_context_tracks_fallback_and_weak_grounding():
    state = {
        "architect_retrieval": {"enabled": True, "hits_count": 0},
        "citations": [
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.25},
            {"citation_type": "rag_claim_support", "citation_confidence": 0.9},
        ],
    }

    ctx = _citation_grounding_context(state)
    assert ctx["citation_count"] == 5
    assert ctx["fallback_namespace_citation_count"] == 2
    assert ctx["rag_low_confidence_citation_count"] == 2
    assert ctx["low_confidence_citation_count"] == 4
    assert ctx["architect_retrieval_hits_count"] == 0
    assert ctx["weak_grounding"] is True
    assert "architect_retrieval_no_hits" in ctx["weak_grounding_reasons"]


def test_combine_critic_scores_caps_llm_penalty_in_weak_grounding_context():
    state = {
        "architect_retrieval": {"enabled": True, "hits_count": 0},
        "citations": [
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "fallback_namespace", "citation_confidence": 0.1},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
            {"citation_type": "rag_low_confidence", "citation_confidence": 0.2},
        ],
    }

    score, meta = _combine_critic_scores(rule_score=9.25, llm_score=3.0, state=state)
    assert score == 7.75  # 9.25 - capped 1.5 penalty
    assert meta is not None
    assert meta["applied"] is True
    assert meta["raw_llm_score"] == 3.0
    assert meta["calibrated_llm_score"] == 7.75


def test_combine_critic_scores_keeps_strict_min_when_grounding_is_not_weak():
    state = {
        "architect_retrieval": {"enabled": True, "hits_count": 4},
        "citations": [
            {"citation_type": "rag_claim_support", "citation_confidence": 0.92},
            {"citation_type": "rag_claim_support", "citation_confidence": 0.88},
        ],
    }

    score, meta = _combine_critic_scores(rule_score=9.25, llm_score=5.0, state=state)
    assert score == 5.0
    assert meta is not None
    assert meta["applied"] is False
