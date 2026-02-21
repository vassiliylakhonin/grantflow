# aidgraph/swarm/nodes/critic.py

from __future__ import annotations

from typing import Dict, Any
import random

def red_team_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Критическая оценка ToC и MEL.
    """
    # Заглушка — здесь будет LLM вызов для критики
    # В реальной версии: scoring на основе quality criteria
    score = random.uniform(7.0, 9.5)
    
    state["critic_score"] = score
    state["critic_feedback"] = f"Critic score: {score:.1f}/10.0"
    
    if score < 8.0:
        state["critic_feedback"] += " Needs revision."
    else:
        state["critic_feedback"] += " Approved."
    
    return state
