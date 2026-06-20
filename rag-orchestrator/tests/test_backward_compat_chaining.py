"""
Backward-compatibility regression for form-chaining (task 6.4).
Feature: form-chaining
Task: 6.4 - 抽樣既有表單（查詢型/申請型）流程不變；SOP 既有串接不受影響

需求：7.1, 7.2

只讀 + 純函式（_maybe_chain_next_form 對 next_form_id=NULL 立即回 None，無副作用）。
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

# 抽樣既有表單：查詢型 + 申請型 + show_knowledge / call_api 各型態
SAMPLE_EXISTING_FORMS = [
    "rental_application",       # 申請型 / show_knowledge
    "jgb_repair_query",         # 查詢型 / call_api
    "jgb_repair_create",        # 申請型 / call_api（亦為 SOP 目標）
    "billing_inquiry_guest",    # 查詢型 / call_api（亦為 SOP 目標）
    "complaint_form",           # show_knowledge（亦為 SOP 目標）
]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest_asyncio.fixture
async def conn():
    c = await asyncpg.connect(**_conn_kwargs())
    yield c
    await c.close()


@pytest.fixture
def manager():
    return FormManager()


def _session_state():
    return {
        "session_id": "compat-probe",
        "user_id": "u",
        "vendor_id": None,
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_sampled_existing_forms_do_not_chain(manager):
    """R7.1：抽樣既有表單（next_form_id=NULL）完成時不觸發串接。"""
    for form_id in SAMPLE_EXISTING_FORMS:
        schema = await manager.get_form_schema(form_id)
        assert schema is not None, f"既有表單應存在：{form_id}"
        assert schema.get("next_form_id") in (None,), f"{form_id} 不應設定 next_form_id"
        chain = await manager._maybe_chain_next_form(schema, _session_state())
        assert chain is None, f"既有表單 {form_id} 不應被串接影響"


@pytest.mark.asyncio
async def test_only_payment_gateway_select_chains(conn):
    """R7.1：全表掃描——除刻意設定的串接來源外，其餘表單 next_form_id 皆為 NULL。"""
    rows = await conn.fetch(
        "SELECT form_id FROM form_schemas WHERE next_form_id IS NOT NULL"
    )
    assert {r["form_id"] for r in rows} == {"payment_gateway_select"}


@pytest.mark.asyncio
async def test_sop_chain_data_intact(conn):
    """R7.2：SOP 既有串接資料（vendor_sop_items.next_form_id）仍存在、未受影響。"""
    with_next_form = await conn.fetchval(
        "SELECT count(*) FROM vendor_sop_items WHERE next_form_id IS NOT NULL"
    )
    assert with_next_form > 0, "SOP 既有串接資料應仍存在"


@pytest.mark.asyncio
async def test_sop_target_forms_do_not_auto_chain(conn):
    """R7.2：SOP 觸發的目標表單其 form_schemas.next_form_id 皆為 NULL，
    確保 SOP（vendor_sop_items.next_form_id / form_then_api）不會因新機制被二次串接。"""
    rows = await conn.fetch(
        """
        SELECT DISTINCT fs.form_id
        FROM vendor_sop_items si
        JOIN form_schemas fs ON fs.form_id = si.next_form_id
        WHERE si.next_form_id IS NOT NULL
          AND fs.next_form_id IS NOT NULL
        """
    )
    assert rows == [], (
        "SOP 目標表單不應同時設定 form_schemas.next_form_id："
        f"{[r['form_id'] for r in rows]}"
    )
