"""unit 層：謄本映射（design.md 元件 5）。需求 3.1–3.5。"""
import json
from pathlib import Path

import pytest

from services.ocr_mapping.models import TRANSCRIPT_FIELDS, DocuMindPage, FieldSource, OcrMappingRequest
from services.ocr_mapping.page_merger import merge_pages
from services.ocr_mapping.transcript_mapper import map_transcript

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures" / "documind_transcript_sample.json"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "mode": "b2c"}


def _fixture_pages() -> list[DocuMindPage]:
    data = json.loads(FIX.read_text(encoding="utf-8"))
    req = OcrMappingRequest(**{k: v for k, v in data.items() if not k.startswith("_")}, **IDENTITY)
    return req.pages


def _pg(n: int, **sd) -> DocuMindPage:
    return DocuMindPage(page_number=n, ocr_raw={"text": "…", "confidence": 0.6}, structured_data=sd)


def _run(pages):
    merged = merge_pages(pages, TRANSCRIPT_FIELDS, {}, None)
    return map_transcript(merged, pages)


# ── R3.1 五欄原名、鍵集合恆定、⛔ 不對應到 JGB estates ─────────────────────────
@pytest.mark.req("documind-ocr-mapping:3.1")
def test_fixture_maps_five_fields_with_original_keys():
    fields, notes = _run(_fixture_pages())
    assert set(fields) == set(TRANSCRIPT_FIELDS)
    assert fields["land_number"].value == "竹田鄉測試段0555-0000地號" and fields["land_number"].source is FieldSource.ocr
    assert fields["building_number"].value == "測試段01234-000建號" and fields["building_number"].page == 2
    assert "可能為土地謄本" not in " ".join(notes)          # 第 2 頁有建號 ⇒ 不是土地謄本


# ── R3.2 面積：千分位／單位 → 數值，raw 保留，source=derived ─────────────────
@pytest.mark.req("documind-ocr-mapping:3.2")
def test_area_is_numeric_derived_with_raw():
    fields, _ = _run(_fixture_pages())
    a = fields["area"]
    assert a.value == pytest.approx(3406.98) and a.jgb_value == pytest.approx(3406.98)
    assert a.source is FieldSource.derived and a.raw == "3,406.98" and a.page == 1


@pytest.mark.req("documind-ocr-mapping:3.2")
def test_area_unparseable_is_absent_but_raw_kept():
    fields, _ = _run([_pg(1, area="全部")])
    assert fields["area"].source is FieldSource.absent and fields["area"].value is None and fields["area"].raw == "全部"


# ── R3.3 建號空＋地號有 → 註記，⛔ 不把地號填進建號 ────────────────────────────
@pytest.mark.req("documind-ocr-mapping:3.3")
def test_missing_building_number_with_land_number_adds_note_and_does_not_copy():
    fields, notes = _run([_pg(1, land_number="測試段0555-0000地號", building_number=None)])
    assert fields["building_number"].source is FieldSource.absent and fields["building_number"].value is None
    assert any("可能為土地謄本" in n for n in notes)


# ── R3.4 多所有權人 → 陣列，raw 保留原字串 ───────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:3.4")
@pytest.mark.parametrize("raw,expected", [
    ("王大明、李小華", ["王大明", "李小華"]),
    ("王大明及李小華", ["王大明", "李小華"]),
    ("王大明,李小華,陳阿花", ["王大明", "李小華", "陳阿花"]),
])
def test_multiple_owners_become_list_with_raw(raw, expected):
    fields, _ = _run([_pg(1, owner=raw)])
    assert fields["owner"].value == expected and fields["owner"].raw == raw


@pytest.mark.req("documind-ocr-mapping:3.4")
def test_single_owner_stays_scalar():
    fields, _ = _run([_pg(1, owner="王大明")])
    assert fields["owner"].value == "王大明" and fields["owner"].jgb_value == "王大明"


# ── R3.5 信心度：缺欄位信心度以 extraction_confidence 補位並標 page_level ────────
@pytest.mark.req("documind-ocr-mapping:3.5")
def test_confidence_fallback_to_page_level_is_carried():
    fields, _ = _run([_pg(1, rights_scope="全部", extraction_confidence=0.7)])
    r = fields["rights_scope"]
    assert r.confidence == 0.7 and r.confidence_source == "page_level"


# ── 跨頁衝突透傳到 FieldValue.conflicts（供編排層列 needs_confirmation）──────────
@pytest.mark.req("documind-ocr-mapping:2.3")
def test_conflicts_from_merge_are_carried_on_field_value():
    fields, _ = _run(_fixture_pages())
    assert fields["owner"].value == "王大明" and len(fields["owner"].conflicts) == 1   # 第 3 頁「王大明、李小華」信心較低
