"""unit：T4-C1 executable fulfillment registry ＋ R-29 direct execution（業主凍結 2026-08-30）。

```text
C-G1 AUTHORITY_COMMIT_NO_REROUTE  user_question 極端干擾 → binding／capability 不變
C-G2 R-29 ＋ receipt.actual_amount.v1 → exact registered adapter
C-G3 R-05 ＋ receipt.actual_amount.v1 → responsibility/binding mismatch **hard fail**
C-G4 unknown binding_id → hard fail，⛔ 無 owner-prose fallback
C-G5 resolution state != RESOLVED → executor 拒絕（defense in depth）
C-G6 adapter output_mode 與 reviewed binding 不符 → hard fail（⛔ runtime 不猜）
C-G7 resolved entity type 與 binding input contract 不符 → adapter 前拒絕
C-M1 用 user_question 再進 diagnose_bill → C-G1 RED
C-M2 用 owner_contract 字串解析 callable → C-G4 RED
C-M3 拿第一個 member row answer 當 output → RED
```
"""
import pytest

from services import fulfillment_registry as fr
from services.fulfillment_registry import (BindingAuthorityMismatch, ExecutableBindingNotFound,
                                           FulfillmentExecutionError)

pytestmark = pytest.mark.unit

BINDING = "receipt.actual_amount.v1"
PLAN = {"responsibility_id": "R-29", "fulfillment_binding_id": BINDING,
        "fulfillment_strategy": "CAPABILITY", "input_contract_id": "bill.by_ref.v1"}
PAID_BILL = {"id": 716317, "title": "8月房租", "status": 16, "total": 18000}


def _res(**over):
    r = {"state": "RESOLVED", "input_contract_id": "bill.by_ref.v1", "entity_type": "bill",
         "resolved_id": PAID_BILL["id"], "resolved_entity": PAID_BILL}
    r.update(over)
    return r


# ───────────────────────── C-G2 ─────────────────────────
@pytest.mark.req("T4C_G2:1")
def test_c_g2_exact_registered_adapter():
    out = fr.execute(PLAN, _res())
    assert out["responsibility_id"] == "R-29" and out["binding_id"] == BINDING
    assert out["output_mode"] == fr.OUTPUT_FINAL_TEXT and out["entity_id"] == 716317
    assert "收據" in out["text"], "未走到 _diagnose_receipt"
    assert "text" in out and "facts" not in out


# ───────────────────────── C-G1 ＋ C-M1 ─────────────────────────
@pytest.mark.req("T4C_G1:1")
@pytest.mark.parametrize("noise", ["為什麼不能取消帳單", "我要查滯納金", "提前解約",
                                   "帳單發不出去", ""])
def test_c_g1_no_reroute_by_utterance(noise):
    """⚠️ 干擾語句**無處可傳**——execute() 簽名結構上就沒有 user_question。"""
    base = fr.execute(PLAN, _res())
    got = fr.execute(PLAN, _res(), {"user_question": noise, "face": "滯納金",
                                    "category": "條件診斷：帳單"})
    assert got["text"] == base["text"], f"輸出隨 {noise!r} 改變 ⇒ 發生了 reroute"
    assert got["binding_id"] == BINDING


@pytest.mark.req("T4C_G1:2")
def test_c_m1_rerouting_adapter_makes_g1_red():
    """C-M1：adapter 改成 diagnose_bill(bill, user_question)。"""
    from services.jgb.bills import diagnose_bill
    a = diagnose_bill(PAID_BILL, "收據多少錢")
    b = diagnose_bill(PAID_BILL, "為什麼不能取消帳單")
    assert a != b, "C-M1 未讓 C-G1 變紅 ⇒ guard 是裝飾"


# ───────────────────────── C-G3 ─────────────────────────
@pytest.mark.req("T4C_G3:1")
def test_c_g3_responsibility_binding_mismatch():
    bad = {**PLAN, "responsibility_id": "R-05"}
    with pytest.raises(BindingAuthorityMismatch, match="不是 reviewed pair"):
        fr.execute(bad, _res())


