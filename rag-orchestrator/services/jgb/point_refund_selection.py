"""**點退帳單 selection contract**（業主授權 2026-08-29，scope＝`POINT_REFUND_BILL_SELECTION`）。

## 缺口的精確位置（⚠️ 前一版診斷有誤，見下）

```text
✅ 金額能力**有**      _bill_amount_due → bill["total"] → 「• 金額」
✅ 狀態能力**有**      _format_bill_status
✅ 候選列表**有**      conversational_engine 的 result_mapping／candidate_cap
                      （⚠️ 前一版誤判為「查無實作」——搜尋範圍只掃了 services/jgb/，
                        沒掃 engine 層；正對照因此也選錯層）
⛔ 缺的是 **type 的使用**：全流程從未讀 `type`（2＝點退）
   ⇒ 候選標籤不含類型、收斂後也不驗證選中的那筆真的是點退帳單
```
⇒ first causal break ＝ **辨識／選出 type=2**，⛔ 不是金額能力。

## 契約（⚠️ 只管點退，⛔ 不得泛化成通用 bill selector）

```text
合約多筆帳單 → filter type == 2
  0 筆  → NOT_FOUND：明確回報找不到點退帳單，⛔ 不得 fallback 第一筆
  1 筆  → SELECTED
  >1 筆 → CANDIDATES：列出候選，⛔ 不得任取 data[0]

直接給 bill id → 取得該 bill → verify type == 2
  ⛔ 「bill_id 存在 ＋ query 說點退」**不足以**把它稱為點退帳單
```

## grounding provenance 不可斷（業主定案的真正要求）

要求**不是**「`_format_bill_status` 必須讀 type」，而是：

```text
最後 grounding 必須能證明所回答的那一列就是 type=2，
⛔ 不可以是 selection 過程看過 type、後面 provenance 又消失。
⇒ selected bill identity ＋ selected bill type ＋ amount/status 三者不能斷。
```
本模組的做法：selection 層產生**決定性的 type label 事實行**，與 identity／
amount／status 一起進 facts。
"""
from typing import Any, Dict, List, Optional, Tuple

#: `type` 的值域（鏡射 `BillApiController:173-197`；與 JgbMockTransport.MAPPING 同源）
BILL_TYPE_LABELS: Dict[int, str] = {
    1: "一般租金", 2: "點退", 3: "新增帳單",
    4: "罰款", 5: "儲值", 6: "押金設算息",
}
#: 點退
POINT_REFUND_TYPE = 2

#: 意圖詞（⚠️ 只用來判「這句在問點退帳單」，⛔ 不作為身分證明——身分一律看 type）
POINT_REFUND_KEYWORDS = ("點退", "退租結算", "點退帳單", "點退金額")

STATE_SELECTED = "selected"
STATE_NOT_FOUND = "not_found"
STATE_CANDIDATES = "candidates"
STATE_TYPE_MISMATCH = "type_mismatch"


def is_point_refund_intent(user_question: Optional[str]) -> bool:
    """這句是否在問點退帳單。⚠️ 只決定要不要啟動本契約，⛔ 不決定身分。"""
    q = user_question or ""
    return any(k in q for k in POINT_REFUND_KEYWORDS)


def bill_type(bill: Optional[dict]) -> Optional[int]:
    """讀 `type`。⚠️ 缺值回 None（⛔ 不代 1、⛔ 不猜）——未知不得被當成「不是點退」以外的任何結論。"""
    v = (bill or {}).get("type")
    if isinstance(v, bool):        # ⚠️ bool 是 int 的子類，先擋掉
        return None
    return v if isinstance(v, int) else None


def type_label(bill: Optional[dict]) -> str:
    t = bill_type(bill)
    if t is None:
        return "（系統未記錄類型）"
    return BILL_TYPE_LABELS.get(t, f"未知類型（{t}）")


def is_point_refund(bill: Optional[dict]) -> bool:
    """身分判定——**唯一**依據是 `type`。⛔ 標題含「點退」不算、⛔ 使用者說是不算。"""
    return bill_type(bill) == POINT_REFUND_TYPE


def _label(bill: dict) -> str:
    parts = [bill.get("title"), bill.get("sub_title")]
    total = bill.get("total")
    if isinstance(total, (int, float)):
        parts.append(f"NT$ {total:,.0f}")
    ident = bill.get("id")
    head = f"編號 {ident}" if ident is not None else None
    return "｜".join(str(p) for p in ([head] + parts) if p not in (None, ""))


def select_point_refund(rows: Optional[List[dict]]) -> Tuple[str, Optional[dict], List[dict]]:
    """回傳 `(state, selected, candidates)`。

    ⚠️ ⛔ **任何情況都不得回傳 `rows[0]` 作為預設**——那正是本契約要殺掉的舊行為。
    """
    items = [r for r in (rows or []) if isinstance(r, dict)]
    matched = [r for r in items if is_point_refund(r)]
    if not matched:
        return STATE_NOT_FOUND, None, []
    if len(matched) == 1:
        return STATE_SELECTED, matched[0], matched
    return STATE_CANDIDATES, None, matched


def verify_direct_bill(bill: Optional[dict]) -> str:
    """使用者直接指定某筆帳單時的身分查核。"""
    if not bill:
        return STATE_NOT_FOUND
    return STATE_SELECTED if is_point_refund(bill) else STATE_TYPE_MISMATCH


def type_fact_line(bill: dict) -> str:
    """進 grounding 的**決定性** type 事實行（provenance 不可斷的那一段）。"""
    return f"類型：{type_label(bill)}帳單（系統依帳單 type 判定）"


def not_found_facts() -> str:
    return ("查無點退帳單：這份合約底下沒有任何類型為「點退」的帳單。"
            "⚠️ 系統不會改以其他類型的帳單代答；若已完成點退仍查無，請確認點退流程是否已產生帳單。")


def candidates_facts(candidates: List[dict]) -> str:
    lines = [f"找到 {len(candidates)} 筆點退帳單，請確認要查詢哪一筆："]
    lines += [f"{i}. {_label(c)}" for i, c in enumerate(candidates, 1)]
    lines.append("（系統未自行選定任一筆。）")
    return "\n".join(lines)


def type_mismatch_facts(bill: dict) -> str:
    return (f"這筆帳單的類型是「{type_label(bill)}」，**不是點退帳單**。"
            f"系統不會以點退帳單的身分回答這筆資料；"
            f"若要查點退帳單，請提供該筆點退帳單的編號或改以合約查詢。")
