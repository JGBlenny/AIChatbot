"""unit:API grounding 參數映射 — slot 經 form_data 通道（conversational-diagnosis 任務 4.3 / R3.1, R3.2）。

驗證 `_ground_by_api` 把 `collected_fields` 當 form_data 傳入「真實」`APICallHandler`，由既有
`_prepare_params`/`_resolve_param_value`（不另寫、重用，R3.2）正確解析模板：
  - `{session.role_id}` → session_data.role_id（R3.1）
  - `{form.contract_ref|if_numeric}` → 數字 slot → contract_ids（文字則濾除）
  - `{form.contract_ref|if_text}`    → 文字 slot → keyword（數字則濾除）
僅 stub registry 的端點函式以擷取解析後參數，不打真實網路。

備註：1/0/N/例外四路與 result_mapping 零合約硬編，已由 test_ground_by_api_req.py（4.1）
與 test_ground_by_api_three_way_req.py（4.2）覆蓋（同 spec 需求標記）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.api_call_handler import APICallHandler
from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


GSCOPE = {
    "select": "api",
    "endpoint": "jgb_contracts",
    "required_slots": ["contract_ref"],
    "params": {
        "role_id": "{session.role_id}",
        "contract_ids": "{form.contract_ref|if_numeric}",
        "keyword": "{form.contract_ref|if_text}",
    },
    "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"},
}


def _cfg():
    return ConversationalConfig(
        key="contract_diag", grounding_scope=GSCOPE,
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


def _state(contract_ref):
    return {"config_key": "contract_diag", "collected_fields": {"contract_ref": contract_ref},
            "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
            "asked_count": 1}


def _engine_capturing_params():
    """真實 APICallHandler + stub 端點函式（擷取解析後參數，回單筆假資料）。"""
    handler = APICallHandler(db_pool=None)  # 走自訂代碼路徑（不需 DB / 不打網路）
    captured = {}

    async def fake_contracts(**kwargs):
        captured.update(kwargs)
        # 帶 'message' 使格式化走早返回分支，避開 jgb 專屬 formatter
        return {"message": "查詢成功", "data": [{"id": 1, "title": "基隆物件"}]}

    handler.api_registry["jgb_contracts"] = fake_contracts
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, captured


@pytest.mark.req("conversational-diagnosis:3.2")
async def test_numeric_slot_resolves_to_contract_ids_via_form_channel():
    eng, captured = _engine_capturing_params()
    r = await eng._ground_by_api(_state("12345"), _cfg())
    assert r["kind"] == "converge"           # 1 筆收斂（鏈路全通）
    assert captured["contract_ids"] == "12345"   # if_numeric 命中
    assert "keyword" not in captured             # if_text 濾除（值為數字）
    assert captured["role_id"] == 20151          # session.role_id（R3.1）


@pytest.mark.req("conversational-diagnosis:3.2")
async def test_text_slot_resolves_to_keyword_via_form_channel():
    eng, captured = _engine_capturing_params()
    r = await eng._ground_by_api(_state("基隆"), _cfg())
    assert r["kind"] == "converge"
    assert captured["keyword"] == "基隆"          # if_text 命中
    assert "contract_ids" not in captured        # if_numeric 濾除（值非數字）
    assert captured["role_id"] == 20151


@pytest.mark.req("conversational-diagnosis:3.1")
async def test_session_role_id_passed_through_session_data():
    eng, captured = _engine_capturing_params()
    await eng._ground_by_api(_state("基隆"), _cfg())
    assert captured["role_id"] == 20151          # 會話資訊走 session_data 通道
