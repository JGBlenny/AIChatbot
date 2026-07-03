"""unit:face 參數貫穿三簽名（contract-conversational-facets 任務 1.1 / R2.2, R3.1, R6.1, R7.1）。

`_ground_by_api` 呼叫 `execute_api_call` 補傳 `user_input={"message": user_message}`（既有
參數通道，dict 形狀對齊 `_format_success_data` 的 `user_input.get("message")` 消費）、新增
`face=state.get("face")`；handler → `format_jgb_response` → `format_contract_response`
一路透傳不解讀。全部預設 None → 未傳時行為與現行完全一致（零回歸，任務 1.2 補矩陣）。
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
    "params": {"role_id": "{session.role_id}", "contract_ids": "{form.contract_ref|if_numeric}"},
    "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"},
}


def _cfg():
    return ConversationalConfig(
        key="contract_diag", grounding_scope=GSCOPE,
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


def _state(face=None):
    s = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "83315"},
         "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
         "asked_count": 1}
    if face is not None:
        s["face"] = face
    return s


def _engine_with_mock_handler():
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={
        "success": True, "data": {"data": [{"id": 83315, "title": "基隆物件"}]},
        "formatted_response": "狀態：已簽約"})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, handler


# ── 引擎呼叫點：face 從 state 取、user_message 走既有 user_input 通道（R7.1）──
@pytest.mark.req("contract-conversational-facets:7.1")
async def test_ground_by_api_passes_face_and_user_message():
    eng, handler = _engine_with_mock_handler()
    r = await eng._ground_by_api(_state(face="合約異動"), _cfg(),
                                 user_message="我想改租期")
    assert r["kind"] == "converge"
    kwargs = handler.execute_api_call.call_args.kwargs
    assert kwargs.get("face") == "合約異動"
    # dict 形狀對齊既有通道消費（_format_success_data 讀 user_input.get("message")）
    assert kwargs.get("user_input") == {"message": "我想改租期"}


# ── state 無 face → fallback 進入面向（第一句帶識別直收斂不經 brain 時，
#    builder 仍按進場面向接手；未註冊面向如「狀態判斷」在 formatter 端 fallback 原路）──
@pytest.mark.req("contract-conversational-facets:7.1")
async def test_ground_by_api_falls_back_to_entry_face_when_unset():
    eng, handler = _engine_with_mock_handler()
    await eng._ground_by_api(_state(), _cfg())
    kwargs = handler.execute_api_call.call_args.kwargs
    assert kwargs.get("face") == "條件診斷:合約"   # 進入面向（topic_scope.category）
    assert not kwargs.get("user_input")   # 未傳原句 → 不傳（維持現行 user_question=""）


# ── 全鏈路：face 從引擎 state 經真實 handler/formatter 傳抵 contracts.py（R2.2, R3.1, R6.1）──
@pytest.mark.req("contract-conversational-facets:2.2")
async def test_face_threads_through_real_handler_to_contracts(monkeypatch):
    handler = APICallHandler(db_pool=None)   # 自訂代碼路徑（不需 DB / 不打網路）

    async def fake_contracts(**kwargs):
        # jgb 形狀（無 'message'/'formatted_response'）→ 走 format_jgb_response 分支
        return {"mapping": {}, "data": [{"id": 83315, "title": "基隆物件", "status": 8}]}

    handler.api_registry["jgb_contracts"] = fake_contracts

    captured = {}

    def fake_format_contract_response(contracts, user_question="", keyword="", face=None):
        captured["face"] = face
        captured["user_question"] = user_question
        return "facts"

    # _format_contracts 於呼叫時 import → patch 模組屬性即生效
    monkeypatch.setattr("services.jgb.contracts.format_contract_response",
                        fake_format_contract_response)

    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    r = await eng._ground_by_api(_state(face="退租收尾"), _cfg(),
                                 user_message="退租卡在哪一步")
    assert r["kind"] == "converge"
    assert captured["face"] == "退租收尾"
    assert captured["user_question"] == "退租卡在哪一步"


# ── 簽名相容：三簽名皆收 face 且預設 None（不傳照舊可呼叫，R7.1）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_signatures_accept_face_defaulting_none():
    import inspect
    from services.jgb_response_formatter import format_jgb_response
    from services.jgb.contracts import format_contract_response

    for fn in (APICallHandler.execute_api_call, format_jgb_response, format_contract_response):
        p = inspect.signature(fn).parameters.get("face")
        assert p is not None, f"{fn.__qualname__} 缺 face 參數"
        assert p.default is None
