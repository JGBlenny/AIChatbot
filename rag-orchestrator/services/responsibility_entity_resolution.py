"""T4-B1：**responsibility-only entity resolution layer**（2026-08-30，業主凍結）。

## 為什麼是獨立 layer，而不是在 legacy 裡加 branch

業主裁定：**legacy 的 `matched[0]` / `rows[0]` 原地不動**；C2 **根本不走到那些
first-row authority sites**，而不是「進去後再加 branch 修正」。

```text
⛔ 不把 `if responsibility_mode:` 散落進 contracts.py／bills.py 各處
✅ 抽成本層，只在 responsibility execution seam 呼叫
   input_contract_id ＋ form_data ＋ endpoint rows → ResolutionResult
```

## 三種 cardinality_mode（業主裁定 2026-08-30）

⚠️ **entity-selection contract 與 collection-input contract 是兩件事**，
⛔ 不得把 `>1` 一律解讀成 ambiguity。

### T4-B-C1 — SELECT_ONE EXACT ENTITY RESOLUTION

⚠️ **Applies only when `cardinality_mode = SELECT_ONE`。**

```text
0 valid entity                                    → NO_MATCH
1 verified entity                                 → RESOLVED
>1 valid entities **without deterministic uniqueness proof** → AMBIGUOUS

MUST NOT: choose first ／ choose highest DB order ／ choose earliest returned
```

### T4-B-C2 — SINGLETON INPUT

```text
semantic singleton absent            → NO_MATCH
single valid object                  → RESOLVED
multiple competing singleton objects → AMBIGUOUS ／ contract violation
```
⚠️ 若 API 回傳型別**本來就是單一 dict**，⛔ 不要為了套 cardinality 人工轉成 list 再數量判斷。

### T4-B-C3 — COLLECTION INPUT（F-C11 COLLECTION IS THE ENTITY）

```text
0 valid scoped members  → 依 **empty_collection_policy**（NO_MATCH ／ RESOLVED_EMPTY）
>=1 valid scoped members → RESOLVED，resolved_entity ＝ **collection 本身**

⛔ member count MUST NOT trigger AMBIGUOUS
⛔ first-member selection is forbidden
```

⚠️ **collection 仍要有 scope identity**——⛔ 不是「API 回什麼 list 就全吃」：
contract 必須宣告 `collection_scope_key`（例：`resolved_bill_id`）；
若成員混入不同 scope ⇒ **INPUT_CONTRACT_VIOLATION**，⛔ 不當合法 collection。

## ⚠️ 兩件事先前被混在一起

```text
entity exists?                      ／  capability input is sufficiently resolved?
```
對 collection responsibility，`0 rows` **不一定**表示 entity 不存在——可能是
「bill 已 resolved，但 payment_logs = []」。⇒ `NO_MATCH` 保留給**上游 required entity／scope
本身找不到**；空集合則由 `empty_collection_policy` 決定，讓診斷 capability 有機會
**把「沒有紀錄」當證據**。

**唯一例外**：已被 review 過的 deterministic selection contract 能把集合唯一化
（正例：`select_point_refund()`；⛔ 反例：`rows[0]`）。

## 兩個 operational identity 是分開的

```text
fulfillment_binding_id   找到 entity **之後怎麼回答**
resolver_id              **怎麼找到** entity
```
⚠️ R-31 本身就是證據：「怎麼找到 entity」≠「找到後怎麼回答」。
⛔ resolver 一律不存 Python callable path 當 authority——存穩定 `resolver_id`，由 code registry 映射。

## ⚠️ 可重用 UX 通道，⛔ 不重用它的 authority logic

AMBIGUOUS 可沿用既有列候選 UI，但 resume 回來**仍須回到同一** responsibility_id ／
fulfillment_binding_id ／ input_contract_id——⛔ 使用者選了一筆 entity ⛔ 不得因此重新 retrieval。
"""
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol

STATE_RESOLVED = "RESOLVED"
#: RESOLVED 的子態：collection 已 scope 鎖定但成員為 0（**邏輯上仍是 RESOLVED**）
STATE_RESOLVED_EMPTY = "RESOLVED_EMPTY"
STATE_AMBIGUOUS = "AMBIGUOUS"
STATE_NO_MATCH = "NO_MATCH"
STATE_INVALID_INPUT = "INVALID_INPUT"
#: ⚠️ 只有 RESOLVED 能進 T4-C direct capability
TERMINAL_STATES = (STATE_RESOLVED, STATE_RESOLVED_EMPTY, STATE_AMBIGUOUS,
                   STATE_NO_MATCH, STATE_INVALID_INPUT)
#: ⚠️ 只有這兩態能進 T4-C direct capability
EXECUTABLE_STATES = (STATE_RESOLVED, STATE_RESOLVED_EMPTY)

#: ⚠️ **cardinality_mode 是 input contract 的一部分，⛔ 不是 runtime 猜出來的**（業主裁定 2026-08-30）
CARD_SINGLETON = "SINGLETON"
CARD_SELECT_ONE = "SELECT_ONE"
CARD_COLLECTION = "COLLECTION"
VALID_CARDINALITY = (CARD_SINGLETON, CARD_SELECT_ONE, CARD_COLLECTION)

