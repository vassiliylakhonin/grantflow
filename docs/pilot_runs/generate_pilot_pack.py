#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _json_request(
    method: str,
    url: str,
    *,
    payload: Dict[str, Any] | None = None,
    api_key: str | None = None,
) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=240) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _bytes_request(
    method: str,
    url: str,
    *,
    payload: Dict[str, Any] | None = None,
    api_key: str | None = None,
) -> bytes:
    headers: Dict[str, str] = {}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def _build_summary(root: Path, benchmark_rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(f"# Pilot Validation Pack — {root.name}")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Mode: `llm_mode=true` (grounded via default architect retrieval)")
    lines.append("- Donors: " + ", ".join(f"`{row.get('donor_id')}`" for row in benchmark_rows))
    lines.append("- Source benchmark: `benchmark-results.json`")
    lines.append("")
    lines.append("## Benchmark Summary")
    lines.append("")
    lines.append(
        "| Donor | Job ID | Quality | Critic | Retrieval hits | Citations | "
        "Fallback NS | RAG low | Conf avg | Threshold hit | Readiness |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    for row in benchmark_rows:
        donor_id = str(row.get("donor_id") or "")
        quality_path = root / donor_id / "quality.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
        citations = quality.get("citations") if isinstance(quality.get("citations"), dict) else {}
        architect = quality.get("architect") if isinstance(quality.get("architect"), dict) else {}
        readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}
        expected = (
            readiness.get("expected_doc_families") if isinstance(readiness.get("expected_doc_families"), list) else []
        )
        missing = (
            readiness.get("missing_doc_families") if isinstance(readiness.get("missing_doc_families"), list) else []
        )
        readiness_str = f"{len(expected) - len(missing)}/{len(expected)}" if expected else "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    donor_id,
                    f"`{row.get('job_id')}`",
                    str(quality.get("quality_score")),
                    str(quality.get("critic_score")),
                    str(architect.get("retrieval_hits_count")),
                    str(citations.get("citation_count")),
                    str(citations.get("fallback_namespace_citation_count")),
                    str(citations.get("rag_low_confidence_citation_count")),
                    str(citations.get("citation_confidence_avg")),
                    str(citations.get("architect_threshold_hit_rate")),
                    readiness_str,
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Files")
    for row in benchmark_rows:
        donor_id = str(row.get("donor_id") or "")
        lines.append(
            f"- `{donor_id}/status.json`, `{donor_id}/quality.json`, `{donor_id}/critic.json`, `{donor_id}/citations.json`"
        )
        lines.append(
            f"- `{donor_id}/export-payload.json`, `{donor_id}/review-package.zip`, "
            f"`{donor_id}/toc-review-package.docx`, `{donor_id}/logframe-review-package.xlsx`"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- These runs are sanitized pilot snapshots and not final donor submissions.")
    lines.append("- Grounding quality remains corpus-dependent; inspect per-donor `quality.json` and `citations.json`.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build pilot pack snapshots/artifacts from benchmark results.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--benchmark-json", required=True, help="Path to benchmark-results.json.")
    parser.add_argument(
        "--output-dir", required=True, help="Target pilot pack directory (e.g., docs/pilot_runs/2026-02-27)."
    )
    parser.add_argument("--api-key", default="", help="Optional X-API-Key for protected endpoints.")
    args = parser.parse_args()

    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rows = json.loads(Path(args.benchmark_json).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise SystemExit("benchmark json must contain a non-empty list of run rows")

    api_key = args.api_key.strip() or None
    base = args.api_base.rstrip("/")

    for row in rows:
        donor_id = str(row.get("donor_id") or "")
        job_id = str(row.get("job_id") or "")
        if not donor_id or not job_id:
            raise SystemExit(f"invalid benchmark row: {row}")
        ddir = root / donor_id
        ddir.mkdir(parents=True, exist_ok=True)

        status = _json_request("GET", f"{base}/status/{job_id}", api_key=api_key)
        quality = _json_request("GET", f"{base}/status/{job_id}/quality", api_key=api_key)
        critic = _json_request("GET", f"{base}/status/{job_id}/critic", api_key=api_key)
        citations = _json_request("GET", f"{base}/status/{job_id}/citations", api_key=api_key)
        versions = _json_request("GET", f"{base}/status/{job_id}/versions", api_key=api_key)
        metrics = _json_request("GET", f"{base}/status/{job_id}/metrics", api_key=api_key)
        events = _json_request("GET", f"{base}/status/{job_id}/events", api_key=api_key)
        export_payload = _json_request("GET", f"{base}/status/{job_id}/export-payload", api_key=api_key)

        (ddir / "status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "quality.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "critic.json").write_text(json.dumps(critic, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "citations.json").write_text(json.dumps(citations, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "versions.json").write_text(json.dumps(versions, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "events.json").write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        (ddir / "export-payload.json").write_text(
            json.dumps(export_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        payload = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
        for export_format, fname in (
            ("both", "review-package.zip"),
            ("docx", "toc-review-package.docx"),
            ("xlsx", "logframe-review-package.xlsx"),
        ):
            content = _bytes_request(
                "POST",
                f"{base}/export",
                payload={"payload": payload, "format": export_format},
                api_key=api_key,
            )
            (ddir / fname).write_bytes(content)

    (root / "summary.md").write_text(_build_summary(root, rows), encoding="utf-8")
    print(f"pilot pack saved to {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
