from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from grantflow.core.config import config
from grantflow.swarm.llm_provider import (
    chat_openai_init_kwargs,
    openai_compatible_llm_available,
    openai_compatible_missing_reason,
)
from grantflow.swarm.critic_rules import CriticFatalFlaw, evaluate_rule_based_critic

WEAK_GROUNDING_LLM_SCORE_MAX_PENALTY = 1.5
WEAK_GROUNDING_MIN_CITATIONS_FOR_CALIBRATION = 5
WEAK_GROUNDING_LOW_CONFIDENCE_RATIO_THRESHOLD = 0.75
WEAK_GROUNDING_FALLBACK_RATIO_THRESHOLD = 0.6
ADVISORY_ONLY_LLM_SCORE_MAX_PENALTY = 0.75


class RedTeamEvaluation(BaseModel):
    """Structured evaluation from the Red Team Critic."""

    score: float = Field(
        description="A strict score from 0.0 to 10.0 based on donor compliance and logical soundness.",
        ge=0.0,
        le=10.0,
    )
    fatal_flaws: List[str] = Field(
        description="List of critical logical gaps, missing indicators, or unrealistic assumptions."
    )
    revision_instructions: str = Field(description="Clear, actionable instructions for follow-up revision.")


def _dump_model(model: BaseModel) -> Dict[str, Any]:
    dumper = getattr(model, "model_dump", None)
    if callable(dumper):
        return dumper()
    return model.dict()  # type: ignore[attr-defined]


def _llm_flaws_to_structured(flaws: List[str]) -> List[Dict[str, Any]]:
    structured: List[Dict[str, Any]] = []
    for idx, text in enumerate(flaws or []):
        msg = str(text or "").strip()
        if not msg:
            continue
        section = "general"
        lowered = msg.lower()
        if any(k in lowered for k in ("indicator", "mel", "logframe")):
            section = "logframe"
        elif any(k in lowered for k in ("toc", "objective", "assumption", "causal")):
            section = "toc"
        structured.append(
            _dump_model(
                CriticFatalFlaw(
                    code=f"LLM_REVIEW_FLAG_{idx+1}",
                    severity="medium",
                    section=section,
                    version_id=None,
                    message=msg,
                    fix_hint="Incorporate this reviewer feedback in the next draft iteration.",
                    source="llm",
                )
            )
        )
    return structured


def _is_advisory_llm_message(msg: str) -> bool:
    lowered = str(msg or "").lower()
    advisory_signals = (
        ("baseline" in lowered and "target" in lowered and "indicator" in lowered),
        ("evidence excerpt" in lowered and "indicator" in lowered),
        ("objective" in lowered and ("specific" in lowered or "measurable" in lowered)),
        (
            ("weak causal link" in lowered or "weak causal links" in lowered)
            and ("output" in lowered or "outputs" in lowered)
            and ("ir" in lowered or "intermediate result" in lowered)
        ),
        (
            "unrealistic assumption" in lowered
            and ("motivated to participate" in lowered or "motivation" in lowered)
        ),
        (
            "missing cross-cutting" in lowered
            or ("cross-cutting" in lowered and "lacks a detailed plan" in lowered)
        ),
    )
    return any(advisory_signals)