#: COLLECTION 專屬：空集合是「查無」還是「合法的空」——⛔ 不得全域拍死
EMPTY_NO_MATCH = "NO_MATCH"
EMPTY_RESOLVED_EMPTY = "RESOLVED_EMPTY"
VALID_EMPTY_POLICY = (EMPTY_NO_MATCH, EMPTY_RESOLVED_EMPTY)

AMBIGUITY_EXACT_IDENTIFIER = "exact_identifier"
AMBIGUITY_REVIEWED_SELECTION_CONTRACT = "reviewed_selection_contract"


class EntityResolutionError(RuntimeError):
    """resolution 契約違反——⚠️ 大聲失敗，⛔ 不得以 first row 帶過。"""


#: input contract registry（machine contract；⛔ 不只是名稱）
INPUT_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "bill.by_ref.v1": {
        "entity_type": "bill",
        "cardinality_mode": CARD_SELECT_ONE,
        "required_fields": ["bill_ref"],
        "resolver_id": "bill.by_ref",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
    },
    "contract.current_entity.v1": {
        "entity_type": "contract",
        "cardinality_mode": CARD_SELECT_ONE,
        "required_fields": ["contract_ref"],
        "resolver_id": "contract.by_ref",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
    },
    "point_refund.bill_by_contract.v1": {
        "entity_type": "bill",
        "cardinality_mode": CARD_SELECT_ONE,
        "required_fields": ["contract_ref"],
        "resolver_id": "point_refund_bill.by_contract",
        "ambiguity_policy": AMBIGUITY_REVIEWED_SELECTION_CONTRACT,
        "_selection_contract": "POINT_REFUND_BILL_SELECTION（select_point_refund）"
                               "——⚠️ 這是**唯一例外**的正例：reviewed deterministic uniqueness",
    },
    "late_fee.bill_or_contract.v1": {
        "entity_type": "bill_or_contract",
        "cardinality_mode": CARD_SELECT_ONE,
        "required_fields": [],          # ⚠️ tagged alternatives，見 _accepts
        "_accepts": ["resolved_contract", "resolved_late_fee_bill"],
        "resolver_id": "late_fee.entity",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
        "_note": "⚠️ ⛔ 不是模糊的 `row`——必須是 tagged alternatives 之一",
    },
    # ── 六個新 machine contracts（T4-B input-contract closure，2026-08-30）─────
    # ⚠️ cardinality_mode 由業主裁定；**empty_collection_policy 尚待逐筆裁定**（留 None）。
    "payment_logs.by_bill.v1": {
        "member_scope_field": None,          # ⚠️ member 列**無** bill identity（實查）
        "scope_verification": "ENVELOPE_ONLY",
        "scope_proof_mode": "ENVELOPE_VERIFIABLE_CANDIDATE",   # ⚠️ **候選**，⛔ 尚未成立
        "scope_provenance_status": "NOT_ESTABLISHED",
        "_f_c18_note":
            "⚠️ **F-C18**：member 不帶 scope identity ⛔ 不等於 scope 無法證明——若 production fetch "
            "本身以已解析 scope **強制過濾**且有可稽核實作證據，可由 transport envelope 建立 provenance。"
            "⚠️ 但 `get_payment_logs(bill_id=…)` 的**函式簽名／請求參數 ⛔ 都不算證據**；"
            "信封回吐的 `bill_id` 只是**把我們送過去的值回傳**，⛔ 更不是過濾證據。"
            "⇒ 需唯讀實查 controller／repository／SQL 的 `WHERE bill_id = :resolved_bill_id` "
            "並附 negative control（拿掉 filter → guard RED）才可升 ENVELOPE_VERIFIABLE。",
        "envelope_scope_key": "bill_id",     # 信封層 top-level bill_id（adapter 已帶出）
        "_scope_note":
            "⚠️ `collection_scope_key='resolved_bill_id'` 是**上游變數名**，⛔ 不是 member 欄位名："
            "payment_logs 列只有 payment_id／role_id／transaction_id ⇒ `resolve_collection` 的 "
            "`if scope_key in m` 對本 contract **恆為空檢查**。⛔ 不得因此當 scope 已證 —— "
            "member 層 verification 由 fetch resolver 顯式負責，且結論是 **NOT_ESTABLISHED**（F-C17）。",
        "entity_type": "payment_logs",
        "cardinality_mode": CARD_COLLECTION,
        "collection_scope_key": "resolved_bill_id",
        "empty_collection_policy": EMPTY_RESOLVED_EMPTY,   # ⚠️ 業主裁定 2026-08-30
        "required_fields": ["resolved_bill_id"],
        "resolver_id": "payment_logs.by_bill",
        "ambiguity_policy": None,               # ⚠️ COLLECTION ⛔ 不適用 ambiguity policy
        "_capability_empty_behavior":
            "實測 `_diagnose_payment_not_reflected([])` → '以下是此帳單的付款交易紀錄：\n'"
            "（**退化**：只剩空標題）；⚠️ 有意義的空集合說明在**入口** diagnose_payment_logs，"
            "⛔ 不在具名分支 ⇒ 若裁 RESOLVED_EMPTY，adapter 必須自行處理空態。",
    },
    "invoice_logs.by_bill.v1": {
        "scope_proof_mode": "MEMBER_VERIFIABLE",
        "scope_provenance_status": "CONFIRMED",
        "member_scope_field": "bill_id",     # ⚠️ member 列**帶** bill_id（實查）⇒ 可逐筆驗
        "scope_verification": "MEMBER_VERIFIABLE",
        "envelope_scope_key": None,
        "_scope_note":
            "⚠️ 欄位名 `bill_id` ≠ contract 的 `collection_scope_key='resolved_bill_id'` "
            "⇒ `resolve_collection` 的檢查同樣 vacuous；由 fetch resolver 以 member_scope_field 顯式驗。",
        "entity_type": "invoice_logs",
        "cardinality_mode": CARD_COLLECTION,
        "collection_scope_key": "resolved_bill_id",
        "empty_collection_policy": EMPTY_RESOLVED_EMPTY,   # ⚠️ 業主裁定 2026-08-30
        "required_fields": ["resolved_bill_id"],
        "resolver_id": "invoice_logs.by_bill",
        "ambiguity_policy": None,
        "_capability_empty_behavior":
            "實測 `_diagnose_issue_failure([])` → '查無發票開立紀錄。可能的原因：…'；"
            "`_diagnose_invalid_failure([])` → '查無發票作廢紀錄。…' ⇒ **兩者對空集合都有意義**。",
    },
    "iot.manufacturers.v1": {
        "scope_proof_mode": "MEMBER_VERIFIABLE",
        "scope_provenance_status": "CONFIRMED",
        "member_scope_field": "role_id",     # ⚠️ 三者中**唯一**與 collection_scope_key 同名
        "scope_verification": "MEMBER_VERIFIABLE",
        "envelope_scope_key": None,
        "entity_type": "iot_manufacturers",
        "cardinality_mode": CARD_COLLECTION,
        "collection_scope_key": "role_id",
        "empty_collection_policy": EMPTY_RESOLVED_EMPTY,   # ⚠️ 業主裁定 2026-08-30
        "required_fields": [],
        "resolver_id": "iot.manufacturers",
        "ambiguity_policy": None,
        "_capability_empty_behavior":
            "⚠️ **實測發現語義缺陷**：`_diagnose_binding_failure([])` → "
            "'目前已綁定的 IoT 廠商：\n\n\n所有 IoT 廠商帳號狀態正常…' "
            "——**空清單卻宣稱「所有廠商狀態正常」**。"
            "有意義的空態說明在入口 `diagnose_iot`（'目前沒有綁定任何 IoT 廠商…'）。"
            "⇒ 若裁 RESOLVED_EMPTY 而不處理空態，會**產出錯誤語義**。",
    },
    "subscription.current.v1": {
        "entity_type": "subscription",
        "cardinality_mode": CARD_SINGLETON,
        "empty_collection_policy": None,        # ⚠️ SINGLETON 不適用
        "required_fields": [],
        "resolver_id": "subscription.current",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
        "_note": "⚠️ API 回傳本來就是單一 dict ⇒ ⛔ 不得為了套 cardinality 人工轉 list 再數量判斷"
                 "（T4-B-C2）。dict present → RESOLVED；absent → NO_MATCH。",
    },
    "tenant.summary.v1": {
        "entity_type": "tenant_summary",
        "cardinality_mode": CARD_SINGLETON,          # ⚠️ **proposal**——見 _singleton_runtime_contract
        "singleton_runtime_contract": "NOT_ESTABLISHED",
        "empty_collection_policy": None,
        "required_fields": ["tenant_ref"],
        "resolver_id": "tenant.summary",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
        "_note": "⚠️ 唯讀盤查（2026-08-30）：API 層形狀支持 SINGLETON，但 **identity resolution 未證**。"
                 "① endpoint `/api/external/v1/tenants/{user_id}/summary` —— user_id **已在 path**，"
                 "⇒ 呼叫前身分即已固定，⛔ 無候選清單、⛔ 無 rows[0]／data[0]；"
                 "② `data` 為單一 dict（mock 對齊 TenantApiController@summary 的 ExistedLessee 模型）；"
                 "③ formatter `_format_tenant_summary(data if isinstance(data, dict) else {})` "
                 "——契約即預期 dict。"
                 "⚠️ **但**：form `jgb_tenant_query` 的 api_config 是 "
                 "`user_id: '{form.tenant_keyword}'` —— 欄位名為 **keyword**，卻**逐字**當作 "
                 "user_id 塞進 URL path。⇒ **沒有 tenant identity resolution 這一步**："
                 "使用者若輸入姓名而非 id，會被當成 id 使用。"
                 "⚠️ 這**不是** F-C3 的 first-row 問題（根本沒有清單），而是 "
                 "**identity assumed, not resolved** ⇒ singleton_runtime_contract = NOT_ESTABLISHED。",
    },
    "estate.by_ref.v1": {
        "entity_type": "estate",
        "cardinality_mode": CARD_SELECT_ONE,
        "required_fields": ["estate_ref"],
        "resolver_id": "estate.by_ref",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
        "_note": "⚠️ 與 bill.by_ref 同形；⛔ 必須取代 `face_estate_response` 的 `rows[0]`。",
    },
}


