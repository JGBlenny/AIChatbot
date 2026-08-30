"""T4-C1：**executable fulfillment registry** ＋ direct capability execution（2026-08-30）。

## F-C7 — EXECUTABLE_BINDING_AUTHORITY（凍結）

```text
runtime capability dispatch **只能**由 reviewed `fulfillment_binding_id → executable adapter`
registry 決定。`owner` ／ `owner_contract` 僅是 **review evidence**，
⛔ 不得成為 runtime dispatch source。
```

⚠️ 本 registry 是 **operational binding registry**，⛔ **不是** Registry V2——
Registry V2 答「這個 responsibility 是什麼」，本檔答「它由哪個 adapter 執行」。

⚠️ 本層**結構上**不接收 `owner` ／ `owner_contract` 參數：即使有人想拿 prose 解析 callable，
也沒有參數可傳（⛔ 不是靠自律，是靠簽名堵掉）。

## binding 必須綁 responsibility_id

⛔ 不可只有 `binding_id → callable`。否則 session corruption 成
`R-05 + receipt.actual_amount.v1` 時 runtime 仍會**執行成功**，但 semantic authority 已錯。

## defense in depth

upstream（B1／B3）已守 resolution state，executor **自己仍再驗一次**——
⛔ 不把正確性只押在呼叫端。
"""
from typing import Any, Callable, Dict, Mapping, Optional

OUTPUT_FINAL_TEXT = "FINAL_TEXT"
OUTPUT_GROUNDING_FACTS = "GROUNDING_FACTS"
VALID_OUTPUT_MODES = (OUTPUT_FINAL_TEXT, OUTPUT_GROUNDING_FACTS)


class ExecutableBindingNotFound(RuntimeError):
    """binding_id 未註冊——⚠️ **⛔ 不得**退回 owner prose 解析／getattr 猜函式。"""


class BindingAuthorityMismatch(RuntimeError):
    """responsibility_id 與 binding_id 不是 reviewed pair。"""


class FulfillmentExecutionError(RuntimeError):
    """執行前置條件不成立（resolution state／entity type／output mode）。"""


class BindingSpec(dict):
    pass


#: reviewed binding registry。⚠️ **只註冊已完成 review 的 binding**——
#: ⛔ 不從 25 筆 proposed owner 自動生成（那等於讓 proposal 取得 execution authority）。
_REGISTRY: Dict[str, BindingSpec] = {}


def register(binding_id: str, *, responsibility_id: str, adapter: Callable[..., Any],
             input_contract_id: str, entity_type: str, output_mode: str) -> None:
    if output_mode not in VALID_OUTPUT_MODES:
        raise ValueError(f"未知 output_mode：{output_mode!r}")
    _REGISTRY[binding_id] = BindingSpec(
        binding_id=binding_id, responsibility_id=responsibility_id, adapter=adapter,
        input_contract_id=input_contract_id, entity_type=entity_type, output_mode=output_mode)


def lookup(binding_id: str, responsibility_id: str) -> BindingSpec:
    """⚠️ 必須同時給 responsibility_id——binding 單獨查得到 ⛔ 不代表它屬於這個責任。"""
    spec = _REGISTRY.get(binding_id)
    if spec is None:
        raise ExecutableBindingNotFound(
            f"binding_id {binding_id!r} 未註冊於 executable registry"
            f"——⛔ 不得改以 owner／owner_contract prose 解析 callable（F-C7）")
    if spec["responsibility_id"] != responsibility_id:
        raise BindingAuthorityMismatch(
            f"{responsibility_id} 與 binding {binding_id!r}（屬 {spec['responsibility_id']}）"
            f"不是 reviewed pair——⛔ 執行得成功 ⛔ 不代表 authority 正確")
    return spec


class FulfillmentExecutionResult(dict):
    """⚠️ **typed** result——D1-E 的 converter 依**型別**分流，⛔ 不靠 `"text" in result` 猜。"""


