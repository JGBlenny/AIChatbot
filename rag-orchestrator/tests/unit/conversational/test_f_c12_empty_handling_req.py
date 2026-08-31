"""unit：F-C12 EMPTY RESOLUTION ≠ EMPTY ANSWER SEMANTICS（業主凍結 2026-08-30）。

```text
empty_collection_policy   只決定 [] 是否為**已成功解析**的 capability input
empty_input_handling      決定 capability 對 [] **要說什麼** —— 屬 fulfillment binding
```
⚠️ 同一 shared input contract 底下，不同 responsibility 對同一個 `[]` **可以有不同回答**
⇒ empty answer semantics ⛔ 不能塞進 shared input contract。

```text
DIRECT_SUPPORTED   invoice_issue_failure／invoice_invalid_failure／credit_card_failure
ADAPTER_REQUIRED   payment_not_reflected／iot_binding_failure
NOT_YET_REVIEWED   auto_pay_failure  ⚠️ **⛔ 不因同 family 就自動繼承**
```
"""
import pytest

from services import fulfillment_registry as fr
from services import responsibility_entity_resolution as rer

pytestmark = pytest.mark.unit


# ───────────────── 三個 collection contract 的裁定已寫入 ─────────────────
@pytest.mark.req("FC12_POLICY:1")
@pytest.mark.parametrize("cid", ["payment_logs.by_bill.v1", "invoice_logs.by_bill.v1",
                                  "iot.manufacturers.v1"])
def test_empty_policy_is_resolved_empty(cid):
    assert rer.INPUT_CONTRACTS[cid]["empty_collection_policy"] == rer.EMPTY_RESOLVED_EMPTY


@pytest.mark.req("FC12_POLICY:2")
def test_resolved_empty_is_executable_input():
    """⚠️ 「bill 存在但 logs=[]」是**已解析**的 input，⛔ 不是 entity 不存在。"""
    r = rer.resolve_collection("payment_logs.by_bill.v1", [], scope_value=716317)
    assert r["state"] == rer.STATE_RESOLVED_EMPTY
    assert r["state"] in rer.EXECUTABLE_STATES
    assert r["resolved_entity"] == []


# ───────────────── DIRECT_SUPPORTED：三個分支自己就處理得了 ─────────────────
@pytest.mark.req("FC12_DIRECT:1")
@pytest.mark.parametrize("mod,fn,frag", [
    ("services.jgb.invoices", "_diagnose_issue_failure", "查無發票開立紀錄"),
    ("services.jgb.invoices", "_diagnose_invalid_failure", "查無發票作廢紀錄"),
    ("services.jgb.payments", "_diagnose_credit_card_failure", "查無信用卡付款紀錄"),
])
def test_direct_supported_empty_handling(mod, fn, frag):
    import importlib
    f = getattr(importlib.import_module(mod), fn)
    out = f([])
    assert frag in out, f"{fn} 對空集合的回答已改變 ⇒ DIRECT_SUPPORTED 判定需重審"


@pytest.mark.req("FC12_DIRECT:2")
def test_auto_pay_failure_is_not_assumed_from_family():
    """⚠️ R-16 **⛔ 不得因同 family 就繼承** R-15 的 DIRECT_SUPPORTED——必須自己跑。"""
    from services.jgb.payments import _diagnose_auto_pay_failure
    out = _diagnose_auto_pay_failure([])
    # ⚠️ 這裡**只記錄事實**，⛔ 不宣稱它合格：空清單下仍列出通用原因，未明說「查無紀錄」
    assert "自動扣款相關紀錄" in out
    assert "查無" not in out.split("自動扣款失敗可能原因")[0], \
        "若已改為明說查無，則 R-16 可升 DIRECT_SUPPORTED——需重審本斷言"


