"""unit:query rewriter 改寫邏輯(mock LLM provider,測解析/排除原查詢/各 fallback)。

填補對話檢索真空:query rewriter 的「生成→解析」邏輯先前無測。
"""
from unittest.mock import MagicMock

import pytest

from services.query_rewriter import QueryRewriter

pytestmark = pytest.mark.unit


def _rw(content=None, raises=False):
    rw = QueryRewriter()
    rw.enabled = True
    rw.model = "test"
    rw.temperature = 0
    rw.max_tokens = 100
    prov = MagicMock()
    if raises:
        prov.chat_completion.side_effect = RuntimeError("boom")
    else:
        prov.chat_completion.return_value = {"content": content or ""}
    rw._provider = prov
    return rw


def test_disabled_returns_empty():
    rw = QueryRewriter()
    rw.enabled = False
    rw._provider = None
    assert rw.rewrite("怎麼繳房租") == []


def test_short_query_not_rewritten_and_no_llm_call():
    rw = _rw(content="一\n二")
    assert rw.rewrite("嗨") == []          # <3 字
    rw._provider.chat_completion.assert_not_called()


def test_parses_multiline_and_excludes_original():
    rw = _rw(content="怎麼繳租金\n租金繳納方式\n如何付房租")
    out = rw.rewrite("怎麼繳租金")
    assert "租金繳納方式" in out and "如何付房租" in out
    assert "怎麼繳租金" not in out          # 原查詢排除


def test_empty_content_returns_empty():
    assert _rw(content="   ").rewrite("怎麼繳房租") == []


def test_provider_error_falls_back_to_empty():
    assert _rw(raises=True).rewrite("怎麼繳房租") == []
