from __future__ import annotations

from grantflow.swarm.critic_rules import evaluate_rule_based_critic
from grantflow.swarm.nodes.critic import (
    _advisory_llm_findings_context,
    _apply_advisory_llm_score_cap,
    _citation_grounding_context,
    _combine_critic_scores,
    _downgrade_advisory_llm_findings,
    red_team_critic,
)


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


def test_advisory_llm_findings_are_downgraded_and_score_penalty_is_capped():
    class _RuleCheck:
        def __init__(self, status: str):
            self.status = status

    class _RuleReport:
        def __init__(self):
            self.fatal_flaws = []
            self.checks = [_RuleCheck("pass")]

    state = {
        "citations": [
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.25},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.27},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.29},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.24},
            {"stage": "mel", "citation_type": "rag_result", "citation_confidence": 0.85},
        ]
    }
    llm_items = [
        {
            "code": "LLM_REVIEW_FLAG_1",
            "severity": "medium",
            "section": "logframe",
            "message": "Lack of defined baselines and targets for indicators, making it impossible to measure progress effectively.",
            "source": "llm",
        },
        {
            "code": "LLM_REVIEW_FLAG_2",
            "severity": "medium",
            "section": "logframe",
            "message": "Absence of detailed evidence excerpts to justify the selection of each indicator, reducing credibility.",
            "source": "llm",
        },
        {
            "code": "LLM_REVIEW_FLAG_3",
            "severity": "medium",
            "section": "toc",
            "message": "The Theory of Change objectives are not sufficiently specific and measurable.",
            "source": "llm",
        },
    ]

    advisory_ctx = _advisory_llm_findings_context(state=state, rule_report=_RuleReport(), llm_fatal_flaw_items=llm_items)
    assert advisory_ctx["applies"] is True
    downgraded, meta = _downgrade_advisory_llm_findings(llm_items, advisory_ctx=advisory_ctx)
    assert meta is not None and meta["applied"] is True
    assert all(item["severity"] == "low" for item in downgraded)

    combined, score_meta = _apply_advisory_llm_score_cap(
        combined_score=7.75,
        rule_score=9.25,
        llm_score=4.5,
        advisory_ctx=advisory_ctx,
    )
    assert combined == 8.5
    assert score_meta is not None and score_meta["applied"] is True


def test_usaid_early_draft_llm_findings_are_treated_as_advisory_when_grounded():
    class _RuleCheck:
        def __init__(self, status: str):
            self.status = status

    class _RuleReport:
        def __init__(self):
            self.fatal_flaws = []
            self.checks = [_RuleCheck("pass")]

    state = {
        "citations": [
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.51},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.49},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.53},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.47},
            {"stage": "mel", "citation_type": "rag_result", "citation_confidence": 0.8},
        ]
    }
    llm_items = [
        {
            "code": "LLM_REVIEW_FLAG_1",
            "severity": "medium",
            "section": "toc",
            "message": (
                "Weak causal links between Outputs and IRs: The proposal lacks detailed explanation on how training "
                "modules and workshops will lead to increased AI literacy and skills."
            ),
            "source": "llm",
        },
        {
            "code": "LLM_REVIEW_FLAG_2",
            "severity": "medium",
            "section": "toc",
            "message": (
                "Unrealistic assumptions: The proposal assumes civil servants are motivated to participate without "
                "evidence or strategies to sustain this motivation."
            ),
            "source": "llm",
        },
        {
            "code": "LLM_REVIEW_FLAG_3",
            "severity": "medium",
            "section": "general",
            "message": (
                "Missing cross-cutting themes: While gender equality is mentioned, the proposal lacks a detailed "
                "plan for implementation and measurement."
            ),
            "source": "llm",
        },
    ]

    advisory_ctx = _advisory_llm_findings_context(state=state, rule_report=_RuleReport(), llm_fatal_flaw_items=llm_items)
    assert advisory_ctx["applies"] is True
    downgraded, meta = _downgrade_advisory_llm_findings(llm_items, advisory_ctx=advisory_ctx)
    assert meta is not None and meta["downgraded_count"] == 3
    assert all(item["severity"] == "low" for item in downgraded)


def test_advisory_llm_findings_allow_good_enough_architect_grounding_without_fallback():
    class _RuleCheck:
        def __init__(self, status: str):
            self.status = status

    class _RuleReport:
        def __init__(self):
            self.fatal_flaws = []
            self.checks = [_RuleCheck("pass")]

    state = {
        "citations": [
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.55},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.52},
            {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.48},
            {"stage": "architect", "citation_type": "rag_low_confidence", "citation_confidence": 0.28},
            {"stage": "architect", "citation_type": "rag_low_confidence", "citation_confidence": 0.27},
            {"stage": "mel", "citation_type": "rag_result", "citation_confidence": 0.8},
        ]
    }
    llm_items = [
        {
            "code": "LLM_REVIEW_FLAG_1",
            "severity": "medium",
            "section": "toc",
            "message": "Weak causal links between Outputs and IRs: draft lacks a detailed causal explanation.",
            "source": "llm",
        }
    ]

    advisory_ctx = _advisory_llm_findings_context(state=state, rule_report=_RuleReport(), llm_fatal_flaw_items=llm_items)
    assert advisory_ctx["applies"] is True
    assert advisory_ctx["architect_threshold_hit_rate"] == 0.6
    assert advisory_ctx["architect_rag_low_ratio"] == 0.4
