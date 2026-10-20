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
  `LAST_PERIOD_TERMS`／`UNPAID_TERMS`／`CN_MONTH_VALUES`／`YEAR_MODIFIER_TERMS`＋本檔的
  正則）。
  表外的講法一律 `None`＝**解析不到**，⛔ 不「盡力猜一個最像的」——猜錯期別的
  代價是對到別張帳單，而那張卡看起來完全正常。
- **不猜未來超過一個月**（`MAX_MONTHS_AHEAD`）：只給月份沒給年份時，取**最近的
  過去或當月**；唯一的例外是下一個月（業務在月底講下個月的帳單是常態）。
  ⛔ 不因為「今年還沒到的月份」就一律當今年——那會把「十二月」在九月解成三個月
  後的未來，而帳單早就存在於去年十二月。

- **有寫西元年就用所寫的年份**（期別片 P-1／R1、R2）：`YYYY-MM`、`YYYY/MM`、
  `YYYY年M月`、`YYYY年`＋中文數字月（年、月之間可有空白或夾「的」）都算「有年份」；
  有年份時 ⛔ 呼叫 `_year_for_bare_month`、⛔ 被 `YEAR_MODIFIER_TERMS` 覆寫。
  四位數年份前不得再接數字（「12027/01」⛔ 讀成 2027）。⛔ 設年份值域上限（設了反而會
  退成「不篩選」，安全審查 D3）。
- **寫了年份但認不得 ⇒ 解析不到**（P-1c）：只限「四個中文數字（〇、零、一～九）＋年＋
  月份」（「二〇二七年一月」）——⛔ 只吃月份往回推（那會對到別年的帳單）。一到三位數的
  年份（民國年「115年9月」）依業主 Q-ROC 裁示**維持現行**：只吃月份、往回推。「年」後面
  沒有緊接月份（年資、租期「我租了2年」）不觸發。
- **一則原話可有多個期別**（P-1b）：`parse_period` 只回**一個**（固定判定順序的第一個）；
  值閘要的是「使用者講過的全部期別」，由 `parse_periods` 回傳。兩支同一套封閉語法、
  同樣不讀時鐘。

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
#: 年份修飾詞（封閉表）：值＝相對今年的位移；`None`＝表內但不支援 ⇒ 整句不解析。
#: ⚠️ 「明年」「前年」「後年」列 None 是刻意：延期只對既有帳單，未來年份沒有可對的張。
YEAR_MODIFIER_TERMS: Final[dict] = {"去年": -1, "今年": 0, "明年": None, "前年": None, "後年": None}

#: `YYYY-MM`／`YYYY/MM`。年份四位、月份一或兩位（值域另驗）。
#: 期別片 D3：開頭 `(?<!\d)`——「12027/01」⛔ 讀成 2027。
_YEAR_MONTH_RE: Final = re.compile(r"(?<!\d)(\d{4})[-/](\d{1,2})(?!\d)")

#: 中文數字月份的字面（長字面在前，否則「十一月」會先被「十」吃掉）。
_CN_MONTH_ALT: Final[str] = r"十[一二]|[一二三四五六七八九十]"

#: 期別片 P-1：`YYYY年M月`／`YYYY年`＋中文數字月。年份四位且前面不得再接數字；
#: 「年」前後、阿拉伯數字月與「月」之間可有空白；年、月之間可夾一個「的」
#: （「2027 年 5 月」「2027年的1月」「2027年一月」）。group 1＝年、2＝阿拉伯數字月、
#: 3＝中文數字月。
_YEAR_ZH_MONTH_RE: Final = re.compile(
    r"(?<!\d)(\d{4})\s*年\s*(?:的\s*)?(?:(\d{1,2})\s*月|(" + _CN_MONTH_ALT + r")月)"
)

#: 期別片 P-1c：寫了中文數字西元年（「二〇二七年一月」「二零二七年 一月」）⇒ 解析不到。
#: 年份字只收〇、零、一～九（⛔ 十：「二十年」是年數）；「年」後面必須緊接月份
#: （可夾空白或「的」），年資、租期（「租約一年」）不觸發。⚠️ 刻意 ⛔ 加前置 lookbehind：
#: 五個以上中文數字＋年＋月同樣解析不到（失敗方向＝不篩選，⛔ 只吃月份往回推）。
_CN_YEAR_MONTH_RE: Final = re.compile(
    r"[〇零一二三四五六七八九]{4}\s*年\s*(?:的\s*)?(?:\d{1,2}\s*月|(?:" + _CN_MONTH_ALT + r")月)"
)

#: `N月`（阿拉伯數字）。⚠️ 前面不得再接數字（`20260901` 不是「1 月」），
#: 「三個月」「3 個月」因為中間隔了「個」而**不會**命中（刻意：那是天數／期間，
#: 不是期別）。
_ARABIC_MONTH_RE: Final = re.compile(r"(?<!\d)(\d{1,2})月")

