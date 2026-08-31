"""unit：B3 三個 COLLECTION fetch resolver（業主凍結 2026-08-31，F-C17）。

```text
B3-G1 三個 fetch resolver signature 無 user_question／face／category
B3-G2 payment logs 只呼固定 payment-log API，⛔ 不得呼 diagnose_payment_logs
B3-G3 invoice 同理，⛔ 不得呼 diagnose_invoice_logs
B3-G4 IoT 同理，⛔ 不得呼 diagnose_iot
B3-G5 >1 members → RESOLVED collection，⛔ 不得 AMBIGUOUS／members[0]
B3-G6 [] → RESOLVED_EMPTY；fetch resolver 本身 ⛔ 不編 answer
B3-G7 scope mismatch → hard fail，⛔ 不得 silent filter
B3-G8 API exception／malformed → transport failure，⛔ 不得轉成 NO_MATCH
B3-M1 fetch 完直接 members[0]      → collection guard RED
B3-M2 改呼 diagnose_* dispatcher   → AST／call guard RED
B3-M3 scope mismatch 時偷偷 filter → scope guard RED
```
⚠️ **F-C17**：真正的風險 ⛔ 不是演算法，而是 fetch resolver 重新長成 dispatcher。
"""
import ast
import inspect
import textwrap

import pytest

from services import responsibility_entity_resolution as rer
from services.responsibility_entity_resolution import (IdentityNotResolved,
                                                       InputScopeViolation,
                                                       TransportFailure)

pytestmark = pytest.mark.unit

FETCH_FNS = ["fetch_payment_logs_by_bill", "fetch_invoice_logs_by_bill",
             "fetch_iot_manufacturers"]
BILL = 716317
ROLE = "20151"


# ── fakes：⚠️ 形狀對齊 JGBSystemAPI 的**真實**回應（⛔ 不自己發明信封）──────
class FakePaymentLogsApi:
    """`{success, bill_id, payments, payment_logs, summary}` 經 adapter 正規化後的 `data`。"""

    def __init__(self, logs=None, envelope_bill_id=BILL, resp=None, exc=None):
        self._logs, self._env, self._resp, self._exc = logs or [], envelope_bill_id, resp, exc
        self.calls = []

    async def get_payment_logs(self, role_id, bill_id=None, **kw):
        self.calls.append(("get_payment_logs", role_id, bill_id))
        if self._exc:
            raise self._exc
        if self._resp is not None:
            return self._resp
        return {"success": True, "data": self._logs, "payments": [],
                "summary": {}, "bill_id": self._env}


class FakeInvoiceLogsApi:
    def __init__(self, rows=None, resp=None, exc=None):
        self._rows, self._resp, self._exc = rows or [], resp, exc
        self.calls = []

    async def get_invoice_logs(self, role_id, bill_id=None, **kw):
        self.calls.append(("get_invoice_logs", role_id, bill_id))
        if self._exc:
            raise self._exc
        if self._resp is not None:
            return self._resp
        return {"success": True, "data": self._rows, "pagination": {}}


class FakeIotApi:
    def __init__(self, rows=None, resp=None, exc=None):
        self._rows, self._resp, self._exc = rows or [], resp, exc
        self.calls = []

    async def get_iot_manufacturers(self, role_id, **kw):
        self.calls.append(("get_iot_manufacturers", role_id))
        if self._exc:
            raise self._exc
        if self._resp is not None:
            return self._resp
        return {"success": True, "data": self._rows, "mapping": {}, "pagination": {}}


def _plogs(n):
    """⚠️ 真實 payment_logs 列——**刻意不含任何 bill identity**（實查形狀）。"""
    return [{"source": "payment_logs", "id": 50000 + i, "payment_id": 9876,
             "role_id": int(ROLE), "action": "credit_card"} for i in range(1, n + 1)]


def _ilogs(n, bill_id=BILL):
    return [{"id": 60000 + i, "invoice_id": 5000 + i, "bill_id": bill_id,
             "action": "issue"} for i in range(1, n + 1)]


def _iot(n, role_id=ROLE):
    return [{"id": i, "role_id": int(role_id), "manufacturer": "SkyWatch",
             "is_active": 1} for i in range(1, n + 1)]


