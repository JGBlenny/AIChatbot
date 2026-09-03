"""謄本映射（design.md 元件 5）：DocuMind `transcript` 五欄 → 物件草稿欄位。需求 3.1–3.5。

⚠️ 鍵名沿用 DocuMind 原名（`land_number／building_number／area／rights_scope／owner`）——
JGB `estates` 的落點待產品決定（謄本在 JGB 目前只有日期與面積兩欄），⛔ 不在此自行對應。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from services.ocr_mapping.field_normalizer import normalize_area
from services.ocr_mapping.models import TRANSCRIPT_FIELDS, DocuMindPage, DocumentType, FieldSource, FieldValue, empty_fields
from services.ocr_mapping.page_merger import MergedField

_OWNER_SEP = re.compile(r"\s*[、,，及和與/／]\s*")
LAND_ONLY_NOTE = "可能為土地謄本：building_number 空而 land_number 非空（⛔ 未以地號填建號）"


def _base(mf: MergedField, raw: str) -> Dict[str, Any]:
    return {
        "confidence": mf.confidence, "confidence_source": mf.confidence_source,
        "page": mf.page, "raw": raw, "conflicts": list(mf.conflicts),
    }


def _ocr_scalar(mf: MergedField) -> FieldValue:
    v = str(mf.value).strip()
    return FieldValue(value=v, jgb_value=v, source=FieldSource.ocr, **_base(mf, v))


def _area(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    r = normalize_area(raw)
    if r is None:                                   # 解析不了 ⇒ absent，但 raw 留給人看
        return FieldValue(source=FieldSource.absent, **_base(mf, raw))
    return FieldValue(value=r[0], jgb_value=r[0], source=FieldSource.derived, **_base(mf, raw))


def _owner(mf: MergedField) -> FieldValue:
    raw = str(mf.value).strip()
    parts = [p for p in _OWNER_SEP.split(raw) if p]
    if len(parts) > 1:                              # 多所有權人 → 陣列（需求 3.4），jgb_value 非標量故留空
        return FieldValue(value=parts, jgb_value=None, source=FieldSource.ocr, **_base(mf, raw))
    return FieldValue(value=raw, jgb_value=raw, source=FieldSource.ocr, **_base(mf, raw))


_HANDLERS = {"area": _area, "owner": _owner}


def map_transcript(merged: Mapping[str, MergedField], pages: Sequence[DocuMindPage]) -> Tuple[Dict[str, FieldValue], List[str]]:
    """回 (fields, notes)。fields 鍵集合恆為 TRANSCRIPT_FIELDS；notes 供 `provenance.notes`。"""
    fields = empty_fields(DocumentType.transcript)
    for name in TRANSCRIPT_FIELDS:
        mf = merged.get(name)
        if mf is None or mf.value in (None, "", [], {}):
            continue
        fields[name] = _HANDLERS.get(name, _ocr_scalar)(mf)
    notes: List[str] = []
    if fields["building_number"].source is FieldSource.absent and fields["land_number"].source is not FieldSource.absent:
        notes.append(LAND_ONLY_NOTE)
    return fields, notes


__all__ = ["LAND_ONLY_NOTE", "map_transcript"]
