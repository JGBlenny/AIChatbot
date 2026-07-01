"""unit:API grounding 結構（conversational-diagnosis 任務 4.1 / R3.1, R3.2, R3.3, R6.1, R6.3）。

`_ground_by_api(state, config)`：組 session_data(role_id/vendor_id/session_id/user_id)
+ form_data=collected_fields → 重用 `api_handler.execute_api_call`；endpoint/params 讀
grounding_scope，清單路徑/id/label 讀 result_mapping（零合約硬編）；依 list_path 判筆數
（1→converge / 0→ask / N→ask+candidates）。mock api_handler，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


# 合約首案的 api 型 grounding_scope（endpoint/params/result_mapping 全由設定提供）
GSCOPE = {
    "select": "api",
    "endpoint": "jgb_contracts",
    "required_slots": ["contract_ref"],
    "params": {
        "role_id": "{session.role_id}",
        "contract_ids": "{form.contract_ref|if_numeric}",
        "keyword": "{form.contract_ref|if_text}",
    },
    "result_mapping": {
        "list_path": "data",
        "id_field": "id",
        "label_field": "title",
        "refine_param": "contract_ids",
    },
}


def _engine(api_result):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value=api_result)
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, handler


def _state(**fields):
    return {
        "config_key": "contract_diag",
        "collected_fields": {"contract_ref": "基隆", **fields},
        "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
        "asked_count": 1,
    }


def _cfg(gscope=GSCOPE, key="contract_diag"):
    return ConversationalConfig(
        key=key, grounding_scope=gscope,
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


# ── 輸入組裝 + 重用既有 execute_api_call（R3.1, R3.2）──
@pytest.mark.req("conversational-diagnosis:3.2")
async def test_reuses_execute_api_call_with_assembled_inputs():
    eng, handler = _engine(
        {"success": True, "data": {"data": [{"id": 1, "title": "基隆物件"}]},
         "formatted_response": "狀態：已簽約"})
    await eng._ground_by_api(_state(), _cfg())

    handler.execute_api_call.assert_awaited_once()
    args, kwargs = handler.execute_api_call.call_args
    api_config = kwargs.get("api_config", args[0] if args else None)
    session_data = kwargs.get("session_data", args[1] if len(args) > 1 else None)
    form_data = kwargs.get("form_data", args[2] if len(args) > 2 else None)
    # api_config 的 endpoint/params 讀 grounding_scope（R3.3，不硬編）
    assert api_config["endpoint"] == "jgb_contracts"
    assert api_config["params"] == GSCOPE["params"]
    # session_data 含 role_id 等會話資訊（R3.1）
    assert session_data["role_id"] == 20151
    assert session_data["vendor_id"] == 7
    assert session_data["session_id"] == "s1"
    assert session_data["user_id"] == "u1"
    # slot 走 form_data 通道（R3.2）= collected_fields
    assert form_data["contract_ref"] == "基隆"


# ── endpoint/params/result_mapping 全由設定驅動（R3.3, R6.3，零合約硬編）──
@pytest.mark.req("conversational-diagnosis:6.3")
async def test_endpoint_and_mapping_from_config_not_hardcoded():
    gs = {
        "select": "api", "endpoint": "jgb_bills",
        "params": {"role_id": "{session.role_id}", "bill_no": "{form.x}"},
        "result_mapping": {"list_path": "items", "id_field": "uid", "label_field": "name"},
    }
    eng, handler = _engine({"success": True, "data": {"items": [{"uid": 9, "name": "帳單A"}]}})
    r = await eng._ground_by_api(_state(), _cfg(gscope=gs, key="bill_diag"))
    assert handler.execute_api_call.call_args[0][0]["endpoint"] == "jgb_bills"
    assert r["kind"] == "converge"  # 換端點/欄位名照樣運作（程式無合約字面）


# ── 依 result_mapping.list_path 判筆數（R3.1, R6.1）──
@pytest.mark.req("conversational-diagnosis:3.1")
async def test_one_row_converges():
    eng, _ = _engine(
        {"success": True, "data": {"data": [{"id": 1, "title": "基隆物件"}]},
         "formatted_response": "狀態：已簽約待點交"})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "converge"
    assert r.get("grounding")


@pytest.mark.req("conversational-diagnosis:3.1")
async def test_zero_rows_asks_without_candidates():
    eng, _ = _engine({"success": True, "data": {"data": []}})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "ask"
    assert "candidates" not in r
    assert r.get("answer")


@pytest.mark.req("conversational-diagnosis:6.1")
async def test_many_rows_list_candidates_via_result_mapping():
    eng, _ = _engine({"success": True, "data": {"data": [
        {"id": 1, "title": "基隆物件"}, {"id": 2, "title": "台北物件"}]}})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "ask"
    # 候選 id/label 取自 result_mapping 指定欄位（id_field/label_field）
    assert [c["id"] for c in r["candidates"]] == [1, 2]
    assert [c["label"] for c in r["candidates"]] == ["基隆物件", "台北物件"]
