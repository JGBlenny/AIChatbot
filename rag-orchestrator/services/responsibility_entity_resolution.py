"""T4-B1：**responsibility-only entity resolution layer**（2026-08-30，業主凍結）。

## 為什麼是獨立 layer，而不是在 legacy 裡加 branch

業主裁定：**legacy 的 `matched[0]` / `rows[0]` 原地不動**；C2 **根本不走到那些
first-row authority sites**，而不是「進去後再加 branch 修正」。

```text
⛔ 不把 `if responsibility_mode:` 散落進 contracts.py／bills.py 各處
✅ 抽成本層，只在 responsibility execution seam 呼叫
   input_contract_id ＋ form_data ＋ endpoint rows → ResolutionResult
```

## T4-B-C1 — EXACT ENTITY RESOLUTION（凍結）

```text
0 valid entity                                    → NO_MATCH
1 verified entity                                 → RESOLVED
>1 valid entities **without deterministic uniqueness proof** → AMBIGUOUS

MUST NOT: choose first ／ choose highest DB order ／ choose earliest returned
```

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
from typing import Any, Callable, Dict, List, Mapping, Optional

STATE_RESOLVED = "RESOLVED"
STATE_AMBIGUOUS = "AMBIGUOUS"
STATE_NO_MATCH = "NO_MATCH"
STATE_INVALID_INPUT = "INVALID_INPUT"
#: ⚠️ 只有 RESOLVED 能進 T4-C direct capability
TERMINAL_STATES = (STATE_RESOLVED, STATE_AMBIGUOUS, STATE_NO_MATCH, STATE_INVALID_INPUT)

AMBIGUITY_EXACT_IDENTIFIER = "exact_identifier"
AMBIGUITY_REVIEWED_SELECTION_CONTRACT = "reviewed_selection_contract"


class EntityResolutionError(RuntimeError):
    """resolution 契約違反——⚠️ 大聲失敗，⛔ 不得以 first row 帶過。"""


#: input contract registry（machine contract；⛔ 不只是名稱）
INPUT_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "bill.by_ref.v1": {
        "entity_type": "bill",
        "required_fields": ["bill_ref"],
        "resolver_id": "bill.by_ref",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
    },
    "contract.current_entity.v1": {
        "entity_type": "contract",
        "required_fields": ["contract_ref"],
        "resolver_id": "contract.by_ref",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
    },
    "point_refund.bill_by_contract.v1": {
        "entity_type": "bill",
        "required_fields": ["contract_ref"],
        "resolver_id": "point_refund_bill.by_contract",
        "ambiguity_policy": AMBIGUITY_REVIEWED_SELECTION_CONTRACT,
        "_selection_contract": "POINT_REFUND_BILL_SELECTION（select_point_refund）"
                               "——⚠️ 這是**唯一例外**的正例：reviewed deterministic uniqueness",
    },
    "late_fee.bill_or_contract.v1": {
        "entity_type": "bill_or_contract",
        "required_fields": [],          # ⚠️ tagged alternatives，見 _accepts
        "_accepts": ["resolved_contract", "resolved_late_fee_bill"],
        "resolver_id": "late_fee.entity",
        "ambiguity_policy": AMBIGUITY_EXACT_IDENTIFIER,
        "_note": "⚠️ ⛔ 不是模糊的 `row`——必須是 tagged alternatives 之一",
    },
}


def result(state: str, input_contract_id: str, entity_type: str, **extra: Any) -> Dict[str, Any]:
    if state not in TERMINAL_STATES:
        raise EntityResolutionError(f"未知的 resolution state：{state!r}")
    out = {"state": state, "input_contract_id": input_contract_id, "entity_type": entity_type}
    out.update(extra)
    if state != STATE_RESOLVED:
        out["_not_executable"] = ("⚠️ 只有 RESOLVED 能進 T4-C direct capability；"
                                  "本 state 走既有 UX 通道，⛔ 但 ⛔ 不得重新 retrieval")
    return out


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
