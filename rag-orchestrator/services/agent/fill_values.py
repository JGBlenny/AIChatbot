"""填欄結構化 S3：AI 給的欄位值的**型別檢查**（plan-fill-structured-20261030 §6.1 S3；DSP-128）。

分工（DSP-091、DSP-127）：AI 理解客人的話、輸出換算好的值；程式只驗格式、範圍、值域。
本檔是**純函式**：參數只有動作、欄位宣告、AI 的值、今天日期、候選集（選定紀錄的欄才用）。
⛔ 收使用者原話、⛔ 比對原話、⛔ 開放詞表；⛔ 讀時鐘（`today` 由呼叫端傳，與系統句同回合同一個 `bills._today()`）；
任何輸入都不丟例外，失敗一律回 `None`（另回 trace 標記，⛔ 帶值）。

只涵蓋 `int`、`number`、`date`、`text` 四種型別（`S3_KINDS`）；enum、category、email、phone、period、range 只走
現行值閘 `runtime._write_draft_gate_value`，不經本檔。
⛔ 改 `write_forms.parse_number`、`parse_number_token`、`user_text_dates`（off 路徑在用）。
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from typing import Any, Collection, Final, Optional, Tuple

from services.agent import write_forms as WF
from services.agent.completed_actions import sanitize_data_piece

#: S3 取代原話比對的型別。
S3_KINDS: Final[frozenset] = frozenset({"int", "number", "date", "text"})

#: 數字只收 ASCII 阿拉伯數字（N16）：開頭一個數字，之後數字或千分位逗號，可有一段小數。
#: 千分位是否合法交給 `WF.parse_number`（`1,000,00`、`2,0000` 解析不出 ⇒ 不收；N14）。
#: ⚠️ 用 `[0-9]` 而不是 `\d`：`\d` 會收全形、上標、圈號等 Unicode 數字。
_ASCII_NUMBER_RE: Final = re.compile(r"[0-9][0-9,]*(?:\.[0-9]+)?")


def is_record_pick_field(action: Any, f: Any) -> bool:
    """選定紀錄的欄（N1）：表單出卡前預檢宣告的編號欄（`bill_due_extend` 的 `bill_id`）。由表單宣告判斷，⛔ 欄位名分支。"""
    form = WF.FORMS.get(action) if isinstance(action, str) else None
    pc = getattr(form, "precheck", None)
    return pc is not None and getattr(f, "key", None) == pc.id_key


def _check_number(action: str, f: Any, text: str, today: date,
                  candidates: Optional[Collection[str]]) -> Tuple[Optional[str], Optional[str]]:
    if text.startswith("-"):
        # 負數（含 `-0`）：格式像數字 ⇒ 超出範圍；否則格式不對。
        return None, (WF.V_FS_OUT_OF_BOUNDS if _ASCII_NUMBER_RE.fullmatch(text[1:]) else WF.V_FS_FORMAT_INVALID)
    if not _ASCII_NUMBER_RE.fullmatch(text):
        return None, WF.V_FS_FORMAT_INVALID
    num = WF.parse_number(text, f.kind)
    if num is None or isinstance(num, bool):
        return None, WF.V_FS_FORMAT_INVALID
    if isinstance(num, float) and not math.isfinite(num):
        return None, WF.V_FS_FORMAT_INVALID
    if f.kind == "int" and not isinstance(num, int):
        return None, WF.V_FS_FORMAT_INVALID
    lo, hi = getattr(f, "lo", None), getattr(f, "hi", None)
    if lo is not None and ((num <= lo) if getattr(f, "lo_open", False) else (num < lo)):
        return None, WF.V_FS_OUT_OF_BOUNDS
    if hi is not None and num > hi:
        return None, WF.V_FS_OUT_OF_BOUNDS
    if num < 0:
        return None, WF.V_FS_OUT_OF_BOUNDS
    if getattr(f, "date_offset", False):
        # §9 Q9：`days` 只擋溢位（下游 `今天或原到期日 + days`）；⛔ 自創業務上限。
        try:
            today + timedelta(days=num)
        except (OverflowError, ValueError):
            return None, WF.V_FS_OUT_OF_BOUNDS
    if is_record_pick_field(action, f):
        # N1：只收候選已開、且屬於候選集的編號；候選沒開 ⇒ 不收。
        if candidates is None or str(num) not in {str(c) for c in candidates}:
            return None, WF.V_FS_PICK_NOT_IN_CANDIDATES
    return str(num), None


def _check_date(action: str, f: Any, text: str, today: date) -> Tuple[Optional[str], Optional[str]]:
    d = WF.parse_model_date(text)
    if d is None:
        return None, WF.V_FS_FORMAT_INVALID
    if WF.field_not_before_today(action, f.key) and d < today:
        return None, WF.V_FS_OUT_OF_BOUNDS
    return WF.iso_date(d), None


def validate_with_reason(action: str, field: Any, value: Any, *, today: date,
                         candidates: Optional[Collection[str]] = None) -> Tuple[Optional[str], Optional[str]]:
    """AI 給的一欄值 ⇒ `(要存進草稿的正規化字串或 None, trace 標記或 None)`。

    - 空值（非空白字元為 0）⇒ `(None, None)`（沒給，不記標記）；
    - 非字串（含布林、數字）、超長（`WF.value_max_len`）、含 `sanitize_data_piece` 會改動的字元 ⇒ 格式不對；
    - int／number：只收 ASCII 數字（`WF.parse_number` 解析）；負數、超出表單宣告範圍（依動作取、含開下界）⇒ 超出範圍；
      沒宣告範圍的欄只驗非負；`date_offset` 欄另擋溢位；選定紀錄的編號欄另驗候選集；
    - date：`WF.parse_model_date` 解析得出；標了 `NOT_BEFORE_TODAY` 的欄早於今天 ⇒ 超出範圍；存 `YYYY-MM-DD`；
    - text：存去前後空白的值。
    ⛔ 丟例外：任何例外一律回 `(None, V_FS_FORMAT_INVALID)`。"""
    try:
        return _validate(action, field, value, today, candidates)
    except Exception:  # noqa: BLE001 — 純函式保證不丟例外（S3：失敗一律回 None）
        return None, WF.V_FS_FORMAT_INVALID


def _validate(action: Any, f: Any, value: Any, today: Any,
              candidates: Optional[Collection[str]]) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(f, WF.FormField) or f.kind not in S3_KINDS or not isinstance(today, date):
        return None, WF.V_FS_FORMAT_INVALID
    if not isinstance(value, str) or isinstance(value, bool):
        return None, WF.V_FS_FORMAT_INVALID
    text = value.strip()
    if not text:
        return None, None
    if len(text) > WF.value_max_len(f) or sanitize_data_piece(text) != text:
        return None, WF.V_FS_FORMAT_INVALID
    if f.kind in ("int", "number"):
        return _check_number(action, f, text, today, candidates)
    if f.kind == "date":
        return _check_date(action, f, text, today)
    return text, None                                  # text


def validate(action: str, field: Any, value: Any, *, today: date,
             candidates: Optional[Collection[str]] = None) -> Optional[str]:
    """`validate_with_reason` 只取值（不收 ⇒ `None`）。"""
    return validate_with_reason(action, field, value, today=today, candidates=candidates)[0]


__all__ = ["S3_KINDS", "is_record_pick_field", "validate_with_reason", "validate"]
