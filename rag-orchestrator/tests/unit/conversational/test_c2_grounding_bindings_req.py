"""unit：T4-C2 R-28／R-31 GROUNDING_FACTS bindings ＋ D2 整合（業主凍結 2026-08-30）。

```text
C2-G1 R-28 no-reroute            改任何 noise → binding／payload 不變
C2-G2 R-28 no-member-answer      3939/3940 answer 皆空；把 member answer 改成任意字 → 輸出不變
C2-G3 R-31 fixed builder         question 看起來像其他 bill intent → builder 仍固定
C2-G4 candidate state            CANDIDATES → builder call = 0；D2 kind = ask
C2-G5 provenance preserved       SELECTED → type provenance 必在 facts；拿掉 type_fact_line → RED
C2-G6 outcome notes required     NOT_FOUND／TYPE_MISMATCH 缺 note → D2 hard fail
C2-G7 responsibility/binding pair R-28＋point_refund binding → hard fail（反之亦然）
C2-G8 output mode exactness      registry 說 GROUNDING_FACTS，adapter ⛔ 不得回 FINAL_TEXT
C2-M1 R-31 重新呼叫 is_point_refund_intent(user_question) → no-reroute RED
C2-M2 R-31 CANDIDATES 時 candidates[0] → candidate guard RED
C2-M3 R-28／R-31 回 member.answer → no-row-authority RED
```
"""
import inspect

import pytest

from services import fulfillment_registry as fr
from services import grounding_presentation as gp
from services.fulfillment_registry import BindingAuthorityMismatch, FulfillmentExecutionError

pytestmark = pytest.mark.unit

LATE_FEE_BILL = {"id": 88012, "title": "延遲金 2026-07", "type": 4, "status": 2,
                 "total": 360, "date_expire": 20260731}
PR_BILL_A = {"id": 9001, "title": "點退帳單 A", "type": 2, "status": 2, "total": -14300}
PR_BILL_B = {"id": 9002, "title": "點退帳單 B", "type": 2, "status": 2, "total": -900}
RENT_BILL = {"id": 7001, "title": "8月房租", "type": 1, "status": 2, "total": 18000}


def _plan(rid, binding, contract):
    return {"responsibility_id": rid, "fulfillment_binding_id": binding,
            "fulfillment_strategy": "CAPABILITY", "input_contract_id": contract}


def _res(contract, etype, entity, **over):
    r = {"state": "RESOLVED", "input_contract_id": contract, "entity_type": etype,
         "resolved_id": entity.get("id") if isinstance(entity, dict) else None,
         "resolved_entity": entity}
    r.update(over)
    return r


R28_PLAN = _plan("R-28", "late_fee.facts.v1", "late_fee.bill_or_contract.v1")
R31_PLAN = _plan("R-31", "point_refund.bill_facts.v1", "point_refund.bill_by_contract.v1")


def _r28(entity=LATE_FEE_BILL, tag="resolved_late_fee_bill", **ctx):
    return fr.execute(R28_PLAN,
                      _res("late_fee.bill_or_contract.v1", "bill_or_contract", entity),
                      {"entity_tag": tag, **ctx})


def _r31(rows, **ctx):
    entity = rows if isinstance(rows, dict) else {"id": "rows", "rows": rows}
    res = _res("point_refund.bill_by_contract.v1", "bill", entity)
    res["resolved_entity"] = entity
    return fr.execute(R31_PLAN, res, {"resolved_rows": rows, **ctx})


# ⚠️ R-31 的 adapter 收 resolved_rows：executor 傳 resolved_entity，故用 context 轉交
def _r31_direct(rows, **ctx):
    return fr.point_refund_bill_facts_adapter(rows, ctx)


# ───────────────────────── C2-G1 ─────────────────────────
@pytest.mark.req("T4C2_G1:1")
@pytest.mark.parametrize("noise", ["為什麼不能取消帳單", "我要查收據", "提前解約", ""])
def test_c2_g1_r28_no_reroute(noise):
    base = _r28()
    got = _r28(user_question=noise, face="帳單異常", category="帳單管理")
    assert got["grounding_outcome"] == base["grounding_outcome"]
    assert got["binding_id"] == "late_fee.facts.v1"


