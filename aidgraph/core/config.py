# aidgraph/core/config.py

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel

class LLMConfig(BaseModel):
    """Конфигурация LLM моделей."""
    cheap_model: str = "gpt-4o-mini"
    reasoning_model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.7

class GraphConfig(BaseModel):
    """Конфигурация графа."""
    max_iterations: int = 3
    critic_threshold: float = 8.0
    hitl_enabled: bool = True

class RAGConfig(BaseModel):
    """Конфигурация RAG."""
    chroma_persist_dir: str = "./chroma_db"
    default_top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200

class AidGraphConfig(BaseModel):
    """Основная конфигурация AidGraph."""
    llm: LLMConfig = LLMConfig()
    graph: GraphConfig = GraphConfig()
    rag: RAGConfig = RAGConfig()
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "AidGraphConfig":
        """Загружает конфигурацию из переменных окружения."""
        return cls(
            llm=LLMConfig(
                cheap_model=os.getenv("AIDGRAPH_CHEAP_MODEL", "gpt-4o-mini"),
                reasoning_model=os.getenv("AIDGRAPH_REASONING_MODEL", "gpt-4o"),
                max_tokens=int(os.getenv("AIDGRAPH_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("AIDGRAPH_TEMPERATURE", "0.7")),
            ),
            graph=GraphConfig(
                max_iterations=int(os.getenv("AIDGRAPH_MAX_ITERATIONS", "3")),
                critic_threshold=float(os.getenv("AIDGRAPH_CRITIC_THRESHOLD", "8.0")),
                hitl_enabled=os.getenv("AIDGRAPH_HITL_ENABLED", "true").lower() == "true",
            ),
            rag=RAGConfig(
                chroma_persist_dir=os.getenv("AIDGRAPH_CHROMA_DIR", "./chroma_db"),
                default_top_k=int(os.getenv("AIDGRAPH_TOP_K", "5")),
            ),
            api_host=os.getenv("AIDGRAPH_API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("AIDGRAPH_API_PORT", "8000")),
            debug=os.getenv("AIDGRAPH_DEBUG", "false").lower() == "true",
        )

config = AidGraphConfig.from_env()
