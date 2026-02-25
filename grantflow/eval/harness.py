from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from grantflow.core.config import config
from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.graph import grantflow_graph

FIXTURES_DIR = Path(__file__).with_name("fixtures")
DEFAULT_BASELINE_PATH = FIXTURES_DIR / "baseline_regression_snapshot.json"

HIGHER_IS_BETTER_METRICS = (
    "quality_score",
    "critic_score",
    "citations_total",
    "architect_citation_count",
    "mel_citation_count",
    "draft_version_count",
)
LOWER_IS_BETTER_METRICS = (
    "fatal_flaw_count",
    "high_severity_fatal_flaw_count",
    "error_count",
)
BOOLEAN_GUARDRAIL_METRICS = (
    "toc_schema_valid",
    "has_toc_draft",
    "has_logframe_draft",
)
REGRESSION_TOLERANCE = 1e-6


def _looks_like_eval_case(item: Any) -> bool:
    return isinstance(item, dict) and ("donor_id" in item or "case_id" in item)


def load_eval_cases(fixtures_dir: Path | None = None) -> list[dict[str, Any]]:
    base_dir = fixtures_dir or FIXTURES_DIR
    cases: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for item in payload:
                if _looks_like_eval_case(item):
                    item = dict(item)
                    item.setdefault("_fixture_file", path.name)
                    cases.append(item)
            continue
        if _looks_like_eval_case(payload):
            payload = dict(payload)
            payload.setdefault("_fixture_file", path.name)
            cases.append(payload)
    return cases


def build_initial_state(case: dict[str, Any]) -> dict[str, Any]:
    donor_id = str(case.get("donor_id") or "").strip()
    if not donor_id:
        raise ValueError(f"Missing donor_id in eval case: {case.get('case_id') or '<unknown>'}")
    strategy = DonorFactory.get_strategy(donor_id)

    input_payload = deepcopy(case.get("input_context") or {})
    if not isinstance(input_payload, dict):
        raise ValueError("input_context must be an object")

    return {
        "donor": donor_id,
        "donor_id": donor_id,
        "donor_strategy": strategy,
        "strategy": strategy,
        "input": input_payload,
        "input_context": input_payload,
        "llm_mode": bool(case.get("llm_mode", False)),
        "architect_rag_enabled": bool(case.get("architect_rag_enabled", False)),
        "iteration": 0,
        "iteration_count": 0,
        "max_iterations": int(case.get("max_iterations", config.graph.max_iterations)),
        "quality_score": 0.0,
        "critic_score": 0.0,
        "needs_revision": False,
        "critic_notes": [],
        "critic_feedback_history": [],
        "hitl_pending": False,
        "errors": [],
    }


def _count_stage_citations(citations: list[Any], stage: str) -> int:
    return sum(1 for c in citations if isinstance(c, dict) and c.get("stage") == stage)


def compute_state_metrics(state: dict[str, Any]) -> dict[str, Any]:
    citations = state.get("citations") if isinstance(state.get("citations"), list) else []
    draft_versions = state.get("draft_versions") if isinstance(state.get("draft_versions"), list) else []
    errors = state.get("errors") if isinstance(state.get("errors"), list) else []
    critic_notes = state.get("critic_notes") if isinstance(state.get("critic_notes"), dict) else {}
    fatal_flaws = critic_notes.get("fatal_flaws") if isinstance(critic_notes.get("fatal_flaws"), list) else []
    toc_validation = state.get("toc_validation") if isinstance(state.get("toc_validation"), dict) else {}

    high_flaws = sum(
        1 for flaw in fatal_flaws if isinstance(flaw, dict) and str(flaw.get("severity") or "").lower() == "high"
    )
    return {
        "toc_schema_valid": bool(toc_validation.get("valid")),
        "toc_schema_name": toc_validation.get("schema_name"),
        "has_toc_draft": bool(state.get("toc_draft")),
        "has_logframe_draft": bool(state.get("logframe_draft")),
        "quality_score": float(state.get("quality_score") or 0.0),
        "critic_score": float(state.get("critic_score") or 0.0),
        "needs_revision": bool(state.get("needs_revision")),
        "fatal_flaw_count": len(fatal_flaws),
        "high_severity_fatal_flaw_count": high_flaws,
        "citations_total": len(citations),
        "architect_citation_count": _count_stage_citations(citations, "architect"),
        "mel_citation_count": _count_stage_citations(citations, "mel"),
        "draft_version_count": len(draft_versions),
        "error_count": len(errors),
    }


