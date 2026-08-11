"""unit：條件診斷：帳單 面向收編（系統回測 run307「帳單發不出去」死路逼出）。

真相：帳務域五面向皆有對話規則，唯「條件診斷：帳單」（知識 3495/3496/3498/3499）
漏 seed → 進場判定查無 config → 落回 v1.1 表單（只收帳單編號）→ 無編號死路。
修法沿合約診斷先例：seed 規則（識別鏈抄繳費金流排障 3915）＋formatter face 出口
重用決定性 diagnose_bill 引擎（B01–B04 keyword 分流），引擎與診斷邏輯零改動。
"""
import pytest

from services.jgb.bills import BILL_FACE_BUILDERS, face_bill_response

pytestmark = pytest.mark.unit

FACE = "條件診斷：帳單"


def _bill(**kw):
    base = {"id": 555, "title": "重慶北137-503 2026-06 房租", "status": 2}
    base.update(kw)
    return base


def test_face_registered():
    """face 註冊表必須有「條件診斷：帳單」builder——這是收編的程式側唯一缺口。"""
    assert FACE in BILL_FACE_BUILDERS


def test_cannot_send_already_sent_deterministic():
    """B01：已發送（status=2）問發不出去 → 決定性回「不在待發送階段」。"""
    out = face_bill_response("jgb_bills", [_bill(status=2)], "帳單為什麼發不出去", FACE)
    assert out is not None
    assert "不在待發送階段" in out


def test_cannot_send_draft_missing_details():
    """B01：草稿（status=1）無明細 → 列出阻擋原因（收費項目）。"""
    out = face_bill_response("jgb_bills", [_bill(status=1, details=[])],
                             "帳單發不出去", FACE)
    assert "無法發送" in out and "收費項目" in out


def test_manual_complete_routes_by_keyword():
    """B04：手動到帳問法 → keyword 分流至 manual_complete 診斷（非發送診斷）。"""
    out = face_bill_response("jgb_bills", [_bill(status=2)],
                             "帳單手動到帳失敗", FACE)
    assert out is not None and "不在待發送階段" not in out


def test_secondary_detail_attached_is_merged():
    """secondary_call 附掛的 bill_detail 應併回主列再判定——
    列表列常缺 details/status 細節，診斷要用 detail 的值。"""
    row = {"id": 555, "title": "重慶北137-503 2026-06 房租",
           "bill_detail": {"status": 2}}
    out = face_bill_response("jgb_bills", [row], "帳單為什麼發不出去", FACE)
    assert "不在待發送階段" in out          # 用 detail 的 status=2 而非缺值


def test_candidate_pick_turn_emits_full_verdicts():
    """收斂輪的 user_message 常是「1」（選序號）——無症狀關鍵字時必須輸出
    全判定 facts（發送/取消/手動到帳），原句症狀由 LLM 從對話脈絡選答；
    否則只回通用狀態描述，答不到「為什麼發不出去」（e2e v3 實測）。"""
    out = face_bill_response("jgb_bills", [_bill(status=2)], "1", FACE)
    assert "發送" in out and "取消" in out and "到帳" in out


def test_cancel_verdict_ready_is_cancellable():
    """B02 勘誤（客服回報批次20260731 R-33 同源）：應到帳(status=2)可收回——
    jgb2 Bill::canCancel 只認 BILL_READY(2)/BILL_PREPARE_TO_READY(32)，
    舊解碼「只有待發送能取消」方向相反。"""
    out = face_bill_response("jgb_bills", [_bill(status=2)], "帳單可以取消嗎", FACE)
    assert "可以取消" in out
    assert "只有「待發送」狀態的帳單才能取消" not in out


def test_cancel_verdict_scheduled_is_cancellable():
    """B02：排定發送(status=32)同樣可取消。"""
    out = face_bill_response("jgb_bills", [_bill(status=32)], "帳單取消不了", FACE)
    assert "可以取消" in out


def test_cancel_verdict_draft_needs_no_cancel():
    """B02：待發送(status=1)是草稿——沒有「取消」可言，應導向直接編輯/失效。"""
    out = face_bill_response("jgb_bills", [_bill(status=1)], "帳單可以取消嗎", FACE)
    assert "不需要取消" in out or "直接編輯" in out


def test_cancel_verdict_paid_not_cancellable():
    """B02：待對帳(8)/已到帳(16)——款項已進流程，不能收回。"""
    for st in (8, 16):
        out = face_bill_response("jgb_bills", [_bill(status=st)], "帳單為什麼取消不了", FACE)
        assert "無法取消" in out and "不能收回" in out


def test_receipt_unpaid_says_no_receipt_yet():
    """B05 收據判定（客服回報 R-31／情境回測 D-1 逼出）：未繳費（status=2）問收據
    → 明說「尚未繳費、尚無收據」，不得沉默改答帳單金額。"""
    out = face_bill_response("jgb_bills", [_bill(status=2, total=28500)],
                             "這張帳單的收據金額是多少", FACE)
    assert "尚無收據" in out or "還沒有收據" in out


def test_receipt_paid_gives_receipt_amount():
    """B05：已繳費（status=16）問收據 → 給收據金額與下載出口。"""
    out = face_bill_response("jgb_bills",
                             [_bill(status=16, total=28500, final_total=28500)],
                             "收據金額是多少", FACE)
    assert "收據" in out and "28,500" in out


def test_receipt_paid_zero_final_total_uses_bill_total():
    """B05（20260810 真對話重播 P1-a，帳單 716317 實案）：已繳費但 final_total=0
    （後台手動標記到帳、未填實收），舊碼 `get("final_total", total)` 因 key 存在而
    直接吐「NT$ 0」——錯誤實值比查無更傷。

    jgb2 真相：收據 PDF 金額由 feeDetails 合計（即 total）而來（Bill::generateGeneralReceiptPdf）；
    final_total 是「實收金額」，後台以 `final_total > 0 ? : '尚未付款'` 呈現
    （Admin/BillController），且 External/BillApiController 把 null 轉成 (float) 0，
    RAG 側分不出 null 與 0 → 一律以 >0 為有效實收。"""
    out = face_bill_response("jgb_bills",
                             [_bill(status=16, total=3999996, final_total=0)],
                             "收據金額是多少", FACE)
    assert "NT$ 0" not in out
    assert "3,999,996" in out


def test_receipt_paid_final_total_differs_flags_actual_received():
    """B05：實收金額（final_total>0）與帳單金額不符時，收據金額仍以帳單明細合計為準，
    但必須把實收金額一併說明，不可沉默吞掉差額。"""
    out = face_bill_response("jgb_bills",
                             [_bill(status=16, total=28500, final_total=28000)],
                             "收據金額是多少", FACE)
    assert "28,500" in out and "28,000" in out


def test_other_faces_unaffected():
    """零回歸：既有四個 face builder 不受收編影響。"""
    for f in ("繳費金流排障", "帳單異常", "發票", "滯納金"):
        assert f in BILL_FACE_BUILDERS
