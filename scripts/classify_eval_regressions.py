#!/usr/bin/env python3
"""Classify eval regressions into hard and warn buckets.

Parses the comparison text output emitted by grantflow.eval.harness and
extracts lines that start with "- REGRESSION ...".
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-text", required=True)
    parser.add_argument("--hard-metric", action="append", default=[])
    parser.add_argument("--warn-metric", action="append", default=[])
    parser.add_argument("--summary-out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    text = Path(args.comparison_text).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if "REGRESSION " in line]

    metric_re = re.compile(r"\)\s+([a-zA-Z0-9_]+):")
    hard_set = set(args.hard_metric)
    warn_set = set(args.warn_metric)

    hard: list[tuple[str, str]] = []
    warn: list[tuple[str, str]] = []
    other: list[tuple[str, str]] = []

    for line in lines:
        match = metric_re.search(line)
        metric = match.group(1) if match else "unknown_metric"
        if metric in hard_set:
            hard.append((metric, line))
        elif metric in warn_set:
            warn.append((metric, line))
        else:
            other.append((metric, line))

    summary_lines: list[str] = []
    summary_lines.append("## Nightly Gate Summary")
    summary_lines.append(f"- total_regressions: {len(lines)}")
    summary_lines.append(f"- hard_regressions: {len(hard)}")
    summary_lines.append(f"- warn_regressions: {len(warn)}")
    summary_lines.append(f"- uncategorized_regressions: {len(other)}")
    summary_lines.append("")

    if hard:
        summary_lines.append("### Hard regressions")
        for _, line in hard:
            summary_lines.append(f"- {line}")
        summary_lines.append("")

    if warn:
        summary_lines.append("### Warn-only regressions")
        for _, line in warn:
            summary_lines.append(f"- {line}")
        summary_lines.append("")

    if other:
        summary_lines.append("### Uncategorized regressions (default: warn)")
        for _, line in other:
            summary_lines.append(f"- {line}")
        summary_lines.append("")

    Path(args.summary_out).write_text("\n".join(summary_lines).rstrip() + "\n", encoding="utf-8")

    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"hard_count={len(hard)}\n")
            handle.write(f"warn_count={len(warn)}\n")
            handle.write(f"other_count={len(other)}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
