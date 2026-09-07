"""unit：確認卡的決定性 render（子 spec `agent-write-tools` W2｜DSP-038-2｜R4.2）。

⚠️ 本檔守的是「使用者看到的字」與「將被執行的 payload」之間**沒有縫**：
   卡只從 payload 導出、同 payload 必得同字串、缺欄位大聲失敗。
"""
from __future__ import annotations

import pytest

from services.agent.confirm_card import (
    CARD_FOOTER,
    CONFIRM_ACTIONS,
    EMPTY_DESCRIPTION_ZH,
    ACTION_FAILED_TEXT,
    ConfirmCardError,
    receipt_id_of,
    render,
    render_receipt,
)

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.2"

_BILL = {
    "action": "bill_due_extend",
    "bill_id": "900001",
    "date_expire_before": "20260815",
    "days": 3,
    "date_expire_after": "20260818",
}

_REPAIR = {
    "action": "repair_create",
    "estate_name": "松江路一段 5 號 3F",
    "category_name": "水電",          # 父節點（大類）也收
    "description": "熱水器沒有熱水",
    "emergency_status": 2,
}


@pytest.mark.req(_REQ)
def test_bill_due_extend_card_shape():
    card = render("bill_due_extend", _BILL)
    assert card == (
        "即將調整帳單到期日，請確認：\n"
        "・帳單編號：900001\n"
        "・原到期日：2026/08/15\n"
        "・延後天數：3 天\n"
        "・新到期日：2026/08/18\n"
        + CARD_FOOTER
    )


@pytest.mark.req(_REQ)
def test_repair_create_card_shape():
    card = render("repair_create", _REPAIR)
    assert card == (
        "即將建立修繕單，請確認：\n"
        "・物件：松江路一段 5 號 3F\n"
        "・修繕分類：水電\n"
        "・急迫程度：緊急\n"
        "・問題描述：熱水器沒有熱水\n"
        + CARD_FOOTER
    )


@pytest.mark.req(_REQ)
def test_same_payload_renders_the_same_card_regardless_of_key_order():
    """決定性：鍵順序不同、內容相同 ⇒ 同一個字串（雜湊才對得上）。"""
    reordered = dict(reversed(list(_BILL.items())))
    assert render("bill_due_extend", reordered) == render("bill_due_extend", _BILL)
    assert render("bill_due_extend", _BILL) == render("bill_due_extend", dict(_BILL))


@pytest.mark.req(_REQ)
def test_changing_any_field_changes_the_card():
    """改任一欄 ⇒ 卡不同 ⇒ `summary_sha256` 不同 ⇒ 兌現時比對得出來。"""
    base = render("bill_due_extend", _BILL)
    variants = [
        {**_BILL, "bill_id": "900002"},
        {**_BILL, "days": 4, "date_expire_after": "20260819"},
        {**_BILL, "date_expire_before": "20260816", "date_expire_after": "20260819"},
    ]
    for v in variants:
        assert render("bill_due_extend", v) != base, v


@pytest.mark.req(_REQ)
def test_repair_accepts_parent_category_and_empty_description():
    """line-bot 線③：分類樹涵蓋不到 ⇒ 退回大類；描述留空 ⇒ 照樣開得成單。
    ⛔ 卡上不得憑空補一個葉節點或一段描述。"""
    payload = {**_REPAIR, "category_name": "其他", "description": ""}
    card = render("repair_create", payload)
    assert "・修繕分類：其他" in card
    assert f"・問題描述：{EMPTY_DESCRIPTION_ZH}" in card
    # 只有空白也算空
    assert render("repair_create", {**payload, "description": "   "}) == card


@pytest.mark.req(_REQ)
def test_emergency_status_labels_match_production_truth_table():
    """`emergency_status` 是已知地雷（jgb2 對外 mapping 曾標反）。
    本檔的對照表必須與產線 formatter 的自家真值表逐鍵相同——⛔ 兩邊不得分岔。

    正對照組：先確認產線那張表真的存在且有這兩個鍵（否則下面的比對是空跑）。
    """
    from services.jgb_response_formatter import _EMERGENCY_STATUS_LABELS

    assert set(_EMERGENCY_STATUS_LABELS) == {"1", "2"}          # 正對照組
    for value, label in _EMERGENCY_STATUS_LABELS.items():
        payload = {**_REPAIR, "emergency_status": int(value)}
        assert f"・急迫程度：{label}" in render("repair_create", payload), value


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("missing", sorted(set(_BILL) - {"action"}))
def test_bill_missing_any_field_raises(missing):
    payload = {k: v for k, v in _BILL.items() if k != missing}
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend", payload)


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("missing", sorted(set(_REPAIR) - {"action"}))
def test_repair_missing_any_field_raises(missing):
    payload = {k: v for k, v in _REPAIR.items() if k != missing}
    with pytest.raises(ConfirmCardError):
        render("repair_create", payload)


