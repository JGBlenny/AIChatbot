"""
Cancel & off-topic handling on the chained followup menu (form-chaining task 6.2).
Feature: form-chaining
Task: 6.2 - 追問選單輸入「取消」→ 結束串接、不再自動觸發；離題/無對應沿用既有處理

需求：5.1, 5.2, 5.3（並對齊 4.2：無對應選項→fallback，不送檢索）

說明：追問選單為 select 欄位，依既有設計跳過離題偵測，故「取消」需有明確處理
（與第一欄提示「輸入取消結束填寫」一致）。無對應輸入則回 branch_answer fallback。
"""

import os

os.environ.setdefault("DB_HOST", "localhost")

import sys

import asyncpg
import pytest
import pytest_asyncio

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "services"))
sys.path.insert(0, os.path.join(_HERE, ".."))

from form_manager import FormManager  # noqa: E402

SOURCE = "payment_gateway_select"
NEXT = "payment_gateway_followup"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


async def _cleanup(session_id):
    c = await asyncpg.connect(**_conn_kwargs())
    await c.execute(
        "DELETE FROM form_submissions WHERE form_session_id IN "
        "(SELECT id FROM form_sessions WHERE session_id = $1)",
        session_id,
    )
    await c.execute("DELETE FROM form_sessions WHERE session_id = $1", session_id)
    await c.close()


async def _session_count(session_id, state=None):
    c = await asyncpg.connect(**_conn_kwargs())
    if state:
        n = await c.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND state=$2",
            session_id, state,
        )
    else:
        n = await c.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1", session_id
        )
    await c.close()
    return n


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    yield p
    await p.close()


@pytest_asyncio.fixture
async def manager(pool):
    return FormManager(db_pool=pool)


async def _chain_to_followup(manager, session_id):
    """建立來源會話並選永豐，串接到追問選單。"""
    await manager.create_form_session(
        session_id=session_id, user_id="u-62", vendor_id=None, form_id=SOURCE
    )
    r1 = await manager.collect_field_data("永豐", session_id, vendor_id=1)
    assert r1.get("form_id") == NEXT, "前置：應已串接到追問選單"


@pytest.mark.asyncio
async def test_cancel_on_followup_ends_chain(manager):
    """R5.1/R5.3：追問選單輸入「取消」→ 結束、會話 CANCELLED、不再自動觸發。"""
    session_id = "test-fc-62-cancel"
    await _cleanup(session_id)
    try:
        await _chain_to_followup(manager, session_id)

        r = await manager.collect_field_data("取消", session_id, vendor_id=1)
        assert r.get("form_cancelled") is True, f"應取消，實際：{r}"
        assert "取消" in r["answer"]
        # 不得觸發新表單
        assert r.get("form_triggered") is not True

        # 會話為 CANCELLED，且未殘留任何 COLLECTING 會話（R5.3：不再自動觸發）
        latest = await manager.get_session_state(session_id)
        assert latest["state"] == "CANCELLED"
        assert await _session_count(session_id, state="COLLECTING") == 0
    finally:
        await _cleanup(session_id)


@pytest.mark.asyncio
async def test_unmatched_input_returns_fallback_no_retrieval(manager):
    """R5.2/R4.2：無對應選項的輸入 → branch_answer fallback，不送檢索、不再串接。"""
    session_id = "test-fc-62-offtopic"
    await _cleanup(session_id)
    try:
        await _chain_to_followup(manager, session_id)

        r = await manager.collect_field_data("今天天氣如何", session_id, vendor_id=1)
        # 回追問選單設定的 fallback（不對應任何選項）
        assert "客服" in r["answer"], f"應回 fallback，實際：{r['answer'][:80]}"
        # 不應再串接出新表單（追問選單無 next_form_id）
        assert r.get("form_id") != NEXT or r.get("form_triggered") is not True
    finally:
        await _cleanup(session_id)
