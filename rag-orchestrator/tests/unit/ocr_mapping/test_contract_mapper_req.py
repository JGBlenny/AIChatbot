"""unit 層：合約映射（design.md 元件 6／contract_mapper）。需求 4.1–4.5、5.3。"""
import json
from pathlib import Path

import pytest

from services.ocr_mapping.contract_mapper import CONTRACT_SOURCE_MAP, map_contract
from services.ocr_mapping.models import CONTRACT_FIELDS, REQUIRED_FOR_WRITE, DocuMindPage, FieldSource, OcrMappingRequest
from services.ocr_mapping.name_splitter import NamePolicy
from services.ocr_mapping.page_merger import merge_pages

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures" / "documind_contract_sample.json"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "mode": "b2c"}


def _fixture_pages() -> list[DocuMindPage]:
    data = json.loads(FIX.read_text(encoding="utf-8"))
    return OcrMappingRequest(**{k: v for k, v in data.items() if not k.startswith("_")}, **IDENTITY).pages


def _pg(n: int, sd: dict, text: str = "", conf: float = 0.6) -> DocuMindPage:
    return DocuMindPage(page_number=n, ocr_raw={"text": text, "confidence": conf}, structured_data=sd)


def _run(pages, policy=NamePolicy.split):
    merged = merge_pages(pages, CONTRACT_SOURCE_MAP.values(), {}, None)
    return map_contract(merged, pages, name_policy=policy)


# ── R4.1 依表映射（fixture 端到端）─────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.1")
def test_fixture_maps_core_fields_per_table():
    r = _run(_fixture_pages())
    f = r.fields
    assert set(f) == set(CONTRACT_FIELDS)                                        # R4.3 鍵集合恆定
    assert (f["date_start"].value, f["date_start"].jgb_value, f["date_start"].source) == ("2025-01-21", 20250121, FieldSource.derived)
    assert f["rent"].value == 13800 and f["rent"].jgb_value == 13800 and f["rent"].source is FieldSource.derived
    assert f["currency"].value == "TWD" and f["currency"].source is FieldSource.ocr
    assert f["cycle_date"].value == 5 and f["cycle_date"].source is FieldSource.derived   # 「每月五日前」可決定性解析
    assert (f["to_user_last_name"].value, f["to_user_first_name"].value, f["party_b_full_name"].value) == ("歐陽", "小美", "歐陽小美")
    assert f["deposit_type"].value == 1 and f["deposit_amount"].value == 27600 and f["deposit"].source is FieldSource.absent


@pytest.mark.req("documind-ocr-mapping:4.1")
def test_signing_date_same_date_different_notation_is_not_a_conflict():
    # p1 民國114年1月15日（0.85）與 p3 2025/1/15（0.6）正規化後相同 ⇒ 不算衝突
    r = _run(_fixture_pages())
    sd = r.fields["lease_signing_date"]
    assert sd.value == "2025-01-15" and sd.jgb_value == 20250115 and sd.conflicts == []
    assert "lease_signing_date" not in r.needs_confirmation


# ── R4.2 date_end 由租期推算，source=derived、列 needs_confirmation ─────────────
@pytest.mark.req("documind-ocr-mapping:4.2")
def test_date_end_derived_from_lease_months_and_flagged():
    r = _run(_fixture_pages())
    assert r.fields["lease_months"].value == 12 and r.fields["lease_months"].source is FieldSource.derived
    de = r.fields["date_end"]
    assert (de.value, de.jgb_value, de.source) == ("2026-01-20", 20260120, FieldSource.derived)
    # ⑧(a)（2026-09-03）：fixture 原文明寫「至中華民國115年1月20日止」⇒ 明文優先、不反白；月數推算與明文一致 ⇒ 無衝突
    assert "115年1月20日" in (de.raw or "") and de.conflicts == [] and "date_end" not in r.needs_confirmation


