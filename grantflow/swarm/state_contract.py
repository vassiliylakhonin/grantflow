from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, MutableMapping, Optional, TypedDict, cast


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


def normalize_donor_token(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_input_context(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): inner for key, inner in value.items()}
    return {}


def normalize_rag_namespace(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    token = token.replace("\\", "/")
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"/+", "/", token)
    token = "/".join(part.strip("._-") for part in token.split("/") if part.strip("._-"))
    token = token.strip("/")
    return token.lower()


def state_donor_id(state: Mapping[str, Any], default: str = "") -> str:
    donor = normalize_donor_token(state.get("donor_id") or state.get("donor"))
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
    input_context = normalize_input_context(state.get("input_context"))
    if input_context:
        return input_context
    legacy_input = normalize_input_context(state.get("input"))
    if legacy_input:
        return legacy_input
    return {}


def state_rag_namespace(state: Mapping[str, Any], default: str = "") -> str:
    namespace = normalize_rag_namespace(state.get("rag_namespace") or state.get("retrieval_namespace"))
    return namespace or default


def state_iteration(state: Mapping[str, Any], default: int = 0) -> int:
    return _as_int(state.get("iteration_count"), default=_as_int(state.get("iteration"), default=default))


def set_state_iteration(state: MutableMapping[str, Any], iteration: Any) -> int:
    value = max(0, _as_int(iteration, default=0))
    state["iteration_count"] = value
    # Legacy alias retained for compatibility with older payload consumers.
    state["iteration"] = value
    return value


def state_llm_mode(state: Mapping[str, Any], default: bool = False) -> bool:
    return _as_bool(state.get("llm_mode"), default=default)


def state_max_iterations(state: Mapping[str, Any], default: int = 3) -> int:
    return max(1, _as_int(state.get("max_iterations"), default=default))


def state_revision_hint(state: Mapping[str, Any]) -> str:
    critic_notes = state.get("critic_notes")
    if isinstance(critic_notes, dict):
        return str(critic_notes.get("revision_instructions") or "")
    if isinstance(critic_notes, str):
        return critic_notes
    return ""


def normalized_state_copy(state: Any) -> GrantFlowState:
    raw = dict(state) if isinstance(state, Mapping) else {}
    return normalize_state_contract(raw)


def build_graph_state(
    *,
    donor_id: str,
    input_context: Optional[Mapping[str, Any]] = None,
    donor_strategy: Any = None,
    tenant_id: Optional[str] = None,
    rag_namespace: Optional[str] = None,
    llm_mode: bool = False,
    hitl_checkpoints: Optional[Iterable[str]] = None,
    max_iterations: int = 3,
    generate_preflight: Optional[Mapping[str, Any]] = None,
    strict_preflight: bool = False,
    extras: Optional[Mapping[str, Any]] = None,
) -> GrantFlowState:
    state: dict[str, Any] = {
        "donor_id": normalize_donor_token(donor_id),
        "input_context": normalize_input_context(input_context),
        "llm_mode": bool(llm_mode),
        "iteration_count": 0,
        "max_iterations": _as_int(max_iterations, default=3),
        "critic_score": 0.0,
        "quality_score": 0.0,
        "needs_revision": False,
        "critic_notes": {},
        "critic_feedback_history": [],
        "hitl_pending": False,
        "hitl_checkpoints": [str(token).strip() for token in (hitl_checkpoints or []) if str(token).strip()],
        "errors": [],
        "strict_preflight": bool(strict_preflight),
    }
    if donor_strategy is not None:
        set_state_donor_strategy(state, donor_strategy)
    normalized_tenant = str(tenant_id or "").strip()
    if normalized_tenant:
        state["tenant_id"] = normalized_tenant
    normalized_namespace = normalize_rag_namespace(rag_namespace)
    if normalized_namespace:
        state["rag_namespace"] = normalized_namespace
    if isinstance(generate_preflight, Mapping):
        state["generate_preflight"] = dict(generate_preflight)
    if isinstance(extras, Mapping):
        state.update(dict(extras))
    return normalize_state_contract(state)


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

    set_state_iteration(state, state_iteration(state))

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

    state["llm_mode"] = state_llm_mode(state, default=False)
    state["needs_revision"] = _as_bool(state.get("needs_revision"), default=False)
    state["hitl_pending"] = _as_bool(state.get("hitl_pending"), default=False)
    state["max_iterations"] = state_max_iterations(state, default=3)
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