def execute(plan: Mapping[str, Any], resolution: Mapping[str, Any],
            context: Optional[Mapping[str, Any]] = None) -> FulfillmentExecutionResult:
    """direct committed execution。

    ⚠️ 簽名**只**收 plan／resolution／context ——⛔ 沒有 user_question、⛔ 沒有 face、
    ⛔ 沒有 category、⛔ 沒有 owner prose：F-C1 的 no-reroute 由**結構**保證，⛔ 不靠自律。
    """
    rid = plan["responsibility_id"]
    spec = lookup(plan["fulfillment_binding_id"], rid)

    # defense in depth：executor 自己再驗 resolution state（⛔ 不只依賴 upstream）
    if resolution.get("state") != "RESOLVED":
        raise FulfillmentExecutionError(
            f"resolution state={resolution.get('state')!r} ⛔ 不得進 direct capability")
    if resolution.get("input_contract_id") != spec["input_contract_id"]:
        raise FulfillmentExecutionError(
            f"resolution 的 input_contract={resolution.get('input_contract_id')!r} 與 binding 宣告的 "
            f"{spec['input_contract_id']!r} 不符")
    if resolution.get("entity_type") != spec["entity_type"]:
        raise FulfillmentExecutionError(
            f"entity_type {resolution.get('entity_type')!r} 與 binding 要求的 "
            f"{spec['entity_type']!r} 不符——⛔ 即使函式碰巧讀得到同名欄位也不得執行")
    entity = resolution.get("resolved_entity")
    if not isinstance(entity, dict) or not entity:
        raise FulfillmentExecutionError("resolved_entity 缺漏——⛔ 不得以 member row 代替")

    out = spec["adapter"](entity, dict(context or {}))
    mode = spec["output_mode"]
    if mode == OUTPUT_FINAL_TEXT and not isinstance(out, str):
        raise FulfillmentExecutionError(
            f"binding 宣告 FINAL_TEXT 但 adapter 回 {type(out).__name__}"
            f"——⛔ runtime 不得猜 output mode")
    if mode == OUTPUT_GROUNDING_FACTS:
        # ⚠️ GROUNDING_FACTS 的 adapter 回的是 **outcome dict**（交給 D2 present()），
        #    ⛔ 不是單純字串——四種 outcome 的形狀不同（FACTS／CANDIDATES／NOT_FOUND／
        #    TYPE_MISMATCH），壓成字串會把 candidate 態的結構弄丟。
        if not isinstance(out, dict) or "outcome" not in out:
            raise FulfillmentExecutionError(
                f"GROUNDING_FACTS adapter 必須回帶 outcome 的 dict，實得 {type(out).__name__}"
                f"——⛔ runtime 不得猜 output mode")
    return FulfillmentExecutionResult(
        responsibility_id=rid, binding_id=spec["binding_id"], output_mode=mode,
        entity_id=resolution.get("resolved_id"),
        **({"text": out} if mode == OUTPUT_FINAL_TEXT else {"grounding_outcome": out}),
        _not_transported="⚠️ T4-C 只證 direct execution 正確；"
                         "⛔ 尚未接 routers/chat 或 AnswerFormatter（那是 T4-D）")


# ── 第一個 reviewed binding：R-29（⛔ 只建這一個）──────────────────────────
def receipt_actual_amount_adapter(resolved_bill: Dict[str, Any],
                                  context: Mapping[str, Any]) -> str:
    """`receipt.actual_amount.v1` → `bills._diagnose_receipt(bill)`。

    ⚠️ **⛔ 不呼叫 `diagnose_bill(bill, user_question)`**——那會讓 `'收據'` keyword
    再判一次 semantic owner（違反 F-C1）。本 adapter 直接進具名分支。
    """
    from services.jgb.bills import _diagnose_receipt
    return _diagnose_receipt(resolved_bill)


# ── R-28：direct GROUNDING_FACTS capability ────────────────────────────────
def late_fee_facts_adapter(resolved_entity: Dict[str, Any],
                           context: Mapping[str, Any]) -> Dict[str, Any]:
    """`late_fee.facts.v1` → `bills.build_late_fee_facts(row)`。

    ⚠️ **⛔ 不呼叫 `face_bill_response`**——那裡有 `BILL_FACE_BUILDERS.get(face)` 與
    `is_point_refund_intent(user_question)` 兩道 semantic dispatch（違反 F-C1）。
    ⚠️ builder 經 T4 稽核判為 **NOT_QUESTION_SENSITIVE**，故 ⛔ 不傳 user_question。

    ⚠️ input contract 是 **tagged alternatives**：呼叫端必須已標明 entity 是
    `resolved_contract` 還是 `resolved_late_fee_bill`——⛔ 不得退化成模糊的 `row`。
    """
    tag = context.get("entity_tag")
    if tag not in ("resolved_contract", "resolved_late_fee_bill"):
        raise FulfillmentExecutionError(
            f"late_fee.facts.v1 的 entity_tag 必須是 resolved_contract 或 "
            f"resolved_late_fee_bill，實得 {tag!r}——⛔ 不得退化成模糊的 row")
    from services.jgb.bills import build_late_fee_facts
    facts = build_late_fee_facts(resolved_entity)
    return {"outcome": "FACTS", "grounding_facts": facts,
            "entity_id": resolved_entity.get("id"),
            "entity_label": resolved_entity.get("title"), "entity_tag": tag}


