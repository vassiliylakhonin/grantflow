from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from grantflow.api.app import app
from grantflow.api.idempotency_store_facade import _set_job


def _fixture_payloads() -> dict[str, object]:
    fixture_path = Path(__file__).parent / "fixtures" / "bid_no_bid_e2e_payloads.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_e2e_bid_no_bid_job_decision_roundtrip() -> None:
    payloads = _fixture_payloads()
    decision_payload = payloads["job_decision_payload"]
    assert isinstance(decision_payload, dict)

    client = TestClient(app)
    job_id = "job-e2e-bid-no-bid-roundtrip"
    _set_job(
        job_id,
        {
            "status": "done",
            "state": {},
            "hitl_enabled": False,
            "donor_id": "eu",
            "tenant_id": "tenant_demo",
        },
    )

    decision_response = client.post(f"/status/{job_id}/decision/bid-no-bid", json=decision_payload)
    assert decision_response.status_code == 200
    decision = decision_response.json()
    assert decision["verdict"] in {"BID", "CONDITIONAL_BID", "NO_BID"}
    assert decision["preset_profile"] == "eu"

    quality_response = client.get(f"/status/{job_id}/quality")
    assert quality_response.status_code == 200
    quality_payload = quality_response.json()
    stored = quality_payload.get("bid_no_bid_decision")
    assert isinstance(stored, dict)
    assert stored.get("verdict") == decision.get("verdict")
    assert stored.get("inputs", {}).get("donor_profile") == "eu"

    trail_response = client.get(f"/status/{job_id}/decision/bid-no-bid/trail")
    assert trail_response.status_code == 200
    entries = trail_response.json().get("entries")
    assert isinstance(entries, list)
    assert entries
    assert entries[-1].get("reason") == "manual_update"


def test_e2e_quality_state_drift_auto_refreshes_decision() -> None:
    payloads = _fixture_payloads()
    base_scores = payloads["base_scores"]
    assert isinstance(base_scores, dict)

    client = TestClient(app)
    job_id = "job-e2e-bid-no-bid-quality-drift"
    _set_job(
        job_id,
        {
            "status": "done",
            "state": {
                "needs_revision": False,
                "critic_notes": {
                    "fatal_flaws": [
                        {
                            "finding_id": "f-1",
                            "status": "resolved",
                        }
                    ]
                },
                "bid_no_bid_decision": {
                    "weighted_score": 71.2,
                    "verdict": "BID",
                    "hard_blockers": [],
                    "top_risks": [],
                    "must_fix_before_bid": [],
                    "weights": {},
                    "inputs": {
                        "scores": base_scores,
                        "donor_profile": "eu",
                        "weight_overrides": None,
                        "mandatory_eligibility_gap": False,
                        "conflict_of_interest": False,
                    },
                    "freshness_signature": {
                        "open_critic_findings": 0,
                        "open_review_comments": 0,
                        "needs_revision": False,
                    },
                    "decision_stale": False,
                    "decision_updated_at": "2026-03-01T00:00:00+00:00",
                },
            },
            "review_comments": [{"comment_id": "c-1", "status": "open"}],
            "hitl_enabled": False,
            "donor_id": "eu",
            "tenant_id": "tenant_demo",
        },
    )

    quality_response = client.get(f"/status/{job_id}/quality")
    assert quality_response.status_code == 200
    decision = quality_response.json().get("bid_no_bid_decision")
    assert isinstance(decision, dict)
    freshness_signature = decision.get("freshness_signature")
    assert isinstance(freshness_signature, dict)
    assert freshness_signature.get("open_review_comments") == 1
    assert decision.get("decision_stale") is False

    trail_response = client.get(f"/status/{job_id}/decision/bid-no-bid/trail")
    assert trail_response.status_code == 200
    entries = trail_response.json().get("entries")
    assert isinstance(entries, list)
    assert entries[-1].get("reason") == "auto_refresh_quality_drift"


def test_e2e_invalid_donor_profile_rejected() -> None:
    payloads = _fixture_payloads()
    base_scores = payloads["base_scores"]
    assert isinstance(base_scores, dict)

    client = TestClient(app)
    response = client.post("/decision/bid-no-bid", json={**base_scores, "donor_profile": "invalid_donor"})
    assert response.status_code == 422


def test_e2e_malformed_what_if_payload_rejected() -> None:
    payloads = _fixture_payloads()
    simulation_payload = payloads["simulation_payload"]
    assert isinstance(simulation_payload, dict)

    malformed_payload = dict(simulation_payload)
    malformed_payload["step"] = "oops"

    client = TestClient(app)
    response = client.post("/decision/bid-no-bid/simulate", json=malformed_payload)
    assert response.status_code == 422
