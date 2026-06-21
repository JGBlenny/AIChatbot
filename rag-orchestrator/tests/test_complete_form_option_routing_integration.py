"""
Real-DB integration tests for option-routing dispatch (option-routing task 3.2).
Feature: option-routing
Task: 3.2 - 整合測試（真實 DB）：
    - 選項分歧建立後續 COLLECTING 會話且 get_session_state 切換
    - 葉答案覆寫不雙重回答（on_complete_action=show_knowledge）
    - 終端非 select → fallback 表單層 next_form_id
    - 未設選項路由之既有表單與 form-chaining 金流範例回傳不變

需求：2.4, 3.2, 3.3, 7.1, 7.2

自帶 fixtures（測試用 form_schemas + knowledge_base 葉答案），不依賴 presales 範例資料（任務 5/6）。
使用真實 DB（aichatbot-postgres）。
"""

import json
import os

# 同步 DB 層（form_manager.get_db_cursor）預設連 docker 網路名 'postgres'；
# host 上跑整合測試需指向 localhost。須在匯入 form_manager 前設定。
os.environ.setdefault("DB_HOST", "localhost")

import sys

import asyncpg
import pytest
import pytest_asyncio

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "services"))
sys.path.insert(0, os.path.join(_HERE, ".."))

from form_manager import FormManager  # noqa: E402

INTRO_FORM = "test_or_intro"
UNITS_FORM = "test_or_units"
TEXTONLY_FORM = "test_or_textonly"
LEAF_MARK = "團隊請洽專人 demo（測試葉答案，不含價格）"

# 既有 form-chaining 金流範例（向後相容對照）
PAY_SOURCE = "payment_gateway_select"
PAY_NEXT = "payment_gateway_followup"


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
        "DELETE FROM knowledge_base WHERE question_summary = '團隊方案說明(測試)'"
    )


async def _insert_form(conn, form_id, fields, *, next_form_id=None,
                       on_complete_action="show_knowledge"):
    await conn.execute(
        """
        INSERT INTO form_schemas
            (form_id, form_name, fields, vendor_id, is_active,
             on_complete_action, api_config, next_form_id)
        VALUES ($1, $2, $3::jsonb, NULL, TRUE, $4, NULL, $5)
        """,
        form_id, f"{form_id}（測試）", json.dumps(fields),
        on_complete_action, next_form_id,
    )


@pytest_asyncio.fixture
async def env():
    # 葉答案需經 ApiCallHandler._handle_branch_answer 查 knowledge_base，
    # 該處用 asyncpg db_pool；故 FormManager 須帶真實 pool（否則 branch_answer 無 DB 回 fallback）。
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    conn = await asyncpg.connect(**_conn_kwargs())
    session_ids = [
        "test-or-32-subtree",
        "test-or-32-leaf",
        "test-or-32-fallback",
        "test-or-32-compat",
    ]
    await _cleanup(conn, session_ids)

    # 1. 葉答案知識（供選項 answer_kb 指向）
    leaf_id = await conn.fetchval(
        """
        INSERT INTO knowledge_base (question_summary, answer, scope, is_active)
        VALUES ('團隊方案說明(測試)', $1, 'system_provider', TRUE)
        RETURNING id
        """,
        LEAF_MARK,
    )

    # 2. 子樹目標表單（戶數 select）
    await _insert_form(conn, UNITS_FORM, [
        {
            "field_name": "units",
            "field_type": "select",
            "prompt": "大約管幾戶？\n1. 10 戶\n2. 20 戶\n3. 30 戶",
            "options": [
                {"label": "10 戶", "value": "10"},
                {"label": "20 戶", "value": "20"},
                {"label": "30 戶", "value": "30"},
            ],
        }
    ])

    # 3. 起手式分流（select，per-option 路由）
    await _insert_form(conn, INTRO_FORM, [
        {
            "field_name": "identity",
            "field_type": "select",
            "prompt": "您是？\n1. 個人房東\n2. 公司團隊",
            "options": [
                {"label": "個人房東", "value": "individual", "next_form_id": UNITS_FORM},
                {"label": "公司團隊", "value": "team", "answer_kb": leaf_id},
            ],
        }
    ])

    # 4. 純文字表單（終端非 select）→ 表單層 next_form_id fallback
    await _insert_form(conn, TEXTONLY_FORM, [
        {"field_name": "note", "field_type": "text", "prompt": "請補充說明"}
    ], next_form_id=UNITS_FORM)

    manager = FormManager(db_pool=pool)
    try:
        yield manager, leaf_id, session_ids
    finally:
        await _cleanup(conn, session_ids)
        await conn.close()
        await pool.close()


