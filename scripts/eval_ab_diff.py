from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable

HIGHER_IS_BETTER_METRICS: dict[str, str] = {
    "quality_score": "quality_score",
    "critic_score": "critic_score",
    "retrieval_grounded_citation_rate": "retrieval_grounded_rate",
    "retrieval_metadata_complete_citation_rate": "retrieval_metadata_complete_rate",
    "retrieval_rank_present_citation_rate": "retrieval_rank_present_rate",
    "doc_id_present_citation_rate": "doc_id_present_rate",
}

LOWER_IS_BETTER_METRICS: dict[str, str] = {
    "non_retrieval_citation_rate": "non_retrieval_rate",
    "traceability_gap_citation_rate": "traceability_gap_rate",
    "fallback_namespace_citation_count": "fallback_namespace_count",
}

EPSILON = 1e-9


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Iterable[float]) -> float | None:
    rows = [float(v) for v in values]
    if not rows:
        return None
    return round(sum(rows) / len(rows), 4)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_map(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in suite.get("cases") or []:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id") or "").strip()
        if not case_id:
            continue
        out[case_id] = row
    return out


def _metric_delta_report(
    *,
    metric_key: str,
    metric_label: str,
    matched_cases: list[tuple[str, dict[str, Any], dict[str, Any]]],
    higher_is_better: bool,
) -> dict[str, Any]:
    a_values: list[float] = []
    b_values: list[float] = []
    improved = 0
    worsened = 0
    unchanged = 0
    for _, case_a, case_b in matched_cases:
        metrics_a = case_a.get("metrics") if isinstance(case_a.get("metrics"), dict) else {}
        metrics_b = case_b.get("metrics") if isinstance(case_b.get("metrics"), dict) else {}
        value_a = _as_float(metrics_a.get(metric_key))
        value_b = _as_float(metrics_b.get(metric_key))
        if value_a is None or value_b is None:
            continue
        a_values.append(value_a)
        b_values.append(value_b)
        delta = value_b - value_a
        if abs(delta) <= EPSILON:
            unchanged += 1
            continue
        if higher_is_better:
            if delta > 0:
                improved += 1
            else:
                worsened += 1
        else:
            if delta < 0:
                improved += 1
            else:
                worsened += 1

    avg_a = _avg(a_values)
    avg_b = _avg(b_values)
    delta_avg = None if avg_a is None or avg_b is None else round(avg_b - avg_a, 4)
    return {
        "metric_key": metric_key,
        "metric_label": metric_label,
        "higher_is_better": higher_is_better,
        "a_avg": avg_a,
        "b_avg": avg_b,
        "delta_b_minus_a": delta_avg,
        "observed_case_count": len(a_values),
        "improved_case_count": improved,
        "worsened_case_count": worsened,
        "unchanged_case_count": unchanged,
    }


def _build_diff_payload(
    *,
    suite_a: dict[str, Any],
    suite_b: dict[str, Any],
    a_label: str,
    b_label: str,
) -> dict[str, Any]:
    map_a = _case_map(suite_a)
    map_b = _case_map(suite_b)
    ids_a = set(map_a.keys())
    ids_b = set(map_b.keys())
    matched_ids = sorted(ids_a & ids_b)
    missing_in_a = sorted(ids_b - ids_a)
    missing_in_b = sorted(ids_a - ids_b)

    matched_cases: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        (case_id, map_a[case_id], map_b[case_id]) for case_id in matched_ids
    ]

    metric_summary: Dict[str, Dict[str, Any]] = {}
    for metric_key, metric_label in HIGHER_IS_BETTER_METRICS.items():
        metric_summary[metric_key] = _metric_delta_report(
            metric_key=metric_key,
            metric_label=metric_label,
            matched_cases=matched_cases,
            higher_is_better=True,
        )
    for metric_key, metric_label in LOWER_IS_BETTER_METRICS.items():
        metric_summary[metric_key] = _metric_delta_report(
            metric_key=metric_key,
            metric_label=metric_label,
            matched_cases=matched_cases,
            higher_is_better=False,
        )

    donor_rows: Dict[str, Dict[str, list[float]]] = {}
    for _, case_a, case_b in matched_cases:
        donor_id = str(case_a.get("donor_id") or case_b.get("donor_id") or "unknown")
        donor_row = donor_rows.setdefault(
            donor_id,
            {
                "a_non_retrieval_rate": [],
                "b_non_retrieval_rate": [],
                "a_retrieval_grounded_rate": [],
                "b_retrieval_grounded_rate": [],
                "a_traceability_gap_rate": [],
                "b_traceability_gap_rate": [],
            },
        )
        metrics_a = case_a.get("metrics") if isinstance(case_a.get("metrics"), dict) else {}
        metrics_b = case_b.get("metrics") if isinstance(case_b.get("metrics"), dict) else {}
        a_non_retrieval = _as_float(metrics_a.get("non_retrieval_citation_rate"))
        b_non_retrieval = _as_float(metrics_b.get("non_retrieval_citation_rate"))
        a_retrieval_grounded = _as_float(metrics_a.get("retrieval_grounded_citation_rate"))
        b_retrieval_grounded = _as_float(metrics_b.get("retrieval_grounded_citation_rate"))
        a_traceability_gap = _as_float(metrics_a.get("traceability_gap_citation_rate"))
        b_traceability_gap = _as_float(metrics_b.get("traceability_gap_citation_rate"))
        if a_non_retrieval is not None:
            donor_row["a_non_retrieval_rate"].append(a_non_retrieval)
        if b_non_retrieval is not None:
            donor_row["b_non_retrieval_rate"].append(b_non_retrieval)
        if a_retrieval_grounded is not None:
            donor_row["a_retrieval_grounded_rate"].append(a_retrieval_grounded)
        if b_retrieval_grounded is not None:
            donor_row["b_retrieval_grounded_rate"].append(b_retrieval_grounded)
        if a_traceability_gap is not None:
            donor_row["a_traceability_gap_rate"].append(a_traceability_gap)
        if b_traceability_gap is not None:
            donor_row["b_traceability_gap_rate"].append(b_traceability_gap)

    donor_summary: Dict[str, Dict[str, Any]] = {}
    for donor_id, row in sorted(donor_rows.items()):
        a_non_retrieval_avg = _avg(row["a_non_retrieval_rate"])
        b_non_retrieval_avg = _avg(row["b_non_retrieval_rate"])
        a_retrieval_grounded_avg = _avg(row["a_retrieval_grounded_rate"])
        b_retrieval_grounded_avg = _avg(row["b_retrieval_grounded_rate"])
        a_traceability_gap_avg = _avg(row["a_traceability_gap_rate"])
        b_traceability_gap_avg = _avg(row["b_traceability_gap_rate"])
        donor_summary[donor_id] = {
            "a_non_retrieval_rate_avg": a_non_retrieval_avg,
            "b_non_retrieval_rate_avg": b_non_retrieval_avg,
            "delta_non_retrieval_rate_b_minus_a": (
                round(b_non_retrieval_avg - a_non_retrieval_avg, 4)
                if a_non_retrieval_avg is not None and b_non_retrieval_avg is not None
                else None
            ),
            "a_retrieval_grounded_rate_avg": a_retrieval_grounded_avg,
            "b_retrieval_grounded_rate_avg": b_retrieval_grounded_avg,
            "delta_retrieval_grounded_rate_b_minus_a": (
                round(b_retrieval_grounded_avg - a_retrieval_grounded_avg, 4)
                if a_retrieval_grounded_avg is not None and b_retrieval_grounded_avg is not None
                else None
            ),
            "a_traceability_gap_rate_avg": a_traceability_gap_avg,
            "b_traceability_gap_rate_avg": b_traceability_gap_avg,
            "delta_traceability_gap_rate_b_minus_a": (
                round(b_traceability_gap_avg - a_traceability_gap_avg, 4)
                if a_traceability_gap_avg is not None and b_traceability_gap_avg is not None
                else None
            ),
        }

    case_deltas: list[dict[str, Any]] = []
    for case_id, case_a, case_b in matched_cases:
        metrics_a = case_a.get("metrics") if isinstance(case_a.get("metrics"), dict) else {}
        metrics_b = case_b.get("metrics") if isinstance(case_b.get("metrics"), dict) else {}
        a_non_retrieval = _as_float(metrics_a.get("non_retrieval_citation_rate"))
        b_non_retrieval = _as_float(metrics_b.get("non_retrieval_citation_rate"))
        a_retrieval_grounded = _as_float(metrics_a.get("retrieval_grounded_citation_rate"))
        b_retrieval_grounded = _as_float(metrics_b.get("retrieval_grounded_citation_rate"))
        case_deltas.append(
            {
                "case_id": case_id,
                "donor_id": str(case_a.get("donor_id") or case_b.get("donor_id") or "unknown"),
                "a_non_retrieval_rate": a_non_retrieval,
                "b_non_retrieval_rate": b_non_retrieval,
                "delta_non_retrieval_rate_b_minus_a": (
                    round(b_non_retrieval - a_non_retrieval, 4)
                    if a_non_retrieval is not None and b_non_retrieval is not None
                    else None
                ),
                "a_retrieval_grounded_rate": a_retrieval_grounded,
                "b_retrieval_grounded_rate": b_retrieval_grounded,
                "delta_retrieval_grounded_rate_b_minus_a": (
                    round(b_retrieval_grounded - a_retrieval_grounded, 4)
                    if a_retrieval_grounded is not None and b_retrieval_grounded is not None
                    else None
                ),
            }
        )

    return {
        "labels": {"a": a_label, "b": b_label},
        "suite_a_label": str(suite_a.get("suite_label") or ""),
        "suite_b_label": str(suite_b.get("suite_label") or ""),
        "suite_a_case_count": len(ids_a),
        "suite_b_case_count": len(ids_b),
        "matched_case_count": len(matched_ids),
        "missing_in_a": missing_in_a,
        "missing_in_b": missing_in_b,
        "metric_summary": metric_summary,
        "donor_summary": donor_summary,
        "case_deltas": case_deltas,
    }


