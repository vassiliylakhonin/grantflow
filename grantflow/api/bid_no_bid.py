from __future__ import annotations

from typing import Any

DEFAULT_WEIGHTS: dict[str, float] = {
    "strategic_fit": 0.18,
    "win_probability": 0.18,
    "budget_margin": 0.12,
    "delivery_capacity": 0.14,
    "compliance_readiness": 0.14,
    "partner_strength": 0.08,
    "timeline_realism": 0.08,
    "evidence_strength": 0.08,
}

DONOR_WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "usaid": {
        "strategic_fit": 0.2,
        "win_probability": 0.16,
        "budget_margin": 0.1,
        "delivery_capacity": 0.14,
        "compliance_readiness": 0.18,
        "partner_strength": 0.06,
        "timeline_realism": 0.06,
        "evidence_strength": 0.1,
    },
    "eu": {
        "strategic_fit": 0.16,
        "win_probability": 0.16,
        "budget_margin": 0.12,
        "delivery_capacity": 0.14,
        "compliance_readiness": 0.14,
        "partner_strength": 0.1,
        "timeline_realism": 0.08,
        "evidence_strength": 0.1,
    },
    "un": {
        "strategic_fit": 0.17,
        "win_probability": 0.15,
        "budget_margin": 0.1,
        "delivery_capacity": 0.15,
        "compliance_readiness": 0.14,
        "partner_strength": 0.12,
        "timeline_realism": 0.07,
        "evidence_strength": 0.1,
    },
    "giz": {
        "strategic_fit": 0.18,
        "win_probability": 0.16,
        "budget_margin": 0.11,
        "delivery_capacity": 0.14,
        "compliance_readiness": 0.16,
        "partner_strength": 0.08,
        "timeline_realism": 0.07,
        "evidence_strength": 0.1,
    },
}

CRITERIA_ORDER: tuple[str, ...] = tuple(DEFAULT_WEIGHTS.keys())

RISK_HINTS: dict[str, str] = {
    "strategic_fit": "Clarify donor fit, priorities, and comparative advantage before bidding.",
    "win_probability": "Rebuild win strategy and competitor differentiation with concrete evidence.",
    "budget_margin": "Rework commercial model and scope to restore healthy margin.",
    "delivery_capacity": "Confirm staffing plan, surge capacity, and delivery ownership.",
    "compliance_readiness": "Close eligibility/compliance gaps and validate mandatory requirements.",
    "partner_strength": "Strengthen consortium roles and secure partner commitments.",
    "timeline_realism": "Rebaseline timeline and submission workplan with realistic milestones.",
    "evidence_strength": "Improve proof points, references, and measurable past-performance evidence.",
}


def _normalized_weights(
    weight_overrides: dict[str, float] | None,
    donor_profile: str | None = None,
) -> tuple[dict[str, float], str | None]:
    profile_key = str(donor_profile or "").strip().lower() or None
    preset = DONOR_WEIGHT_PRESETS.get(profile_key or "")

    if not weight_overrides:
        base = dict(preset or DEFAULT_WEIGHTS)
        total = sum(base.values())
        if total <= 0:
            return dict(DEFAULT_WEIGHTS), None
        return ({key: value / total for key, value in base.items()}, profile_key if preset else None)

    merged = dict(preset or DEFAULT_WEIGHTS)
    for key, value in weight_overrides.items():
        if key in merged and float(value) > 0:
            merged[key] = float(value)

    total = sum(merged.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS), None
    return ({key: value / total for key, value in merged.items()}, profile_key if preset else None)


def evaluate_bid_no_bid(
    *,
    scores: dict[str, int],
    weight_overrides: dict[str, float] | None = None,
    donor_profile: str | None = None,
    mandatory_eligibility_gap: bool = False,
    conflict_of_interest: bool = False,
) -> dict[str, Any]:
    weights, preset_profile = _normalized_weights(weight_overrides, donor_profile=donor_profile)

    weighted_score = 0.0
    for key in CRITERIA_ORDER:
        weighted_score += float(scores.get(key, 0)) * weights[key]

    hard_blockers: list[str] = []
    if mandatory_eligibility_gap:
        hard_blockers.append("mandatory_eligibility_gap")
    if conflict_of_interest:
        hard_blockers.append("conflict_of_interest")

    if scores.get("compliance_readiness", 0) < 40:
        hard_blockers.append("critical_compliance_readiness")
    if scores.get("delivery_capacity", 0) < 35:
        hard_blockers.append("critical_delivery_capacity")

    low_signals = sorted(
        ((key, int(scores.get(key, 0)), float(weights[key])) for key in CRITERIA_ORDER if int(scores.get(key, 0)) < 60),
        key=lambda row: (row[1], -row[2]),
    )

    must_fix_before_bid = []
    for criterion, current_score, _weight in low_signals[:3]:
        must_fix_before_bid.append(
            {
                "criterion": criterion,
                "current_score": current_score,
                "target_score": 70,
                "action": RISK_HINTS.get(criterion, "Raise this signal before bid commitment."),
            }
        )

    if hard_blockers:
        verdict = "NO_BID"
    elif weighted_score >= 70 and len(low_signals) <= 1:
        verdict = "BID"
    elif weighted_score >= 55:
        verdict = "CONDITIONAL_BID"
    else:
        verdict = "NO_BID"

    top_risks = [
        {
            "criterion": criterion,
            "score": score,
            "risk_level": "high" if score < 45 else "medium",
        }
        for criterion, score, _weight in low_signals[:3]
    ]

    return {
        "weighted_score": round(weighted_score, 2),
        "verdict": verdict,
        "hard_blockers": hard_blockers,
        "top_risks": top_risks,
        "must_fix_before_bid": must_fix_before_bid,
        "weights": {key: round(weights[key], 4) for key in CRITERIA_ORDER},
        "preset_profile": preset_profile,
    }