@pytest.mark.req("T4C2_G1:2")
def test_c2_g1_adapter_does_not_touch_face_dispatch():
    src = inspect.getsource(fr.late_fee_facts_adapter)
    code = "\n".join(l for l in src.splitlines() if "⛔" not in l and "⚠️" not in l)
    assert "face_bill_response" not in code and "BILL_FACE_BUILDERS" not in code


# ───────────────────────── C2-G2 ＋ C2-M3 ─────────────────────────
@pytest.mark.req("T4C2_G2:1")
def test_c2_g2_member_answer_never_participates():
    base = _r28()
    polluted = _r28({**LATE_FEE_BILL, "answer": "MEMBER ANSWER", "knowledge_id": 3939})
    assert polluted["grounding_outcome"]["grounding_facts"] == \
        base["grounding_outcome"]["grounding_facts"]
    assert "MEMBER ANSWER" not in polluted["grounding_outcome"]["grounding_facts"]


@pytest.mark.req("T4C2_G2:2")
def test_c2_g2_tagged_alternatives_required():
    """⚠️ ⛔ 不得退化成模糊的 row——entity_tag 必須明示是哪一型。"""
    with pytest.raises(FulfillmentExecutionError, match="不得退化成模糊的 row"):
        _r28(tag=None)
    with pytest.raises(FulfillmentExecutionError, match="entity_tag"):
        _r28(tag="row")


# ───────────────────────── C2-G3 ＋ C2-M1 ─────────────────────────
@pytest.mark.req("T4C2_G3:1")
@pytest.mark.parametrize("noise", ["這筆收據多少錢", "帳單為什麼發不出去", "滯納金怎麼算"])
def test_c2_g3_r31_fixed_builder(noise):
    base = _r31_direct([PR_BILL_A])
    got = _r31_direct([PR_BILL_A], user_question=noise, face="條件診斷：帳單")
    assert got == base, "R-31 輸出隨 utterance 改變 ⇒ builder 被重選"


@pytest.mark.req("T4C2_M1:1")
def test_c2_m1_intent_check_would_reroute():
    """C2-M1：證明 is_point_refund_intent 確實會依 utterance 分歧 ⇒ 不得進 adapter。"""
    from services.jgb import point_refund_selection as pr
    assert pr.is_point_refund_intent("我這份合約的點退帳單多少錢") is True
    assert pr.is_point_refund_intent("這筆收據多少錢") is False
    src = inspect.getsource(fr.point_refund_bill_facts_adapter)
    code = "\n".join(l for l in src.splitlines() if "⛔" not in l and "⚠️" not in l)
    assert "is_point_refund_intent" not in code


# ───────────────────────── C2-G4 ＋ C2-M2 ─────────────────────────
@pytest.mark.req("T4C2_G4:1")
def test_c2_g4_candidates_do_not_build_facts():
    out = _r31_direct([PR_BILL_A, PR_BILL_B])
    assert out["outcome"] == "CANDIDATES"
    assert "grounding_facts" not in out, "候選態 ⛔ 不得執行 builder"
    assert [c["id"] for c in out["candidates"]] == [9001, 9002]
    presented = gp.present({"responsibility_id": "R-31", **out})
    assert presented["kind"] == gp.KIND_ASK


@pytest.mark.req("T4C2_M2:1")
def test_c2_m2_taking_first_candidate_would_be_red():
    out = _r31_direct([PR_BILL_A, PR_BILL_B])
    mutated = {"outcome": "FACTS", "grounding_facts": "假的 facts",
               "entity_id": out["candidates"][0]["id"]}
    presented = gp.present({"responsibility_id": "R-31", **mutated})
    assert presented["kind"] == gp.KIND_CONVERGE and "9001" in presented["grounding"], \
        "C2-M2 未讓 candidate guard 變紅 ⇒ guard 是裝飾"


# ───────────────────────── C2-G5 ─────────────────────────
@pytest.mark.req("T4C2_G5:1")
def test_c2_g5_selection_provenance_preserved():
    from services.jgb import point_refund_selection as pr
    out = _r31_direct([PR_BILL_A])
    facts = out["grounding_facts"]
    assert pr.type_fact_line(PR_BILL_A) in facts, "type provenance 被吃掉了"
    assert "點退帳單 A" in facts