# ───────────────── ADAPTER_REQUIRED：R-12 ─────────────────
@pytest.mark.req("FC12_R12:1")
def test_r12_empty_is_degenerate_without_adapter():
    """⚠️ 正對照：先證明**不加 adapter 就是退化的**，否則本 guard 無鑑別力。"""
    from services.jgb.payments import _diagnose_payment_not_reflected
    raw = _diagnose_payment_not_reflected([])
    assert raw.strip() == "以下是此帳單的付款交易紀錄：", "退化形狀已改變 ⇒ 需重審"


@pytest.mark.req("FC12_R12:2")
def test_r12_adapter_handles_empty():
    out = fr.payment_not_reflected_facts_adapter([], {})
    assert out["empty_input"] is True
    assert "查無此帳單的金流交易日誌" in out["grounding_facts"]


@pytest.mark.req("FC12_R12:3")
def test_r12_adapter_delegates_when_non_empty():
    from services.jgb.payments import _diagnose_payment_not_reflected
    # ⚠️ fixture 必須含 `response`——見 PROD-DEFECT-01：第一筆缺 response 會 UnboundLocalError
    logs = [{"id": 1, "status": 1, "amount": 18000, "created_at": "2026-08-01 10:00:00",
             "action": "pay", "response": {"Status": "1", "Message": "OK"}}]
    out = fr.payment_not_reflected_facts_adapter(logs, {})
    assert out["empty_input"] is False
    assert out["grounding_facts"] == _diagnose_payment_not_reflected(logs)


# ───────────────── ADAPTER_REQUIRED：R-23（語義錯誤）─────────────────
@pytest.mark.req("FC12_R23:1")
def test_r23_empty_without_adapter_is_semantically_wrong():
    """⚠️ 正對照：空清單卻宣稱「所有廠商狀態正常」——這是 adapter 必要性的證據。"""
    from services.jgb.iot import _diagnose_binding_failure
    raw = _diagnose_binding_failure([])
    assert "所有 IoT 廠商帳號狀態正常" in raw, "語義缺陷形狀已改變 ⇒ 需重審 domain gap 判定"


@pytest.mark.req("FC12_R23:2")
def test_r23_adapter_handles_empty():
    out = fr.iot_binding_failure_facts_adapter([], {})
    assert out["empty_input"] is True
    assert "目前沒有綁定任何 IoT 廠商" in out["grounding_facts"]
    assert "所有 IoT 廠商帳號狀態正常" not in out["grounding_facts"]


# ───────────────── R-16（F-C22）：auto_pay 空態 adapter ─────────────────
@pytest.mark.req("FC22_R16:1")
def test_r16_empty_adapter_replaces_causal_assertion_with_reviewed_facts():
    """⚠️ 空清單時 ⛔ 不得再宣告「自動扣款失敗可能原因」——那是無事件卻斷言成因。"""
    out = fr.auto_pay_failure_facts_adapter([], {})
    assert out["outcome"] == "FACTS" and out["empty_input"] is True
    assert out["grounding_facts"] == fr.EMPTY_PAYMENT_LOGS_FACTS, \
        "⛔ 不得重新發明空態文字——沿用同一 input contract 的 reviewed 空態"
    assert "自動扣款失敗可能原因" not in out["grounding_facts"]
    assert "信用卡授權已過期" not in out["grounding_facts"]


@pytest.mark.req("FC22_R16:2")
def test_r16_non_empty_still_uses_the_named_branch_unchanged():
    """⚠️ **F-C22**：補的是空態 domain，⛔ 不改變 underlying capability identity。"""
    from services.jgb.payments import _diagnose_auto_pay_failure
    logs = [{"created_at": "2026-08-01T10:00:00", "action": "auto_pay",
             "response": {"Status": "FAIL", "Message": "額度不足"}, "note": ""}]
    out = fr.auto_pay_failure_facts_adapter(logs, {})
    assert out["empty_input"] is False
    assert out["grounding_facts"] == _diagnose_auto_pay_failure(logs), \
        "non-empty 路徑必須逐字等同具名分支——⛔ adapter 不得改寫語義"


