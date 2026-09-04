"""unit：`kb.get`／`kb.search` 工具（spec agentic-mcp-orchestration 任務 1.4）。

假 pool（psycopg2 `getconn`／`putconn` 介面）與假 retriever，離線、不接觸真 DB。
"""
from unittest.mock import MagicMock

import pytest

from services.agent.identity import Identity
from services.agent.tools.kb import KB_GET_SPEC, KB_SEARCH_SPEC, kb_get, kb_search
from services.agent.tools.registry import ToolRegistry, ToolResult

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:1.4"


def _identity(target_user="tenant", *, mode="b2c", vendor_id=1, api_key_id=1):
    return Identity(vendor_id=vendor_id, target_user=target_user, mode=mode, api_key_id=api_key_id)


class _FakeCursor:
    def __init__(self, row):
        self._row = row
        self.executed = None

    def execute(self, sql, params):
        self.executed = (sql, params)

    def fetchone(self):
        return self._row

    def close(self):
        pass


class _FakeConn:
    def __init__(self, row):
        self.cursor_obj = _FakeCursor(row)

    def cursor(self):
        return self.cursor_obj


class _FakePool:
    """psycopg2 pool 介面（`getconn`／`putconn`），見 kb.py docstring 的硬約束。"""

    def __init__(self, row):
        self.conn = _FakeConn(row)
        self.put_calls = 0

    def getconn(self):
        return self.conn

    def putconn(self, conn):
        self.put_calls += 1
        assert conn is self.conn


# ---------------------------------------------------------------------------
# kb.get — 純數字命中
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
async def test_kb_get_numeric_hit_shape():
    pool = _FakePool((42, "怎麼繳費", "請至租客頁面點選繳費。"))
    result = await kb_get(_identity(), {"kb_id": "42"}, db_pool=pool)
    assert result.ok is True
    assert set(result.data.keys()) == {"id", "question_summary", "answer"}
    assert result.data == {
        "id": 42, "question_summary": "怎麼繳費", "answer": "請至租客頁面點選繳費。",
    }
    assert result.text_for_model == "請至租客頁面點選繳費。"
    assert len(result.provenance) == 1
    assert result.provenance[0].source == "kb:42"
    assert result.provenance[0].text == "請至租客頁面點選繳費。"
    assert result.provenance[0].citable is True
    assert pool.put_calls == 1, "getconn 後必須 putconn 歸還（⛔ 不得洩漏連線）"


@pytest.mark.req(_SPEC)
async def test_kb_get_numeric_hit_uses_visibility_predicate_params():
    """SQL 送出的參數必須是 `[id] + build_visibility_predicate(identity) 的參數`。"""
    pool = _FakePool((1, "q", "a"))
    identity = _identity(target_user="tenant", vendor_id=7)
    await kb_get(identity, {"kb_id": "1"}, db_pool=pool)
    sql, params = pool.conn.cursor_obj.executed
    assert "kb.id = %s" in sql
    assert params[0] == 1
    # 不變量 20 的間接驗證：這裡不重寫謂詞，只確認確實把 build_visibility_predicate
    # 的參數原樣接上（vendor_id 出現在其中一個參數）。
    assert any(p == [7] for p in params[1:] if isinstance(p, list))


@pytest.mark.req(_SPEC)
async def test_kb_get_no_match_and_out_of_pool_are_the_same_error():
    """查無（None）與池外（謂詞不合亦回 None）⇛ 同一個 NO_MATCH，⛔ 不區分。"""
    pool_missing = _FakePool(None)
    r1 = await kb_get(_identity(), {"kb_id": "999999"}, db_pool=pool_missing)
    assert r1.ok is False and r1.error == "NO_MATCH"

    pool_out_of_scope = _FakePool(None)  # 謂詞擋掉＝資料庫端也回 0 列
    r2 = await kb_get(_identity(target_user="tenant"), {"kb_id": "5"}, db_pool=pool_out_of_scope)
    assert r2.ok is False and r2.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_kb_get_non_numeric_non_outline_is_invalid_input():
    pool = _FakePool(None)
    for bad in ["abc", "12.5", "-5", "", "12abc"]:
        result = await kb_get(_identity(), {"kb_id": bad}, db_pool=pool)
        assert result.ok is False and result.error == "INVALID_INPUT", bad


@pytest.mark.req(_SPEC)
async def test_kb_get_non_string_kb_id_is_invalid_input():
    pool = _FakePool(None)
    result = await kb_get(_identity(), {"kb_id": 42}, db_pool=pool)
    assert result.ok is False and result.error == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# kb.get — outline:*
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
async def test_kb_get_outline_with_resolver_delegates():
    expected = ToolResult(ok=True, data={"section": "contract"}, text_for_model="大綱內容")

    async def resolver(identity, kb_id):
        assert kb_id == "outline:contract"
        return expected

    pool = _FakePool(None)
    result = await kb_get(_identity(), {"kb_id": "outline:contract"}, db_pool=pool, outline_resolver=resolver)
    assert result is expected


@pytest.mark.req(_SPEC)
async def test_kb_get_outline_sync_resolver_also_supported():
    expected = ToolResult(ok=True, data={"section": "contract"}, text_for_model="ok")

    def resolver(identity, kb_id):
        return expected

    pool = _FakePool(None)
    result = await kb_get(_identity(), {"kb_id": "outline:x"}, db_pool=pool, outline_resolver=resolver)
    assert result is expected