def _format_text(payload: dict[str, Any]) -> str:
    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    a_label = str(labels.get("a") or "A")
    b_label = str(labels.get("b") or "B")
    lines = [
        "GrantFlow grounded A/B diff",
        f"Labels: A={a_label} | B={b_label}",
        (
            f"Cases: matched={int(payload.get('matched_case_count') or 0)} "
            f"A_total={int(payload.get('suite_a_case_count') or 0)} "
            f"B_total={int(payload.get('suite_b_case_count') or 0)}"
        ),
    ]

    metric_summary = payload.get("metric_summary")
    if isinstance(metric_summary, dict) and metric_summary:
        lines.append("")
        lines.append("Metric deltas (B - A)")
        ordered_metrics = sorted(
            (row for row in metric_summary.values() if isinstance(row, dict)),
            key=lambda row: str(row.get("metric_key") or ""),
        )
        for row in ordered_metrics:
            lines.append(
                (
                    f"- {row.get('metric_key')}: "
                    f"{a_label}={row.get('a_avg')} {b_label}={row.get('b_avg')} "
                    f"delta={row.get('delta_b_minus_a')} "
                    f"improved={int(row.get('improved_case_count') or 0)} "
                    f"worsened={int(row.get('worsened_case_count') or 0)} "
                    f"unchanged={int(row.get('unchanged_case_count') or 0)}"
                )
            )

    donor_summary = payload.get("donor_summary")
    if isinstance(donor_summary, dict) and donor_summary:
        lines.append("")
        lines.append("Donor grounding deltas (B - A)")
        for donor_id in sorted(donor_summary):
            row = donor_summary.get(donor_id)
            if not isinstance(row, dict):
                continue
            lines.append(
                (
                    f"- {donor_id}: non_retrieval_delta={row.get('delta_non_retrieval_rate_b_minus_a')} "
                    f"retrieval_grounded_delta={row.get('delta_retrieval_grounded_rate_b_minus_a')} "
                    f"traceability_gap_delta={row.get('delta_traceability_gap_rate_b_minus_a')}"
                )
            )

    guard = payload.get("guard")
    if isinstance(guard, dict):
        status = str(guard.get("status") or "not_configured")
        lines.append("")
        lines.append(f"Guard status: {status}")
        if status == "failed":
            failures = guard.get("failures")
            if isinstance(failures, list):
                for item in failures:
                    if not isinstance(item, dict):
                        continue
                    kind = str(item.get("kind") or "")
                    donor_id = item.get("donor_id")
                    if kind == "max_a_non_retrieval_rate":
                        lines.append(
                            (
                                f"- FAIL {donor_id}: "
                                f"a_non_retrieval_rate_avg={item.get('observed')} "
                                f"max_allowed={item.get('threshold')}"
                            )
                        )
                    elif kind == "min_a_retrieval_grounded_rate":
                        lines.append(
                            (
                                f"- FAIL {donor_id}: "
                                f"a_retrieval_grounded_rate_avg={item.get('observed')} "
                                f"min_required={item.get('threshold')}"
                            )
                        )
                    elif kind == "max_a_traceability_gap_rate":
                        lines.append(
                            (
                                f"- FAIL {donor_id}: "
                                f"a_traceability_gap_rate_avg={item.get('observed')} "
                                f"max_allowed={item.get('threshold')}"
                            )
                        )
                    elif kind == "min_a_non_retrieval_improvement_vs_b":
                        lines.append(
                            (
                                f"- FAIL {donor_id}: "
                                f"(b-a) non_retrieval_rate improvement={item.get('observed')} "
                                f"min_required={item.get('threshold')}"
                            )
                        )
                    elif kind == "min_a_retrieval_grounded_improvement_vs_b":
                        lines.append(
                            (
                                f"- FAIL {donor_id}: "
                                f"(a-b) retrieval_grounded_rate improvement={item.get('observed')} "
                                f"min_required={item.get('threshold')}"
                            )
                        )
                    else:
                        lines.append(f"- FAIL {donor_id}: {item}")
        missing_donors = guard.get("missing_donors")
        if isinstance(missing_donors, list) and missing_donors:
            lines.append(f"- Missing donors in matched set: {', '.join(str(x) for x in missing_donors)}")

    return "\n".join(lines)