@pytest.mark.req(_REQ)
def test_inconsistent_dates_raise_instead_of_picking_one():
    """`before + days != after` ⇒ raise。⛔ 不挑一個印——那等於替使用者決定
    他同意的是哪一個數字。"""
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend", {**_BILL, "date_expire_after": "20260901"})
    # 正對照組：改成一致就過（證明上面的 raise 不是恆真）
    render("bill_due_extend", {**_BILL, "days": 17, "date_expire_after": "20260901"})


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("bad", [
    {"action": "bill_due_extend", **{k: v for k, v in _BILL.items() if k != "action"}, "days": "3"},
    {**_BILL, "days": 0},
    {**_BILL, "days": -1, "date_expire_after": "20260814"},
    {**_BILL, "date_expire_before": "2026-08-15"},
    {**_BILL, "date_expire_before": "20260899"},
    {**_BILL, "bill_id": ""},
    {**_BILL, "bill_id": True},
])
def test_bill_bad_field_shapes_raise(bad):
    if bad == _BILL:
        pytest.fail("參數化案例與合法 payload 相同——這條測試會空跑")
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend", bad)


@pytest.mark.req(_REQ)
def test_repair_rejects_out_of_range_emergency_status():
    for bad in (0, 3, "2", True, None):
        with pytest.raises(ConfirmCardError):
            render("repair_create", {**_REPAIR, "emergency_status": bad})


@pytest.mark.req(_REQ)
def test_unknown_action_and_non_object_payload_raise():
    for action in ("", None, "delete_everything", "BILL_DUE_EXTEND"):
        with pytest.raises(ConfirmCardError):
            render(action, _BILL)
    for payload in (None, "{}", [1, 2], 3):
        with pytest.raises(ConfirmCardError):
            render("bill_due_extend", payload)


@pytest.mark.req(_REQ)
def test_action_enum_and_renderer_table_stay_in_sync():
    """每個值域內的 action 都 render 得出東西（⛔ 不得有「有值域沒分支」的 action）。"""
    assert set(CONFIRM_ACTIONS) == {"bill_due_extend", "repair_create"}
    assert render("bill_due_extend", _BILL)
    assert render("repair_create", _REPAIR)


# ---------------------------------------------------------------------------
# 執行後的回覆句
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_render_receipt_uses_payload_not_receipt_free_text():
    """句子只從 `action`＋`payload` 導出；receipt 只貢獻一個形狀安全的識別碼。
    ⛔ receipt 裡的自由文字不得出現在回覆裡。"""
    receipt = {"id": "BILL-77", "message": "<script>惡意訊息</script>", "note": "下游備註"}
    text = render_receipt("bill_due_extend", _BILL, receipt)
    assert text == "已將帳單 900001 的到期日延至 2026/08/18。（單號 BILL-77）"
    assert "惡意訊息" not in text and "下游備註" not in text

    repair_text = render_receipt("repair_create", _REPAIR, {"repair_id": 5566})
    assert repair_text == "已為「松江路一段 5 號 3F」建立修繕單。（單號 5566）"


@pytest.mark.req(_REQ)
def test_receipt_id_only_accepts_safe_shapes():
    assert receipt_id_of({"id": "R-1"}) == "R-1"
    assert receipt_id_of({"id": 12}) == "12"
    # 形狀不合 ⇒ 不採用（那多半是一段訊息，不是識別碼）
    assert receipt_id_of({"id": "R 1 建立成功"}) == ""
    assert receipt_id_of({"id": "x" * 65}) == ""
    assert receipt_id_of({"id": ""}) == ""
    assert receipt_id_of({"id": True}) == ""
    assert receipt_id_of(None) == ""
    assert receipt_id_of({"other": "R-1"}) == ""


@pytest.mark.req(_REQ)
def test_render_receipt_degrades_without_raising():
    """payload 殘缺 ⇒ 退保底句，⛔ 不在回合末端丟例外把一次成功的寫入變成錯誤。"""
    assert render_receipt("bill_due_extend", {}, {}) == "已完成這筆帳單到期日調整。"
    assert render_receipt("repair_create", {}, {}) == "已建立修繕單。"
    assert render_receipt("unknown", {}, {"id": "Z1"}) == "已完成這筆操作。（單號 Z1）"


@pytest.mark.req(_REQ)
def test_failure_sentence_is_the_plan_literal():
    """⛔ 不加「請稍後再試」之類的補語（我們並不知道重試會不會成功）。"""
    assert ACTION_FAILED_TEXT == "這筆操作目前無法執行"