#: `N月`（中文數字）。長字面在前，否則「十一月」會先被「十」吃掉。
_CN_MONTH_RE: Final = re.compile(r"(" + _CN_MONTH_ALT + r")月")


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
    得到不同結果）：有年份的寫法（`YYYY-MM`／`YYYY/MM` → `YYYY年M月`／`YYYY年`＋中文
    數字月）→ 阿拉伯數字月 → 中文數字月 → 這期類 → 上期類。第一個命中的就是答案。
    有年份的寫法命中時，年份就是所寫的年份（⛔ 往回推、⛔ 被「去年／今年」覆寫）。
    寫了中文數字西元年（`_CN_YEAR_MONTH_RE`）⇒ 整句 `None`（期別片 P-1c）。
    一則原話裡的**全部**期別見 `parse_periods`。
    """
    if not isinstance(text, str) or not text.strip():
        return None

    # 期別片 P-1c：寫了西元年但認不得（中文數字年）⇒ 解析不到（⛔ 只吃月份往回推）。
    if _CN_YEAR_MONTH_RE.search(text) is not None:
        return None

    # verifier 2026-09-10 P2-1：年份修飾詞是封閉表——「去年」⇒ 上一年、「今年」⇒ 當年；
    # 「明年」「前年」等表內但不支援的修飾詞 ⇒ 整句 None（⛔ 不忽略修飾詞只吃月份：那會把
    # 「去年九月」對到今年九月，卡看起來完全正常）。
    year_shift: Optional[int] = None
    for term, shift in YEAR_MODIFIER_TERMS.items():
        if term in text:
            if shift is None:
                return None
            year_shift = shift
            break
    unpaid_only = any(term in text for term in UNPAID_TERMS)

    year: Optional[int] = None
    month: Optional[int] = None
    year_written = False

    ym = _YEAR_MONTH_RE.search(text)
    if ym is not None:
        candidate = _month_in_range(ym.group(2))
        if candidate is not None:
            year, month = int(ym.group(1)), candidate

    if month is None:
        yzm = _YEAR_ZH_MONTH_RE.search(text)
        if yzm is not None:
            candidate = _year_zh_month(yzm)
            if candidate is not None:
                year, month = int(yzm.group(1)), candidate

    if month is not None:
        year_written = True   # 期別片 R2：有寫年份 ⇒ ⛔ 往回推、⛔ 修飾詞覆寫

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

    if month is not None and year_shift is not None and not year_written and ym is None:
        year = today.year + year_shift   # 修飾詞優先於「裸月份取最近」的推定
    if month is None and not unpaid_only:
        # 封閉語法一個都沒命中 ⇒ 解析不到（⛔ 不回一個「什麼都不篩」的空規格：
        # 那會讓呼叫端分不出「使用者沒講期別」與「講了但我看不懂」）。
        return None
    return PeriodSpec(year=year, month=month, unpaid_only=unpaid_only)


def _year_zh_month(match: "re.Match") -> Optional[int]:
    """`_YEAR_ZH_MONTH_RE` 命中 → 月份（阿拉伯數字驗值域；中文數字查封閉表）。"""
    if match.group(2) is not None:
        return _month_in_range(match.group(2))
    return CN_MONTH_VALUES[match.group(3)]


# ---------------------------------------------------------------------------
# 期別片 P-1b：一則原話裡的**全部**期別（值閘的使用者原話集合 U）
# ---------------------------------------------------------------------------
#: 已被有年份寫法／中文數字年吃掉的那一段，換成這個字元（等長、非數字、非空白、非「的」）
#: ⇒ 後面的裸月份掃描看不到它，「去年／今年」也不會隔著它綁到別的月份。
_CONSUMED: Final[str] = "\x00"

#: 緊鄰在期別項前面的年份修飾詞（可夾空白與一個「的」）。group 名 `mod`。
_MODIFIER_PREFIX: Final[str] = (
    r"(?:(?P<mod>"
    + "|".join(re.escape(t) for t in sorted(YEAR_MODIFIER_TERMS, key=len, reverse=True))
    + r")\s*(?:的\s*)?)?"
)
_ITEM_ARABIC_RE: Final = re.compile(_MODIFIER_PREFIX + r"(?<!\d)(?P<m>\d{1,2})月")
_ITEM_CN_RE: Final = re.compile(_MODIFIER_PREFIX + r"(?P<m>" + _CN_MONTH_ALT + r")月")
_ITEM_THIS_RE: Final = re.compile(
    _MODIFIER_PREFIX + r"(?P<m>"
    + "|".join(re.escape(t) for t in sorted(THIS_PERIOD_TERMS, key=len, reverse=True)) + r")"
)
_ITEM_LAST_RE: Final = re.compile(
    _MODIFIER_PREFIX + r"(?P<m>"
    + "|".join(re.escape(t) for t in sorted(LAST_PERIOD_TERMS, key=len, reverse=True)) + r")"
)


def _consume(text: str, rx: "re.Pattern") -> Tuple[str, list]:
    """`rx` 的每一處命中 ⇒ 回（吃掉命中段後的字串, 命中清單）。等長替換，位置不變。"""
    matches = list(rx.finditer(text))
    if not matches:
        return text, matches
    chars = list(text)
    for m in matches:
        chars[m.start():m.end()] = _CONSUMED * (m.end() - m.start())
    return "".join(chars), matches


def _apply_modifier(mod: Optional[str], year: int, today: date) -> Optional[int]:
    """緊鄰修飾詞 ⇒ 年份：無 ⇒ 原推定；「去年／今年」⇒ 今年＋位移；「明年／前年／後年」
    （表內值 `None`）⇒ `None`＝這一項丟掉。"""
    if mod is None:
        return year
    shift = YEAR_MODIFIER_TERMS[mod]
    if shift is None:
        return None
    return today.year + shift


def parse_periods(text: Any, today: date) -> Tuple[PeriodSpec, ...]:
    """一則原話裡的**全部**期別（期別片 P-1b；值閘的使用者原話集合 U 由各則聯集而成）。

    與 `parse_period` 同一套封閉語法、同樣是純函式（⛔ 讀時鐘，`today` 由呼叫端傳）。
    每一項都有年月（`has_month`）；`unpaid_only` 是整則原話的狀態（同 `parse_period`）。
    「未繳」單獨出現不成項（呼叫端以 `UNPAID_TERMS` 判）。非字串／空白／沒有任何期別 ⇒ `()`。

    收項規則（安全審查 B1、D2；計畫 §5.1）：
    1. 有年份寫法（`YYYY-MM`／`YYYY/MM`、`YYYY年M月`／`YYYY年`＋中文數字月）的**每一處**
       都成項，年份＝所寫年份；命中段先吃掉。
    2. 中文數字西元年＋月份（P-1c）**只丟這一項**、命中段同樣吃掉——⚠️ 安全關鍵：被吃掉
       的月份字 ⛔ 再當裸月份算一次（「2027年1月」的 U ⛔ 含 2026/01）。
    3. 其餘：阿拉伯數字月、中文數字月、這期類、上期類，各自取同 `parse_period` 的推定。
       緊鄰在前（可夾空白與一個「的」）的「去年／今年」只改**這一項**的年份；緊鄰的
       「明年／前年／後年」⇒ 這一項丟掉；不緊鄰的修飾詞不影響任何項（「去年也延過，這次
       九月的」的九月 ⇒ 今年九月）。
    4. 輸出順序固定（有年份 → 阿拉伯數字月 → 中文數字月 → 這期類 → 上期類，同類依出現
       位置），重複項只留第一個。
    """
    if not isinstance(text, str) or not text.strip():
        return ()
    unpaid_only = any(term in text for term in UNPAID_TERMS)
    found: list = []

    def _add(year: Optional[int], month: Optional[int]) -> None:
        if year is None or month is None:
            return
        spec = PeriodSpec(year=year, month=month, unpaid_only=unpaid_only)
        if spec not in found:
            found.append(spec)

    rest, matches = _consume(text, _YEAR_MONTH_RE)
    for m in matches:
        _add(int(m.group(1)), _month_in_range(m.group(2)))
    rest, matches = _consume(rest, _YEAR_ZH_MONTH_RE)
    for m in matches:
        _add(int(m.group(1)), _year_zh_month(m))
    rest, _dropped = _consume(rest, _CN_YEAR_MONTH_RE)   # P-1c：只丟這一項

    for m in _ITEM_ARABIC_RE.finditer(rest):
        month = _month_in_range(m.group("m"))
        if month is not None:
            _add(_apply_modifier(m.group("mod"), _year_for_bare_month(month, today), today), month)
    for m in _ITEM_CN_RE.finditer(rest):
        month = CN_MONTH_VALUES[m.group("m")]
        _add(_apply_modifier(m.group("mod"), _year_for_bare_month(month, today), today), month)
    for m in _ITEM_THIS_RE.finditer(rest):
        _add(_apply_modifier(m.group("mod"), today.year, today), today.month)
    for m in _ITEM_LAST_RE.finditer(rest):
        year, month = _previous_month(today)
        _add(_apply_modifier(m.group("mod"), year, today), month)
    return tuple(found)


__all__ = [
    "CN_MONTH_VALUES",
    "LAST_PERIOD_TERMS",
    "MAX_MONTHS_AHEAD",
    "YEAR_MODIFIER_TERMS",
    "PeriodSpec",
    "THIS_PERIOD_TERMS",
    "UNPAID_TERMS",
    "parse_period",
    "parse_periods",
]
