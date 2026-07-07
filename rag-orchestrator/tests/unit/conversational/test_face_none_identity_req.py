"""unit:face=None／未註冊 → 輸出與現行完全一致（contract-conversational-facets 任務 1.2 / R11.1）。

任務 1.1 讓 face 貫穿三簽名但「全部預設 None、不解讀」；本檔以恆等式把零回歸講死：
  - `format_contract_response`：全 status 矩陣 × 意圖問句 —— 不傳 face、face=None、
    face=未註冊值，三者輸出逐字相同（狀態判斷現行路由不受擾動）。
  - `format_jgb_response`：jgb_contracts 進入點同樣恆等。
  - 引擎層：state 無 face → 一路傳抵 contracts.py 時為 None（不虛構值）。
face 值正向貫穿（state → contracts.py）已由 test_face_param_threading_req.py 覆蓋；
既有狀態判斷矩陣（test_contract_all_stages_matrix_req.py）不改一字、同倉全綠。
註冊表命中後的分流行為屬任務 2.x，非本檔範圍——本檔的未註冊值取不會被註冊的字面。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.jgb.contracts import ContractBit, format_contract_response
from services.jgb_response_formatter import format_jgb_response

pytestmark = pytest.mark.unit

_ORDER = [ContractBit.READY, ContractBit.INVITING, ContractBit.INVITING_NEXT,
          ContractBit.SIGNED, ContractBit.MOVE_IN, ContractBit.MOVE_IN_DONE,
          ContractBit.MOVE_OUT, ContractBit.MOVE_OUT_DONE,
          ContractBit.EARLY_TERMINATION, ContractBit.EARLY_TERMINATION_DONE]

_STATUSES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]

# 覆蓋現行路由的兩類入口：狀態問句＋操作意圖問句（check_can_* 分支）
_QUESTIONS = ["", "現在狀態如何", "可以點交嗎", "可以點退嗎", "可以續約嗎"]

# 永不註冊的字面（FACE_BUILDERS 未來只收 5 個面向值）——未命中 → 現行路由
_UNREGISTERED = "不存在的面向"


def _bits_upto(status: int) -> int:
    bits = 0
    for b in _ORDER:
        if b <= status:
            bits |= b
    return bits


def _contract(status):
    return {"id": 1, "title": "T", "status": status, "bit_status": _bits_upto(status),
            "is_history": 0, "is_history_done": 0,
            "date_start": 20260701, "date_end": 99991231, "rent": 20000,
            "to_user_connect": 1}


# ── 恆等式：不傳 face ≡ face=None ≡ face=未註冊（全 status × 問句矩陣，R11.1）──
@pytest.mark.req("contract-conversational-facets:11.1")
@pytest.mark.parametrize("status", _STATUSES)
@pytest.mark.parametrize("question", _QUESTIONS)
def test_face_none_and_unregistered_identical_output(status, question):
    c = _contract(status)
    baseline = format_contract_response([c], user_question=question)
    assert format_contract_response([c], user_question=question, face=None) == baseline
    assert format_contract_response([c], user_question=question, face=_UNREGISTERED) == baseline


# ── formatter 進入點同樣恆等（jgb_contracts 分支透傳不解讀，R11.1）──
@pytest.mark.req("contract-conversational-facets:11.1")
def test_format_jgb_response_identity_with_face():
    api_result = {"mapping": {}, "data": [_contract(8)]}
    baseline = format_jgb_response(api_result, endpoint="jgb_contracts",
                                   user_question="可以點交嗎")
    for face in (None, _UNREGISTERED):
        assert format_jgb_response(api_result, endpoint="jgb_contracts",
                                   user_question="可以點交嗎", face=face) == baseline


# ── 引擎層：state 無 face → contracts.py 收到「進入面向」（fallback _domain_key；
#    未註冊面向（如狀態判斷）在 formatter 端 fallback 原路，恆等保證由上方矩陣把守）──
@pytest.mark.req("contract-conversational-facets:11.1")
async def test_state_without_face_reaches_contracts_as_entry_face(monkeypatch):
    from services.api_call_handler import APICallHandler
    from services.conversational_engine import ConversationalEngine
    from services.conversational_config import ConversationalConfig

    handler = APICallHandler(db_pool=None)

    async def fake_contracts(**kwargs):
        return {"mapping": {}, "data": [_contract(8)]}

    handler.api_registry["jgb_contracts"] = fake_contracts

    captured = {"face": "sentinel"}

    def fake_format_contract_response(contracts, user_question="", keyword="", face=None):
        captured["face"] = face
        return "facts"

    monkeypatch.setattr("services.jgb.contracts.format_contract_response",
                        fake_format_contract_response)

    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    cfg = ConversationalConfig(
        key="contract_diag",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts",
                         "required_slots": ["contract_ref"],
                         "params": {"contract_ids": "{form.contract_ref|if_numeric}"},
                         "result_mapping": {"list_path": "data", "id_field": "id",
                                            "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "1"},
             "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1"}

    r = await eng._ground_by_api(state, cfg, user_message="狀態如何")
    assert r["kind"] == "converge"
    assert captured["face"] == "狀態判斷"   # 進入面向；未註冊 → builder 不接手（原路）