def evaluate_expectations(metrics: dict[str, Any], expectations: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def _add_check(name: str, passed: bool, *, expected: Any, actual: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "expected": expected, "actual": actual})

    if "toc_schema_valid" in expectations:
        expected = bool(expectations["toc_schema_valid"])
        actual = bool(metrics.get("toc_schema_valid"))
        _add_check("toc_schema_valid", actual is expected, expected=expected, actual=actual)

    if "expect_needs_revision" in expectations:
        expected = bool(expectations["expect_needs_revision"])
        actual = bool(metrics.get("needs_revision"))
        _add_check("needs_revision", actual is expected, expected=expected, actual=actual)

    for key, metric_key in (
        ("min_quality_score", "quality_score"),
        ("min_critic_score", "critic_score"),
        ("min_citations_total", "citations_total"),
        ("min_architect_citations", "architect_citation_count"),
        ("min_mel_citations", "mel_citation_count"),
        ("min_draft_versions", "draft_version_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) >= float(expected), expected=expected, actual=actual)

    for key, metric_key in (
        ("max_fatal_flaws", "fatal_flaw_count"),
        ("max_high_severity_fatal_flaws", "high_severity_fatal_flaw_count"),
        ("max_errors", "error_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) <= float(expected), expected=expected, actual=actual)

    if expectations.get("require_toc_draft"):
        _add_check("require_toc_draft", bool(metrics.get("has_toc_draft")), expected=True, actual=metrics.get("has_toc_draft"))
    if expectations.get("require_logframe_draft"):
        _add_check(
            "require_logframe_draft",
            bool(metrics.get("has_logframe_draft")),
            expected=True,
            actual=metrics.get("has_logframe_draft"),
        )

    passed = all(bool(c.get("passed")) for c in checks) if checks else True
    return passed, checks


def run_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "unnamed_case")
    donor_id = str(case.get("donor_id") or "")
    final_state = grantflow_graph.invoke(build_initial_state(case))
    metrics = compute_state_metrics(final_state)
    expectations = case.get("expectations") if isinstance(case.get("expectations"), dict) else {}
    passed, checks = evaluate_expectations(metrics, expectations)
    failed_checks = [c for c in checks if not c.get("passed")]

    return {
        "case_id": case_id,
        "donor_id": donor_id,
        "fixture_file": case.get("_fixture_file"),
        "passed": passed,
        "metrics": metrics,
        "checks": checks,
        "failed_checks": failed_checks,
    }


def run_eval_suite(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [run_eval_case(case) for case in cases]
    passed_count = sum(1 for r in results if r.get("passed"))
    return {
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "cases": results,
    }


def format_eval_suite_report(suite: dict[str, Any]) -> str:
    lines = [
        "GrantFlow evaluation suite",
        f"Cases: {suite.get('case_count', 0)} | Passed: {suite.get('passed_count', 0)} | Failed: {suite.get('failed_count', 0)}",
    ]
    for case in suite.get("cases") or []:
        prefix = "PASS" if case.get("passed") else "FAIL"
        metrics = case.get("metrics") or {}
        lines.append(
            (
                f"- {prefix} {case.get('case_id')} ({case.get('donor_id')}): "
                f"q={metrics.get('quality_score')} critic={metrics.get('critic_score')} "
                f"toc_valid={metrics.get('toc_schema_valid')} flaws={metrics.get('fatal_flaw_count')} "
                f"citations={metrics.get('citations_total')}"
            )
        )
        for check in case.get("failed_checks") or []:
            lines.append(
                f"    * {check.get('name')}: expected {check.get('expected')} got {check.get('actual')}"
            )
    return "\n".join(lines)


def build_regression_baseline_snapshot(suite: dict[str, Any]) -> dict[str, Any]:
    case_map: dict[str, Any] = {}
    for case in suite.get("cases") or []:
        case_id = str(case.get("case_id") or "")
        if not case_id:
            continue
        metrics = case.get("metrics") if isinstance(case.get("metrics"), dict) else {}
        case_map[case_id] = {
            "donor_id": case.get("donor_id"),
            "metrics": {
                key: metrics.get(key)
                for key in (
                    *HIGHER_IS_BETTER_METRICS,
                    *LOWER_IS_BETTER_METRICS,
                    *BOOLEAN_GUARDRAIL_METRICS,
                    "needs_revision",
                )
            },
        }
    return {
        "schema_version": 1,
        "tracked_metrics": {
            "higher_is_better": list(HIGHER_IS_BETTER_METRICS),
            "lower_is_better": list(LOWER_IS_BETTER_METRICS),
            "boolean_guardrails": list(BOOLEAN_GUARDRAIL_METRICS) + ["needs_revision"],
        },
        "cases": case_map,
    }


def compare_suite_to_baseline(
    suite: dict[str, Any], baseline: dict[str, Any], *, tolerance: float = REGRESSION_TOLERANCE
) -> dict[str, Any]:
    baseline_cases = (baseline.get("cases") or {}) if isinstance(baseline, dict) else {}
    current_cases = {
        str(case.get("case_id") or ""): case
        for case in (suite.get("cases") or [])
        if isinstance(case, dict) and str(case.get("case_id") or "")
    }

    regressions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for case_id, current_case in current_cases.items():
        current_metrics = current_case.get("metrics") if isinstance(current_case.get("metrics"), dict) else {}
        baseline_case = baseline_cases.get(case_id)
        if not isinstance(baseline_case, dict):
            warnings.append(
                {
                    "type": "new_case_not_in_baseline",
                    "case_id": case_id,
                    "message": "Current eval case is not present in baseline snapshot.",
                }
            )
            continue

        baseline_metrics = baseline_case.get("metrics") if isinstance(baseline_case.get("metrics"), dict) else {}

        for metric in HIGHER_IS_BETTER_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = float(baseline_metrics[metric] or 0.0)
            current_value = float(current_metrics[metric] or 0.0)
            if current_value + tolerance < baseline_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "metric": metric,
                        "direction": "higher_is_better",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} decreased below baseline",
                    }
                )

        for metric in LOWER_IS_BETTER_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = float(baseline_metrics[metric] or 0.0)
            current_value = float(current_metrics[metric] or 0.0)
            if current_value > baseline_value + tolerance:
                regressions.append(
                    {
                        "case_id": case_id,
                        "metric": metric,
                        "direction": "lower_is_better",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} increased above baseline",
                    }
                )

        for metric in BOOLEAN_GUARDRAIL_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = bool(baseline_metrics[metric])
            current_value = bool(current_metrics[metric])
            if baseline_value and not current_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "metric": metric,
                        "direction": "boolean_guardrail",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} regressed from true to false",
                    }
                )

        if "needs_revision" in baseline_metrics and "needs_revision" in current_metrics:
            baseline_value = bool(baseline_metrics["needs_revision"])
            current_value = bool(current_metrics["needs_revision"])
            if not baseline_value and current_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "metric": "needs_revision",
                        "direction": "boolean_guardrail",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": "needs_revision changed from false to true",
                    }
                )

    for case_id in baseline_cases:
        if case_id not in current_cases:
            warnings.append(
                {
                    "type": "baseline_case_missing_in_current_suite",
                    "case_id": case_id,
                    "message": "Baseline snapshot contains a case not present in current suite.",
                }
            )

    return {
        "baseline_path": None,
        "case_count": len(current_cases),
        "baseline_case_count": len(baseline_cases),
        "regression_count": len(regressions),
        "warning_count": len(warnings),
        "has_regressions": bool(regressions),
        "regressions": regressions,
        "warnings": warnings,
    }


