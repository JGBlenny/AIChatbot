"""T4-D1：**responsibility completion handler**（2026-08-30，業主裁定）。

⚠️ 與 legacy `_legacy_complete_form` **完全分離**——共用的是 form completion **transport**，
⛔ 不是 completion authority。兩者只有「都是表單完成」這個共性。

```text
1. resume_fulfillment(session)                 ← authority exact restore（F-C5）
2. resolve entity by input_contract_id         ← B1／B3（⛔ 不走 legacy first-row）
3. require RESOLVED                            ← ⛔ 其餘一律不執行
4. execute committed fulfillment binding       ← F-C7 registry（⛔ 無 owner prose）
5. require output_mode == FINAL_TEXT           ← D1 第一版只服務 FINAL_TEXT
6. emit responsibility final-text result
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
from services import responsibility_bill_resolution as rbr
from services import responsibility_entity_resolution as rer
from services import responsibility_session as rsess

#: input_contract_id → 顯式解析器（⛔ 不存 callable path 進 session；此處才解析）
_RESOLVERS = {"bill.by_ref.v1": rbr.resolve_bill_by_ref}


class ResponsibilityInputResolutionResult(dict):
    """responsibility path 的**未解析**結果（AMBIGUOUS／NO_MATCH／INVALID_INPUT）。

    ⚠️ 與 `FulfillmentExecutionResult` 是**兩個 result family**——D1-E converter 依型別分流。
    ⚠️ `RESOLVED` **⛔ 不得**以本型別對外出現：那代表 T4-C executor 被跳過了。
    """


class ResponsibilityCompletionError(RuntimeError):
    """responsibility completion 前置不成立——⚠️ 大聲失敗，⛔ 不得落回 legacy。"""


def _needs(plan: Mapping[str, Any], form_data: Mapping[str, Any]) -> str:
    """從 input contract 取出識別欄位值。⚠️ 目前只服務 bill.by_ref.v1。"""
    spec = rer.INPUT_CONTRACTS.get(plan["input_contract_id"])
    if spec is None:
        raise ResponsibilityCompletionError(
            f"未註冊的 input_contract_id：{plan['input_contract_id']!r}")
    field = spec["required_fields"][0]
    return (form_data or {}).get(field)


async def complete_responsibility_form(session_state: Mapping[str, Any], form_schema: Mapping[str, Any],
                                       collected_data: Mapping[str, Any],
                                       db_pool: Any = None,
                                       api: Optional[Any] = None) -> Dict[str, Any]:
    """responsibility-mode 的表單完成。

    ⚠️ 簽名刻意**不收** user_question／face／category——與 `fulfillment_registry.execute()`
    同一原則：no-reroute 由**結構**保證（F-C1）。
    """
    plan = rsess.resume_fulfillment(session_state, collected_data)   # ① authority exact restore

    resolver = _RESOLVERS.get(plan["input_contract_id"])
    if resolver is None:
        raise ResponsibilityCompletionError(
            f"input_contract {plan['input_contract_id']!r} 尚無 responsibility resolver"
            f"——⛔ 不得改用 legacy 查詢路徑（F-C6）")
    if api is None:
        from services.jgb_system_api import JGBSystemAPI
        api = JGBSystemAPI()
    role_id = (session_state.get("vendor_id") if session_state.get("vendor_id") is not None
               else (session_state.get("metadata") or {}).get("role_id"))

    resolution = await resolver(api, str(role_id), _needs(plan, collected_data))   # ②

    if resolution["state"] != rer.STATE_RESOLVED:                                  # ③
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
    if result["output_mode"] != fr.OUTPUT_FINAL_TEXT:                              # ⑤
        raise ResponsibilityCompletionError(
            f"D1 第一版只服務 FINAL_TEXT，實際 {result['output_mode']}"
            f"——⛔ GROUNDING_FACTS 的 presentation adapter 尚未建立（T4-D2）")
    return result                                                                  # ⑥
