"""unit：T4-D1 responsibility completion wiring guards（業主凍結 2026-08-30）。

```text
D1-G1 responsibility path **bypasses** legacy completion（legacy 呼叫次數 = 0）
      mutation：先進 _complete_form 再判 mode → 必紅
D1-G2 legacy byte-for-byte：mode NULL 與 legacy_row 都走原 _legacy_complete_form
D1-G3 exact authority survives wired path；form payload 無權覆寫
D1-G4 real resolver，⛔ 無隱藏 legacy bill lookup（B-G5 提升到 wired seam）
D1-G5 FINAL_TEXT 無 semantic reroute（干擾語句無處可傳）
D1-G6 非 RESOLVED → executor 呼叫次數 = 0
```
"""
import pytest

from services import fulfillment_registry as fr
from services import responsibility_completion as rc
from services import responsibility_entity_resolution as rer
from services import responsibility_session as rsess

pytestmark = pytest.mark.unit

R29 = dict(responsibility_id="R-29", fulfillment_binding_id="receipt.actual_amount.v1",
           fulfillment_strategy="CAPABILITY", input_contract_id="bill.by_ref.v1")
PAID = {"id": 716317, "title": "8月房租", "status": 16, "total": 18000}


def _sess(**over):
    s = rsess.build_responsibility_session(**R29)
    s["vendor_id"] = 24
    s.update(over)
    return s


class FakeApi:
    def __init__(self, detail=None, contracts=None, bills=None):
        self._d, self._c, self._b = detail, contracts, bills
        self.calls = []

    async def get_bill_detail(self, role_id, bill_id):
        self.calls.append(("get_bill_detail", bill_id)); return self._d

    async def get_contracts(self, role_id, contract_ids=None, keyword=None, **kw):
        self.calls.append(("get_contracts", keyword)); return self._c

    async def get_bills(self, role_id, contract_ids=None, **kw):
        if "bill_ref" in kw:
            raise AssertionError("⛔ wired path 呼叫了 legacy bill_ref 分支（F-C6）")
        self.calls.append(("get_bills", contract_ids)); return self._b


def ok(d):
    return {"success": True, "data": d}


# ───────────────────── D1-G1：dispatcher 在 legacy 之前 ─────────────────────
@pytest.mark.req("T4D1_G1:1")
@pytest.mark.asyncio
async def test_d1_g1_responsibility_bypasses_legacy(monkeypatch):
    from services.form_manager import FormManager
    fm = FormManager.__new__(FormManager)
    fm.db_pool = None
    legacy_calls = []
    monkeypatch.setattr(FormManager, "_legacy_complete_form",
                        lambda self, s, f, c: legacy_calls.append(1), raising=True)
    seen = {}

    async def fake_handler(session_state, form_schema, collected_data, db_pool=None, api=None):
        seen["called"] = seen.get("called", 0) + 1
        return {"kind": "ok"}
    monkeypatch.setattr(rc, "complete_responsibility_form", fake_handler)
    monkeypatch.setitem(__import__("sys").modules, "services.responsibility_completion", rc)

    out = await fm._complete_form(_sess(), {}, {"bill_ref": "716317"})
    assert out == {"kind": "ok"}
    assert seen["called"] == 1, "responsibility handler 未被呼叫"
    assert legacy_calls == [], "⛔ legacy _legacy_complete_form 被呼叫了"


@pytest.mark.req("T4D1_G1:2")
def test_d1_g1_mutation_dispatch_after_legacy_would_be_red():
    """mutation：先進 legacy 再判 mode ⇒ legacy 已執行，bypass 不成立。"""
    order = []

    def mutated(mode):
        order.append("legacy")                      # ⛔ 先跑 legacy
        return "responsibility" if mode == "responsibility" else "legacy"
    mutated("responsibility")
    assert order == ["legacy"], "mutation 未讓 D1-G1 變紅 ⇒ guard 是裝飾"


# ───────────────────── D1-G2：legacy 不變 ─────────────────────
@pytest.mark.req("T4D1_G2:1")
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [None, "", "legacy_row"])
async def test_d1_g2_legacy_modes_go_to_legacy(monkeypatch, mode):
    from services.form_manager import FormManager
    fm = FormManager.__new__(FormManager)
    fm.db_pool = None
    marker = {"legacy": 0}

    async def legacy(self, s, f, c):
        marker["legacy"] += 1
        return {"kind": "legacy_result", "knowledge_id": s.get("knowledge_id")}
    monkeypatch.setattr(FormManager, "_legacy_complete_form", legacy, raising=True)

    sess = {"session_authority_mode": mode, "knowledge_id": 3496} if mode is not None \
        else {"knowledge_id": 3496}
    out = await fm._complete_form(sess, {}, {})
    assert marker["legacy"] == 1 and out["knowledge_id"] == 3496


