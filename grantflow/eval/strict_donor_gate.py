from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_DONORS: tuple[str, ...] = ("usaid", "eu", "worldbank", "giz", "state_department")

_THRESHOLD_KEYS = {
    "min_cases",
    "min_avg_quality_score",
    "min_avg_critic_score",
    "min_avg_retrieval_grounded_citation_rate",
    "max_avg_non_retrieval_citation_rate",
    "max_avg_traceability_gap_citation_rate",
    "max_avg_high_severity_fatal_flaws_per_case",
}

DEFAULT_DONOR_THRESHOLDS: dict[str, dict[str, float]] = {
    "usaid": {
        "min_cases": 1,
        "min_avg_quality_score": 7.0,
        "min_avg_critic_score": 7.0,
        "min_avg_retrieval_grounded_citation_rate": 0.70,
        "max_avg_non_retrieval_citation_rate": 0.30,
        "max_avg_traceability_gap_citation_rate": 0.15,
        "max_avg_high_severity_fatal_flaws_per_case": 1.0,
    },
    "eu": {
        "min_cases": 1,
        "min_avg_quality_score": 6.0,
        "min_avg_critic_score": 6.0,
        "min_avg_retrieval_grounded_citation_rate": 0.60,
        "max_avg_non_retrieval_citation_rate": 0.40,
        "max_avg_traceability_gap_citation_rate": 0.25,
        "max_avg_high_severity_fatal_flaws_per_case": 1.0,
    },
    "worldbank": {
        "min_cases": 1,
        "min_avg_quality_score": 7.0,
        "min_avg_critic_score": 7.0,
        "min_avg_retrieval_grounded_citation_rate": 0.70,
        "max_avg_non_retrieval_citation_rate": 0.30,
        "max_avg_traceability_gap_citation_rate": 0.15,
        "max_avg_high_severity_fatal_flaws_per_case": 1.0,
    },
    "giz": {
        "min_cases": 1,
        "min_avg_quality_score": 6.5,
        "min_avg_critic_score": 6.5,
        "min_avg_retrieval_grounded_citation_rate": 0.65,
        "max_avg_non_retrieval_citation_rate": 0.35,
        "max_avg_traceability_gap_citation_rate": 0.20,
        "max_avg_high_severity_fatal_flaws_per_case": 1.0,
    },
    "state_department": {
        "min_cases": 1,
        "min_avg_quality_score": 6.5,
        "min_avg_critic_score": 6.5,
        "min_avg_retrieval_grounded_citation_rate": 0.65,
        "max_avg_non_retrieval_citation_rate": 0.35,
        "max_avg_traceability_gap_citation_rate": 0.20,
        "max_avg_high_severity_fatal_flaws_per_case": 1.0,
    },
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def parse_csv_tokens(raw: str | None) -> list[str]:
    if raw is None:
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        token = str(part or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _sanitize_thresholds(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    clean: dict[str, float] = {}
    for key, raw in value.items():
        token = str(key or "").strip()
        if token not in _THRESHOLD_KEYS:
            continue
        numeric = _as_float(raw)
        if numeric is None:
            continue
        clean[token] = float(numeric)
    return clean


def build_thresholds(
    *,
    required_donors: list[str],
    threshold_payload: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    payload = threshold_payload or {}
    default_override = _sanitize_thresholds(payload.get("default"))
    donor_overrides_raw = _as_dict(payload.get("donors"))
    donor_overrides = {
        str(donor_id).strip().lower(): _sanitize_thresholds(value) for donor_id, value in donor_overrides_raw.items()
    }

    resolved: dict[str, dict[str, float]] = {}
    for donor_id in required_donors:
        base = dict(DEFAULT_DONOR_THRESHOLDS.get(donor_id, {}))
        if not base:
            base = dict(DEFAULT_DONOR_THRESHOLDS["giz"])
        base.update(default_override)
        base.update(donor_overrides.get(donor_id, {}))
        resolved[donor_id] = base
    return resolved


def load_threshold_payload(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _avg(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return round(total / count, 4)


def summarize_report_by_donor(report_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from_report = report_payload.get("donor_quality_breakdown")
    if isinstance(from_report, dict) and from_report:
        report_summary: dict[str, dict[str, Any]] = {}
        for donor_id, row in from_report.items():
            if not isinstance(row, dict):
                continue
            token = str(donor_id or "unknown").strip().lower()
            report_summary[token] = {
                "case_count": _as_int(row.get("cases_total"), default=0),
                "passed_count": _as_int(row.get("cases_passed"), default=0),
                "avg_quality_score": _as_float(row.get("avg_quality_score")),
                "avg_critic_score": _as_float(row.get("avg_critic_score")),
                "avg_retrieval_grounded_citation_rate": _as_float(row.get("avg_retrieval_grounded_citation_rate")),
                "avg_non_retrieval_citation_rate": _as_float(row.get("avg_non_retrieval_citation_rate")),
                "avg_traceability_gap_citation_rate": _as_float(row.get("avg_traceability_gap_citation_rate")),
                "avg_high_severity_fatal_flaws_per_case": (
                    round(
                        _as_int(row.get("high_severity_fatal_flaws_total"), default=0)
                        / max(1, _as_int(row.get("cases_total"), default=0)),
                        4,
                    )
                    if _as_int(row.get("cases_total"), default=0) > 0
                    else None
                ),
            }
        if report_summary:
            return report_summary

    rows: dict[str, dict[str, Any]] = {}
    for case in _as_list(report_payload.get("cases")):
        if not isinstance(case, dict):
            continue
        donor_id = str(case.get("donor_id") or "unknown").strip().lower()
        metrics = _as_dict(case.get("metrics"))
        row = rows.setdefault(
            donor_id,
            {
                "case_count": 0,
                "passed_count": 0,
                "quality_total": 0.0,
                "quality_count": 0,
                "critic_total": 0.0,
                "critic_count": 0,
                "retrieval_grounded_total": 0.0,
                "retrieval_grounded_count": 0,
                "non_retrieval_total": 0.0,
                "non_retrieval_count": 0,
                "traceability_gap_total": 0.0,
                "traceability_gap_count": 0,
                "high_flaws_total": 0,
            },
        )
        row["case_count"] = int(row["case_count"]) + 1
        if bool(case.get("passed")):
            row["passed_count"] = int(row["passed_count"]) + 1

        for metric_key, total_key, count_key in (
            ("quality_score", "quality_total", "quality_count"),
            ("critic_score", "critic_total", "critic_count"),
            ("retrieval_grounded_citation_rate", "retrieval_grounded_total", "retrieval_grounded_count"),
            ("non_retrieval_citation_rate", "non_retrieval_total", "non_retrieval_count"),
            ("traceability_gap_citation_rate", "traceability_gap_total", "traceability_gap_count"),
        ):
            value = _as_float(metrics.get(metric_key))
            if value is None:
                continue
            row[total_key] = float(row.get(total_key) or 0.0) + float(value)
            row[count_key] = int(row.get(count_key) or 0) + 1

        row["high_flaws_total"] = int(row.get("high_flaws_total") or 0) + _as_int(
            metrics.get("high_severity_fatal_flaw_count"),
            default=0,
        )

    summary: dict[str, dict[str, Any]] = {}
    for donor_id, row in rows.items():
        case_count = int(row.get("case_count") or 0)
        summary[donor_id] = {
            "case_count": case_count,
            "passed_count": int(row.get("passed_count") or 0),
            "avg_quality_score": _avg(float(row.get("quality_total") or 0.0), int(row.get("quality_count") or 0)),
            "avg_critic_score": _avg(float(row.get("critic_total") or 0.0), int(row.get("critic_count") or 0)),
            "avg_retrieval_grounded_citation_rate": _avg(
                float(row.get("retrieval_grounded_total") or 0.0),
                int(row.get("retrieval_grounded_count") or 0),
            ),
            "avg_non_retrieval_citation_rate": _avg(
                float(row.get("non_retrieval_total") or 0.0),
                int(row.get("non_retrieval_count") or 0),
            ),
            "avg_traceability_gap_citation_rate": _avg(
                float(row.get("traceability_gap_total") or 0.0),
                int(row.get("traceability_gap_count") or 0),
            ),
            "avg_high_severity_fatal_flaws_per_case": (
                round(int(row.get("high_flaws_total") or 0) / case_count, 4) if case_count > 0 else None
            ),
        }
    return summary


def _evaluate_thresholds(
    *,
    donor_id: str,
    donor_metrics: dict[str, Any] | None,
    thresholds: dict[str, float],
) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    metrics = donor_metrics or {}
    case_count = _as_int(metrics.get("case_count"), default=0)
    min_cases = _as_int(thresholds.get("min_cases"), default=1)

    checks.append(
        {
            "name": "min_cases",
            "passed": case_count >= min_cases,
            "expected": min_cases,
            "actual": case_count,
            "donor_id": donor_id,
        }
    )

    if case_count <= 0:
        return False, checks

    for name, metric_key, mode in (
        ("min_avg_quality_score", "avg_quality_score", "min"),
        ("min_avg_critic_score", "avg_critic_score", "min"),
        ("min_avg_retrieval_grounded_citation_rate", "avg_retrieval_grounded_citation_rate", "min"),
        ("max_avg_non_retrieval_citation_rate", "avg_non_retrieval_citation_rate", "max"),
        ("max_avg_traceability_gap_citation_rate", "avg_traceability_gap_citation_rate", "max"),
        ("max_avg_high_severity_fatal_flaws_per_case", "avg_high_severity_fatal_flaws_per_case", "max"),
    ):
        threshold_value = _as_float(thresholds.get(name))
        if threshold_value is None:
            continue
        actual_value = _as_float(metrics.get(metric_key))
        if actual_value is None:
            passed = False
        elif mode == "min":
            passed = float(actual_value) >= float(threshold_value)
        else:
            passed = float(actual_value) <= float(threshold_value)
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "expected": round(float(threshold_value), 4),
                "actual": None if actual_value is None else round(float(actual_value), 4),
                "donor_id": donor_id,
            }
        )

    return all(bool(item.get("passed")) for item in checks), checks


def evaluate_strict_donor_gate(
    *,
    report_payload: dict[str, Any],
    required_donors: list[str],
    thresholds: dict[str, dict[str, float]],
    enforce_on_exploratory: bool = False,
) -> dict[str, Any]:
    report_skipped = bool(report_payload.get("skipped"))
    expectations_skipped = bool(report_payload.get("expectations_skipped"))
    donor_breakdown = summarize_report_by_donor(report_payload)

    if report_skipped:
        return {
            "status": "skipped",
            "reason": str(report_payload.get("reason") or "report marked as skipped"),
            "required_donors": required_donors,
            "thresholds": thresholds,
            "donor_breakdown": donor_breakdown,
            "failures": [],
        }
    if expectations_skipped and not enforce_on_exploratory:
        return {
            "status": "skipped_exploratory",
            "reason": "expectations_skipped=true",
            "required_donors": required_donors,
            "thresholds": thresholds,
            "donor_breakdown": donor_breakdown,
            "failures": [],
        }

    failures: list[dict[str, Any]] = []
    donor_gate_results: dict[str, dict[str, Any]] = {}
    for donor_id in required_donors:
        donor_metrics = donor_breakdown.get(donor_id)
        donor_thresholds = thresholds.get(donor_id, {})
        passed, checks = _evaluate_thresholds(
            donor_id=donor_id,
            donor_metrics=donor_metrics,
            thresholds=donor_thresholds,
        )
        failing_checks = [item for item in checks if not bool(item.get("passed"))]
        donor_gate_results[donor_id] = {
            "passed": passed,
            "checks": checks,
            "failing_checks": failing_checks,
        }
        if not passed:
            failures.extend(failing_checks)

    return {
        "status": "pass" if not failures else "fail",
        "reason": "" if not failures else f"{len(failures)} donor gate checks failed",
        "required_donors": required_donors,
        "thresholds": thresholds,
        "donor_breakdown": donor_breakdown,
        "donor_gate_results": donor_gate_results,
        "failures": failures,
    }


def _fmt_float(value: Any) -> str:
    cast = _as_float(value)
    if cast is None:
        return "-"
    return f"{float(cast):.3f}"


def render_gate_markdown(*, report_payload: dict[str, Any], gate_payload: dict[str, Any]) -> str:
    status = str(gate_payload.get("status") or "unknown")
    suite_label = str(report_payload.get("suite_label") or "llm-eval-grounded-strict")
    case_count = _as_int(report_payload.get("case_count"), default=0)
    passed_count = _as_int(report_payload.get("passed_count"), default=0)
    failed_count = _as_int(report_payload.get("failed_count"), default=0)
    required_donors = [str(item) for item in (gate_payload.get("required_donors") or [])]
    donor_breakdown = _as_dict(gate_payload.get("donor_breakdown"))
    donor_gate_results = _as_dict(gate_payload.get("donor_gate_results"))
    failures = _as_list(gate_payload.get("failures"))

    lines = [
        "## LLM Grounded Strict Donor Gate",
        "",
        f"- Status: **{status.upper()}**",
        f"- Suite: `{suite_label}`",
        f"- Cases: `{case_count}` (passed=`{passed_count}`, failed=`{failed_count}`)",
        f"- Required donors: `{','.join(required_donors)}`",
    ]
    reason = str(gate_payload.get("reason") or "").strip()
    if reason:
        lines.append(f"- Reason: `{reason}`")

    lines.extend(
        [
            "",
            "| Donor | Cases | Pass | Avg Q | Avg Critic | Avg Retrieval | Avg Non-Retrieval | Avg Traceability Gap | High Flaws/Case | Gate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for donor_id in required_donors:
        donor_metrics = _as_dict(donor_breakdown.get(donor_id))
        gate_row = _as_dict(donor_gate_results.get(donor_id))
        gate_mark = "PASS" if bool(gate_row.get("passed")) else "FAIL"
        if status.startswith("skipped"):
            gate_mark = "SKIP"
        lines.append(
            "| {donor} | {cases} | {passed} | {q} | {critic} | {retr} | {nonretr} | {gap} | {hf} | **{gate}** |".format(
                donor=donor_id,
                cases=_as_int(donor_metrics.get("case_count"), default=0),
                passed=_as_int(donor_metrics.get("passed_count"), default=0),
                q=_fmt_float(donor_metrics.get("avg_quality_score")),
                critic=_fmt_float(donor_metrics.get("avg_critic_score")),
                retr=_fmt_float(donor_metrics.get("avg_retrieval_grounded_citation_rate")),
                nonretr=_fmt_float(donor_metrics.get("avg_non_retrieval_citation_rate")),
                gap=_fmt_float(donor_metrics.get("avg_traceability_gap_citation_rate")),
                hf=_fmt_float(donor_metrics.get("avg_high_severity_fatal_flaws_per_case")),
                gate=gate_mark,
            )
        )

    if failures:
        lines.extend(["", "### Failing Checks"])
        for item in failures:
            if not isinstance(item, dict):
                continue
            lines.append(
                (
                    f"- `{item.get('donor_id')}` `{item.get('name')}` "
                    f"expected=`{item.get('expected')}` actual=`{item.get('actual')}`"
                )
            )
    return "\n".join(lines) + "\n"


def render_gate_text(*, report_payload: dict[str, Any], gate_payload: dict[str, Any]) -> str:
    status = str(gate_payload.get("status") or "unknown")
    suite_label = str(report_payload.get("suite_label") or "llm-eval-grounded-strict")
    failures = _as_list(gate_payload.get("failures"))
    lines = [
        "Strict donor gate",
        f"Suite: {suite_label}",
        f"Status: {status}",
        f"Failure checks: {len(failures)}",
    ]
    for item in failures:
        if not isinstance(item, dict):
            continue
        lines.append(
            (
                f"- {item.get('donor_id')} {item.get('name')}: "
                f"expected={item.get('expected')} actual={item.get('actual')}"
            )
        )
    if not failures:
        lines.append("- No donor gate failures.")
    return "\n".join(lines) + "\n"