# ── R-31：composite GROUNDING_FACTS capability ─────────────────────────────
def point_refund_bill_facts_adapter(resolved_rows: Any,
                                    context: Mapping[str, Any]) -> Dict[str, Any]:
    """`point_refund.bill_facts.v1` —— **composite**：selection → outcome → fixed builder。

    ## F-C9 三段全部在 binding 內固定

    ```text
    selection algorithm  select_point_refund      （固定）
    downstream builder   build_late_fee_facts     （固定；⛔ 不由 utterance／face 選）
    outcome mapping      SELECTED／CANDIDATES／NOT_FOUND／TYPE_MISMATCH（固定）
    ```

    ⚠️ runtime 可依**資料狀態**分支，⛔ 但不得依 utterance／face／category／member row
    決定 semantic path——**data-dependent branching 是合法 fulfillment；semantic re-routing 不是。**

    ⚠️ ⛔ 不重用 `_point_refund_response(rows, user_question, builder)`：它仍要求
    `user_question` 且 builder 由呼叫端傳入 ⇒ 不符合 fixed-builder 契約。
    """
    from services.jgb import point_refund_selection as pr
    from services.jgb.bills import build_late_fee_facts   # ⚠️ **固定** builder

    rows = resolved_rows if isinstance(resolved_rows, list) else [resolved_rows]
    if len(rows) == 1 and context.get("direct_bill"):
        # 使用者直接指定某一筆 → 身分查核
        state = pr.verify_direct_bill(rows[0])
        selected = rows[0] if state == pr.STATE_SELECTED else None
        candidates = []
    else:
        state, selected, candidates = pr.select_point_refund(rows)

    if state == pr.STATE_SELECTED and selected is not None:
        # ⚠️ provenance 不可斷：type 事實行與 amount／status facts **一起**進 grounding
        facts = "\n".join([pr.type_fact_line(selected), build_late_fee_facts(selected)])
        return {"outcome": "FACTS", "grounding_facts": facts,
                "entity_id": selected.get("id"), "entity_label": selected.get("title"),
                "selection_state": state}
    if state == pr.STATE_CANDIDATES:
        # ⚠️ ⛔ builder **不執行**——多筆時系統不自行選定任一筆
        return {"outcome": "CANDIDATES",
                "candidates": [{"id": c.get("id"), "label": c.get("title")} for c in candidates],
                "outcome_note": pr.candidates_facts(candidates), "selection_state": state}
    if state == pr.STATE_TYPE_MISMATCH:
        return {"outcome": "TYPE_MISMATCH",
                "outcome_note": pr.type_mismatch_facts(rows[0]), "selection_state": state}
    return {"outcome": "NOT_FOUND", "outcome_note": pr.not_found_facts(),
            "selection_state": state}


register("late_fee.facts.v1", responsibility_id="R-28",
         adapter=late_fee_facts_adapter,
         input_contract_id="late_fee.bill_or_contract.v1", entity_type="bill_or_contract",
         output_mode=OUTPUT_GROUNDING_FACTS)

register("point_refund.bill_facts.v1", responsibility_id="R-31",
         adapter=point_refund_bill_facts_adapter,
         input_contract_id="point_refund.bill_by_contract.v1", entity_type="bill",
         output_mode=OUTPUT_GROUNDING_FACTS)

register("receipt.actual_amount.v1", responsibility_id="R-29",
         adapter=receipt_actual_amount_adapter,
         input_contract_id="bill.by_ref.v1", entity_type="bill",
         output_mode=OUTPUT_FINAL_TEXT)