def result(state: str, input_contract_id: str, entity_type: str, **extra: Any) -> Dict[str, Any]:
    if state not in TERMINAL_STATES:
        raise EntityResolutionError(f"未知的 resolution state：{state!r}")
    out = {"state": state, "input_contract_id": input_contract_id, "entity_type": entity_type}
    out.update(extra)
    if state not in EXECUTABLE_STATES:
        out["_not_executable"] = ("⚠️ 只有 RESOLVED 能進 T4-C direct capability；"
                                  "本 state 走既有 UX 通道，⛔ 但 ⛔ 不得重新 retrieval")
    return out


def resolve_collection(input_contract_id: str, members, scope_value=None) -> Dict[str, Any]:
    """COLLECTION 型 input 的解析（T4-B-C3 ／ F-C11）。

    ⚠️ **member count ⛔ 永不觸發 AMBIGUOUS**；⛔ 也不得取第一筆。
    """
    spec = INPUT_CONTRACTS.get(input_contract_id)
    if spec is None:
        raise EntityResolutionError(f"未註冊的 input_contract_id：{input_contract_id!r}")
    if spec.get("cardinality_mode") != CARD_COLLECTION:
        raise EntityResolutionError(
            f"{input_contract_id} 的 cardinality_mode 是 {spec.get('cardinality_mode')!r}"
            f"——⛔ 不得以 collection 方式解析")
    policy = spec.get("empty_collection_policy")
    if policy not in VALID_EMPTY_POLICY:
        # ⚠️ 大聲失敗：⛔ 不得預設成 NO_MATCH——那正是「0 rows 被錯當不存在」的對稱 bug
        raise EntityResolutionError(
            f"{input_contract_id} 的 empty_collection_policy 尚未裁定（{policy!r}）"
            f"——⛔ 不得全域拍死；先逐筆 review")
    items = [m for m in (members or []) if isinstance(m, dict)]
    scope_key = spec.get("collection_scope_key")
    if scope_key and scope_value is not None:
        # ⚠️ collection 必須已被上游 scope 鎖定；混入其他 scope ⇒ INPUT_CONTRACT_VIOLATION
        bad = [m for m in items if scope_key in m and m.get(scope_key) != scope_value]
        if bad:
            raise EntityResolutionError(
                f"{input_contract_id}：collection 混入其他 {scope_key}"
                f"（{sorted({m.get(scope_key) for m in bad})}）——INPUT_CONTRACT_VIOLATION")
    if not items:
        state = (STATE_NO_MATCH if policy == EMPTY_NO_MATCH else STATE_RESOLVED_EMPTY)
        return result(state, input_contract_id, spec["entity_type"],
                      resolved_entity=[], member_count=0, empty_collection_policy=policy)
    return result(STATE_RESOLVED, input_contract_id, spec["entity_type"],
                  resolved_entity=items, member_count=len(items),
                  uniqueness="collection_is_the_entity")


