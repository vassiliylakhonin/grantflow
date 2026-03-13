from __future__ import annotations

from datetime import datetime, timedelta, timezone

from grantflow.api.public_views import (
    _comment_triage_summary_payload,
    _finding_recommended_action,
    _finding_review_title,
    public_job_review_workflow_payload,
    public_portfolio_review_workflow_payload,
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
    now = datetime.now(timezone.utc)
    summary = _comment_triage_summary_payload(
        review_comments=[
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "linked_finding_id": "finding-1",
                "ts": (now - timedelta(days=3)).isoformat(),
                "due_at": (now - timedelta(days=2, hours=20)).isoformat(),
            },
            {
                "comment_id": "comment-2",
                "status": "acknowledged",
                "section": "logframe",
                "linked_finding_id": "finding-2",
                "ts": (now - timedelta(hours=6)).isoformat(),
                "acknowledged_at": (now - timedelta(hours=5, minutes=45)).isoformat(),
            },
            {
                "comment_id": "comment-3",
                "status": "resolved",
                "section": "logframe",
                "ts": (now - timedelta(hours=5)).isoformat(),
                "resolved_at": (now - timedelta(hours=4, minutes=30)).isoformat(),
            },
        ],
        critic_findings=[
            {
                "id": "finding-1",
                "status": "open",
                "severity": "high",
                "section": "toc",
                "message": "Theory of Change repeats boilerplate narrative across multiple sections.",
            },
            {
                "id": "finding-2",
                "status": "acknowledged",
                "severity": "medium",
                "section": "logframe",
                "message": "Indicator baseline and target values still need confirmation.",
            },
        ],
        donor_id="usaid",
    )
    assert summary["open_comment_count"] == 2
    assert summary["resolved_comment_count"] == 1
    assert summary["acknowledged_comment_count"] == 1
    assert summary["overdue_comment_count"] == 1
    assert summary["stale_open_comment_count"] == 1
    assert summary["aging_band_counts"]["d3_7"] == 1
    assert summary["aging_band_counts"]["lt_24h"] == 1
    assert summary["next_comment_section"] == "toc"
    assert summary["next_comment_bucket"] == "logic"
    assert summary["comment_bucket_counts"]["logic"] == 1
    assert "USAID results hierarchy" in str(summary["next_recommended_action"])


def test_job_review_workflow_payload_emits_comment_triage_and_reviewer_workflow_summary():
    job = {
        "status": "done",
        "state": {
            "donor_id": "usaid",
            "critic_notes": {
                "fatal_flaws": [
                    {
                        "finding_id": "finding-1",
                        "status": "open",
                        "severity": "high",
                        "section": "toc",
                        "message": "Theory of Change repeats boilerplate narrative across multiple sections.",
                    }
                ]
            },
            "critic_fatal_flaws": [
                {
                    "finding_id": "finding-1",
                    "status": "open",
                    "severity": "high",
                    "section": "toc",
                    "message": "Theory of Change repeats boilerplate narrative across multiple sections.",
                }
            ],
        },
        "review_comments": [
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "linked_finding_id": "finding-1",
                "ts": "2026-03-01T10:00:00+00:00",
                "updated_ts": "2026-03-01T10:30:00+00:00",
                "due_at": "2026-03-01T11:00:00+00:00",
            },
            {
                "comment_id": "comment-2",
                "status": "acknowledged",
                "section": "toc",
                "linked_finding_id": "finding-1",
                "ts": "2026-03-03T09:00:00+00:00",
                "acknowledged_at": "2026-03-03T09:15:00+00:00",
            },
            {
                "comment_id": "comment-3",
                "status": "resolved",
                "section": "logframe",
                "ts": "2026-03-03T10:00:00+00:00",
                "resolved_at": "2026-03-03T10:30:00+00:00",
            },
        ],
        "job_events": [
            {
                "event_id": "evt-1",
                "ts": "2026-03-01T10:30:00+00:00",
                "type": "review_comment_added",
                "comment_id": "comment-1",
                "section": "toc",
            },
            {
                "event_id": "evt-2",
                "ts": "2026-03-03T09:15:00+00:00",
                "type": "review_comment_status_changed",
                "comment_id": "comment-2",
                "section": "toc",
                "status": "acknowledged",
            },
            {
                "event_id": "evt-3",
                "ts": "2026-03-03T10:30:00+00:00",
                "type": "review_comment_status_changed",
                "comment_id": "comment-3",
                "section": "logframe",
                "status": "resolved",
            },
        ],
    }
    payload = public_job_review_workflow_payload("job-1", job)
    summary = payload["summary"]
    findings = payload["findings"]
    assert findings[0]["triage_priority_label"] == "P0 · Immediate"
    assert isinstance(findings[0]["reviewer_next_actions"], list)
    assert findings[0]["reviewer_next_action_short"]
    assert summary["acknowledged_comment_count"] == 1
    assert summary["comment_triage_summary"]["stale_comment_bucket_counts"]["logic"] == 2
    assert summary["comment_triage_summary"]["next_comment_bucket"] == "logic"
    assert summary["reviewer_workflow_summary"]["open_items"] == 3
    assert summary["reviewer_workflow_summary"]["acknowledged_items"] == 1
    assert summary["reviewer_workflow_summary"]["resolved_items"] == 1
    assert summary["reviewer_workflow_summary"]["top_stale_comment_bucket"] == "logic"
    assert summary["action_queue_summary"]["finding_ack_queue_count"] == 1
    assert summary["action_queue_summary"]["comment_ack_queue_count"] == 2
    assert summary["action_queue_summary"]["comment_resolve_queue_count"] == 1
    assert summary["action_queue_summary"]["comment_reopen_queue_count"] == 1
    assert summary["action_queue_summary"]["next_primary_action"] == "ack_finding"
    assert summary["throughput_summary"]["finding_ack_completed_count"] == 0
    assert summary["throughput_summary"]["comment_ack_completed_count"] == 1
    assert summary["throughput_summary"]["comment_resolve_completed_count"] == 1
    assert summary["throughput_summary"]["dominant_completed_action"] == "ack_comment"
    assert summary["queue_delta_summary"]["finding_ack_queue_count"] == 1
    assert summary["queue_delta_summary"]["comment_ack_net_delta"] == 1
    assert summary["queue_delta_summary"]["comment_resolve_net_delta"] == 0
    assert summary["triage_summary"]["next_priority_label"] == "P0 · Immediate"
    assert "ToC" in str(summary["triage_summary"]["next_action_brief"])
    assert summary["review_workflow_policy_summary"]["status"] == "breach"
    assert summary["review_workflow_policy_summary"]["go_no_go_flag"] == "hold"
    assert "overdue_review_comments_present" in summary["review_workflow_policy_summary"]["breaches"]