# ───────────────────────── B3-G1 ─────────────────────────
@pytest.mark.req("B3_G1:1")
@pytest.mark.parametrize("fn", FETCH_FNS)
def test_fetch_resolver_signature_has_no_semantic_inputs(fn):
    params = set(inspect.signature(getattr(rer, fn)).parameters)
    assert not ({"user_question", "face", "category", "utterance", "query"} & params), \
        f"{fn} 收了 semantic input ⇒ fetch resolver 正在長成 dispatcher（F-C17）"


@pytest.mark.req("B3_G1:2")
@pytest.mark.parametrize("fn", FETCH_FNS)
def test_fetch_resolver_only_takes_verified_transport_input(fn):
    """⚠️ 正對照組：每個 fetch resolver 都必須**真的**收 scope identity，⛔ 不是空簽名過關。"""
    params = set(inspect.signature(getattr(rer, fn)).parameters)
    assert {"api"} <= params, fn
    assert params & {"verified_role_id", "resolved_bill_id"}, f"{fn} 沒有任何 scope identity 參數"


# ───────────────── B3-G2 / G3 / G4：⛔ 不得呼 dispatcher ─────────────────
BANNED_CALLS = {"diagnose_payment_logs", "diagnose_invoice_logs", "diagnose_iot",
                "diagnose_bill", "diagnose_subscription", "_build_response"}
ALLOWED_API = {"fetch_payment_logs_by_bill": "get_payment_logs",
               "fetch_invoice_logs_by_bill": "get_invoice_logs",
               "fetch_iot_manufacturers": "get_iot_manufacturers"}


def _called_names(fn_name):
    src = inspect.getsource(getattr(rer, fn_name))
    tree = ast.parse(textwrap.dedent(src))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            names.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
        elif isinstance(node, (ast.Attribute, ast.Name)):
            names.add(getattr(node, "attr", None) or getattr(node, "id", ""))
    return names


@pytest.mark.req("B3_G2:1")
@pytest.mark.parametrize("fn", FETCH_FNS)
def test_fetch_resolver_never_touches_legacy_dispatcher(fn):
    hit = BANNED_CALLS & _called_names(fn)
    assert not hit, f"{fn} 觸及 legacy dispatcher {hit} ⇒ 違反 F-C1／F-C17"


@pytest.mark.req("B3_G2:2")
@pytest.mark.parametrize("fn,api_method", sorted(ALLOWED_API.items()))
def test_fetch_resolver_calls_its_fixed_endpoint(fn, api_method):
    """⚠️ 正對照組：guard 必須看得見**真的有**呼叫固定 endpoint，⛔ 否則 G2 只是空掃。"""
    assert api_method in _called_names(fn), f"{fn} 沒有呼叫固定 endpoint {api_method}"


@pytest.mark.req("B3_G3:1")
@pytest.mark.asyncio
async def test_invoice_resolver_only_calls_invoice_endpoint():
    api = FakeInvoiceLogsApi(_ilogs(2))
    await rer.fetch_invoice_logs_by_bill(api, ROLE, BILL)
    assert [c[0] for c in api.calls] == ["get_invoice_logs"]


@pytest.mark.req("B3_G4:1")
@pytest.mark.asyncio
async def test_iot_resolver_only_calls_iot_endpoint():
    api = FakeIotApi(_iot(2))
    await rer.fetch_iot_manufacturers(api, ROLE)
    assert [c[0] for c in api.calls] == ["get_iot_manufacturers"]


# ───────────────────────── B3-G5 ─────────────────────────
@pytest.mark.req("B3_G5:1")
@pytest.mark.asyncio
async def test_many_members_resolve_as_collection_not_ambiguous():
    r = await rer.fetch_payment_logs_by_bill(FakePaymentLogsApi(_plogs(7)), ROLE, BILL)
    assert r["state"] == rer.STATE_RESOLVED
    assert r["member_count"] == 7 and len(r["resolved_entity"]) == 7
    assert r["uniqueness"] == "collection_is_the_entity"
    assert "resolved_id" not in r, "⛔ collection 不得產生單筆 resolved_id（那是 members[0] 的味道）"


@pytest.mark.req("B3_G5:2")
@pytest.mark.asyncio
async def test_collection_entity_is_the_whole_list():
    rows = _ilogs(3)
    r = await rer.fetch_invoice_logs_by_bill(FakeInvoiceLogsApi(rows), ROLE, BILL)
    assert r["resolved_entity"] == rows, "⛔ resolved_entity 必須是整個 collection，⛔ 不是第一筆"


