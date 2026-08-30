"""unit：D1-E responsibility → envelope converter guards（業主凍結 2026-08-30）。

```text
E-G1 exact FINAL_TEXT mapping        result.text → response.answer **逐字相同**
E-G2 no silent empty fallback        text None／""／缺 → hard fail；mutation `.get('answer','')` 必紅
E-G3 no row-shaped recovery          即使塞 answer／knowledge_id 也 ⛔ 不得拿來補 text
E-G4 envelope metadata is transport-only  form_id 來源是 **persisted session**，⛔ 非 member row
E-G5 unresolved remains responsibility mode   form_completed=false ＋ authority 四欄不變
E-G6 RESOLVED cannot escape executor  → hard fail
E-G7 legacy converter unchanged       legacy dict 仍逐位走原 converter
```
⚠️ audit lesson：**同名欄位 ≠ 同一 authority**。`knowledge.answer` 是內容來源；
`VendorChatResponse.answer` 是 API envelope。風險不在寫入 `answer` 這個名字，
而在**從錯誤 semantic slot 取值**與**用 silent default 把型別錯誤吃掉**。
"""
import pytest

from services.fulfillment_registry import FulfillmentExecutionResult
from services.responsibility_completion import ResponsibilityInputResolutionResult

pytestmark = pytest.mark.unit


@pytest.fixture
def mod():
    from routers import chat
    return chat


@pytest.fixture
def request_obj(mod):
    return mod.VendorChatRequest(message="收據多少錢", vendor_id=24, session_id="s-1",
                                 include_sources=True)


SESSION = {"form_id": "jgb_bill_diagnosis", "session_authority_mode": "responsibility",
           "responsibility_id": "R-29", "fulfillment_binding_id": "receipt.actual_amount.v1",
           "fulfillment_strategy": "CAPABILITY", "input_contract_id": "bill.by_ref.v1"}
TEXT = "帳單「8月房租」已繳費，收據金額為 NT$ 1,234。"


def _final(**over):
    r = FulfillmentExecutionResult(responsibility_id="R-29",
                                   binding_id="receipt.actual_amount.v1",
                                   output_mode="FINAL_TEXT", entity_id=716317, text=TEXT)
    r.update(over)
    return r


def _unresolved(state="AMBIGUOUS", **res):
    resolution = {"state": state, "input_contract_id": "bill.by_ref.v1", "entity_type": "bill"}
    resolution.update(res)
    return ResponsibilityInputResolutionResult(
        kind="responsibility_entity_unresolved", responsibility_id="R-29",
        fulfillment_binding_id="receipt.actual_amount.v1",
        input_contract_id="bill.by_ref.v1", state=state, resolution=resolution)


# ───────────────────────── E-G1 ─────────────────────────
@pytest.mark.req("D1E_G1:1")
def test_e_g1_exact_final_text_mapping(mod, request_obj):
    resp = mod._convert_responsibility_result_to_response(_final(), SESSION, request_obj)
    assert resp.answer == TEXT, "answer 未逐字對應 FINAL_TEXT.text"
    assert resp.form_completed is True


# ───────────────────────── E-G2 ─────────────────────────
@pytest.mark.req("D1E_G2:1")
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_e_g2_no_silent_empty_fallback(mod, request_obj, bad):
    with pytest.raises(mod.ResponsibilityEnvelopeError, match="不得以 '' 帶過"):
        mod._convert_responsibility_result_to_response(_final(text=bad), SESSION, request_obj)


@pytest.mark.req("D1E_G2:2")
def test_e_g2_missing_text_key_also_fails(mod, request_obj):
    r = _final()
    del r["text"]
    with pytest.raises(mod.ResponsibilityEnvelopeError):
        mod._convert_responsibility_result_to_response(r, SESSION, request_obj)


@pytest.mark.req("D1E_G2:3")
def test_e_g2_mutation_silent_default_would_pass_silently():
    """mutation：`answer = result.get('answer','')`——證明舊寫法會**靜默**產出空回答。"""
    r = _final(text=None)
    assert r.get("answer", "") == "", "mutation 未讓 E-G2 變紅 ⇒ guard 是裝飾"


# ───────────────────────── E-G3 ─────────────────────────
@pytest.mark.req("D1E_G3:1")
def test_e_g3_no_row_shaped_recovery(mod, request_obj):
    """即使塞了 answer／knowledge_id，⛔ 不得拿來補 text。"""
    r = _final(text=None, answer="ROW ANSWER", knowledge_id=4640)
    with pytest.raises(mod.ResponsibilityEnvelopeError, match="不得改用"):
        mod._convert_responsibility_result_to_response(r, SESSION, request_obj)


