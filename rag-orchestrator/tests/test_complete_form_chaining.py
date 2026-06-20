"""
Integration-of-wiring tests for _complete_form chaining (form-chaining task 4.1).
Feature: form-chaining
Task: 4.1 - _complete_form 完成後呼叫 _maybe_chain_next_form，套用串接 turn 旗標契約

需求：2.1, 2.2, 3.1, 3.2, 6.3, 6.4, 7.1

策略：mock DB/格式化（update_session_state / save_form_submission / _format_completion_message）
與已測過的 _maybe_chain_next_form，聚焦驗證「整合 + 旗標契約 + 合併 answer + 向後相容」。
"""

import os
import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from form_manager import FormManager  # noqa: E402


def _session_state():
    return {
        "id": 100,
        "session_id": "sess-1",
        "user_id": "user-1",
        "vendor_id": 1,
        "form_id": "payment_gateway_select",
        "current_field_index": 0,
        "metadata": {},
    }


def _form_schema():
    return {
        "form_id": "payment_gateway_select",
        "form_name": "金流商選擇",
        "on_complete_action": "show_knowledge",
        "api_config": None,
        "next_form_id": "payment_gateway_followup",
        "fields": [{"field_name": "gateway", "field_type": "select", "prompt": "選哪家？"}],
    }


def _chain_result():
    return {
        "next_form_id": "payment_gateway_followup",
        "first_field_prompt": "📝 **金流追問選單**\n\n還想了解什麼？\n1. 手續費誰負擔\n\n（或輸入「**取消**」結束填寫）",
        "current_field": "followup_topic",
        "current_field_type": "select",
        "quick_replies": [{"text": "手續費誰負擔", "value": "fee", "style": "default"}],
        "chain_depth": 1,
    }


def _wire_completion(manager):
    """共用：mock 完成路徑的 DB/格式化副作用。"""
    manager.update_session_state = AsyncMock(return_value={})
    manager.save_form_submission = AsyncMock(return_value=555)
    manager._format_completion_message = AsyncMock(return_value="永豐設定說明內容")


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_chain_merges_answer_and_sets_flag_contract(manager):
    _wire_completion(manager)
    manager._maybe_chain_next_form = AsyncMock(return_value=_chain_result())

    result = await manager._complete_form(_session_state(), _form_schema(), {"gateway": "sinopac"})

    # answer 合併：來源完成答案 + 分隔線 + 後續第一欄提示
    assert result["answer"] == "永豐設定說明內容\n\n---\n\n" + _chain_result()["first_field_prompt"]
    # 串接 turn 旗標契約
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == "payment_gateway_followup"
    assert result["current_field"] == "followup_topic"
    assert result["current_field_type"] == "select"
    assert result["quick_replies"] == _chain_result()["quick_replies"]
    assert result["next_form_id"] == "payment_gateway_followup"
    # 保留既有欄位
    assert result["collected_data"] == {"gateway": "sinopac"}


@pytest.mark.asyncio
async def test_source_completion_still_happens_on_chain(manager):
    """串接不得影響來源核心完成：來源列仍被標記 COMPLETED。"""
    _wire_completion(manager)
    manager._maybe_chain_next_form = AsyncMock(return_value=_chain_result())

    await manager._complete_form(_session_state(), _form_schema(), {"gateway": "sinopac"})

    # 來源完成的 update_session_state 仍被呼叫（state=COMPLETED）
    assert manager.update_session_state.await_count >= 1
    states = [c.kwargs.get("state") for c in manager.update_session_state.await_args_list]
    assert "COMPLETED" in states


@pytest.mark.asyncio
async def test_no_chain_returns_unchanged_contract(manager):
    """未串接（_maybe_chain_next_form→None）：回傳與現況完全一致（R7.1 向後相容）。"""
    _wire_completion(manager)
    manager._maybe_chain_next_form = AsyncMock(return_value=None)

    result = await manager._complete_form(_session_state(), _form_schema(), {"gateway": "sinopac"})

    assert result["answer"] == "永豐設定說明內容"
    assert result["form_completed"] is True
    assert "form_triggered" not in result
    assert "next_form_id" not in result
    assert result["submission_id"] == 555
    assert result["collected_data"] == {"gateway": "sinopac"}
