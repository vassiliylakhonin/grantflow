from __future__ import annotations

import os
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from grantflow.core.config import config


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
    revision_instructions: str = Field(
        description="Clear, actionable instructions for follow-up revision."
    )


def _fallback_critic(state: Dict[str, Any], reason: str) -> RedTeamEvaluation:
    toc_ok = bool(state.get("toc_draft"))
    mel_ok = bool(state.get("logframe_draft") or state.get("mel"))
    score = 8.5 if toc_ok and mel_ok else 5.5
    flaws: List[str] = []
    if not toc_ok:
        flaws.append("Missing ToC draft")
    if not mel_ok:
        flaws.append("Missing MEL/Logframe draft")
    if not flaws:
        flaws.append("Minor improvements suggested")
    return RedTeamEvaluation(
        score=score,
        fatal_flaws=flaws,
        revision_instructions=(
            f"Fallback critic used ({reason}). Tighten causal logic and make indicators more specific."
        ),
    )


def red_team_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates the drafted ToC and LogFrame and updates loop-control fields."""
    donor_strategy = state.get("donor_strategy") or state.get("strategy")
    if not donor_strategy:
        raise ValueError("Critical Error: DonorStrategy not found in state.")

    evaluation: RedTeamEvaluation
    llm_mode = bool(state.get("llm_mode", False))
    critic_engine = "fallback"

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
            critic_engine = f"llm:{config.llm.reasoning_model}"
        except Exception as exc:
            evaluation = _fallback_critic(state, f"LLM unavailable: {exc}")
    else:
        reason = "llm_mode=false" if not llm_mode else "OPENAI_API_KEY missing"
        evaluation = _fallback_critic(state, reason)

    iteration = int(state.get("iteration", state.get("iteration_count", 0)) or 0) + 1
    max_iters = int(state.get("max_iterations", 3) or 3)
    score = float(evaluation.score)
    threshold = float(getattr(config.graph, "critic_threshold", 8.0) or 8.0)

    notes = {
        "score": score,
        "fatal_flaws": evaluation.fatal_flaws,
        "revision_instructions": evaluation.revision_instructions,
        "engine": critic_engine,
    }

    state["quality_score"] = score
    state["critic_score"] = score
    state["critic_notes"] = notes

    history = list(state.get("critic_feedback_history") or [])
    history.append(
        f"Iteration {iteration}: score={score}; flaws={evaluation.fatal_flaws}; instructions={evaluation.revision_instructions}"
    )
    state["critic_feedback_history"] = history

    state["iteration"] = iteration
    state["iteration_count"] = iteration
    state["needs_revision"] = score < threshold and iteration < max_iters
    state["next_step"] = "architect" if state["needs_revision"] else "end"
    return state
