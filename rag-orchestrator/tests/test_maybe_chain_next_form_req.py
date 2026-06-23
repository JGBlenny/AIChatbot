"""重建：FormManager._maybe_chain_next_form 早分支與容錯降級（spec unit-coverage-rebuild・任務 3・R3）。

只覆蓋「不需真實 DB／會話」的早分支與容錯路徑（純 unit，以 monkeypatch 控制 seam）：
- 無 option 路由且無表單層 next_form_id → None
- 純葉答案（answer_kb、無 next_form_id）→ {"leaf": True, ...}
- _resolve_leaf_answer 回 None → 整體 None（議題 2 容錯，intended）
- 子樹載入失敗（_get_form_schema_sync 回 None）但有 leaf_answer → 降級回葉契約（_degrade_to_leaf，intended）

深子樹串接（建立會話/寫 metadata/實際載入）需真實 DB → 不在本檔（→ integration 軌道）。
"""
import pytest
from unittest.mock import AsyncMock

from form_manager import FormManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.req("unit-coverage-rebuild:3.1")
async def test_no_route_and_no_form_level_next_returns_none(manager):
    """無 option 路由（collected_data=None）且來源無表單層 next_form_id → None。"""
    source_schema = {"form_id": "src", "fields": [{"field_name": "x", "field_type": "text"}]}
    session_state = {"session_id": "s1", "metadata": {}}
    result = await manager._maybe_chain_next_form(source_schema, session_state, collected_data=None)
    assert result is None


@pytest.mark.req("unit-coverage-rebuild:3.1")
async def test_pure_leaf_answer_returns_leaf_contract(manager, monkeypatch):
    """選項帶 answer_kb、無 next_form_id → 回葉契約 {"leaf": True, "answer", "accumulated_context"}。"""
    monkeypatch.setattr(manager, "_resolve_leaf_answer", AsyncMock(return_value="這是葉答案內容"))
    source_schema = {
        "form_id": "src",
        "fields": [
            {"field_name": "identity", "field_type": "select",
             "options": [{"label": "公司團隊", "value": "team", "answer_kb": 9001}]},
        ],
    }
    session_state = {"session_id": "s1", "metadata": {}}
    result = await manager._maybe_chain_next_form(
        source_schema, session_state, collected_data={"identity": "team"}
    )
    assert result is not None
    assert result["leaf"] is True
    assert result["answer"] == "這是葉答案內容"
    assert "accumulated_context" in result


@pytest.mark.req("unit-coverage-rebuild:3.2")
async def test_leaf_answer_resolution_failure_returns_none(manager, monkeypatch):
    """intended（議題 2）：answer_kb 解析回 None → 整體 None（不回半套）。"""
    monkeypatch.setattr(manager, "_resolve_leaf_answer", AsyncMock(return_value=None))
    source_schema = {
        "form_id": "src",
        "fields": [
            {"field_name": "identity", "field_type": "select",
             "options": [{"label": "公司團隊", "value": "team", "answer_kb": 9001}]},
        ],
    }
    session_state = {"session_id": "s1", "metadata": {}}
    result = await manager._maybe_chain_next_form(
        source_schema, session_state, collected_data={"identity": "team"}
    )
    assert result is None


@pytest.mark.req("unit-coverage-rebuild:3.2")
async def test_subtree_load_fail_degrades_to_leaf(manager, monkeypatch):
    """intended：選項帶 answer_kb+next_form_id，子樹載入回 None → 降級回葉契約（不丟葉答案）。"""
    monkeypatch.setattr(manager, "_resolve_leaf_answer", AsyncMock(return_value="葉答案保底"))
    # 子樹載入失敗 seam：_get_form_schema_sync 回 None（不需真實 DB）
    monkeypatch.setattr(manager, "_get_form_schema_sync", lambda *a, **k: None)
    source_schema = {
        "form_id": "src",
        "fields": [
            {"field_name": "identity", "field_type": "select",
             "options": [{"label": "公司團隊", "value": "team",
                          "answer_kb": 9001, "next_form_id": "child_form"}]},
        ],
    }
    session_state = {"session_id": "s1", "vendor_id": 1, "metadata": {}}
    result = await manager._maybe_chain_next_form(
        source_schema, session_state, collected_data={"identity": "team"}
    )
    assert result is not None
    assert result["leaf"] is True
    assert result["answer"] == "葉答案保底"
