from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_expected_donors(raw: str | None) -> list[str]:
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


def validate_seeded_corpus(
    *,
    report_payload: dict[str, Any],
    expected_donors: list[str],
    min_seeded_total: int,
    require_no_errors: bool,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    seeded = report_payload.get("seeded_corpus")
    if not isinstance(seeded, dict):
        return False, ["Missing seeded_corpus block in report payload."]

    errors = seeded.get("errors")
    error_rows = [str(item) for item in errors] if isinstance(errors, list) else []
    if require_no_errors and error_rows:
        failures.append(f"seeded_corpus.errors is non-empty ({len(error_rows)}): {error_rows[0]}")

    seeded_total = _as_int(seeded.get("seeded_total"), default=0)
    if seeded_total < max(0, min_seeded_total):
        failures.append(
            f"seeded_corpus.seeded_total={seeded_total} is below required minimum {max(0, min_seeded_total)}"
        )

    donor_counts_raw = seeded.get("donor_counts")
    donor_counts = donor_counts_raw if isinstance(donor_counts_raw, dict) else {}
    for donor_id in expected_donors:
        count = _as_int(donor_counts.get(donor_id), default=0)
        if count <= 0:
            failures.append(f"Expected donor '{donor_id}' has seeded count={count}")

    return len(failures) == 0, failures


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate seeded_corpus section in GrantFlow eval report JSON.")
    parser.add_argument("--json", type=Path, required=True, help="Path to eval report JSON.")
    parser.add_argument(
        "--expected-donors",
        type=str,
        default="",
        help="Comma-separated donor ids that must have donor_counts > 0 (for example: usaid,eu,worldbank).",
    )
    parser.add_argument(
        "--min-seeded-total",
        type=int,
        default=1,
        help="Fail when seeded_corpus.seeded_total is lower than this minimum.",
    )
    parser.add_argument(
        "--allow-seed-errors",
        action="store_true",
        help="Do not fail on seeded_corpus.errors entries.",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="seeded-corpus-check",
        help="Label used in output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = json.loads(args.json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print(f"[{args.label}] invalid JSON root: expected object")
        return 2

    expected_donors = _parse_expected_donors(args.expected_donors)
    ok, failures = validate_seeded_corpus(
        report_payload=payload,
        expected_donors=expected_donors,
        min_seeded_total=max(0, int(args.min_seeded_total)),
        require_no_errors=not bool(args.allow_seed_errors),
    )
    if not ok:
        print(f"[{args.label}] FAILED")
        for row in failures:
            print(f"- {row}")
        return 2

    seeded = payload.get("seeded_corpus") if isinstance(payload.get("seeded_corpus"), dict) else {}
    seeded_total = _as_int(seeded.get("seeded_total"), default=0)
    donor_counts = seeded.get("donor_counts") if isinstance(seeded.get("donor_counts"), dict) else {}
    donor_summary = ", ".join(f"{k}={_as_int(v)}" for k, v in sorted(donor_counts.items()))
    print(
        f"[{args.label}] PASS seeded_total={seeded_total}"
        + (f" donor_counts: {donor_summary}" if donor_summary else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