def resolve(input_contract_id: str, form_data: Mapping[str, Any], rows: Optional[List[dict]],
            selection_contract: Optional[Callable[[List[dict]], Any]] = None) -> Dict[str, Any]:
    """依 **reviewed input contract** 把 endpoint rows 收斂成單一 entity。

    ⚠️ **⛔ 絕不** choose first／highest DB order／earliest returned。
    """
    spec = INPUT_CONTRACTS.get(input_contract_id)
    if spec is None:
        raise EntityResolutionError(
            f"未註冊的 input_contract_id：{input_contract_id!r}"
            f"——⛔ 不得因為缺 resolver 就 fallback 取第一筆")
    etype = spec["entity_type"]

    missing = [f for f in spec["required_fields"] if not (form_data or {}).get(f)]
    if missing:
        return result(STATE_INVALID_INPUT, input_contract_id, etype, missing_fields=missing)
    accepts = spec.get("_accepts")
    if accepts and not any((form_data or {}).get(k) for k in accepts):
        return result(STATE_INVALID_INPUT, input_contract_id, etype,
                      missing_fields=[f"one of {accepts}"])

    valid = [r for r in (rows or []) if isinstance(r, dict) and r]
    if not valid:
        return result(STATE_NO_MATCH, input_contract_id, etype)
    if len(valid) == 1:
        return result(STATE_RESOLVED, input_contract_id, etype,
                      resolved_id=valid[0].get("id"), resolved_entity=valid[0],
                      uniqueness="single_returned_entity")

    # >1：⚠️ 只有 **reviewed deterministic selection contract** 才可唯一化
    if spec["ambiguity_policy"] == AMBIGUITY_REVIEWED_SELECTION_CONTRACT and selection_contract:
        state, selected, candidates = selection_contract(valid)
        if selected is not None:
            return result(STATE_RESOLVED, input_contract_id, etype,
                          resolved_id=selected.get("id"), resolved_entity=selected,
                          uniqueness="reviewed_selection_contract",
                          selection_state=state)
        if candidates:
            return result(STATE_AMBIGUOUS, input_contract_id, etype,
                          candidates=candidates, selection_state=state)
        return result(STATE_NO_MATCH, input_contract_id, etype, selection_state=state)
    # ⛔ 沒有 uniqueness proof ⇒ AMBIGUOUS，**⛔ 不得取第一筆**
    return result(STATE_AMBIGUOUS, input_contract_id, etype, candidates=valid)


def assert_executable(res: Mapping[str, Any]) -> Dict[str, Any]:
    """T4-C 的入口守門：⛔ 非 RESOLVED 一律不得執行 capability。"""
    if res.get("state") != STATE_RESOLVED:
        raise EntityResolutionError(
            f"resolution state={res.get('state')!r}，⛔ 不得進 direct capability")
    return dict(res)