@pytest.mark.req("T4C2_G5:2")
def test_c2_g5_mutation_dropping_type_line_is_red():
    from services.jgb import point_refund_selection as pr
    from services.jgb.bills import build_late_fee_facts
    mutated = build_late_fee_facts(PR_BILL_A)          # ⛔ 少了 type_fact_line
    assert pr.type_fact_line(PR_BILL_A) not in mutated, \
        "C2-G5 mutation 未變紅 ⇒ guard 是裝飾"


# ───────────────────────── C2-G6 ─────────────────────────
@pytest.mark.req("T4C2_G6:1")
@pytest.mark.parametrize("rows,outcome", [([RENT_BILL], "NOT_FOUND"), ([], "NOT_FOUND")])
def test_c2_g6_not_found_carries_reviewed_note(rows, outcome):
    out = _r31_direct(rows)
    assert out["outcome"] == outcome and out["outcome_note"].strip()
    presented = gp.present({"responsibility_id": "R-31", **out})
    assert presented["kind"] == gp.KIND_ASK and presented["answer"] == out["outcome_note"]


@pytest.mark.req("T4C2_G6:2")
def test_c2_g6_type_mismatch_carries_note():
    out = _r31_direct([RENT_BILL], direct_bill=True)
    assert out["outcome"] == "TYPE_MISMATCH" and "不是點退帳單" in out["outcome_note"]


@pytest.mark.req("T4C2_G6:3")
def test_c2_g6_missing_note_makes_d2_hard_fail():
    with pytest.raises(gp.GroundingPresentationError, match="本層不自行編話術"):
        gp.present({"responsibility_id": "R-31", "outcome": "NOT_FOUND"})


# ───────────────────────── C2-G7 ─────────────────────────
@pytest.mark.req("T4C2_G7:1")
@pytest.mark.parametrize("rid,binding", [("R-28", "point_refund.bill_facts.v1"),
                                          ("R-31", "late_fee.facts.v1")])
def test_c2_g7_binding_pair_enforced(rid, binding):
    plan = _plan(rid, binding, "late_fee.bill_or_contract.v1")
    with pytest.raises(BindingAuthorityMismatch):
        fr.execute(plan, _res("late_fee.bill_or_contract.v1", "bill_or_contract", LATE_FEE_BILL),
                   {"entity_tag": "resolved_late_fee_bill"})


# ───────────────────────── C2-G8 ─────────────────────────
@pytest.mark.req("T4C2_G8:1")
def test_c2_g8_output_mode_exactness():
    out = _r28()
    assert out["output_mode"] == fr.OUTPUT_GROUNDING_FACTS
    assert "grounding_outcome" in out and "text" not in out


@pytest.mark.req("T4C2_G8:2")
def test_c2_g8_string_return_is_rejected(monkeypatch):
    """registry 說 GROUNDING_FACTS，adapter 若回字串（FINAL_TEXT 形狀）→ hard fail。"""
    fr.register("test.grounding_liar.v1", responsibility_id="R-98",
                adapter=lambda e, c: "我是 final text",
                input_contract_id="late_fee.bill_or_contract.v1",
                entity_type="bill_or_contract", output_mode=fr.OUTPUT_GROUNDING_FACTS)
    plan = _plan("R-98", "test.grounding_liar.v1", "late_fee.bill_or_contract.v1")
    with pytest.raises(FulfillmentExecutionError, match="必須回帶 outcome 的 dict"):
        fr.execute(plan, _res("late_fee.bill_or_contract.v1", "bill_or_contract", LATE_FEE_BILL),
                   {"entity_tag": "resolved_late_fee_bill"})


# ───────────────────────── 三種形狀的 precedent ─────────────────────────
@pytest.mark.req("T4C2_SHAPES:1")
def test_three_fulfillment_shapes_registered():
    """⚠️ R-29 direct FINAL_TEXT／R-28 direct GROUNDING_FACTS／R-31 composite GROUNDING_FACTS。"""
    assert fr.lookup("receipt.actual_amount.v1", "R-29")["output_mode"] == fr.OUTPUT_FINAL_TEXT
    assert fr.lookup("late_fee.facts.v1", "R-28")["output_mode"] == fr.OUTPUT_GROUNDING_FACTS
    assert fr.lookup("point_refund.bill_facts.v1", "R-31")["output_mode"] == fr.OUTPUT_GROUNDING_FACTS
