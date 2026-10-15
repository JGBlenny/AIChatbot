"""unit：2026-10-15 業主選 A——舊知識庫零列已審 ⇒ `kb.search` 不給模型（門面照列）。

依據：正式機 `knowledge_base` 有效 926 列、已審 0 列；`kb.get` 只放行已審列，`kb.search` 列出的
每一筆模型都開不了，實測 `kb.search` 成功後 `kb.get` 連續失敗直到預算用完（`issues-after-golive-20261015.md`）。
"""
from __future__ import annotations

import pytest

from services.agent import mcp_facade as F
from services.agent.identity import Identity

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

_PM = Identity(vendor_id=4, target_user="property_manager", mode="b2b",
               role_id="20151", user_id="12291", api_key_id=1)


def _registry():
    return F.build_registry(F.FacadeDeps(get_db_pool=lambda: None, get_kb_pool=lambda: None,
                                         get_retriever=lambda: None, stage="M1"))


def _model_names(reg):
    return {t["function"]["name"] for t in reg.to_openai_tools(_PM, "M1")}


def _facade_names(reg):
    return {s["name"] for s in reg.specs_for(_PM, "M1", for_model=False)}


class _Conn:
    def __init__(self, value, exc=None):
        self.value, self.exc, self.sql = value, exc, None

    async def fetchval(self, sql, *args):
        self.sql = sql
        if self.exc:
            raise self.exc
        return self.value


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self):
                return pool.conn

            async def __aexit__(self, *a):
                return False
        return _Ctx()


async def test_zero_reviewed_rows_hides_kb_search_from_model_but_not_facade():
    reg = _registry()
    assert "kb__search" in _model_names(reg)                       # 正對照：預設模型看得到
    n = await F.gate_kb_search_on_reviewed_rows(reg, _Pool(_Conn(0)))
    assert n == 0
    assert "kb__search" not in _model_names(reg)
    assert "kb.search" in _facade_names(reg)                       # 門面（tools/list）照列
    assert "kb__get" in _model_names(reg)                          # kb.get（正本 outline:*）不受影響


async def test_reviewed_rows_present_keeps_kb_search_for_model():
    reg = _registry()
    assert await F.gate_kb_search_on_reviewed_rows(reg, _Pool(_Conn(3))) == 3
    assert "kb__search" in _model_names(reg)


async def test_count_query_failure_keeps_current_behaviour():
    reg = _registry()
    assert await F.gate_kb_search_on_reviewed_rows(reg, _Pool(_Conn(0, exc=RuntimeError("db down")))) is None
    assert "kb__search" in _model_names(reg)


async def test_count_query_uses_the_same_reviewed_column_as_kb_get():
    from services.agent.canon.review_state import COLUMN
    conn = _Conn(0)
    await F.gate_kb_search_on_reviewed_rows(_registry(), _Pool(conn))
    assert f"kb.{COLUMN} ~ $1" in conn.sql and "kb.is_active" in conn.sql
