"""編排（design.md 元件 9）：串接合併→映射→條款→草稿語意。需求 1.4、7.5、7.6、9.1、9.2。

同步、無狀態、無 I/O；第二段 LLM 抽取（元件 8）由 router 依旗標另行接入，⛔ 本模組不呼叫 LLM。
`status` 規則（需求 7.6）：DocuMind `needs_review=true` **或** 任一必填欄位 absent ⇒ `draft`；否則 `ready`。
`needs_confirmation`（需求 7.5）＝ DocuMind 各頁聯集 ∪ 跨頁衝突欄位 ∪ 映射規則新增 ∪ 必填缺漏，去重、順序穩定。
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from services.ocr_mapping.clause_splitter import split_clauses
from services.ocr_mapping.contract_mapper import CONTRACT_SOURCE_FIELDS, map_contract
from services.ocr_mapping.models import (
    MAPPING_VERSION, REQUIRED_FOR_WRITE, TRANSCRIPT_FIELDS,
    DocumentType, FieldSource, FieldValue, MappingResult, OcrMappingRequest, Provenance,
)
from services.ocr_mapping.name_splitter import NamePolicy
from services.ocr_mapping.page_merger import collect_needs_confirmation, merge_pages
from services.ocr_mapping.transcript_mapper import map_transcript

#: 謄本沒有 JGB 的 isWriteDone 概念；保守起見五欄任一 absent 即 draft（缺欄本來就該人確認）
_REQUIRED: Dict[DocumentType, Sequence[str]] = {
    DocumentType.contract: REQUIRED_FOR_WRITE,
    DocumentType.transcript: TRANSCRIPT_FIELDS,
}


def _dedup(*groups: Sequence[str]) -> List[str]:
    seen: dict[str, None] = {}
    for g in groups:
        for x in g:
            if x and x not in seen:
                seen[x] = None
    return list(seen)


def run_mapping(req: OcrMappingRequest, *, name_policy: NamePolicy = NamePolicy.split) -> MappingResult:
    pages = req.pages
    notes: List[str] = []
    unmapped: List[str] = []
    rule_needs: List[str] = []

    if req.document_type is DocumentType.transcript:
        merged = merge_pages(pages, TRANSCRIPT_FIELDS, req.field_confidences, req.consensus)
        fields, notes = map_transcript(merged, pages)
    else:
        merged = merge_pages(pages, CONTRACT_SOURCE_FIELDS, req.field_confidences, req.consensus)   # 通用 ∪ rental_terms（需求 4.6）
        cm = map_contract(merged, pages, name_policy=name_policy)
        fields, rule_needs = cm.fields, list(cm.needs_confirmation)
        unmapped = _dedup(cm.unmapped_from_fields, split_clauses(pages, cm.absorbed_raws))

    conflict_fields = [n for n, fv in fields.items() if fv.conflicts]
    required = _REQUIRED[req.document_type]
    missing = [n for n in required if fields[n].source is FieldSource.absent]

    needs = _dedup(collect_needs_confirmation(pages), conflict_fields, rule_needs, missing)
    status = "draft" if (req.needs_review or missing) else "ready"

    provenance = Provenance(
        document_type=req.document_type, total_pages=req.total_pages, needs_review=req.needs_review,
        review_item_id=req.review_item_id,
        documind_estimated_cost=(req.stats.estimated_cost if req.stats else None),
        mapping_version=MAPPING_VERSION, notes=notes,
    )
    return MappingResult(status=status, document_type=req.document_type, fields=fields,
                         needs_confirmation=needs, unmapped_clauses=unmapped, provenance=provenance)


__all__ = ["run_mapping"]
