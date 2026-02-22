# Рёбра (Edges & Workflow)
graph.set_entry_point("discovery")
graph.add_edge("discovery", "architect")
graph.add_edge("architect", "mel_specialist")  # Архитектор всегда передает работу MEL
graph.add_edge("mel_specialist", "critic")  # MEL всегда отдает готовую сборку Критику

# Условный переход (Conditional Edge) - Решает только Критик
def check_critic_score(state: AidGraphState) -> Literal["architect", "end"]:
    score = state.get("critic_score", 0)
    iterations = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", 3)
    
    # Если всё отлично или лимит исчерпан - заканчиваем
    if score >= 8.0 or iterations >= max_iters:
        return "end"
    
    # Иначе возвращаем на полную переработку к Архитектору
    return "architect"

graph.add_conditional_edges(
    "critic", check_critic_score, {
        "architect": "architect",
        "end": END
    }
)