@pytest.mark.asyncio
async def test_option_branch_creates_followup_session_and_switches(env):
    """選項分歧（個人→戶數子樹）：建立後續 COLLECTING 會話且 get_session_state 切換。"""
    manager, _leaf_id, _ = env
    session_id = "test-or-32-subtree"

    await manager.create_form_session(
        session_id=session_id, user_id="u-32", vendor_id=None, form_id=INTRO_FORM
    )
    session_state = await manager.get_session_state(session_id)
    form_schema = await manager.get_form_schema(INTRO_FORM)

    result = await manager._complete_form(
        session_state, form_schema, {"identity": "individual"}
    )

    # 串接旗標契約指向子樹
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == UNITS_FORM
    assert result["current_field"] == "units"
    assert result["current_field_type"] == "select"
    assert "10 戶" in result["answer"]

    # 會話切換到子樹 COLLECTING
    switched = await manager.get_session_state(session_id)
    assert switched["form_id"] == UNITS_FORM
    assert switched["state"] == "COLLECTING"


@pytest.mark.asyncio
async def test_leaf_answer_overwrites_no_double_answer(env):
    """葉答案（團隊→answer_kb）覆寫 completion_message，不雙重回答（show_knowledge）。"""
    manager, _leaf_id, _ = env
    session_id = "test-or-32-leaf"

    await manager.create_form_session(
        session_id=session_id, user_id="u-32", vendor_id=None, form_id=INTRO_FORM
    )
    session_state = await manager.get_session_state(session_id)
    form_schema = await manager.get_form_schema(INTRO_FORM)
    assert form_schema["on_complete_action"] == "show_knowledge"

    result = await manager._complete_form(
        session_state, form_schema, {"identity": "team"}
    )

    # 分支結束，answer == 葉答案知識內容（覆寫，非附加）
    assert result["form_completed"] is True
    assert result["answer"] == LEAF_MARK
    assert "form_triggered" not in result
    assert "next_form_id" not in result
    # 不雙重回答：通用完成訊息不出現
    assert "表單填寫完成" not in result["answer"]
    assert "---" not in result["answer"]

    # 未建立後續會話，來源維持並 COMPLETED
    latest = await manager.get_session_state(session_id)
    assert latest["form_id"] == INTRO_FORM
    assert latest["state"] == "COMPLETED"


@pytest.mark.asyncio
async def test_terminal_non_select_falls_back_to_form_layer(env):
    """終端非 select（純文字表單）→ _resolve_selected_route 回 None → fallback 表單層 next_form_id。"""
    manager, _leaf_id, _ = env
    session_id = "test-or-32-fallback"

    await manager.create_form_session(
        session_id=session_id, user_id="u-32", vendor_id=None, form_id=TEXTONLY_FORM
    )
    session_state = await manager.get_session_state(session_id)
    form_schema = await manager.get_form_schema(TEXTONLY_FORM)

    result = await manager._complete_form(
        session_state, form_schema, {"note": "想多了解"}
    )

    # 走表單層 fallback → 串接 UNITS_FORM
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == UNITS_FORM

    switched = await manager.get_session_state(session_id)
    assert switched["form_id"] == UNITS_FORM
    assert switched["state"] == "COLLECTING"


@pytest.mark.asyncio
async def test_existing_form_chaining_payment_example_unchanged(env):
    """向後相容：未設選項路由之既有 form-chaining 金流範例，傳 collected_data 後行為不變。"""
    manager, _leaf_id, _ = env
    session_id = "test-or-32-compat"

    await manager.create_form_session(
        session_id=session_id, user_id="u-32", vendor_id=None, form_id=PAY_SOURCE
    )
    session_state = await manager.get_session_state(session_id)
    form_schema = await manager.get_form_schema(PAY_SOURCE)
    assert form_schema["next_form_id"] == PAY_NEXT
    # 以 show_knowledge 避開 branch_answer API 噪音（對照既有整合測試）
    form_schema["on_complete_action"] = "show_knowledge"
    form_schema["api_config"] = None

    result = await manager._complete_form(
        session_state, form_schema, {"gateway": "sinopac"}
    )

    # 表單層主幹串接不受新機制影響
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == PAY_NEXT
    assert "\n\n---\n\n" in result["answer"]
    assert "金流追問選單" in result["answer"]

    switched = await manager.get_session_state(session_id)
    assert switched["form_id"] == PAY_NEXT
    assert switched["state"] == "COLLECTING"
