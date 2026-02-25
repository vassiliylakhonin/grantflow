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


def load_eval_cases(fixtures_dir: Path | None = None) -> list[dict[str, Any]]:
    base_dir = fixtures_dir or FIXTURES_DIR
    cases: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    item = dict(item)
                    item.setdefault("_fixture_file", path.name)
                    cases.append(item)
            continue
        if isinstance(payload, dict):
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
    return 0 if suite.get("all_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
