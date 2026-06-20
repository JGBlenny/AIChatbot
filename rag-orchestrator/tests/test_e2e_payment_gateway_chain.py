"""
End-to-end test for the payment-gateway chaining scenario (form-chaining task 6.1).
Feature: form-chaining
Task: 6.1 - 選「永豐」→ 設定說明(3550) + 追問選單 → 選「1」→ branch_answer 回手續費(3551)

需求：3.1, 3.2, 4.1, 4.3

驅動真實 collect_field_data → _complete_form → branch_answer（純內部、DB-only）流程，
全程不經向量檢索 / reranker（決定性）。初始知識觸發（需檢索）屬既有行為，不在本測試範圍，
故直接建立來源會話模擬「表單已被觸發」後的兩步點選。
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
SESSION_ID = "test-fc-61-e2e"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


async def _cleanup():
    c = await asyncpg.connect(**_conn_kwargs())
    await c.execute(
        "DELETE FROM form_submissions WHERE form_session_id IN "
        "(SELECT id FROM form_sessions WHERE session_id = $1)",
        SESSION_ID,
    )
    await c.execute("DELETE FROM form_sessions WHERE session_id = $1", SESSION_ID)
    await c.close()


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    yield p
    await p.close()


@pytest_asyncio.fixture
async def manager(pool):
    return FormManager(db_pool=pool)


@pytest.mark.asyncio
async def test_select_sinopac_then_followup_fee(manager):
    await _cleanup()
    try:
        # 模擬表單已由知識觸發（payment_gateway_select 進入收集）
        await manager.create_form_session(
            session_id=SESSION_ID,
            user_id="u-61",
            vendor_id=None,
            form_id=SOURCE,
            trigger_question="線上金流怎麼申請",
        )

        # ── 第 1 步：選「永豐」→ 設定說明(3550) + 自動串接追問選單 ──
        r1 = await manager.collect_field_data("永豐", SESSION_ID, vendor_id=1)

        assert r1.get("form_id") == NEXT, f"應串接到追問選單，實際：{r1.get('form_id')}"
        assert r1.get("form_triggered") is True
        assert r1.get("form_completed") is False
        # 永豐設定說明（kb 3550）
        assert "店舖編號" in r1["answer"], "應含永豐設定說明（3550）"
        # 合併分隔線 + 追問選單
        assert "\n\n---\n\n" in r1["answer"]
        assert "手續費誰負擔" in r1["answer"], "應含追問選單選項"

        # ── 第 2 步：選「1」→ branch_answer 回手續費(3551) ──
        r2 = await manager.collect_field_data("1", SESSION_ID, vendor_id=1)

        # 手續費由房東負擔（kb 3551）
        assert "房東" in r2["answer"], f"應回手續費知識（3551），實際：{r2['answer'][:80]}"
        # 追問選單無後續串接 → 正常完成，不再觸發新表單
        assert r2.get("form_id") != NEXT or r2.get("form_triggered") is not True
    finally:
        await _cleanup()
