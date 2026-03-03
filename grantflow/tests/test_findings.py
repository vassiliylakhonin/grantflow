from __future__ import annotations

from grantflow.swarm.findings import (
    bind_findings_to_latest_versions,
    canonicalize_findings,
    finding_messages,
    normalize_findings,
    state_critic_findings,
    write_state_critic_findings,
)


def test_normalize_findings_converts_legacy_string_items():
    rows = normalize_findings(
        [
            "Missing indicator baseline in logframe.",
            {
                "code": "TOC_WEAK",
                "section": "toc",
                "severity": "high",
                "message": "Objective statement is too broad.",
                "fix_hint": "Split objective into measurable outcomes.",
            },
        ],
        default_source="rules",
    )

    assert len(rows) == 2
    first = rows[0]
    assert first["code"] == "LEGACY_UNSTRUCTURED_FINDING"
    assert first["section"] == "logframe"
    assert first["severity"] == "medium"
    assert first["status"] == "open"
    assert first["id"]
    assert first["finding_id"]
    assert first["id"] == first["finding_id"]
    assert first["source"] == "rules"

    second = rows[1]
    assert second["code"] == "TOC_WEAK"
    assert second["id"] == second["finding_id"]
    assert second["fix_suggestion"] == "Split objective into measurable outcomes."
    assert second["fix_hint"] == "Split objective into measurable outcomes."


def test_normalize_findings_preserves_previous_status_when_recomputing():
    previous = [
        {
            "id": "f-1",
            "finding_id": "f-1",
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "medium",
            "status": "acknowledged",
            "acknowledged_at": "2026-02-27T00:00:00Z",
            "message": "Objective too broad.",
            "source": "rules",
        }
    ]
    current = [
        {
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "medium",
            "message": "Objective too broad.",
            "source": "rules",
        }
    ]
    rows = normalize_findings(current, previous_items=previous, default_source="rules")
    assert rows[0]["id"] == "f-1"
    assert rows[0]["finding_id"] == "f-1"
    assert rows[0]["status"] == "acknowledged"
    assert rows[0]["acknowledged_at"] == "2026-02-27T00:00:00Z"


def test_normalize_findings_supports_id_only_payload():
    rows = normalize_findings(
        [
            {
                "id": "f-2",
                "code": "TOC_WEAK",
                "section": "toc",
                "severity": "high",
                "status": "resolved",
                "resolved_at": "2026-02-27T00:00:00Z",
                "message": "Objective statement lacks measurable phrasing.",
                "source": "rules",
            }
        ],
        default_source="rules",
    )
    assert rows[0]["id"] == "f-2"
    assert rows[0]["finding_id"] == "f-2"
    assert rows[0]["status"] == "resolved"
    assert rows[0]["resolved_at"] == "2026-02-27T00:00:00Z"


def test_normalize_findings_keeps_ack_timestamp_for_resolved_items():
    rows = normalize_findings(
        [
            {
                "id": "f-3",
                "code": "TOC_WEAK",
                "section": "toc",
                "severity": "high",
                "status": "resolved",
                "acknowledged_at": "2026-02-27T00:00:00Z",
                "resolved_at": "2026-02-27T01:00:00Z",
                "message": "Objective statement lacks measurable phrasing.",
                "source": "rules",
            }
        ],
        default_source="rules",
    )
    assert rows[0]["status"] == "resolved"
    assert rows[0]["acknowledged_at"] == "2026-02-27T00:00:00Z"
    assert rows[0]["resolved_at"] == "2026-02-27T01:00:00Z"


def test_bind_findings_to_latest_versions_fills_missing_version_id():
    findings = [
        {
            "id": "f-toc",
            "finding_id": "f-toc",
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "medium",
            "status": "open",
            "message": "Objective is broad.",
            "source": "rules",
        },
        {
            "id": "f-logframe",
            "finding_id": "f-logframe",
            "code": "LOGFRAME_MISSING_BASELINE",
            "section": "logframe",
            "severity": "high",
            "status": "open",
            "message": "Baseline missing.",
            "source": "rules",
        },
        {
            "id": "f-general",
            "finding_id": "f-general",
            "code": "GENERAL_NOTE",
            "section": "general",
            "severity": "low",
            "status": "open",
            "message": "General review note.",
            "source": "rules",
        },
    ]
    state = {
        "draft_versions": [
            {"version_id": "toc_v1", "sequence": 1, "section": "toc"},
            {"version_id": "toc_v2", "sequence": 2, "section": "toc"},
            {"version_id": "logframe_v1", "sequence": 3, "section": "logframe"},
        ]
    }

    out = bind_findings_to_latest_versions(findings, state=state)
    by_id = {row["finding_id"]: row for row in out}
    assert by_id["f-toc"]["version_id"] == "toc_v2"
    assert by_id["f-logframe"]["version_id"] == "logframe_v1"
    assert by_id["f-general"].get("version_id") is None


def test_normalize_findings_generates_deterministic_id_for_legacy_string():
    payload = ["Missing indicator baseline in logframe."]
    first = normalize_findings(payload, default_source="rules")
    second = normalize_findings(payload, default_source="rules")
    assert first[0]["finding_id"] == second[0]["finding_id"]
    assert first[0]["id"] == second[0]["id"]


def test_normalize_findings_generates_deterministic_id_for_object_without_id():
    payload = [
        {
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "high",
            "message": "Objective statement is too broad.",
            "source": "rules",
        }
    ]
    first = normalize_findings(payload, default_source="rules")
    second = normalize_findings(payload, default_source="rules")
    assert first[0]["finding_id"] == second[0]["finding_id"]
    assert first[0]["id"] == second[0]["id"]


def test_canonicalize_findings_dedupes_by_finding_id():
    items = [
        {
            "finding_id": "f-dup",
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "high",
            "status": "open",
            "message": "First",
            "source": "rules",
        },
        {
            "id": "f-dup",
            "code": "TOC_WEAK",
            "section": "toc",
            "severity": "low",
            "status": "acknowledged",
            "message": "Second",
            "source": "rules",
        },
    ]
    rows = canonicalize_findings(items, default_source="rules")
    assert len(rows) == 1
    assert rows[0]["id"] == "f-dup"
    assert rows[0]["finding_id"] == "f-dup"
    assert rows[0]["status"] == "acknowledged"
    assert rows[0]["message"] == "Second"


def test_state_critic_findings_reads_legacy_alias_and_write_syncs_aliases():
    state = {
        "critic_fatal_flaws": [
            {
                "code": "TOC_WEAK",
                "section": "toc",
                "severity": "high",
                "message": "Legacy alias item",
                "source": "rules",
            }
        ],
        "draft_versions": [{"version_id": "toc_v2", "section": "toc", "sequence": 2}],
    }
    read_rows = state_critic_findings(state, default_source="rules")
    assert len(read_rows) == 1
    assert read_rows[0]["version_id"] == "toc_v2"
    assert read_rows[0]["id"] == read_rows[0]["finding_id"]

    written = write_state_critic_findings(state, read_rows, default_source="rules")
    assert len(written) == 1
    notes = state.get("critic_notes")
    assert isinstance(notes, dict)
    assert notes.get("fatal_flaws") == written
    assert state.get("critic_fatal_flaws") == written


def test_finding_messages_returns_unique_entries():
    findings = [
        {"message": "Fix logframe baseline."},
        {"message": "Fix logframe baseline."},
        {"message": "Add ToC assumptions."},
    ]
    out = finding_messages(findings, fallback="Minor improvements suggested")
    assert out == ["Fix logframe baseline.", "Add ToC assumptions."]
