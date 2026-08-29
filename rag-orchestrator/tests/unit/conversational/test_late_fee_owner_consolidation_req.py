"""unit：late-fee owner 收斂 **Step 1**——把 `pay_at`／`complete_at` 搬進 B。

背景（T1 決定性比對）：`_diagnose_late_fee`（A）是同責任面的 **partial
implementation**，唯一 genuine 的獨有能力就是印出付款／到帳時間；
其餘 A-only 項目經查為缺陷（把合約列叫成帳單、認不出滯納金帳單）或量尺誤判。
⇒ 收斂 owner 到 `build_late_fee_facts`（B）之前，必須先補這項，否則收斂＝丟能力。

業主指定的 5 組 guard 全數在此，⚠️ 含 mutation（guard exists ≠ guard can fail）。
"""
import pytest

from services.jgb import bills as bills_mod
from services.jgb.bills import build_late_fee_facts

pytestmark = pytest.mark.unit


def _bill(**kw):
    b = {"id": 901, "title": "2026年8月租金", "status": 2, "total": 25000,
         "date_expire": 20260805,
         "details": [{"active": True, "label": "租金", "total_price": 25000}]}
    b.update(kw)
    return b


# ───────────────────────── guard 1：已付款必須保留時間 ─────────────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:1")
def test_paid_bill_keeps_payment_and_settlement_time():
    out = build_late_fee_facts(_bill(status=16, date_expire=20260705,
                                     pay_at="2026-07-20 10:00:00",
                                     complete_at="2026-07-21 09:00:00"))
    assert "2026-07-20 10:00:00" in out
    assert "2026-07-21 09:00:00" in out
    # ⚠️ 收斂不得丟掉 B 原有的能力
    assert "狀態：已繳費" in out and "NT$ 25,000" in out


# ───────────────────────── guard 2：未付款不得偽造 ─────────────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2")
def test_unpaid_bill_never_fabricates_payment_time():
    out = build_late_fee_facts(_bill(status=2, date_expire=20260705))
    assert "繳費時間" not in out
    assert "到帳時間" not in out


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2")
def test_only_present_fields_are_emitted():
    """只有 complete_at ⇒ ⛔ 不得憑空生出繳費時間。"""
    out = build_late_fee_facts(_bill(status=16, complete_at="2026-07-21 09:00:00"))
    assert "到帳時間：2026-07-21 09:00:00" in out
    assert "租客繳費時間" not in out


# ─────────────────── guard 3：滯納金帳單身分不得退化 ───────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:3")
def test_late_fee_bill_identity_survives():
    out = build_late_fee_facts(_bill(
        id=902, title="2026年7月延遲金", type=4, total=1250, status=2,
        date_expire=20260731,
        late_fee_info={"note": "租金 25000 × 遲繳 10 天 × 0.5% = 1,250"}))
    assert "系統結算備註（原樣）：租金 25000 × 遲繳 10 天 × 0.5% = 1,250" in out
    assert "每張逾期帳單各自結算、不累加" in out
    # ⛔ 不得繼承 A 的錯誤語義（把滯納金帳單當成「之後還會被收滯納金」）
    assert "若超過繳費期限仍未付款" not in out


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:3")
def test_paid_late_fee_bill_shows_both():
    out = build_late_fee_facts(_bill(
        id=902, title="2026年7月延遲金", type=4, total=1250, status=16,
        pay_at="2026-08-01 08:00:00", late_fee_info={"note": "備註"}))
    assert "系統結算備註" in out and "2026-08-01 08:00:00" in out


# ─────────────────── guard 4：合約設定 facts 不變 ───────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:4")
def test_contract_settings_unchanged():
    out = build_late_fee_facts({"id": 77, "title": "忠孝東路 3F 租約",
                                "enable_late_fee": True, "late_fee_percent": 5,
                                "calc_late_fee_buffer_days": 3})
    assert "費率 5%" in out and "緩衝 3 天" in out
    assert "付款後結算的延遲金" in out and "排程開單" in out
    # ⚠️ 合約列沒有付款時間語義 ⇒ ⛔ 不得出現
    assert "繳費時間" not in out and "到帳時間" not in out


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:4")
def test_contract_late_fee_disabled_unchanged():
    out = build_late_fee_facts({"id": 78, "title": "測試租約", "enable_late_fee": False})
    assert "未啟用" in out


# ───────────────────────── guard 5：mutation ─────────────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:5")
def test_mutation_removing_payment_projection_turns_red(monkeypatch):
    """拿掉 pay_at／complete_at 的投影 ⇒ guard 1 必須紅。"""
    monkeypatch.setattr(bills_mod, "_payment_time_lines", lambda bill: [])
    out = build_late_fee_facts(_bill(status=16, pay_at="2026-07-20 10:00:00",
                                     complete_at="2026-07-21 09:00:00"))
    assert "2026-07-20 10:00:00" not in out, "移除投影卻仍輸出 ⇒ guard 1 是假綠"
    assert "2026-07-21 09:00:00" not in out
