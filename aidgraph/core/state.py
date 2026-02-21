# aidgraph/core/state.py

from __future__ import annotations

from typing import TypedDict, Optional, Any, List

class AidGraphState(TypedDict):
    """Full LangGraph state for AidGraph."""
    donor_id: str
    input_context: dict
    toc_draft: Optional[dict]
    logframe_draft: Optional[dict]
    critic_score: Optional[float]
    critic_feedback: Optional[str]
    iteration_count: int
    max_iterations: int
    hitl_approval_toc: Optional[bool]
    hitl_approval_logframe: Optional[bool]
    final_output: Optional[dict]
    errors: List[str]
