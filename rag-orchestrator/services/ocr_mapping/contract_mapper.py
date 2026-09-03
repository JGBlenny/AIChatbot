"""合約映射（design.md 元件 6）：DocuMind `contract` 通用欄位 → JGB 租約欄位（line-bot §7.2）。需求 4.1–4.5、5.3。

來源兩層（需求 4.6，D1 定案 A，2026-09-03）：
- 通用三組 `contract_metadata／parties／financial_terms`（DocuMind 一定回）；
- 租約專用 `rental_terms`（DocuMind 原文含租賃標記時才多掛；`contract_field_extractor.py` 符號 `rental_fields`）。
  同一 JGB 欄位兩邊都有 ⇒ **租約專用優先**、通用值進 `conflicts` 反白；租約值解析不了 ⇒ 退回通用。
`cycle`／`early_termination_penalty*` 兩邊都沒有 ⇒ 恆 absent。
⚠️ 「AI 不碰數字」：金額、日期、月數全部經 field_normalizer 的決定性換算；本模組無 LLM。
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence

from services.ocr_mapping.deposit_rule import decide_deposit
from services.ocr_mapping.field_normalizer import (
    _NUMERIC_CLASS, _cn_to_int, normalize_amount, normalize_cycle_date, normalize_date, normalize_lease_months,
)
from services.ocr_mapping.models import (
    REQUIRED_FOR_WRITE, DocuMindPage, DocumentType, FieldConflict, FieldSource, FieldValue, empty_fields,
)
from services.ocr_mapping.name_splitter import NamePolicy, split_name
from services.ocr_mapping.page_merger import MergedField

#: JGB 欄位／中介鍵 → DocuMind 點路徑（需求 4.1 表）；`party_a*` 刻意不在表內（出租方由 JGB 帳號帶入）
CONTRACT_SOURCE_MAP: Dict[str, str] = {
    "date_start": "contract_metadata.effective_date",
    "lease_signing_date": "contract_metadata.signing_date",
    "rent": "financial_terms.contract_amount",
    "currency": "financial_terms.currency",
    "cycle_date": "financial_terms.payment_deadline",
    "party_b": "parties.party_b",
    "payment_method": "financial_terms.payment_method",
}

#: D1 定案 A：DocuMind `rental_terms` 的值是**擷取群**不是整句——「13,800」沒有「元」、民國日期被空白串成「114 1 21」、
#: 繳費日只剩「5」⇒ 各有專用換算（`_rental_rent_field`／`_payment_day_field`／`_ROC_SPACED`）。
#: ⛔ `rental_terms.deposit` 刻意不列：DocuMind 把「押金：27,600元」與「押金：相當於2個月租金」都填進同一鍵（回「27,600」／「2」），
#:    收到「2」無法區分月數與金額，二選一鐵則下寧可 absent，等 DocuMind 拆鍵（BACKLOG「DocuMind 側待辦」）。
CONTRACT_RENTAL_MAP: Dict[str, str] = {
    "date_start": "rental_terms.date_start",
    "date_end": "rental_terms.date_end",
    "rent": "rental_terms.monthly_rent",
    "cycle_date": "rental_terms.payment_day",
    "party_b": "rental_terms.tenant_name",
}
#: `merge_pages` 要合併的全部來源路徑（通用 ∪ 租約專用；保序去重）
CONTRACT_SOURCE_FIELDS: tuple = tuple(dict.fromkeys([*CONTRACT_SOURCE_MAP.values(), *CONTRACT_RENTAL_MAP.values()]))

#: ⚠️ 2026-09-03 對抗驗證 ②-1／N4：視窗遇標點即停（「為期二年，押金三個月」曾變 27 個月）
_LEASE_WINDOW = re.compile(r"(?:租期|租賃期間|為期)[^。\n，,；;、（(]{0,30}")
#: 明文到期日「…起至 <日期> 止」——⑧(a)：先讀明文，月數推算只當 fallback
_END_DATE = re.compile(r"(?:至|到)\s*((?:中華民國|民國)?\s*\d{2,4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|\d{2,4}[/.\-]\d{1,2}[/.\-]\d{1,2})\s*止")
_DEPOSIT_WINDOW = re.compile(r"[^。\n]{0,20}押金[^。\n]{0,40}")
#: ⑧(b)：提前終止「N 日／天前」通知期——決定性，⛔ 不用 LLM；「一個月前」不是日數 ⇒ absent
_ET_WINDOW = re.compile(r"(?:提前終止|提前解約|終止租約|解約)[^。\n]{0,40}")
_ET_DAYS = re.compile(rf"({_NUMERIC_CLASS}+)\s*(?:日|天)\s*前")


class ContractMapping(NamedTuple):
    fields: Dict[str, FieldValue]
    needs_confirmation: List[str]
    unmapped_from_fields: List[str]
    absorbed_raws: List[str]


def _empty(v) -> bool:
    return v in (None, "", [], {})


def _base(mf: MergedField, raw: str) -> dict:
    return {"confidence": mf.confidence, "confidence_source": mf.confidence_source, "page": mf.page, "raw": raw}


def _date_field(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    nd = normalize_date(raw)
    if nd is None:
        return FieldValue(source=FieldSource.absent, conflicts=list(mf.conflicts), **_base(mf, raw))
    # 需求 4.1／5.3：同日期不同寫法（民國 vs 西元）不算衝突；換算後仍不同者才保留
    real_conflicts: List[FieldConflict] = []
    for c in mf.conflicts:
        cd = normalize_date(str(c.value)) if c.value is not None else None
        if cd is None or cd.iso != nd.iso:
            real_conflicts.append(c)
    src = FieldSource.derived if nd.calendar == "roc" else FieldSource.ocr
    return FieldValue(value=nd.iso, jgb_value=nd.ymd, source=src, conflicts=real_conflicts, **_base(mf, raw))


def _rent_field(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    r = normalize_amount(raw)
    if r is None:
        return FieldValue(source=FieldSource.absent, conflicts=list(mf.conflicts), **_base(mf, raw))
    return FieldValue(value=r[0], jgb_value=r[0], source=FieldSource.derived, conflicts=list(mf.conflicts), **_base(mf, raw))


def _currency_field(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    return FieldValue(value=raw, jgb_value=raw, source=FieldSource.ocr, conflicts=list(mf.conflicts), **_base(mf, raw))


def _cycle_date_field(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    r = normalize_cycle_date(raw)
    if r is None:
        return FieldValue(source=FieldSource.absent, conflicts=list(mf.conflicts), **_base(mf, raw))
    return FieldValue(value=r[0], jgb_value=r[0], source=FieldSource.derived, conflicts=list(mf.conflicts), **_base(mf, raw))


_BARE_NUMBER = re.compile(rf"^{_NUMERIC_CLASS}+$")


def _rental_rent_field(mf: MergedField) -> FieldValue:
    """`rental_terms.monthly_rent` 是擷取群（「13,800」「壹萬參仟捌佰」），沒有「元」也決定性收下；整句則走 normalize_amount。
    ⚠️ 只給租約專用來源用——通用 `contract_amount` 仍守需求 5.5（無單位／幣別 ⇒ absent）。"""
    raw = str(mf.value).strip()
    value: Optional[int] = _cn_to_int(raw) if _BARE_NUMBER.fullmatch(raw) else None
    if value is None:
        r = normalize_amount(raw)
        value = r[0] if r else None
    if value is None or value <= 0:
        return FieldValue(source=FieldSource.absent, conflicts=list(mf.conflicts), **_base(mf, raw))
    return FieldValue(value=value, jgb_value=value, source=FieldSource.derived, conflicts=list(mf.conflicts), **_base(mf, raw))


def _payment_day_field(mf: MergedField) -> FieldValue:
    """`rental_terms.payment_day`：「5」→5；「每月5日」走 normalize_cycle_date；「月初／月底」⛔ 不猜 ⇒ absent（退回通用備援）。"""
    raw = str(mf.value).strip()
    if raw.isdigit():
        day: Optional[int] = int(raw)
    else:
        r = normalize_cycle_date(raw)
        day = r[0] if r else None
    if day is None or not 1 <= day <= 31:
        return FieldValue(source=FieldSource.absent, conflicts=list(mf.conflicts), **_base(mf, raw))
    return FieldValue(value=day, jgb_value=day, source=FieldSource.derived, conflicts=list(mf.conflicts), **_base(mf, raw))


def _prefer(primary: Optional[FieldValue], fallback: Optional[FieldValue]) -> tuple[Optional[FieldValue], Optional[str]]:
    """需求 4.6：租約專用值優先；兩者皆可解析且換算後不同 ⇒ 通用值進 `conflicts`（`put()` 據此反白）。
    回 (欄位值, 需一併吸收的落選 raw)——落選原文也被欄位吃掉，條款切分才不會再列一次。"""
    p_ok = primary is not None and primary.source is not FieldSource.absent
    f_ok = fallback is not None and fallback.source is not FieldSource.absent
    if p_ok and f_ok:
        if primary.value != fallback.value:
            primary = primary.model_copy(update={"conflicts": [
                *primary.conflicts, FieldConflict(value=fallback.value, page=fallback.page, confidence=fallback.confidence)]})
        return primary, fallback.raw
    if p_ok:
        return primary, None
    if f_ok:
        return fallback, None
    return fallback or primary, None


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _first_window(pages: Sequence[DocuMindPage], pattern: re.Pattern) -> Optional[tuple[str, DocuMindPage]]:
    for pg in pages:
        m = pattern.search(pg.ocr_raw.text or "")
        if m:
            return m.group(0), pg
    return None


def map_contract(merged: Mapping[str, MergedField], pages: Sequence[DocuMindPage], *,
                 name_policy: NamePolicy = NamePolicy.split) -> ContractMapping:
    fields = empty_fields(DocumentType.contract)
    needs: List[str] = []
    unmapped: List[str] = []
    absorbed: List[str] = []

    def mf_path(path: Optional[str]) -> Optional[MergedField]:
        mf = merged.get(path) if path else None
        return None if mf is None or _empty(mf.value) else mf

    def mf_of(key: str) -> Optional[MergedField]:
        return mf_path(CONTRACT_SOURCE_MAP[key])

    def put(name: str, fv: FieldValue) -> None:
        fields[name] = fv
        if fv.source is not FieldSource.absent and fv.raw:
            absorbed.append(fv.raw)
        if fv.conflicts:
            needs.append(name)

    def put_preferred(name: str, primary: Optional[FieldValue], fallback: Optional[FieldValue]) -> None:
        fv, loser_raw = _prefer(primary, fallback)
        if fv is not None:
            put(name, fv)
            if loser_raw:
                absorbed.append(loser_raw)

    # 只有通用來源的欄位
    for name, fn in (("lease_signing_date", _date_field), ("currency", _currency_field)):
        mf = mf_of(name)
        if mf is not None:
            put(name, fn(mf))

    # 兩層來源的欄位（需求 4.6）：rental_terms 優先、通用備援、皆有且不同 ⇒ 衝突反白
    for name, rental_fn, generic_fn in (("date_start", _date_field, _date_field),
                                        ("rent", _rental_rent_field, _rent_field),
                                        ("cycle_date", _payment_day_field, _cycle_date_field)):
        r_mf, g_mf = mf_path(CONTRACT_RENTAL_MAP[name]), mf_of(name)
        put_preferred(name, rental_fn(r_mf) if r_mf is not None else None, generic_fn(g_mf) if g_mf is not None else None)

    # 承租方姓名（D3 策略）：rental_terms.tenant_name 優先於 parties.party_b
    r_mf, g_mf = mf_path(CONTRACT_RENTAL_MAP["party_b"]), mf_of("party_b")
    chosen = r_mf or g_mf
    if chosen is not None:
        ns = split_name(str(chosen.value).strip(), name_policy, confidence=chosen.confidence, page=chosen.page)
        full = ns.full
        if r_mf is not None and g_mf is not None and str(g_mf.value).strip() != str(r_mf.value).strip():
            loser = str(g_mf.value).strip()
            full = full.model_copy(update={"conflicts": [*full.conflicts, FieldConflict(value=loser, page=g_mf.page, confidence=g_mf.confidence)]})
            absorbed.append(loser)
        put("to_user_last_name", ns.last); put("to_user_first_name", ns.first); put("party_b_full_name", full)
        needs.extend(ns.needs_confirmation)

    # payment_method：JGB 收款方式是結構化旗標，⛔ 不由自由文字推導 ⇒ 原樣進未映射條款（需求 4.5）
    mf = mf_of("payment_method")
    if mf is not None:
        unmapped.append(str(mf.value).strip())

    # 到期日（需求 4.2／4.6＋⑧(a)）：① rental_terms.date_end；② 明文「…起至 <日期> 止」；③ 租期月數推算只當 fallback。
    # 取第一個可用者為值，其餘不同者進 conflicts 反白；三者一致則不反白。
    rental_end: Optional[FieldValue] = None
    r_mf = mf_path(CONTRACT_RENTAL_MAP["date_end"])
    if r_mf is not None:
        fv = _date_field(r_mf)
        if fv.source is not FieldSource.absent:
            rental_end = fv

    explicit_end: Optional[FieldValue] = None
    hit = _first_window(pages, _END_DATE)
    if hit:
        m_text, pg = hit
        m = _END_DATE.search(pg.ocr_raw.text or "")
        nd = normalize_date(m.group(1)) if m else None
        if nd is not None:
            explicit_end = FieldValue(value=nd.iso, jgb_value=nd.ymd,
                                      source=FieldSource.derived if nd.calendar == "roc" else FieldSource.ocr,
                                      confidence=pg.ocr_raw.confidence, page=pg.page_number, raw=m.group(0))

    derived_end: Optional[FieldValue] = None
    hit = _first_window(pages, _LEASE_WINDOW)
    if hit:
        window, pg = hit
        lm = normalize_lease_months(window)
        if lm is not None:
            put("lease_months", FieldValue(value=lm[0], jgb_value=lm[0], source=FieldSource.derived,
                                           confidence=pg.ocr_raw.confidence, page=pg.page_number, raw=window))
            ds = fields["date_start"]
            if ds.source is not FieldSource.absent and isinstance(ds.value, str):
                start = date.fromisoformat(ds.value)
                end = _add_months(start, lm[0]) - timedelta(days=1)
                derived_end = FieldValue(value=end.isoformat(), jgb_value=end.year * 10000 + end.month * 100 + end.day,
                                         source=FieldSource.derived, confidence=min(ds.confidence or 1.0, pg.ocr_raw.confidence),
                                         page=pg.page_number, raw=f"{ds.raw}；{window}")

    candidates = [c for c in (rental_end, explicit_end, derived_end) if c is not None]
    if candidates:
        chosen = candidates[0]
        chosen_is_derived = chosen is derived_end
        losers: List[FieldConflict] = []
        seen = {chosen.value}
        for c in candidates[1:]:
            if c.value not in seen:                      # 明文與推算同值 ⇒ 只記一筆落選
                losers.append(FieldConflict(value=c.value, page=c.page, confidence=c.confidence)); seen.add(c.value)
            if c is explicit_end and c.raw:
                absorbed.append(c.raw)                   # 明文那句被欄位吃掉，條款不再列；推算 raw 是合成字串，不吸收
        if losers:
            chosen = chosen.model_copy(update={"conflicts": [*chosen.conflicts, *losers]})
        put("date_end", chosen)                          # 有衝突時 put() 依 conflicts 反白
        if chosen_is_derived:
            needs.append("date_end")                     # 推算值一律反白

    # 提前終止通知期（⑧(b)）：「三十日前」「60 天前」→ early_termination_days（derived，反白）
    hit = _first_window(pages, _ET_WINDOW)
    if hit:
        window, pg = hit
        m = _ET_DAYS.search(window)
        days = _cn_to_int(m[1]) if m else None
        if days is not None and 1 <= days <= 365:
            put("early_termination_days", FieldValue(value=days, jgb_value=days, source=FieldSource.derived,
                                                     confidence=pg.ocr_raw.confidence, page=pg.page_number, raw=window))
            needs.append("early_termination_days")

    # 押金二選一（需求 6）
    hit = _first_window(pages, _DEPOSIT_WINDOW)
    if hit:
        window, pg = hit
        dd = decide_deposit(window, page=pg.page_number, confidence=pg.ocr_raw.confidence)
        put("deposit_type", dd.deposit_type); put("deposit", dd.deposit); put("deposit_amount", dd.deposit_amount)
        if dd.needs_confirmation:
            needs.append("deposit_type")

    # 必填缺漏（需求 4.4）
    for name in REQUIRED_FOR_WRITE:
        if fields[name].source is FieldSource.absent:
            needs.append(name)

    ordered = list(dict.fromkeys(needs))
    return ContractMapping(fields, ordered, unmapped, list(dict.fromkeys(absorbed)))


__all__ = ["CONTRACT_RENTAL_MAP", "CONTRACT_SOURCE_FIELDS", "CONTRACT_SOURCE_MAP", "ContractMapping", "map_contract"]
