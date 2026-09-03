"""unit 層：documind-ocr-mapping 契約模型（純 Pydantic，無服務、無 I/O）。

比照 tests/unit/api/test_api_request_contract_req.py：直接建構模型驗契約，不用 TestClient。
對應 design.md 元件 2（models.py）。
"""
import pytest
from pydantic import ValidationError

from services.ocr_mapping.models import (
    CONTRACT_FIELDS,
    REQUIRED_FOR_WRITE,
    TRANSCRIPT_FIELDS,
    DocumentType,
    DocuMindPage,
    FieldSource,
    FieldValue,
    MappingResult,
    OcrMappingRequest,
    Provenance,
    empty_fields,
)

pytestmark = pytest.mark.unit


def _page(n: int = 1, **sd) -> dict:
    return {
        "page_number": n,
        "ocr_raw": {"text": "第一條 租金每月新台幣壹萬參仟捌佰元整", "confidence": 0.69},
        "rule_postprocessed": {"text": "…", "stats": {}},
        "llm_postprocessed": None,          # DocuMind：LLM 未觸發時為 null，不是空物件
        "structured_data": sd,
        "field_confidences": {},
        "consensus": None,
    }


def _identity() -> dict:
    return {"vendor_id": 1, "role_id": "20151", "user_id": "12291",
            "mode": "b2c", "target_user": "landlord", "session_id": "backtest_session_ocr_t"}


# ── R1.1：接受 DocuMind 回應全文＋身分 ────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:1.1")
def test_request_accepts_full_documind_payload_with_identity():
    req = OcrMappingRequest(
        document_type="contract", total_pages=1, needs_review=True,
        review_item_id="98563520-43ad-43cb-a4ac-d04eb901f436",
        stats={"total_time_ms": 150861, "total_pages": 1, "llm_pages_used": 0, "estimated_cost": 0.11},
        pages=[_page(1, contract_metadata={"signing_date": "1140115"})],
        **_identity(),
    )
    assert req.document_type is DocumentType.contract
    assert req.pages[0].llm_postprocessed is None
    assert req.field_confidences == {} and req.consensus is None   # 頂層兩鍵可缺


@pytest.mark.req("documind-ocr-mapping:1.1")
def test_request_rejects_missing_pages_and_identity():
    with pytest.raises(ValidationError):
        OcrMappingRequest(document_type="contract", total_pages=0, needs_review=True, **_identity())  # 無 pages
    with pytest.raises(ValidationError):
        OcrMappingRequest(document_type="contract", total_pages=0, needs_review=True, pages=[])      # 無身分


@pytest.mark.req("documind-ocr-mapping:1.1")
def test_request_allows_empty_pages_for_draft_path():
    # R1.4：空 pages 是合法輸入（端點須回 200 draft，不是 422）
    req = OcrMappingRequest(document_type="transcript", total_pages=0, needs_review=True, pages=[], **_identity())
    assert req.pages == []


# ── R9.1：source 值域封閉；FieldValue 形狀 ──────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.1")
def test_field_source_domain_is_closed():
    assert {s.value for s in FieldSource} == {"ocr", "derived", "llm_extracted", "absent"}
    with pytest.raises(ValidationError):
        FieldValue(value="x", source="guess")


@pytest.mark.req("documind-ocr-mapping:7.4")
def test_absent_field_has_null_confidence_and_no_value():
    fv = FieldValue()
    assert fv.source is FieldSource.absent
    assert fv.value is None and fv.jgb_value is None and fv.confidence is None
    assert fv.conflicts == []


@pytest.mark.req("documind-ocr-mapping:3.5")
def test_confidence_source_is_field_or_page_level_only():
    FieldValue(value="全部", source="ocr", confidence=0.9, confidence_source="page_level")
    with pytest.raises(ValidationError):
        FieldValue(value="全部", source="ocr", confidence=0.9, confidence_source="guessed")


# ── R4.3 / R9.1：同型 fields 鍵集合恆定 ────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.3")
def test_empty_fields_yields_fixed_key_set_per_type():
    assert set(empty_fields(DocumentType.contract)) == set(CONTRACT_FIELDS)
    assert set(empty_fields(DocumentType.transcript)) == set(TRANSCRIPT_FIELDS)
    assert all(v.source is FieldSource.absent for v in empty_fields(DocumentType.contract).values())


@pytest.mark.req("documind-ocr-mapping:9.1")
def test_mapping_result_rejects_wrong_key_set():
    prov = Provenance(document_type="contract", total_pages=1, needs_review=True,
                      review_item_id=None, documind_estimated_cost=None, mapping_version="1.0.0")
    bad = empty_fields(DocumentType.contract)
    bad.pop("rent")
    with pytest.raises(ValidationError):
        MappingResult(status="draft", document_type="contract", fields=bad,
                      needs_confirmation=[], unmapped_clauses=[], provenance=prov)
    ok = MappingResult(status="draft", document_type="contract", fields=empty_fields(DocumentType.contract),
                       needs_confirmation=[], unmapped_clauses=[], provenance=prov)
    assert set(ok.fields) == set(CONTRACT_FIELDS)


@pytest.mark.req("documind-ocr-mapping:4.3")
def test_required_for_write_is_subset_of_contract_fields():
    assert set(REQUIRED_FOR_WRITE) <= set(CONTRACT_FIELDS)
    assert set(REQUIRED_FOR_WRITE) == {"date_start", "date_end", "cycle_date", "rent"}


# ── R9.2：Provenance 必含鍵 ─────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.2")
def test_provenance_requires_core_keys_and_notes_default_empty():
    p = Provenance(document_type="transcript", total_pages=4, needs_review=True,
                   review_item_id="r1", documind_estimated_cost=0.1112, mapping_version="1.0.0")
    assert p.notes == []
    with pytest.raises(ValidationError):
        Provenance(document_type="transcript", total_pages=4)   # 缺 needs_review／mapping_version


# ── DocuMindPage：頁模型容忍 DocuMind 的 null 與空物件 ─────────────────────
@pytest.mark.req("documind-ocr-mapping:2.4")
def test_page_accepts_null_llm_postprocessed_and_empty_structured_data():
    p = DocuMindPage(**_page(3))
    assert p.page_number == 3 and p.structured_data == {} and p.llm_postprocessed is None
    assert 0.0 <= p.ocr_raw.confidence <= 1.0
