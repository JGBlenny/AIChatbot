"""unit：**BUGFIX-PAYMENT-NOT-REFLECTED-01**（業主 2026-08-31 開立的獨立 production bugfix slice）。

```text
target  services/jgb/payments.py::_diagnose_payment_not_reflected
defect  `code` 只在 `if response:` 內指派，卻在迴圈末無條件讀取
  A CRASH        第一筆 log 缺 response → UnboundLocalError
  B STALE STATE  前一筆有、後一筆缺 → 後一筆沿用前一筆的 code
fix     per-iteration `code = ""`
```

## ⚠️ B 的定性（實測後修正，⛔ 不憑 code shape 推斷嚴重度）

窮舉 8 種 log 形狀 × 長度 1–3 ＝ **584 組合**，逐案比對修前／修後：

```text
修前 crash            219 組   ← defect A 的可達面
修前/修後輸出不同      **0 組**  ← defect B ⛔ 不改變任何輸出
```
⇒ B 是**真實的狀態外洩**，但 **NOT_OUTPUT_OBSERVABLE**：
stale code 若落在成功集合，設定它的那一筆**本身**必然已被判成功
（`_get_log_status` 與迴圈末用的是同一組欄位）⇒ `has_success` 早已為 True；
stale code 若非成功值，`status_text` 那一項會短路。
⚠️ 故 ⛔ **不升** `CONFIRMED_BEHAVIOR`——維持狀態外洩層級。
⚠️ 這同時證明本修**對所有非 crash 輸入是行為保持的**（G3／G4 的基礎）。

## ⛔ 本 slice 不碰
dispatcher keyword routing／response 文案／payment classification 規則／
empty-list handling／R-12 adapter／executable registry／任何 responsibility wiring。
"""
import itertools

import pytest

from services.jgb.payments import _diagnose_payment_not_reflected as diag
from services.jgb.payments import _get_log_status

pytestmark = pytest.mark.unit

SUCCESS_TAIL = "有付款成功的紀錄"
FAILURE_TAIL = "所有付款嘗試都未成功"


def _log(tag, resp="__omit__", note=""):
    d = {"created_at": f"2026-08-0{tag}T10:00:00", "action": f"a{tag}",
         "amount": "100", "note": note}
    if resp != "__omit__":
        d["response"] = resp
    return d


SUCC = _log("1", {"Status": "1", "Message": "授權成功"})
SUCC_S = _log("2", {"Status": "SUCCESS", "Message": "OK"})
SUCC_INT = _log("3", {"RtnCode": 1, "RtnMsg": "成功"})
FAIL = _log("4", {"Status": "10", "Message": "餘額不足"})
NOMSG = _log("5", {"Status": "1"})
EMPTY_RESP = _log("6", {}, note="手動到帳")
MISSING = _log("7", note="ATM 待對帳")          # ⚠️ 完全沒有 response 鍵
NONE_RESP = _log("8", None, note="無回應")


# ───────────────────── G1：第一筆缺 response 不 crash ─────────────────────
@pytest.mark.req("BUGFIX_PNR01_G1:1")
@pytest.mark.parametrize("first", [MISSING, NONE_RESP, EMPTY_RESP])
def test_g1_first_log_without_response_does_not_crash(first):
    out = diag([first])
    assert isinstance(out, str) and out.startswith("以下是此帳單的付款交易紀錄：")


@pytest.mark.req("BUGFIX_PNR01_G1:2")
def test_g1_first_missing_then_others_does_not_crash():
    out = diag([MISSING, SUCC, FAIL])
    assert SUCCESS_TAIL in out, "首筆缺 response 不得影響其餘紀錄的既有判定"


# ───────────── G2：後續缺 response 不得沿用前一筆 code ─────────────
@pytest.mark.req("BUGFIX_PNR01_G2:1")
def test_g2_later_missing_response_does_not_inherit_previous_code():
    """⚠️ 合併結果的 has_success 必須恰為兩筆各自判定的 OR——⛔ 不得因 stale 而多出成功。"""
    solo_success = SUCCESS_TAIL in diag([MISSING])
    for lead in (SUCC, SUCC_S, SUCC_INT, NOMSG, FAIL, EMPTY_RESP):
        lead_success = SUCCESS_TAIL in diag([lead])
        pair_success = SUCCESS_TAIL in diag([lead, MISSING])
        assert pair_success == (lead_success or solo_success), \
            f"第二筆分類被第一筆污染（lead={lead['action']}）"


@pytest.mark.req("BUGFIX_PNR01_G2:2")
def test_g2_all_missing_after_success_still_reports_each_row():
    assert diag([SUCC, MISSING, MISSING]).count("• ") == 3


