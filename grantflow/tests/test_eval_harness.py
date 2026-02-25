from __future__ import annotations

import json

from grantflow.eval import harness
from grantflow.eval.harness import (
    build_regression_baseline_snapshot,
    compare_suite_to_baseline,
    evaluate_expectations,
    format_eval_suite_report,
    load_eval_cases,
    run_eval_suite,
)


def test_eval_harness_baseline_cases_pass():
    cases = load_eval_cases()
    assert cases, "Expected bundled eval fixtures"

    suite = run_eval_suite(cases)
    assert suite["case_count"] == len(cases)
    assert suite["all_passed"], format_eval_suite_report(suite)


def test_eval_harness_expectations_detect_regression():
    metrics = {
        "toc_schema_valid": True,
        "needs_revision": False,
        "quality_score": 8.5,
        "critic_score": 8.0,
        "citations_total": 3,
        "architect_citation_count": 2,
        "mel_citation_count": 1,
        "high_confidence_citation_count": 1,
        "citation_confidence_avg": 0.4,
        "low_confidence_citation_count": 1,
        "rag_low_confidence_citation_count": 0,
        "draft_version_count": 2,
        "fatal_flaw_count": 0,
        "high_severity_fatal_flaw_count": 0,
        "error_count": 0,
        "has_toc_draft": True,
        "has_logframe_draft": True,
    }
    passed, checks = evaluate_expectations(
        metrics,
        {
            "toc_schema_valid": True,
            "min_quality_score": 9.0,
            "max_fatal_flaws": 0,
            "max_low_confidence_citations": 0,
            "max_rag_low_confidence_citations": 0,
            "require_toc_draft": True,
        },
    )

    assert passed is False
    failing = [c for c in checks if not c["passed"]]
    assert any(c["name"] == "min_quality_score" for c in failing)


def test_eval_harness_cli_writes_json_and_text_reports(tmp_path):
    json_out = tmp_path / "eval-report.json"
    text_out = tmp_path / "eval-report.txt"

    exit_code = harness.main(["--json-out", str(json_out), "--text-out", str(text_out)])
    assert exit_code == 0
    assert json_out.exists()
    assert text_out.exists()

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["all_passed"] is True
    assert payload["case_count"] >= 1

    text = text_out.read_text(encoding="utf-8")
    assert "GrantFlow evaluation suite" in text
    assert "PASS" in text


def test_eval_harness_regression_comparison_flags_only_degradations():
    suite = {
        "cases": [
            {
                "case_id": "case_a",
                "donor_id": "usaid",
                "metrics": {
                    "quality_score": 9.0,
                    "critic_score": 8.5,
                    "citations_total": 4,
                    "architect_citation_count": 3,
                    "mel_citation_count": 1,
                    "high_confidence_citation_count": 1,
                    "citation_confidence_avg": 0.4,
                    "low_confidence_citation_count": 1,
                    "rag_low_confidence_citation_count": 0,
                    "draft_version_count": 2,
                    "fatal_flaw_count": 0,
                    "high_severity_fatal_flaw_count": 0,
                    "error_count": 0,
                    "toc_schema_valid": True,
                    "has_toc_draft": True,
                    "has_logframe_draft": True,
                    "needs_revision": False,
                },
            },
            {
                "case_id": "new_case",
                "donor_id": "eu",
                "metrics": {
                    "quality_score": 9.5,
                    "critic_score": 9.0,
                    "citations_total": 5,
                    "architect_citation_count": 4,
                    "mel_citation_count": 1,
                    "high_confidence_citation_count": 2,
                    "citation_confidence_avg": 0.6,
                    "low_confidence_citation_count": 0,
                    "rag_low_confidence_citation_count": 0,
                    "draft_version_count": 2,
                    "fatal_flaw_count": 0,
                    "high_severity_fatal_flaw_count": 0,
                    "error_count": 0,
                    "toc_schema_valid": True,
                    "has_toc_draft": True,
                    "has_logframe_draft": True,
                    "needs_revision": False,
                },
            },
        ]
    }
    baseline = {
        "cases": {
            "case_a": {
                "donor_id": "usaid",
                "metrics": {
                    "quality_score": 9.25,  # higher-is-better regression
                    "critic_score": 8.0,  # improvement, should not fail
                    "citations_total": 4,
                    "architect_citation_count": 2,
                    "mel_citation_count": 1,
                    "high_confidence_citation_count": 0,
                    "citation_confidence_avg": 0.3,
                    "low_confidence_citation_count": 1,
                    "rag_low_confidence_citation_count": 0,
                    "draft_version_count": 2,
                    "fatal_flaw_count": 0,
                    "high_severity_fatal_flaw_count": 0,
                    "error_count": 0,
                    "toc_schema_valid": True,
                    "has_toc_draft": True,
                    "has_logframe_draft": True,
                    "needs_revision": False,
                },
            },
            "missing_now": {
                "donor_id": "giz",
                "metrics": {},
            },
        }
    }

    comparison = compare_suite_to_baseline(suite, baseline)
    assert comparison["has_regressions"] is True
    assert comparison["regression_count"] == 1
    assert comparison["regressions"][0]["metric"] == "quality_score"
    assert comparison["warning_count"] >= 2  # new case + missing baseline case


def test_eval_harness_cli_can_write_baseline_and_comparison_reports(tmp_path):
    suite_cases = load_eval_cases()
    suite = run_eval_suite(suite_cases)
    baseline = build_regression_baseline_snapshot(suite)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")

    json_out = tmp_path / "eval-report.json"
    text_out = tmp_path / "eval-report.txt"
    cmp_json_out = tmp_path / "eval-compare.json"
    cmp_text_out = tmp_path / "eval-compare.txt"
    regenerated_baseline_out = tmp_path / "baseline-regenerated.json"

    exit_code = harness.main(
        [
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
            "--compare-to-baseline",
            str(baseline_path),
            "--comparison-json-out",
            str(cmp_json_out),
            "--comparison-text-out",
            str(cmp_text_out),
            "--baseline-snapshot-out",
            str(regenerated_baseline_out),
        ]
    )
    assert exit_code == 0
    comparison = json.loads(cmp_json_out.read_text(encoding="utf-8"))
    assert comparison["has_regressions"] is False
    assert comparison["regression_count"] == 0
    assert regenerated_baseline_out.exists()
    assert "No regressions detected" in cmp_text_out.read_text(encoding="utf-8")
