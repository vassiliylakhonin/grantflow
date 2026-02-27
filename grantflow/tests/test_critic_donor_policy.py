from __future__ import annotations

import pytest

from grantflow.swarm.critic_donor_policy import apply_donor_specific_toc_checks, normalized_donor_id


def _run_policy(donor_id: str, toc_payload):
    checks: list[dict] = []
    flaws: list[dict] = []

    def check_fn(**kwargs):
        checks.append(dict(kwargs))

    def add_flaw_fn(**kwargs):
        flaws.append(dict(kwargs))

    apply_donor_specific_toc_checks(
        state={"donor_id": donor_id},
        toc_payload=toc_payload,
        check_fn=check_fn,
        add_flaw_fn=add_flaw_fn,
    )
    return checks, flaws


def test_normalized_donor_id_prefers_donor_id_and_lowercases():
    assert normalized_donor_id({"donor_id": " USAID "}) == "usaid"
    assert normalized_donor_id({"donor": " GIZ "}) == "giz"


def test_unknown_donor_produces_no_checks_or_flaws():
    checks, flaws = _run_policy("unknown_donor", {"project_goal": "Example"})
    assert checks == []
    assert flaws == []


@pytest.mark.parametrize(
    ("donor_id", "toc_payload", "expected_check_code", "expected_check_status", "expected_flaw_code"),
    [
        ("usaid", {"project_goal": "Goal"}, "USAID_DO_PRESENT", "fail", "USAID_DO_MISSING"),
        ("eu", {}, "EU_OVERALL_OBJECTIVE_COMPLETE", "fail", "EU_OVERALL_OBJECTIVE_MISSING"),
        ("giz", {"outcomes": []}, "GIZ_OUTCOMES_PRESENT", "fail", "GIZ_OUTCOMES_MISSING"),
        (
            "state_department",
            {"stakeholder_map": [], "risk_mitigation": []},
            "STATE_STRATEGIC_CONTEXT_PRESENT",
            "fail",
            "STATE_STRATEGIC_CONTEXT_PRESENT_MISSING",
        ),
        ("worldbank", {"objectives": []}, "WB_OBJECTIVES_PRESENT", "fail", "WB_OBJECTIVES_MISSING"),
    ],
)
def test_donor_policy_emits_expected_failure_signals(
    donor_id, toc_payload, expected_check_code, expected_check_status, expected_flaw_code
):
    checks, flaws = _run_policy(donor_id, toc_payload)
    assert any(c["code"] == expected_check_code and c["status"] == expected_check_status for c in checks)
    assert any(f["code"] == expected_flaw_code for f in flaws)


def test_state_department_alias_uses_same_policy_rules():
    checks, flaws = _run_policy("us_state_department", {})
    assert any(c["code"] == "STATE_STRATEGIC_CONTEXT_PRESENT" for c in checks)
    assert any(f["code"] == "STATE_STRATEGIC_CONTEXT_PRESENT_MISSING" for f in flaws)


def test_usaid_complete_hierarchy_passes_core_checks_without_high_flaws():
    toc_payload = {
        "project_goal": "Improve services",
        "development_objectives": [
            {
                "do_id": "DO 1",
                "description": "DO",
                "intermediate_results": [
                    {
                        "ir_id": "IR 1.1",
                        "description": "IR",
                        "outputs": [{"output_id": "Output 1.1.1", "description": "Output", "indicators": []}],
                    }
                ],
            }
        ],
        "critical_assumptions": ["Assumption 1"],
    }
    checks, flaws = _run_policy("usaid", toc_payload)

    assert any(c["code"] == "USAID_DO_PRESENT" and c["status"] == "pass" for c in checks)
    assert any(c["code"] == "USAID_IR_HIERARCHY" and c["status"] == "pass" for c in checks)
    assert any(c["code"] == "USAID_OUTPUT_HIERARCHY" and c["status"] == "pass" for c in checks)
    assert any(c["code"] == "USAID_CRITICAL_ASSUMPTIONS_PRESENT" and c["status"] == "pass" for c in checks)
    assert not any(f["severity"] == "high" for f in flaws)