def test_portfolio_review_workflow_payload_aggregates_reviewer_workflow_summary():
    base_job = {
        "status": "done",
        "state": {
            "donor_id": "usaid",
            "critic_notes": {
                "fatal_flaws": [
                    {
                        "finding_id": "finding-1",
                        "status": "open",
                        "severity": "high",
                        "section": "toc",
                        "message": "Theory of Change repeats boilerplate narrative across multiple sections.",
                    }
                ]
            },
            "critic_fatal_flaws": [
                {
                    "finding_id": "finding-1",
                    "status": "open",
                    "severity": "high",
                    "section": "toc",
                    "message": "Theory of Change repeats boilerplate narrative across multiple sections.",
                }
            ],
        },
        "review_comments": [
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "linked_finding_id": "finding-1",
                "ts": "2026-03-01T10:00:00+00:00",
                "updated_ts": "2026-03-01T10:30:00+00:00",
                "due_at": "2026-03-01T11:00:00+00:00",
            }
        ],
        "job_events": [
            {
                "event_id": "evt-1",
                "ts": "2026-03-01T10:30:00+00:00",
                "type": "review_comment_added",
                "comment_id": "comment-1",
                "section": "toc",
            }
        ],
    }
    portfolio = public_portfolio_review_workflow_payload(
        {
            "job-1": base_job,
            "job-2": {
                **base_job,
                "state": {
                    **base_job["state"],
                    "donor_id": "eu",
                },
            },
        }
    )
    summary = portfolio["summary"]
    assert summary["comment_status_counts"]["open"] == 2
    assert summary["reviewer_workflow_summary"]["open_items"] >= 2
    assert summary["reviewer_workflow_summary"]["stale_comment_bucket_counts"]["logic"] == 2
    assert summary["reviewer_workflow_summary"]["top_stale_comment_bucket"] == "logic"
    assert summary["action_queue_summary"]["finding_ack_queue_count"] == 2
    assert summary["action_queue_summary"]["comment_ack_queue_count"] == 2
    assert summary["action_queue_summary"]["next_primary_action"] == "ack_finding"
    assert summary["throughput_summary"]["comment_added_count"] == 2
    assert summary["throughput_summary"]["dominant_completed_action"] is None
    assert summary["queue_delta_summary"]["finding_ack_queue_count"] == 2
    assert summary["queue_delta_summary"]["comment_intake_net_delta"] == 0
    assert summary["review_workflow_policy_summary"]["status"] == "breach"
    assert summary["review_workflow_policy_summary"]["go_no_go_flag"] == "hold"
