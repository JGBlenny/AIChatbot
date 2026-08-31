"""T4-D1：**responsibility completion handler**（2026-08-30，業主裁定）。

⚠️ 與 legacy `_legacy_complete_form` **完全分離**——共用的是 form completion **transport**，
⛔ 不是 completion authority。兩者只有「都是表單完成」這個共性。

```text
1. resume_fulfillment(session)                 ← authority exact restore（F-C5）
2. resolve entity by input_contract_id         ← B1／B3（⛔ 不走 legacy first-row）
3. require RESOLVED                            ← ⛔ 其餘一律不執行
4. execute committed fulfillment binding       ← F-C7 registry（⛔ 無 owner prose）
5. FINAL_TEXT       → 直接回 FulfillmentExecutionResult
   GROUNDING_FACTS  → D2 `present()` → ResponsibilityGroundingResult（T4-D2，2026-08-31）
6. emit responsibility result（**三個 family**，依型別分流）
```

## ⛔ 不轉成假 row

回傳 **FulfillmentExecutionResult 形狀**，⛔ 不是 `{knowledge_id, answer, form_id}`——
那會把 row authority 從後門帶回來（T4 最初的 blocker 就是這個形狀）。

## ⚠️ AMBIGUOUS 也留在 responsibility handler

使用者選完 entity 後的第二次 resume **仍從最上層**依 `session_authority_mode` 回到本 handler，
⛔ 不得掉回 legacy completion——這才把 F-C5 延伸到多回合。
"""
from typing import Any, Dict, Mapping, Optional

from services import fulfillment_registry as fr
from services import grounding_presentation as gp
from services import responsibility_bill_resolution as rbr
from services import responsibility_entity_resolution as rer
from services import responsibility_session as rsess

# ══════════════════════════════════════════════════════════════════════════
# W-G1：input_contract_id → **exact registered resolver**（2026-08-31）
#
# ```text
# ⛔ 不允許 fallback ／ 動態組名 getattr ／ 猜函式
# ⛔ 不允許「查不到 resolver 就走 legacy 查詢路徑」（F-C6）
# ```
# ⚠️ 每個 contract 的 resolver **簽名不同**（有的要 bill_ref、有的只要 role）⇒ 這裡用
# **顯式 spec 表**，⛔ 不做統一 arity 的假設（那正是動態猜測的溫床）。
#
# `input_kind` 三種：
# ```text
# ROLE_AND_REF   resolver(api, role_id, ref)      ref 取自 form 的 form_ref_field
# ROLE_ONLY      resolver(api, role_id)
# UPSTREAM_REF   先跑 upstream_contract 取得 **RESOLVED 的 entity id**，再 resolver(api, role_id, id)
# ```
# ⚠️ **UPSTREAM_REF 是關鍵**：`payment_logs.by_bill.v1` 的 `resolved_bill_id` 依定義是
# **已解析的帳單 id**，⛔ 不得拿使用者輸入的 `bill_ref` 冒充——那會讓「已解析」變成假設。
# ══════════════════════════════════════════════════════════════════════════
KIND_ROLE_AND_REF = "ROLE_AND_REF"
KIND_ROLE_ONLY = "ROLE_ONLY"
KIND_UPSTREAM_REF = "UPSTREAM_REF"

_RESOLVER_SPECS = {
    "bill.by_ref.v1": {"fn": rbr.resolve_bill_by_ref, "kind": KIND_ROLE_AND_REF,
                       "form_ref_field": "bill_ref"},
    "estate.by_ref.v1": {"fn": rer.resolve_estate_by_ref, "kind": KIND_ROLE_AND_REF,
                         "form_ref_field": "estate_ref"},
    "subscription.current.v1": {"fn": rer.resolve_subscription_current, "kind": KIND_ROLE_ONLY},
    "iot.manufacturers.v1": {"fn": rer.fetch_iot_manufacturers, "kind": KIND_ROLE_ONLY},
    "payment_logs.by_bill.v1": {"fn": rer.fetch_payment_logs_by_bill, "kind": KIND_UPSTREAM_REF,
                                "upstream_contract": "bill.by_ref.v1"},
    "invoice_logs.by_bill.v1": {"fn": rer.fetch_invoice_logs_by_bill, "kind": KIND_UPSTREAM_REF,
                                "upstream_contract": "bill.by_ref.v1"},
    # ⚠️ tenant.summary.v1 **刻意不接**：`resolve_tenant_summary` 需 verified_user_id，
    #    而目前沒有合法的 keyword → user_id resolver（F-C13／R-24 IDENTITY_BLOCKED）。
    #    ⛔ 接上去只會讓它在 runtime 才炸；此處**明示缺席**才看得見。
}

