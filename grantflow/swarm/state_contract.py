from __future__ import annotations

from typing import Any, Mapping, MutableMapping, TypedDict, cast


class GrantFlowState(TypedDict, total=False):
    donor_id: str
    donor: str
    tenant_id: str
    rag_namespace: str
    retrieval_namespace: str
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
    hitl_checkpoints: list[str]
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


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        token = value.strip()
        return [token] if token else []
    if isinstance(value, (list, tuple, set)):
        normalized: list[str] = []
        for item in value:
            token = str(item or "").strip()
            if token:
                normalized.append(token)
        return normalized
    return []


def state_donor_id(state: Mapping[str, Any], default: str = "") -> str:
    donor = str(state.get("donor_id") or state.get("donor") or "").strip().lower()
    return donor or default


def state_donor_strategy(state: Mapping[str, Any], default: Any = None) -> Any:
    strategy = state.get("donor_strategy")
    if strategy is not None:
        return strategy
    strategy = state.get("strategy")
    return strategy if strategy is not None else default


def set_state_donor_strategy(state: MutableMapping[str, Any], strategy: Any) -> None:
    if strategy is None:
        return
    state["donor_strategy"] = strategy
    # Legacy alias retained for compatibility with older payload consumers.
    state["strategy"] = strategy


def state_input_context(state: Mapping[str, Any]) -> dict[str, Any]:
    input_context = state.get("input_context")
    if isinstance(input_context, dict):
        return input_context
    legacy_input = state.get("input")
    if isinstance(legacy_input, dict):
        return legacy_input
    return {}


def state_rag_namespace(state: Mapping[str, Any], default: str = "") -> str:
    namespace = str(state.get("rag_namespace") or state.get("retrieval_namespace") or "").strip()
    return namespace or default


def state_iteration(state: Mapping[str, Any], default: int = 0) -> int:
    return _as_int(state.get("iteration_count"), default=_as_int(state.get("iteration"), default=default))


def normalize_state_contract(state: MutableMapping[str, Any]) -> GrantFlowState:
    donor_id = state_donor_id(state)
    if donor_id:
        state["donor_id"] = donor_id
        # Legacy alias retained for compatibility with older payload consumers.
        state["donor"] = donor_id

    input_context = state_input_context(state)
    state["input_context"] = input_context
    # Legacy alias retained for compatibility with older payload consumers.
    state["input"] = input_context

    set_state_donor_strategy(state, state_donor_strategy(state))

    tenant_id = str(state.get("tenant_id") or "").strip()
    if tenant_id:
        state["tenant_id"] = tenant_id

    rag_namespace = state_rag_namespace(state)
    if rag_namespace:
        state["rag_namespace"] = rag_namespace
        # Legacy alias retained for compatibility with older payload consumers.
        state["retrieval_namespace"] = rag_namespace

    iteration = state_iteration(state)
    state["iteration_count"] = iteration
    # Legacy alias retained for compatibility with older payload consumers.
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
    state["max_iterations"] = max(1, _as_int(state.get("max_iterations"), default=3))
    hitl_checkpoints = state.get("hitl_checkpoints")
    if isinstance(hitl_checkpoints, (list, tuple, set)):
        normalized_checkpoints: list[str] = []
        for item in hitl_checkpoints:
            token = str(item or "").strip().lower()
            if token:
                normalized_checkpoints.append(token)
        state["hitl_checkpoints"] = normalized_checkpoints
    elif isinstance(hitl_checkpoints, str):
        tokens = [part.strip().lower() for part in hitl_checkpoints.split(",") if part.strip()]
        state["hitl_checkpoints"] = tokens
    else:
        state["hitl_checkpoints"] = []

    critic_notes = state.get("critic_notes")
    state["critic_notes"] = critic_notes if isinstance(critic_notes, dict) else {}

    state["critic_feedback_history"] = _as_str_list(state.get("critic_feedback_history"))
    state["errors"] = _as_str_list(state.get("errors"))

    return cast(GrantFlowState, state)
