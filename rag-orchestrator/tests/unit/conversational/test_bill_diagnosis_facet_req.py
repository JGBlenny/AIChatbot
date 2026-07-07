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


def test_other_faces_unaffected():
    """零回歸：既有四個 face builder 不受收編影響。"""
    for f in ("繳費金流排障", "帳單異常", "發票", "滯納金"):
        assert f in BILL_FACE_BUILDERS