def _advisory_llm_findings_context(
    *,
    state: Dict[str, Any],
    rule_report: Any,
    llm_fatal_flaw_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    llm_items = [f for f in llm_fatal_flaw_items if isinstance(f, dict)]
    if not llm_items:
        return {"applies": False, "reason": "no_llm_findings"}

    rule_fatal_flaws = list(getattr(rule_report, "fatal_flaws", []) or [])
    rule_checks = list(getattr(rule_report, "checks", []) or [])
    failed_rule_checks = [c for c in rule_checks if str(getattr(c, "status", "")).lower() == "fail"]
    if rule_fatal_flaws or failed_rule_checks:
        return {"applies": False, "reason": "rule_critic_has_failures"}

    if any(not _is_advisory_llm_message(str(item.get("message") or "")) for item in llm_items):
        return {"applies": False, "reason": "non_advisory_llm_finding_present"}

    grounding = _citation_grounding_context(state)
    architect_citations = [
        c for c in (state.get("citations") or []) if isinstance(c, dict) and str(c.get("stage") or "") == "architect"
    ]
    architect_count = len(architect_citations)
    architect_support = sum(1 for c in architect_citations if str(c.get("citation_type") or "") == "rag_claim_support")
    architect_rag_low = sum(
        1 for c in architect_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
    )
    architect_fallback = sum(
        1 for c in architect_citations if str(c.get("citation_type") or "") == "fallback_namespace"
    )
    threshold_hit_rate = round(architect_support / architect_count, 4) if architect_count else None

    if architect_count == 0:
        return {"applies": False, "reason": "no_architect_citations"}
    if architect_rag_low > 0 or architect_fallback > 0:
        return {"applies": False, "reason": "architect_grounding_not_strong"}
    if threshold_hit_rate is None or threshold_hit_rate < 0.8:
        return {"applies": False, "reason": "threshold_hit_rate_below_min", "threshold_hit_rate": threshold_hit_rate}

    return {
        "applies": True,
        "reason": "advisory_only_llm_findings_with_strong_architect_grounding",
        "architect_citation_count": architect_count,
        "architect_threshold_hit_rate": threshold_hit_rate,
        "grounding_context": grounding,
    }


def _downgrade_advisory_llm_findings(
    llm_fatal_flaw_items: List[Dict[str, Any]],
    *,
    advisory_ctx: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not advisory_ctx.get("applies"):
        return llm_fatal_flaw_items, None

    changed = 0
    out: List[Dict[str, Any]] = []
    for item in llm_fatal_flaw_items:
        current = dict(item)
        if _is_advisory_llm_message(str(current.get("message") or "")):
            if str(current.get("severity") or "").lower() != "low":
                current["severity"] = "low"
                changed += 1
        out.append(current)
    return out, {
        "applied": True,
        "reason": str(advisory_ctx.get("reason") or ""),
        "downgraded_count": changed,
        "architect_threshold_hit_rate": advisory_ctx.get("architect_threshold_hit_rate"),
    }


def _apply_advisory_llm_score_cap(
    *,
    combined_score: float,
    rule_score: float,
    llm_score: Optional[float],
    advisory_ctx: Dict[str, Any],
) -> tuple[float, Optional[Dict[str, Any]]]:
    if llm_score is None or not advisory_ctx.get("applies"):
        return round(float(combined_score), 2), None
    if float(llm_score) >= float(rule_score):
        return round(float(combined_score), 2), None

    min_allowed = float(rule_score) - ADVISORY_ONLY_LLM_SCORE_MAX_PENALTY
    adjusted = max(float(combined_score), min_allowed)
    if adjusted <= float(combined_score):
        return round(float(combined_score), 2), None
    return round(adjusted, 2), {
        "applied": True,
        "reason": "advisory_only_llm_findings_caps_penalty",
        "rule_score": round(float(rule_score), 2),
        "raw_llm_score": round(float(llm_score), 2),
        "combined_score_before": round(float(combined_score), 2),
        "combined_score_after": round(adjusted, 2),
        "max_llm_penalty": ADVISORY_ONLY_LLM_SCORE_MAX_PENALTY,
        "advisory_context": advisory_ctx,
    }


def _finding_identity_key(item: Dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("code") or ""),
        str(item.get("section") or ""),
        str(item.get("version_id") or ""),
        str(item.get("message") or ""),
        str(item.get("source") or ""),
    )


def _normalize_fatal_flaw_items(
    items: List[Dict[str, Any]],
    previous_items: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    previous_by_key: Dict[tuple[str, str, str, str, str], Dict[str, Any]] = {}
    for old in previous_items or []:
        if not isinstance(old, dict):
            continue
        previous_by_key[_finding_identity_key(old)] = old

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        current = dict(item)
        prior = previous_by_key.get(_finding_identity_key(current))
        if prior:
            for key in ("finding_id", "status", "acknowledged_at", "resolved_at"):
                if prior.get(key) is not None and current.get(key) in (None, ""):
                    current[key] = prior.get(key)

        if not str(current.get("finding_id") or "").strip():
            current["finding_id"] = str(uuid.uuid4())

        status = str(current.get("status") or "open").strip().lower()
        if status not in {"open", "acknowledged", "resolved"}:
            status = "open"
        current["status"] = status
        if status != "acknowledged":
            current.pop("acknowledged_at", None)
        if status != "resolved":
            current.pop("resolved_at", None)
        normalized.append(current)
    return normalized


def _citation_grounding_context(state: Dict[str, Any]) -> Dict[str, Any]:
    citations = state.get("citations") if isinstance(state.get("citations"), list) else []
    citation_count = 0
    low_confidence_count = 0
    rag_low_confidence_count = 0
    fallback_namespace_count = 0
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        citation_count += 1
        citation_type = str(citation.get("citation_type") or "")
        if citation_type == "rag_low_confidence":
            rag_low_confidence_count += 1
        if citation_type == "fallback_namespace":
            fallback_namespace_count += 1
        confidence = citation.get("citation_confidence")
        try:
            conf_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            conf_value = None
        if conf_value is not None and conf_value < 0.3:
            low_confidence_count += 1

    raw_architect_retrieval = state.get("architect_retrieval")
    architect_retrieval = raw_architect_retrieval if isinstance(raw_architect_retrieval, dict) else {}
    retrieval_enabled = bool(architect_retrieval.get("enabled")) if architect_retrieval else False
    try:
        retrieval_hits_count = (
            int(architect_retrieval.get("hits_count")) if architect_retrieval.get("hits_count") is not None else None
        )
    except (TypeError, ValueError):
        retrieval_hits_count = None

    low_confidence_ratio = round(low_confidence_count / citation_count, 4) if citation_count else None
    weak_rag_or_fallback_count = rag_low_confidence_count + fallback_namespace_count
    weak_rag_or_fallback_ratio = round(weak_rag_or_fallback_count / citation_count, 4) if citation_count else None

    weak_grounding_reasons: list[str] = []
    if retrieval_enabled and retrieval_hits_count == 0:
        weak_grounding_reasons.append("architect_retrieval_no_hits")
    if (
        citation_count >= WEAK_GROUNDING_MIN_CITATIONS_FOR_CALIBRATION
        and weak_rag_or_fallback_ratio is not None
        and weak_rag_or_fallback_ratio >= WEAK_GROUNDING_FALLBACK_RATIO_THRESHOLD
    ):
        weak_grounding_reasons.append("fallback_or_low_rag_citations_dominate")
    if (
        citation_count >= WEAK_GROUNDING_MIN_CITATIONS_FOR_CALIBRATION
        and low_confidence_ratio is not None
        and low_confidence_ratio >= WEAK_GROUNDING_LOW_CONFIDENCE_RATIO_THRESHOLD
    ):
        weak_grounding_reasons.append("low_confidence_citations_dominate")

    return {
        "citation_count": citation_count,
        "low_confidence_citation_count": low_confidence_count,
        "rag_low_confidence_citation_count": rag_low_confidence_count,
        "fallback_namespace_citation_count": fallback_namespace_count,
        "low_confidence_ratio": low_confidence_ratio,
        "weak_rag_or_fallback_ratio": weak_rag_or_fallback_ratio,
        "architect_retrieval_enabled": retrieval_enabled,
        "architect_retrieval_hits_count": retrieval_hits_count,
        "weak_grounding": bool(weak_grounding_reasons),
        "weak_grounding_reasons": weak_grounding_reasons,
    }


def _combine_critic_scores(
    *,
    rule_score: float,
    llm_score: Optional[float],
    state: Dict[str, Any],
) -> tuple[float, Optional[Dict[str, Any]]]:
    if llm_score is None:
        return float(rule_score), None

    base_combined = min(float(rule_score), float(llm_score))
    grounding_context = _citation_grounding_context(state)
    if llm_score >= rule_score or not bool(grounding_context.get("weak_grounding")):
        return round(base_combined, 2), {
            "applied": False,
            "rule_score": round(float(rule_score), 2),
            "raw_llm_score": round(float(llm_score), 2),
            "combined_score": round(base_combined, 2),
            "reason": None if llm_score >= rule_score else "no_weak_grounding_context",
            "grounding_context": grounding_context,
        }

    capped_llm_score = max(float(llm_score), float(rule_score) - WEAK_GROUNDING_LLM_SCORE_MAX_PENALTY)
    combined = min(float(rule_score), capped_llm_score)
    return round(combined, 2), {
        "applied": True,
        "reason": "weak_grounding_caps_llm_penalty",
        "rule_score": round(float(rule_score), 2),
        "raw_llm_score": round(float(llm_score), 2),
        "calibrated_llm_score": round(capped_llm_score, 2),
        "combined_score": round(combined, 2),
        "max_llm_penalty": WEAK_GROUNDING_LLM_SCORE_MAX_PENALTY,
        "grounding_context": grounding_context,
    }


def red_team_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates the drafted ToC and LogFrame and updates loop-control fields."""
    donor_strategy = state.get("donor_strategy") or state.get("strategy")
    if not donor_strategy:
        raise ValueError("Critical Error: DonorStrategy not found in state.")

    evaluation: Optional[RedTeamEvaluation] = None
    llm_mode = bool(state.get("llm_mode", False))
    critic_engine = "rules"
    llm_reason: Optional[str] = None
    rule_report = evaluate_rule_based_critic(state)

    if llm_mode and openai_compatible_llm_available():
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            llm_kwargs = chat_openai_init_kwargs(model=config.llm.reasoning_model, temperature=0.1)
            if llm_kwargs is None:
                raise RuntimeError(openai_compatible_missing_reason())
            llm = ChatOpenAI(**llm_kwargs)
            evaluator_llm = llm.with_structured_output(RedTeamEvaluation)
            system_prompt = donor_strategy.get_system_prompts().get(
                "Red_Team_Critic", "Evaluate quality and compliance strictly."
            )
            human_prompt = (
                "Evaluate the following grant proposal artifacts:\n\n"
                f"Theory of Change:\n{state.get('toc_draft', {})}\n\n"
                f"Logical Framework / Indicators:\n{state.get('logframe_draft', {})}\n\n"
                "Be strict and return the structured schema only."
            )
            evaluation = evaluator_llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            )
            critic_engine = f"rules+llm:{config.llm.reasoning_model}"
        except Exception as exc:
            llm_reason = f"LLM unavailable: {exc}"
    else:
        llm_reason = "llm_mode=false" if not llm_mode else openai_compatible_missing_reason()

    iteration = int(state.get("iteration", state.get("iteration_count", 0)) or 0) + 1
    max_iters = int(state.get("max_iterations", 3) or 3)
    llm_score = float(evaluation.score) if evaluation is not None else None
    llm_fatal_flaw_items: List[Dict[str, Any]] = []
    if evaluation is not None:
        llm_fatal_flaw_items = _llm_flaws_to_structured(list(evaluation.fatal_flaws or []))
    advisory_ctx = _advisory_llm_findings_context(
        state=state,
        rule_report=rule_report,
        llm_fatal_flaw_items=llm_fatal_flaw_items,
    )
    llm_fatal_flaw_items, llm_advisory_normalization = _downgrade_advisory_llm_findings(
        llm_fatal_flaw_items,
        advisory_ctx=advisory_ctx,
    )

    score, llm_score_calibration = _combine_critic_scores(
        rule_score=float(rule_report.score),
        llm_score=llm_score,
        state=state,
    )
    score, llm_advisory_score_calibration = _apply_advisory_llm_score_cap(
        combined_score=score,
        rule_score=float(rule_report.score),
        llm_score=llm_score,
        advisory_ctx=advisory_ctx,
    )
    threshold = float(getattr(config.graph, "critic_threshold", 8.0) or 8.0)

    previous_notes = state.get("critic_notes") if isinstance(state.get("critic_notes"), dict) else {}
    previous_fatal_flaws = (
        [f for f in previous_notes.get("fatal_flaws", []) if isinstance(f, dict)]
        if isinstance(previous_notes, dict)
        else []
    )

    fatal_flaw_items: List[Dict[str, Any]] = [_dump_model(item) for item in rule_report.fatal_flaws]
    if llm_fatal_flaw_items:
        fatal_flaw_items.extend(llm_fatal_flaw_items)
    fatal_flaw_items = _normalize_fatal_flaw_items(fatal_flaw_items, previous_fatal_flaws)

    fatal_flaw_messages = [
        str(item.get("message") or "") for item in fatal_flaw_items if str(item.get("message") or "").strip()
    ]
    if not fatal_flaw_messages:
        fatal_flaw_messages = ["Minor improvements suggested"]

    revision_parts = [rule_report.revision_instructions]
    if evaluation is not None and str(evaluation.revision_instructions or "").strip():
        revision_parts.append(f"LLM reviewer notes: {evaluation.revision_instructions}")
    elif llm_reason and llm_mode:
        revision_parts.append(f"LLM critic fallback reason: {llm_reason}")
    revision_instructions = "\n\n".join([p for p in revision_parts if p])

    notes = {
        "score": score,
        "fatal_flaws": fatal_flaw_items,
        "fatal_flaw_messages": fatal_flaw_messages,
        "revision_instructions": revision_instructions,
        "rule_checks": [_dump_model(c) for c in rule_report.checks],
        "rule_score": float(rule_report.score),
        "llm_score": llm_score,
        "engine": critic_engine,
    }
    if llm_reason:
        notes["llm_reason"] = llm_reason
    if llm_score_calibration is not None:
        notes["llm_score_calibration"] = llm_score_calibration
    if llm_advisory_normalization is not None:
        notes["llm_advisory_normalization"] = llm_advisory_normalization
    if llm_advisory_score_calibration is not None:
        notes["llm_advisory_score_calibration"] = llm_advisory_score_calibration

    state["quality_score"] = score
    state["critic_score"] = score
    state["critic_notes"] = notes
    state["critic_fatal_flaws"] = fatal_flaw_items

    history = list(state.get("critic_feedback_history") or [])
    history.append(
        f"Iteration {iteration}: score={score}; flaws={fatal_flaw_messages}; instructions={revision_instructions}"
    )
    state["critic_feedback_history"] = history

    state["iteration"] = iteration
    state["iteration_count"] = iteration
    state["needs_revision"] = score < threshold and iteration < max_iters
    state["next_step"] = "architect" if state["needs_revision"] else "end"
    return state
