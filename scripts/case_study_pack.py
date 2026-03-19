#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CASE_FILES = (
    "generate-request.json",
    "generate-response.json",
    "preset-detail.json",
    "status.json",
    "quality.json",
    "critic.json",
    "citations.json",
    "versions.json",
    "events.json",
    "hitl-history.json",
    "metrics.json",
    "export-payload.json",
    "toc-review-package.docx",
    "logframe-review-package.xlsx",
    "review-package.zip",
)

SUPPORTING_FILES = (
    "buyer-brief.md",
    "pilot-scorecard.md",
    "pilot-metrics.md",
    "pilot-evaluation-checklist.md",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _slugify(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    while "--" in token:
        token = token.replace("--", "-")
    return token.strip("-") or "case"


def _pick_case_row(
    rows: list[dict[str, Any]],
    *,
    case_dir: str,
    preset_key: str,
) -> dict[str, Any]:
    if case_dir:
        for row in rows:
            if str(row.get("case_dir") or "").strip() == case_dir:
                return row
        raise SystemExit(f"Case dir not found in benchmark results: {case_dir}")
    if preset_key:
        for row in rows:
            if str(row.get("preset_key") or "").strip() == preset_key:
                return row
        raise SystemExit(f"Preset key not found in benchmark results: {preset_key}")
    return rows[0]


def _extract_toc_preview(versions_payload: dict[str, Any]) -> dict[str, Any]:
    versions = versions_payload.get("versions") or []
    toc_version = next(
        (item for item in versions if str(item.get("section") or "").strip().lower() == "toc"),
        {},
    )
    toc = ((toc_version.get("content") or {}).get("toc") or {}) if isinstance(toc_version, dict) else {}
    development_objectives = toc.get("development_objectives") or []
    preview_dos: list[dict[str, Any]] = []
    for development_objective in development_objectives[:2]:
        intermediate_results = development_objective.get("intermediate_results") or []
        preview_dos.append(
            {
                "do_id": development_objective.get("do_id"),
                "description": development_objective.get("description"),
                "intermediate_results": [
                    {
                        "ir_id": intermediate_result.get("ir_id"),
                        "description": intermediate_result.get("description"),
                    }
                    for intermediate_result in intermediate_results[:2]
                ],
            }
        )
    return {
        "project_goal": toc.get("project_goal"),
        "development_objectives": preview_dos,
        "critical_assumptions": (toc.get("critical_assumptions") or [])[:3],
    }


def _extract_logframe_preview(export_payload: dict[str, Any]) -> list[dict[str, Any]]:
    state = (export_payload.get("payload") or {}).get("state") or {}
    logframe = state.get("logframe") or {}
    mel = state.get("mel") or {}
    indicators = (mel.get("indicators") or []) or (logframe.get("indicators") or [])
    preview: list[dict[str, Any]] = []
    for indicator in indicators[:3]:
        preview.append(
            {
                "code": indicator.get("code") or indicator.get("indicator_code") or indicator.get("indicator_id"),
                "name": indicator.get("name"),
                "baseline": indicator.get("baseline"),
                "target": indicator.get("target"),
                "frequency": indicator.get("frequency"),
                "data_source": indicator.get("data_source"),
            }
        )
    return preview


def _build_summary(
    *,
    pilot_pack_name: str,
    row: dict[str, Any],
    status_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    critic_payload: dict[str, Any],
    citations_payload: dict[str, Any],
    metrics_payload: dict[str, Any],
    versions_payload: dict[str, Any],
    export_payload: dict[str, Any],
    supporting_files: list[str],
) -> str:
    state = (status_payload.get("state") or {}) if isinstance(status_payload, dict) else {}
    input_context = state.get("input_context") or {}
    toc_preview = _extract_toc_preview(versions_payload)
    logframe_preview = _extract_logframe_preview(export_payload)
    fatal_flaws = critic_payload.get("fatal_flaws") or []
    citations = citations_payload.get("citations") or []
    top_citations = citations[:3]

    lines: list[str] = []
    lines.append("# GrantFlow Case Study Pack")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Source pilot pack: `{pilot_pack_name}`")
    lines.append(f"- Case dir: `{row.get('case_dir')}`")
    lines.append("")
    lines.append("## Case Snapshot")
    lines.append(f"- Donor: `{row.get('donor_id')}`")
    lines.append(f"- Preset: `{row.get('preset_key')}`")
    lines.append(f"- Job ID: `{row.get('job_id')}`")
    lines.append(f"- Status: `{row.get('status')}`")
    lines.append(f"- HITL enabled: `{'true' if row.get('hitl_enabled') else 'false'}`")
    lines.append(f"- Quality score: `{quality_payload.get('quality_score', row.get('quality_score'))}`")
    lines.append(f"- Critic score: `{quality_payload.get('critic_score', row.get('critic_score'))}`")
    lines.append(f"- Citation count: `{citations_payload.get('citation_count', row.get('citation_count'))}`")
    lines.append("")
    lines.append("## Problem Context")
    if input_context:
        for key in (
            "project",
            "country",
            "region",
            "timeframe",
            "problem",
            "target_population",
            "expected_change",
        ):
            value = input_context.get(key)
            if value:
                lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")
    else:
        lines.append("- No input context preview available.")
    lines.append("")
    lines.append("## Workflow Evidence")
    lines.append(f"- Terminal status: `{metrics_payload.get('terminal_status', row.get('status'))}`")
    lines.append(f"- Time to first draft (s): `{metrics_payload.get('time_to_first_draft_seconds', '-')}`")
    lines.append(f"- Time to terminal (s): `{metrics_payload.get('time_to_terminal_seconds', '-')}`")
    lines.append(f"- Time in pending HITL (s): `{metrics_payload.get('time_in_pending_hitl_seconds', '-')}`")
    lines.append(f"- Status changes: `{metrics_payload.get('status_change_count', '-')}`")
    lines.append(f"- Pauses: `{metrics_payload.get('pause_count', '-')}`")
    lines.append(f"- Resumes: `{metrics_payload.get('resume_count', '-')}`")
    lines.append(
        f"- Grounding risk: `{metrics_payload.get('grounding_risk_level', quality_payload.get('citations', {}).get('grounding_risk_level', '-'))}`"
    )
    lines.append("")
    lines.append("## ToC Preview")
    if toc_preview.get("project_goal"):
        lines.append(f"- Project goal: {toc_preview['project_goal']}")
    for development_objective in toc_preview.get("development_objectives") or []:
        lines.append(f"- {development_objective.get('do_id')}: {development_objective.get('description')}")
        for intermediate_result in development_objective.get("intermediate_results") or []:
            lines.append(f"  - {intermediate_result.get('ir_id')}: {intermediate_result.get('description')}")
    assumptions = toc_preview.get("critical_assumptions") or []
    if assumptions:
        lines.append("- Critical assumptions:")
        for assumption in assumptions:
            lines.append(f"  - {assumption}")
    lines.append("")
    lines.append("## LogFrame Indicator Preview")
    if logframe_preview:
        for indicator in logframe_preview:
            lines.append(
                f"- `{indicator.get('code') or '-'}` {indicator.get('name') or '-'} | baseline: `{indicator.get('baseline') or '-'}` | target: `{indicator.get('target') or '-'}` | frequency: `{indicator.get('frequency') or '-'}`"
            )
    else:
        lines.append("- No logframe indicator preview available in export payload.")
    lines.append("")
    lines.append("## Critic Findings")
    lines.append(f"- Fatal flaw count: `{critic_payload.get('fatal_flaw_count', 0)}`")
    if fatal_flaws:
        for flaw in fatal_flaws[:3]:
            lines.append(
                f"- `{flaw.get('severity', 'unknown')}` `{flaw.get('section', '-')}`: {flaw.get('message') or flaw.get('rationale') or '-'}"
            )
    else:
        lines.append("- No fatal flaws recorded.")
    if critic_payload.get("revision_instructions"):
        lines.append("")
        lines.append("Revision instructions:")
        lines.append("")
        lines.append("```text")
        lines.append(str(critic_payload.get("revision_instructions")))
        lines.append("```")
    lines.append("")
    lines.append("## Citation Preview")
    for citation in top_citations:
        lines.append(
            f"- `{citation.get('stage', '-')}` `{citation.get('statement_path', '-')}` -> `{citation.get('doc_id', '-')}` (confidence `{citation.get('citation_confidence', '-')}`)"
        )
    if not top_citations:
        lines.append("- No citations available.")
    lines.append("")
    lines.append("## Included Files")
    lines.append("- `artifacts/` contains copied JSON traces and export files for this case only.")
    if supporting_files:
        lines.append("- `supporting/` contains pilot-level supporting docs copied from the source pilot pack.")
    lines.append("")
    lines.append("## Notes")
    lines.append(
        "- This is a single-case review pack for demos and pilot conversations, not a submission-ready donor package."
    )
    lines.append("- Final compliance review remains a human responsibility.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact GrantFlow case-study pack from an existing pilot pack."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--case-dir", default="")
    parser.add_argument("--preset-key", default="")
    parser.add_argument("--output-dir", default="build/case-study-pack")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")

    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    row = _pick_case_row(
        rows,
        case_dir=str(args.case_dir).strip(),
        preset_key=str(args.preset_key).strip(),
    )
    case_dir_name = str(row.get("case_dir") or "").strip()
    if not case_dir_name:
        raise SystemExit("Selected benchmark row has no case_dir")

    source_case_dir = pilot_pack_dir / "live-runs" / case_dir_name
    if not source_case_dir.exists():
        raise SystemExit(f"Missing case directory: {source_case_dir}")

    output_root = Path(str(args.output_dir)).resolve() / _slugify(case_dir_name)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    artifacts_dir = output_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for file_name in CASE_FILES:
        _copy_if_exists(source_case_dir / file_name, artifacts_dir / file_name)

    supporting_dir = output_root / "supporting"
    copied_supporting_files: list[str] = []
    for file_name in SUPPORTING_FILES:
        src = pilot_pack_dir / file_name
        if src.exists():
            _copy_if_exists(src, supporting_dir / file_name)
            copied_supporting_files.append(file_name)

    status_payload = _read_json(source_case_dir / "status.json")
    quality_payload = _read_json(source_case_dir / "quality.json")
    critic_payload = _read_json(source_case_dir / "critic.json")
    citations_payload = _read_json(source_case_dir / "citations.json")
    metrics_payload = _read_json(source_case_dir / "metrics.json")
    versions_payload = _read_json(source_case_dir / "versions.json")
    export_payload = _read_json(source_case_dir / "export-payload.json")

    (output_root / "README.md").write_text(
        _build_summary(
            pilot_pack_name=pilot_pack_dir.name,
            row=row,
            status_payload=status_payload,
            quality_payload=quality_payload,
            critic_payload=critic_payload,
            citations_payload=citations_payload,
            metrics_payload=metrics_payload,
            versions_payload=versions_payload,
            export_payload=export_payload,
            supporting_files=copied_supporting_files,
        ),
        encoding="utf-8",
    )
    print(f"case study pack saved to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
