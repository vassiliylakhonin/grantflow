from __future__ import annotations

from grantflow.swarm.findings import normalize_findings


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
