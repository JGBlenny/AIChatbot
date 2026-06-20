"""
DB verification for the payment_gateway_followup sample form (form-chaining task 5.1).
Feature: form-chaining
Task: 5.1 - 建立金流追問選單範例表單（單一 select + branch_answer mapping）

需求：4.1, 4.2

前置：須已套用 database/migrations/create_payment_gateway_followup_form.sql。
"""

import json
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
async def form():
    c = await asyncpg.connect(**_conn_kwargs())
    row = await c.fetchrow(
        """
        SELECT form_id, form_name, vendor_id, is_active, on_complete_action,
               fields::text AS fields, api_config::text AS api_config
        FROM form_schemas WHERE form_id = 'payment_gateway_followup'
        """
    )
    await c.close()
    assert row is not None, "payment_gateway_followup 表單不存在（migration 未套用？）"
    return {
        "form_id": row["form_id"],
        "form_name": row["form_name"],
        "vendor_id": row["vendor_id"],
        "is_active": row["is_active"],
        "on_complete_action": row["on_complete_action"],
        "fields": json.loads(row["fields"]),
        "api_config": json.loads(row["api_config"]),
    }


@pytest.mark.asyncio
async def test_form_active_and_call_api(form):
    assert form["is_active"] is True
    assert form["on_complete_action"] == "call_api"
    # 與 payment_gateway_select 一致：平台通用表單
    assert form["vendor_id"] is None


@pytest.mark.asyncio
async def test_single_select_field_with_three_options(form):
    fields = form["fields"]
    assert len(fields) == 1, "應為單一欄位"
    field = fields[0]
    assert field["field_type"] == "select"
    assert field["field_name"] == "followup_topic"
    labels = [o["label"] for o in field["options"]]
    values = [o["value"] for o in field["options"]]
    assert labels == ["手續費誰負擔", "能不能綁多家", "怎麼換金流商"]
    assert values == ["fee", "multi", "switch"]
    # prompt 含 1./2./3. 編號選項
    for n, label in enumerate(labels, start=1):
        assert f"{n}. {label}" in field["prompt"]


@pytest.mark.asyncio
async def test_branch_answer_mapping(form):
    cfg = form["api_config"]
    assert cfg["endpoint"] == "branch_answer"
    assert cfg["combine_with_knowledge"] is False
    params = cfg["params"]
    assert params["choice"] == "{form.followup_topic}"
    # 手續費→3551；綁多家／換金流商→3554
    assert params["mapping"] == {"fee": 3551, "multi": 3554, "switch": 3554}
    assert params.get("fallback"), "應提供 fallback 訊息"
