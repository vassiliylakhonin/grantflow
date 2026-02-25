from __future__ import annotations

from grantflow.swarm.critic_rules import evaluate_rule_based_critic
from grantflow.swarm.nodes.critic import red_team_critic


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
