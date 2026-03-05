from __future__ import annotations

import json
from pathlib import Path

from grantflow.eval import harness
from grantflow.eval.harness import (
    apply_runtime_overrides_to_cases,
    build_regression_baseline_snapshot,
    compare_suite_to_baseline,
    compute_state_metrics,
    evaluate_expectations,
    filter_eval_cases,
    format_eval_comparison_report,
    format_eval_suite_report,
    limit_eval_cases,
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
        "architect_claim_citation_count": 2,
        "mel_citation_count": 1,
        "high_confidence_citation_count": 1,
        "architect_threshold_hit_rate": 0.5,
        "architect_key_claim_coverage_ratio": 0.6,
        "architect_fallback_claim_ratio": 0.5,
        "citation_confidence_avg": 0.4,
        "low_confidence_citation_count": 1,
        "rag_low_confidence_citation_count": 0,
        "fallback_namespace_citation_count": 0,
        "non_retrieval_citation_rate": 0.5,
        "traceability_gap_citation_rate": 0.5,
        "doc_id_present_citation_rate": 0.6,
        "retrieval_rank_present_citation_rate": 0.6,
        "retrieval_confidence_present_citation_rate": 0.6,
        "retrieval_metadata_complete_citation_rate": 0.6,
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
            "min_architect_threshold_hit_rate": 0.8,
            "min_architect_key_claim_coverage_ratio": 0.8,
            "max_fatal_flaws": 0,
            "max_low_confidence_citations": 0,
            "max_rag_low_confidence_citations": 0,
            "max_architect_fallback_claim_ratio": 0.4,
            "max_fallback_namespace_citations": 0,
            "max_non_retrieval_citation_rate": 0.4,
            "max_traceability_gap_citation_rate": 0.4,
            "min_doc_id_present_citation_rate": 0.7,
            "min_retrieval_rank_present_citation_rate": 0.7,
            "min_retrieval_confidence_present_citation_rate": 0.7,
            "min_retrieval_metadata_complete_citation_rate": 0.7,
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
    assert payload["suite_label"] == "baseline"

    text = text_out.read_text(encoding="utf-8")
    assert "GrantFlow evaluation suite" in text
    assert "Suite: baseline" in text
    assert "PASS" in text
    assert "Donor quality breakdown (suite-level)" in text


def test_format_eval_suite_report_highlights_fallback_dominance_signals():
    suite = {
        "suite_label": "llm-eval",
        "expectations_skipped": True,
        "case_count": 2,
        "passed_count": 2,
        "failed_count": 0,
        "all_passed": True,
        "cases": [
            {
                "case_id": "c1",
                "donor_id": "usaid",
                "passed": True,
                "failed_checks": [],
                "metrics": {
                    "quality_score": 7.0,
                    "critic_score": 7.0,
                    "toc_schema_valid": True,
                    "fatal_flaw_count": 2,
                    "llm_finding_label_counts": {"CAUSAL_LINK_DETAIL": 2, "BASELINE_TARGET_MISSING": 1},
                    "llm_advisory_applied_label_counts": {"CAUSAL_LINK_DETAIL": 2},
                    "llm_advisory_rejected_label_counts": {"BASELINE_TARGET_MISSING": 1},
                    "citations_total": 10,
                    "fallback_namespace_citation_count": 9,
                    "high_severity_fatal_flaw_count": 0,
                    "low_confidence_citation_count": 9,
                    "needs_revision": False,
                },
            },
            {
                "case_id": "c2",
                "donor_id": "eu",
                "passed": True,
                "failed_checks": [],
                "metrics": {
                    "quality_score": 7.0,
                    "critic_score": 7.0,
                    "toc_schema_valid": True,
                    "fatal_flaw_count": 1,
                    "llm_finding_label_counts": {"BASELINE_TARGET_MISSING": 1},
                    "llm_advisory_applied_label_counts": {},
                    "llm_advisory_rejected_label_counts": {"BASELINE_TARGET_MISSING": 1},
                    "citations_total": 4,
                    "fallback_namespace_citation_count": 4,
                    "high_severity_fatal_flaw_count": 0,
                    "low_confidence_citation_count": 4,
                    "needs_revision": False,
                },
            },
        ],
    }

    text = format_eval_suite_report(suite)
    assert "grounding_risk=fallback_dominant:high(90%)" in text
    assert "Grounding risk summary (fallback dominance)" in text
    assert "usaid: fallback_dominance=high (90%) fallback_ns_citations=9/10" in text
    assert "LLM finding label mix (suite-level)" in text
    assert "- BASELINE_TARGET_MISSING: 2" in text
    assert "- CAUSAL_LINK_DETAIL: 2" in text
    assert "LLM finding label mix by donor" in text
    assert "- usaid: CAUSAL_LINK_DETAIL=2, BASELINE_TARGET_MISSING=1" in text
    assert "LLM advisory label mix (applied)" in text
    assert "- CAUSAL_LINK_DETAIL: 2" in text
    assert "LLM advisory label mix (rejected)" in text
    assert "- BASELINE_TARGET_MISSING: 2" in text
    assert "LLM advisory label mix (rejected) by donor" in text
    assert "- usaid: BASELINE_TARGET_MISSING=1" in text
    assert "Grounding risk summary (non-retrieval dominance)" in text
    # c2 is below minimum citation threshold for dominance reporting
    assert "eu: fallback_dominance" not in text


def test_format_eval_suite_report_suppresses_grounding_risk_when_architect_rag_disabled():
    suite = {
        "suite_label": "baseline",
        "expectations_skipped": True,
        "case_count": 1,
        "passed_count": 1,
        "failed_count": 0,
        "all_passed": True,
        "cases": [
            {
                "case_id": "c_no_rag",
                "donor_id": "eu",
                "passed": True,
                "failed_checks": [],
                "metrics": {
                    "architect_rag_enabled": False,
                    "quality_score": 8.75,
                    "critic_score": 8.75,
                    "toc_schema_valid": True,
                    "fatal_flaw_count": 1,
                    "citations_total": 12,
                    "fallback_namespace_citation_count": 0,
                    "strategy_reference_citation_count": 12,
                    "non_retrieval_citation_count": 12,
                    "traceability_gap_citation_count": 0,
                    "high_severity_fatal_flaw_count": 0,
                    "low_confidence_citation_count": 0,
                    "needs_revision": False,
                },
            }
        ],
    }
    text = format_eval_suite_report(suite)
    assert "grounding_risk=" not in text
    assert "Grounding risk summary (fallback dominance)" not in text
    assert "Grounding risk summary (non-retrieval dominance)" not in text


def test_compute_state_metrics_splits_fallback_namespace_from_rag_low_confidence():
    metrics = compute_state_metrics(
        {
            "toc_validation": {"valid": True},
            "toc_draft": {"toc": {}},
            "logframe_draft": {"indicators": []},
            "critic_notes": {
                "fatal_flaws": [
                    {"source": "llm", "label": "CAUSAL_LINK_DETAIL", "message": "Add causal chain detail."},
                    {"source": "llm", "label": "CAUSAL_LINK_DETAIL", "message": "Clarify assumptions in chain."},
                    {
                        "source": "llm",
                        "label": "BASELINE_TARGET_MISSING",
                        "message": "Baseline and target missing for indicator.",
                    },
                    {"source": "rules", "label": "IGNORE_ME", "message": "Rule-based structural mismatch."},
                ],
                "llm_advisory_diagnostics": {
                    "advisory_applies": True,
                    "candidate_label_counts": {
                        "CAUSAL_LINK_DETAIL": 2,
                        "BASELINE_TARGET_MISSING": 1,
                    },
                },
            },
            "citations": [
                {
                    "stage": "architect",
                    "used_for": "toc_claim",
                    "statement_path": "toc.project_goal",
                    "citation_type": "fallback_namespace",
                    "citation_confidence": 0.1,
                    "doc_id": "doc-1",
                    "retrieval_rank": 1,
                    "retrieval_confidence": 0.2,
                },
                {
                    "stage": "architect",
                    "used_for": "toc_claim",
                    "statement_path": "toc.objectives[0].description",
                    "citation_type": "rag_low_confidence",
                    "citation_confidence": 0.2,
                    "doc_id": "doc-2",
                    "retrieval_rank": 2,
                    "retrieval_confidence": 0.4,
                },
                {"stage": "mel", "citation_type": "rag_result", "citation_confidence": 0.8},
            ],
        }
    )
    assert metrics["architect_rag_enabled"] is True
    assert metrics["citations_total"] == 3
    assert metrics["low_confidence_citation_count"] == 2
    assert metrics["rag_low_confidence_citation_count"] == 1
    assert metrics["fallback_namespace_citation_count"] == 1
    assert metrics["strategy_reference_citation_count"] == 0
    assert metrics["retrieval_grounded_citation_count"] == 2
    assert metrics["non_retrieval_citation_count"] == 1
    assert metrics["non_retrieval_citation_rate"] == 0.3333
    assert metrics["retrieval_grounded_citation_rate"] == 0.6667
    assert metrics["doc_id_present_citation_count"] == 2
    assert metrics["doc_id_present_citation_rate"] == 0.6667
    assert metrics["retrieval_rank_present_citation_count"] == 2
    assert metrics["retrieval_rank_present_citation_rate"] == 0.6667
    assert metrics["retrieval_confidence_present_citation_count"] == 3
    assert metrics["retrieval_confidence_present_citation_rate"] == 1.0
    assert metrics["retrieval_metadata_complete_citation_count"] == 2
    assert metrics["retrieval_metadata_complete_citation_rate"] == 0.6667
    assert metrics["architect_claim_citation_count"] == 2
    assert metrics["architect_key_claim_coverage_ratio"] == 1.0
    assert metrics["architect_fallback_claim_ratio"] == 0.5
    assert metrics["traceability_complete_citation_count"] == 0
    assert metrics["traceability_partial_citation_count"] == 2
    assert metrics["traceability_missing_citation_count"] == 1
    assert metrics["traceability_gap_citation_count"] == 3
    assert metrics["traceability_gap_citation_rate"] == 1.0
    assert metrics["llm_finding_label_counts"]["CAUSAL_LINK_DETAIL"] == 2
    assert metrics["llm_finding_label_counts"]["BASELINE_TARGET_MISSING"] == 1
    assert metrics["llm_advisory_applied_label_counts"]["CAUSAL_LINK_DETAIL"] == 2
    assert metrics["llm_advisory_applied_label_counts"]["BASELINE_TARGET_MISSING"] == 1
    assert metrics["llm_advisory_rejected_label_counts"] == {}


def test_compute_state_metrics_preserves_architect_rag_flag():
    metrics = compute_state_metrics(
        {
            "architect_rag_enabled": False,
            "toc_validation": {"valid": True},
            "toc_draft": {"toc": {}},
            "logframe_draft": {"indicators": []},
            "citations": [],
        }
    )
    assert metrics["architect_rag_enabled"] is False


def test_compute_state_metrics_tracks_strategy_reference_separately():
    metrics = compute_state_metrics(
        {
            "toc_validation": {"valid": True},
            "toc_draft": {"toc": {}},
            "logframe_draft": {"indicators": []},
            "citations": [
                {"stage": "architect", "citation_type": "strategy_reference", "citation_confidence": 0.75},
                {"stage": "mel", "citation_type": "strategy_reference", "citation_confidence": 0.75},
                {"stage": "architect", "citation_type": "rag_claim_support", "citation_confidence": 0.9},
            ],
        }
    )
    assert metrics["citations_total"] == 3
    assert metrics["fallback_namespace_citation_count"] == 0
    assert metrics["strategy_reference_citation_count"] == 2
    assert metrics["retrieval_grounded_citation_count"] == 1
    assert metrics["non_retrieval_citation_count"] == 2
    assert metrics["non_retrieval_citation_rate"] == 0.6667


def test_compute_state_metrics_normalizes_legacy_alias_string_findings():
    metrics = compute_state_metrics(
        {
            "toc_validation": {"valid": True},
            "toc_draft": {"toc": {}},
            "logframe_draft": {"indicators": []},
            "critic_fatal_flaws": [
                "Missing baseline for indicator set.",
            ],
            "citations": [],
        }
    )
    assert metrics["fatal_flaw_count"] == 1
    assert metrics["high_severity_fatal_flaw_count"] == 0
    assert metrics["llm_finding_label_counts"] == {}


def test_eval_harness_runtime_overrides_apply_to_cases_without_mutating_original():
    source_cases = [
        {"case_id": "c1", "donor_id": "usaid", "llm_mode": False, "architect_rag_enabled": False},
        {"case_id": "c2", "donor_id": "eu"},
    ]
    overridden = apply_runtime_overrides_to_cases(
        source_cases,
        force_llm=True,
        force_architect_rag=True,
    )
    assert overridden is not source_cases
    assert all(bool(case.get("llm_mode")) is True for case in overridden)
    assert all(bool(case.get("architect_rag_enabled")) is True for case in overridden)
    assert source_cases[0]["llm_mode"] is False
    assert "architect_rag_enabled" not in source_cases[1]


def test_eval_harness_runtime_overrides_can_disable_architect_rag_without_mutating_original():
    source_cases = [
        {"case_id": "c1", "donor_id": "usaid", "llm_mode": False, "architect_rag_enabled": True},
        {"case_id": "c2", "donor_id": "eu"},
    ]
    overridden = apply_runtime_overrides_to_cases(
        source_cases,
        force_no_architect_rag=True,
    )
    assert overridden is not source_cases
    assert all(bool(case.get("architect_rag_enabled")) is False for case in overridden)
    assert source_cases[0]["architect_rag_enabled"] is True
    assert "architect_rag_enabled" not in source_cases[1]


def test_build_initial_state_uses_canonical_state_contract():
    state = harness.build_initial_state(
        {
            "case_id": "s1",
            "donor_id": "USAID",
            "input_context": {"project": "AI training", "country": "Kazakhstan"},
            "llm_mode": True,
            "architect_rag_enabled": True,
            "max_iterations": 0,
        }
    )
    assert state["donor_id"] == "usaid"
    assert "donor" not in state
    assert state["input_context"]["project"] == "AI training"
    assert "input" not in state
    assert state["llm_mode"] is True
    assert state["architect_rag_enabled"] is True
    assert state["max_iterations"] == 1
    assert isinstance(state.get("critic_notes"), dict)


def test_load_eval_cases_supports_explicit_case_files(tmp_path):
    payload = [
        {
            "case_id": "explicit_case",
            "donor_id": "usaid",
            "input_context": {"project": "P", "country": "C"},
            "expectations": {"toc_schema_valid": True},
        }
    ]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    rows = load_eval_cases(case_files=[path])
    assert len(rows) == 1
    assert rows[0]["case_id"] == "explicit_case"
    assert rows[0]["_fixture_file"] == "cases.json"


def test_grounded_cases_expectations_are_strict_quality_gate():
    rows = load_eval_cases(case_files=[Path("grantflow/eval/cases/grounded_cases.json")])
    assert rows, "Expected grounded eval fixtures"
    for case in rows:
        expectations = case.get("expectations") if isinstance(case.get("expectations"), dict) else {}
        assert expectations.get("min_quality_score") >= 8.0
        assert expectations.get("min_critic_score") >= 8.0
        assert expectations.get("max_fatal_flaws") <= 1
        assert expectations.get("max_high_severity_fatal_flaws") == 0
        assert expectations.get("max_rag_low_confidence_citations") == 0
        assert expectations.get("max_fallback_namespace_citations") == 0
        assert expectations.get("max_architect_fallback_claim_ratio") == 0.0
        assert expectations.get("max_non_retrieval_citation_rate") <= 0.1
        assert expectations.get("max_traceability_gap_citation_rate") <= 0.1


def test_grounded_regression_snapshot_covers_grounded_cases():
    cases = load_eval_cases(case_files=[Path("grantflow/eval/cases/grounded_cases.json")])
    expected_case_ids = {str(case.get("case_id") or "").strip() for case in cases if case.get("case_id")}
    assert expected_case_ids, "Expected non-empty grounded case ids"
    snapshot = json.loads(Path("grantflow/eval/fixtures/grounded_regression_snapshot.json").read_text(encoding="utf-8"))
    snapshot_cases = snapshot.get("cases") if isinstance(snapshot.get("cases"), dict) else {}
    snapshot_case_ids = {str(case_id).strip() for case_id in snapshot_cases}
    assert snapshot_case_ids == expected_case_ids


def test_filter_eval_cases_supports_donor_and_case_filters():
    source_cases = [
        {"case_id": "usaid_a", "donor_id": "usaid"},
        {"case_id": "eu_a", "donor_id": "eu"},
        {"case_id": "wb_a", "donor_id": "worldbank"},
    ]
    filtered = filter_eval_cases(source_cases, donor_ids=["usaid", "eu"], case_ids=["eu_a", "usaid_a"])
    assert [case["case_id"] for case in filtered] == ["usaid_a", "eu_a"]


def test_limit_eval_cases_supports_head_and_seeded_sampling():
    source_cases = [
        {"case_id": "c1", "donor_id": "usaid"},
        {"case_id": "c2", "donor_id": "eu"},
        {"case_id": "c3", "donor_id": "worldbank"},
        {"case_id": "c4", "donor_id": "state_department"},
    ]
    head = limit_eval_cases(source_cases, max_cases=2, sample_seed=None)
    seeded = limit_eval_cases(source_cases, max_cases=2, sample_seed=42)
    assert [case["case_id"] for case in head] == ["c1", "c2"]
    assert [case["case_id"] for case in seeded] == ["c1", "c4"]


def test_eval_harness_cli_supports_suite_label_and_runtime_override_flags(tmp_path, monkeypatch):
    json_out = tmp_path / "llm-eval-report.json"
    text_out = tmp_path / "llm-eval-report.txt"

    monkeypatch.setattr(
        harness,
        "load_eval_cases",
        lambda fixtures_dir=None, case_files=None: [
            {"case_id": "stub", "donor_id": "usaid", "llm_mode": False, "architect_rag_enabled": False}
        ],
    )

    captured: dict[str, object] = {}

    def fake_run_eval_suite(cases, *, suite_label=None, skip_expectations=False):
        captured["cases"] = cases
        captured["suite_label"] = suite_label
        captured["skip_expectations"] = skip_expectations
        return {
            "suite_label": suite_label or "baseline",
            "expectations_skipped": bool(skip_expectations),
            "case_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "all_passed": True,
            "cases": [],
        }

    monkeypatch.setattr(harness, "run_eval_suite", fake_run_eval_suite)

    exit_code = harness.main(
        [
            "--suite-label",
            "llm-eval",
            "--force-llm",
            "--skip-expectations",
            "--donor-id",
            "usaid",
            "--case-id",
            "stub",
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
        ]
    )
    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["suite_label"] == "llm-eval"
    assert payload["runtime_overrides"]["force_llm"] is True
    assert payload["runtime_overrides"]["force_architect_rag"] is False
    assert payload["runtime_overrides"]["force_no_architect_rag"] is False
    assert payload["runtime_overrides"]["skip_expectations"] is True
    assert payload["runtime_overrides"]["donor_filters"] == ["usaid"]
    assert payload["runtime_overrides"]["case_filters"] == ["stub"]
    assert payload["runtime_overrides"]["cases_files"] == []
    assert payload["runtime_overrides"]["max_cases"] is None
    assert payload["runtime_overrides"]["sample_seed"] is None
    assert payload["expectations_skipped"] is True
    assert captured["suite_label"] == "llm-eval"
    assert captured["skip_expectations"] is True
    captured_cases = captured["cases"]
    assert isinstance(captured_cases, list) and captured_cases
    assert captured_cases[0]["llm_mode"] is True
    assert captured_cases[0]["architect_rag_enabled"] is False
    text = text_out.read_text(encoding="utf-8")
    assert "Suite: llm-eval" in text
    assert "Expectations: skipped" in text


def test_eval_harness_cli_supports_force_no_architect_rag(tmp_path, monkeypatch):
    json_out = tmp_path / "ab-report.json"
    text_out = tmp_path / "ab-report.txt"

    monkeypatch.setattr(
        harness,
        "load_eval_cases",
        lambda fixtures_dir=None, case_files=None: [
            {"case_id": "stub", "donor_id": "usaid", "llm_mode": False, "architect_rag_enabled": True}
        ],
    )

    captured: dict[str, object] = {}

    def fake_run_eval_suite(cases, *, suite_label=None, skip_expectations=False):
        captured["cases"] = cases
        return {
            "suite_label": suite_label or "baseline",
            "expectations_skipped": bool(skip_expectations),
            "case_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "all_passed": True,
            "cases": [],
        }

    monkeypatch.setattr(harness, "run_eval_suite", fake_run_eval_suite)

    exit_code = harness.main(
        [
            "--suite-label",
            "grounded-ab-b",
            "--force-no-architect-rag",
            "--skip-expectations",
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
        ]
    )
    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["runtime_overrides"]["force_architect_rag"] is False
    assert payload["runtime_overrides"]["force_no_architect_rag"] is True
    captured_cases = captured["cases"]
    assert isinstance(captured_cases, list) and captured_cases
    assert captured_cases[0]["architect_rag_enabled"] is False


def test_eval_harness_cli_supports_max_cases_and_sample_seed(tmp_path, monkeypatch):
    json_out = tmp_path / "sampled-report.json"
    text_out = tmp_path / "sampled-report.txt"

    monkeypatch.setattr(
        harness,
        "load_eval_cases",
        lambda fixtures_dir=None, case_files=None: [
            {"case_id": "c1", "donor_id": "usaid"},
            {"case_id": "c2", "donor_id": "eu"},
            {"case_id": "c3", "donor_id": "worldbank"},
            {"case_id": "c4", "donor_id": "state_department"},
        ],
    )

    captured: dict[str, object] = {}

    def fake_run_eval_suite(cases, *, suite_label=None, skip_expectations=False):
        captured["cases"] = cases
        return {
            "suite_label": suite_label or "baseline",
            "expectations_skipped": bool(skip_expectations),
            "case_count": len(cases),
            "passed_count": len(cases),
            "failed_count": 0,
            "all_passed": True,
            "cases": [],
        }

    monkeypatch.setattr(harness, "run_eval_suite", fake_run_eval_suite)

    exit_code = harness.main(
        [
            "--suite-label",
            "llm-eval-sampled",
            "--max-cases",
            "2",
            "--sample-seed",
            "42",
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
        ]
    )
    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["runtime_overrides"]["max_cases"] == 2
    assert payload["runtime_overrides"]["sample_seed"] == 42
    captured_cases = captured["cases"]
    assert isinstance(captured_cases, list)
    assert [str(case.get("case_id")) for case in captured_cases] == ["c1", "c4"]


def test_eval_harness_cli_supports_cases_file_argument(tmp_path):
    json_out = tmp_path / "eval-report.json"
    text_out = tmp_path / "eval-report.txt"
    cases_file = tmp_path / "explicit-cases.json"
    cases_file.write_text(
        json.dumps(
            [
                {
                    "case_id": "explicit_only",
                    "donor_id": "usaid",
                    "input_context": {"project": "Water", "country": "Kenya"},
                    "llm_mode": False,
                    "architect_rag_enabled": False,
                    "expectations": {"toc_schema_valid": True},
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = harness.main(
        [
            "--suite-label",
            "explicit-file-suite",
            "--cases-file",
            str(cases_file),
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
        ]
    )
    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["case_count"] == 1
    assert payload["runtime_overrides"]["cases_files"] == [str(cases_file)]
    assert payload["cases"][0]["case_id"] == "explicit_only"


def test_eval_harness_cli_returns_nonzero_when_filters_match_no_cases(tmp_path):
    json_out = tmp_path / "eval-report.json"
    text_out = tmp_path / "eval-report.txt"
    exit_code = harness.main(
        [
            "--donor-id",
            "nonexistent_donor",
            "--json-out",
            str(json_out),
            "--text-out",
            str(text_out),
        ]
    )
    assert exit_code == 2
    assert not json_out.exists()
    assert not text_out.exists()


def test_run_eval_case_can_skip_expectations(monkeypatch):
    monkeypatch.setattr(
        harness,
        "grantflow_graph",
        type(
            "StubGraph",
            (),
            {
                "invoke": staticmethod(
                    lambda state: {"toc_validation": {"valid": True}, "toc_draft": {}, "logframe_draft": {}}
                )
            },
        )(),
    )
    result = harness.run_eval_case(
        {
            "case_id": "c1",
            "donor_id": "usaid",
            "input_context": {"project": "P", "country": "C"},
            "expectations": {"min_quality_score": 99},
        },
        skip_expectations=True,
    )
    assert result["passed"] is True
    assert result["expectations_skipped"] is True
    assert result["checks"] == []
    assert result["failed_checks"] == []


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
                    "architect_threshold_hit_rate": 0.5,
                    "citation_confidence_avg": 0.4,
                    "low_confidence_citation_count": 1,
                    "rag_low_confidence_citation_count": 0,
                    "fallback_namespace_citation_count": 0,
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
                    "architect_threshold_hit_rate": 0.8,
                    "citation_confidence_avg": 0.6,
                    "low_confidence_citation_count": 0,
                    "rag_low_confidence_citation_count": 0,
                    "fallback_namespace_citation_count": 0,
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
                    "architect_threshold_hit_rate": 0.6,
                    "citation_confidence_avg": 0.3,
                    "low_confidence_citation_count": 1,
                    "rag_low_confidence_citation_count": 0,
                    "fallback_namespace_citation_count": 0,
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
    assert comparison["regression_count"] == 2
    assert {item["metric"] for item in comparison["regressions"]} == {"quality_score", "architect_threshold_hit_rate"}
    assert comparison["warning_count"] >= 2  # new case + missing baseline case
    assert comparison["donor_breakdown"]["usaid"]["regression_count"] == 2
    assert comparison["donor_breakdown"]["eu"]["warning_count"] >= 1
    assert comparison["donor_breakdown"]["giz"]["warning_count"] >= 1
    assert comparison["severity_weighted_regression_score"] >= 6
    assert comparison["high_priority_regression_count"] >= 1
    assert comparison["priority_metric_breakdown"]["architect_threshold_hit_rate"]["weight"] >= 4
    assert comparison["donor_priority_breakdown"]["usaid"]["weighted_score"] >= 1

    text = format_eval_comparison_report(comparison)
    assert "Donor regression breakdown" in text
    assert "usaid: regressions=2" in text
    assert "Severity-weighted regression summary" in text
    assert "Top donor weighted risk" in text


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
    assert comparison["severity_weighted_regression_score"] == 0
    assert regenerated_baseline_out.exists()
    cmp_text = cmp_text_out.read_text(encoding="utf-8")
    assert "No regressions detected" in cmp_text


def test_seed_rag_corpus_from_manifest_uses_strategy_rag_namespace(tmp_path, monkeypatch):
    seed_pdf = tmp_path / "seed.pdf"
    seed_pdf.write_bytes(b"%PDF-1.4\n%seed\n")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"donor_id": "usaid", "file": str(seed_pdf)}),
                json.dumps({"donor_id": "state_department", "file": str(seed_pdf)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    calls: list[dict[str, str]] = []

    def _fake_ingest(path: str, *, namespace: str, metadata=None):
        calls.append({"path": path, "namespace": namespace})
        return {"ok": True}

    monkeypatch.setattr("grantflow.memory_bank.ingest.ingest_pdf_to_namespace", _fake_ingest)

    result = harness.seed_rag_corpus_from_manifest(manifest)

    assert result["errors"] == []
    assert result["seeded_total"] == 2
    assert result["donor_counts"]["usaid"] == 1
    assert result["donor_counts"]["state_department"] == 1
    assert result["donor_namespaces"]["usaid"] == "usaid_ads201"
    assert result["donor_namespaces"]["state_department"] == "us_state_department_guidance"
    assert {row["namespace"] for row in calls} == {"usaid_ads201", "us_state_department_guidance"}


def test_seed_rag_corpus_from_manifest_reports_unknown_donor_id(tmp_path, monkeypatch):
    seed_pdf = tmp_path / "seed.pdf"
    seed_pdf.write_bytes(b"%PDF-1.4\n%seed\n")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps({"donor_id": "not_real_donor", "file": str(seed_pdf)}) + "\n", encoding="utf-8")

    def _fake_ingest(path: str, *, namespace: str, metadata=None):
        raise AssertionError("ingest should not run for unknown donor ids")

    monkeypatch.setattr("grantflow.memory_bank.ingest.ingest_pdf_to_namespace", _fake_ingest)

    result = harness.seed_rag_corpus_from_manifest(manifest)

    assert result["seeded_total"] == 0
    assert result["donor_counts"] == {}
    assert result["errors"]
    assert "unknown donor_id 'not_real_donor'" in result["errors"][0]
