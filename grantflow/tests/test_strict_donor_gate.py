from __future__ import annotations

from grantflow.eval.strict_donor_gate import (
    build_thresholds,
    evaluate_strict_donor_gate,
    parse_csv_tokens,
    render_gate_markdown,
    summarize_report_by_donor,
)


def _report(cases: list[dict]) -> dict:
    return {
        "suite_label": "llm-eval-grounded-strict",
        "case_count": len(cases),
        "passed_count": sum(1 for c in cases if c.get("passed")),
        "failed_count": sum(1 for c in cases if not c.get("passed")),
        "cases": cases,
    }


def test_parse_csv_tokens_normalizes_and_deduplicates() -> None:
    assert parse_csv_tokens(" USAID,eu,usaid , ,GIZ") == ["usaid", "eu", "giz"]


def test_summarize_report_by_donor_aggregates_key_metrics() -> None:
    payload = _report(
        [
            {
                "donor_id": "usaid",
                "passed": True,
                "metrics": {
                    "quality_score": 7.0,
                    "critic_score": 7.5,
                    "retrieval_grounded_citation_rate": 0.8,
                    "non_retrieval_citation_rate": 0.2,
                    "traceability_gap_citation_rate": 0.1,
                    "high_severity_fatal_flaw_count": 1,
                },
            },
            {
                "donor_id": "usaid",
                "passed": False,
                "metrics": {
                    "quality_score": 8.0,
                    "critic_score": 8.5,
                    "retrieval_grounded_citation_rate": 0.7,
                    "non_retrieval_citation_rate": 0.3,
                    "traceability_gap_citation_rate": 0.2,
                    "high_severity_fatal_flaw_count": 0,
                },
            },
        ]
    )
    summary = summarize_report_by_donor(payload)
    assert summary["usaid"]["case_count"] == 2
    assert summary["usaid"]["passed_count"] == 1
    assert summary["usaid"]["avg_quality_score"] == 7.5
    assert summary["usaid"]["avg_critic_score"] == 8.0
    assert summary["usaid"]["avg_retrieval_grounded_citation_rate"] == 0.75
    assert summary["usaid"]["avg_non_retrieval_citation_rate"] == 0.25
    assert summary["usaid"]["avg_traceability_gap_citation_rate"] == 0.15
    assert summary["usaid"]["avg_high_severity_fatal_flaws_per_case"] == 0.5


def test_evaluate_strict_donor_gate_fails_per_donor_thresholds() -> None:
    payload = _report(
        [
            {
                "donor_id": "usaid",
                "passed": True,
                "metrics": {
                    "quality_score": 7.5,
                    "critic_score": 7.5,
                    "retrieval_grounded_citation_rate": 0.75,
                    "non_retrieval_citation_rate": 0.2,
                    "traceability_gap_citation_rate": 0.1,
                    "high_severity_fatal_flaw_count": 0,
                },
            },
            {
                "donor_id": "eu",
                "passed": True,
                "metrics": {
                    "quality_score": 4.0,
                    "critic_score": 4.0,
                    "retrieval_grounded_citation_rate": 0.4,
                    "non_retrieval_citation_rate": 0.8,
                    "traceability_gap_citation_rate": 0.6,
                    "high_severity_fatal_flaw_count": 2,
                },
            },
        ]
    )
    required_donors = ["usaid", "eu"]
    thresholds = build_thresholds(required_donors=required_donors, threshold_payload={})
    gate = evaluate_strict_donor_gate(
        report_payload=payload,
        required_donors=required_donors,
        thresholds=thresholds,
    )
    assert gate["status"] == "fail"
    assert any(item.get("donor_id") == "eu" for item in gate["failures"])
    assert gate["donor_gate_results"]["usaid"]["passed"] is True
    assert gate["donor_gate_results"]["eu"]["passed"] is False


def test_evaluate_strict_donor_gate_skips_when_exploratory() -> None:
    payload = _report([])
    payload["expectations_skipped"] = True
    required_donors = ["usaid"]
    thresholds = build_thresholds(required_donors=required_donors, threshold_payload={})
    gate = evaluate_strict_donor_gate(
        report_payload=payload,
        required_donors=required_donors,
        thresholds=thresholds,
    )
    assert gate["status"] == "skipped_exploratory"


def test_render_gate_markdown_includes_failures_table() -> None:
    payload = _report(
        [
            {
                "donor_id": "usaid",
                "passed": True,
                "metrics": {
                    "quality_score": 6.0,
                    "critic_score": 6.0,
                    "retrieval_grounded_citation_rate": 0.5,
                    "non_retrieval_citation_rate": 0.5,
                    "traceability_gap_citation_rate": 0.4,
                    "high_severity_fatal_flaw_count": 1,
                },
            }
        ]
    )
    required_donors = ["usaid"]
    thresholds = build_thresholds(required_donors=required_donors, threshold_payload={})
    gate = evaluate_strict_donor_gate(
        report_payload=payload,
        required_donors=required_donors,
        thresholds=thresholds,
    )
    text = render_gate_markdown(report_payload=payload, gate_payload=gate)
    assert "LLM Grounded Strict Donor Gate" in text
    assert "| usaid |" in text
    assert "Failing Checks" in text
