"""unit：`_RESOLVERS` 接線 ＋ T4-D2 GROUNDING_FACTS 出口的 wired-seam guards（2026-08-31）。

```text
W-G1 responsibility input_contract_id → exact registered resolver
     ⛔ 不允許 fallback ／ 動態組名 getattr ／ 猜函式
W-G2 GROUNDING_FACTS execution result → D2 present() → responsibility converter
     整條 ⛔ 不得重入 legacy dispatcher ／ show_knowledge ／ row.answer
     unresolved（NO_MATCH／AMBIGUOUS／INVALID）仍保持**同一 responsibility authority**，
     ⛔ 不得因 _RESOLVERS 接上後掉回 form／legacy path
W-M1 未註冊 contract → 動態猜函式        → guard RED
W-M2 上游未 RESOLVED 卻拿 raw ref 硬跑下游 → guard RED
W-M3 GROUNDING 缺文字時以 row.answer 補值  → guard RED
```
"""
import ast
import inspect
import textwrap

import pytest

from services import fulfillment_registry as fr
from services import responsibility_completion as rc
from services import responsibility_entity_resolution as rer

pytestmark = pytest.mark.unit

ROLE = "20151"
BILL = 716317


class FakeApi:
    """⚠️ 一個 fake 供三種 resolver 用——只回**已對齊真實信封**的形狀。"""

    def __init__(self, bill_rows=None, logs=None, iot=None, envelope_bill_id=BILL):
        self._bill_rows, self._logs, self._iot = bill_rows, logs, iot
        self._env = envelope_bill_id
        self.calls = []

    async def get_bill_detail(self, role_id, bill_id, **kw):
        self.calls.append(("get_bill_detail", bill_id))
        return {"success": True, "data": self._bill_rows}

    async def get_contracts(self, role_id, keyword="", **kw):
        self.calls.append(("get_contracts", keyword))
        return {"success": True, "data": []}

    async def get_payment_logs(self, role_id, bill_id=None, **kw):
        """⚠️ 必須模擬**真實信封**：`{success, bill_id, payments[], payment_logs→data[]}`。

        ⚠️ F-C21 會驗 `payment_logs[].payment_id ∈ {payments[].id}`——
        替身若省略 `payments`，resolver 會（正確地）hard fail。⛔ 不得為了讓測試過而放寬 guard。
        """
        self.calls.append(("get_payment_logs", bill_id))
        logs = self._logs or []
        payments = [{"id": p} for p in sorted({l.get("payment_id") for l in logs
                                               if l.get("payment_id") is not None})]
        return {"success": True, "data": logs, "payments": payments, "bill_id": self._env}

    async def get_iot_manufacturers(self, role_id, **kw):
        self.calls.append(("get_iot_manufacturers", role_id))
        return {"success": True, "data": self._iot or []}


def _session(rid, binding, cid):
    return {"vendor_id": ROLE, "form_id": "f1",
            "session_authority_mode": "responsibility",
            "responsibility_id": rid, "fulfillment_binding_id": binding,
            "input_contract_id": cid}


# ───────────────────────── W-G1 ─────────────────────────
@pytest.mark.req("W_G1:1")
def test_every_wired_contract_is_explicitly_declared():
    """⚠️ ⛔ 不得動態組名——每個 contract 的 resolver 必須在 spec 表裡明示。"""
    for cid, spec in rc._RESOLVER_SPECS.items():
        assert cid in rer.INPUT_CONTRACTS, f"{cid} 不在 input contract registry"
        assert callable(spec["fn"]), cid
        assert spec["kind"] in (rc.KIND_ROLE_AND_REF, rc.KIND_ROLE_ONLY, rc.KIND_UPSTREAM_REF), cid


@pytest.mark.req("W_G1:2")
def test_wiring_never_uses_dynamic_name_resolution():
    """⚠️ AST：接線層 ⛔ 不得出現 getattr／eval／importlib 之類的動態取名。"""
    src = inspect.getsource(rc)
    banned = {"getattr", "eval", "exec", "import_module", "globals", "vars"}
    hit = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in banned:
                hit.add(name)
    assert not hit, f"接線層出現動態取名 {hit} ⇒ W-G1 被打穿"


@pytest.mark.req("W_G1:3")
@pytest.mark.asyncio
async def test_unregistered_contract_is_loud_not_legacy_fallback():
    with pytest.raises(rc.ResponsibilityCompletionError, match="不得改用 legacy 查詢路徑"):
        await rc._resolve_input("nope.contract.v1", FakeApi(), ROLE, {})


@pytest.mark.req("W_G1:4")
def test_tenant_summary_is_deliberately_absent_from_wiring():
    """⚠️ R-24 IDENTITY_BLOCKED ⇒ **明示缺席**才看得見，⛔ 不得偷接。"""
    assert "tenant.summary.v1" not in rc._RESOLVER_SPECS
    assert "tenant.summary.v1" in rer.INPUT_CONTRACTS, "契約本身仍須註冊（缺席的是接線）"


