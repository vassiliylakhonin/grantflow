from __future__ import annotations

from grantflow.swarm import llm_provider


def test_openai_compatible_prefers_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    assert llm_provider.openai_compatible_api_key() == "openai-key"


def test_openai_compatible_uses_openrouter_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.delenv("GRANTFLOW_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    assert llm_provider.openai_compatible_api_key() == "openrouter-key"
    assert llm_provider.openai_compatible_base_url() == llm_provider.OPENROUTER_DEFAULT_BASE_URL

    kwargs = llm_provider.chat_openai_init_kwargs(model="gpt-4o-mini", temperature=0.1)
    assert kwargs is not None
    assert kwargs["api_key"] == "openrouter-key"
    assert kwargs["base_url"] == llm_provider.OPENROUTER_DEFAULT_BASE_URL


def test_openai_compatible_headers_support_generic_and_openrouter_env(monkeypatch):
    monkeypatch.delenv("GRANTFLOW_LLM_HTTP_REFERER", raising=False)
    monkeypatch.delenv("GRANTFLOW_LLM_APP_NAME", raising=False)
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://example.org")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "GrantFlow Test")

    headers = llm_provider.openai_compatible_default_headers()
    assert headers["HTTP-Referer"] == "https://example.org"
    assert headers["X-Title"] == "GrantFlow Test"

    monkeypatch.setenv("GRANTFLOW_LLM_HTTP_REFERER", "https://custom.example")
    monkeypatch.setenv("GRANTFLOW_LLM_APP_NAME", "GrantFlow Custom")
    headers_override = llm_provider.openai_compatible_default_headers()
    assert headers_override["HTTP-Referer"] == "https://custom.example"
    assert headers_override["X-Title"] == "GrantFlow Custom"


def test_chat_openai_init_kwargs_returns_none_without_any_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert llm_provider.chat_openai_init_kwargs(model="gpt-4o", temperature=0.2) is None
    assert llm_provider.openai_compatible_llm_available() is False
    assert "OPENROUTER_API_KEY" in llm_provider.openai_compatible_missing_reason()