# ───────────────────────── C-G4 ＋ C-M2 ─────────────────────────
@pytest.mark.req("T4C_G4:1")
def test_c_g4_unknown_binding_hard_fails():
    bad = {**PLAN, "fulfillment_binding_id": "late_fee.facts.v1"}
    with pytest.raises(ExecutableBindingNotFound, match="未註冊於 executable registry"):
        fr.execute(bad, _res())


@pytest.mark.req("T4C_G4:2")
def test_c_g4_owner_prose_is_structurally_unusable():
    """⚠️ C-M2：execute() **結構上**不接收 owner／owner_contract——沒有參數可傳。"""
    import inspect
    params = set(inspect.signature(fr.execute).parameters)
    assert "owner" not in params and "owner_contract" not in params
    assert params == {"plan", "resolution", "context"}
    with pytest.raises(TypeError):
        fr.execute(PLAN, _res(), owner_contract="bill_diagnosis 的 receipt-amount capability（B05）")


@pytest.mark.req("T4C_G4:3")
def test_c_m2_prose_parsing_would_bypass_registry():
    """C-M2 mutation：證明「用 prose getattr」確實拿得到函式 ⇒ 必須被結構堵掉。"""
    import services.jgb.bills as bills_mod
    prose = "bill_diagnosis 的 receipt-amount deterministic capability（B05）"
    assert "_diagnose_receipt" not in prose, "prose 本身不含函式名"
    assert getattr(bills_mod, "_diagnose_receipt", None) is not None, \
        "若改以 getattr 猜名即可繞過 registry ⇒ C-G4 的結構性封堵是必要的"


# ───────────────────────── C-G5 ─────────────────────────
@pytest.mark.req("T4C_G5:1")
@pytest.mark.parametrize("state", ["AMBIGUOUS", "NO_MATCH", "INVALID_INPUT", None])
def test_c_g5_non_resolved_is_unreachable(state):
    with pytest.raises(FulfillmentExecutionError, match="不得進 direct capability"):
        fr.execute(PLAN, _res(state=state))


# ───────────────────────── C-G6 ─────────────────────────
@pytest.mark.req("T4C_G6:1")
def test_c_g6_output_mode_mismatch_hard_fails():
    fr.register("test.mode_liar.v1", responsibility_id="R-99",
                adapter=lambda e, c: {"facts": ["不是字串"]},
                input_contract_id="bill.by_ref.v1", entity_type="bill",
                output_mode=fr.OUTPUT_FINAL_TEXT)
    plan = {**PLAN, "responsibility_id": "R-99", "fulfillment_binding_id": "test.mode_liar.v1"}
    with pytest.raises(FulfillmentExecutionError, match="runtime 不得猜 output mode"):
        fr.execute(plan, _res())


# ───────────────────────── C-G7 ─────────────────────────
@pytest.mark.req("T4C_G7:1")
def test_c_g7_entity_type_must_match():
    contract_like = {"id": 101, "title": "某合約", "status": 16}   # ⚠️ 同名欄位讀得到
    with pytest.raises(FulfillmentExecutionError, match="即使函式碰巧讀得到同名欄位"):
        fr.execute(PLAN, _res(entity_type="contract", resolved_entity=contract_like))


@pytest.mark.req("T4C_G7:2")
def test_c_g7_input_contract_must_match():
    with pytest.raises(FulfillmentExecutionError, match="input_contract"):
        fr.execute(PLAN, _res(input_contract_id="contract.current_entity.v1"))


# ───────────────────────── C-M3 ─────────────────────────
@pytest.mark.req("T4C_M3:1")
def test_c_m3_member_row_answer_cannot_be_output():
    """C-M3：拿 member row answer 當 output——T4 最初的 blocker 就是這個形狀。"""
    with pytest.raises(FulfillmentExecutionError, match="不得以 member row 代替"):
        fr.execute(PLAN, _res(resolved_entity=None))
    # 正對照：R-29 的 member 4640 **answer 為空**——若真去挑 member answer 會拿到空字串
    out = fr.execute(PLAN, _res())
    assert out["text"].strip(), "direct execution 必須產出實質內容，⛔ 不是空的 member answer"