# ══════════════════════════════════════════════════════════════════════════
# T4-B4：SINGLETON ／ SELECT_ONE 的 **execution closure**（2026-08-30）
#
# ⚠️ resolver signature **只收已審核 transport input**——⛔ 無 user_question／face／
#    category：input resolution 本身 ⛔ 不得變成另一個 semantic rerouter。
# ══════════════════════════════════════════════════════════════════════════

class IdentityNotResolved(EntityResolutionError):
    """**F-C13**：request identity 未經 reviewed resolution——⚠️ 大聲失敗。

    ```text
    API 回傳單一 dict **只證 output cardinality**。
    若 request identity 未經 reviewed resolution，⛔ 不得因此把 input 標 RESOLVED。
    ```
    """


class EstateApi(Protocol):
    async def get_estate_detail(self, estate_id: Any = None, **kw) -> Dict[str, Any]: ...
    async def get_estates(self, role_id: str, keyword: str = "", **kw) -> Dict[str, Any]: ...


async def resolve_estate_by_ref(api: "EstateApi", role_id: str,
                                estate_ref: Optional[str]) -> Dict[str, Any]:
    """`estate.by_ref.v1`（SELECT_ONE）——比照 `bill.by_ref` precedent。

    ⚠️ **exact path 優先**：production 有 `GET /estates/{id}` 的單筆深查
    （`get_estate_detail`）⇒ 數字 ref 直接走它，⛔ 不為了重用 legacy search 而製造候選歧義。
    ⛔ 一律不得使用 `rows[0]`／`face_estate_response` 的既有 first-row path。
    """
    cid, etype = "estate.by_ref.v1", "estate"
    ref = str(estate_ref).strip() if estate_ref is not None else ""
    if not ref:
        return result(STATE_INVALID_INPUT, cid, etype, missing_fields=["estate_ref"])

    if ref.isdigit():                       # ⚠️ exact-ID path 優先
        resp = await api.get_estate_detail(estate_id=int(ref))
        rows = _normalize_rows(resp)
        if not rows:
            return result(STATE_NO_MATCH, cid, etype, estate_ref=ref, stage="estate_detail")
        if len(rows) > 1:
            return result(STATE_AMBIGUOUS, cid, etype, candidates=rows, stage="estate_detail")
        return result(STATE_RESOLVED, cid, etype, resolved_id=rows[0].get("id"),
                      resolved_entity=rows[0], uniqueness="exact_estate_id",
                      stage="estate_detail")

    rows = _normalize_rows(await api.get_estates(role_id, keyword=ref))
    # ⚠️ sentinel（{"found": False}）不是實體 ⇒ 視為查無
    rows = [r for r in rows if r.get("found") is not False]
    if not rows:
        return result(STATE_NO_MATCH, cid, etype, estate_ref=ref, stage="estate_search")
    if len(rows) > 1:
        # ⛔ **絕不** rows[0]
        return result(STATE_AMBIGUOUS, cid, etype, candidates=rows, stage="estate_search")
    return result(STATE_RESOLVED, cid, etype, resolved_id=rows[0].get("id"),
                  resolved_entity=rows[0], uniqueness="unique_keyword_match",
                  stage="estate_search")


class SubscriptionApi(Protocol):
    async def get_subscription(self, role_id: str, **kw) -> Dict[str, Any]: ...


async def resolve_subscription_current(api: "SubscriptionApi",
                                       verified_role_id: Optional[str]) -> Dict[str, Any]:
    """`subscription.current.v1`（SINGLETON）。

    ⚠️ ⛔ 不套 list cardinality：endpoint `GET /roles/{role_id}/subscription` 回單一 dict。
    ⚠️ **lookup scope 必須已唯一**——`verified_role_id` 是**已驗證**的身分；
    ⛔ identity 若是猜的，⛔ 不得只因 endpoint 回 dict 就叫 resolved（F-C13）。
    """
    cid, etype = "subscription.current.v1", "subscription"
    if not verified_role_id:
        raise IdentityNotResolved(
            "subscription.current.v1 需要 **verified_role_id**"
            "——⛔ 不得以未驗證的身分呼叫（F-C13）")
    resp = await api.get_subscription(str(verified_role_id))
    if not (resp or {}).get("success"):
        return result(STATE_NO_MATCH, cid, etype, role_id=verified_role_id)
    data = (resp or {}).get("data")
    if data is None:
        return result(STATE_NO_MATCH, cid, etype, role_id=verified_role_id)
    if not isinstance(data, dict):
        # ⚠️ 回了 list／純量 ＝ contract violation，⛔ 不得人工轉成 list 再數量判斷（T4-B-C2）
        return result(STATE_INVALID_INPUT, cid, etype,
                      contract_violation=f"expected dict, got {type(data).__name__}")
    if not data:
        return result(STATE_NO_MATCH, cid, etype, role_id=verified_role_id)
    return result(STATE_RESOLVED, cid, etype, resolved_id=verified_role_id,
                  resolved_entity=data, uniqueness="semantic_singleton_by_verified_role")


class TenantSummaryApi(Protocol):
    async def get_tenant_summary(self, role_id: str, user_id: str, **kw) -> Dict[str, Any]: ...