@pytest.mark.req("documind-ocr-mapping:4.2")
def test_lease_months_not_confused_by_prepaid_electricity_months():
    # 「電費預繳1000/月共6個月」不在租期句內 ⇒ ⛔ 不得把 6 個月加進租期
    pages = [_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"}}, "租期壹年 自2025/1/21起"),
             _pg(2, {}, "電費預繳1000/月共6個月")]
    r = _run(pages)
    assert r.fields["lease_months"].value == 12 and r.fields["date_end"].value == "2026-01-20"


# ── R4.3／4.4 每欄都回物件；必填缺漏列 needs_confirmation ─────────────────────
@pytest.mark.req("documind-ocr-mapping:4.4")
def test_empty_contract_lists_all_required_fields_for_confirmation():
    r = _run([_pg(1, {})])
    assert set(r.fields) == set(CONTRACT_FIELDS) and all(v.source is FieldSource.absent for v in r.fields.values())
    assert set(REQUIRED_FOR_WRITE) <= set(r.needs_confirmation)


@pytest.mark.req("documind-ocr-mapping:4.3")
def test_absent_fields_are_still_present_as_objects():
    r = _run(_fixture_pages())
    for name in ("cycle", "early_termination_penalty", "early_termination_penalty2"):
        assert r.fields[name].source is FieldSource.absent and r.fields[name].value is None
    # ⑧(b)：fixture p3「三十日前以書面通知」可決定性解析 ⇒ early_termination_days=30（derived、反白）
    assert r.fields["early_termination_days"].value == 30 and "early_termination_days" in r.needs_confirmation


# ── R4.5 payment_method 原樣進未映射條款，⛔ 不推導收款旗標 ─────────────────────
@pytest.mark.req("documind-ocr-mapping:4.5")
def test_payment_method_goes_to_unmapped_verbatim():
    r = _run(_fixture_pages())
    assert "轉帳至甲方指定帳戶" in r.unmapped_from_fields


# ── R4.1 表的邊界：currency ⛔ 不預設；cycle_date 解析不了 → absent＋待確認；party_a 不映射 ──
@pytest.mark.req("documind-ocr-mapping:4.1")
def test_currency_absent_when_missing_and_cycle_date_flagged_when_vague():
    pages = [_pg(1, {"financial_terms": {"contract_amount": "壹萬元整", "currency": None, "payment_deadline": "月初"},
                     "parties": {"party_a": "張三", "party_a_address": "台北市"}})]
    r = _run(pages)
    assert r.fields["currency"].source is FieldSource.absent
    assert r.fields["cycle_date"].source is FieldSource.absent and "cycle_date" in r.needs_confirmation
    assert "party_a" not in r.fields and "party_a_address" not in r.fields


@pytest.mark.req("documind-ocr-mapping:4.1")
def test_keep_full_policy_leaves_name_parts_absent():
    r = _run(_fixture_pages(), policy=NamePolicy.keep_full)
    assert r.fields["to_user_last_name"].source is FieldSource.absent and r.fields["party_b_full_name"].value == "歐陽小美"
    assert "to_user_last_name" not in r.needs_confirmation


# ── R5.3 民國／西元同文件不一致 → 高信心者為值、其餘 conflicts、列 needs_confirmation ──
@pytest.mark.req("documind-ocr-mapping:5.3")
def test_inconsistent_calendars_pick_high_confidence_and_flag():
    pages = [_pg(1, {"contract_metadata": {"signing_date": "中華民國114年1月15日"}, "field_confidences": {"signing_date": 0.6}}),
             _pg(2, {"contract_metadata": {"signing_date": "2025/1/16"}, "field_confidences": {"signing_date": 0.9}})]
    r = _run(pages)
    sd = r.fields["lease_signing_date"]
    assert sd.value == "2025-01-16" and len(sd.conflicts) == 1 and sd.conflicts[0].value == "中華民國114年1月15日"
    assert "lease_signing_date" in r.needs_confirmation


# ── absorbed_raws 供條款去重 ───────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:7.1")
def test_absorbed_raws_include_mapped_field_raw_text():
    r = _run(_fixture_pages())
    assert "每月租金新台幣壹萬參仟捌佰元整" in r.absorbed_raws
