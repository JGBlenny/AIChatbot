"""
Unit tests for FormManager._maybe_chain_next_form option-routing 接入 (task 2.1/2.2).
Feature: option-routing
Task: 2.1 - _maybe_chain_next_form 接入選項路由（collected_data 解析、葉答案、合併、fallback）

需求：2.2, 2.3, 3.1, 6.1, 6.2, 6.3

以 mock 隔離 DB（_get_form_schema_sync / create_form_session / update_session_state）
與葉答案解析（_resolve_leaf_answer）；_resolve_selected_route / _present_first_field
為純函式保留真實實作。
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from form_manager import FormManager  # noqa: E402


def _next_schema(form_id="presales_individual_units"):
    return {
        "form_id": form_id,
        "form_name": "戶數子樹",
        "is_active": True,
        "fields": [
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
        ],
    }


def _source_schema(options, next_form_id=None, form_id="presales_intro"):
    """來源（起手式分流）：單一 select，options 帶 per-option 路由。"""
    return {
        "form_id": form_id,
        "form_name": "起手式分流",
        "next_form_id": next_form_id,  # 表單層 fallback
        "fields": [
            {
                "field_name": "identity",
                "field_type": "select",
                "options": options,
            }
        ],
    }


def _session_state(metadata=None):
    return {
        "session_id": "sess-1",
        "user_id": "user-1",
        "vendor_id": 1,
        "metadata": metadata,
    }


def _wire(manager, next_schema):
    manager._get_form_schema_sync = MagicMock(return_value=next_schema)
    manager.create_form_session = AsyncMock(return_value={"id": 999, "session_id": "sess-1"})
    manager.update_session_state = AsyncMock(return_value={"id": 999})


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_option_subtree_builds_session_and_contract(manager):
    """選項含 next_form_id → 建後續會話、回子樹契約（next_form_id 來自選項層）。"""
    _wire(manager, _next_schema("presales_individual_units"))
    src = _source_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "presales_individual_units"},
        {"label": "公司團隊", "value": "team", "answer_kb": 9001},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "individual"}
    )
    assert result is not None
    assert result["next_form_id"] == "presales_individual_units"
    assert result["current_field"] == "units"
    assert result["current_field_type"] == "select"
    assert result["chain_depth"] == 1
    assert result["leaf_answer"] is None  # 純子樹，無葉答案
    manager.create_form_session.assert_awaited_once()
    _, kwargs = manager.create_form_session.call_args
    assert kwargs.get("form_id") == "presales_individual_units"


@pytest.mark.asyncio
async def test_option_leaf_answer_only(manager):
    """選項僅含 answer_kb → 回葉契約，不建會話（分支結束）。"""
    _wire(manager, _next_schema())
    manager._resolve_leaf_answer = AsyncMock(return_value="團隊方案說明（不含價格）")
    src = _source_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "team"}
    )
    assert result == {"leaf": True, "answer": "團隊方案說明（不含價格）"}
    manager.create_form_session.assert_not_called()
    manager._resolve_leaf_answer.assert_awaited_once_with(9001)


@pytest.mark.asyncio
async def test_option_leaf_plus_subtree_merges(manager):
    """選項同時含 answer_kb + next_form_id → 串接子樹且回傳含 leaf_answer 供合併。"""
    _wire(manager, _next_schema("demo_form"))
    manager._resolve_leaf_answer = AsyncMock(return_value="團隊請走 demo")
    src = _source_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001, "next_form_id": "demo_form"},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "team"}
    )
    assert result is not None
    assert result["next_form_id"] == "demo_form"
    assert result["leaf_answer"] == "團隊請走 demo"
    manager.create_form_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_leaf_plus_subtree_degrades_to_leaf_when_subtree_missing(manager):
    """葉答案+子樹：子樹不存在/未啟用 → 降級回葉契約，不丟失葉答案（R6 容錯）。"""
    manager._get_form_schema_sync = MagicMock(return_value=None)  # 子樹載入失敗
    manager.create_form_session = AsyncMock()
    manager.update_session_state = AsyncMock()
    manager._resolve_leaf_answer = AsyncMock(return_value="團隊方案請走 demo")
    src = _source_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001, "next_form_id": "missing_form"},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "team"}
    )
    assert result == {"leaf": True, "answer": "團隊方案請走 demo"}
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_leaf_plus_subtree_degrades_to_leaf_on_depth_limit(manager):
    """葉答案+子樹：深度上限命中 → 降級回葉契約（不丟失葉答案）。"""
    _wire(manager, _next_schema("demo_form"))
    manager._resolve_leaf_answer = AsyncMock(return_value="團隊方案請走 demo")
    meta = {"chain_depth": manager.MAX_CHAIN_DEPTH, "chain_visited": ["a", "b", "c"]}
    src = _source_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001, "next_form_id": "demo_form"},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(meta), collected_data={"identity": "team"}
    )
    assert result == {"leaf": True, "answer": "團隊方案請走 demo"}
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_subtree_only_missing_still_returns_none(manager):
    """純子樹（無葉答案）子樹不存在 → 仍回 None（無葉可降級，行為不變）。"""
    manager._get_form_schema_sync = MagicMock(return_value=None)
    manager.create_form_session = AsyncMock()
    src = _source_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "missing_form"},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "individual"}
    )
    assert result is None


@pytest.mark.asyncio
async def test_option_no_route_falls_back_to_form_layer(manager):
    """被選中選項無路由 → fallback 表單層 next_form_id（擴充共存）。"""
    _wire(manager, _next_schema("payment_gateway_followup"))
    src = _source_schema(
        [{"label": "個人房東", "value": "individual"}],  # 無 per-option 路由
        next_form_id="payment_gateway_followup",
    )
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "individual"}
    )
    assert result is not None
    assert result["next_form_id"] == "payment_gateway_followup"


@pytest.mark.asyncio
async def test_leaf_answer_resolution_failure_returns_none(manager):
    """葉答案解析失敗（_resolve_leaf_answer 回 None）→ 整體回 None（議題 2 容錯）。"""
    _wire(manager, _next_schema())
    manager._resolve_leaf_answer = AsyncMock(return_value=None)
    src = _source_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(None), collected_data={"identity": "team"}
    )
    assert result is None


@pytest.mark.asyncio
async def test_option_subtree_depth_guard_reused(manager):
    """選項子樹仍沿用深度上限防護（R6.1）。"""
    _wire(manager, _next_schema("presales_individual_units"))
    meta = {"chain_depth": manager.MAX_CHAIN_DEPTH, "chain_visited": ["a", "b", "c"]}
    src = _source_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "presales_individual_units"},
    ])
    result = await manager._maybe_chain_next_form(
        src, _session_state(meta), collected_data={"identity": "individual"}
    )
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_option_subtree_cycle_guard_reused(manager):
    """選項子樹仍沿用循環偵測（R6.2）。"""
    _wire(manager, _next_schema("presales_intro"))
    meta = {"chain_depth": 1, "chain_visited": ["presales_intro"]}
    src = _source_schema(
        [{"label": "回頭", "value": "back", "next_form_id": "presales_intro"}],
        form_id="presales_intro",
    )
    result = await manager._maybe_chain_next_form(
        src, _session_state(meta), collected_data={"identity": "back"}
    )
    assert result is None


@pytest.mark.asyncio
async def test_backward_compat_no_collected_data(manager):
    """不傳 collected_data → 行為與既有 form-chaining 完全一致（fallback 表單層）。"""
    _wire(manager, _next_schema("payment_gateway_followup"))
    src = _source_schema(
        [{"label": "x", "value": "x", "next_form_id": "should_be_ignored"}],
        next_form_id="payment_gateway_followup",
    )
    # collected_data 預設 None → 不解析選項路由
    result = await manager._maybe_chain_next_form(src, _session_state(None))
    assert result is not None
    assert result["next_form_id"] == "payment_gateway_followup"


@pytest.mark.asyncio
async def test_resolve_leaf_answer_uses_branch_answer(manager, monkeypatch):
    """_resolve_leaf_answer 經 branch_answer 取知識文字。"""
    import form_manager as fm

    fake_handler = MagicMock()
    fake_handler._handle_branch_answer = AsyncMock(return_value={"message": "個人 20 戶方案說明"})
    monkeypatch.setattr(fm, "get_api_call_handler", lambda db_pool: fake_handler)

    answer = await manager._resolve_leaf_answer(9002)
    assert answer == "個人 20 戶方案說明"
    fake_handler._handle_branch_answer.assert_awaited_once()
    _, kwargs = fake_handler._handle_branch_answer.call_args
    assert kwargs.get("mapping") == {"__leaf__": 9002}


@pytest.mark.asyncio
async def test_resolve_leaf_answer_exception_returns_none(manager, monkeypatch):
    """_resolve_leaf_answer 任一例外 → None（容錯）。"""
    import form_manager as fm

    fake_handler = MagicMock()
    fake_handler._handle_branch_answer = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(fm, "get_api_call_handler", lambda db_pool: fake_handler)

    assert await manager._resolve_leaf_answer(9002) is None