@pytest.mark.req("W_G1:5")
@pytest.mark.asyncio
async def test_upstream_unresolved_never_forges_a_resolved_id():
    """**W-M2 的正面版**：上游 NO_MATCH ⇒ ⛔ 不得拿 raw ref 當 resolved_bill_id 硬跑下游。"""
    api = FakeApi(bill_rows=[], logs=[{"id": 1, "payment_id": 9876}])
    r = await rc._resolve_input("payment_logs.by_bill.v1", api, ROLE, {"bill_ref": "999"})
    assert r["state"] == rer.STATE_NO_MATCH
    assert r["_blocked_downstream"] == "payment_logs.by_bill.v1"
    assert not any(c[0] == "get_payment_logs" for c in api.calls), \
        "上游未 RESOLVED 卻仍呼叫了下游 fetch ⇒ resolved id 被偽造"


@pytest.mark.req("W_G1:6")
@pytest.mark.asyncio
async def test_upstream_resolved_feeds_downstream_the_resolved_id():
    """⚠️ 正對照組：上游成功時，下游收到的必須是**上游解析出的 id**，⛔ 不是使用者輸入。"""
    api = FakeApi(bill_rows=[{"id": BILL, "title": "四月租金"}],
                  logs=[{"id": 1, "payment_id": 9876}])
    r = await rc._resolve_input("payment_logs.by_bill.v1", api, ROLE, {"bill_ref": "716317"})
    assert r["state"] == rer.STATE_RESOLVED
    assert ("get_payment_logs", BILL) in api.calls


# ───────────────────────── W-G2 ─────────────────────────
def _grounding_plan_session():
    """借用**已註冊**的 R-28 binding 走完整 GROUNDING_FACTS 路徑。"""
    return _session("R-28", "late_fee.facts.v1", "late_fee.bill_or_contract.v1")


@pytest.mark.req("W_G2:1")
def test_grounding_exit_never_reenters_legacy_or_row_answer():
    """⚠️ AST：T4-D2 出口 ⛔ 不得觸及 legacy dispatcher／show_knowledge／row answer。"""
    src = inspect.getsource(rc._present_grounding)
    banned = {"diagnose_payment_logs", "diagnose_invoice_logs", "diagnose_iot", "diagnose_bill",
              "show_knowledge", "knowledge_base", "format_jgb_response", "face_bill_response"}
    names = set()
    for node in ast.walk(ast.parse(textwrap.dedent(src))):
        if isinstance(node, (ast.Attribute, ast.Name)):
            names.add(getattr(node, "attr", None) or getattr(node, "id", ""))
    assert not (banned & names), f"T4-D2 出口觸及 {banned & names}"


@pytest.mark.req("W_G2:2")
def test_grounding_authority_comes_from_plan_not_adapter_output():
    """⚠️ adapter 若回了別的 responsibility_id，⛔ 不得覆蓋 committed authority。"""
    plan = {"responsibility_id": "R-28", "fulfillment_binding_id": "late_fee.facts.v1",
            "input_contract_id": "late_fee.bill_or_contract.v1"}
    result = {"output_mode": fr.OUTPUT_GROUNDING_FACTS,
              "grounding_outcome": {"outcome": "FACTS", "grounding_facts": "應繳滯納金 100 元",
                                    "responsibility_id": "R-99-EVIL", "entity_id": 1}}
    out = rc._present_grounding(plan, result)
    assert out["responsibility_id"] == "R-28", "adapter 輸出竄改了 authority"
    assert out["presentation"]["responsibility_id"] == "R-28"


@pytest.mark.req("W_G2:3")
def test_grounding_facts_missing_is_hard_fail_not_silent_empty():
    from services.grounding_presentation import GroundingPresentationError
    plan = {"responsibility_id": "R-28", "fulfillment_binding_id": "late_fee.facts.v1",
            "input_contract_id": "late_fee.bill_or_contract.v1"}
    with pytest.raises(GroundingPresentationError):
        rc._present_grounding(plan, {"output_mode": fr.OUTPUT_GROUNDING_FACTS,
                                     "grounding_outcome": {"outcome": "FACTS",
                                                           "grounding_facts": "  "}})


@pytest.mark.req("W_G2:4")
def test_grounding_outcome_must_be_a_classified_dict():
    plan = {"responsibility_id": "R-28", "fulfillment_binding_id": "late_fee.facts.v1",
            "input_contract_id": "late_fee.bill_or_contract.v1"}
    with pytest.raises(rc.ResponsibilityCompletionError, match="缺 outcome dict"):
        rc._present_grounding(plan, {"output_mode": fr.OUTPUT_GROUNDING_FACTS,
                                     "grounding_outcome": "已是字串"})