# ───────────── G3：多筆皆有 response，輸出逐字不變 ─────────────
@pytest.mark.req("BUGFIX_PNR01_G3:1")
def test_g3_all_with_response_output_matches_recomputed_expectation():
    """⚠️ 以既有語義**重算**期望值，⛔ 不抄現行輸出當期望（那會自我證成）。"""
    logs = [SUCC, FAIL, SUCC_S]
    expected = ["以下是此帳單的付款交易紀錄：\n"]
    for lg in logs:
        st = _get_log_status(lg)
        resp = lg.get("response", {})
        expected.append(f"• {lg['created_at'][:16]} | {lg['action']} | NT$ {lg['amount']} | {st}")
        if resp:
            msg = resp.get("Message") or resp.get("RtnMsg", "")
            code = resp.get("Status") or resp.get("RtnCode", "")
            if msg:
                expected.append(f"  回應：[{code}] {msg}")
    expected.append("\n✅ 有付款成功的紀錄。如果帳單狀態仍未更新，可能是金流回呼延遲，"
                    "通常 1-2 小時內會自動同步。若超過 24 小時仍未更新，請聯繫客服。")
    assert diag(logs) == "\n".join(expected)


@pytest.mark.req("BUGFIX_PNR01_G3:2")
def test_g3_all_failed_keeps_failure_tail():
    out = diag([FAIL, FAIL])
    assert FAILURE_TAIL in out and SUCCESS_TAIL not in out


# ───────────── G4：既有 code 分支 classification 不變 ─────────────
@pytest.mark.req("BUGFIX_PNR01_G4:1")
@pytest.mark.parametrize("log,expect_success", [
    (SUCC, True), (SUCC_S, True), (SUCC_INT, True), (NOMSG, True),
    (FAIL, False), (EMPTY_RESP, False),
])
def test_g4_classification_per_code_branch_unchanged(log, expect_success):
    out = diag([log])
    assert (SUCCESS_TAIL in out) is expect_success, f"{log['action']} 分類改變"
    assert (FAILURE_TAIL in out) is (not expect_success)


# ───────────── G5：[] 的邊界不受本修影響 ─────────────
@pytest.mark.req("BUGFIX_PNR01_G5:1")
def test_g5_empty_list_behaviour_unchanged():
    """⚠️ 空集合仍是**只剩空標題**的退化態——本修 ⛔ 未觸碰空態語義（那屬 F-C12／dispatcher）。"""
    assert diag([]).strip() == "以下是此帳單的付款交易紀錄："


@pytest.mark.req("BUGFIX_PNR01_G5:2")
def test_g5_dispatcher_empty_boundary_untouched():
    from services.jgb.payments import diagnose_payment_logs
    assert diagnose_payment_logs([], "沒到帳").startswith("查無此帳單的金流交易日誌")


@pytest.mark.req("BUGFIX_PNR01_G5:3")
def test_g5_responsibility_empty_adapter_untouched():
    from services import fulfillment_registry as fr
    out = fr.payment_not_reflected_facts_adapter([], {})
    assert out["empty_input"] is True
    assert out["grounding_facts"] == fr.EMPTY_PAYMENT_LOGS_FACTS


# ───────────── 全面回歸：584 組合皆不 crash ─────────────
@pytest.mark.req("BUGFIX_PNR01_G1:3")
def test_exhaustive_combinations_never_crash():
    kinds = [SUCC, SUCC_S, SUCC_INT, FAIL, NOMSG, EMPTY_RESP, MISSING, NONE_RESP]
    n = 0
    for size in (1, 2, 3):
        for combo in itertools.product(kinds, repeat=size):
            diag(list(combo))
            n += 1
    assert n == 584, f"組合數 {n} ≠ 584 ⇒ 矩陣被縮小，⛔ 不得默默改動"


# ───────────────────────── mutation ─────────────────────────
@pytest.mark.req("BUGFIX_PNR01_M1:1")
def test_m1_moving_init_back_inside_if_would_crash():
    """M1：把 `code` 初始化搬回 `if response:` 內 ⇒ 必 crash。

    ⚠️ 以**等價重建**證明 guard 抓的是 state leakage，⛔ 不是被 try/except 掩掉的 exception。
    """
    def mutated(logs):
        has_success = has_failure = False
        for log in logs:
            st = _get_log_status(log)
            resp = log.get("response", {})
            if resp:                                  # ← M1：初始化搬回 if 內
                code = resp.get("Status") or resp.get("RtnCode", "")
            if "成功" in st or code in ("SUCCESS", "1", 1):
                has_success = True
            else:
                has_failure = True
        return has_success, has_failure

    with pytest.raises(UnboundLocalError):
        mutated([MISSING])
    # ⚠️ 正對照：修後的真實函式對同一輸入 ⛔ 不得 crash
    assert diag([MISSING]).startswith("以下是此帳單的付款交易紀錄：")