#: 相容既有呼叫端／測試的視圖（⛔ 只讀）
_RESOLVERS = {cid: spec["fn"] for cid, spec in _RESOLVER_SPECS.items()}


class ResponsibilityInputResolutionResult(dict):
    """responsibility path 的**未解析**結果（AMBIGUOUS／NO_MATCH／INVALID_INPUT）。

    ⚠️ 與 `FulfillmentExecutionResult` 是**兩個 result family**——D1-E converter 依型別分流。
    ⚠️ `RESOLVED` **⛔ 不得**以本型別對外出現：那代表 T4-C executor 被跳過了。
    """


class ResponsibilityGroundingResult(dict):
    """**第三個 result family**（T4-D2，2026-08-31）：GROUNDING_FACTS 經 D2 present() 後的結果。

    ⚠️ 與 `FulfillmentExecutionResult`（FINAL_TEXT）／`ResponsibilityInputResolutionResult`
    （未解析）**依型別分流**，⛔ 不靠 key 猜。⚠️ 新增 family ⇒ D1-E converter 必須同步，
    ⛔ 否則會掉進「未知 responsibility result 型別」的 hard fail（那是刻意的：⛔ 不得靜默降級）。
    """


class ResponsibilityCompletionError(RuntimeError):
    """responsibility completion 前置不成立——⚠️ 大聲失敗，⛔ 不得落回 legacy。"""


def _needs(plan: Mapping[str, Any], form_data: Mapping[str, Any]) -> Any:
    """從 form 取出識別欄位值。⚠️ 只服務 `ROLE_AND_REF`／`UPSTREAM_REF` 的**上游** ref。"""
    cid = plan["input_contract_id"]
    if rer.INPUT_CONTRACTS.get(cid) is None:
        raise ResponsibilityCompletionError(f"未註冊的 input_contract_id：{cid!r}")
    spec = _RESOLVER_SPECS[cid]
    field = (spec.get("form_ref_field")
             or _RESOLVER_SPECS[spec["upstream_contract"]]["form_ref_field"])
    return (form_data or {}).get(field)


async def _resolve_input(cid: str, api: Any, role_id: str,
                         collected_data: Mapping[str, Any]) -> Dict[str, Any]:
    """依 **exact registered spec** 解析 input（W-G1）。

    ⚠️ `UPSTREAM_REF` 走**兩階段**：上游必須先回 `RESOLVED`，才把它的 `resolved_id`
    餵給下游 fetch resolver。⛔ 上游未 RESOLVED 就**原樣回傳上游結果**——
    使用者要先把帳單選定，⛔ 不得拿 raw ref 硬跑下游。
    """
    spec = _RESOLVER_SPECS.get(cid)
    if spec is None:
        raise ResponsibilityCompletionError(
            f"input_contract {cid!r} 尚無 responsibility resolver"
            f"——⛔ 不得改用 legacy 查詢路徑（F-C6），⛔ 也不得動態猜函式（W-G1）")
    kind = spec["kind"]
    if kind == KIND_ROLE_ONLY:
        return await spec["fn"](api, role_id)
    if kind == KIND_ROLE_AND_REF:
        return await spec["fn"](api, role_id, (collected_data or {}).get(spec["form_ref_field"]))
    if kind == KIND_UPSTREAM_REF:
        up_cid = spec["upstream_contract"]
        up = _RESOLVER_SPECS[up_cid]
        upstream = await up["fn"](api, role_id,
                                  (collected_data or {}).get(up["form_ref_field"]))
        if upstream.get("state") != rer.STATE_RESOLVED:
            # ⚠️ 上游未唯一化 ⇒ 直接把上游結果交還（AMBIGUOUS／NO_MATCH／INVALID_INPUT）
            return dict(upstream, _blocked_downstream=cid,
                        _why="⚠️ 上游 entity 未 RESOLVED ⇒ ⛔ 不得以 raw ref 冒充 resolved id")
        return await spec["fn"](api, role_id, upstream.get("resolved_id"))
    raise ResponsibilityCompletionError(f"未知的 resolver kind：{kind!r}")


