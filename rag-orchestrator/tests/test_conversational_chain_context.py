"""
單元測試：跨步情境累積（option-routing task 9.5 / 元件 8 / R12）。

驗證 FormManager 串接時 chain_context 的累積、純函式情境擷取，以及
「決定性路由不受情境累積影響」（R12.3）。

以 mock 隔離 DB（_get_form_schema_sync / create_form_session / update_session_state）；
_resolve_selected_route / _selected_option_context 為純函式保留真實實作。
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.form_manager import FormManager  # noqa: E402


def _next_schema(form_id="presales_individual_units"):
    return {
        "form_id": form_id, "form_name": "戶數子樹", "is_active": True,
        "fields": [{
            "field_name": "units", "field_type": "select",
            "prompt": "大約管幾戶？",
            "options": [{"label": "10 戶", "value": "10"}, {"label": "20 戶", "value": "20"}],
        }],
    }


def _source_schema(options, form_id="presales_intro", field_label="您的身分"):
    return {
        "form_id": form_id, "form_name": "起手式分流",
        "fields": [{
            "field_name": "identity", "field_type": "select",
            "field_label": field_label, "options": options,
        }],
    }


def _session_state(metadata=None):
    return {"session_id": "sess-1", "user_id": "user-1", "vendor_id": 1, "metadata": metadata}


def _wire(manager, next_schema):
    manager._get_form_schema_sync = MagicMock(return_value=next_schema)
    manager.create_form_session = AsyncMock(return_value={"id": 999, "session_id": "sess-1"})
    manager.update_session_state = AsyncMock(return_value={"id": 999})


@pytest.fixture
def manager():
    return FormManager()


# ---------- _selected_option_context 純函式 ----------

def test_selected_option_context_returns_entry(manager):
    src = _source_schema([{"label": "個人房東", "value": "individual", "next_form_id": "x"}])
    entry = manager._selected_option_context(src, {"identity": "individual"})
    assert entry == {
        "form_id": "presales_intro", "field_label": "您的身分",
        "selected_label": "個人房東", "selected_value": "individual",
    }


def test_selected_option_context_falls_back_to_raw_value(manager):
    """情境擷取寬鬆：選項無相符時仍記錄使用者原始輸入（供個人化措辭），label=原始值。
    （對比 _resolve_selected_route 路由需精確、不匹配回 None）"""
    src = _source_schema([{"label": "個人房東", "value": "individual"}])
    entry = manager._selected_option_context(src, {"identity": "不存在"})
    assert entry["selected_label"] == "不存在"
    # 同輸入下，決定性路由不匹配 → None（精確）
    assert manager._resolve_selected_route(src, {"identity": "不存在"}) is None


def test_selected_option_context_no_select_returns_none(manager):
    schema = {"form_id": "f", "fields": [{"field_name": "name", "field_type": "text"}]}
    assert manager._selected_option_context(schema, {"name": "abc"}) is None


# ---------- chain_context 累積（串接時 append 並由 metadata 傳遞） ----------

@pytest.mark.asyncio
async def test_chain_context_starts_fresh_when_none(manager):
    """來源無既有 chain_context → 後續會話 metadata 帶 [本步情境]。"""
    _wire(manager, _next_schema())
    src = _source_schema([{"label": "個人房東", "value": "individual",
                           "next_form_id": "presales_individual_units"}])
    await manager._maybe_chain_next_form(src, _session_state(None),
                                         collected_data={"identity": "individual"})
    _, kwargs = manager.update_session_state.call_args
    ctx = kwargs["metadata"]["chain_context"]
    assert [c["selected_label"] for c in ctx] == ["個人房東"]


@pytest.mark.asyncio
async def test_chain_context_accumulates_over_steps(manager):
    """來源已帶前一步 chain_context → 後續會話 metadata 為「前一步 + 本步」累積。"""
    _wire(manager, _next_schema())
    prior = [{"form_id": "presales_entry", "field_label": "主題",
              "selected_label": "適不適合", "selected_value": "fit"}]
    src = _source_schema([{"label": "個人房東", "value": "individual",
                           "next_form_id": "presales_individual_units"}])
    await manager._maybe_chain_next_form(src, _session_state({"chain_context": prior}),
                                         collected_data={"identity": "individual"})
    _, kwargs = manager.update_session_state.call_args
    ctx = kwargs["metadata"]["chain_context"]
    assert [c["selected_label"] for c in ctx] == ["適不適合", "個人房東"]


# ---------- R12.3：決定性路由不受情境累積影響 ----------

def test_routing_unaffected_by_accumulated_context(manager):
    """同一被選選項，不論 metadata 帶多少 chain_context，_resolve_selected_route 結果相同。"""
    src = _source_schema([{"label": "個人房東", "value": "individual",
                           "next_form_id": "presales_individual_units"}])
    route = manager._resolve_selected_route(src, {"identity": "individual"})
    assert route == {"next_form_id": "presales_individual_units"}
    # _resolve_selected_route 不吃 metadata/情境，純由 schema+collected_data 決定（決定性）