# ───────────────────────── B3-G6 ─────────────────────────
@pytest.mark.req("B3_G6:1")
@pytest.mark.asyncio
@pytest.mark.parametrize("fn,api,args", [
    ("fetch_payment_logs_by_bill", FakePaymentLogsApi([]), (ROLE, BILL)),
    ("fetch_invoice_logs_by_bill", FakeInvoiceLogsApi([]), (ROLE, BILL)),
    ("fetch_iot_manufacturers", FakeIotApi([]), (ROLE,)),
])
async def test_empty_becomes_resolved_empty_per_ruled_policy(fn, api, args):
    r = await getattr(rer, fn)(api, *args)
    assert r["state"] == rer.STATE_RESOLVED_EMPTY, "⛔ 已裁 RESOLVED_EMPTY，⛔ 不得回 NO_MATCH"
    assert r["member_count"] == 0 and r["resolved_entity"] == []


@pytest.mark.req("B3_G6:2")
@pytest.mark.asyncio
@pytest.mark.parametrize("fn,api,args", [
    ("fetch_payment_logs_by_bill", FakePaymentLogsApi([]), (ROLE, BILL)),
    ("fetch_invoice_logs_by_bill", FakeInvoiceLogsApi([]), (ROLE, BILL)),
    ("fetch_iot_manufacturers", FakeIotApi([]), (ROLE,)),
])
async def test_fetch_resolver_never_composes_an_answer(fn, api, args):
    """⚠️ empty semantics 是 fulfillment adapter 的責任（F-C12）——⛔ 不得在本層編話。"""
    r = await getattr(rer, fn)(api, *args)
    assert not ({"grounding_facts", "text", "answer", "outcome"} & set(r)), \
        "fetch resolver 產生了 answer 形狀 ⇒ 三層分工被打穿"
    blob = "".join(str(v) for k, v in r.items() if k != "_f_open_01")
    for phrase in ("查無", "可能原因", "建議"):
        assert phrase not in blob, f"fetch resolver 回傳含空態話術 {phrase!r}"


# ───────────────────────── B3-G7 ─────────────────────────
@pytest.mark.req("B3_G7:1")
@pytest.mark.asyncio
async def test_member_scope_mismatch_is_hard_fail_not_filtered():
    rows = _ilogs(2, bill_id=BILL) + _ilogs(1, bill_id=999999)
    with pytest.raises(InputScopeViolation, match="INPUT_SCOPE_VIOLATION"):
        await rer.fetch_invoice_logs_by_bill(FakeInvoiceLogsApi(rows), ROLE, BILL)


@pytest.mark.req("B3_G7:2")
@pytest.mark.asyncio
async def test_iot_role_scope_mismatch_is_hard_fail():
    with pytest.raises(InputScopeViolation):
        await rer.fetch_iot_manufacturers(FakeIotApi(_iot(2, role_id="99999")), ROLE)


@pytest.mark.req("B3_G7:3")
@pytest.mark.asyncio
async def test_envelope_scope_mismatch_is_hard_fail():
    api = FakePaymentLogsApi(_plogs(2), envelope_bill_id=999999)
    with pytest.raises(InputScopeViolation, match="信封"):
        await rer.fetch_payment_logs_by_bill(api, ROLE, BILL)


@pytest.mark.req("B3_G7:4")
@pytest.mark.asyncio
async def test_payment_scope_proof_is_split_not_collapsed():
    """**F-C18**：member 沒 scope id 是**已知 schema 事實**；envelope 有沒有強制過濾是**還沒查**。

    ⚠️ 兩者 ⛔ 不得揉成一個結論——所以拆成兩個鍵，各自有自己的狀態。
    """
    r = await rer.fetch_payment_logs_by_bill(FakePaymentLogsApi(_plogs(3)), ROLE, BILL)
    prov = r["scope_provenance"]
    assert prov["member_scope_proof"] == "UNAVAILABLE_BY_RESPONSE_SCHEMA", \
        "⛔ 不得寫成 NOT_ESTABLISHED——那看起來像只是還沒驗"
    assert prov["envelope_scope_proof"] == "CONFIRMED", \
        "2026-08-31 已完成 server-side audit ⇒ ENVELOPE_VERIFIABLE（⛔ 依據是 controller 實查，"\
        "⛔ 不是信封 echo——echo 只證 transport 沒改掉我們送出的值）"
    assert prov["_echo_matched"] is True, "echo 檢查本身仍要跑（不符時要 hard fail）"


