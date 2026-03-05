from __future__ import annotations

import argparse
import json
from pathlib import Path

from grantflow.eval.strict_donor_gate import (
    DEFAULT_REQUIRED_DONORS,
    build_thresholds,
    evaluate_strict_donor_gate,
    load_threshold_payload,
    parse_csv_tokens,
    render_gate_markdown,
    render_gate_text,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate donor-level quality gate for strict grounded LLM suite.")
    parser.add_argument(
        "--report-json",
        type=Path,
        required=True,
        help="Path to llm-eval-grounded-strict report JSON.",
    )
    parser.add_argument(
        "--required-donors",
        type=str,
        default=",".join(DEFAULT_REQUIRED_DONORS),
        help="Comma-separated donor_ids to enforce in this gate.",
    )
    parser.add_argument(
        "--thresholds-json",
        type=Path,
        default=None,
        help="Optional threshold profile JSON with optional {default, donors} blocks.",
    )
    parser.add_argument(
        "--enforce-on-exploratory",
        action="store_true",
        help="Evaluate/fail donor gate even when report expectations were skipped.",
    )
    parser.add_argument(
        "--fail-on-skipped-exploratory",
        action="store_true",
        help="Return non-zero when gate status is skipped_exploratory.",
    )
    parser.add_argument("--out-json", type=Path, default=None, help="Optional output gate payload JSON path.")
    parser.add_argument("--out-text", type=Path, default=None, help="Optional output plain text summary path.")
    parser.add_argument("--out-md", type=Path, default=None, help="Optional output markdown summary path.")
    return parser.parse_args()


def _write(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = _parse_args()
    report_payload = json.loads(args.report_json.read_text(encoding="utf-8"))
    if not isinstance(report_payload, dict):
        raise SystemExit("report-json root must be an object")

    required_donors = parse_csv_tokens(args.required_donors)
    if not required_donors:
        required_donors = list(DEFAULT_REQUIRED_DONORS)

    thresholds_payload = load_threshold_payload(args.thresholds_json)
    thresholds = build_thresholds(
        required_donors=required_donors,
        threshold_payload=thresholds_payload,
    )
    gate_payload = evaluate_strict_donor_gate(
        report_payload=report_payload,
        required_donors=required_donors,
        thresholds=thresholds,
        enforce_on_exploratory=bool(args.enforce_on_exploratory),
    )

    text_summary = render_gate_text(report_payload=report_payload, gate_payload=gate_payload)
    md_summary = render_gate_markdown(report_payload=report_payload, gate_payload=gate_payload)

    _write(args.out_text, text_summary)
    _write(args.out_md, md_summary)
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(gate_payload, indent=2, sort_keys=True), encoding="utf-8")

    print(text_summary, end="")
    status = str(gate_payload.get("status") or "")
    if status == "fail":
        return 1
    if status == "skipped_exploratory" and bool(args.fail_on_skipped_exploratory):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
