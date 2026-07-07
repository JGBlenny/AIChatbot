"""unit:face 透傳帳務分支＋BILL_FACE_BUILDERS 底座（billing-conversational-facets 任務 1.1 / R1.4, R7.1, R11.1）。

零回歸設計：`format_jgb_response` 於四個帳務 endpoint（jgb_bills/jgb_bill_detail/
jgb_payment_logs/jgb_invoice_logs）**face 命中註冊表才分流**至 `bills.py::face_bill_response`；
face=None/未註冊 → 原路不動（jgb_bills 維持通用格式化、其餘維持各自 diagnose 引擎）。
入口把 list 資料正規化為單列（引擎收斂本為單筆）再交 builder：(row, question) -> facts。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.jgb.bills import BILL_FACE_BUILDERS, BillFaceBuilder, face_bill_response
from services.jgb_response_formatter import format_jgb_response

pytestmark = pytest.mark.unit

_BILL = {"id": 714100, "title": "2026-07 租金", "status": 8, "total": 20000}
_ENDPOINTS = {
    "jgb_bills": [_BILL],
    "jgb_bill_detail": _BILL,
    "jgb_payment_logs": [{"id": 1, "action": "notify"}],
    "jgb_invoice_logs": [{"id": 9, "action": "開立發票"}],
}


# ── face=None／未註冊 → 四分支輸出與現行完全一致（R11.1 恆等）──
@pytest.mark.req("billing-conversational-facets:11.1")
@pytest.mark.parametrize("endpoint,data", _ENDPOINTS.items())
def test_face_none_and_unregistered_identical(endpoint, data, monkeypatch):
    api_result = {"mapping": {}, "data": data}
    baseline = format_jgb_response(api_result, endpoint=endpoint, user_question="這筆怎麼了")
    for face in (None, "沒這面向"):
        out = format_jgb_response(api_result, endpoint=endpoint,
                                  user_question="這筆怎麼了", face=face)
        assert out == baseline, f"{endpoint} face={face} 應與現行逐字相同"
    # 掛了別的面向也不影響（只有命中才分流）
    monkeypatch.setitem(BILL_FACE_BUILDERS, "測試面向", lambda row, q: "FACTS")
    assert format_jgb_response(api_result, endpoint=endpoint,
                               user_question="這筆怎麼了", face="別的") == baseline


# ── face 命中 → builder 接手：list 正規化為單列、dict 原樣（R7.1）──
@pytest.mark.req("billing-conversational-facets:7.1")
@pytest.mark.parametrize("endpoint,data,expect_row", [
    ("jgb_bills", [_BILL, {"id": 2}], _BILL),      # list → 第一列（收斂單筆）
    ("jgb_bill_detail", _BILL, _BILL),             # dict → 原樣
])
def test_face_hit_dispatches_with_normalized_row(endpoint, data, expect_row, monkeypatch):
    seen = {}

    def fake_builder(row, question):
        seen["row"], seen["q"] = row, question
        return "BILL-FACTS"

    monkeypatch.setitem(BILL_FACE_BUILDERS, "繳費金流排障", fake_builder)
    out = format_jgb_response({"mapping": {}, "data": data}, endpoint=endpoint,
                              user_question="繳了沒入帳", face="繳費金流排障")
    assert out == "BILL-FACTS"
    assert seen["row"] == expect_row and seen["q"] == "繳了沒入帳"


# ── 空資料 → 不分流（builder 無列可 ground，走原路）──
@pytest.mark.req("billing-conversational-facets:7.1")
def test_face_hit_empty_data_falls_back(monkeypatch):
    monkeypatch.setitem(BILL_FACE_BUILDERS, "繳費金流排障", lambda r, q: "FACTS")
    api_result = {"mapping": {}, "data": []}
    baseline = format_jgb_response(api_result, endpoint="jgb_bills", user_question="x")
    assert format_jgb_response(api_result, endpoint="jgb_bills",
                               user_question="x", face="繳費金流排障") == baseline


# ── 引擎 state.face 經真實 handler 一路傳抵 bills.py（R1.4；沿 contracts 同構驗證）──
@pytest.mark.req("billing-conversational-facets:1.4")
async def test_face_threads_through_real_handler_to_bills(monkeypatch):
    from services.api_call_handler import APICallHandler
    from services.conversational_engine import ConversationalEngine
    from services.conversational_config import ConversationalConfig

    handler = APICallHandler(db_pool=None)

    async def fake_bills(**kwargs):
        return {"mapping": {}, "data": [_BILL]}

    handler.api_registry["jgb_bills"] = fake_bills
    captured = {}
    monkeypatch.setitem(BILL_FACE_BUILDERS, "繳費金流排障",
                        lambda row, q: captured.update(row=row, q=q) or "FACTS")

    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    cfg = ConversationalConfig(
        key="billing_flow",
        grounding_scope={"select": "api", "endpoint": "jgb_bills",
                         "required_slots": ["bill_ref"],
                         "params": {"contract_ids": "{form.bill_ref}"},
                         "result_mapping": {"list_path": "data", "id_field": "id",
                                            "label_field": "title"}},
        topic_scope={"mode": "category", "category": "繳費金流排障"})
    state = {"config_key": "billing_flow", "collected_fields": {"bill_ref": "714100"},
             "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
             "face": "繳費金流排障"}
    r = await eng._ground_by_api(state, cfg, user_message="繳了沒入帳")
    assert r["kind"] == "converge"
    assert captured["row"]["id"] == 714100 and captured["q"] == "繳了沒入帳"


# ── 介面型別與入口存在（design 元件 2）──
@pytest.mark.req("billing-conversational-facets:7.1")
def test_interface_types_defined():
    assert isinstance(BILL_FACE_BUILDERS, dict)
    assert BillFaceBuilder is not None
    assert callable(face_bill_response)
    assert "帳單設定引導" not in BILL_FACE_BUILDERS      # 輕引導永不註冊（select=category）
