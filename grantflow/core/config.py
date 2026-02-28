# grantflow/core/config.py

from __future__ import annotations

import os

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
    grounding_gate_mode: str = "warn"
    preflight_grounding_policy_mode: str = "warn"
    grounding_min_citations_for_calibration: int = 5
    grounding_max_weak_rag_or_fallback_ratio: float = 0.6
    grounding_max_low_confidence_ratio: float = 0.75
    mel_grounding_policy_mode: str = "warn"
    mel_grounding_min_mel_citations: int = 2
    mel_grounding_min_claim_support_rate: float = 0.5
    export_grounding_policy_mode: str = "warn"
    export_grounding_min_architect_citations: int = 3
    export_grounding_min_claim_support_rate: float = 0.5
    preflight_grounding_high_risk_coverage_threshold: float = 0.5
    preflight_grounding_medium_risk_coverage_threshold: float = 0.8
    preflight_grounding_min_uploads: int = 3


class RAGConfig(BaseModel):
    """Конфигурация RAG."""

    chroma_persist_dir: str = "./chroma_db"
    default_top_k: int = 5
    architect_top_k: int = 3
    architect_rerank_pool_size: int = 12
    architect_query_variants: int = 3
    architect_min_hit_confidence: float = 0.25
    mel_top_k: int = 3
    mel_rerank_pool_size: int = 12
    mel_query_variants: int = 3
    mel_min_hit_confidence: float = 0.3
    mel_citation_high_confidence_threshold: float = 0.33
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
        grounding_gate_mode = _env("GRANTFLOW_GROUNDING_GATE_MODE", "warn")
        preflight_grounding_policy_mode = _env("GRANTFLOW_PREFLIGHT_GROUNDING_POLICY_MODE", grounding_gate_mode)
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
                grounding_gate_mode=grounding_gate_mode,
                preflight_grounding_policy_mode=preflight_grounding_policy_mode,
                grounding_min_citations_for_calibration=int(
                    _env("GRANTFLOW_GROUNDING_MIN_CITATIONS_FOR_CALIBRATION", "5")
                ),
                grounding_max_weak_rag_or_fallback_ratio=float(
                    _env("GRANTFLOW_GROUNDING_MAX_WEAK_RAG_OR_FALLBACK_RATIO", "0.6")
                ),
                grounding_max_low_confidence_ratio=float(_env("GRANTFLOW_GROUNDING_MAX_LOW_CONFIDENCE_RATIO", "0.75")),
                mel_grounding_policy_mode=_env("GRANTFLOW_MEL_GROUNDING_POLICY_MODE", "warn"),
                mel_grounding_min_mel_citations=int(_env("GRANTFLOW_MEL_GROUNDING_MIN_MEL_CITATIONS", "2")),
                mel_grounding_min_claim_support_rate=float(
                    _env("GRANTFLOW_MEL_GROUNDING_MIN_CLAIM_SUPPORT_RATE", "0.5")
                ),
                export_grounding_policy_mode=_env("GRANTFLOW_EXPORT_GROUNDING_POLICY_MODE", "warn"),
                export_grounding_min_architect_citations=int(
                    _env("GRANTFLOW_EXPORT_GROUNDING_MIN_ARCHITECT_CITATIONS", "3")
                ),
                export_grounding_min_claim_support_rate=float(
                    _env("GRANTFLOW_EXPORT_GROUNDING_MIN_CLAIM_SUPPORT_RATE", "0.5")
                ),
                preflight_grounding_high_risk_coverage_threshold=float(
                    _env("GRANTFLOW_PREFLIGHT_GROUNDING_HIGH_RISK_COVERAGE_THRESHOLD", "0.5")
                ),
                preflight_grounding_medium_risk_coverage_threshold=float(
                    _env("GRANTFLOW_PREFLIGHT_GROUNDING_MEDIUM_RISK_COVERAGE_THRESHOLD", "0.8")
                ),
                preflight_grounding_min_uploads=int(_env("GRANTFLOW_PREFLIGHT_GROUNDING_MIN_UPLOADS", "3")),
            ),
            rag=RAGConfig(
                chroma_persist_dir=_env("GRANTFLOW_CHROMA_DIR", "./chroma_db"),
                default_top_k=int(_env("GRANTFLOW_TOP_K", "5")),
                architect_top_k=int(_env("GRANTFLOW_ARCHITECT_TOP_K", "3")),
                architect_rerank_pool_size=int(_env("GRANTFLOW_ARCHITECT_RERANK_POOL_SIZE", "12")),
                architect_query_variants=int(_env("GRANTFLOW_ARCHITECT_QUERY_VARIANTS", "3")),
                architect_min_hit_confidence=float(_env("GRANTFLOW_ARCHITECT_MIN_HIT_CONFIDENCE", "0.25")),
                mel_top_k=int(_env("GRANTFLOW_MEL_TOP_K", "3")),
                mel_rerank_pool_size=int(_env("GRANTFLOW_MEL_RERANK_POOL_SIZE", "12")),
                mel_query_variants=int(_env("GRANTFLOW_MEL_QUERY_VARIANTS", "3")),
                mel_min_hit_confidence=float(_env("GRANTFLOW_MEL_MIN_HIT_CONFIDENCE", "0.3")),
                mel_citation_high_confidence_threshold=float(
                    _env("GRANTFLOW_MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD", "0.33")
                ),
            ),
            api_host=_env("GRANTFLOW_API_HOST", "0.0.0.0"),
            api_port=int(_env("GRANTFLOW_API_PORT", "8000")),
            debug=_env("GRANTFLOW_DEBUG", "false").lower() == "true",
        )


config = GrantFlowConfig.from_env()
