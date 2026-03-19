from __future__ import annotations

from fastapi import HTTPException

from grantflow.api.bid_no_bid import evaluate_bid_no_bid
from grantflow.api.diagnostics_service import _health_diagnostics
from grantflow.api.readiness_service import _build_readiness_payload
from grantflow.api.routers import system_router
from grantflow.api.schemas import BidNoBidRequest, BidNoBidResponse
from grantflow.core.version import __version__


@system_router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": __version__,
        "diagnostics": _health_diagnostics(),
    }


@system_router.get("/ready")
def readiness_check():
    payload = _build_readiness_payload()
    if str(payload.get("status") or "").strip().lower() != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@system_router.post("/decision/bid-no-bid", response_model=BidNoBidResponse)
def bid_no_bid_decision(payload: BidNoBidRequest):
    scores = {
        "strategic_fit": payload.strategic_fit,
        "win_probability": payload.win_probability,
        "budget_margin": payload.budget_margin,
        "delivery_capacity": payload.delivery_capacity,
        "compliance_readiness": payload.compliance_readiness,
        "partner_strength": payload.partner_strength,
        "timeline_realism": payload.timeline_realism,
        "evidence_strength": payload.evidence_strength,
    }

    invalid_fields = [key for key, value in scores.items() if int(value) < 0 or int(value) > 100]
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Scores must be between 0 and 100: {', '.join(invalid_fields)}")

    return evaluate_bid_no_bid(
        scores=scores,
        weight_overrides=payload.weight_overrides,
        mandatory_eligibility_gap=payload.mandatory_eligibility_gap,
        conflict_of_interest=payload.conflict_of_interest,
    )