@pytest.mark.req("D1E_G3:2")
def test_e_g3_row_answer_never_wins_over_text(mod, request_obj):
    resp = mod._convert_responsibility_result_to_response(
        _final(answer="ROW ANSWER"), SESSION, request_obj)
    assert resp.answer == TEXT and resp.answer != "ROW ANSWER"


# ───────────────────────── E-G4 ─────────────────────────
@pytest.mark.req("D1E_G4:1")
def test_e_g4_envelope_metadata_from_session_only(mod, request_obj):
    """member row 的 form_id／action_type ⛔ 不得改變 response。"""
    r = _final(form_id="ROW_FORM", action_type="api_call")
    resp = mod._convert_responsibility_result_to_response(r, SESSION, request_obj)
    assert resp.form_id == SESSION["form_id"], "form_id 來源必須是 persisted session"
    assert resp.action_type == "form_fill", "D1-E v1 ⛔ 不新增 responsibility_fulfillment"


# ───────────────────────── E-G5 ─────────────────────────
@pytest.mark.req("D1E_G5:1")
def test_e_g5_ambiguous_prompt_and_not_completed(mod, request_obj):
    r = _unresolved("AMBIGUOUS", candidates=[{"id": 101, "title": "民生東路"},
                                             {"id": 102, "title": "松山"}])
    resp = mod._convert_responsibility_result_to_response(r, SESSION, request_obj)
    assert resp.form_completed is False
    assert "哪一筆" in resp.answer and "民生東路" in resp.answer
    # ⚠️ quick_replies 依既有 QuickReply 契約（text/value），⛔ 非字串陣列
    assert [q.value for q in resp.quick_replies] == ["101", "102"]
    assert [q.text for q in resp.quick_replies] == ["民生東路", "松山"]
    # ⚠️ authority 四欄仍在 result 上，未被 converter 動過
    for k in ("responsibility_id", "fulfillment_binding_id", "input_contract_id"):
        assert r[k] == SESSION[k]


@pytest.mark.req("D1E_G5:2")
@pytest.mark.parametrize("state,frag", [("NO_MATCH", "查無符合"), ("INVALID_INPUT", "還需要")])
def test_e_g5_other_unresolved_states(mod, request_obj, state, frag):
    r = _unresolved(state, missing_fields=["bill_ref"])
    resp = mod._convert_responsibility_result_to_response(r, SESSION, request_obj)
    assert resp.form_completed is False and frag in resp.answer


# ───────────────────────── E-G6 ─────────────────────────
@pytest.mark.req("D1E_G6:1")
def test_e_g6_resolved_cannot_escape_executor(mod, request_obj):
    with pytest.raises(mod.ResponsibilityEnvelopeError, match="不得繞過 executor"):
        mod._convert_responsibility_result_to_response(
            _unresolved("RESOLVED"), SESSION, request_obj)


# ───────────────────────── E-G7 ─────────────────────────
@pytest.mark.req("D1E_G7:1")
def test_e_g7_legacy_dict_goes_to_legacy_converter(mod, request_obj):
    legacy = {"answer": "legacy 的答案", "form_completed": True, "form_id": "legacy_form"}
    resp = mod._convert_responsibility_or_form_result(legacy, SESSION, request_obj)
    assert resp.answer == "legacy 的答案" and resp.form_id == "legacy_form"


@pytest.mark.req("D1E_G7:2")
def test_e_g7_dispatch_is_by_type_not_by_key(mod, request_obj):
    """⚠️ 依**型別**分流：一個帶 text／responsibility_id 的**普通 dict** 仍走 legacy。"""
    lookalike = {"text": "看起來像 responsibility", "responsibility_id": "R-29",
                 "answer": "legacy 欄位"}
    resp = mod._convert_responsibility_or_form_result(lookalike, SESSION, request_obj)
    assert resp.answer == "legacy 欄位", "⛔ 不得靠 key 猜型別"


@pytest.mark.req("D1E_G7:3")
def test_e_g7_unknown_type_hard_fails(mod, request_obj):
    class Weird(dict):
        pass
    with pytest.raises(mod.ResponsibilityEnvelopeError, match="未知的 responsibility result 型別"):
        mod._convert_responsibility_result_to_response(Weird(), SESSION, request_obj)
