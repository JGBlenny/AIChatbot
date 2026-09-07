"""unit：`OPENAI_TIMEOUT_S` 設了才覆寫 AsyncOpenAI timeout；未設維持 SDK 預設（探針 53：600 s 掛住 ×2）。"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:5.1")]


def _make(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    from services import llm_provider as lp
    cls = getattr(lp, "OpenAIProvider", None) or getattr(lp, "LLMProvider", None)
    assert cls is not None, "找不到 provider 類別——測試對象錯了"
    return cls()


def test_unset_keeps_sdk_default(monkeypatch):
    monkeypatch.delenv("OPENAI_TIMEOUT_S", raising=False)
    prov = _make(monkeypatch)
    from openai import DEFAULT_TIMEOUT
    assert prov.async_client.timeout == DEFAULT_TIMEOUT


def test_env_overrides_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_TIMEOUT_S", "60")
    prov = _make(monkeypatch)
    assert float(prov.async_client.timeout) == 60.0
