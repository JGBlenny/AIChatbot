"""unit 層：多頁合併（design.md 元件 3）。需求 2.1–2.6。"""
import pytest

from services.ocr_mapping.models import DocuMindPage
from services.ocr_mapping.page_merger import collect_needs_confirmation, merge_pages

pytestmark = pytest.mark.unit


def page(n: int, sd: dict, fc: dict | None = None, extraction: float | None = None, llm=None) -> DocuMindPage:
    sd = dict(sd)
    if fc is not None:
        sd["field_confidences"] = fc
    if extraction is not None:
        sd["extraction_confidence"] = extraction
    return DocuMindPage(page_number=n, ocr_raw={"text": "…", "confidence": 0.6},
                        llm_postprocessed=llm, structured_data=sd)


# ── R2.1 單頁非空 ─────────────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:2.1")
def test_single_page_value_adopted_with_page_recorded():
    out = merge_pages([page(1, {"owner": None}), page(2, {"owner": "王大明"}, {"owner": 0.9})], ["owner"], {}, None)
    f = out["owner"]
    assert f.value == "王大明" and f.page == 2 and f.confidence == 0.9 and f.conflicts == ()


# ── R2.2 多頁相同 ─────────────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:2.2")
def test_same_value_on_multiple_pages_takes_max_confidence_and_first_page():
    out = merge_pages([page(1, {"owner": "王大明"}, {"owner": 0.7}), page(3, {"owner": "王大明"}, {"owner": 0.9})], ["owner"], {}, None)
    f = out["owner"]
    assert (f.value, f.confidence, f.page, f.conflicts) == ("王大明", 0.9, 1, ())


# ── R2.3 多頁不同 → 最高信心者為值、其餘進 conflicts、⛔ 不靜默取第一頁 ─────────
@pytest.mark.req("documind-ocr-mapping:2.3")
def test_different_values_pick_highest_confidence_and_keep_conflicts():
    out = merge_pages([page(1, {"signing_date": "中華民國114年1月15日"}, {"signing_date": 0.6}),
                       page(3, {"signing_date": "2025/1/15"}, {"signing_date": 0.85})], ["signing_date"], {}, None)
    f = out["signing_date"]
    assert f.value == "2025/1/15" and f.page == 3
    assert [(c.value, c.page, c.confidence) for c in f.conflicts] == [("中華民國114年1月15日", 1, 0.6)]


@pytest.mark.req("documind-ocr-mapping:2.3")
def test_conflict_tie_prefers_first_page_but_still_records_conflict():
    out = merge_pages([page(1, {"x": "a"}, {"x": 0.5}), page(2, {"x": "b"}, {"x": 0.5})], ["x"], {}, None)
    assert out["x"].value == "a" and out["x"].page == 1 and len(out["x"].conflicts) == 1


# ── R2.4 llm_postprocessed=None 的頁照常參與 ─────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:2.4")
def test_page_without_llm_postprocess_still_participates():
    out = merge_pages([page(1, {"area": None}, llm={"used": True}), page(2, {"area": "3,406.98"}, {"area": 0.9}, llm=None)], ["area"], {}, None)
    assert out["area"].value == "3,406.98" and out["area"].page == 2


# ── R2.5 各頁 needs_confirmation 取聯集（去重、順序穩定）────────────────────────
@pytest.mark.req("documind-ocr-mapping:2.5")
def test_needs_confirmation_union_dedup_ordered():
    pages = [page(1, {"needs_confirmation": ["building_number", "area"]}),
             page(2, {"needs_confirmation": ["area", "owner"]}),
             page(3, {})]
    assert collect_needs_confirmation(pages) == ["building_number", "area", "owner"]


# ── R2.6 頂層 consensus 非空 → 優先採用、不再頁級合併（無 conflicts）─────────────
@pytest.mark.req("documind-ocr-mapping:2.6")
def test_top_level_consensus_wins_and_skips_page_merge():
    pages = [page(1, {"owner": "王大明"}, {"owner": 0.9}), page(2, {"owner": "李小華"}, {"owner": 0.95})]
    out = merge_pages(pages, ["owner"], {"owner": 0.8}, {"owner": "王大明"})
    f = out["owner"]
    assert f.value == "王大明" and f.confidence == 0.8 and f.conflicts == () and f.from_consensus is True


@pytest.mark.req("documind-ocr-mapping:2.6")
def test_consensus_missing_field_falls_back_to_page_merge():
    pages = [page(1, {"owner": "王大明"}, {"owner": 0.9})]
    out = merge_pages(pages, ["owner"], {}, {"area": "1"})     # consensus 沒有 owner
    assert out["owner"].value == "王大明" and out["owner"].from_consensus is False


# ── R3.5 缺 field_confidences → 以 extraction_confidence 補位並標 page_level ────
@pytest.mark.req("documind-ocr-mapping:3.5")
def test_missing_field_confidence_falls_back_to_page_extraction_confidence():
    out = merge_pages([page(1, {"rights_scope": "全部"}, fc={}, extraction=0.7)], ["rights_scope"], {}, None)
    assert out["rights_scope"].confidence == 0.7 and out["rights_scope"].confidence_source == "page_level"


# ── 巢狀路徑（contract 型 structured_data 是三組物件）────────────────────────
@pytest.mark.req("documind-ocr-mapping:2.1")
def test_dotted_path_reads_nested_structured_data_and_leaf_confidence():
    sd = {"contract_metadata": {"effective_date": "中華民國114年1月21日"}, "field_confidences": {"effective_date": 0.9}}
    out = merge_pages([page(1, sd)], ["contract_metadata.effective_date"], {}, None)
    f = out["contract_metadata.effective_date"]
    assert f.value == "中華民國114年1月21日" and f.confidence == 0.9


@pytest.mark.req("documind-ocr-mapping:2.1")
def test_all_pages_empty_yields_absent_merged_field():
    out = merge_pages([page(1, {}), page(2, {"owner": ""})], ["owner"], {}, None)
    assert out["owner"].value is None and out["owner"].page is None and out["owner"].confidence is None