@pytest.mark.req("W_G2:5")
def test_grounding_result_is_a_distinct_family_not_a_form_dict():
    """⚠️ ⛔ 不得退化成 `{knowledge_id, answer, form_id}`——那是 row authority 的後門形狀。"""
    plan = {"responsibility_id": "R-28", "fulfillment_binding_id": "late_fee.facts.v1",
            "input_contract_id": "late_fee.bill_or_contract.v1"}
    out = rc._present_grounding(plan, {"output_mode": fr.OUTPUT_GROUNDING_FACTS,
                                       "grounding_outcome": {"outcome": "FACTS",
                                                             "grounding_facts": "x"}})
    assert isinstance(out, rc.ResponsibilityGroundingResult)
    assert not ({"knowledge_id", "answer", "form_id"} & set(out)), "退化成 legacy form 形狀"


@pytest.mark.req("W_G2:6")
def test_three_result_families_are_type_disjoint():
    """⚠️ converter 依**型別**分流 ⇒ 三個 family ⛔ 不得互為子類。"""
    fams = [fr.FulfillmentExecutionResult, rc.ResponsibilityGroundingResult,
            rc.ResponsibilityInputResolutionResult]
    for a in fams:
        for b in fams:
            if a is not b:
                assert not issubclass(a, b), f"{a.__name__} 是 {b.__name__} 的子類 ⇒ 型別分流會誤判"


# ───────────────── COLLECTION 能真的執行到底（接線的意義）─────────────────
@pytest.mark.req("W_G2:7")
def test_collection_entity_can_reach_executor():
    """⚠️ executor 原本一律要求 dict ⇒ COLLECTION 會被擋死；放寬**僅限** COLLECTION。"""
    fr.register("__test.collection.v1", responsibility_id="R-TEST",
                adapter=lambda entity, ctx: {"outcome": "FACTS",
                                             "grounding_facts": f"{len(entity)} 筆"},
                input_contract_id="payment_logs.by_bill.v1", entity_type="payment_logs",
                output_mode=fr.OUTPUT_GROUNDING_FACTS)
    try:
        res = {"state": rer.STATE_RESOLVED, "input_contract_id": "payment_logs.by_bill.v1",
               "entity_type": "payment_logs", "resolved_entity": [{"id": 1}, {"id": 2}]}
        out = fr.execute({"responsibility_id": "R-TEST",
                          "fulfillment_binding_id": "__test.collection.v1"}, res)
        assert out["grounding_outcome"]["grounding_facts"] == "2 筆"
    finally:
        fr._REGISTRY.pop("__test.collection.v1", None)


@pytest.mark.req("W_G2:8")
def test_single_entity_contract_still_rejects_a_list():
    """⚠️ 負控制：放寬 ⛔ 不得外溢到 SELECT_ONE——單筆契約仍不許收 list。"""
    res = {"state": rer.STATE_RESOLVED, "input_contract_id": "bill.by_ref.v1",
           "entity_type": "bill", "resolved_entity": [{"id": 1}, {"id": 2}]}
    with pytest.raises(fr.FulfillmentExecutionError, match="resolved_entity 缺漏"):
        fr.execute({"responsibility_id": "R-29",
                    "fulfillment_binding_id": "receipt.actual_amount.v1"}, res)


@pytest.mark.req("W_G2:9")
def test_empty_collection_only_executes_under_resolved_empty():
    fr.register("__test.empty.v1", responsibility_id="R-TEST2",
                adapter=lambda entity, ctx: {"outcome": "FACTS", "grounding_facts": "空"},
                input_contract_id="payment_logs.by_bill.v1", entity_type="payment_logs",
                output_mode=fr.OUTPUT_GROUNDING_FACTS)
    try:
        plan = {"responsibility_id": "R-TEST2", "fulfillment_binding_id": "__test.empty.v1"}
        base = {"input_contract_id": "payment_logs.by_bill.v1", "entity_type": "payment_logs",
                "resolved_entity": []}
        ok = fr.execute(plan, {**base, "state": rer.STATE_RESOLVED_EMPTY})
        assert ok["grounding_outcome"]["grounding_facts"] == "空"
        with pytest.raises(fr.FulfillmentExecutionError, match="RESOLVED_EMPTY"):
            fr.execute(plan, {**base, "state": rer.STATE_RESOLVED})
    finally:
        fr._REGISTRY.pop("__test.empty.v1", None)


# ───────────────────────── mutations ─────────────────────────
@pytest.mark.req("W_M1:1")
def test_w_m1_dynamic_getattr_would_be_caught():
    """W-M1：若接線改用 `getattr(rer, name)` 猜函式，AST guard 必須抓到。"""
    mutated = "def _resolve_input(cid, api, role, data):\n    return getattr(rer, 'resolve_' + cid)\n"
    hit = {n.func.id for n in ast.walk(ast.parse(mutated))
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "getattr" in hit, "W-M1 未讓 AST guard 變紅 ⇒ guard 是裝飾"


@pytest.mark.req("W_M3:1")
def test_w_m3_row_answer_fallback_would_be_caught():
    """W-M3：若 converter 在缺文字時改用 row.answer 補值，D2 層必須先擋下。"""
    from services.grounding_presentation import GroundingPresentationError, present
    with pytest.raises(GroundingPresentationError, match="不得改用"):
        present({"outcome": "FACTS", "responsibility_id": "R-28", "grounding_facts": ""})
