"""承租方姓名切分（design.md 元件 6／name_splitter）。需求 4.1；D3 兩策略皆支援。

DocuMind 只回 `party_b` 全名，JGB 分 `to_user_last_name／to_user_first_name`。
切分屬**猜測**（複姓表命中取兩字、否則首字），所以 `NamePolicy.split` 下兩欄**恆**進
`needs_confirmation`，並永遠保留 `party_b_full_name` 原串讓 LIFF 可改。
⚠️ 複姓表待 JGB 慣例（research.md Q5），先以常見表落地、可配置。
"""
from __future__ import annotations

from enum import Enum
from typing import List, NamedTuple, Optional, Tuple

from services.ocr_mapping.models import FieldSource, FieldValue

#: 台灣常見複姓（可配置；命中即取兩字為姓）
COMPOUND_SURNAMES: Tuple[str, ...] = (
    "歐陽", "司徒", "司馬", "張簡", "范姜", "諸葛", "上官", "端木", "東方", "獨孤",
    "令狐", "慕容", "夏侯", "尉遲", "皇甫", "長孫", "鮮于", "宇文", "呂尚", "張廖",
)


class NamePolicy(str, Enum):
    split = "split"
    keep_full = "keep_full"


class NameSplit(NamedTuple):
    last: FieldValue
    first: FieldValue
    full: FieldValue
    needs_confirmation: List[str]


def split_name(full: Optional[str], policy: NamePolicy, *, confidence: Optional[float], page: Optional[int]) -> NameSplit:
    name = (full or "").strip()
    if not name:
        return NameSplit(FieldValue(), FieldValue(), FieldValue(), [])
    full_fv = FieldValue(value=name, jgb_value=name, source=FieldSource.ocr, confidence=confidence, page=page, raw=name)
    if policy is NamePolicy.keep_full:
        return NameSplit(FieldValue(), FieldValue(), full_fv, [])

    comp = next((c for c in COMPOUND_SURNAMES if name.startswith(c) and len(name) > len(c)), None)
    last, first = (comp, name[len(comp):]) if comp else (name[0], name[1:])
    derived = {"source": FieldSource.derived, "confidence": confidence, "page": page, "raw": name}
    last_fv = FieldValue(value=last, jgb_value=last, **derived)
    first_fv = FieldValue(value=first, jgb_value=first, **derived) if first else FieldValue(raw=name)
    return NameSplit(last_fv, first_fv, full_fv, ["to_user_last_name", "to_user_first_name"])


__all__ = ["COMPOUND_SURNAMES", "NamePolicy", "NameSplit", "split_name"]
