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
    "high_confidence_citation_count",
    "architect_threshold_hit_rate",
    "draft_version_count",
    "citation_confidence_avg",
)
LOWER_IS_BETTER_METRICS = (
    "fatal_flaw_count",
    "high_severity_fatal_flaw_count",
    "error_count",
    "low_confidence_citation_count",
    "rag_low_confidence_citation_count",
    "fallback_namespace_citation_count",
)
BOOLEAN_GUARDRAIL_METRICS = (
    "toc_schema_valid",
    "has_toc_draft",
    "has_logframe_draft",
)
REGRESSION_TOLERANCE = 1e-6
REGRESSION_PRIORITY_WEIGHTS: dict[str, int] = {
    "toc_schema_valid": 5,
    "has_toc_draft": 5,
    "has_logframe_draft": 5,
    "error_count": 5,
    "high_severity_fatal_flaw_count": 5,
    "needs_revision": 4,
    "architect_threshold_hit_rate": 4,
    "citation_confidence_avg": 3,
    "fatal_flaw_count": 3,
    "quality_score": 2,
    "critic_score": 2,
    "low_confidence_citation_count": 2,
    "rag_low_confidence_citation_count": 2,
    "fallback_namespace_citation_count": 1,
}
GROUNDING_RISK_MIN_CITATIONS = 5
FALLBACK_DOMINANCE_WARN_RATIO = 0.6
FALLBACK_DOMINANCE_HIGH_RATIO = 0.85


def _fallback_dominance_label(*, fallback_count: int, citation_count: int) -> tuple[str | None, float | None]:
    if citation_count < GROUNDING_RISK_MIN_CITATIONS or citation_count <= 0:
        return None, None
    ratio = fallback_count / citation_count
    if ratio >= FALLBACK_DOMINANCE_HIGH_RATIO:
        return "high", round(ratio, 4)
    if ratio >= FALLBACK_DOMINANCE_WARN_RATIO:
        return "warn", round(ratio, 4)
    return None, round(ratio, 4)


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


def apply_runtime_overrides_to_cases(
    cases: list[dict[str, Any]],
    *,
    force_llm: bool = False,
    force_architect_rag: bool = False,
) -> list[dict[str, Any]]:
    if not (force_llm or force_architect_rag):
        return cases
    overridden: list[dict[str, Any]] = []
    for case in cases:
        next_case = dict(case)
        if force_llm:
            next_case["llm_mode"] = True
        if force_architect_rag:
            next_case["architect_rag_enabled"] = True
        overridden.append(next_case)
    return overridden


