"""
DB-level verification for form-chaining migration (task 1.2).
Feature: form-chaining
Task: 1.2 - 套用 migration 並驗證：欄位／FK／索引存在；既有列 next_form_id 為 NULL 且行為不受影響

需求：7.1, 7.3

前置：須已套用 database/migrations/add_next_form_id_to_form_schemas.sql。
連線參數沿用既有 migration 測試慣例（環境變數覆寫，預設對 localhost）。
"""

import os

import asyncpg
import pytest
import pytest_asyncio


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


@pytest.mark.asyncio
async def test_next_form_id_column_exists_nullable_varchar100(conn):
    """next_form_id 欄位存在、可空、character varying(100)。"""
    row = await conn.fetchrow(
        """
        SELECT data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'form_schemas' AND column_name = 'next_form_id'
        """
    )
    assert row is not None, "next_form_id 欄位不存在（migration 未套用？）"
    assert row["data_type"] == "character varying"
    assert row["character_maximum_length"] == 100
    assert row["is_nullable"] == "YES", "next_form_id 應可空"


@pytest.mark.asyncio
async def test_foreign_key_on_delete_set_null(conn):
    """FK fk_form_schemas_next_form 自我參照 form_schemas(form_id)，ON DELETE SET NULL。"""
    row = await conn.fetchrow(
        """
        SELECT confreltype.relname AS ref_table,
               confdeltype,
               pg_get_constraintdef(c.oid) AS def
        FROM pg_constraint c
        JOIN pg_class confreltype ON confreltype.oid = c.confrelid
        WHERE c.conname = 'fk_form_schemas_next_form'
        """
    )
    assert row is not None, "FK fk_form_schemas_next_form 不存在"
    assert row["ref_table"] == "form_schemas", "FK 應參照 form_schemas"
    # confdeltype 'n' = SET NULL（pg "char" 型，asyncpg 回傳 bytes）
    confdeltype = row["confdeltype"]
    if isinstance(confdeltype, bytes):
        confdeltype = confdeltype.decode()
    assert confdeltype == "n", "FK 應為 ON DELETE SET NULL"
    assert "REFERENCES form_schemas(form_id)" in row["def"]
    assert "ON DELETE SET NULL" in row["def"]


@pytest.mark.asyncio
async def test_index_exists(conn):
    """索引 idx_form_schemas_next_form_id 存在且建於 next_form_id。"""
    row = await conn.fetchrow(
        """
        SELECT indexdef FROM pg_indexes
        WHERE tablename = 'form_schemas' AND indexname = 'idx_form_schemas_next_form_id'
        """
    )
    assert row is not None, "索引 idx_form_schemas_next_form_id 不存在"
    assert "next_form_id" in row["indexdef"]


# 本 spec 刻意建立的串接來源（task 5.2）。其餘既有表單皆不應有 next_form_id。
INTENTIONAL_CHAIN_SOURCES = {"payment_gateway_select"}


@pytest.mark.asyncio
async def test_only_intentional_chain_sources_have_next_form_id(conn):
    """向後相容：migration 不自動填值；除了本 spec 刻意設定的串接來源外，
    其餘既有表單 next_form_id 皆為 NULL（R7.1, 7.3）。"""
    total = await conn.fetchval("SELECT count(*) FROM form_schemas")
    assert total > 0, "form_schemas 應有既有資料以驗證向後相容"

    rows = await conn.fetch(
        "SELECT form_id FROM form_schemas WHERE next_form_id IS NOT NULL"
    )
    non_null_form_ids = {r["form_id"] for r in rows}
    unexpected = non_null_form_ids - INTENTIONAL_CHAIN_SOURCES
    assert not unexpected, f"非預期的表單被設定了 next_form_id：{unexpected}"
