"""unit 層：編排與草稿語意（design.md 元件 9／mapper.run_mapping）。需求 1.4、7.5、7.6、9.1、9.2。

純函式端到端：fixture → MappingResult；⛔ 不經 HTTP、不經 DB。
"""
import json
from pathlib import Path

import pytest

from services.ocr_mapping.mapper import run_mapping
from services.ocr_mapping.models import (
    CONTRACT_FIELDS, MAPPING_VERSION, REQUIRED_FOR_WRITE, TRANSCRIPT_FIELDS, FieldSource, OcrMappingRequest,
)

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c", "target_user": "landlord"}


def _req(name: str, **override) -> OcrMappingRequest:
    data = json.loads((FIX / name).read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    data.update(override)
    return OcrMappingRequest(**data, **IDENTITY)


# ── 合約 fixture 端到端 ───────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.1")
def test_contract_fixture_end_to_end_shape_and_status():
    r = run_mapping(_req("documind_contract_sample.json"))
    assert r.status == "draft" and set(r.fields) == set(CONTRACT_FIELDS)
    assert r.fields["rent"].value == 13800 and r.fields["date_start"].jgb_value == 20250121
    assert "半年繳整年優惠6000" in r.unmapped_clauses and "轉帳至甲方指定帳戶" in r.unmapped_clauses
    assert not any("貳萬柒仟陸佰" in c for c in r.unmapped_clauses)          # 押金條款整段被欄位吸收 ⇒ 不重列
    # ⚠️ 租金那一行含「乙方應於每月五日前繳納」等未被完整吸收的義務語 ⇒ 依 R7.1／拍板 4 寧可多列不可丟
    assert any("壹萬參仟捌佰" in c for c in r.unmapped_clauses)


@pytest.mark.req("documind-ocr-mapping:7.5")
def test_needs_confirmation_is_union_dedup_ordered():
    r = run_mapping(_req("documind_contract_sample.json"))
    nc = r.needs_confirmation
    assert len(nc) == len(set(nc))                                          # 去重
    assert {"contract_number", "party_b_address"} <= set(nc)               # DocuMind 各頁聯集
    assert {"to_user_last_name", "to_user_first_name", "early_termination_days"} <= set(nc)   # chatai 規則新增
    assert "date_end" not in nc                                             # 明文到期日讀到 ⇒ 不反白（⑧(a)）
    assert nc == run_mapping(_req("documind_contract_sample.json")).needs_confirmation   # 順序穩定


@pytest.mark.req("documind-ocr-mapping:9.2")
def test_provenance_passthrough():
    r = run_mapping(_req("documind_contract_sample.json"))
    p = r.provenance
    assert (p.document_type.value, p.total_pages, p.needs_review) == ("contract", 3, True)
    assert p.review_item_id == "0f3c1a2e-0000-4000-8000-000000000001"
    assert p.documind_estimated_cost == 0.08 and p.mapping_version == MAPPING_VERSION


# ── 謄本 fixture 端到端 ───────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.1")
def test_transcript_fixture_end_to_end():
    r = run_mapping(_req("documind_transcript_sample.json"))
    assert set(r.fields) == set(TRANSCRIPT_FIELDS) and r.status == "draft"
    assert r.fields["area"].value == pytest.approx(3406.98)
    assert {"building_number", "area"} <= set(r.needs_confirmation)        # DocuMind 聯集
    assert "owner" in r.needs_confirmation                                  # 跨頁衝突
    assert r.unmapped_clauses == []                                         # 謄本不產條款


# ── R1.4 空頁 → 200 draft、全欄 absent、必填全列，⛔ 不 500 ───────────────────
@pytest.mark.req("documind-ocr-mapping:1.4")
def test_empty_pages_contract_is_draft_with_all_required_listed():
    r = run_mapping(_req("documind_contract_sample.json", pages=[], total_pages=0))
    assert r.status == "draft" and all(v.source is FieldSource.absent for v in r.fields.values())
    assert set(REQUIRED_FOR_WRITE) <= set(r.needs_confirmation)


@pytest.mark.req("documind-ocr-mapping:1.4")
def test_all_empty_structured_data_transcript_is_draft_with_all_fields_listed():
    req = _req("documind_transcript_sample.json")
    for p in req.pages:
        p.structured_data = {}
    r = run_mapping(req)
    assert r.status == "draft" and set(TRANSCRIPT_FIELDS) <= set(r.needs_confirmation)


# ── R7.6 needs_review=true 恆 draft；否則必填齊全才 ready ─────────────────────
@pytest.mark.req("documind-ocr-mapping:7.6")
def test_needs_review_true_forces_draft_even_when_required_present():
    req = _req("documind_contract_sample.json", needs_review=True)
    r = run_mapping(req)
    assert r.status == "draft" and r.provenance.needs_review is True


@pytest.mark.req("documind-ocr-mapping:7.6")
def test_ready_only_when_not_needs_review_and_required_present():
    req = _req("documind_contract_sample.json", needs_review=False)
    r = run_mapping(req)
    missing = [n for n in REQUIRED_FOR_WRITE if r.fields[n].source is FieldSource.absent]
    assert r.status == ("ready" if not missing else "draft")
    # fixture 合約四個必填皆可解析 ⇒ 應為 ready
    assert missing == [] and r.status == "ready"


@pytest.mark.req("documind-ocr-mapping:7.6")
def test_not_needs_review_but_missing_required_stays_draft():
    req = _req("documind_contract_sample.json", needs_review=False)
    for p in req.pages:
        p.structured_data.get("financial_terms", {}).pop("contract_amount", None)
    r = run_mapping(req)
    assert r.fields["rent"].source is FieldSource.absent and r.status == "draft" and "rent" in r.needs_confirmation
