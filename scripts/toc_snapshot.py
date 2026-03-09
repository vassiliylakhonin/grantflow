from __future__ import annotations

from typing import Any


def _compact_text(value: Any, *, max_len: int = 140) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3].rstrip()}..."


def _state_toc(export_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    payload_root = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
    state = payload_root.get("state") if isinstance(payload_root.get("state"), dict) else {}
    donor_id = str(state.get("donor_id") or "").strip().lower()
    toc = state.get("toc") if isinstance(state.get("toc"), dict) else {}
    if not toc:
        toc_draft = state.get("toc_draft") if isinstance(state.get("toc_draft"), dict) else {}
        toc = toc_draft.get("toc") if isinstance(toc_draft.get("toc"), dict) else {}
    return donor_id, toc if isinstance(toc, dict) else {}


def build_toc_snapshot(export_payload: dict[str, Any], *, max_items: int = 4) -> list[str]:
    donor_id, toc = _state_toc(export_payload)
    if not toc:
        return []

    lines: list[str] = []

    def add(label: str, value: Any) -> None:
        text = _compact_text(value)
        if text and len(lines) < max_items:
            lines.append(f"{label}: {text}")

    if donor_id == "usaid":
        add("Project goal", toc.get("project_goal"))
        for row in (toc.get("development_objectives") or [])[:2]:
            if isinstance(row, dict):
                add(str(row.get("do_id") or "DO"), row.get("description"))
        assumptions = toc.get("critical_assumptions") or []
        if assumptions:
            add("Critical assumption", assumptions[0])
        return lines[:max_items]

    if donor_id == "eu":
        overall = toc.get("overall_objective")
        if isinstance(overall, dict):
            add("Overall objective", overall.get("title"))
        for row in (toc.get("specific_objectives") or [])[:2]:
            if isinstance(row, dict):
                add(str(row.get("objective_id") or "Specific objective"), row.get("title"))
        outcomes = toc.get("expected_outcomes") or []
        if outcomes:
            first = outcomes[0]
            if isinstance(first, dict):
                add(str(first.get("outcome_id") or "Expected outcome"), first.get("title"))
        return lines[:max_items]

    if donor_id == "worldbank":
        add("PDO", toc.get("project_development_objective"))
        for row in (toc.get("objectives") or [])[:2]:
            if isinstance(row, dict):
                add(str(row.get("objective_id") or "Objective"), row.get("title"))
        results = toc.get("results_chain") or []
        if results:
            first = results[0]
            if isinstance(first, dict):
                add(str(first.get("result_id") or "Result"), first.get("title"))
        return lines[:max_items]

    add("Goal", toc.get("project_goal") or toc.get("project_development_objective"))
    for key in ("development_objectives", "specific_objectives", "objectives", "expected_outcomes", "results_chain"):
        for row in (toc.get(key) or [])[: max(0, max_items - len(lines))]:
            if not isinstance(row, dict):
                continue
            add(
                str(
                    row.get("objective_id")
                    or row.get("do_id")
                    or row.get("outcome_id")
                    or row.get("result_id")
                    or key[:-1].title()
                ),
                row.get("title") or row.get("description"),
            )
            if len(lines) >= max_items:
                break
        if len(lines) >= max_items:
            break
    return lines[:max_items]


def build_logframe_snapshot(export_payload: dict[str, Any], *, max_items: int = 3) -> list[str]:
    payload_root = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
    state = payload_root.get("state") if isinstance(payload_root.get("state"), dict) else {}
    mel = state.get("mel") if isinstance(state.get("mel"), dict) else {}
    logframe = state.get("logframe") if isinstance(state.get("logframe"), dict) else {}
    indicators = mel.get("indicators") if isinstance(mel.get("indicators"), list) else []
    if not indicators:
        indicators = logframe.get("indicators") if isinstance(logframe.get("indicators"), list) else []

    lines: list[str] = []
    for indicator in indicators[:max_items]:
        if not isinstance(indicator, dict):
            continue
        code = _compact_text(
            indicator.get("code") or indicator.get("indicator_code") or indicator.get("indicator_id"),
            max_len=24,
        )
        name = _compact_text(indicator.get("name"), max_len=96)
        baseline = _compact_text(indicator.get("baseline"), max_len=32) or "-"
        target = _compact_text(indicator.get("target"), max_len=32) or "-"
        frequency = _compact_text(indicator.get("frequency"), max_len=24)
        owner = _compact_text(indicator.get("owner"), max_len=44)
        means_of_verification = _compact_text(indicator.get("means_of_verification"), max_len=56)

        parts = [f"`{code or '-'}` {name or '-'}", f"baseline `{baseline}`", f"target `{target}`"]
        if frequency:
            parts.append(f"freq `{frequency}`")
        if owner:
            parts.append(f"owner `{owner}`")
        if means_of_verification:
            parts.append(f"mov `{means_of_verification}`")
        lines.append(" | ".join(parts))

    return lines[:max_items]
