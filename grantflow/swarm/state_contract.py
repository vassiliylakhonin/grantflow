from __future__ import annotations

from typing import Any, Mapping, MutableMapping, TypedDict, cast


class GrantFlowState(TypedDict, total=False):
    donor_id: str
    donor: str
    donor_strategy: Any
    strategy: Any
    input_context: dict[str, Any]
    input: dict[str, Any]
    llm_mode: bool
    iteration: int
    iteration_count: int
    max_iterations: int
    quality_score: float
    critic_score: float
    needs_revision: bool
    critic_notes: dict[str, Any]
    critic_feedback_history: list[str]
    hitl_pending: bool
    errors: list[str]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def state_donor_id(state: Mapping[str, Any], default: str = "") -> str:
    donor = str(state.get("donor_id") or state.get("donor") or "").strip().lower()
    return donor or default


def state_input_context(state: Mapping[str, Any]) -> dict[str, Any]:
    input_context = state.get("input_context")
    if isinstance(input_context, dict):
        return input_context
    legacy_input = state.get("input")
    if isinstance(legacy_input, dict):
        return legacy_input
    return {}


def normalize_state_contract(state: MutableMapping[str, Any]) -> GrantFlowState:
    donor_id = state_donor_id(state)
    if donor_id:
        state["donor_id"] = donor_id
        state["donor"] = donor_id

    input_context = state_input_context(state)
    state["input_context"] = input_context
    state["input"] = input_context

    strategy = state.get("donor_strategy") or state.get("strategy")
    if strategy is not None:
        state["donor_strategy"] = strategy
        state["strategy"] = strategy

    iteration = _as_int(
        state.get("iteration_count"),
        default=_as_int(state.get("iteration"), default=0),
    )
    state["iteration_count"] = iteration
    state["iteration"] = iteration

    critic_score = _as_float(
        state.get("critic_score"),
        default=_as_float(state.get("quality_score"), default=0.0),
    )
    quality_score = _as_float(
        state.get("quality_score"),
        default=critic_score,
    )
    state["critic_score"] = critic_score
    state["quality_score"] = quality_score

    state["llm_mode"] = _as_bool(state.get("llm_mode"), default=False)
    state["needs_revision"] = _as_bool(state.get("needs_revision"), default=False)
    state["hitl_pending"] = _as_bool(state.get("hitl_pending"), default=False)

    critic_notes = state.get("critic_notes")
    state["critic_notes"] = critic_notes if isinstance(critic_notes, dict) else {}

    critic_feedback_history = state.get("critic_feedback_history")
    if not isinstance(critic_feedback_history, list):
        state["critic_feedback_history"] = []

    errors = state.get("errors")
    if not isinstance(errors, list):
        state["errors"] = []

    return cast(GrantFlowState, state)
