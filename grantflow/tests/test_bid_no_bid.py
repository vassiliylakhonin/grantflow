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

    decision_response = client.post(f"/status/{job_id}/decision/bid-no-bid", json=_base_payload())
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