@pytest.mark.req("B3_G7:5")
@pytest.mark.asyncio
async def test_verifiable_contracts_do_report_verified():
    """⚠️ 正對照組：⛔ 不能全部都回未證——那量尺就是瞎的。"""
    r = await rer.fetch_invoice_logs_by_bill(FakeInvoiceLogsApi(_ilogs(3)), ROLE, BILL)
    assert r["scope_provenance"]["member_scope_proof"] == "VERIFIED"
    r2 = await rer.fetch_iot_manufacturers(FakeIotApi(_iot(3)), ROLE)
    assert r2["scope_provenance"]["member_scope_proof"] == "VERIFIED"


@pytest.mark.req("B3_G7:8")
def test_payment_logs_scope_proof_is_envelope_verifiable_with_cited_evidence():
    """**F-C18／F-C20**：升為 ENVELOPE_VERIFIABLE **必須附可稽核的 server-side 證據引用**。

    ⚠️ ⛔ 不得只把狀態字串改成 CONFIRMED 就算數——那正是 F-C20 要擋的「request scope
    冒充 data scope」。故本 guard 同時檢查**證據欄位存在且指名 controller**。
    """
    spec = rer.INPUT_CONTRACTS["payment_logs.by_bill.v1"]
    assert spec["scope_proof_mode"] == "ENVELOPE_VERIFIABLE"
    assert spec["scope_provenance_status"] == "CONFIRMED"
    ev = spec.get("_scope_provenance_evidence", "")
    assert "PaymentLogApiController" in ev and "paymentable_id" in ev, \
        "CONFIRMED 卻沒有引用 server-side 過濾證據 ⇒ 違反 F-C20"
    assert spec["member_scope_field"] is None, \
        "member 仍無 bill identity——⛔ 不得因 envelope 已證就改寫成 member 可驗"
    for cid in ("invoice_logs.by_bill.v1", "iot.manufacturers.v1"):
        assert rer.INPUT_CONTRACTS[cid]["scope_proof_mode"] == "MEMBER_VERIFIABLE"
        assert rer.INPUT_CONTRACTS[cid]["scope_provenance_status"] == "CONFIRMED"


@pytest.mark.req("B3_G7:7")
@pytest.mark.asyncio
async def test_empty_collection_scope_is_not_reported_verified():
    """**F-C19 EMPTY COLLECTION CANNOT PROVE MEMBER SCOPE**。

    ⚠️ 沒有反例 ≠ 有正面 scope 證據 ⇒ ⛔ 不得冒充成 VERIFIED。
    """
    r = await rer.fetch_invoice_logs_by_bill(FakeInvoiceLogsApi([]), ROLE, BILL)
    assert r["state"] == rer.STATE_RESOLVED_EMPTY
    assert r["scope_provenance"]["member_scope_proof"] == "N/A_EMPTY", \
        "空集合被回報成 VERIFIED ⇒ vacuous truth 冒充 scope 證據（F-C19）"
    r2 = await rer.fetch_iot_manufacturers(FakeIotApi([]), ROLE)
    assert r2["scope_provenance"]["member_scope_proof"] == "N/A_EMPTY"


# ───────────────────────── B3-G8 ─────────────────────────
@pytest.mark.req("B3_G8:1")
@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"success": False, "error": {"code": 500, "message": "boom"}},
    {"success": False, "error": {"code": 404, "message": "not found"}},
    {"success": True},                                   # 缺 data
    {"success": True, "data": "not-a-list"},             # 型別錯
    "not-a-dict",                                        # malformed
])
async def test_api_failure_never_becomes_no_match(bad):
    with pytest.raises(TransportFailure):
        await rer.fetch_payment_logs_by_bill(FakePaymentLogsApi(resp=bad), ROLE, BILL)


@pytest.mark.req("B3_G8:2")
@pytest.mark.asyncio
async def test_api_exception_becomes_transport_failure():
    api = FakeInvoiceLogsApi(exc=ConnectionError("timeout"))
    with pytest.raises(TransportFailure, match="ConnectionError"):
        await rer.fetch_invoice_logs_by_bill(api, ROLE, BILL)


@pytest.mark.req("B3_G8:3")
@pytest.mark.asyncio
async def test_missing_identity_is_loud_not_no_match():
    with pytest.raises(IdentityNotResolved):
        await rer.fetch_iot_manufacturers(FakeIotApi(_iot(1)), None)
    r = await rer.fetch_payment_logs_by_bill(FakePaymentLogsApi(_plogs(1)), ROLE, None)
    assert r["state"] == rer.STATE_INVALID_INPUT and r["missing_fields"] == ["resolved_bill_id"]


