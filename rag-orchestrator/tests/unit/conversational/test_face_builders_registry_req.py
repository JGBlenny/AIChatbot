"""unit:FACE_BUILDERS 註冊表接入 format_contract_response（contract-conversational-facets 任務 2.1 / R7.1, R11.1）。

face 命中註冊表 → 該面向 fact-builder 接手（收 (matched_row, user_question)、回 facts 文字）；
未命中/None → 現行意圖關鍵字/狀態路由（零回歸，恆等已由 test_face_none_identity_req.py 矩陣講死）。
含 `CheckResult`／`FaceBuilder` 型別定義（design.md 元件 2 介面）。
「狀態判斷」永不註冊 → 既有面向天然走 fallback。
"""
import pytest

from services.jgb.contracts import (FACE_BUILDERS, CheckResult, FaceBuilder,
                                    format_contract_response)

pytestmark = pytest.mark.unit


def _contract(status=8, cid=83315, title="基隆物件"):
    return {"id": cid, "title": title, "status": status, "bit_status": 15,
            "is_history": 0, "date_start": 20260701, "date_end": 99991231,
            "rent": 20000, "to_user_connect": 1}


# ── face 命中 → builder 接手：收 (匹配列, 原句)、回傳值即回應（R7.1）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_face_hit_dispatches_to_builder(monkeypatch):
    seen = {}

    def fake_builder(row, question):
        seen["row"], seen["question"] = row, question
        return "FACTS"

    monkeypatch.setitem(FACE_BUILDERS, "測試面向", fake_builder)
    out = format_contract_response([_contract()], user_question="我想改租期",
                                   face="測試面向")
    assert out == "FACTS"
    assert seen["row"]["id"] == 83315
    assert seen["question"] == "我想改租期"


# ── keyword 過濾先於分發：builder 收到的是匹配列，不是第一列（R7.1）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_keyword_filter_applies_before_builder(monkeypatch):
    monkeypatch.setitem(FACE_BUILDERS, "測試面向",
                        lambda row, q: f"ID:{row['id']}")
    rows = [_contract(cid=1, title="台北物件"), _contract(cid=2, title="基隆物件")]
    out = format_contract_response(rows, keyword="基隆", face="測試面向")
    assert out == "ID:2"


# ── face 未命中/None → 現行路由（狀態回應照舊，R11.1）──
@pytest.mark.req("contract-conversational-facets:11.1")
def test_face_miss_falls_back_to_existing_routing(monkeypatch):
    monkeypatch.setitem(FACE_BUILDERS, "測試面向", lambda row, q: "FACTS")
    baseline = format_contract_response([_contract()], user_question="狀態如何")
    for face in (None, "沒這面向"):
        assert format_contract_response([_contract()], user_question="狀態如何",
                                        face=face) == baseline
    assert "目前狀態" in baseline   # 走的是現行狀態回應，不是 builder


# ── 「狀態判斷」不註冊 → 既有面向天然 fallback（零回歸鐵律，R11.1）──
@pytest.mark.req("contract-conversational-facets:11.1")
def test_status_face_never_registered():
    assert "狀態判斷" not in FACE_BUILDERS


# ── 0 筆/keyword 無匹配 → 既有「查無」訊息優先於 builder（builder 必須有列可 ground）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_no_rows_returns_existing_message_even_with_face(monkeypatch):
    monkeypatch.setitem(FACE_BUILDERS, "測試面向", lambda row, q: "FACTS")
    assert "查無合約資料" in format_contract_response([], face="測試面向")
    out = format_contract_response([_contract(title="台北物件")],
                                   keyword="高雄", face="測試面向")
    assert "查無符合" in out


# ── 介面型別存在且形狀正確（design.md 元件 2）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_interface_types_defined():
    assert set(CheckResult.__annotations__) == {"ok", "reasons", "facts"}
    assert callable(FaceBuilder) or FaceBuilder is not None   # Callable alias
    assert isinstance(FACE_BUILDERS, dict)
