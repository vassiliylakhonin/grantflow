#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from grantflow.api.public_views import _comment_triage_summary_payload

DEFAULT_PRESET_KEYS = (
    "usaid_gov_ai_kazakhstan",
    "eu_digital_governance_moldova",
    "worldbank_public_sector_uzbekistan",
)


def _json_request(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def _bytes_request(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> bytes:
    headers: dict[str, str] = {}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def _slugify(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    while "--" in token:
        token = token.replace("--", "-")
    return token.strip("-") or "case"


def _wait_for_terminal_status(
    base_url: str,
    job_id: str,
    *,
    api_key: str | None,
    timeout_s: float,
    poll_interval_s: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = _json_request("GET", f"{base_url}/status/{job_id}", api_key=api_key)
        token = str(status.get("status") or "").strip().lower()
        if token in {"done", "error", "pending_hitl"}:
            return status
        time.sleep(poll_interval_s)
    raise RuntimeError(f"Timed out waiting for terminal status for job {job_id}")


def _drain_hitl_to_done(
    base_url: str,
    job_id: str,
    *,
    api_key: str | None,
    initial_status: dict[str, Any],
    timeout_s: float,
    poll_interval_s: float,
    max_cycles: int = 6,
) -> dict[str, Any]:
    status = initial_status
    for _ in range(max_cycles):
        if str(status.get("status") or "").strip().lower() == "done":
            return status
        if str(status.get("status") or "").strip().lower() != "pending_hitl":
            raise RuntimeError(f"Unexpected HITL status for job {job_id}: {status.get('status')}")
        checkpoint_id = str(status.get("checkpoint_id") or "").strip()
        checkpoint_stage = str(status.get("checkpoint_stage") or "").strip().lower()
        if not checkpoint_id:
            raise RuntimeError(f"Missing checkpoint_id for pending HITL job {job_id}")

        _json_request(
            "POST",
            f"{base_url}/hitl/approve",
            payload={
                "checkpoint_id": checkpoint_id,
                "approved": True,
                "feedback": f"Auto-approved by demo-pack at {checkpoint_stage or 'checkpoint'} stage",
            },
            api_key=api_key,
        )
        _json_request("POST", f"{base_url}/resume/{job_id}", payload={}, api_key=api_key)
        status = _wait_for_terminal_status(
            base_url,
            job_id,
            api_key=api_key,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
    raise RuntimeError(f"HITL job {job_id} did not reach done within {max_cycles} cycles")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _iso_at_offset(*, days: int = 0, hours: int = 0) -> str:
    dt = datetime.now(timezone.utc)
    dt = dt.replace(microsecond=0)
    return (
        (dt.fromtimestamp(dt.timestamp() - (days * 86400 + hours * 3600), tz=timezone.utc))
        .isoformat()
        .replace("+00:00", "Z")
    )


def _first_finding_id_for_section(critic_payload: dict[str, Any], section: str) -> str:
    findings = critic_payload.get("fatal_flaws")
    if not isinstance(findings, list):
        return ""
    for item in findings:
        if not isinstance(item, dict):
            continue
        if str(item.get("section") or "").strip().lower() != section:
            continue
        token = str(item.get("finding_id") or item.get("id") or "").strip()
        if token:
            return token
    for item in findings:
        if not isinstance(item, dict):
            continue
        token = str(item.get("finding_id") or item.get("id") or "").strip()
        if token:
            return token
    return ""


def _seed_review_comments(
    *,
    preset_key: str,
    donor_id: str,
    critic_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    logic_finding = _first_finding_id_for_section(critic_payload, "toc")
    logframe_finding = _first_finding_id_for_section(critic_payload, "logframe")
    general_finding = _first_finding_id_for_section(critic_payload, "general")
    donor_token = donor_id.strip().lower()
    if donor_token == "usaid":
        return [
            {
                "comment_id": f"{preset_key}-comment-logic-stale",
                "status": "open",
                "section": "toc",
                "author": "proposal-lead",
                "message": "Rewrite the DO -> IR -> Output chain so each result step reads as a distinct causal move with its own assumption line, not repeated boilerplate from the USAID results hierarchy package.",
                "version_id": "toc_v1",
                "linked_finding_id": logic_finding or None,
                "ts": _iso_at_offset(days=9),
                "updated_ts": _iso_at_offset(days=8, hours=12),
            },
            {
                "comment_id": f"{preset_key}-comment-grounding-ack",
                "status": "acknowledged",
                "section": "toc",
                "author": "mel-lead",
                "message": "Keep the claim, but replace fallback citations with source-linked ADS/PMP evidence and complete citation traceability before the USAID red-team review.",
                "version_id": "toc_v1",
                "linked_finding_id": logic_finding or general_finding or None,
                "ts": _iso_at_offset(days=4),
                "updated_ts": _iso_at_offset(days=3, hours=12),
                "acknowledged_at": _iso_at_offset(days=3, hours=12),
                "acknowledged_by": "mel-lead",
            },
            {
                "comment_id": f"{preset_key}-comment-logframe-resolved",
                "status": "resolved",
                "section": "logframe",
                "author": "review-manager",
                "message": "Baseline and target placeholders were replaced with reviewer-defensible values aligned to the USAID monitoring package and partner-owned means of verification.",
                "version_id": "logframe_v1",
                "linked_finding_id": logframe_finding or None,
                "ts": _iso_at_offset(days=2),
                "updated_ts": _iso_at_offset(days=1, hours=12),
                "resolved_at": _iso_at_offset(days=1, hours=12),
            },
        ]
    if donor_token == "eu":
        return [
            {
                "comment_id": f"{preset_key}-comment-measurement-stale",
                "status": "open",
                "section": "logframe",
                "author": "eu-reviewer",
                "message": "Tighten means of verification, responsible owner, and disaggregation for this intervention-logic row so it can survive formal EU quality review and annex verification.",
                "version_id": "logframe_v1",
                "linked_finding_id": logframe_finding or general_finding or None,
                "ts": _iso_at_offset(days=6),
                "updated_ts": _iso_at_offset(days=5, hours=6),
            },
            {
                "comment_id": f"{preset_key}-comment-delivery-open",
                "status": "open",
                "section": "general",
                "author": "eu-program-manager",
                "message": "Clarify delivery sequencing, partner responsibilities, and evidence handoff across work packages before the next internal intervention-logic review.",
                "version_id": "toc_v1",
                "linked_finding_id": None,
                "ts": _iso_at_offset(days=2),
                "updated_ts": _iso_at_offset(days=1, hours=12),
            },
        ]
    if donor_token == "worldbank":
        return [
            {
                "comment_id": f"{preset_key}-comment-isr-stale",
                "status": "open",
                "section": "general",
                "author": "wb-results-specialist",
                "message": "Add ISR-style evidence notes, attribution wording, and implementing-agency support so the results framework can be defended in the next portfolio review cycle.",
                "version_id": "toc_v1",
                "linked_finding_id": general_finding or None,
                "ts": _iso_at_offset(days=4),
                "updated_ts": _iso_at_offset(days=3, hours=6),
            },
            {
                "comment_id": f"{preset_key}-comment-pdo-resolved",
                "status": "resolved",
                "section": "toc",
                "author": "results-specialist",
                "message": "PDO wording now matches the results-framework and ISR review package, with clearer institutional performance language and reviewer-ready causal scope.",
                "version_id": "toc_v1",
                "linked_finding_id": logic_finding or general_finding or None,
                "ts": _iso_at_offset(days=1, hours=12),
                "updated_ts": _iso_at_offset(days=1),
                "resolved_at": _iso_at_offset(days=1),
            },
        ]
    return []


def _apply_seeded_review_comments(
    *,
    preset_key: str,
    donor_id: str,
    quality_payload: dict[str, Any],
    critic_payload: dict[str, Any],
    export_payload_wrapper: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    seeded_comments = _seed_review_comments(preset_key=preset_key, donor_id=donor_id, critic_payload=critic_payload)
    if not seeded_comments:
        return quality_payload, export_payload_wrapper, []

    payload_root = export_payload_wrapper.get("payload")
    payload_root_dict = dict(payload_root) if isinstance(payload_root, dict) else {}
    payload_root_dict["review_comments"] = seeded_comments
    updated_export_payload_wrapper = dict(export_payload_wrapper)
    updated_export_payload_wrapper["payload"] = payload_root_dict

    raw_findings = critic_payload.get("fatal_flaws")
    findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
    comment_triage = _comment_triage_summary_payload(
        review_comments=seeded_comments,
        critic_findings=findings,
        donor_id=donor_id,
    )
    total_comment_count = len(seeded_comments)
    resolved_comment_count = int(comment_triage.get("resolved_comment_count") or 0)
    acknowledged_comment_count = int(comment_triage.get("acknowledged_comment_count") or 0)
    updated_readiness = dict(
        quality_payload.get("review_readiness_summary")
        if isinstance(quality_payload.get("review_readiness_summary"), dict)
        else {}
    )
    updated_readiness.update(
        {
            "open_review_comments": int(comment_triage.get("open_comment_count") or 0),
            "resolved_review_comments": resolved_comment_count,
            "acknowledged_review_comments": acknowledged_comment_count,
            "pending_review_comments": int(comment_triage.get("pending_comment_count") or 0),
            "overdue_review_comments": int(comment_triage.get("overdue_comment_count") or 0),
            "stale_open_review_comments": int(comment_triage.get("stale_open_comment_count") or 0),
            "linked_review_comments": int(comment_triage.get("linked_comment_count") or 0),
            "orphan_linked_review_comments": int(comment_triage.get("orphan_linked_comment_count") or 0),
            "review_comment_resolution_rate": (
                round(resolved_comment_count / total_comment_count, 4) if total_comment_count else None
            ),
            "review_comment_acknowledgment_rate": (
                round((resolved_comment_count + acknowledged_comment_count) / total_comment_count, 4)
                if total_comment_count
                else None
            ),
            "comment_triage_summary": comment_triage,
        }
    )
    updated_quality_payload = dict(quality_payload)
    updated_quality_payload["review_readiness_summary"] = updated_readiness
    return updated_quality_payload, updated_export_payload_wrapper, seeded_comments


def _apply_generate_overrides(
    payload: dict[str, Any],
    *,
    llm_mode: bool,
    hitl_enabled: bool,
    architect_rag_enabled: bool,
) -> dict[str, Any]:
    out = dict(payload)
    out["llm_mode"] = bool(llm_mode)
    out["hitl_enabled"] = bool(hitl_enabled)
    out["architect_rag_enabled"] = bool(architect_rag_enabled)
    return out


def _resolve_local_preset_detail(
    preset_key: str,
    *,
    llm_mode: bool,
    hitl_enabled: bool,
    architect_rag_enabled: bool,
) -> dict[str, Any]:
    from grantflow.api.presets_service import _generate_preset_rows_for_public, _resolve_generate_payload_from_preset

    source_kind, generate_payload = _resolve_generate_payload_from_preset(preset_key, preset_type="auto")
    target: dict[str, Any] | None = None
    for row in _generate_preset_rows_for_public():
        if isinstance(row, dict) and str(row.get("preset_key") or "").strip() == preset_key:
            target = dict(row)
            break
    resolved_payload = _apply_generate_overrides(
        dict(generate_payload),
        llm_mode=llm_mode,
        hitl_enabled=hitl_enabled,
        architect_rag_enabled=architect_rag_enabled,
    )
    return {
        "preset_key": preset_key,
        "donor_id": str((target or {}).get("donor_id") or resolved_payload.get("donor_id") or "").strip() or None,
        "title": (target or {}).get("title"),
        "label": (target or {}).get("label"),
        "source_kind": (target or {}).get("source_kind") or source_kind,
        "source_file": (target or {}).get("source_file"),
        "generate_payload": resolved_payload,
    }


def _resolve_preset_detail(
    base_url: str,
    preset_key: str,
    *,
    api_key: str | None,
    llm_mode: bool,
    hitl_enabled: bool,
    architect_rag_enabled: bool,
) -> dict[str, Any]:
    query = urlencode(
        {
            "llm_mode": "true" if llm_mode else "false",
            "hitl_enabled": "true" if hitl_enabled else "false",
            "architect_rag_enabled": "true" if architect_rag_enabled else "false",
        }
    )
    url = f"{base_url}/generate/presets/{preset_key}?{query}"
    try:
        return _json_request("GET", url, api_key=api_key)
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise
    return _resolve_local_preset_detail(
        preset_key,
        llm_mode=llm_mode,
        hitl_enabled=hitl_enabled,
        architect_rag_enabled=architect_rag_enabled,
    )


def _submit_generate_request(
    base_url: str,
    *,
    preset_key: str,
    preset_detail: dict[str, Any],
    request_payload: dict[str, Any],
    api_key: str | None,
) -> tuple[dict[str, Any], str]:
    try:
        response = _json_request(
            "POST",
            f"{base_url}/generate/from-preset",
            payload=request_payload,
            api_key=api_key,
        )
        return response, "from-preset"
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise

    generate_payload = dict(preset_detail.get("generate_payload") or {})
    if not generate_payload:
        raise RuntimeError(f"Could not build generate payload for preset {preset_key}")
    response = _json_request(
        "POST",
        f"{base_url}/generate",
        payload=generate_payload,
        api_key=api_key,
    )
    return response, "generate"


def _build_summary(root: Path, rows: list[dict[str, Any]], *, llm_mode: bool, hitl_preset_key: str | None) -> str:
    lines: list[str] = []
    lines.append(f"# Demo Pack — {root.name}")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- Mode: `llm_mode={'true' if llm_mode else 'false'}`")
    lines.append("- Source: live API run via `scripts/demo_pack.py`")
    if hitl_preset_key:
        lines.append(f"- Auto-HITL case: `{hitl_preset_key}`")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append("| Preset | Donor | Job ID | Status | Quality | Critic | Citations | HITL | Seeded Comments |")
    lines.append("|---|---|---|---|---:|---:|---:|---|---:|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('preset_key')}`",
                    f"`{row.get('donor_id')}`",
                    f"`{row.get('job_id')}`",
                    str(row.get("status")),
                    str(row.get("quality_score")),
                    str(row.get("critic_score")),
                    str(row.get("citation_count")),
                    "yes" if row.get("hitl_enabled") else "no",
                    str(row.get("seeded_review_comments") or 0),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Files")
    for row in rows:
        case_slug = str(row.get("case_dir") or "")
        lines.append(
            f"- `{case_slug}/generate-request.json`, `{case_slug}/generate-response.json`, "
            f"`{case_slug}/status.json`, `{case_slug}/quality.json`, `{case_slug}/critic.json`"
        )
        lines.append(
            f"- `{case_slug}/citations.json`, `{case_slug}/versions.json`, `{case_slug}/events.json`, "
            f"`{case_slug}/export-payload.json`, `{case_slug}/review-package.zip`"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- This bundle is intended for demos and pilot evaluation, not final donor submission.")
    lines.append("- Grounding and citation quality remain dependent on corpus quality when RAG is enabled.")
    lines.append(
        "- When review-comment seeding is enabled, demo artifacts include a synthetic reviewer workflow scenario for triage and throughput evidence."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reproducible GrantFlow demo bundle from a live API.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", default="build/demo-pack")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--preset-keys", default=",".join(DEFAULT_PRESET_KEYS))
    parser.add_argument("--hitl-preset-key", default="")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.25)
    parser.add_argument("--llm-mode", action="store_true")
    parser.add_argument(
        "--architect-rag-enabled",
        dest="architect_rag_enabled",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-architect-rag-enabled",
        dest="architect_rag_enabled",
        action="store_false",
    )
    parser.add_argument("--seed-review-comments", action="store_true")
    args = parser.parse_args()

    base_url = str(args.api_base).rstrip("/")
    api_key = str(args.api_key).strip() or None
    output_dir = Path(str(args.output_dir)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    preset_keys = [token.strip() for token in str(args.preset_keys).split(",") if token.strip()]
    if not preset_keys:
        raise SystemExit("No preset keys configured")

    hitl_preset_key = str(args.hitl_preset_key).strip() or None
    if hitl_preset_key and hitl_preset_key not in preset_keys:
        raise SystemExit("--hitl-preset-key must be included in --preset-keys")

    summary_rows: list[dict[str, Any]] = []

    for preset_key in preset_keys:
        hitl_enabled = bool(hitl_preset_key and preset_key == hitl_preset_key)
        preset_detail = _resolve_preset_detail(
            base_url,
            preset_key,
            api_key=api_key,
            llm_mode=bool(args.llm_mode),
            hitl_enabled=hitl_enabled,
            architect_rag_enabled=bool(args.architect_rag_enabled),
        )
        generate_payload = dict(preset_detail.get("generate_payload") or {})
        donor_id = str(generate_payload.get("donor_id") or preset_detail.get("donor_id") or "").strip()
        if not donor_id:
            raise RuntimeError(f"Could not resolve donor_id for preset {preset_key}")

        request_payload = {
            "preset_key": preset_key,
            "preset_type": "auto",
            "llm_mode": bool(args.llm_mode),
            "hitl_enabled": hitl_enabled,
            "architect_rag_enabled": bool(args.architect_rag_enabled),
        }

        case_dir_name = f"{_slugify(donor_id)}-{_slugify(preset_key)}"
        case_dir = output_dir / case_dir_name
        case_dir.mkdir(parents=True, exist_ok=True)
        _write_json(case_dir / "preset-detail.json", preset_detail)
        _write_json(case_dir / "generate-request.json", request_payload)

        generate_response, generate_mode = _submit_generate_request(
            base_url,
            preset_key=preset_key,
            preset_detail=preset_detail,
            request_payload=request_payload,
            api_key=api_key,
        )
        _write_json(case_dir / "generate-response.json", generate_response)

        job_id = str(generate_response.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError(f"Missing job_id for preset {preset_key}")

        status = _wait_for_terminal_status(
            base_url,
            job_id,
            api_key=api_key,
            timeout_s=float(args.timeout_seconds),
            poll_interval_s=float(args.poll_interval_seconds),
        )
        if str(status.get("status") or "").strip().lower() == "pending_hitl":
            status = _drain_hitl_to_done(
                base_url,
                job_id,
                api_key=api_key,
                initial_status=status,
                timeout_s=float(args.timeout_seconds),
                poll_interval_s=float(args.poll_interval_seconds),
            )

        endpoints = {
            "status.json": f"{base_url}/status/{job_id}",
            "quality.json": f"{base_url}/status/{job_id}/quality",
            "critic.json": f"{base_url}/status/{job_id}/critic",
            "comments.json": f"{base_url}/status/{job_id}/comments",
            "citations.json": f"{base_url}/status/{job_id}/citations",
            "versions.json": f"{base_url}/status/{job_id}/versions",
            "metrics.json": f"{base_url}/status/{job_id}/metrics",
            "events.json": f"{base_url}/status/{job_id}/events",
            "hitl-history.json": f"{base_url}/status/{job_id}/hitl/history",
            "export-payload.json": f"{base_url}/status/{job_id}/export-payload",
        }
        fetched: dict[str, dict[str, Any]] = {}
        for filename, url in endpoints.items():
            payload = _json_request("GET", url, api_key=api_key)
            fetched[filename] = payload
            _write_json(case_dir / filename, payload)

        quality_payload = fetched["quality.json"]
        export_payload_wrapper = fetched["export-payload.json"]
        seeded_review_comments: list[dict[str, Any]] = []
        if bool(args.seed_review_comments):
            quality_payload, export_payload_wrapper, seeded_review_comments = _apply_seeded_review_comments(
                preset_key=preset_key,
                donor_id=donor_id,
                quality_payload=quality_payload,
                critic_payload=fetched["critic.json"],
                export_payload_wrapper=export_payload_wrapper,
            )
            fetched["quality.json"] = quality_payload
            fetched["export-payload.json"] = export_payload_wrapper
            fetched["comments.json"] = {
                "job_id": job_id,
                "comments": seeded_review_comments,
            }
            _write_json(case_dir / "quality.json", quality_payload)
            _write_json(case_dir / "export-payload.json", export_payload_wrapper)
            _write_json(case_dir / "comments.json", fetched["comments.json"])

        export_payload = dict(export_payload_wrapper.get("payload") or {})
        for export_format, filename in (
            ("both", "review-package.zip"),
            ("docx", "toc-review-package.docx"),
            ("xlsx", "logframe-review-package.xlsx"),
        ):
            content = _bytes_request(
                "POST",
                f"{base_url}/export",
                payload={"payload": export_payload, "format": export_format},
                api_key=api_key,
            )
            (case_dir / filename).write_bytes(content)

        citations_payload = fetched["citations.json"]
        final_status_payload = fetched["status.json"]
        final_donor_id = str(
            (final_status_payload.get("state") or {}).get("donor_id")
            or (final_status_payload.get("state") or {}).get("donor")
            or donor_id
        ).strip()

        summary_rows.append(
            {
                "preset_key": preset_key,
                "donor_id": final_donor_id,
                "job_id": job_id,
                "status": final_status_payload.get("status"),
                "quality_score": quality_payload.get("quality_score"),
                "critic_score": quality_payload.get("critic_score"),
                "citation_count": citations_payload.get("citation_count"),
                "hitl_enabled": hitl_enabled,
                "case_dir": case_dir_name,
                "generate_mode": generate_mode,
                "seeded_review_comments": len(seeded_review_comments),
            }
        )

    _write_json(output_dir / "benchmark-results.json", summary_rows)
    (output_dir / "summary.md").write_text(
        _build_summary(
            output_dir,
            summary_rows,
            llm_mode=bool(args.llm_mode),
            hitl_preset_key=hitl_preset_key,
        ),
        encoding="utf-8",
    )
    print(f"demo pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
