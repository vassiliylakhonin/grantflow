from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from grantflow.core.config import config
from grantflow.swarm.critic_rules import CriticFatalFlaw, evaluate_rule_based_critic


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

    if llm_mode and os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=config.llm.reasoning_model, temperature=0.1)
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
        llm_reason = "llm_mode=false" if not llm_mode else "OPENAI_API_KEY missing"

    iteration = int(state.get("iteration", state.get("iteration_count", 0)) or 0) + 1
    max_iters = int(state.get("max_iterations", 3) or 3)
    llm_score = float(evaluation.score) if evaluation is not None else None
    score = min(rule_report.score, llm_score) if llm_score is not None else float(rule_report.score)
    threshold = float(getattr(config.graph, "critic_threshold", 8.0) or 8.0)

    fatal_flaw_items: List[Dict[str, Any]] = [_dump_model(item) for item in rule_report.fatal_flaws]
    if evaluation is not None:
        fatal_flaw_items.extend(_llm_flaws_to_structured(list(evaluation.fatal_flaws or [])))

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