@pytest.mark.req(_SPEC)
async def test_kb_get_outline_without_resolver_is_no_match():
    pool = _FakePool(None)
    result = await kb_get(_identity(), {"kb_id": "outline:contract"}, db_pool=pool, outline_resolver=None)
    assert result.ok is False and result.error == "NO_MATCH"


# ---------------------------------------------------------------------------
# kb.search
# ---------------------------------------------------------------------------


class _FakeRetriever:
    def __init__(self, results=None, exc=None):
        self._results = results if results is not None else []
        self._exc = exc
        self.calls = []

    async def retrieve(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self._exc is not None:
            raise self._exc
        return self._results


@pytest.mark.req(_SPEC)
async def test_kb_search_calls_retrieve_with_expected_kwargs():
    retriever = _FakeRetriever(results=[{"id": 1, "question_summary": "怎麼繳費", "answer": "全文", "similarity": 0.9}])
    identity = _identity(target_user="tenant", mode="b2c", vendor_id=3)
    result = await kb_search(identity, {"query": "繳費", "k": 3}, retriever=retriever)
    assert result.ok is True
    query, kwargs = retriever.calls[0]
    assert query == "繳費"
    assert kwargs["vendor_id"] == 3
    assert kwargs["top_k"] == 3
    assert kwargs["target_user"] == "tenant"
    assert kwargs["mode"] == "b2c"
    assert "similarity_threshold" in kwargs


@pytest.mark.req(_SPEC)
async def test_kb_search_uses_decision_config_threshold_by_default(monkeypatch):
    from services import decision_layer

    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.42")
    retriever = _FakeRetriever(results=[{"id": 1, "question_summary": "q", "similarity": 0.5}])
    await kb_search(_identity(), {"query": "x", "k": 1}, retriever=retriever)
    _, kwargs = retriever.calls[0]
    assert kwargs["similarity_threshold"] == pytest.approx(
        decision_layer.DecisionConfig.load().kb_threshold
    )
    assert kwargs["similarity_threshold"] == pytest.approx(0.42)


@pytest.mark.req(_SPEC)
async def test_kb_search_explicit_threshold_overrides_default():
    retriever = _FakeRetriever(results=[{"id": 1, "question_summary": "q", "similarity": 0.5}])
    await kb_search(_identity(), {"query": "x", "k": 1}, retriever=retriever, threshold=0.99)
    _, kwargs = retriever.calls[0]
    assert kwargs["similarity_threshold"] == 0.99


@pytest.mark.req(_SPEC)
async def test_kb_search_k_boundaries():
    retriever = _FakeRetriever(results=[{"id": 1, "question_summary": "q", "similarity": 0.5}])
    for k in (1, 5):
        result = await kb_search(_identity(), {"query": "x", "k": k}, retriever=retriever)
        assert result.ok is True, k
    for k in (0, 6, -1):
        result = await kb_search(_identity(), {"query": "x", "k": k}, retriever=retriever)
        assert result.ok is False and result.error == "INVALID_INPUT", k


@pytest.mark.req(_SPEC)
async def test_kb_search_zero_hits_is_no_match():
    retriever = _FakeRetriever(results=[])
    result = await kb_search(_identity(), {"query": "查無此物", "k": 3}, retriever=retriever)
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_kb_search_retriever_exception_is_no_match_fail_closed():
    retriever = _FakeRetriever(exc=RuntimeError("池掛了"))
    result = await kb_search(_identity(), {"query": "x", "k": 3}, retriever=retriever)
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_kb_search_does_not_leak_answer_full_text():
    retriever = _FakeRetriever(
        results=[{"id": 1, "question_summary": "q", "answer": "⛔不該外洩的全文", "similarity": 0.9}]
    )
    result = await kb_search(_identity(), {"query": "x", "k": 1}, retriever=retriever)
    assert "answer" not in result.data["items"][0]
    assert "⛔不該外洩的全文" not in result.text_for_model
    assert all("⛔不該外洩的全文" not in p.text for p in result.provenance)
    for item in result.data["items"]:
        assert set(item.keys()) == {"id", "question_summary", "similarity"}


# ---------------------------------------------------------------------------
# ToolSpec 過 ToolRegistry.register（不變量 18）＋ prospect 可見性
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_specs_register_without_invariant_18_violation():
    async def _fn(identity, args):
        raise NotImplementedError

    reg = ToolRegistry()
    reg.register(KB_GET_SPEC, _fn)
    reg.register(KB_SEARCH_SPEC, _fn)


@pytest.mark.req(_SPEC)
def test_prospect_sees_kb_get_but_not_kb_search():
    async def _fn(identity, args):
        raise NotImplementedError

    reg = ToolRegistry()
    reg.register(KB_GET_SPEC, _fn)
    reg.register(KB_SEARCH_SPEC, _fn)

    prospect = _identity(target_user="prospect")
    visible = {s["name"] for s in reg.specs_for(prospect, "M0")}
    assert "kb.get" in visible
    assert "kb.search" not in visible

    tenant = _identity(target_user="tenant")
    visible_tenant = {s["name"] for s in reg.specs_for(tenant, "M0")}
    assert "kb.get" in visible_tenant
    assert "kb.search" in visible_tenant
