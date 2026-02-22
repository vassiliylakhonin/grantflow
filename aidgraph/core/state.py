# aidgraph/core/state.py
from __future__ import annotations
from typing import TypedDict, Optional, Any, List, Annotated
import operator

class AidGraphState(TypedDict):
    """Full LangGraph state for AidGraph."""
    # 1. Базовые поля (Перезаписываются при каждом обновлении)
    donor_id: str
    input_context: dict
    # Словари с драфтами (Можно перезаписывать, так как они обновляются целиком)
    toc_draft: Optional[dict]
    logframe_draft: Optional[dict]
    final_output: Optional[dict]
    # Метрики и Флаги
    critic_score: Optional[float]
    iteration_count: int
    max_iterations: int
    hitl_approval_toc: Optional[bool]
    hitl_approval_logframe: Optional[bool]
    # 2. Аккумулируемые поля (Reducers) - Значения ДОБАВЛЯЮТСЯ, а не перезаписываются!
    # Теперь новые ошибки будут добавляться в конец списка: errors.extend(["новая ошибка"])
    errors: Annotated[List[str], operator.add]
    # Если мы хотим хранить историю фидбека за все итерации,
    # лучше сделать это списком строк, а не одной строкой:
    critic_feedback_history: Annotated[List[str], operator.add]
