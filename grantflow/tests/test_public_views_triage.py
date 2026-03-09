from __future__ import annotations

from grantflow.api.public_views import (
    _comment_triage_summary_payload,
    _finding_recommended_action,
    _finding_review_title,
)


def test_finding_recommended_action_uses_donor_specific_logic_language():
    action = _finding_recommended_action(
        {
            "code": "USAID_DO_MISSING",
            "section": "toc",
            "message": "USAID ToC is missing Development Objectives.",
            "severity": "high",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "DO -> IR -> Output" in action
    assert "USAID results hierarchy" in action


def test_finding_recommended_action_uses_donor_specific_measurement_language():
    action = _finding_recommended_action(
        {
            "code": "MEL_PLACEHOLDER_TARGETS",
            "section": "logframe",
            "message": "Most indicators still use placeholder baseline/target values.",
            "severity": "medium",
            "status": "open",
        },
        donor_id="worldbank",
    )
    assert "placeholder baseline and target values" in action.lower()
    assert "world bank results framework and pdo package" in action.lower()


def test_finding_recommended_action_uses_donor_specific_compliance_language():
    action = _finding_recommended_action(
        {
            "code": "EU_OVERALL_OBJECTIVE_MISSING",
            "section": "toc",
            "message": "EU ToC is missing the overall objective needed to anchor the intervention logic.",
            "severity": "high",
            "status": "open",
        },
        donor_id="eu",
    )
    assert "overall objective" in action.lower()
    assert "verification intent" in action.lower()


def test_finding_recommended_action_makes_grounding_gap_more_specific():
    action = _finding_recommended_action(
        {
            "code": "TOC_EVIDENCE_GAP",
            "section": "toc",
            "message": "Outcome chain lacks grounded support and relies on fallback evidence.",
            "severity": "high",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "fallback evidence" in action.lower()
    assert "pmp references" in action.lower()


def test_finding_recommended_action_makes_placeholder_targets_more_specific():
    action = _finding_recommended_action(
        {
            "code": "BASELINE_TARGET_MISSING",
            "section": "logframe",
            "message": "Indicators still use placeholder baseline and target values.",
            "severity": "medium",
            "status": "open",
        },
        donor_id="eu",
    )
    assert "placeholder baseline and target values" in action.lower()
    assert "eu intervention logic and verification package" in action.lower()


def test_finding_recommended_action_makes_boilerplate_logic_more_specific():
    action = _finding_recommended_action(
        {
            "code": "TOC_BOILERPLATE_REPETITION",
            "section": "toc",
            "message": "Theory of Change contains repeated boilerplate narrative across multiple sections.",
            "severity": "low",
            "status": "open",
        },
        donor_id="usaid",
    )
    assert "repeated boilerplate" in action.lower()
    assert "reviewer-ready" in action.lower()


def test_finding_review_title_prefers_human_readable_mapping_for_known_codes():
    title = _finding_review_title(
        {
            "code": "USAID_DO_MISSING",
            "section": "toc",
            "message": "USAID ToC is missing Development Objectives.",
        }
    )
    assert title == "USAID Development Objectives Missing"


def test_finding_review_title_uses_semantic_mapping_for_boilerplate():
    title = _finding_review_title(
        {
            "code": "TOC_BOILERPLATE_REPETITION",
            "section": "toc",
            "message": "Theory of Change contains repeated boilerplate narrative across multiple sections.",
        }
    )
    assert title == "ToC Boilerplate Repetition"


def test_finding_review_title_uses_semantic_mapping_for_traceability_gap():
    title = _finding_review_title(
        {
            "code": "ARCHITECT_TRACEABILITY_GAP",
            "section": "toc",
            "message": "Architect claim citations contain significant traceability gaps with missing doc_id and page metadata.",
        }
    )
    assert title == "Citation Traceability Gap"


def test_comment_triage_summary_tracks_overdue_and_next_action():
    summary = _comment_triage_summary_payload(
        review_comments=[
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "linked_finding_id": "finding-1",
                "ts": "2026-03-01T10:00:00+00:00",
                "due_at": "2026-03-01T11:00:00+00:00",
            },
            {
                "comment_id": "comment-2",
                "status": "resolved",
                "section": "logframe",
                "ts": "2026-03-01T10:00:00+00:00",
                "resolved_at": "2026-03-01T10:30:00+00:00",
            },
        ],
        critic_findings=[
            {
                "id": "finding-1",
                "status": "open",
                "severity": "high",
                "section": "toc",
            }
        ],
        donor_id="usaid",
    )
    assert summary["open_comment_count"] == 1
    assert summary["resolved_comment_count"] == 1
    assert summary["overdue_comment_count"] == 1
    assert summary["next_comment_section"] == "toc"
    assert "USAID results hierarchy" in str(summary["next_recommended_action"])
