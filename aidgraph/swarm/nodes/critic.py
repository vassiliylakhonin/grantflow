from __future__ import annotations

from typing import Dict, Any, List

from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from aidgraph.core.state import AidGraphState


# 1. Pydantic-схема для жесткого контроля выхода LLM

class RedTeamEvaluation(BaseModel):
    """Structured evaluation from the Red Team Critic."""
    
    score: float = Field(
        description="A strict score from 0.0 to 10.0 based on donor compliance and logical soundness.",
        ge=0.0,
        le=10.0
    )
    
    fatal_flaws: List[str] = Field(
        description="List of critical logical gaps, missing indicators, or unrealistic assumptions."
    )
    
    revision_instructions: str = Field(
        description="Clear, actionable instructions for the Architect and MEL Specialist on how to fix the flaws."
    )


def red_team_critic(state: AidGraphState) -> Dict[str, Any]:
    """ Evaluates the drafted ToC and LogFrame against the specific donor's strict guidelines. """
    
    # 1. Достаем стратегию донора (usaid, eu, etc.) из State
    donor_strategy = state.get("donor_strategy")
    if not donor_strategy:
        raise ValueError("Critical Error: DonorStrategy not found in state.")
    
    # 2. Инициализируем дорогую/умную модель (Критик должен быть самым умным в рое)
    # В проде лучше брать имя модели из config.py
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    # 3. Привязываем Pydantic схему к модели
    evaluator_llm = llm.with_structured_output(RedTeamEvaluation)
    
    # 4. Формируем промпты
    system_prompt = donor_strategy.get_system_prompts().get("Red_Team_Critic")
    
    # Собираем черновики (что именно мы оцениваем)
    toc_data = state.get("toc_draft", {})
    logframe_data = state.get("logframe_draft", {})
    
    human_prompt = (
        "Evaluate the following grant proposal artifacts:\n\n"
        f"Theory of Change:\n{toc_data}\n\n"
        f"Logical Framework / Indicators:\n{logframe_data}\n\n"
        "Be ruthless. Output your evaluation strictly using the provided schema."
    )
    
    # 5. Вызываем LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    # LLM вернет не текст, а готовый Pydantic-объект!
    evaluation: RedTeamEvaluation = evaluator_llm.invoke(messages)
    
    # 6. Формируем фидбек для истории
    feedback_string = (
        f"Iteration {state.get('iteration_count', 0)} - Score: {evaluation.score}/10.0\n"
        f"Flaws: {', '.join(evaluation.fatal_flaws)}\n"
        f"Instructions: {evaluation.revision_instructions}"
    )
    
    # 7. Возвращаем обновления в LangGraph State
    return {
        "critic_score": evaluation.score,
        # Используем список, так как в state.py мы настроили Reducer (operator.add)
        "critic_feedback_history": [feedback_string],
        "iteration_count": state.get("iteration_count", 0) + 1
    }