"""
Real-DB integration tests for the three leaf-outlet types (option-routing task 4.1).
Feature: option-routing
Task: 4.1 - 葉出口三型分派驗證：
    - 知識答案：選項 answer_kb 經 branch_answer 回知識（不經檢索）
    - 動作表單：CTA（demo_form/trial_form）以選項 next_form_id 串接，目標表單 on_complete_action=call_api
    - 導向連結：URL 葉出口＝answer_kb 指向內含連結（/pricing）之知識，連結於 answer 呈現

需求：4.1, 4.2, 4.3, 4.4, 4.5

自帶 fixtures，使用真實 DB（aichatbot-postgres）。FormManager 帶 asyncpg pool 以支援 branch_answer。
"""

import json
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

INTRO_FORM = "test_or_leaf_intro"
CTA_FORM = "test_or_cta_demo"

# 知識答案（type 1）：精確內容，用於驗證「不經檢索、直取該知識」
KB_PLAN_MARK = "個人 20 戶方案：含收租對帳、合約、報修，模組齊全（測試）"
# 導向連結（type 3）：內含 /pricing markdown 連結
KB_PRICE_MARK = "方案分級與費用請參考 [線上方案與報價](/pricing)，可自助比較（測試）"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


async def _cleanup(conn, session_ids):
    for sid in session_ids:
        await conn.execute(
            "DELETE FROM form_submissions WHERE form_session_id IN "
            "(SELECT id FROM form_sessions WHERE session_id = $1)",
            sid,
        )
        await conn.execute("DELETE FROM form_sessions WHERE session_id = $1", sid)
    await conn.execute("DELETE FROM form_schemas WHERE form_id LIKE 'test_or_%'")
    await conn.execute(
        "DELETE FROM knowledge_base WHERE question_summary IN "
        "('方案說明(測試4.1)', '價格導連結(測試4.1)')"
    )


@pytest_asyncio.fixture
async def env():
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    conn = await asyncpg.connect(**_conn_kwargs())
    session_ids = ["test-or-41-knowledge", "test-or-41-cta", "test-or-41-url"]
    await _cleanup(conn, session_ids)

    # 知識答案（type 1）與導向連結（type 3）
    kb_plan = await conn.fetchval(
        "INSERT INTO knowledge_base (question_summary, answer, scope, is_active) "
        "VALUES ('方案說明(測試4.1)', $1, 'system_provider', TRUE) RETURNING id",
        KB_PLAN_MARK,
    )
    kb_price = await conn.fetchval(
        "INSERT INTO knowledge_base (question_summary, answer, scope, is_active) "
        "VALUES ('價格導連結(測試4.1)', $1, 'system_provider', TRUE) RETURNING id",
        KB_PRICE_MARK,
    )

    # 動作表單（type 2）：CTA demo_form，on_complete_action=call_api
    await conn.execute(
        """
        INSERT INTO form_schemas
            (form_id, form_name, fields, vendor_id, is_active, on_complete_action, api_config)
        VALUES ($1, '預約專人 demo（測試）', $2::jsonb, NULL, TRUE, 'call_api', $3::jsonb)
        """,
        CTA_FORM,
        json.dumps([
            {"field_name": "contact", "field_type": "text", "prompt": "方便聯絡的電話或 email？"}
        ]),
        json.dumps({"endpoint": "demo_form", "method": "POST", "url": "/api2/demo_form"}),
    )

    # 起手式（select）：三選項各對應一型葉出口
    await conn.execute(
        """
        INSERT INTO form_schemas
            (form_id, form_name, fields, vendor_id, is_active, on_complete_action, next_form_id)
        VALUES ($1, '葉出口分流（測試）', $2::jsonb, NULL, TRUE, 'show_knowledge', NULL)
        """,
        INTRO_FORM,
        json.dumps([
            {
                "field_name": "choice",
                "field_type": "select",
                "prompt": "想先看什麼？\n1. 看方案\n2. 預約 demo\n3. 看價格",
                "options": [
                    {"label": "看方案", "value": "plan", "answer_kb": kb_plan},
                    {"label": "預約 demo", "value": "demo", "next_form_id": CTA_FORM},
                    {"label": "看價格", "value": "price", "answer_kb": kb_price},
                ],
            }
        ]),
    )

    manager = FormManager(db_pool=pool)
    try:
        yield manager
    finally:
        await _cleanup(conn, session_ids)
        await conn.close()
        await pool.close()


async def _complete_choice(manager, session_id, value):
    await manager.create_form_session(
        session_id=session_id, user_id="u-41", vendor_id=None, form_id=INTRO_FORM
    )
    session_state = await manager.get_session_state(session_id)
    form_schema = await manager.get_form_schema(INTRO_FORM)
    return await manager._complete_form(session_state, form_schema, {"choice": value})


@pytest.mark.asyncio
async def test_leaf_type1_knowledge_answer_without_retrieval(env):
    """type 1 知識答案：選項 answer_kb → branch_answer 直取該知識（精確內容，不經檢索）。"""
    result = await _complete_choice(env, "test-or-41-knowledge", "plan")
    assert result["form_completed"] is True
    assert result["answer"] == KB_PLAN_MARK  # 精確等於該知識，非檢索拼湊
    assert "form_triggered" not in result


@pytest.mark.asyncio
async def test_leaf_type2_cta_action_form_chained(env):
    """type 2 動作表單：選項 next_form_id → 串接 CTA demo_form，目標 on_complete_action=call_api。"""
    result = await _complete_choice(env, "test-or-41-cta", "demo")
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == CTA_FORM
    assert result["current_field"] == "contact"

    # 會話切換到 CTA 表單；該表單為 call_api 動作型
    switched = await env.get_session_state("test-or-41-cta")
    assert switched["form_id"] == CTA_FORM
    assert switched["state"] == "COLLECTING"
    cta_schema = await env.get_form_schema(CTA_FORM)
    assert cta_schema["on_complete_action"] == "call_api"
    assert cta_schema["api_config"]["endpoint"] == "demo_form"


@pytest.mark.asyncio
async def test_leaf_type3_url_outlet_link_in_answer(env):
    """type 3 導向連結：選項 answer_kb 指向內含 /pricing 連結之知識，連結於 answer 呈現。"""
    result = await _complete_choice(env, "test-or-41-url", "price")
    assert result["form_completed"] is True
    assert "/pricing" in result["answer"]
    assert result["answer"] == KB_PRICE_MARK