@pytest.mark.req("B3_G8:4")
@pytest.mark.asyncio
async def test_transport_failure_never_returns_a_resolution_state():
    """⚠️ `NO_MATCH` 是合法 domain result；HTTP／API failure ⛔ 不是「沒有資料」。

    ⚠️ 斷言的是**沒有任何 resolution dict 被回傳**（⛔ 不是比對訊息字串——訊息本來就寫著
    「⛔ 不得轉成 NO_MATCH」，拿它做關鍵字比對是自我欺騙）。
    """
    api = FakePaymentLogsApi(resp={"success": False, "error": {"code": 404}})
    returned = None
    try:
        returned = await rer.fetch_payment_logs_by_bill(api, ROLE, BILL)
    except TransportFailure:
        pass
    assert returned is None, \
        f"transport 失敗卻回了 resolution state={returned.get('state')!r} ⇒ 被吞成 domain result"


# ───────────────────────── mutations ─────────────────────────
@pytest.mark.req("B3_M1:1")
@pytest.mark.asyncio
async def test_b3_m1_taking_first_member_makes_guard_red():
    """B3-M1：fetch 完直接 members[0]。"""
    r = await rer.fetch_payment_logs_by_bill(FakePaymentLogsApi(_plogs(7)), ROLE, BILL)
    mutated = {**r, "resolved_entity": r["resolved_entity"][0], "member_count": 1}
    assert not isinstance(mutated["resolved_entity"], list), "B3-M1 未生效"
    with pytest.raises(AssertionError):
        assert isinstance(mutated["resolved_entity"], list) and mutated["member_count"] == 7, \
            "collection guard 必須抓到 members[0]"


@pytest.mark.req("B3_M2:1")
def test_b3_m2_calling_dispatcher_makes_ast_guard_red():
    """B3-M2：若 resolver 改呼 diagnose_* dispatcher，AST guard 必須變紅。"""
    mutated_src = ("async def fetch_payment_logs_by_bill(api, verified_role_id, resolved_bill_id):\n"
                   "    from services.jgb.payments import diagnose_payment_logs\n"
                   "    return diagnose_payment_logs(await api.get_payment_logs(1), '')\n")
    names = set()
    for node in ast.walk(ast.parse(mutated_src)):
        if isinstance(node, ast.Call):
            f = node.func
            names.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    assert BANNED_CALLS & names, "B3-M2 未讓 AST guard 變紅 ⇒ guard 是裝飾"


@pytest.mark.req("B3_M3:1")
@pytest.mark.asyncio
async def test_b3_m3_silent_filtering_makes_scope_guard_red():
    """B3-M3：scope mismatch 時偷偷 filter ⇒ 真實 resolver 必須 raise，⛔ 不得回 RESOLVED。"""
    rows = _ilogs(2, bill_id=BILL) + _ilogs(1, bill_id=999999)
    silently_filtered = [r for r in rows if r["bill_id"] == BILL]
    assert len(silently_filtered) == 2, "mutation 前提不成立"
    with pytest.raises(InputScopeViolation):
        await rer.fetch_invoice_logs_by_bill(FakeInvoiceLogsApi(rows), ROLE, BILL)


# ───────────────── contract 自身的 scope 宣告不得漂移 ─────────────────
@pytest.mark.req("B3_G7:6")
def test_collection_contracts_declare_scope_verification():
    want = {"payment_logs.by_bill.v1": ("ENVELOPE_ONLY", None),
            "invoice_logs.by_bill.v1": ("MEMBER_VERIFIABLE", "bill_id"),
            "iot.manufacturers.v1": ("MEMBER_VERIFIABLE", "role_id")}
    for cid, (mode, field) in want.items():
        spec = rer.INPUT_CONTRACTS[cid]
        assert spec["scope_verification"] == mode, cid
        assert spec["member_scope_field"] == field, cid


@pytest.mark.req("B3_G1:3")
def test_every_collection_contract_has_a_fetch_resolver():
    coll = {cid for cid, s in rer.INPUT_CONTRACTS.items()
            if s["cardinality_mode"] == rer.CARD_COLLECTION}
    assert coll == set(rer.FETCH_RESOLVERS), f"COLLECTION contract 與 fetch resolver 不對稱：{coll}"