@pytest.mark.req("FC22_R16:3")
def test_r16_adapter_never_enters_the_dispatcher():
    """⚠️ ⛔ 不得呼叫 `diagnose_payment_logs`（會把 user_question 帶回來，違反 F-C1）。"""
    import ast
    import inspect
    import textwrap
    names = set()
    for node in ast.walk(ast.parse(textwrap.dedent(
            inspect.getsource(fr.auto_pay_failure_facts_adapter)))):
        if isinstance(node, (ast.Attribute, ast.Name)):
            names.add(getattr(node, "attr", None) or getattr(node, "id", ""))
    assert "diagnose_payment_logs" not in names
    assert "_diagnose_auto_pay_failure" in names, "⚠️ 正對照：必須真的呼叫到具名分支"


# ───────────────── drift 偵測：adapter 文字須與 legacy 空態一致 ─────────────
@pytest.mark.req("FC12_DRIFT:1")
def test_adapter_empty_text_matches_legacy_dispatcher_text():
    """⚠️ adapter ⛔ 不呼叫 dispatcher（會把 question 帶回來），改以 guard 比對文字，
    使 legacy 空態文字**日後若改動**能被偵測到。"""
    from services.jgb.iot import diagnose_iot
    from services.jgb.payments import diagnose_payment_logs
    assert diagnose_payment_logs([], "") == fr.EMPTY_PAYMENT_LOGS_FACTS
    assert diagnose_iot([], "") == fr.EMPTY_IOT_MANUFACTURERS_FACTS


@pytest.mark.req("FC12_DRIFT:2")
def test_adapters_are_not_registered_yet():
    """⚠️ F-G1：⛔ 不得「找到具名函式就先啟用」——R-12／R-23 仍為 proposed。"""
    ids = set(fr._REGISTRY)
    assert "payment.not_reflected_diagnosis.v1" not in ids
    assert "iot.binding_failure_diagnosis.v1" not in ids
    assert "payment.auto_pay_failure_diagnosis.v1" not in ids   # R-16（F-C22）同樣仍 proposed


# ───────────────── PROD-DEFECT-01（僅記錄現況，⛔ 不修）─────────────────
@pytest.mark.req("FC12_R12:4")
def test_r12_records_known_production_defect():
    """⚠️ **PROD-DEFECT-01**：`_diagnose_payment_not_reflected` 的 `code` 只在
    `if response:` 內指派，卻在迴圈末無條件讀取 ⇒ **第一筆 log 缺 `response` 即 UnboundLocalError**。

    ⚠️ 本測試**只記錄現況**，⛔ 不修 production、⛔ 不 xfail 掩蓋——
    修不修是業主的裁定（它不在本輪 scope 內，也不是本輪造成的）。
    """
    from services.jgb.payments import _diagnose_payment_not_reflected
    first_without_response = [{"id": 1, "action": "pay", "amount": 100,
                               "created_at": "2026-08-01 10:00", "status": 1}]
    with pytest.raises(UnboundLocalError):
        _diagnose_payment_not_reflected(first_without_response)
    # 對照：第一筆有 response 就正常；第二筆缺則沿用前一筆的 code（⚠️ 也是可疑行為）
    ok = _diagnose_payment_not_reflected(
        [{"id": 1, "response": {"Status": "1"}, "status": 1}, {"id": 2, "status": 1}])
    assert "付款交易紀錄" in ok


# ───────────────── tenant.summary 的 singleton 未證 ─────────────────
@pytest.mark.req("FC12_TENANT:1")
def test_tenant_singleton_runtime_contract_not_established():
    spec = rer.INPUT_CONTRACTS["tenant.summary.v1"]
    assert spec["cardinality_mode"] == rer.CARD_SINGLETON
    assert spec["singleton_runtime_contract"] == "NOT_ESTABLISHED", \
        "⛔ 不得因 API 形狀是 dict 就宣稱 identity resolution 已證"
