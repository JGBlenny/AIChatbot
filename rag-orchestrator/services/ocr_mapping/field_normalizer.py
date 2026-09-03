"""決定性換算器（design.md 元件 4）：民國年、中文數字、面積、租期、繳費日。

鐵律（需求 5、業主 2026-09-03 拍板）：
- ⛔ 無 LLM、⛔ 無猜測——同輸入恆同輸出；解析不了一律回 None，由呼叫端標 `absent`。
- 每個成功值都帶 `raw`（原文全段，⛔ 不是只有命中的子字串）——需求 5.6 可逆對照。
- 日期同時回 `iso`（給人看）與 `ymd` 整數（給 JGB 送，與 `jgb_system_api.py` 既有先例同形）。

⚠️ 為什麼不用 `cn2an`：合約與謄本的數字詞彙是封閉集合（壹～玖、拾佰仟萬、元整、個月、年），
自寫可保證每條規則對應一組正反例，且不多一個正式 image 依賴（research.md 選型 1）。
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal, NamedTuple, Optional

Calendar = Literal["roc", "gregorian"]


class NormalizedDate(NamedTuple):
    iso: str            # "2025-01-21"
    ymd: int            # 20250121
    raw: str            # 原文全段
    calendar: Calendar


# ── 日期 ──────────────────────────────────────────────────────────────────────
# ⚠️ 順序與邊界很重要：
#   「2025年1月21日」若先給民國樣式、且民國年只寫 \d{2,3}，會從「025年」誤命中 ⇒
#   民國樣式加 (?<!\d) 左邊界，並先試西元樣式。
_GREG_CJK = re.compile(r"(?<!\d)(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_ROC_CJK = re.compile(r"(?:中華民國|民國)?\s*(?<!\d)(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_SEP = re.compile(r"(?<!\d)(\d{2,4})[/.\-](\d{1,2})[/.\-](\d{1,2})(?!\d)")
_GREG8 = re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)")     # 20250121
_ROC7 = re.compile(r"(?<!\d)(\d{3})(\d{2})(\d{2})(?!\d)")      # 1140121（ContractService 七碼）
#: 「114 1 21」——DocuMind 民國樣式有三個捕獲組，`contract_field_extractor.py` 用空白 join（符號 `match.groups()`）
#: ⇒ `rental_terms.date_start／date_end` 會長這樣。只在前面全部樣式都沒中時才試，⛔ 不接受四碼西元（DocuMind 不會產生）。
_ROC_SPACED = re.compile(r"(?<!\d)(\d{2,3})\s+(\d{1,2})\s+(\d{1,2})(?!\d)")

_ROC_OFFSET = 1911


def _build(y: int, m: int, d: int, raw: str, calendar: Calendar) -> Optional[NormalizedDate]:
    """曆法合法性交給 datetime；不合法（2/30、13 月）一律 None，⛔ 不修正。"""
    try:
        dt = date(y, m, d)
    except ValueError:
        return None
    return NormalizedDate(iso=dt.isoformat(), ymd=y * 10000 + m * 100 + d, raw=raw, calendar=calendar)


def normalize_date(text: Optional[str]) -> Optional[NormalizedDate]:
    """民國四格式（中華民國NNN年M月D日／NNN/M/D／七碼 NNNMMDD／DocuMind 空白串接「NNN M D」）與西元三格式
    （YYYY/M/D／YYYY-MM-DD／YYYY年M月D日，另接受八碼 YYYYMMDD）→ NormalizedDate；取**首個**可解析命中；解析不了回 None。
    """
    if not text or not text.strip():
        return None
    raw = text.strip()

    m = _GREG_CJK.search(raw)
    if m:
        return _build(int(m[1]), int(m[2]), int(m[3]), raw, "gregorian")

    m = _ROC_CJK.search(raw)
    if m:
        return _build(int(m[1]) + _ROC_OFFSET, int(m[2]), int(m[3]), raw, "roc")

    m = _SEP.search(raw)
    if m:
        y = int(m[1])
        if len(m[1]) == 4:
            return _build(y, int(m[2]), int(m[3]), raw, "gregorian")
        return _build(y + _ROC_OFFSET, int(m[2]), int(m[3]), raw, "roc")

    m = _GREG8.search(raw)
    if m and 1912 <= int(m[1]) <= 2200:
        return _build(int(m[1]), int(m[2]), int(m[3]), raw, "gregorian")

    m = _ROC7.search(raw)
    if m:
        return _build(int(m[1]) + _ROC_OFFSET, int(m[2]), int(m[3]), raw, "roc")

    m = _ROC_SPACED.search(raw)
    if m:
        return _build(int(m[1]) + _ROC_OFFSET, int(m[2]), int(m[3]), raw, "roc")

    return None


# ── 中文數字（封閉詞彙）────────────────────────────────────────────────────────
_CN_DIGIT = {
    "零": 0, "〇": 0, "一": 1, "壹": 1, "二": 2, "貳": 2, "兩": 2, "三": 3, "參": 3, "叁": 3,
    "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6, "陸": 6, "七": 7, "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9,
}
_CN_UNIT = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000, "萬": 10_000, "万": 10_000, "億": 100_000_000}
_CN_CHARS = "".join(_CN_DIGIT) + "".join(_CN_UNIT) + "廿卅"
_NUMERIC_CLASS = rf"[{re.escape(_CN_CHARS)}\d,]"

#: 模糊量詞——出現即視為「不可決定性解析」（需求 5.5），⛔ 不取近似值
#: ⚠️ 「約」只在**後接數字／幣別**時才算模糊（約壹萬、約 13,800、約新台幣…），
#:    且不得是「簽約／契約／合約／租約／公約／違約／預約」的一部分——
#:    2026-09-03 實測「於簽約時一次付清」被誤判為模糊 ⇒ 押金整欄 absent。
_VAGUE = re.compile(
    rf"(?<![簽契合租公違預])約(?=\s*(?:新台幣|新臺幣|NT\$|NTD)?\s*{_NUMERIC_CLASS})"
    r"|以上|以下|左右|面議|另議|起跳|至少|大約"
)


def _cn_to_int(s: str) -> Optional[int]:
    """「壹萬參仟捌佰」「壹拾貳萬」「2萬5千」「十二」「廿五」→ int；含未知字元回 None。"""
    s = s.replace(",", "").replace("廿", "二十").replace("卅", "三十").strip()
    if not s:
        return None
    total = section = num = 0
    has_any = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit():                          # 阿拉伯數字可連續多位
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            num = int(s[i:j]); has_any = True; i = j; continue
        if ch in _CN_DIGIT:
            num = num * 10 + _CN_DIGIT[ch]; has_any = True
        elif ch in _CN_UNIT:
            u = _CN_UNIT[ch]; has_any = True
            if u >= 10_000:
                total += (section + num) * u; section = num = 0
            else:
                section += (num or 1) * u; num = 0
        else:
            return None
        i += 1
    return (total + section + num) if has_any else None


# ── 金額（需求 5.5）────────────────────────────────────────────────────────────
_AMOUNT_WITH_UNIT = re.compile(rf"(?:新台幣|新臺幣|NT\$|NTD)?\s*({_NUMERIC_CLASS}+)\s*(?:元|圓)")
_AMOUNT_WITH_PREFIX = re.compile(rf"(?:NT\$|NTD|新台幣|新臺幣)\s*({_NUMERIC_CLASS}+)")


def normalize_amount(text: Optional[str]) -> Optional[tuple[int, str]]:
    """中文大寫／阿拉伯／千分位金額 → (整數, raw)。須帶幣別前綴或「元」；含模糊量詞（約／以上…）→ None。"""
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _VAGUE.search(raw):
        return None
    m = _AMOUNT_WITH_UNIT.search(raw) or _AMOUNT_WITH_PREFIX.search(raw)
    if not m:
        return None
    value = _cn_to_int(m[1])
    return (value, raw) if value is not None and value > 0 else None


# ── 面積（需求 3.2）────────────────────────────────────────────────────────────
_DECIMAL = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\d])")


def normalize_area(text: Optional[str]) -> Optional[tuple[float, str]]:
    """「3,406.98」「3406.98平方公尺」「25.5 坪」→ (float, raw)；無數字或含模糊量詞 → None。"""
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _VAGUE.search(raw):
        return None
    m = _DECIMAL.search(raw)
    if not m:
        return None
    whole = m[1].replace(",", "")
    return (float(f"{whole}.{m[2]}") if m[2] else float(whole), raw)


# ── 租期 → 月數（需求 5.4）─────────────────────────────────────────────────────
_LEASE_YEARS = re.compile(rf"({_NUMERIC_CLASS}+)\s*年(半)?(?!\s*\d+\s*月)")  # 排除「114年1月」型日期；「一年半」→ +6
#: ⚠️ 2026-09-03 對抗驗證 ②-1：「押金三個月」曾被加進租期 ⇒ 月數前一字是「押／金」者不算
#: ⚠️ 同日實打抓到：視窗把「115年1月20日」切成「115年1月2」，裸「1月」被當 +1 個月 ⇒
#:    **沒有「個」的裸「N月」若緊接在「年」之後一律視為日期**（「一年六個月」有「個」不受影響）
_LEASE_MONTHS_GE = re.compile(rf"(?<![押金])({_NUMERIC_CLASS}+)\s*個\s*月")
_LEASE_MONTHS_BARE = re.compile(rf"(?<![押金年])({_NUMERIC_CLASS}+)\s*月(?![\s\d]*日)")
_MAX_LEASE_YEARS = 30                                                        # 超過即視為誤抓（如民國年）


def normalize_lease_months(text: Optional[str]) -> Optional[tuple[int, str]]:
    """「租期壹年」→12、「一年半」→18、「一年六個月」→18、「為期十二個月」→12；日期、「另議」、無數字 → None。"""
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _VAGUE.search(raw):
        return None
    months = 0
    found = False
    ym = _LEASE_YEARS.search(raw)
    if ym:
        y = _cn_to_int(ym[1])
        if y is None or y <= 0 or y > _MAX_LEASE_YEARS:
            return None
        months += y * 12 + (6 if ym[2] else 0); found = True
    mm = _LEASE_MONTHS_GE.search(raw) or _LEASE_MONTHS_BARE.search(raw)
    if mm:
        n = _cn_to_int(mm[1])
        if n is None or n <= 0 or n > 360:
            return None
        months += n; found = True
    return (months, raw) if found and months > 0 else None


# ── 繳費日（需求 4.1）──────────────────────────────────────────────────────────
_CYCLE_DATE = re.compile(rf"每月\s*({_NUMERIC_CLASS}+)\s*(?:日|號)")


def normalize_cycle_date(text: Optional[str]) -> Optional[tuple[int, str]]:
    """「每月五日前」→5、「每月廿五日」→25；須帶「每月」且結果在 1–31，否則 None（⛔ 不猜月初／季初）。"""
    if not text or not text.strip():
        return None
    raw = text.strip()
    m = _CYCLE_DATE.search(raw)
    if not m:
        return None
    day = _cn_to_int(m[1])
    return (day, raw) if day is not None and 1 <= day <= 31 else None


__all__ = [
    "Calendar", "NormalizedDate",
    "normalize_amount", "normalize_area", "normalize_cycle_date", "normalize_date", "normalize_lease_months",
]
