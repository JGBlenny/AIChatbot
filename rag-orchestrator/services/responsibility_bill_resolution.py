"""T4-B3：`bill.by_ref.v1` 的 **responsibility-only** 顯式解析階段（2026-08-30）。

## 為什麼不能重用 legacy `get_bills(bill_ref=...)`

`services/jgb_system_api.py:190` 的**非數字**分支：

```text
get_contracts(keyword=ref) → contract_ids = rows[0].get("id")   ← **取第一筆合約**
```

⇒ authority 在 resolver 看見 candidates **之前**就被 commit 掉了（違反 F-C3）。
**F-C6**：responsibility path ⛔ 不得呼叫該分支。

⚠️ 依業主裁定，**⛔ 不把 `bill.by_ref.v1` 收窄成只接受數字**——那會把 execution limitation
錯寫成 responsibility semantics。改為把 legacy adapter 裡**隱藏**的
「keyword → first contract」拆成**顯式 entity-resolution stages**：

```text
numeric ref     → get_bill_detail  → 0 NO_MATCH ／ 1 RESOLVED
non-numeric ref → get_contracts(keyword)
                  → 0 NO_MATCH ／ >1 AMBIGUOUS ／ 1 verified contract
                  → get_bills(contract_ids=<verified>)      ⚠️ **只走 contract_ids 分支**
                  → 0 NO_MATCH ／ >1 AMBIGUOUS ／ 1 RESOLVED
```

⚠️ 每一階段都各自套 T4-B-C1 四態，⛔ 任一階段都不得取第一筆。
"""
from typing import Any, Dict, List, Optional, Protocol

from services.responsibility_entity_resolution import (STATE_AMBIGUOUS, STATE_INVALID_INPUT,
                                                       STATE_NO_MATCH, STATE_RESOLVED, result)

INPUT_CONTRACT_ID = "bill.by_ref.v1"
ENTITY_TYPE = "bill"

STAGE_BILL_DIRECT = "bill_direct"
STAGE_CONTRACT_LOOKUP = "contract_lookup"
STAGE_BILLS_OF_CONTRACT = "bills_of_contract"


class BillRefApi(Protocol):
    """本 resolver 需要的**最小** API 面。⚠️ 刻意 ⛔ 不含 `get_bills(bill_ref=...)`。"""

    async def get_bill_detail(self, role_id: str, bill_id: int) -> Dict[str, Any]: ...
    async def get_contracts(self, role_id: str, contract_ids: Optional[str] = None,
                            keyword: Optional[str] = None, **kw) -> Dict[str, Any]: ...
    async def get_bills(self, role_id: str, contract_ids: Optional[str] = None,
                        **kw) -> Dict[str, Any]: ...


def _rows(resp: Optional[Dict[str, Any]]) -> List[dict]:
    """把 API 回應正規化成列表。⚠️ 單物件端點回 dict → **包成單元素 list**
    （比照既有 secondary_call 的修正；`else []` 會把 dict 整個丟掉＝假綠來源）。"""
    if not resp or not resp.get("success"):
        return []
    data = resp.get("data")
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict) and r]
    if isinstance(data, dict) and data:
        return [data]
    return []


def _stage(state: str, stage: str, **extra: Any) -> Dict[str, Any]:
    return result(state, INPUT_CONTRACT_ID, ENTITY_TYPE, stage=stage, **extra)


async def resolve_bill_by_ref(api: BillRefApi, role_id: str,
                              bill_ref: Optional[str]) -> Dict[str, Any]:
    """把 `bill_ref` 解析成**唯一**帳單。⛔ 任一階段都不得取第一筆。"""
    ref = (str(bill_ref).strip() if bill_ref is not None else "")
    if not ref:
        return _stage(STATE_INVALID_INPUT, STAGE_BILL_DIRECT, missing_fields=["bill_ref"])

    # ── 數字 ref：直查單筆 ────────────────────────────────────────────────
    if ref.isdigit():
        rows = _rows(await api.get_bill_detail(role_id, int(ref)))
        if not rows:
            return _stage(STATE_NO_MATCH, STAGE_BILL_DIRECT, bill_ref=ref)
        if len(rows) > 1:      # ⚠️ 理論上不該發生；發生就是 AMBIGUOUS，⛔ 不得取第一筆
            return _stage(STATE_AMBIGUOUS, STAGE_BILL_DIRECT, candidates=rows)
        return _stage(STATE_RESOLVED, STAGE_BILL_DIRECT, resolved_id=rows[0].get("id"),
                      resolved_entity=rows[0], uniqueness="direct_bill_id")

    # ── 非數字 ref：**顯式** 兩階段（⛔ 不走 legacy 的隱藏 rows[0]）──────────
    contracts = _rows(await api.get_contracts(role_id, keyword=ref))
    if not contracts:
        return _stage(STATE_NO_MATCH, STAGE_CONTRACT_LOOKUP, bill_ref=ref)
    if len(contracts) > 1:
        # ⚠️ **B-G5 守的就是這裡**：legacy 在此處直接 rows[0]
        return _stage(STATE_AMBIGUOUS, STAGE_CONTRACT_LOOKUP, candidates=contracts,
                      _why="多筆合約 ⇒ 必須由使用者選；⛔ 不得沿用 legacy 的 first-contract")
    contract = contracts[0]    # ⚠️ 此處是 **len==1** 的 verified contract，⛔ 非「取第一筆」

    bills = _rows(await api.get_bills(role_id, contract_ids=contract.get("id")))
    if not bills:
        return _stage(STATE_NO_MATCH, STAGE_BILLS_OF_CONTRACT,
                      resolved_contract_id=contract.get("id"))
    if len(bills) > 1:
        return _stage(STATE_AMBIGUOUS, STAGE_BILLS_OF_CONTRACT, candidates=bills,
                      resolved_contract_id=contract.get("id"))
    return _stage(STATE_RESOLVED, STAGE_BILLS_OF_CONTRACT, resolved_id=bills[0].get("id"),
                  resolved_entity=bills[0], resolved_contract_id=contract.get("id"),
                  uniqueness="unique_contract_then_unique_bill")