async def complete_responsibility_form(session_state: Mapping[str, Any], form_schema: Mapping[str, Any],
                                       collected_data: Mapping[str, Any],
                                       db_pool: Any = None,
                                       api: Optional[Any] = None) -> Dict[str, Any]:
    """responsibility-mode 的表單完成。

    ⚠️ 簽名刻意**不收** user_question／face／category——與 `fulfillment_registry.execute()`
    同一原則：no-reroute 由**結構**保證（F-C1）。
    """
    plan = rsess.resume_fulfillment(session_state, collected_data)   # ① authority exact restore

    if api is None:
        from services.jgb_system_api import JGBSystemAPI
        api = JGBSystemAPI()
    role_id = (session_state.get("vendor_id") if session_state.get("vendor_id") is not None
               else (session_state.get("metadata") or {}).get("role_id"))

    resolution = await _resolve_input(plan["input_contract_id"], api, str(role_id),
                                      collected_data)                              # ②

    if resolution["state"] not in rer.EXECUTABLE_STATES:                            # ③
        # ⚠️ 走既有 UX 通道，但 **仍是 responsibility 結果**——⛔ 不轉成 legacy row 形狀，
        #    ⛔ 且下一輪 resume 必須再回到本 handler（F-C5 多回合）。
        return ResponsibilityInputResolutionResult(
            kind="responsibility_entity_unresolved",
            responsibility_id=plan["responsibility_id"],
            fulfillment_binding_id=plan["fulfillment_binding_id"],
            input_contract_id=plan["input_contract_id"],
            state=resolution["state"], resolution=resolution,
            _no_execution="⚠️ 非 RESOLVED ⇒ executor **未被呼叫**")

    result = fr.execute(plan, resolution)                                          # ④
    if result["output_mode"] == fr.OUTPUT_FINAL_TEXT:                              # ⑤a
        return result
    if result["output_mode"] == fr.OUTPUT_GROUNDING_FACTS:                         # ⑤b（T4-D2）
        return _present_grounding(plan, result)
    raise ResponsibilityCompletionError(
        f"未知 output_mode {result['output_mode']!r}——⛔ runtime 不得猜")


def _present_grounding(plan: Mapping[str, Any],
                       result: Mapping[str, Any]) -> "ResponsibilityGroundingResult":
    """**T4-D2 出口**：GROUNDING_FACTS → `grounding_presentation.present()`。

    ⚠️ **W-G2**：本段 ⛔ 不得重入 legacy dispatcher／`show_knowledge`／`row.answer`。
    ⚠️ `present()` 的簽名本身就沒有 user_question／face／category ⇒ no-reroute 由**結構**保證。
    ⚠️ payload 的 `responsibility_id` 一律取自 **plan**（committed authority），
    ⛔ 不從 outcome dict 讀——那是 adapter 的輸出，⛔ 不是 authority 來源。
    """
    outcome = result.get("grounding_outcome")
    if not isinstance(outcome, dict) or "outcome" not in outcome:
        raise ResponsibilityCompletionError(
            f"GROUNDING_FACTS 結果缺 outcome dict（實得 {type(outcome).__name__}）"
            f"——⛔ 不得以字串帶過")
    payload = {k: v for k, v in outcome.items() if k != "responsibility_id"}
    payload["responsibility_id"] = plan["responsibility_id"]        # ⚠️ authority 來自 plan
    presented = gp.present(payload)
    return ResponsibilityGroundingResult(
        responsibility_id=plan["responsibility_id"],
        binding_id=plan["fulfillment_binding_id"],
        input_contract_id=plan["input_contract_id"],
        output_mode=fr.OUTPUT_GROUNDING_FACTS,
        presentation=dict(presented),
        _authority_from="plan（committed），⛔ 不是 adapter 輸出，⛔ 不是 member row")
