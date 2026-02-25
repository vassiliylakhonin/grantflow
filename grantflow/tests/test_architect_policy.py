from __future__ import annotations

import pytest

from grantflow.swarm.nodes.architect_policy import (
    ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES,
    ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD,
    architect_claim_confidence_threshold,
    architect_donor_prompt_constraints,
    sanitize_validation_error_hint,
)


def test_architect_prompt_constraints_include_common_guardrails_for_unknown_donor():
    text = architect_donor_prompt_constraints("unknown")
    assert "schema-valid object" in text
    assert "Do not invent citations" in text


@pytest.mark.parametrize(
    ("donor_id", "needle"),
    [
        ("usaid", "USAID hierarchy"),
        ("eu", "EU intervention logic"),
        ("giz", "implementation feasibility"),
        ("worldbank", "development operations"),
        ("state_department", "stakeholder mapping"),
        ("us_state_department", "stakeholder mapping"),
    ],
)
def test_architect_prompt_constraints_include_donor_specific_guidance(donor_id, needle):
    text = architect_donor_prompt_constraints(donor_id)
    assert needle in text


def test_sanitize_validation_error_hint_compacts_lines_and_limits_length():
    raw = "\n".join(
        [
            "line one",
            "  ",
            "line two",
            "line three",
            "line four",
            "line five should be dropped",
        ]
    )
    out = sanitize_validation_error_hint(raw, max_chars=40)
    assert out is not None
    assert "line one" in out
    assert "line two" in out
    assert "|" in out
    assert len(out) <= 40


def test_sanitize_validation_error_hint_returns_none_for_empty_values():
    assert sanitize_validation_error_hint(None) is None
    assert sanitize_validation_error_hint("") is None
    assert sanitize_validation_error_hint("   \n  ") is None


def test_architect_threshold_uses_default_for_unknown_donor_and_section_tuning():
    base = architect_claim_confidence_threshold(donor_id="unknown", statement_path="toc.misc_field")
    goal = architect_claim_confidence_threshold(donor_id="unknown", statement_path="toc.project_goal")
    risk = architect_claim_confidence_threshold(donor_id="unknown", statement_path="toc.risks[0]")

    assert base == round(ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD, 2)
    assert goal > base
    assert risk > goal


def test_architect_threshold_uses_donor_override_and_caps_range():
    usaid_goal = architect_claim_confidence_threshold(donor_id="usaid", statement_path="toc.project_goal")
    usaid_assumption = architect_claim_confidence_threshold(donor_id="usaid", statement_path="toc.critical_assumptions[0]")

    assert usaid_goal >= ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES["usaid"]
    assert usaid_assumption > usaid_goal
    assert 0.1 <= usaid_assumption <= 0.95