def format_eval_comparison_report(comparison: dict[str, Any]) -> str:
    lines = [
        "GrantFlow evaluation baseline comparison",
        (
            f"Current cases: {comparison.get('case_count', 0)} | "
            f"Baseline cases: {comparison.get('baseline_case_count', 0)} | "
            f"Regressions: {comparison.get('regression_count', 0)} | "
            f"Warnings: {comparison.get('warning_count', 0)}"
        ),
    ]
    for item in comparison.get("regressions") or []:
        lines.append(
            (
                f"- REGRESSION {item.get('case_id')} {item.get('metric')}: "
                f"baseline={item.get('baseline')} current={item.get('current')} "
                f"({item.get('message')})"
            )
        )
    for item in comparison.get("warnings") or []:
        lines.append(f"- WARNING {item.get('case_id')}: {item.get('message')}")
    if not (comparison.get("regressions") or comparison.get("warnings")):
        lines.append("- No regressions detected against baseline.")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GrantFlow baseline evaluation fixtures.")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write raw suite results as JSON to this path.",
    )
    parser.add_argument(
        "--text-out",
        type=Path,
        default=None,
        help="Write formatted text summary to this path.",
    )
    parser.add_argument(
        "--baseline-snapshot-out",
        type=Path,
        default=None,
        help="Write a baseline snapshot JSON (used for future regression comparisons).",
    )
    parser.add_argument(
        "--compare-to-baseline",
        type=Path,
        default=None,
        help="Compare current suite metrics to a baseline snapshot JSON and fail only on regressions.",
    )
    parser.add_argument(
        "--comparison-json-out",
        type=Path,
        default=None,
        help="Write baseline comparison result JSON to this path.",
    )
    parser.add_argument(
        "--comparison-text-out",
        type=Path,
        default=None,
        help="Write formatted baseline comparison summary to this path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    cases = load_eval_cases()
    suite = run_eval_suite(cases)
    text_report = format_eval_suite_report(suite)
    print(text_report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(suite, indent=2, sort_keys=True), encoding="utf-8")
    if args.text_out is not None:
        args.text_out.parent.mkdir(parents=True, exist_ok=True)
        args.text_out.write_text(text_report + "\n", encoding="utf-8")
    if args.baseline_snapshot_out is not None:
        snapshot = build_regression_baseline_snapshot(suite)
        args.baseline_snapshot_out.parent.mkdir(parents=True, exist_ok=True)
        args.baseline_snapshot_out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    comparison: dict[str, Any] | None = None
    if args.compare_to_baseline is not None:
        baseline = json.loads(args.compare_to_baseline.read_text(encoding="utf-8"))
        comparison = compare_suite_to_baseline(suite, baseline)
        comparison["baseline_path"] = str(args.compare_to_baseline)
        comparison_text = format_eval_comparison_report(comparison)
        print()
        print(comparison_text)
        if args.comparison_json_out is not None:
            args.comparison_json_out.parent.mkdir(parents=True, exist_ok=True)
            args.comparison_json_out.write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")
        if args.comparison_text_out is not None:
            args.comparison_text_out.parent.mkdir(parents=True, exist_ok=True)
            args.comparison_text_out.write_text(comparison_text + "\n", encoding="utf-8")

    suite_ok = bool(suite.get("all_passed"))
    comparison_ok = comparison is None or not bool(comparison.get("has_regressions"))
    return 0 if (suite_ok and comparison_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
