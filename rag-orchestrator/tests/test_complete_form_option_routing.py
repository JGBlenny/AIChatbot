"""
Wiring tests for _complete_form option-routing dispatch (option-routing task 3.1).
Feature: option-routing
Task: 3.1 - _complete_form 傳新鮮 collected_data；依 _maybe_chain_next_form 結果分派
            （子樹合併 / 純葉答案覆寫 / 未路由不變）

需求：2.4, 2.5, 3.2, 4.1, 7.1, 7.2

策略：mock DB/格式化與已測過的 _maybe_chain_next_form，聚焦驗證 _complete_form 的分派與契約。
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
        "form_id": "presales_intro",
        "current_field_index": 0,
        "metadata": {},
    }


def _form_schema():
    return {
        "form_id": "presales_intro",
        "form_name": "起手式分流",
        "on_complete_action": "show_knowledge",
        "api_config": None,
        "next_form_id": None,
        "fields": [{"field_name": "identity", "field_type": "select", "prompt": "您是？"}],
    }


def _wire_completion(manager):
    manager.update_session_state = AsyncMock(return_value={})
    manager.save_form_submission = AsyncMock(return_value=555)
    manager._format_completion_message = AsyncMock(return_value="✅ 表單填寫完成！")


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_fresh_collected_data_passed_to_chain(manager):
    """_complete_form 須以新鮮 collected_data 呼叫 _maybe_chain_next_form（決策 4）。"""
    _wire_completion(manager)
    manager._maybe_chain_next_form = AsyncMock(return_value=None)

    await manager._complete_form(_session_state(), _form_schema(), {"identity": "individual"})

    manager._maybe_chain_next_form.assert_awaited_once()
    _, kwargs = manager._maybe_chain_next_form.call_args
    assert kwargs.get("collected_data") == {"identity": "individual"}


@pytest.mark.asyncio
async def test_pure_leaf_answer_overwrites_completion_message(manager):
    """純葉答案：form_completed=True、answer 以選項知識覆寫 completion_message（決策 7）。"""
    _wire_completion(manager)
    manager._maybe_chain_next_form = AsyncMock(
        return_value={"leaf": True, "answer": "團隊方案請走 demo（不含價格）"}
    )

    result = await manager._complete_form(_session_state(), _form_schema(), {"identity": "team"})

    assert result["answer"] == "團隊方案請走 demo（不含價格）"  # 覆寫，非附加
    assert "✅ 表單填寫完成！" not in result["answer"]  # 不雙重回答
    assert result["form_completed"] is True
    assert "form_triggered" not in result
    assert "next_form_id" not in result
    assert result["submission_id"] == 555
    assert result["collected_data"] == {"identity": "team"}


@pytest.mark.asyncio
async def test_subtree_with_leaf_answer_merges_leaf_as_head(manager):
    """子樹 + 葉答案：合併頭部以選項葉答案覆寫 completion_message + 分隔線 + 後續第一欄。"""
    _wire_completion(manager)
    chain = {
        "next_form_id": "demo_form",
        "first_field_prompt": "請問貴公司名稱？",
        "current_field": "company",
        "current_field_type": "text",
        "quick_replies": None,
        "chain_depth": 1,
        "leaf_answer": "團隊請走 demo",
    }
    manager._maybe_chain_next_form = AsyncMock(return_value=chain)

    result = await manager._complete_form(_session_state(), _form_schema(), {"identity": "team"})

    assert result["answer"] == "團隊請走 demo\n\n---\n\n請問貴公司名稱？"
    assert "✅ 表單填寫完成！" not in result["answer"]  # 葉答案覆寫
    assert result["form_completed"] is False
    assert result["form_triggered"] is True
    assert result["form_id"] == "demo_form"
    assert result["next_form_id"] == "demo_form"


@pytest.mark.asyncio
async def test_subtree_without_leaf_answer_uses_completion_message(manager):
    """子樹無葉答案（選項僅 next_form_id）：頭部沿用 completion_message（向後相容）。"""
    _wire_completion(manager)
    chain = {
        "next_form_id": "presales_individual_units",
        "first_field_prompt": "大約管幾戶？",
        "current_field": "units",
        "current_field_type": "select",
        "quick_replies": [{"text": "10 戶", "value": "10", "style": "default"}],
        "chain_depth": 1,
        "leaf_answer": None,
    }
    manager._maybe_chain_next_form = AsyncMock(return_value=chain)

    result = await manager._complete_form(
        _session_state(), _form_schema(), {"identity": "individual"}
    )

    assert result["answer"] == "✅ 表單填寫完成！\n\n---\n\n大約管幾戶？"
    assert result["form_completed"] is False
    assert result["form_id"] == "presales_individual_units"
