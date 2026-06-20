"""
Tests for the `branch_answer` internal endpoint (選項分歧知識回覆).

Covers:
1. Registry: 'branch_answer' is registered and maps to _handle_branch_answer
2. Happy path: choice → mapping → knowledge_base.answer
3. End-to-end through execute_api_call with {form.xxx} param resolution
4. Fallbacks: unknown choice, missing/inactive KB row, empty answer,
   None choice, no db_pool
5. Robustness: DB error never crashes, always returns a message
6. int() coercion when mapping value is a numeric string
"""

import pytest


# ---------------------------------------------------------------------------
# Fake async DB pool (mimics asyncpg Pool.acquire() async context manager)
# ---------------------------------------------------------------------------

class FakeConn:
    """Query-aware fake connection.

    execute_api_call first queries `api_endpoints` (endpoint config) via the
    same pool, then _handle_branch_answer queries `knowledge_base`. We route by
    query text so the two lookups don't collide, and expose only the
    knowledge_base lookups via `kb_calls` for assertions.
    """

    def __init__(self, row, raise_exc=None):
        self._row = row
        self._raise = raise_exc
        self.kb_calls = []  # (query, args) for knowledge_base lookups only

    async def fetchrow(self, query, *args):
        if "api_endpoints" in query:
            # branch_answer is custom-code, not a dynamic endpoint → None
            return None
        # knowledge_base lookup
        self.kb_calls.append((query, args))
        if self._raise:
            raise self._raise
        return self._row


class FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, row=None, raise_exc=None):
        self.conn = FakeConn(row, raise_exc)

    def acquire(self):
        return FakeAcquire(self.conn)


def make_handler(row=None, raise_exc=None, with_pool=True):
    from services.api_call_handler import APICallHandler
    pool = FakePool(row=row, raise_exc=raise_exc) if with_pool else None
    return APICallHandler(db_pool=pool)


DEFAULT_FALLBACK = '抱歉，這個選項目前沒有對應的說明，請聯繫客服協助。'
CUSTOM_FALLBACK = '這個選項目前沒有對應的說明，請聯繫客服協助。'
MAPPING = {"newebpay": 3551, "sinopac": 3553}


# ===========================================================================
# 1. Registry
# ===========================================================================

class TestRegistry:
    def test_branch_answer_registered(self):
        handler = make_handler()
        assert "branch_answer" in handler.api_registry

    def test_branch_answer_maps_to_handler(self):
        handler = make_handler()
        func = handler.api_registry["branch_answer"]
        assert callable(func)
        assert func.__name__ == "_handle_branch_answer"


# ===========================================================================
# 2. Happy path (direct call)
# ===========================================================================

class TestHappyPath:
    @pytest.mark.asyncio
    async def test_choice_returns_mapped_answer(self):
        handler = make_handler(row={"answer": "藍新金流設定步驟：..."})
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": "藍新金流設定步驟：..."}

    @pytest.mark.asyncio
    async def test_correct_kb_id_queried(self):
        handler = make_handler(row={"answer": "ok"})
        await handler._handle_branch_answer(
            choice="sinopac", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        # sinopac → 3553 → query arg int(3553)
        _, args = handler.db_pool.conn.kb_calls[0]
        assert args == (3553,)

    @pytest.mark.asyncio
    async def test_choice_is_stripped(self):
        handler = make_handler(row={"answer": "ok"})
        result = await handler._handle_branch_answer(
            choice="  newebpay  ", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": "ok"}

    @pytest.mark.asyncio
    async def test_numeric_string_mapping_value_coerced(self):
        handler = make_handler(row={"answer": "ok"})
        await handler._handle_branch_answer(
            choice="newebpay", mapping={"newebpay": "3551"}, fallback=CUSTOM_FALLBACK
        )
        _, args = handler.db_pool.conn.kb_calls[0]
        assert args == (3551,)  # int("3551")


# ===========================================================================
# 3. End-to-end through execute_api_call ({form.xxx} resolution)
# ===========================================================================

class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_execute_api_call_resolves_form_choice(self):
        handler = make_handler(row={"answer": "永豐金流設定：..."})
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "branch_answer",
                "combine_with_knowledge": False,
                "params": {
                    "choice": "{form.gateway}",
                    "mapping": MAPPING,
                    "fallback": CUSTOM_FALLBACK,
                },
            },
            form_data={"gateway": "sinopac"},
        )
        assert result["success"] is True
        assert result["formatted_response"] == "永豐金流設定：..."
        _, args = handler.db_pool.conn.kb_calls[0]
        assert args == (3553,)

    @pytest.mark.asyncio
    async def test_execute_api_call_empty_form_field_falls_back(self):
        # gateway not provided → choice resolves to None → fallback
        handler = make_handler(row={"answer": "should-not-appear"})
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "branch_answer",
                "combine_with_knowledge": False,
                "params": {
                    "choice": "{form.gateway}",
                    "mapping": MAPPING,
                    "fallback": CUSTOM_FALLBACK,
                },
            },
            form_data={},
        )
        assert result["success"] is True
        assert result["formatted_response"] == CUSTOM_FALLBACK
        # no DB query happened (choice was None)
        assert handler.db_pool.conn.kb_calls == []


# ===========================================================================
# 4. Fallbacks
# ===========================================================================

class TestFallbacks:
    @pytest.mark.asyncio
    async def test_unknown_choice_uses_custom_fallback(self):
        handler = make_handler(row={"answer": "x"})
        result = await handler._handle_branch_answer(
            choice="stripe", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}
        assert handler.db_pool.conn.kb_calls == []  # no lookup attempted

    @pytest.mark.asyncio
    async def test_missing_or_inactive_row_uses_fallback(self):
        handler = make_handler(row=None)  # WHERE id=.. AND is_active matched nothing
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}

    @pytest.mark.asyncio
    async def test_empty_answer_uses_fallback(self):
        handler = make_handler(row={"answer": ""})
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}

    @pytest.mark.asyncio
    async def test_none_choice_uses_fallback(self):
        handler = make_handler(row={"answer": "x"})
        result = await handler._handle_branch_answer(
            choice=None, mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}

    @pytest.mark.asyncio
    async def test_no_fallback_uses_default(self):
        handler = make_handler(row=None)
        result = await handler._handle_branch_answer(
            choice="stripe", mapping=MAPPING, fallback=None
        )
        assert result == {"message": DEFAULT_FALLBACK}

    @pytest.mark.asyncio
    async def test_no_db_pool_uses_fallback(self):
        handler = make_handler(with_pool=False)
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}


# ===========================================================================
# 5. Robustness
# ===========================================================================

class TestRobustness:
    @pytest.mark.asyncio
    async def test_db_error_never_crashes(self):
        handler = make_handler(raise_exc=RuntimeError("connection lost"))
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=MAPPING, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}

    @pytest.mark.asyncio
    async def test_empty_mapping_uses_fallback(self):
        handler = make_handler(row={"answer": "x"})
        result = await handler._handle_branch_answer(
            choice="newebpay", mapping=None, fallback=CUSTOM_FALLBACK
        )
        assert result == {"message": CUSTOM_FALLBACK}