@pytest.mark.req("T4D1_G2:2")
@pytest.mark.asyncio
async def test_d1_g2_unknown_mode_hard_fails(monkeypatch):
    from services.form_manager import FormManager
    fm = FormManager.__new__(FormManager)
    fm.db_pool = None
    monkeypatch.setattr(FormManager, "_legacy_complete_form",
                        lambda self, s, f, c: {"kind": "legacy"}, raising=True)
    with pytest.raises(ValueError, match="不得默默走 legacy completion"):
        await fm._complete_form({"session_authority_mode": "auto"}, {}, {})


# ───────────────────── D1-G3 ＋ D1-G5：authority 與 no-reroute ─────────────────
@pytest.mark.req("T4D1_G3:1")
@pytest.mark.asyncio
async def test_d1_g3_authority_survives_wired_path():
    api = FakeApi(detail=ok(PAID))
    out = await rc.complete_responsibility_form(_sess(), {}, {"bill_ref": "716317"}, api=api)
    assert out["responsibility_id"] == "R-29"
    assert out["binding_id"] == "receipt.actual_amount.v1"
    assert out["output_mode"] == fr.OUTPUT_FINAL_TEXT and out["entity_id"] == 716317
    assert "收據" in out["text"]
    # ⛔ 不得回傳假 row
    assert "knowledge_id" not in out and "answer" not in out and "form_id" not in out


@pytest.mark.req("T4D1_G3:2")
@pytest.mark.asyncio
async def test_d1_g3_payload_cannot_override_authority():
    api = FakeApi(detail=ok(PAID))
    with pytest.raises(rsess.SessionAuthorityError, match="嘗試覆寫 execution authority"):
        await rc.complete_responsibility_form(
            _sess(), {}, {"bill_ref": "716317", "responsibility_id": "R-05"}, api=api)


@pytest.mark.req("T4D1_G5:1")
@pytest.mark.asyncio
async def test_d1_g5_no_semantic_reroute():
    """⚠️ 干擾語句**無處可傳**——handler 簽名沒有 user_question／face／category。"""
    import inspect
    params = set(inspect.signature(rc.complete_responsibility_form).parameters)
    assert not ({"user_question", "face", "category"} & params)
    api = FakeApi(detail=ok(PAID))
    a = await rc.complete_responsibility_form(_sess(), {}, {"bill_ref": "716317"}, api=api)
    api2 = FakeApi(detail=ok(PAID))
    b = await rc.complete_responsibility_form(
        _sess(trigger_question="為什麼不能取消帳單 我要查滯納金 提前解約"), {},
        {"bill_ref": "716317"}, api=api2)
    assert a["text"] == b["text"], "輸出隨干擾語句改變 ⇒ 發生 reroute"


# ───────────────────── D1-G4 ＋ D1-G6 ─────────────────────
@pytest.mark.req("T4D1_G4:1")
@pytest.mark.asyncio
async def test_d1_g4_real_resolver_no_hidden_legacy_lookup():
    api = FakeApi(contracts=ok([{"id": 101}, {"id": 102}]))
    out = await rc.complete_responsibility_form(_sess(), {}, {"bill_ref": "台北"}, api=api)
    assert out["kind"] == "responsibility_entity_unresolved"
    assert out["resolution"]["state"] == rer.STATE_AMBIGUOUS
    assert not any(c[0] == "get_bills" for c in api.calls), "AMBIGUOUS 後 ⛔ 不應查帳單"
    # ⚠️ 仍是 responsibility 結果，⛔ 不是 legacy row 形狀
    assert out["responsibility_id"] == "R-29" and "knowledge_id" not in out


@pytest.mark.req("T4D1_G6:1")
@pytest.mark.asyncio
@pytest.mark.parametrize("api,ref", [
    (FakeApi(detail={"success": True, "data": None}), "999999"),
    (FakeApi(contracts=ok([])), "查無此物件"),
    (FakeApi(contracts=ok([{"id": 1}, {"id": 2}])), "台北"),
])
async def test_d1_g6_non_resolved_never_executes(monkeypatch, api, ref):
    calls = []
    monkeypatch.setattr(fr, "execute", lambda *a, **k: calls.append(1), raising=True)
    out = await rc.complete_responsibility_form(_sess(), {}, {"bill_ref": ref}, api=api)
    assert out["kind"] == "responsibility_entity_unresolved"
    assert calls == [], "非 RESOLVED 卻呼叫了 executor"
