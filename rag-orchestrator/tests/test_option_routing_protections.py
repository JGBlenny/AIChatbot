"""
單元測試：選項路由（決策樹）多層情境的防護沿用（option-routing task 8.3 / R6.1, R6.2）。

form-chaining 的深度上限與循環防護，於「被選中選項」帶 next_form_id 的多層決策樹路徑
（而非表單層 next_form_id）同樣生效。取消/離題另由 test_followup_cancel_and_digression
與 conversational 引擎覆蓋。

以 mock 隔離 DB；_resolve_selected_route 為純函式保留真實實作。
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.form_manager import FormManager  # noqa: E402


def _next_schema(form_id):
    return {
        "form_id": form_id, "form_name": "子樹", "is_active": True,
        "fields": [{"field_name": "f", "field_type": "select",
                    "prompt": "?", "options": [{"label": "A", "value": "a"}]}],
    }


def _source_with_option_route(next_form_id, form_id="lvl_src"):
    """來源表單：被選中選項帶 next_form_id（per-option 決策樹路徑）。"""
    return {
        "form_id": form_id, "form_name": "決策層",
        "next_form_id": None,  # 無表單層 fallback，確保走的是選項路由
        "fields": [{
            "field_name": "choice", "field_type": "select",
            "options": [{"label": "往下", "value": "go", "next_form_id": next_form_id}],
        }],
    }


def _session_state(metadata=None):
    return {"session_id": "s", "user_id": "u", "vendor_id": 1, "metadata": metadata}


def _wire(manager, next_schema):
    manager._get_form_schema_sync = MagicMock(return_value=next_schema)
    manager.create_form_session = AsyncMock(return_value={"id": 9, "session_id": "s"})
    manager.update_session_state = AsyncMock(return_value={"id": 9})


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.asyncio
async def test_option_route_depth_limit(manager):
    """選項路由的子樹：深度達上限 → 不再串接（沿用 R6.1）。"""
    _wire(manager, _next_schema("lvl_next"))
    meta = {"chain_depth": manager.MAX_CHAIN_DEPTH, "chain_visited": ["x"]}
    result = await manager._maybe_chain_next_form(
        _source_with_option_route("lvl_next"), _session_state(meta),
        collected_data={"choice": "go"},
    )
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_option_route_cycle_detection(manager):
    """選項路由指向已訪表單 → 循環中止（沿用 R6.2）。"""
    _wire(manager, _next_schema("already_visited"))
    meta = {"chain_depth": 1, "chain_visited": ["lvl_src", "already_visited"]}
    result = await manager._maybe_chain_next_form(
        _source_with_option_route("already_visited"), _session_state(meta),
        collected_data={"choice": "go"},
    )
    assert result is None
    manager.create_form_session.assert_not_called()


@pytest.mark.asyncio
async def test_option_route_normal_multilayer_chains(manager):
    """防護未命中時，選項路由的多層決策樹正常串接下一層。"""
    _wire(manager, _next_schema("lvl2"))
    meta = {"chain_depth": 1, "chain_visited": ["lvl_src"]}
    result = await manager._maybe_chain_next_form(
        _source_with_option_route("lvl2"), _session_state(meta),
        collected_data={"choice": "go"},
    )
    assert result is not None
    assert result["next_form_id"] == "lvl2"
    assert result["chain_depth"] == 2
    manager.create_form_session.assert_awaited_once()
