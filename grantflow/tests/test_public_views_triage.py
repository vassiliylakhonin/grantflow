from __future__ import annotations

from grantflow.api.public_views import _finding_recommended_action


def test_finding_recommended_action_uses_donor_specific_logic_language():
    action = _finding_recommended_action(
        {
            "code": "USAID_DO_MISSING",
            "section": "toc",
            "message": "USAID ToC is missing Development Objectives.",
            "severity": "high",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "DO -> IR -> Output" in action
    assert "USAID results hierarchy" in action


def test_finding_recommended_action_uses_donor_specific_measurement_language():
    action = _finding_recommended_action(
        {
            "code": "MEL_PLACEHOLDER_TARGETS",
            "section": "logframe",
            "message": "Most indicators still use placeholder baseline/target values.",
            "severity": "medium",
            "status": "open",
        },
        donor_id="worldbank",
    )
    assert "placeholder baseline and target values" in action.lower()
    assert "world bank results framework and pdo package" in action.lower()


def test_finding_recommended_action_uses_donor_specific_compliance_language():
    action = _finding_recommended_action(
        {
            "code": "EU_OVERALL_OBJECTIVE_MISSING",
            "section": "toc",
            "message": "EU ToC is missing the overall objective needed to anchor the intervention logic.",
            "severity": "high",
            "status": "open",
        },
        donor_id="eu",
    )
    assert "overall objective" in action.lower()
    assert "verification intent" in action.lower()


def test_finding_recommended_action_makes_grounding_gap_more_specific():
    action = _finding_recommended_action(
        {
            "code": "TOC_EVIDENCE_GAP",
            "section": "toc",
            "message": "Outcome chain lacks grounded support and relies on fallback evidence.",
            "severity": "high",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "fallback evidence" in action.lower()
    assert "pmp references" in action.lower()


def test_finding_recommended_action_makes_placeholder_targets_more_specific():
    action = _finding_recommended_action(
        {
            "code": "BASELINE_TARGET_MISSING",
            "section": "logframe",
            "message": "Indicators still use placeholder baseline and target values.",
            "severity": "medium",
            "status": "open",
        },
        donor_id="eu",
    )
    assert "placeholder baseline and target values" in action.lower()
    assert "eu intervention logic and verification package" in action.lower()


def test_finding_recommended_action_makes_boilerplate_logic_more_specific():
    action = _finding_recommended_action(
        {
            "code": "TOC_BOILERPLATE_REPETITION",
            "section": "toc",
            "message": "Theory of Change contains repeated boilerplate narrative across multiple sections.",
            "severity": "low",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "repeated boilerplate" in action.lower()
    assert "reviewer-ready" in action.lower()
