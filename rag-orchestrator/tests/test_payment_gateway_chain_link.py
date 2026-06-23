"""
DB verification for the chain link payment_gateway_select → payment_gateway_followup
(form-chaining task 5.2).
Feature: form-chaining
Task: 5.2 - 設定 payment_gateway_select.next_form_id = 'payment_gateway_followup'

需求：2.1

前置：須已套用 database/migrations/set_payment_gateway_select_next_form.sql。
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
async def test_source_form_points_to_followup(conn):
    next_form_id = await conn.fetchval(
        "SELECT next_form_id FROM form_schemas WHERE form_id = 'payment_gateway_select'"
    )
    assert next_form_id == "payment_gateway_followup"


@pytest.mark.asyncio
async def test_followup_target_exists_and_active(conn):
    """串接目標必須存在且啟用，否則 FK / 串接無意義。"""
    is_active = await conn.fetchval(
        "SELECT is_active FROM form_schemas WHERE form_id = 'payment_gateway_followup'"
    )
    assert is_active is True


@pytest.mark.req("testing-traceability:5.4")
@pytest.mark.asyncio
async def test_no_chain_cycle(conn):
    """後續表單不得反向指回來源（避免循環設定）。"""
    followup_next = await conn.fetchval(
        "SELECT next_form_id FROM form_schemas WHERE form_id = 'payment_gateway_followup'"
    )
    assert followup_next != "payment_gateway_select"
