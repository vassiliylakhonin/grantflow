from __future__ import annotations

from fastapi.testclient import TestClient

from grantflow.api.app import app
from grantflow.api.idempotency_store_facade import _set_job


def _base_payload() -> dict[str, int]:
    return {
        "strategic_fit": 80,
        "win_probability": 75,
        "budget_margin": 70,
        "delivery_capacity": 78,
        "compliance_readiness": 82,
        "partner_strength": 68,
        "timeline_realism": 72,
        "evidence_strength": 74,
    }


def test_bid_no_bid_returns_bid_for_strong_profile() -> None:
    client = TestClient(app)
    response = client.post("/decision/bid-no-bid", json=_base_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "BID"
    assert payload["weighted_score"] >= 70
    assert payload["hard_blockers"] == []


def test_bid_no_bid_applies_donor_preset_when_requested() -> None:
    client = TestClient(app)
    response = client.post("/decision/bid-no-bid", json={**_base_payload(), "donor_profile": "usaid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["preset_profile"] == "usaid"
    assert payload["weights"]["compliance_readiness"] >= 0.17


def test_bid_no_bid_returns_conditional_bid_for_mid_profile() -> None:
    client = TestClient(app)
    request_payload = {
        **_base_payload(),
        "win_probability": 58,
        "budget_margin": 55,
        "partner_strength": 50,
        "evidence_strength": 52,
    }
    response = client.post("/decision/bid-no-bid", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "CONDITIONAL_BID"
    assert len(payload["must_fix_before_bid"]) >= 1


def test_bid_no_bid_returns_no_bid_on_hard_blocker() -> None:
    client = TestClient(app)
    request_payload = {
        **_base_payload(),
        "mandatory_eligibility_gap": True,
    }
    response = client.post("/decision/bid-no-bid", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "NO_BID"
    assert "mandatory_eligibility_gap" in payload["hard_blockers"]


def test_bid_no_bid_rejects_invalid_score_range() -> None:
    client = TestClient(app)
    request_payload = {
        **_base_payload(),
        "win_probability": 140,
    }
    response = client.post("/decision/bid-no-bid", json=request_payload)

    assert response.status_code == 400
    assert "Scores must be between 0 and 100" in str(response.json())


def test_bid_no_bid_simulation_returns_ranked_scenarios() -> None:
    client = TestClient(app)
    request_payload = {
        **_base_payload(),
        "step": 12,
        "max_scenarios": 3,
    }
    response = client.post("/decision/bid-no-bid/simulate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("baseline"), dict)
    assert isinstance(payload.get("scenarios"), list)
    assert len(payload["scenarios"]) <= 3
    if payload["scenarios"]:
        top = payload["scenarios"][0]
        assert "criterion" in top
        assert "score_delta" in top


def test_bid_no_bid_simulation_validates_step() -> None:
    client = TestClient(app)
    response = client.post("/decision/bid-no-bid/simulate", json={**_base_payload(), "step": 0})
    assert response.status_code == 400
    assert "step must be between 1 and 30" in str(response.json())


def test_job_scoped_bid_no_bid_persists_to_quality_payload() -> None:
    client = TestClient(app)
    job_id = "job-bid-no-bid-persist"
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

    decision_response = client.post(
        f"/status/{job_id}/decision/bid-no-bid",
        json={**_base_payload(), "donor_profile": "eu"},
    )
    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    assert decision_payload["verdict"] in {"BID", "CONDITIONAL_BID", "NO_BID"}

    quality_response = client.get(f"/status/{job_id}/quality")
    assert quality_response.status_code == 200
    quality_payload = quality_response.json()
    stored_decision = quality_payload.get("bid_no_bid_decision")
    assert isinstance(stored_decision, dict)
    assert stored_decision.get("verdict") == decision_payload.get("verdict")
    assert isinstance(stored_decision.get("inputs"), dict)
    assert stored_decision["inputs"].get("donor_profile") == "eu"
    assert stored_decision.get("decision_stale") is False
    assert isinstance(stored_decision.get("decision_updated_at"), str)

    trail_response = client.get(f"/status/{job_id}/decision/bid-no-bid/trail")
    assert trail_response.status_code == 200
    trail_payload = trail_response.json()
    assert isinstance(trail_payload.get("entries"), list)
    assert trail_payload["entries"]
    last = trail_payload["entries"][-1]
    assert last.get("reason") == "manual_update"
    assert last.get("actor") == "user"


def test_job_scoped_bid_no_bid_auto_refreshes_when_review_signal_changes() -> None:
    client = TestClient(app)
    job_id = "job-bid-no-bid-refresh"
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
                    "weighted_score": 72.0,
                    "verdict": "BID",
                    "hard_blockers": [],
                    "top_risks": [],
                    "must_fix_before_bid": [],
                    "weights": {},
                    "inputs": {
                        "scores": _base_payload(),
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
    payload = quality_response.json()
    decision = payload.get("bid_no_bid_decision")
    assert isinstance(decision, dict)
    assert decision.get("decision_stale") is False
    assert isinstance(decision.get("decision_updated_at"), str)
    sig = decision.get("freshness_signature")
    assert isinstance(sig, dict)
    assert sig.get("open_review_comments") == 1

    trail_response = client.get(f"/status/{job_id}/decision/bid-no-bid/trail")
    assert trail_response.status_code == 200
    entries = trail_response.json().get("entries")
    assert isinstance(entries, list)
    assert entries
    assert entries[-1].get("reason") == "auto_refresh_quality_drift"
    assert entries[-1].get("actor") == "system"