async def resolve_tenant_summary(api: "TenantSummaryApi", verified_role_id: Optional[str],
                                 verified_user_id: Optional[str] = None,
                                 tenant_keyword: Optional[str] = None) -> Dict[str, Any]:
    """`tenant.summary.v1`（SINGLETON）——⚠️ 本 resolver 的重點是**負控制**。

    ## F-C13 在這裡的具體形狀

    ```text
    endpoint 回單一 dict  →  只證 **output cardinality**
    tenant_keyword        →  ⛔ **不得**原樣當 user_id（legacy api_config 正是如此）
    ```

    ⚠️ 目前**沒有**合法的 `keyword → user_id` resolver ⇒ 只給 keyword 時本函式
    **大聲失敗**，⛔ 不呼叫 summary endpoint。這比把錯誤 legacy wiring 包進新 contract 更有價值。
    """
    cid, etype = "tenant.summary.v1", "tenant_summary"
    if not verified_role_id:
        raise IdentityNotResolved("tenant.summary.v1 需要 verified_role_id")
    if not verified_user_id:
        raise IdentityNotResolved(
            "tenant.summary.v1 需要 **verified_user_id**；"
            f"僅有 tenant_keyword={tenant_keyword!r} ⛔ 不得原樣當 user_id"
            "——identity assumed, not resolved（F-C13）")
    resp = await api.get_tenant_summary(str(verified_role_id), str(verified_user_id))
    if not (resp or {}).get("success"):
        return result(STATE_NO_MATCH, cid, etype, user_id=verified_user_id)
    data = (resp or {}).get("data")
    if not isinstance(data, dict):
        return result(STATE_INVALID_INPUT, cid, etype,
                      contract_violation=f"expected dict, got {type(data).__name__}")
    if not data:
        return result(STATE_NO_MATCH, cid, etype, user_id=verified_user_id)
    return result(STATE_RESOLVED, cid, etype, resolved_id=verified_user_id,
                  resolved_entity=data, uniqueness="verified_user_id")


def _normalize_rows(resp: Optional[Dict[str, Any]]) -> List[dict]:
    """API 回應 → 列表。⚠️ 單物件 dict **包成單元素 list**（⛔ `else []` 會整個丟掉）。"""
    if not resp or not resp.get("success"):
        return []
    data = resp.get("data")
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict) and r]
    if isinstance(data, dict) and data:
        return [data]
    return []


# ══════════════════════════════════════════════════════════════════════════
# T4-B5 / B3：三個 COLLECTION contract 的 **fetch resolver**（2026-08-31，業主凍結）
#
# ## F-C17 — FETCH RESOLVER IS TRANSPORT, NOT SEMANTIC ROUTING
#
# ```text
# 可以：接收已確定的 scope identity ／ 呼叫固定 API endpoint ／ 驗證回傳 scope
#       ／ 把 members 交給既有 resolve_collection()
# 不可以：接 user_question／face／category ／ 呼叫 diagnose_* dispatcher
#         ／ 挑 member[0] ／ 選 capability／binding ／ 依資料內容改 responsibility
# ```
# ⚠️ 真正的風險 ⛔ 不是演算法，而是 **fetch resolver 不小心重新長成 dispatcher**。
#
# ## 三層分工（⛔ 不得在本層重做 empty semantics）
#
# ```text
# fetch  →  resolve input  →  execute binding  →  empty adapter ／ direct branch
# ```
# 三個 contract 的 `empty_collection_policy` 皆已裁 **RESOLVED_EMPTY** ⇒ 本層只負責把 `[]`
# 交給 `resolve_collection()`。⛔ **不得** `if not rows: return "查無付款紀錄…"`——
# 那是 fulfillment adapter 的責任（F-C12）。
#
# ## ⚠️ scope 檢查為什麼不能只靠 resolve_collection
#
# `collection_scope_key` 記的是**上游變數名**（`resolved_bill_id`），⛔ 不是 member 欄位名。
# 實查三個真實 member 形狀後：
#
# ```text
# payment_logs   member 無任何 bill identity  → scope_verification = ENVELOPE_ONLY
# invoice_logs   member 帶 bill_id            → MEMBER_VERIFIABLE（欄位名不同名）
# iot            member 帶 role_id            → MEMBER_VERIFIABLE（唯一同名）
# ```
# ⇒ `resolve_collection` 的 `if scope_key in m` 對前兩者**恆為空檢查**。member 層驗證改由
# 本層依 `member_scope_field` **顯式**執行；⛔ 不得因 endpoint 叫 `get_payment_logs(bill_id=…)`
# 就當 member scope 已證。
# ══════════════════════════════════════════════════════════════════════════

class InputScopeViolation(EntityResolutionError):
    """**B3-G7**：回傳的 member 不屬於請求的 scope——⚠️ 大聲失敗。

    ⛔ **不得** filter 掉不合 scope 的 member 然後假裝沒看到：silent filtering 會把
    upstream ／ API contract defect **藏掉**。
    """


class TransportFailure(EntityResolutionError):
    """**B3-G8**：API exception ／ `success=False` ／ malformed response。

    ```text
    NO_MATCH 是合法 domain result；HTTP／API failure ⛔ 不是「沒有資料」。
    ```
    ⚠️ `resolved_bill_id` 依定義**已由上游 bill.by_ref 解析過** ⇒ 本層再遇 404 屬 transport／
    authorization 異常，⛔ 不是「查無帳單」。⚠️ JGBSystemAPI 把 404 與 5xx 都收斂成
    `success=False` ⇒ **domain_vs_transport_discrimination = NOT_ESTABLISHED**，第一版一律 hard fail。
    """


