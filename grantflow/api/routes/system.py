from __future__ import annotations

from fastapi import HTTPException

from grantflow.api.bid_no_bid import CRITERIA_ORDER, evaluate_bid_no_bid
from grantflow.api.diagnostics_service import _health_diagnostics
from grantflow.api.readiness_service import _build_readiness_payload
from grantflow.api.routers import system_router
from grantflow.api.schemas import (
    BidNoBidRequest,
    BidNoBidResponse,
    BidNoBidSimulationRequest,
    BidNoBidSimulationResponse,
)
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


def _extract_bid_no_bid_scores(payload: BidNoBidRequest) -> dict[str, int]:
    return {
        "strategic_fit": payload.strategic_fit,
        "win_probability": payload.win_probability,
        "budget_margin": payload.budget_margin,
        "delivery_capacity": payload.delivery_capacity,
        "compliance_readiness": payload.compliance_readiness,
        "partner_strength": payload.partner_strength,
        "timeline_realism": payload.timeline_realism,
        "evidence_strength": payload.evidence_strength,
    }


@system_router.post("/decision/bid-no-bid", response_model=BidNoBidResponse)
def bid_no_bid_decision(payload: BidNoBidRequest):
    scores = _extract_bid_no_bid_scores(payload)

    invalid_fields = [key for key, value in scores.items() if int(value) < 0 or int(value) > 100]
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Scores must be between 0 and 100: {', '.join(invalid_fields)}")

    return evaluate_bid_no_bid(
        scores=scores,
        donor_profile=payload.donor_profile,
        weight_overrides=payload.weight_overrides,
        mandatory_eligibility_gap=payload.mandatory_eligibility_gap,
        conflict_of_interest=payload.conflict_of_interest,
    )


@system_router.post("/decision/bid-no-bid/simulate", response_model=BidNoBidSimulationResponse)
def bid_no_bid_simulation(payload: BidNoBidSimulationRequest):
    scores = _extract_bid_no_bid_scores(payload)

    invalid_fields = [key for key, value in scores.items() if int(value) < 0 or int(value) > 100]
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Scores must be between 0 and 100: {', '.join(invalid_fields)}")

    step = int(payload.step)
    if step < 1 or step > 30:
        raise HTTPException(status_code=400, detail="step must be between 1 and 30")

    max_scenarios = int(payload.max_scenarios)
    if max_scenarios < 1 or max_scenarios > 8:
        raise HTTPException(status_code=400, detail="max_scenarios must be between 1 and 8")

    baseline = evaluate_bid_no_bid(
        scores=scores,
        donor_profile=payload.donor_profile,
        weight_overrides=payload.weight_overrides,
        mandatory_eligibility_gap=payload.mandatory_eligibility_gap,
        conflict_of_interest=payload.conflict_of_interest,
    )

    ranked: list[tuple[float, bool, dict[str, object]]] = []
    for criterion in CRITERIA_ORDER:
        current = int(scores.get(criterion, 0))
        if current >= 100:
            continue
        simulated_scores = dict(scores)
        simulated_scores[criterion] = min(100, current + step)
        simulated = evaluate_bid_no_bid(
            scores=simulated_scores,
            donor_profile=payload.donor_profile,
            weight_overrides=payload.weight_overrides,
            mandatory_eligibility_gap=payload.mandatory_eligibility_gap,
            conflict_of_interest=payload.conflict_of_interest,
        )
        delta = round(float(simulated["weighted_score"]) - float(baseline["weighted_score"]), 2)
        scenario = {
            "criterion": criterion,
            "from_score": current,
            "to_score": simulated_scores[criterion],
            "score_delta": delta,
            "verdict": simulated["verdict"],
            "projected_weighted_score": simulated["weighted_score"],
        }
        ranked.append((delta, str(simulated["verdict"]) == "BID", scenario))

    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    candidates = [row[2] for row in ranked]
    return {
        "baseline": baseline,
        "scenarios": candidates[:max_scenarios],
    }