def _parse_guard_donors(raw: str | None) -> list[str]:
    if raw is None:
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        token = str(item or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _evaluate_guard(
    *,
    payload: dict[str, Any],
    guard_donors: list[str],
    max_a_non_retrieval_rate: float | None,
    min_a_retrieval_grounded_rate: float | None,
    max_a_traceability_gap_rate: float | None,
    min_a_non_retrieval_improvement_vs_b: float | None,
    min_a_retrieval_grounded_improvement_vs_b: float | None,
) -> dict[str, Any]:
    if not guard_donors or (
        max_a_non_retrieval_rate is None
        and min_a_retrieval_grounded_rate is None
        and max_a_traceability_gap_rate is None
        and min_a_non_retrieval_improvement_vs_b is None
        and min_a_retrieval_grounded_improvement_vs_b is None
    ):
        return {"status": "not_configured", "guard_donors": guard_donors}

    donor_summary = payload.get("donor_summary")
    donor_rows = donor_summary if isinstance(donor_summary, dict) else {}
    failures: list[dict[str, Any]] = []
    missing: list[str] = []
    for donor_id in guard_donors:
        row = donor_rows.get(donor_id)
        if not isinstance(row, dict):
            missing.append(donor_id)
            continue
        if max_a_non_retrieval_rate is not None:
            rate = _as_float(row.get("a_non_retrieval_rate_avg"))
            if rate is None:
                missing.append(donor_id)
                continue
            if rate > max_a_non_retrieval_rate + EPSILON:
                failures.append(
                    {
                        "donor_id": donor_id,
                        "kind": "max_a_non_retrieval_rate",
                        "observed": round(rate, 4),
                        "threshold": round(max_a_non_retrieval_rate, 4),
                    }
                )
        if min_a_retrieval_grounded_rate is not None:
            rate = _as_float(row.get("a_retrieval_grounded_rate_avg"))
            if rate is None:
                missing.append(donor_id)
                continue
            if rate + EPSILON < min_a_retrieval_grounded_rate:
                failures.append(
                    {
                        "donor_id": donor_id,
                        "kind": "min_a_retrieval_grounded_rate",
                        "observed": round(rate, 4),
                        "threshold": round(min_a_retrieval_grounded_rate, 4),
                    }
                )
        if max_a_traceability_gap_rate is not None:
            rate = _as_float(row.get("a_traceability_gap_rate_avg"))
            if rate is None:
                missing.append(donor_id)
                continue
            if rate > max_a_traceability_gap_rate + EPSILON:
                failures.append(
                    {
                        "donor_id": donor_id,
                        "kind": "max_a_traceability_gap_rate",
                        "observed": round(rate, 4),
                        "threshold": round(max_a_traceability_gap_rate, 4),
                    }
                )
        if min_a_non_retrieval_improvement_vs_b is not None:
            rate = _as_float(row.get("delta_non_retrieval_rate_b_minus_a"))
            if rate is None:
                missing.append(donor_id)
                continue
            if rate + EPSILON < min_a_non_retrieval_improvement_vs_b:
                failures.append(
                    {
                        "donor_id": donor_id,
                        "kind": "min_a_non_retrieval_improvement_vs_b",
                        "observed": round(rate, 4),
                        "threshold": round(min_a_non_retrieval_improvement_vs_b, 4),
                    }
                )
        if min_a_retrieval_grounded_improvement_vs_b is not None:
            a_rate = _as_float(row.get("a_retrieval_grounded_rate_avg"))
            b_rate = _as_float(row.get("b_retrieval_grounded_rate_avg"))
            if a_rate is None or b_rate is None:
                missing.append(donor_id)
                continue
            improvement = a_rate - b_rate
            if improvement + EPSILON < min_a_retrieval_grounded_improvement_vs_b:
                failures.append(
                    {
                        "donor_id": donor_id,
                        "kind": "min_a_retrieval_grounded_improvement_vs_b",
                        "observed": round(improvement, 4),
                        "threshold": round(min_a_retrieval_grounded_improvement_vs_b, 4),
                    }
                )

    status = "failed" if failures else "passed"
    return {
        "status": status,
        "guard_donors": guard_donors,
        "max_a_non_retrieval_rate": (
            round(max_a_non_retrieval_rate, 4) if max_a_non_retrieval_rate is not None else None
        ),
        "min_a_retrieval_grounded_rate": (
            round(min_a_retrieval_grounded_rate, 4) if min_a_retrieval_grounded_rate is not None else None
        ),
        "max_a_traceability_gap_rate": (
            round(max_a_traceability_gap_rate, 4) if max_a_traceability_gap_rate is not None else None
        ),
        "min_a_non_retrieval_improvement_vs_b": (
            round(min_a_non_retrieval_improvement_vs_b, 4) if min_a_non_retrieval_improvement_vs_b is not None else None
        ),
        "min_a_retrieval_grounded_improvement_vs_b": (
            round(min_a_retrieval_grounded_improvement_vs_b, 4)
            if min_a_retrieval_grounded_improvement_vs_b is not None
            else None
        ),
        "checked_donors": len(guard_donors) - len(missing),
        "missing_donors": missing,
        "failures": failures,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two GrantFlow eval suite JSON reports (A/B diff).")
    parser.add_argument("--a-json", type=Path, required=True, help="Path to suite A JSON report.")
    parser.add_argument("--b-json", type=Path, required=True, help="Path to suite B JSON report.")
    parser.add_argument("--a-label", type=str, default="A", help="Display label for suite A.")
    parser.add_argument("--b-label", type=str, default="B", help="Display label for suite B.")
    parser.add_argument("--json-out", type=Path, default=None, help="Write diff JSON report to this path.")
    parser.add_argument("--text-out", type=Path, default=None, help="Write diff text report to this path.")
    parser.add_argument(
        "--guard-donors",
        type=str,
        default="",
        help="Comma-separated donor ids for non-retrieval guard in A suite (for example: usaid,worldbank).",
    )
    parser.add_argument(
        "--max-a-non-retrieval-rate",
        type=float,
        default=None,
        help="Fail when donor A avg non_retrieval_citation_rate exceeds this threshold (0..1).",
    )
    parser.add_argument(
        "--min-a-retrieval-grounded-rate",
        type=float,
        default=None,
        help="Fail when donor A avg retrieval_grounded_citation_rate drops below this threshold (0..1).",
    )
    parser.add_argument(
        "--max-a-traceability-gap-rate",
        type=float,
        default=None,
        help="Fail when donor A avg traceability_gap_citation_rate exceeds this threshold (0..1).",
    )
    parser.add_argument(
        "--min-a-non-retrieval-improvement-vs-b",
        type=float,
        default=None,
        help="Fail when donor-level (B - A) non_retrieval_citation_rate lift is below this threshold.",
    )
    parser.add_argument(
        "--min-a-retrieval-grounded-improvement-vs-b",
        type=float,
        default=None,
        help="Fail when donor-level (A - B) retrieval_grounded_citation_rate lift is below this threshold.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    suite_a = _load_json(args.a_json)
    suite_b = _load_json(args.b_json)
    payload = _build_diff_payload(
        suite_a=suite_a,
        suite_b=suite_b,
        a_label=str(args.a_label),
        b_label=str(args.b_label),
    )
    guard_payload = _evaluate_guard(
        payload=payload,
        guard_donors=_parse_guard_donors(args.guard_donors),
        max_a_non_retrieval_rate=args.max_a_non_retrieval_rate,
        min_a_retrieval_grounded_rate=args.min_a_retrieval_grounded_rate,
        max_a_traceability_gap_rate=args.max_a_traceability_gap_rate,
        min_a_non_retrieval_improvement_vs_b=args.min_a_non_retrieval_improvement_vs_b,
        min_a_retrieval_grounded_improvement_vs_b=args.min_a_retrieval_grounded_improvement_vs_b,
    )
    payload["guard"] = guard_payload
    text_report = _format_text(payload)
    print(text_report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.text_out is not None:
        args.text_out.parent.mkdir(parents=True, exist_ok=True)
        args.text_out.write_text(text_report + "\n", encoding="utf-8")
    if str(guard_payload.get("status") or "") == "failed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