class PaymentLogsApi(Protocol):
    async def get_payment_logs(self, role_id: str, bill_id: Any = None,
                               **kw) -> Dict[str, Any]: ...


class InvoiceLogsApi(Protocol):
    async def get_invoice_logs(self, role_id: str, bill_id: Any = None,
                               **kw) -> Dict[str, Any]: ...


class IotManufacturersApi(Protocol):
    async def get_iot_manufacturers(self, role_id: str, **kw) -> Dict[str, Any]: ...


def _require_success(cid: str, resp: Any, what: str) -> Dict[str, Any]:
    """B3-G8：⛔ 失敗一律 hard fail，⛔ 不得轉成 NO_MATCH。"""
    if not isinstance(resp, dict):
        raise TransportFailure(
            f"{cid}：{what} 回了 {type(resp).__name__}，非 dict——malformed response"
            f"，⛔ 不得當成『沒有資料』")
    if not resp.get("success"):
        err = (resp.get("error") or {})
        raise TransportFailure(
            f"{cid}：{what} success=False（code={err.get('code')!r}）"
            f"——⚠️ transport／authorization 失敗，⛔ 不得轉成 NO_MATCH")
    return resp


def _members(cid: str, resp: Dict[str, Any]) -> List[dict]:
    data = resp.get("data")
    if data is None:
        raise TransportFailure(f"{cid}：回應缺 `data` 鍵——malformed，⛔ 不得當成空集合")
    if not isinstance(data, list):
        raise TransportFailure(
            f"{cid}：`data` 是 {type(data).__name__}，COLLECTION contract 要求 list"
            f"——⛔ 不得人工轉型")
    return [m for m in data if isinstance(m, dict) and m]


def _verify_member_scope(cid: str, members: List[dict], scope_value: Any) -> Dict[str, Any]:
    """依 contract 的 `member_scope_field` 逐筆驗 scope。

    ⚠️ **⛔ 絕不 filter**——不合 scope 即 `InputScopeViolation`（B3-G7）。
    ⚠️ 若 contract 宣告 member 無 scope 欄位，回報 **NOT_ESTABLISHED**，
    ⛔ 不得因「檢查沒報錯」就當已驗（那正是 vacuous check 的陷阱）。
    """
    spec = INPUT_CONTRACTS[cid]
    field = spec.get("member_scope_field")
    if not field:
        return {"member_scope_proof": "UNAVAILABLE_BY_RESPONSE_SCHEMA",
                "_why": f"{cid} 的 member 列無 scope 欄位（scope_proof_mode="
                        f"{spec.get('scope_proof_mode')!r}）——⚠️ 這是**已知 schema 事實**，"
                        f"⛔ 不是「還沒驗」，也 ⛔ 不得當已驗"}
    if not members:
        # ⚠️ 空集合時「沒有不合 scope 的 member」是**恆真**的 ⇒ ⛔ 不得回報 VERIFIED，
        #    那會讓一個 vacuous truth 冒充成 scope 證據（與本檔開頭記的 vacuous check 同一種病）。
        # **F-C19**：EMPTY COLLECTION CANNOT PROVE MEMBER SCOPE
        return {"member_scope_proof": "N/A_EMPTY", "_field": field, "_checked": 0}
    bad = [m for m in members if str(m.get(field)) != str(scope_value)]
    if bad:
        raise InputScopeViolation(
            f"{cid}：{len(bad)}/{len(members)} 筆 member 的 {field} 不等於請求 scope "
            f"{scope_value!r}（實得 {sorted({str(m.get(field)) for m in bad})}）"
            f"——INPUT_SCOPE_VIOLATION，⛔ 不得 filter 掉後繼續")
    return {"member_scope_proof": "VERIFIED",
            "_field": field, "_checked": len(members)}


def _verify_envelope_scope(cid: str, resp: Dict[str, Any], scope_value: Any) -> Dict[str, Any]:
    spec = INPUT_CONTRACTS[cid]
    key = spec.get("envelope_scope_key")
    if not key:
        return {"envelope_scope_proof": "N/A"}
    if key not in resp:
        return {"envelope_scope_proof": "NOT_ESTABLISHED",
                "_why": f"回應信封缺 {key!r}——⛔ 不得因 endpoint 簽名有 scope 參數就當已證"}
    if str(resp.get(key)) != str(scope_value):
        raise InputScopeViolation(
            f"{cid}：信封 {key}={resp.get(key)!r} 與請求 scope {scope_value!r} 不符"
            f"——INPUT_SCOPE_VIOLATION")
    # ⚠️ **F-C18**：信封值相符只證「回吐了我們送過去的值」，⛔ **不是** production 有強制過濾的證據。
    return {"envelope_scope_proof": INPUT_CONTRACTS[cid].get("scope_provenance_status")
            or "NOT_YET_REVIEWED",
            "_echo_matched": True, "_field": key,
            "_why": "⚠️ 信封 echo 相符 ⛔ 不構成 filtering proof（F-C18）"}


