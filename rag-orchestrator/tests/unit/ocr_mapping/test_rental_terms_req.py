"""unit 層：DocuMind `rental_terms` 群組的映射與來源優先序（design.md 元件 6 v1.3／需求 4.6、5.1）。

背景（2026-09-03，D1 定案 A）：DocuMind `contract_field_extractor.py` 在原文含租賃標記時會多掛 `rental_terms`
（`date_start／date_end／monthly_rent／payment_day／tenant_name／deposit…`）；值是**擷取群**不是整句——
「13,800」沒有「元」、民國日期被空白串成「114 1 21」、繳費日只剩「5」。這些形狀 ⛔ 不得靠猜，逐一有決定性規則。
"""
import pytest

from services.ocr_mapping.contract_mapper import (
    CONTRACT_RENTAL_MAP, CONTRACT_SOURCE_FIELDS, CONTRACT_SOURCE_MAP, map_contract,
)
from services.ocr_mapping.field_normalizer import normalize_date
from services.ocr_mapping.mapper import run_mapping
from services.ocr_mapping.models import DocuMindPage, FieldSource, OcrMappingRequest
from services.ocr_mapping.page_merger import merge_pages

pytestmark = pytest.mark.unit
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c", "target_user": "landlord",
            "session_id": "backtest_session_ocr_rental"}


def _pg(n: int, sd: dict, text: str = "", conf: float = 0.6) -> DocuMindPage:
    return DocuMindPage(page_number=n, ocr_raw={"text": text, "confidence": conf}, structured_data=sd)


def _run(pages):
    merged = merge_pages(pages, CONTRACT_SOURCE_FIELDS, {}, None)
    return map_contract(merged, pages)


# ── 映射表本身 ────────────────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_map_covers_five_fields_and_source_fields_is_union():
    assert set(CONTRACT_RENTAL_MAP) == {"date_start", "date_end", "rent", "cycle_date", "party_b"}
    assert all(v.startswith("rental_terms.") for v in CONTRACT_RENTAL_MAP.values())
    assert set(CONTRACT_SOURCE_FIELDS) == set(CONTRACT_SOURCE_MAP.values()) | set(CONTRACT_RENTAL_MAP.values())
    assert "rental_terms.deposit" not in CONTRACT_SOURCE_FIELDS      # ⛔ 金額／月數混收同鍵，不消費（見 R4.6）


# ── 日期：租約專用優先、通用備援、同日不同寫法不算衝突 ─────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_date_start_wins_and_generic_goes_to_conflicts():
    r = _run([_pg(1, {"contract_metadata": {"effective_date": "2025/1/15"},
                      "rental_terms": {"date_start": "2025年1月21日"}})])
    ds = r.fields["date_start"]
    assert ds.value == "2025-01-21" and ds.jgb_value == 20250121
    assert ds.raw == "2025年1月21日" and ds.source is FieldSource.ocr        # 值、raw、source 三者都來自租約來源（突變控制：反轉優先序必紅）
    assert [c.value for c in ds.conflicts] == ["2025-01-15"]
    assert "date_start" in r.needs_confirmation


@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_and_generic_same_date_different_notation_is_not_a_conflict():
    r = _run([_pg(1, {"contract_metadata": {"effective_date": "中華民國114年1月21日"},
                      "rental_terms": {"date_start": "2025年1月21日"}})])
    ds = r.fields["date_start"]
    assert ds.value == "2025-01-21" and ds.conflicts == []
    assert ds.raw == "2025年1月21日" and ds.source is FieldSource.ocr        # 同值仍取租約來源的 raw（西元 ⇒ ocr），⛔ 不是通用的民國 raw
    assert "date_start" not in r.needs_confirmation


@pytest.mark.req("documind-ocr-mapping:4.6")
def test_unparseable_rental_value_falls_back_to_generic_without_conflict():
    r = _run([_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"},
                      "rental_terms": {"date_start": "無法辨識"}})])
    assert r.fields["date_start"].value == "2025-01-21" and r.fields["date_start"].conflicts == []


@pytest.mark.req("documind-ocr-mapping:5.1")
@pytest.mark.parametrize("raw,iso", [("114 1 21", "2025-01-21"), ("115 12 31", "2026-12-31")])
def test_documind_space_joined_roc_groups_normalize(raw, iso):
    """DocuMind 多捕獲組用空白串接（`contract_field_extractor.py` 符號 `match.groups()`）⇒ 「114 1 21」。"""
    nd = normalize_date(raw)
    assert nd is not None and nd.iso == iso and nd.calendar == "roc"


@pytest.mark.req("documind-ocr-mapping:5.1")
def test_space_joined_roc_in_rental_terms_is_derived():
    r = _run([_pg(1, {"rental_terms": {"date_start": "114 1 21"}})])
    assert r.fields["date_start"].value == "2025-01-21" and r.fields["date_start"].source is FieldSource.derived


# ── 月租金：擷取群沒有「元」也要決定性收下 ───────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
@pytest.mark.parametrize("raw,rent", [("13,800", 13800), ("13800", 13800), ("壹萬參仟捌佰", 13800)])
def test_rental_monthly_rent_bare_number_is_accepted(raw, rent):
    r = _run([_pg(1, {"rental_terms": {"monthly_rent": raw}})])
    assert r.fields["rent"].value == rent and r.fields["rent"].source is FieldSource.derived and r.fields["rent"].raw == raw


