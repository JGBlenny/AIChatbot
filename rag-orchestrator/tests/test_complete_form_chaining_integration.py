"""
Real-DB integration tests for _complete_form chaining (form-chaining task 4.2).
Feature: form-chaining
Task: 4.2 - 整合測試：串接觸發合併 answer + 旗標；建立後續 COLLECTING 會話且
            get_session_state 回傳後續會話；未設 next_form_id 的既有表單回傳與現況一致

需求：2.1, 2.3, 7.1

使用真實 DB（aichatbot-postgres）。聚焦串接整合與會話切換，
來源完成的 API 格式化以 show_knowledge 路徑避開 branch_answer 噪音（端到端見 6.1）。
"""

import os

# 同步 DB 層（form_manager.get_db_cursor）預設連 docker 網路名 'postgres'；
# 在 host 上跑整合測試需指向 localhost。須在匯入 form_manager 前設定。
os.environ.setdefault("DB_HOST", "localhost")

import sys

import asyncpg
import pytest
import pytest_asyncio

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "services"))
sys.path.insert(0, os.path.join(_HERE, ".."))

from form_manager import FormManager  # noqa: E402

SOURCE_FORM = "payment_gateway_select"
NEXT_FORM = "payment_gateway_followup"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


async def _cleanup(session_id: str):
    c = await asyncpg.connect(**_conn_kwargs())
    await c.execute(
        "DELETE FROM form_submissions WHERE form_session_id IN "
        "(SELECT id FROM form_sessions WHERE session_id = $1)",
        session_id,
    )
    await c.execute("DELETE FROM form_sessions WHERE session_id = $1", session_id)
    await c.close()


@pytest_asyncio.fixture
async def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_chain_creates_followup_session_and_switches(manager):
    session_id = "test-fc-42-chain"
    await _cleanup(session_id)
    try:
        # 1. 建立真實來源會話（payment_gateway_select 為平台通用，vendor_id=None）
        await manager.create_form_session(
            session_id=session_id, user_id="u-42", vendor_id=None, form_id=SOURCE_FORM
        )
        session_state = await manager.get_session_state(session_id)
        assert session_state["form_id"] == SOURCE_FORM

        # 2. 取真實表單定義（含 next_form_id）；以 show_knowledge 避開 branch_answer API
        form_schema = await manager.get_form_schema(SOURCE_FORM)
        assert form_schema["next_form_id"] == NEXT_FORM
        form_schema["on_complete_action"] = "show_knowledge"
        form_schema["api_config"] = None

        # 3. 完成來源表單 → 觸發串接
        result = await manager._complete_form(
            session_state, form_schema, {"gateway": "sinopac"}
        )

        # 旗標契約
        assert result["form_completed"] is False
        assert result["form_triggered"] is True
        assert result["form_id"] == NEXT_FORM
        assert result["current_field_type"] == "select"
        # 合併 answer：分隔線 + 後續第一欄提示
        assert "\n\n---\n\n" in result["answer"]
        assert "金流追問選單" in result["answer"]
        assert "1. 手續費誰負擔" in result["answer"]

        # 4. 會話切換：get_session_state 回傳後續 COLLECTING 會話
        switched = await manager.get_session_state(session_id)
        assert switched["form_id"] == NEXT_FORM
        assert switched["state"] == "COLLECTING"
        # 串接情境寫入後續會話 metadata
        meta = switched.get("metadata") or {}
        assert meta.get("chain_depth") == 1
        assert NEXT_FORM in (meta.get("chain_visited") or [])
        assert SOURCE_FORM in (meta.get("chain_visited") or [])
    finally:
        await _cleanup(session_id)


@pytest.mark.asyncio
async def test_source_row_preserved_after_chaining(manager):
    """Fix #1：串接後同一 session_id 有多列，後續更新只動最新列；
    來源 COMPLETED 列的 state/collected_data 不應被後續會話覆寫。"""
    session_id = "test-fc-42-srcrow"
    await _cleanup(session_id)
    try:
        await manager.create_form_session(
            session_id=session_id, user_id="u-42", vendor_id=None, form_id=SOURCE_FORM
        )
        session_state = await manager.get_session_state(session_id)
        form_schema = await manager.get_form_schema(SOURCE_FORM)
        form_schema["on_complete_action"] = "show_knowledge"
        form_schema["api_config"] = None

        # 完成來源 → 串接（來源列此時 COMPLETED、collected_data={gateway: sinopac}）
        await manager._complete_form(session_state, form_schema, {"gateway": "sinopac"})

        # 模擬後續會話的更新（推進/改 metadata）——應只動最新（後續）列
        await manager.update_session_state(
            session_id=session_id,
            collected_data={"followup_topic": "fee"},
            metadata={"chain_depth": 1},
        )

        # 直接查來源列：state 仍 COMPLETED、collected_data 仍為來源資料（未被覆寫）
        c = await asyncpg.connect(**_conn_kwargs())
        src = await c.fetchrow(
            "SELECT state, collected_data::text AS cd FROM form_sessions "
            "WHERE session_id=$1 AND form_id=$2",
            session_id, SOURCE_FORM,
        )
        await c.close()
        assert src is not None
        assert src["state"] == "COMPLETED", "來源列狀態不應被後續更新覆寫"
        assert '"gateway": "sinopac"' in src["cd"], "來源列 collected_data 不應被覆寫"
    finally:
        await _cleanup(session_id)


@pytest.mark.asyncio
async def test_no_next_form_id_completes_normally(manager):
    """向後相容：未設 next_form_id 的表單完成後回傳與現況一致，不建立後續會話。"""
    session_id = "test-fc-42-nochain"
    await _cleanup(session_id)
    try:
        await manager.create_form_session(
            session_id=session_id, user_id="u-42", vendor_id=None, form_id=SOURCE_FORM
        )
        session_state = await manager.get_session_state(session_id)

        form_schema = await manager.get_form_schema(SOURCE_FORM)
        # 模擬「未設定串接」的既有表單
        form_schema["next_form_id"] = None
        form_schema["on_complete_action"] = "show_knowledge"
        form_schema["api_config"] = None

        result = await manager._complete_form(
            session_state, form_schema, {"gateway": "sinopac"}
        )

        assert result["form_completed"] is True
        assert "form_triggered" not in result
        assert "next_form_id" not in result

        # 會話維持來源並標記 COMPLETED，未建立任何後續會話
        latest = await manager.get_session_state(session_id)
        assert latest["form_id"] == SOURCE_FORM
        assert latest["state"] == "COMPLETED"

        c = await asyncpg.connect(**_conn_kwargs())
        row_count = await c.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id = $1", session_id
        )
        await c.close()
        assert row_count == 1, "未串接不應建立額外會話列"
    finally:
        await _cleanup(session_id)
