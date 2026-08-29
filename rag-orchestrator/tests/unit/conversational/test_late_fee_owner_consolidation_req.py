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


# ═════════════ Step 2：ownership consolidation（業主授權 2026-08-29）═════════════
#
# ⚠️ 業主指出的關鍵：**只刪 dispatch 不足以證明「A 不再擁有這個 intent」**——
#    它會改落 generic path，那只是「A 不再專門診斷滯納金」。
#    ⇒ 必須同時驗 execution（不再 dispatch）與 authority（不得 commit）。

from services.jgb.bills import (               # noqa: E402
    build_bill_diagnosis_facts,
    diagnose_bill,
    is_late_fee_intent,
    late_fee_exclusion_facts,
)

FACE = "條件診斷：帳單"


def _diag_row(**kw):
    r = {"id": 901, "title": "2026年8月租金", "status": 2, "total": 25000,
         "date_expire": 20260805, "details": [
             {"active": True, "label": "租金", "total_price": 25000}]}
    r.update(kw)
    return r


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
@pytest.mark.parametrize("q", [
    "這筆帳單為什麼被收滯納金",
    "這筆延遲金怎麼算",
    "我這筆為什麼有逾期費",
])
def test_late_fee_intent_is_not_answered_by_bill_diagnosis(q):
    """guard 1–3：三種 late-fee 提法，bill_diagnosis 一律**不得作答**。"""
    out = build_bill_diagnosis_facts(_diag_row(), q)
    assert out == late_fee_exclusion_facts()
    assert "滯納金" in out and "本面向不承接" in out
    # ⛔ 不得落 generic path 回答（錯誤綠燈）
    assert "• 狀態：" not in out and "收費明細" not in out
    # ⛔ 不得出現 A 的罐頭逾期說明
    assert "若超過繳費期限仍未付款" not in out


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
@pytest.mark.parametrize("q,expect", [
    ("這張帳單為什麼發不出去", "無法發送"),
    ("帳單取消不了", "無法取消"),
    ("手動到帳失敗", "無法手動到帳"),
])
def test_other_bill_diagnoses_unchanged(q, expect):
    """guard 4–6：其他 bill diagnosis ⛔ 不得被排除規則吸走。"""
    row = _diag_row(status=1, details=[]) if "發不出去" in q else _diag_row(status=64)
    out = build_bill_diagnosis_facts(row, q)
    assert out != late_fee_exclusion_facts()
    assert expect in out


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
def test_diagnose_bill_entry_also_excluded():
    """直接呼叫 `diagnose_bill` 亦不得回答 late-fee intent。"""
    assert diagnose_bill(_diag_row(), "為什麼被收逾期費") == late_fee_exclusion_facts()


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
def test_no_dispatch_reaches_superseded_engine(monkeypatch):
    """⛔ 任何 late-fee 提法都不得再抵達 `_diagnose_late_fee`。"""
    called = []
    monkeypatch.setattr(bills_mod, "_diagnose_late_fee",
                        lambda bill: called.append(1) or "SHOULD_NOT_APPEAR")
    for q in ("滯納金", "延遲金怎麼算", "逾期費", "late fee 多少"):
        out = build_bill_diagnosis_facts(_diag_row(), q)
        assert "SHOULD_NOT_APPEAR" not in out
    assert called == [], "superseded 引擎仍被呼叫 ⇒ dispatch 未真正移除"


# ───────────────────────── M1／M2 mutation ─────────────────────────

@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:M1")
def test_M1_restoring_dispatch_turns_red(monkeypatch):
    """M1：把 late-fee intent 判定關掉（等同恢復舊 dispatch 路徑）⇒ ownership guard 必須紅。"""
    monkeypatch.setattr(bills_mod, "is_late_fee_intent", lambda q: False)
    out = build_bill_diagnosis_facts(_diag_row(), "這筆帳單為什麼被收滯納金")
    assert out != late_fee_exclusion_facts(), "關掉判定卻仍排除 ⇒ guard 測不到 execution 層"


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:M2")
def test_M2_removing_authority_exclusion_turns_red(monkeypatch):
    """M2：拿掉排除 facts（authority transfer）⇒ late-fee query 會被 A 收斂回答，必須紅。"""
    monkeypatch.setattr(bills_mod, "late_fee_exclusion_facts", lambda: "")
    out = build_bill_diagnosis_facts(_diag_row(), "這筆帳單為什麼被收滯納金")
    assert out == "", "拿掉 authority 排除卻仍不作答 ⇒ 排除不是唯一來源"


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
def test_intent_predicate_keywords_frozen():
    """⚠️ 判定詞逐字沿用原 dispatch 那組——換一組＝偷偷改 ownership 邊界。"""
    assert bills_mod.LATE_FEE_INTENT_KEYWORDS == ("逾期", "延遲金", "滯納金", "late fee")
    assert all(is_late_fee_intent(k) for k in bills_mod.LATE_FEE_INTENT_KEYWORDS)
    assert not is_late_fee_intent("這張帳單為什麼發不出去")


@pytest.mark.req("LATE_FEE_OWNER_CONSOLIDATION:2A")
def test_diag_keywords_unchanged():
    """⛔ `_DIAG_KEYWORDS` 不得被動——它是 generic discriminator，⛔ 非 late-fee 宣告。"""
    for k in ("發不出", "取消", "到帳", "收據", "虛擬帳號"):
        assert k in bills_mod._DIAG_KEYWORDS
    for k in ("逾期", "延遲金", "滯納金", "late fee"):
        assert k in bills_mod._DIAG_KEYWORDS, "⚠️ 不動它是刻意的：動了會誤傷其他診斷"
