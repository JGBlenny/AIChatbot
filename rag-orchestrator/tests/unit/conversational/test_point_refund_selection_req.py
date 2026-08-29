"""unit：點退帳單 selection contract（`POINT_REFUND_BILL_SELECTION`，2026-08-29 授權）。

six guards（業主指定）＋ mutation：

```text
1 合約 first=type1 / second=type2 → 必須選 second（專門殺掉 data[0] 舊行為）
2 只有一筆 type=2               → 正確取得該筆 amount/status
3 沒有 type=2                   → NOT_FOUND，⛔ 不得 fallback 第一筆
4 兩筆 type=2                   → 列候選，⛔ 不得任選第一筆
5 直接給 bill id 但 type != 2    → ⛔ 不得稱為點退帳單
6 mutation：拿掉 type filter／改回 data[0] → 測試必須紅
```
⚠️ guard 6 是重點：**guard exists ≠ guard can fail**。
"""
import pytest

from services.jgb import bills as bills_mod
from services.jgb import point_refund_selection as pr
from services.jgb.bills import face_bill_response

pytestmark = pytest.mark.unit

FACE = "條件診斷：帳單"
Q = "我這份合約的點退帳單多少錢"


def _bill(bill_id, type_, title, total=1000, status=2):
    return {"id": bill_id, "type": type_, "title": title, "total": total,
            "status": status, "details": [], "date_expire": 20260930}


# ───────────────────────── guard 1：殺掉 data[0] ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:1")
def test_first_row_type1_second_type2_selects_second():
    rows = [_bill(101, 1, "2026年9月租金", total=25000),
            _bill(202, 2, "2026年9月點退結算", total=-3000)]
    out = face_bill_response("jgb_bills", rows, Q, FACE)
    assert "202" in out and "2026年9月點退結算" in out
    # ⛔ 第一筆（一般租金）的識別不得出現在答案裡
    assert "2026年9月租金" not in out
    assert "類型：點退帳單" in out


# ───────────────────────── guard 2：單筆正確取值 ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:2")
def test_single_point_refund_yields_amount_and_status():
    out = face_bill_response("jgb_bills", [_bill(202, 2, "點退結算", total=-3000)], Q, FACE)
    assert "類型：點退帳單" in out          # identity/type provenance
    assert "-3,000" in out                  # amount
    assert "狀態" in out                    # status
    # ⚠️ 三者不可斷：identity ＋ type ＋ amount/status 同時在 grounding 裡
    assert "點退結算" in out


# ───────────────────────── guard 3：沒有 type=2 ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:3")
def test_no_point_refund_bill_is_not_found_not_fallback():
    rows = [_bill(101, 1, "9月租金"), _bill(103, 3, "新增帳單")]
    out = face_bill_response("jgb_bills", rows, Q, FACE)
    assert "查無點退帳單" in out
    # ⛔ 絕不得改用第一筆代答
    assert "9月租金" not in out
    assert "類型：點退帳單" not in out


# ───────────────────────── guard 4：多筆 type=2 ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:4")
def test_multiple_point_refund_bills_list_candidates():
    rows = [_bill(201, 2, "第一次點退結算", total=-1000),
            _bill(202, 2, "第二次點退結算", total=-2000)]
    out = face_bill_response("jgb_bills", rows, Q, FACE)
    assert "找到 2 筆點退帳單" in out
    assert "201" in out and "202" in out
    assert "系統未自行選定任一筆" in out
    # ⛔ 不得已經commit到某一筆的現況
    assert "狀態：" not in out


# ─────────────────── guard 5：直接指定但 type 不符 ───────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:5")
def test_direct_bill_id_with_wrong_type_is_refused():
    out = face_bill_response("jgb_bills", [_bill(101, 1, "9月租金")], Q, FACE)
    assert "不是點退帳單" in out
    assert "一般租金" in out
    assert "類型：點退帳單" not in out


@pytest.mark.req("POINT_REFUND_BILL_SELECTION:5")
def test_missing_type_is_not_treated_as_point_refund():
    """⚠️ 缺 `type` ⛔ 不得被當成點退（未知不是通過）。"""
    row = _bill(101, 1, "看起來像點退的標題")
    row.pop("type")
    out = face_bill_response("jgb_bills", [row], Q, FACE)
    assert "不是點退帳單" in out


@pytest.mark.req("POINT_REFUND_BILL_SELECTION:5")
def test_title_saying_point_refund_is_not_identity():
    """⛔ 標題含「點退」不構成身分——身分唯一依據是 type。"""
    assert pr.is_point_refund({"title": "2026年9月點退結算", "type": 1}) is False


# ───────────────────────── 非點退意圖不受影響 ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:scope")
def test_non_point_refund_intent_keeps_legacy_path():
    """⛔ 授權只到點退——其他帳單問題行為必須**逐字不變**。"""
    rows = [_bill(101, 1, "9月租金", status=1)]
    out = face_bill_response("jgb_bills", rows, "帳單為什麼發不出去", FACE)
    assert "類型：" not in out
    assert "無法發送" in out   # legacy _diagnose_cannot_send 路徑，行為未變


# ───────────────────────── guard 6：mutation ─────────────────────────

@pytest.mark.req("POINT_REFUND_BILL_SELECTION:6")
def test_mutation_removing_type_filter_turns_red(monkeypatch):
    """把 type filter 拿掉（改成「全部都算點退」）⇒ 上面的判定必須紅。"""
    monkeypatch.setattr(pr, "is_point_refund", lambda bill: True)
    rows = [_bill(101, 1, "9月租金"), _bill(202, 2, "點退結算")]
    out = face_bill_response("jgb_bills", rows, Q, FACE)
    # 突變後兩筆都被當成點退 → 走候選路徑；guard 1「必須選 second」因此失守
    assert "找到 2 筆點退帳單" in out, "突變未改變行為 ⇒ guard 1 其實測不到 type filter"


@pytest.mark.req("POINT_REFUND_BILL_SELECTION:6")
def test_mutation_back_to_data0_turns_red(monkeypatch):
    """把 selection 改回「取第一列」⇒ guard 1 必須紅。"""
    monkeypatch.setattr(
        pr, "select_point_refund",
        lambda rows: (pr.STATE_SELECTED, (rows or [None])[0], []),
    )
    rows = [_bill(101, 1, "2026年9月租金"), _bill(202, 2, "2026年9月點退結算")]
    out = face_bill_response("jgb_bills", rows, Q, FACE)
    # 舊行為復辟 ⇒ 答案會變成第一筆（一般租金）
    assert "2026年9月租金" in out, "改回 data[0] 卻沒改變輸出 ⇒ guard 1 是假綠"
    assert "2026年9月點退結算" not in out


@pytest.mark.req("POINT_REFUND_BILL_SELECTION:6")
def test_mutation_dropping_type_fact_line_turns_red(monkeypatch):
    """拿掉 type 事實行 ⇒ grounding provenance 斷掉，guard 2 必須紅。"""
    monkeypatch.setattr(pr, "type_fact_line", lambda bill: "")
    out = face_bill_response("jgb_bills", [_bill(202, 2, "點退結算", total=-3000)], Q, FACE)
    assert "類型：點退帳單" not in out, "拿掉事實行卻仍出現 ⇒ 該行不是唯一來源"
