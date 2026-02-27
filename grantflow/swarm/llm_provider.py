from __future__ import annotations

import os
from typing import Any, Optional

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def openai_compatible_api_key() -> Optional[str]:
    value = str(os.getenv("OPENAI_API_KEY") or "").strip()
    if value:
        return value
    value = str(os.getenv("OPENROUTER_API_KEY") or "").strip()
    return value or None


def openai_compatible_base_url() -> Optional[str]:
    for env_name in ("GRANTFLOW_LLM_BASE_URL", "OPENAI_BASE_URL", "OPENROUTER_BASE_URL"):
        value = str(os.getenv(env_name) or "").strip()
        if value:
            return value
    if str(os.getenv("OPENROUTER_API_KEY") or "").strip():
        return OPENROUTER_DEFAULT_BASE_URL
    return None


def openai_compatible_default_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    http_referer = str(
        os.getenv("GRANTFLOW_LLM_HTTP_REFERER")
        or os.getenv("OPENROUTER_HTTP_REFERER")
        or os.getenv("OPENROUTER_SITE_URL")
        or ""
    ).strip()
    x_title = str(
        os.getenv("GRANTFLOW_LLM_APP_NAME") or os.getenv("OPENROUTER_X_TITLE") or os.getenv("OPENROUTER_APP_NAME") or ""
    ).strip()
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if x_title:
        headers["X-Title"] = x_title
    return headers


def openai_compatible_llm_available() -> bool:
    return bool(openai_compatible_api_key())


def openai_compatible_missing_reason() -> str:
    return "OPENAI_API_KEY / OPENROUTER_API_KEY missing"


def chat_openai_init_kwargs(*, model: str, temperature: float) -> Optional[dict[str, Any]]:
    api_key = openai_compatible_api_key()
    if not api_key:
        return None
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
    }
    base_url = openai_compatible_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    headers = openai_compatible_default_headers()
    if headers:
        kwargs["default_headers"] = headers
    return kwargs
