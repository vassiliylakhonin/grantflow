# grantflow/core/config.py

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel


def _env(name: str, default: str) -> str:
    legacy = name.replace("GRANTFLOW_", "AIDGRAPH_", 1) if name.startswith("GRANTFLOW_") else name
    return os.getenv(name, os.getenv(legacy, default))

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

class GrantFlowConfig(BaseModel):
    """Основная конфигурация GrantFlow."""
    llm: LLMConfig = LLMConfig()
    graph: GraphConfig = GraphConfig()
    rag: RAGConfig = RAGConfig()
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "GrantFlowConfig":
        """Загружает конфигурацию из переменных окружения."""
        return cls(
            llm=LLMConfig(
                cheap_model=_env("GRANTFLOW_CHEAP_MODEL", "gpt-4o-mini"),
                reasoning_model=_env("GRANTFLOW_REASONING_MODEL", "gpt-4o"),
                max_tokens=int(_env("GRANTFLOW_MAX_TOKENS", "4000")),
                temperature=float(_env("GRANTFLOW_TEMPERATURE", "0.7")),
            ),
            graph=GraphConfig(
                max_iterations=int(_env("GRANTFLOW_MAX_ITERATIONS", "3")),
                critic_threshold=float(_env("GRANTFLOW_CRITIC_THRESHOLD", "8.0")),
                hitl_enabled=_env("GRANTFLOW_HITL_ENABLED", "true").lower() == "true",
            ),
            rag=RAGConfig(
                chroma_persist_dir=_env("GRANTFLOW_CHROMA_DIR", "./chroma_db"),
                default_top_k=int(_env("GRANTFLOW_TOP_K", "5")),
            ),
            api_host=_env("GRANTFLOW_API_HOST", "0.0.0.0"),
            api_port=int(_env("GRANTFLOW_API_PORT", "8000")),
            debug=_env("GRANTFLOW_DEBUG", "false").lower() == "true",
        )

config = GrantFlowConfig.from_env()
