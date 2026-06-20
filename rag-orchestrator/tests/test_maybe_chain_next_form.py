"""
Unit tests for FormManager._maybe_chain_next_form (form-chaining task 3.1).
Feature: form-chaining
Task: 3.1 - 串接核心 helper（讀 next_form_id、深度/循環防護、建立後續會話、回呈現契約、全程容錯）

需求：1.1, 1.2, 1.3, 1.4, 2.1, 2.4, 2.5, 6.1, 6.2, 6.3

以 mock 隔離 DB（_get_form_schema_sync / create_form_session / update_session_state），
_present_first_field 為純函式保留真實實作。
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from form_manager import FormManager  # noqa: E402


def _next_schema():
    return {
        "form_id": "payment_gateway_followup",
        "form_name": "金流追問選單",
        "default_intro": "還想了解什麼嗎？",
        "is_active": True,
        "fields": [
            {
                "field_name": "followup_topic",
                "field_type": "select",
                "prompt": "還想了解什麼？\n1. 手續費誰負擔\n2. 能不能綁多家\n3. 怎麼換金流商",
                "required": True,
                "options": [
                    {"label": "手續費誰負擔", "value": "fee"},
                    {"label": "能不能綁多家", "value": "multi"},
                    {"label": "怎麼換金流商", "value": "switch"},
                ],
            }
        ],
    }


def _source_schema(next_form_id="payment_gateway_followup", form_id="payment_gateway_select"):
    return {"form_id": form_id, "form_name": "金流商選擇", "next_form_id": next_form_id, "fields": []}


def _session_state(metadata=None):
    return {
        "session_id": "sess-1",
        "user_id": "user-1",
        "vendor_id": 1,
        "metadata": metadata,
    }


def _wire(manager, next_schema):
    """裝上 mock：DB 載入後續表單成功、建立會話成功、更新 metadata 成功。"""
    manager._get_form_schema_sync = MagicMock(return_value=next_schema)
    manager.create_form_session = AsyncMock(return_value={"id": 999, "session_id": "sess-1"})
    manager.update_session_state = AsyncMock(return_value={"id": 999})


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_no_next_form_returns_none(manager):
    src = _source_schema(next_form_id=None)
    result = await manager._maybe_chain_next_form(src, _session_state())
    assert result is None


@pytest.mark.asyncio
async def test_next_form_not_found_or_inactive_returns_none(manager):
    # _get_form_schema_sync 已過濾 is_active；不存在/未啟用 → None
    manager._get_form_schema_sync = MagicMock(return_value=None)
    manager.create_form_session = AsyncMock()
    result = await manager._maybe_chain_next_form(_source_schema(), _session_state())
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_depth_limit_returns_none(manager):
    _wire(manager, _next_schema())
    # chain_depth 已達上限 MAX_CHAIN_DEPTH → depth+1 超限 → None
    meta = {"chain_depth": manager.MAX_CHAIN_DEPTH, "chain_visited": ["a", "b", "c"]}
    result = await manager._maybe_chain_next_form(_source_schema(), _session_state(meta))
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_cycle_detection_returns_none(manager):
    _wire(manager, _next_schema())
    meta = {"chain_depth": 1, "chain_visited": ["payment_gateway_select", "payment_gateway_followup"]}
    result = await manager._maybe_chain_next_form(_source_schema(), _session_state(meta))
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_self_loop_returns_none(manager):
    """A 接 A（自我循環）：來源 form_id 入訪集後，next == source 即偵測。"""
    _wire(manager, _next_schema())
    src = _source_schema(next_form_id="payment_gateway_select", form_id="payment_gateway_select")
    result = await manager._maybe_chain_next_form(src, _session_state(None))
    assert result is None


@pytest.mark.asyncio
async def test_normal_returns_contract(manager):
    _wire(manager, _next_schema())
    result = await manager._maybe_chain_next_form(_source_schema(), _session_state(None))

    assert result is not None
    assert result["next_form_id"] == "payment_gateway_followup"
    assert result["current_field"] == "followup_topic"
    assert result["current_field_type"] == "select"
    assert result["chain_depth"] == 1
    assert "1. 手續費誰負擔" in result["first_field_prompt"]
    assert "取消" in result["first_field_prompt"]
    assert result["quick_replies"] is not None and len(result["quick_replies"]) == 3

    # 建立後續 COLLECTING 會話
    manager.create_form_session.assert_awaited_once()
    _, kwargs = manager.create_form_session.call_args
    assert kwargs.get("form_id") == "payment_gateway_followup"
    assert kwargs.get("session_id") == "sess-1"


@pytest.mark.asyncio
async def test_metadata_written_with_depth_visited_and_role(manager):
    _wire(manager, _next_schema())
    meta = {"role_id": "landlord", "chain_depth": 0, "chain_visited": ["payment_gateway_select"]}
    await manager._maybe_chain_next_form(_source_schema(), _session_state(meta))

    manager.update_session_state.assert_awaited_once()
    _, kwargs = manager.update_session_state.call_args
    written = kwargs.get("metadata")
    assert written["chain_depth"] == 1
    assert written["chain_visited"] == ["payment_gateway_select", "payment_gateway_followup"]
    assert written["role_id"] == "landlord"  # R2.5 沿用來源角色


@pytest.mark.asyncio
async def test_exception_returns_none(manager):
    """任何例外都回 None，不影響來源完成（R6.3）。"""
    manager._get_form_schema_sync = MagicMock(side_effect=RuntimeError("boom"))
    result = await manager._maybe_chain_next_form(_source_schema(), _session_state())
    assert result is None