@pytest.mark.req("documind-ocr-mapping:4.6")
def test_generic_contract_amount_still_requires_unit():
    """通用 `contract_amount` 是整句擷取，維持需求 5.5：沒有「元」／幣別 ⇒ absent（⛔ 不因租約來源放寬）。"""
    r = _run([_pg(1, {"financial_terms": {"contract_amount": "13800"}})])
    assert r.fields["rent"].source is FieldSource.absent


@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_rent_conflicts_with_generic_amount_when_different():
    r = _run([_pg(1, {"financial_terms": {"contract_amount": "每月租金新台幣壹萬參仟捌佰元整"},
                      "rental_terms": {"monthly_rent": "15,000"}})])
    assert r.fields["rent"].value == 15000 and r.fields["rent"].raw == "15,000"
    assert [c.value for c in r.fields["rent"].conflicts] == [13800]
    assert "rent" in r.needs_confirmation


# ── 繳費日：「5」→5；「月初／月底」不猜 ───────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
@pytest.mark.parametrize("raw,day", [("5", 5), ("25", 25), ("每月5日", 5)])
def test_rental_payment_day_numeric(raw, day):
    r = _run([_pg(1, {"rental_terms": {"payment_day": raw}})])
    assert r.fields["cycle_date"].value == day and r.fields["cycle_date"].source is FieldSource.derived


@pytest.mark.req("documind-ocr-mapping:4.6")
@pytest.mark.parametrize("raw", ["月初", "月底", "0", "32"])
def test_rental_payment_day_vague_or_out_of_range_falls_back_then_absent(raw):
    r = _run([_pg(1, {"rental_terms": {"payment_day": raw}})])
    assert r.fields["cycle_date"].source is FieldSource.absent and "cycle_date" in r.needs_confirmation
    r2 = _run([_pg(1, {"financial_terms": {"payment_deadline": "每月五日前"}, "rental_terms": {"payment_day": raw}})])
    assert r2.fields["cycle_date"].value == 5                        # 租約值不可用 ⇒ 通用備援


# ── 承租人：tenant_name 優先於 party_b ─────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_tenant_name_wins_over_party_b_and_flags_when_different():
    r = _run([_pg(1, {"parties": {"party_b": "王大明"}, "rental_terms": {"tenant_name": "歐陽小美"}})])
    assert r.fields["party_b_full_name"].value == "歐陽小美"
    assert r.fields["to_user_last_name"].value == "歐陽" and r.fields["to_user_first_name"].value == "小美"
    assert [c.value for c in r.fields["party_b_full_name"].conflicts] == ["王大明"]
    assert "party_b_full_name" in r.needs_confirmation


# ── 到期日：rental_terms.date_end > 明文「至…止」> 月數推算 ───────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_date_end_beats_text_and_derivation_and_agreement_is_silent():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"},
                     "rental_terms": {"date_end": "2026年1月20日"}},
                 "租期壹年 自2025/1/21起至2026/1/20止")]
    r = _run(pages)
    de = r.fields["date_end"]
    assert de.value == "2026-01-20" and de.conflicts == [] and de.raw == "2026年1月20日"
    assert "date_end" not in r.needs_confirmation


@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_date_end_disagreeing_with_text_is_flagged_with_both_others():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"},
                     "rental_terms": {"date_end": "2026年6月30日"}},
                 "租期壹年 自2025/1/21起至2026/1/20止")]
    r = _run(pages)
    de = r.fields["date_end"]
    assert de.value == "2026-06-30" and de.raw == "2026年6月30日" and "date_end" in r.needs_confirmation
    assert {c.value for c in de.conflicts} == {"2026-01-20"}          # 明文與推算同值 ⇒ 去重成一筆


# ── 押金：⛔ 刻意不消費 rental_terms.deposit ──────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_rental_deposit_is_ignored_fail_closed():
    """DocuMind 把「押金：27,600元」與「押金：相當於2個月租金」都填進同一個 `deposit` 鍵（各回「27,600」／「2」），
    收到「2」無法區分月數與金額 ⇒ 二選一鐵則下寧可 absent，等 DocuMind 拆鍵。"""
    r = _run([_pg(1, {"rental_terms": {"deposit": "2"}})])
    assert all(r.fields[n].source is FieldSource.absent for n in ("deposit_type", "deposit", "deposit_amount"))


# ── 端到端：mapper 真的把 rental_terms 合併進來 ───────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.6")
def test_run_mapping_consumes_rental_terms_end_to_end():
    req = OcrMappingRequest(document_type="contract", total_pages=1, needs_review=True,
                            pages=[_pg(1, {"rental_terms": {"date_start": "114 1 21", "date_end": "115 1 20",
                                                             "monthly_rent": "13,800", "payment_day": "5",
                                                             "tenant_name": "歐陽小美"}})], **IDENTITY)
    r = run_mapping(req)
    got = {k: r.fields[k].value for k in ("date_start", "date_end", "rent", "cycle_date", "party_b_full_name")}
    assert got == {"date_start": "2025-01-21", "date_end": "2026-01-20", "rent": 13800, "cycle_date": 5,
                   "party_b_full_name": "歐陽小美"}
    assert r.status == "draft"                                        # needs_review=True 恆 draft
