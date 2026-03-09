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
    assert "ISR-style review" in action
    assert "baseline" in action.lower()


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