def filter_eval_cases(
    cases: list[dict[str, Any]],
    *,
    donor_ids: list[str] | None = None,
    case_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    donor_set = {str(v).strip().lower() for v in (donor_ids or []) if str(v).strip()}
    case_set = {str(v).strip() for v in (case_ids or []) if str(v).strip()}
    if not donor_set and not case_set:
        return cases

    filtered: list[dict[str, Any]] = []
    for case in cases:
        donor_id = str(case.get("donor_id") or "").strip().lower()
        case_id = str(case.get("case_id") or "").strip()
        if donor_set and donor_id not in donor_set:
            continue
        if case_set and case_id not in case_set:
            continue
        filtered.append(case)
    return filtered


def _split_csv_args(values: list[str] | None) -> list[str]:
    tokens: list[str] = []
    for raw in values or []:
        for part in str(raw or "").split(","):
            token = part.strip()
            if token:
                tokens.append(token)
    return tokens


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
    llm_finding_label_counts: dict[str, int] = {}
    for flaw in fatal_flaws:
        if not isinstance(flaw, dict):
            continue
        if str(flaw.get("source") or "").lower() != "llm":
            continue
        label = str(flaw.get("label") or "").strip() or "GENERIC_LLM_REVIEW_FLAG"
        llm_finding_label_counts[label] = int(llm_finding_label_counts.get(label, 0)) + 1
    confidence_values: list[float] = []
    low_confidence_count = 0
    high_confidence_count = 0
    rag_low_confidence_count = 0
    fallback_namespace_count = 0
    architect_threshold_considered = 0
    architect_threshold_hits = 0
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        if str(citation.get("stage") or "") == "architect":
            threshold = citation.get("confidence_threshold")
            try:
                threshold_value = float(threshold) if threshold is not None else None
            except (TypeError, ValueError):
                threshold_value = None
            if threshold_value is not None:
                architect_threshold_considered += 1
                try:
                    conf_for_threshold = float(citation.get("citation_confidence") or 0.0)
                except (TypeError, ValueError):
                    conf_for_threshold = 0.0
                if conf_for_threshold >= threshold_value:
                    architect_threshold_hits += 1
        if str(citation.get("citation_type") or "") == "rag_low_confidence":
            rag_low_confidence_count += 1
        if str(citation.get("citation_type") or "") == "fallback_namespace":
            fallback_namespace_count += 1
        confidence = citation.get("citation_confidence")
        if confidence is None:
            continue
        try:
            conf_value = float(confidence)
        except (TypeError, ValueError):
            continue
        confidence_values.append(conf_value)
        if conf_value < 0.3:
            low_confidence_count += 1
        if conf_value >= 0.7:
            high_confidence_count += 1
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
        "llm_finding_label_counts": llm_finding_label_counts,
        "citations_total": len(citations),
        "architect_citation_count": _count_stage_citations(citations, "architect"),
        "mel_citation_count": _count_stage_citations(citations, "mel"),
        "high_confidence_citation_count": high_confidence_count,
        "architect_threshold_hit_rate": (
            round(architect_threshold_hits / architect_threshold_considered, 4)
            if architect_threshold_considered
            else 0.0
        ),
        "citation_confidence_avg": (
            round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0
        ),
        "low_confidence_citation_count": low_confidence_count,
        "rag_low_confidence_citation_count": rag_low_confidence_count,
        "fallback_namespace_citation_count": fallback_namespace_count,
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
        ("min_fatal_flaws", "fatal_flaw_count"),
        ("min_high_severity_fatal_flaws", "high_severity_fatal_flaw_count"),
        ("min_quality_score", "quality_score"),
        ("min_critic_score", "critic_score"),
        ("min_citations_total", "citations_total"),
        ("min_architect_citations", "architect_citation_count"),
        ("min_mel_citations", "mel_citation_count"),
        ("min_high_confidence_citations", "high_confidence_citation_count"),
        ("min_architect_threshold_hit_rate", "architect_threshold_hit_rate"),
        ("min_citation_confidence_avg", "citation_confidence_avg"),
        ("min_draft_versions", "draft_version_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) >= float(expected), expected=expected, actual=actual)

    for key, metric_key in (
        ("max_quality_score", "quality_score"),
        ("max_critic_score", "critic_score"),
        ("max_fatal_flaws", "fatal_flaw_count"),
        ("max_high_severity_fatal_flaws", "high_severity_fatal_flaw_count"),
        ("max_low_confidence_citations", "low_confidence_citation_count"),
        ("max_rag_low_confidence_citations", "rag_low_confidence_citation_count"),
        ("max_fallback_namespace_citations", "fallback_namespace_citation_count"),
        ("max_errors", "error_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) <= float(expected), expected=expected, actual=actual)

    if expectations.get("require_toc_draft"):
        _add_check(
            "require_toc_draft", bool(metrics.get("has_toc_draft")), expected=True, actual=metrics.get("has_toc_draft")
        )
    if expectations.get("require_logframe_draft"):
        _add_check(
            "require_logframe_draft",
            bool(metrics.get("has_logframe_draft")),
            expected=True,
            actual=metrics.get("has_logframe_draft"),
        )

    passed = all(bool(c.get("passed")) for c in checks) if checks else True
    return passed, checks


def run_eval_case(case: dict[str, Any], *, skip_expectations: bool = False) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "unnamed_case")
    donor_id = str(case.get("donor_id") or "")
    final_state = grantflow_graph.invoke(build_initial_state(case))
    metrics = compute_state_metrics(final_state)
    expectations = case.get("expectations") if isinstance(case.get("expectations"), dict) else {}
    if skip_expectations:
        passed, checks = True, []
    else:
        passed, checks = evaluate_expectations(metrics, expectations)
    failed_checks = [c for c in checks if not c.get("passed")]

    return {
        "case_id": case_id,
        "donor_id": donor_id,
        "fixture_file": case.get("_fixture_file"),
        "passed": passed,
        "metrics": metrics,
        "expectations_skipped": bool(skip_expectations),
        "checks": checks,
        "failed_checks": failed_checks,
    }


def run_eval_suite(
    cases: list[dict[str, Any]],
    *,
    suite_label: str | None = None,
    skip_expectations: bool = False,
) -> dict[str, Any]:
    results = [run_eval_case(case, skip_expectations=skip_expectations) for case in cases]
    passed_count = sum(1 for r in results if r.get("passed"))
    return {
        "suite_label": str(suite_label or "baseline"),
        "expectations_skipped": bool(skip_expectations),
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "cases": results,
    }


def format_eval_suite_report(suite: dict[str, Any]) -> str:
    suite_label = str(suite.get("suite_label") or "baseline")
    lines = [
        "GrantFlow evaluation suite",
        f"Suite: {suite_label}",
        f"Cases: {suite.get('case_count', 0)} | Passed: {suite.get('passed_count', 0)} | Failed: {suite.get('failed_count', 0)}",
    ]
    if bool(suite.get("expectations_skipped")):
        lines.append("Expectations: skipped (exploratory metrics-only mode)")
    for case in suite.get("cases") or []:
        prefix = "PASS" if case.get("passed") else "FAIL"
        metrics = case.get("metrics") or {}
        citation_count = int(metrics.get("citations_total") or 0)
        fallback_count = int(metrics.get("fallback_namespace_citation_count") or 0)
        grounding_risk_label, fallback_ratio = _fallback_dominance_label(
            fallback_count=fallback_count,
            citation_count=citation_count,
        )
        grounding_suffix = ""
        if grounding_risk_label and fallback_ratio is not None:
            grounding_suffix = f" grounding_risk=fallback_dominant:{grounding_risk_label}({fallback_ratio:.0%})"
        lines.append(
            (
                f"- {prefix} {case.get('case_id')} ({case.get('donor_id')}): "
                f"q={metrics.get('quality_score')} critic={metrics.get('critic_score')} "
                f"toc_valid={metrics.get('toc_schema_valid')} flaws={metrics.get('fatal_flaw_count')} "
                f"citations={metrics.get('citations_total')}{grounding_suffix}"
            )
        )
        for check in case.get("failed_checks") or []:
            lines.append(f"    * {check.get('name')}: expected {check.get('expected')} got {check.get('actual')}")

    donor_rows: dict[str, dict[str, Any]] = {}
    llm_finding_label_counts_total: dict[str, int] = {}
    for case in suite.get("cases") or []:
        if not isinstance(case, dict):
            continue
        donor_id = str(case.get("donor_id") or "unknown")
        metrics = case.get("metrics") if isinstance(case.get("metrics"), dict) else {}
        row = donor_rows.setdefault(
            donor_id,
            {
                "case_count": 0,
                "pass_count": 0,
                "quality_scores": [],
                "needs_revision_count": 0,
                "high_flaw_total": 0,
                "low_conf_total": 0,
                "fallback_ns_total": 0,
                "citation_total": 0,
            },
        )
        row["case_count"] = int(row["case_count"]) + 1
        if bool(case.get("passed")):
            row["pass_count"] = int(row["pass_count"]) + 1
        if isinstance(metrics.get("quality_score"), (int, float)):
            cast_scores = row.get("quality_scores")
            if isinstance(cast_scores, list):
                cast_scores.append(float(metrics["quality_score"]))
        if bool(metrics.get("needs_revision")):
            row["needs_revision_count"] = int(row["needs_revision_count"]) + 1
        row["high_flaw_total"] = int(row["high_flaw_total"]) + int(metrics.get("high_severity_fatal_flaw_count") or 0)
        row["low_conf_total"] = int(row["low_conf_total"]) + int(metrics.get("low_confidence_citation_count") or 0)
        row["citation_total"] = int(row["citation_total"]) + int(metrics.get("citations_total") or 0)
        row["fallback_ns_total"] = int(row["fallback_ns_total"]) + int(
            metrics.get("fallback_namespace_citation_count") or 0
        )
        row_label_counts = row.setdefault("llm_finding_label_counts", {})
        if not isinstance(row_label_counts, dict):
            row_label_counts = {}
            row["llm_finding_label_counts"] = row_label_counts
        case_label_counts = metrics.get("llm_finding_label_counts") if isinstance(metrics, dict) else {}
        if isinstance(case_label_counts, dict):
            for label, count in case_label_counts.items():
                label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
                row_label_counts[label_key] = int(row_label_counts.get(label_key, 0)) + int(count or 0)
                llm_finding_label_counts_total[label_key] = int(llm_finding_label_counts_total.get(label_key, 0)) + int(
                    count or 0
                )

    if donor_rows:
        lines.append("")
        lines.append("Donor quality breakdown (suite-level)")
        ordered_donors = sorted(
            donor_rows.items(),
            key=lambda item: (
                -(int(item[1].get("needs_revision_count") or 0)),
                -(int(item[1].get("high_flaw_total") or 0)),
                str(item[0]),
            ),
        )
        for donor_id, row in ordered_donors:
            quality_scores = row.get("quality_scores") if isinstance(row.get("quality_scores"), list) else []
            avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else None
            case_count = int(row.get("case_count") or 0)
            needs_revision_count = int(row.get("needs_revision_count") or 0)
            needs_revision_rate = (needs_revision_count / case_count) if case_count else 0.0
            lines.append(
                (
                    f"- {donor_id}: cases={case_count} pass={int(row.get('pass_count') or 0)}/{case_count} "
                    f"avg_q={avg_quality if avg_quality is not None else '-'} "
                    f"needs_revision={needs_revision_count} ({needs_revision_rate:.0%}) "
                    f"high_flaws={int(row.get('high_flaw_total') or 0)} "
                    f"low_conf_citations={int(row.get('low_conf_total') or 0)} "
                    f"fallback_ns_citations={int(row.get('fallback_ns_total') or 0)}"
                )
            )
        risky_donors: list[tuple[str, dict[str, Any], float, str]] = []
        for donor_id, row in donor_rows.items():
            citation_total = int(row.get("citation_total") or 0)
            fallback_total = int(row.get("fallback_ns_total") or 0)
            label, ratio = _fallback_dominance_label(fallback_count=fallback_total, citation_count=citation_total)
            if label and ratio is not None:
                risky_donors.append((donor_id, row, ratio, label))
        if risky_donors:
            lines.append("")
            lines.append("Grounding risk summary (fallback dominance)")
            risky_donors.sort(key=lambda item: (-item[2], -int(item[1].get("citation_total") or 0), item[0]))
            for donor_id, row, ratio, label in risky_donors:
                lines.append(
                    (
                        f"- {donor_id}: fallback_dominance={label} ({ratio:.0%}) "
                        f"fallback_ns_citations={int(row.get('fallback_ns_total') or 0)}/"
                        f"{int(row.get('citation_total') or 0)}"
                    )
                )
    if llm_finding_label_counts_total:
        lines.append("")
        lines.append("LLM finding label mix (suite-level)")
        for label, count in sorted(
            llm_finding_label_counts_total.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            lines.append(f"- {label}: {int(count)}")

        donor_label_mix_rows: list[tuple[str, dict[str, int]]] = []
        for donor_id, row in donor_rows.items():
            donor_label_counts = row.get("llm_finding_label_counts")
            if isinstance(donor_label_counts, dict) and donor_label_counts:
                donor_label_mix_rows.append((donor_id, donor_label_counts))
        if donor_label_mix_rows:
            lines.append("")
            lines.append("LLM finding label mix by donor")
            for donor_id, donor_label_counts in sorted(donor_label_mix_rows, key=lambda item: str(item[0])):
                top_entries = sorted(
                    donor_label_counts.items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )[:5]
                top_str = ", ".join(f"{label}={int(count)}" for label, count in top_entries)
                lines.append(f"- {donor_id}: {top_str}")
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

    def _case_donor_id(case_payload: Any, fallback: str = "unknown") -> str:
        if isinstance(case_payload, dict):
            donor = case_payload.get("donor_id")
            if donor:
                return str(donor)
        return fallback

    for case_id, current_case in current_cases.items():
        current_donor_id = _case_donor_id(current_case)
        current_metrics = current_case.get("metrics") if isinstance(current_case.get("metrics"), dict) else {}
        baseline_case = baseline_cases.get(case_id)
        if not isinstance(baseline_case, dict):
            warnings.append(
                {
                    "type": "new_case_not_in_baseline",
                    "case_id": case_id,
                    "donor_id": current_donor_id,
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
                        "donor_id": current_donor_id,
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
                        "donor_id": current_donor_id,
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
                        "donor_id": current_donor_id,
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
                        "donor_id": current_donor_id,
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
                    "donor_id": _case_donor_id(baseline_cases.get(case_id)),
                    "message": "Baseline snapshot contains a case not present in current suite.",
                }
            )

    donor_breakdown: dict[str, dict[str, Any]] = {}
    for item in regressions:
        donor_id = str(item.get("donor_id") or "unknown")
        row = donor_breakdown.setdefault(
            donor_id,
            {
                "regression_count": 0,
                "warning_count": 0,
                "metrics": {},
            },
        )
        row["regression_count"] = int(row.get("regression_count") or 0) + 1
        metrics_map = row.get("metrics")
        if isinstance(metrics_map, dict):
            metric_name = str(item.get("metric") or "unknown")
            metrics_map[metric_name] = int(metrics_map.get(metric_name) or 0) + 1
    for item in warnings:
        donor_id = str(item.get("donor_id") or "unknown")
        row = donor_breakdown.setdefault(
            donor_id,
            {
                "regression_count": 0,
                "warning_count": 0,
                "metrics": {},
            },
        )
        row["warning_count"] = int(row.get("warning_count") or 0) + 1

    priority_metric_breakdown: dict[str, dict[str, Any]] = {}
    donor_priority_breakdown: dict[str, dict[str, Any]] = {}
    severity_weighted_regression_score = 0
    high_priority_regression_count = 0
    for item in regressions:
        metric = str(item.get("metric") or "unknown")
        donor_id = str(item.get("donor_id") or "unknown")
        weight = int(REGRESSION_PRIORITY_WEIGHTS.get(metric, 1))
        weighted_score = weight
        severity_weighted_regression_score += weighted_score
        if weight >= 4:
            high_priority_regression_count += 1

        metric_row = priority_metric_breakdown.setdefault(
            metric,
            {"count": 0, "weight": weight, "weighted_score": 0},
        )
        metric_row["count"] = int(metric_row.get("count") or 0) + 1
        metric_row["weighted_score"] = int(metric_row.get("weighted_score") or 0) + weighted_score

        donor_row = donor_priority_breakdown.setdefault(
            donor_id,
            {"regression_count": 0, "weighted_score": 0, "high_priority_regression_count": 0},
        )
        donor_row["regression_count"] = int(donor_row.get("regression_count") or 0) + 1
        donor_row["weighted_score"] = int(donor_row.get("weighted_score") or 0) + weighted_score
        if weight >= 4:
            donor_row["high_priority_regression_count"] = int(donor_row.get("high_priority_regression_count") or 0) + 1

    return {
        "baseline_path": None,
        "case_count": len(current_cases),
        "baseline_case_count": len(baseline_cases),
        "regression_count": len(regressions),
        "warning_count": len(warnings),
        "has_regressions": bool(regressions),
        "regressions": regressions,
        "warnings": warnings,
        "donor_breakdown": donor_breakdown,
        "severity_weighted_regression_score": severity_weighted_regression_score,
        "high_priority_regression_count": high_priority_regression_count,
        "priority_metric_breakdown": priority_metric_breakdown,
        "donor_priority_breakdown": donor_priority_breakdown,
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
                f"- REGRESSION {item.get('case_id')} ({item.get('donor_id') or 'unknown'}) {item.get('metric')}: "
                f"baseline={item.get('baseline')} current={item.get('current')} "
                f"({item.get('message')})"
            )
        )
    for item in comparison.get("warnings") or []:
        lines.append(f"- WARNING {item.get('case_id')} ({item.get('donor_id') or 'unknown'}): {item.get('message')}")

    donor_breakdown = comparison.get("donor_breakdown")
    if isinstance(donor_breakdown, dict) and donor_breakdown:
        lines.append("")
        lines.append("Donor regression breakdown")
        ordered = sorted(
            donor_breakdown.items(),
            key=lambda item: (
                -(int((item[1] or {}).get("regression_count") or 0)),
                -(int((item[1] or {}).get("warning_count") or 0)),
                str(item[0]),
            ),
        )
        for donor_id, row in ordered:
            row_dict = row if isinstance(row, dict) else {}
            metrics_map = row_dict.get("metrics") if isinstance(row_dict.get("metrics"), dict) else {}
            top_metrics = sorted(
                ((str(k), int(v or 0)) for k, v in metrics_map.items()),
                key=lambda kv: (-kv[1], kv[0]),
            )[:3]
            metric_text = ", ".join(f"{name}x{count}" for name, count in top_metrics) if top_metrics else "-"
            lines.append(
                (
                    f"- {donor_id}: regressions={int(row_dict.get('regression_count') or 0)} "
                    f"warnings={int(row_dict.get('warning_count') or 0)} top_metrics={metric_text}"
                )
            )

    priority_metric_breakdown = comparison.get("priority_metric_breakdown")
    donor_priority_breakdown = comparison.get("donor_priority_breakdown")
    if isinstance(priority_metric_breakdown, dict) and priority_metric_breakdown:
        lines.append("")
        lines.append(
            "Severity-weighted regression summary "
            f"(weighted_score={int(comparison.get('severity_weighted_regression_score') or 0)}, "
            f"high_priority={int(comparison.get('high_priority_regression_count') or 0)})"
        )
        ordered_metrics = sorted(
            priority_metric_breakdown.items(),
            key=lambda item: (
                -(int((item[1] or {}).get("weighted_score") or 0)),
                -(int((item[1] or {}).get("count") or 0)),
                str(item[0]),
            ),
        )
        for metric, row in ordered_metrics[:8]:
            row_dict = row if isinstance(row, dict) else {}
            lines.append(
                (
                    f"- metric {metric}: count={int(row_dict.get('count') or 0)} "
                    f"weight={int(row_dict.get('weight') or 1)} "
                    f"weighted_score={int(row_dict.get('weighted_score') or 0)}"
                )
            )
        if isinstance(donor_priority_breakdown, dict) and donor_priority_breakdown:
            lines.append("Top donor weighted risk")
            ordered_donors = sorted(
                donor_priority_breakdown.items(),
                key=lambda item: (
                    -(int((item[1] or {}).get("weighted_score") or 0)),
                    -(int((item[1] or {}).get("high_priority_regression_count") or 0)),
                    str(item[0]),
                ),
            )
            for donor_id, row in ordered_donors[:8]:
                row_dict = row if isinstance(row, dict) else {}
                lines.append(
                    (
                        f"- {donor_id}: weighted_score={int(row_dict.get('weighted_score') or 0)} "
                        f"regressions={int(row_dict.get('regression_count') or 0)} "
                        f"high_priority={int(row_dict.get('high_priority_regression_count') or 0)}"
                    )
                )
    if not (comparison.get("regressions") or comparison.get("warnings")):
        lines.append("- No regressions detected against baseline.")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GrantFlow baseline evaluation fixtures.")
    parser.add_argument(
        "--suite-label",
        type=str,
        default="baseline",
        help="Label to include in reports/artifacts (for example: baseline, llm-eval).",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Override fixture settings and run all cases with llm_mode=true.",
    )
    parser.add_argument(
        "--force-architect-rag",
        action="store_true",
        help="Override fixture settings and run all cases with architect_rag_enabled=true.",
    )
    parser.add_argument(
        "--skip-expectations",
        action="store_true",
        help="Skip fixture expectation assertions and collect metrics only (exploratory mode).",
    )
    parser.add_argument(
        "--donor-id",
        action="append",
        default=[],
        help="Filter suite to one or more donor_ids (repeat flag or use comma-separated values).",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Filter suite to one or more case_ids (repeat flag or use comma-separated values).",
    )
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
    donor_filters = _split_csv_args(args.donor_id)
    case_filters = _split_csv_args(args.case_id)
    cases = filter_eval_cases(cases, donor_ids=donor_filters, case_ids=case_filters)
    if not cases:
        print("No eval cases matched the provided filters.", file=sys.stderr)
        return 2
    cases = apply_runtime_overrides_to_cases(
        cases,
        force_llm=bool(args.force_llm),
        force_architect_rag=bool(args.force_architect_rag),
    )
    suite = run_eval_suite(cases, suite_label=args.suite_label, skip_expectations=bool(args.skip_expectations))
    suite["runtime_overrides"] = {
        "force_llm": bool(args.force_llm),
        "force_architect_rag": bool(args.force_architect_rag),
    }
    suite["runtime_overrides"]["skip_expectations"] = bool(args.skip_expectations)
    suite["runtime_overrides"]["donor_filters"] = donor_filters
    suite["runtime_overrides"]["case_filters"] = case_filters
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

    suite_ok = True if bool(args.skip_expectations) else bool(suite.get("all_passed"))
    comparison_ok = comparison is None or not bool(comparison.get("has_regressions"))
    return 0 if (suite_ok and comparison_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
