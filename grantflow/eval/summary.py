from __future__ import annotations

from typing import Any


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


def _fmt_float(value: Any, digits: int = 3) -> str:
    cast = _as_float(value)
    if cast is None:
        return "-"
    return f"{float(cast):.{digits}f}"


def _avg(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return round(total / count, 4)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def donor_rows_from_report(report_payload: dict[str, Any]) -> list[dict[str, Any]]:
    from_report = report_payload.get("donor_quality_breakdown")
    if isinstance(from_report, dict) and from_report:
        rows: list[dict[str, Any]] = []
        for donor_id in sorted(from_report):
            row = from_report.get(donor_id)
            if not isinstance(row, dict):
                continue
            cases_total = _as_int(row.get("cases_total"), default=0)
            high_flaws_total = _as_int(row.get("high_severity_fatal_flaws_total"), default=0)
            rows.append(
                {
                    "donor_id": str(donor_id),
                    "cases_total": cases_total,
                    "cases_passed": _as_int(row.get("cases_passed"), default=0),
                    "avg_quality_score": _as_float(row.get("avg_quality_score")),
                    "avg_critic_score": _as_float(row.get("avg_critic_score")),
                    "avg_retrieval_grounded_citation_rate": _as_float(row.get("avg_retrieval_grounded_citation_rate")),
                    "avg_non_retrieval_citation_rate": _as_float(row.get("avg_non_retrieval_citation_rate")),
                    "avg_traceability_gap_citation_rate": _as_float(row.get("avg_traceability_gap_citation_rate")),
                    "high_severity_fatal_flaws_total": high_flaws_total,
                    "avg_high_severity_fatal_flaws_per_case": (
                        round(high_flaws_total / cases_total, 4) if cases_total > 0 else None
                    ),
                }
            )
        if rows:
            return rows

    grouped: dict[str, dict[str, Any]] = {}
    for case in _as_list(report_payload.get("cases")):
        if not isinstance(case, dict):
            continue
        donor_id = str(case.get("donor_id") or "unknown").strip().lower()
        metrics = _as_dict(case.get("metrics"))
        row = grouped.setdefault(
            donor_id,
            {
                "cases_total": 0,
                "cases_passed": 0,
                "quality_total": 0.0,
                "quality_count": 0,
                "critic_total": 0.0,
                "critic_count": 0,
                "retrieval_total": 0.0,
                "retrieval_count": 0,
                "non_retrieval_total": 0.0,
                "non_retrieval_count": 0,
                "traceability_total": 0.0,
                "traceability_count": 0,
                "high_flaws_total": 0,
            },
        )
        row["cases_total"] = _as_int(row.get("cases_total"), default=0) + 1
        if bool(case.get("passed")):
            row["cases_passed"] = _as_int(row.get("cases_passed"), default=0) + 1
        for metric_key, total_key, count_key in (
            ("quality_score", "quality_total", "quality_count"),
            ("critic_score", "critic_total", "critic_count"),
            ("retrieval_grounded_citation_rate", "retrieval_total", "retrieval_count"),
            ("non_retrieval_citation_rate", "non_retrieval_total", "non_retrieval_count"),
            ("traceability_gap_citation_rate", "traceability_total", "traceability_count"),
        ):
            value = _as_float(metrics.get(metric_key))
            if value is None:
                continue
            row[total_key] = float(row.get(total_key) or 0.0) + float(value)
            row[count_key] = _as_int(row.get(count_key), default=0) + 1
        row["high_flaws_total"] = _as_int(row.get("high_flaws_total"), default=0) + _as_int(
            metrics.get("high_severity_fatal_flaw_count"),
            default=0,
        )

    rows = []
    for donor_id in sorted(grouped):
        row = grouped[donor_id]
        cases_total = _as_int(row.get("cases_total"), default=0)
        high_flaws_total = _as_int(row.get("high_flaws_total"), default=0)
        rows.append(
            {
                "donor_id": donor_id,
                "cases_total": cases_total,
                "cases_passed": _as_int(row.get("cases_passed"), default=0),
                "avg_quality_score": _avg(float(row.get("quality_total") or 0.0), _as_int(row.get("quality_count"))),
                "avg_critic_score": _avg(float(row.get("critic_total") or 0.0), _as_int(row.get("critic_count"))),
                "avg_retrieval_grounded_citation_rate": _avg(
                    float(row.get("retrieval_total") or 0.0), _as_int(row.get("retrieval_count"))
                ),
                "avg_non_retrieval_citation_rate": _avg(
                    float(row.get("non_retrieval_total") or 0.0), _as_int(row.get("non_retrieval_count"))
                ),
                "avg_traceability_gap_citation_rate": _avg(
                    float(row.get("traceability_total") or 0.0), _as_int(row.get("traceability_count"))
                ),
                "high_severity_fatal_flaws_total": high_flaws_total,
                "avg_high_severity_fatal_flaws_per_case": (
                    round(high_flaws_total / cases_total, 4) if cases_total > 0 else None
                ),
            }
        )
    return rows


def build_eval_summary_markdown(
    report_payload: dict[str, Any],
    *,
    title: str = "LLM Eval Summary",
    comparison_payload: dict[str, Any] | None = None,
    gate_payload: dict[str, Any] | None = None,
) -> str:
    suite_label = str(report_payload.get("suite_label") or "")
    case_count = _as_int(report_payload.get("case_count"), default=0)
    passed_count = _as_int(report_payload.get("passed_count"), default=0)
    failed_count = _as_int(report_payload.get("failed_count"), default=0)
    skipped = bool(report_payload.get("skipped"))
    reason = str(report_payload.get("reason") or "").strip()

    lines = [
        f"## {title}",
        "",
        f"- Suite: `{suite_label}`",
        f"- Cases: `{case_count}` (passed=`{passed_count}`, failed=`{failed_count}`)",
    ]
    if bool(report_payload.get("expectations_skipped")):
        lines.append("- Expectations: `skipped`")
    if skipped:
        lines.append("- Status: `skipped`")
    if reason:
        lines.append(f"- Reason: `{reason}`")

    if isinstance(comparison_payload, dict):
        lines.append(
            "- Baseline comparison: regressions=`{reg}`, warnings=`{warn}`, has_regressions=`{flag}`".format(
                reg=_as_int(comparison_payload.get("regression_count"), default=0),
                warn=_as_int(comparison_payload.get("warning_count"), default=0),
                flag=bool(comparison_payload.get("has_regressions")),
            )
        )

    if isinstance(gate_payload, dict):
        gate_status = str(gate_payload.get("status") or "unknown")
        gate_reason = str(gate_payload.get("reason") or "").strip()
        lines.append(f"- Donor gate: **{gate_status.upper()}**")
        if gate_reason:
            lines.append(f"- Donor gate reason: `{gate_reason}`")

    donor_rows = donor_rows_from_report(report_payload)
    if donor_rows:
        lines.extend(
            [
                "",
                "| Donor | Cases | Pass | Avg Q | Avg Critic | Avg Retrieval | Avg Non-Retrieval | Avg Traceability Gap | High Flaws/Case |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in donor_rows:
            lines.append(
                "| {donor} | {cases} | {passed} | {q} | {critic} | {retr} | {nonretr} | {gap} | {hf} |".format(
                    donor=row.get("donor_id"),
                    cases=_as_int(row.get("cases_total"), default=0),
                    passed=_as_int(row.get("cases_passed"), default=0),
                    q=_fmt_float(row.get("avg_quality_score")),
                    critic=_fmt_float(row.get("avg_critic_score")),
                    retr=_fmt_float(row.get("avg_retrieval_grounded_citation_rate")),
                    nonretr=_fmt_float(row.get("avg_non_retrieval_citation_rate")),
                    gap=_fmt_float(row.get("avg_traceability_gap_citation_rate")),
                    hf=_fmt_float(row.get("avg_high_severity_fatal_flaws_per_case")),
                )
            )

    failed_rows = []
    for case in _as_list(report_payload.get("cases")):
        if not isinstance(case, dict) or bool(case.get("passed")):
            continue
        case_id = str(case.get("case_id") or "unknown")
        donor_id = str(case.get("donor_id") or "unknown")
        failed_checks = _as_list(case.get("failed_checks"))
        top = []
        for item in failed_checks[:3]:
            if not isinstance(item, dict):
                continue
            top.append(f"{item.get('name')} ({item.get('actual')} vs {item.get('expected')})")
        failed_rows.append((case_id, donor_id, "; ".join(top) if top else "-"))
    if failed_rows:
        lines.extend(["", "### Failed Cases"])
        for case_id, donor_id, details in failed_rows:
            lines.append(f"- `{case_id}` ({donor_id}): {details}")

    if isinstance(gate_payload, dict):
        failures = gate_payload.get("failures") if isinstance(gate_payload.get("failures"), list) else []
        if failures:
            lines.extend(["", "### Donor Gate Failures"])
            for item in failures[:12]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    (
                        f"- `{item.get('donor_id')}` `{item.get('name')}` "
                        f"expected=`{item.get('expected')}` actual=`{item.get('actual')}`"
                    )
                )

    return "\n".join(lines) + "\n"