async def fetch_payment_logs_by_bill(api: "PaymentLogsApi", verified_role_id: Optional[str],
                                     resolved_bill_id: Optional[Any]) -> Dict[str, Any]:
    """`payment_logs.by_bill.v1`（COLLECTION）的 fetch resolver。

    ⚠️ ⛔ 不呼叫 `diagnose_payment_logs`——那是 question-keyword dispatcher（S6／F-C1）。
    ⚠️ member 層 scope **無法驗**（列無 bill identity）⇒ 結果帶 `NOT_ESTABLISHED` 供上游判讀。
    """
    cid = "payment_logs.by_bill.v1"
    if not verified_role_id:
        raise IdentityNotResolved(f"{cid} 需要 verified_role_id（F-C13）")
    if resolved_bill_id in (None, ""):
        return result(STATE_INVALID_INPUT, cid, INPUT_CONTRACTS[cid]["entity_type"],
                      missing_fields=["resolved_bill_id"])
    try:
        resp = await api.get_payment_logs(str(verified_role_id), bill_id=resolved_bill_id)
    except TransportFailure:
        raise
    except Exception as exc:                      # B3-G8：⛔ 不得吞成 NO_MATCH
        raise TransportFailure(f"{cid}：get_payment_logs 拋出 {type(exc).__name__}: {exc}") from exc
    resp = _require_success(cid, resp, "get_payment_logs")
    members = _members(cid, resp)
    prov = dict(_verify_envelope_scope(cid, resp, resolved_bill_id))
    prov.update(_verify_member_scope(cid, members, resolved_bill_id))
    out = resolve_collection(cid, members)
    out["scope_provenance"] = prov
    out["scope_value"] = resolved_bill_id
    return out


async def fetch_invoice_logs_by_bill(api: "InvoiceLogsApi", verified_role_id: Optional[str],
                                     resolved_bill_id: Optional[Any]) -> Dict[str, Any]:
    """`invoice_logs.by_bill.v1`（COLLECTION）的 fetch resolver。

    ⚠️ ⛔ 不呼叫 `diagnose_invoice_logs`。
    ⚠️ member 列帶 `bill_id` ⇒ 逐筆驗；不符即 `InputScopeViolation`，⛔ 不 filter。
    ⚠️ 另見 F-OPEN-02：該 endpoint 在 production **不做 role 圈定**（⛔ 本層不代為裁定）。
    """
    cid = "invoice_logs.by_bill.v1"
    if not verified_role_id:
        raise IdentityNotResolved(f"{cid} 需要 verified_role_id（F-C13）")
    if resolved_bill_id in (None, ""):
        return result(STATE_INVALID_INPUT, cid, INPUT_CONTRACTS[cid]["entity_type"],
                      missing_fields=["resolved_bill_id"])
    try:
        resp = await api.get_invoice_logs(str(verified_role_id), bill_id=resolved_bill_id)
    except TransportFailure:
        raise
    except Exception as exc:
        raise TransportFailure(f"{cid}：get_invoice_logs 拋出 {type(exc).__name__}: {exc}") from exc
    resp = _require_success(cid, resp, "get_invoice_logs")
    members = _members(cid, resp)
    prov = dict(_verify_envelope_scope(cid, resp, resolved_bill_id))
    prov.update(_verify_member_scope(cid, members, resolved_bill_id))
    out = resolve_collection(cid, members)
    out["scope_provenance"] = prov
    out["scope_value"] = resolved_bill_id
    return out


async def fetch_iot_manufacturers(api: "IotManufacturersApi",
                                  verified_role_id: Optional[str]) -> Dict[str, Any]:
    """`iot.manufacturers.v1`（COLLECTION）的 fetch resolver。

    ⚠️ ⛔ 不呼叫 `diagnose_iot`。
    ⚠️ **F-OPEN-01 ⛔ 不因本 resolver 完成而關閉**：本層可以要求 `verified_role_id`，但
    production 是否真能提供 verified provenance 仍是 `ROLE_ID_VERIFICATION_PROVENANCE =
    NOT_YET_ESTABLISHED` ⇒ R-23 應為 `FETCH_RESOLVER_EXECUTABILITY = CONFIRMED` ＋
    `ROLE_SCOPE_REACHABILITY = BLOCKED_F_OPEN_01`，⛔ **不是** input closed。
    """
    cid = "iot.manufacturers.v1"
    if not verified_role_id:
        raise IdentityNotResolved(f"{cid} 需要 verified_role_id（F-C13）")
    try:
        resp = await api.get_iot_manufacturers(str(verified_role_id))
    except TransportFailure:
        raise
    except Exception as exc:
        raise TransportFailure(f"{cid}：get_iot_manufacturers 拋出 {type(exc).__name__}: {exc}") from exc
    resp = _require_success(cid, resp, "get_iot_manufacturers")
    members = _members(cid, resp)
    prov = dict(_verify_envelope_scope(cid, resp, verified_role_id))
    prov.update(_verify_member_scope(cid, members, verified_role_id))
    out = resolve_collection(cid, members)
    out["scope_provenance"] = prov
    out["scope_value"] = verified_role_id
    out["_f_open_01"] = ("⚠️ ROLE_SCOPE_REACHABILITY 仍受 F-OPEN-01 限制"
                         "——⛔ 本 resolver green ⛔ 不代表 role scope 已可信")
    return out


#: fetch resolver 的 contract 對照（⛔ 存 contract_id → callable，⛔ 不存 prose）
FETCH_RESOLVERS = {
    "payment_logs.by_bill.v1": fetch_payment_logs_by_bill,
    "invoice_logs.by_bill.v1": fetch_invoice_logs_by_bill,
    "iot.manufacturers.v1": fetch_iot_manufacturers,
}
