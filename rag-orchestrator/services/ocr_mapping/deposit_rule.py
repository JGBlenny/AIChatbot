"""押金二選一規則（design.md 元件 6／deposit_rule）。需求 6.1–6.6。

JGB 的押金是二選一、不是兩個都存（line-bot §7.3，`Contract.php` 符號 `deposit_type`）：
    deposit_type=0 根據月數 → 讀 `deposit`（月數），`deposit_amount` 完全不看
    deposit_type=1 固定押金 → 讀 `deposit_amount`，`deposit` 由 JGB 寫 0

⛔ 鐵則（業主曾寫過又拿掉）：**不得**以 `deposit_amount ÷ rent` 推算月數，也**不得**以 `deposit × rent`
推算金額——租金之後若被改動，押金會跟著變，而房東談定的是那個數字。
看不出來 ⇒ 三欄 absent、`deposit_type` 列 needs_confirmation，讓房東自己選。

`assert_deposit_exclusive()` 是這條鐵則的**尺**：`test_deposit_rule_req.py` 以突變控制證明它會紅。
"""
from __future__ import annotations

import re
from typing import NamedTuple, Optional

from services.ocr_mapping.field_normalizer import _NUMERIC_CLASS, _cn_to_int, normalize_amount
from services.ocr_mapping.models import FieldSource, FieldValue

#: ⚠️ 2026-09-03 對抗驗證 ②-4：月數不一定緊接在「押金」後（「押金…元整（貳個月）」）⇒ 視窗內任何「N 個月」都算；
#:    視窗本身已以「押金」為中心（contract_mapper._DEPOSIT_WINDOW），故不再要求前綴。排除「N月N日」型日期。
_DEPOSIT_MONTHS = re.compile(rf"({_NUMERIC_CLASS}+)\s*個?\s*月(?!\s*\d+\s*日)")


class DepositDecision(NamedTuple):
    deposit_type: FieldValue
    deposit: FieldValue
    deposit_amount: FieldValue
    needs_confirmation: bool


def _absent(raw: Optional[str] = None) -> FieldValue:
    return FieldValue(source=FieldSource.absent, raw=raw)


def decide_deposit(raw_text: Optional[str], *, page: Optional[int], confidence: Optional[float]) -> DepositDecision:
    """從押金原文決定三欄。⛔ 任一欄不得由另一欄推算。"""
    text = (raw_text or "").strip()
    if not text or "押金" not in text:
        return DepositDecision(_absent(text or None), _absent(), _absent(), needs_confirmation=True)

    amount = normalize_amount(text)                     # (int, raw) | None；含「另議／約」→ None
    mm = _DEPOSIT_MONTHS.search(text)
    months = _cn_to_int(mm[1]) if mm else None
    if months is not None and not (1 <= months <= 12):
        months = None

    common = {"page": page, "confidence": confidence, "raw": text}
    if amount is not None:                              # 金額為準（6.1／6.3）
        both = months is not None
        return DepositDecision(
            deposit_type=FieldValue(value=1, jgb_value=1, source=FieldSource.ocr, **common),
            deposit=_absent(),
            deposit_amount=FieldValue(value=amount[0], jgb_value=amount[0], source=FieldSource.ocr, **common),
            needs_confirmation=both,
        )
    if months is not None:                              # 月數（6.2）
        return DepositDecision(
            deposit_type=FieldValue(value=0, jgb_value=0, source=FieldSource.ocr, **common),
            deposit=FieldValue(value=months, jgb_value=months, source=FieldSource.ocr, **common),
            deposit_amount=_absent(),
            needs_confirmation=False,
        )
    return DepositDecision(_absent(text), _absent(), _absent(), needs_confirmation=True)   # 6.4


def assert_deposit_exclusive(d: DepositDecision) -> None:
    """不變式：月數與金額不得同時非空；兩者皆 ⛔ 不得是 derived／llm_extracted（那只可能是推算）。"""
    assert not (d.deposit.value is not None and d.deposit_amount.value is not None), \
        "deposit 與 deposit_amount 同時非空——違反 JGB 押金二選一"
    for name, f in (("deposit", d.deposit), ("deposit_amount", d.deposit_amount)):
        assert f.source in (FieldSource.ocr, FieldSource.absent), \
            f"{name} 的 source={f.source.value}——押金 ⛔ 不得推算或由 LLM 補值"


__all__ = ["DepositDecision", "assert_deposit_exclusive", "decide_deposit"]
