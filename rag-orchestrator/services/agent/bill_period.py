"""期別口語 → `PeriodSpec` 的**純函式**解析（Plan 第六批單元 A｜line-bot #2）。

## 為什麼要有這一層
走查病灶（line-bot 2026-09-10 #2）：業務說「基隆獨立共生公寓雅房九月的房租，
房客說想晚三天繳」，模型連問三輪帳單編號——**房東不會講編號**。編號是系統的
識別碼，業務講的是「哪一戶、哪一期」。把「口述期別 → 可比對的年月／未繳」
這一步交給**程式**，模型就不必為了一個它問不到的欄位反問。

## 硬約束
- **純函式**：⛔ 不讀時鐘（`today` 一律由呼叫端傳，同 `services/jgb/bills._today()`
  那個唯一時鐘）、⛔ 不讀 env、⛔ 不查 DB、⛔ 不叫模型。同輸入必得同輸出。
- **封閉語法**：能解析的講法全部列在本檔的常數表裡（`THIS_PERIOD_TERMS`／
  `LAST_PERIOD_TERMS`／`UNPAID_TERMS`／`CN_MONTH_VALUES`＋三條正則）。
  表外的講法一律 `None`＝**解析不到**，⛔ 不「盡力猜一個最像的」——猜錯期別的
  代價是對到別張帳單，而那張卡看起來完全正常。
- **不猜未來超過一個月**（`MAX_MONTHS_AHEAD`）：只給月份沒給年份時，取**最近的
  過去或當月**；唯一的例外是下一個月（業務在月底講下個月的帳單是常態）。
  ⛔ 不因為「今年還沒到的月份」就一律當今年——那會把「十二月」在九月解成三個月
  後的未來，而帳單早就存在於去年十二月。

## `PeriodSpec` 的三個欄位彼此獨立
`year`／`month` 是**期別**，`unpaid_only` 是**狀態**；「未繳」單獨出現時
`year=month=None`（不限月份），「九月 未繳」則兩者都有。⛔ 不把狀態折進月份。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Final, Optional, Tuple


@dataclass(frozen=True)
class PeriodSpec:
    """解析結果。`year`／`month` 同時有值或同時為 `None`（見模組 docstring）。"""

    year: Optional[int]
    month: Optional[int]
    unpaid_only: bool

    @property
    def has_month(self) -> bool:
        return self.year is not None and self.month is not None


#: 「這一期」類：⇒ `today` 所在月份。
THIS_PERIOD_TERMS: Final[Tuple[str, ...]] = ("這期", "本期", "這個月", "本月")

#: 「上一期」類：⇒ `today` 的前一個月。
LAST_PERIOD_TERMS: Final[Tuple[str, ...]] = ("上期", "上個月")

#: 未繳狀態的講法（⇒ `unpaid_only=True`，不限月份）。
UNPAID_TERMS: Final[Tuple[str, ...]] = ("未繳", "還沒繳", "沒繳")

#: 中文數字月份的**封閉映射**（一～十二）。⛔ 不用通用的中文數字轉換器：
#: 月份的值域只有 12 個成員，看得見全部成員的表才驗得完。
CN_MONTH_VALUES: Final[dict] = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}

#: 沒給年份時允許往未來看幾個月（見模組 docstring）。
MAX_MONTHS_AHEAD: Final[int] = 1

#: `YYYY-MM`／`YYYY/MM`。年份四位、月份一或兩位（值域另驗）。
_YEAR_MONTH_RE: Final = re.compile(r"(\d{4})[-/](\d{1,2})(?!\d)")

#: `N月`（阿拉伯數字）。⚠️ 前面不得再接數字（`20260901` 不是「1 月」），
#: 「三個月」「3 個月」因為中間隔了「個」而**不會**命中（刻意：那是天數／期間，
#: 不是期別）。
_ARABIC_MONTH_RE: Final = re.compile(r"(?<!\d)(\d{1,2})月")

#: `N月`（中文數字）。長字面在前，否則「十一月」會先被「十」吃掉。
_CN_MONTH_RE: Final = re.compile(r"(十[一二]|[一二三四五六七八九十])月")


def _month_in_range(value: Any) -> Optional[int]:
    """1–12 ⇒ int；其餘（含 0、13、非數字）⇒ `None`（⛔ 不夾到邊界值）。"""
    try:
        month = int(value)
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def _year_for_bare_month(month: int, today: date) -> int:
    """只給月份沒給年份時的年份：最近的**過去或當月**，最多往前看一個月。

    `ahead = month - today.month`：`<= MAX_MONTHS_AHEAD` ⇒ 今年；否則 ⇒ 去年
    （那個月在今年還沒到，而它在去年已經存在）。
    """
    ahead = month - today.month
    return today.year if ahead <= MAX_MONTHS_AHEAD else today.year - 1


def _previous_month(today: date) -> Tuple[int, int]:
    """`today` 的前一個月 `(year, month)`（一月 ⇒ 去年十二月）。"""
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def parse_period(text: Any, today: date) -> Optional[PeriodSpec]:
    """口述期別 → `PeriodSpec`；封閉語法都對不上 ⇒ `None`。

    Args:
        text: 使用者講的期別原話（非字串／空白 ⇒ `None`）。
        today: 判「這期」「上期」與裸月份年份的基準日。**由呼叫端傳**
            （同 `services/jgb/bills._today()`），⛔ 本檔不讀時鐘。

    月份的判定順序是**固定**的（⛔ 不看誰出現得早，那會讓同一句話因為語序不同
    得到不同結果）：`YYYY-MM`／`YYYY/MM` → 阿拉伯數字月 → 中文數字月 →
    這期類 → 上期類。第一個命中的就是答案。
    """
    if not isinstance(text, str) or not text.strip():
        return None

    unpaid_only = any(term in text for term in UNPAID_TERMS)

    year: Optional[int] = None
    month: Optional[int] = None

    ym = _YEAR_MONTH_RE.search(text)
    if ym is not None:
        candidate = _month_in_range(ym.group(2))
        if candidate is not None:
            year, month = int(ym.group(1)), candidate

    if month is None:
        arabic = _ARABIC_MONTH_RE.search(text)
        if arabic is not None:
            candidate = _month_in_range(arabic.group(1))
            if candidate is not None:
                month = candidate
                year = _year_for_bare_month(candidate, today)

    if month is None:
        cn = _CN_MONTH_RE.search(text)
        if cn is not None:
            candidate = CN_MONTH_VALUES[cn.group(1)]
            month = candidate
            year = _year_for_bare_month(candidate, today)

    if month is None and any(term in text for term in THIS_PERIOD_TERMS):
        year, month = today.year, today.month

    if month is None and any(term in text for term in LAST_PERIOD_TERMS):
        year, month = _previous_month(today)

    if month is None and not unpaid_only:
        # 封閉語法一個都沒命中 ⇒ 解析不到（⛔ 不回一個「什麼都不篩」的空規格：
        # 那會讓呼叫端分不出「使用者沒講期別」與「講了但我看不懂」）。
        return None
    return PeriodSpec(year=year, month=month, unpaid_only=unpaid_only)


__all__ = [
    "CN_MONTH_VALUES",
    "LAST_PERIOD_TERMS",
    "MAX_MONTHS_AHEAD",
    "PeriodSpec",
    "THIS_PERIOD_TERMS",
    "UNPAID_TERMS",
    "parse_period",
]
