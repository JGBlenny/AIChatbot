"""TDD：`/bills` 與 `/bills/{bill_id}` 的 mock HTTP semantics（任務 4.5，R4.1／R4.2）。

⚠️ **本層是 fidelity layer，不是「讓下一層 adapter 比較好寫」**：
真 API 沒有 `bill_ref`、沒有 derived helper 欄位、沒有把 404 拆開，mock 一律不得補。

過濾結果刻意沿用 4.4 的差異矩陣，不另造測資：

    contract 700100 → {900001, 900002}
    bit_status 3    → {900001, 900003}
    invoice 1       → {900002, 900003}
    2026-08         → {900001}
    2026-09         → {900002, 900003}
"""
import asyncio

import pytest

from services.jgb.fixtures import EXTERNAL_BILL_FIELDS, BillFixtureTable
from services.jgb.transport import JGBMockTransport

pytestmark = pytest.mark.unit

BILLS = "/api/external/v1/bills"
ROLE = {"role_id": "R001"}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def mt():
    return JGBMockTransport(BillFixtureTable())


def _ids(resp):
    return {r["id"] for r in resp["data"]}


# ── /bills：必填與過濾 ────────────────────────────────────────────────────
def test_missing_role_id_is_400(mt):
    resp = _run(mt.send("GET", BILLS, params={}))
    assert resp["success"] is False
    assert resp["error"] == {"code": 400, "message": "role_id 為必填參數"}


def test_contract_filter_uses_fixture_matrix(mt):
    # 跨域連貫修正後帳單指向既有 contract fixture 的真實 id（678，非孤立合成值）。
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "contract_id": 678}))
    assert _ids(resp) == {900001, 900002}


def test_status_and_type_filters_are_computed(mt):
    assert _ids(_run(mt.send("GET", BILLS, params={**ROLE, "status": 8}))) == {900003}
    assert _ids(_run(mt.send("GET", BILLS, params={**ROLE, "type": 1}))) == {900001}


def test_bill_id_filter_converges_to_single_row(mt):
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "bill_id": 900002}))
    assert _ids(resp) == {900002}


# ── month：真的算區間，不是查表 ───────────────────────────────────────────
def test_month_filter_is_derived_not_hardcoded(mt):
    aug = _run(mt.send("GET", BILLS, params={**ROLE, "month": "2026-08"}))
    sep = _run(mt.send("GET", BILLS, params={**ROLE, "month": "2026-09"}))
    assert _ids(aug) == {900001}
    assert _ids(sep) == {900002, 900003}


def test_month_with_no_data_returns_empty_not_error(mt):
    """區間確實被計算：查一個沒有資料的月份要得到空集合，而不是報錯或忽略。"""
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "month": "2026-07"}))
    assert _ids(resp) == set()
    assert resp["pagination"]["total"] == 0


@pytest.mark.parametrize("bad", ["2026-8", "202608", "2026/08", "abc", "2026-08-15"])
def test_invalid_month_is_silently_ignored(mt, bad):
    """⚠️ production 只在 `preg_match` 命中時才加條件（BillApiController:78-85）——
    非法格式**不報錯、不過濾**。mock 照抄此行為，不得「改成比較合理的」400。"""
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "month": bad}))
    assert _ids(resp) == {900001, 900002, 900003}
    assert resp["success"] is True


def test_month_range_is_inclusive_to_day_31_like_production(mt):
    """⚠️ production 用 `YYYYMM01 ~ YYYYMM31` inclusive（:81-83），**不是**「次月初」開區間。

    2 月同樣用 31——這是 production 的實際怪癖，mock 保真而非「修正」它。
    """
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "month": "2026-02"}))
    assert _ids(resp) == set()          # fixture 無 2 月資料，但區間本身仍以 31 計


# ── 排序：白名單要真的被消費 ──────────────────────────────────────────────
@pytest.mark.parametrize("field", ["date_expire", "created_at", "total", "updated_at"])
def test_allowed_sort_fields_are_accepted(mt, field):
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "sort_by": field, "sort_direction": "asc"}))
    values = [r[field] for r in resp["data"]]
    assert values == sorted(values)


def test_unsupported_sort_field_falls_back_like_production(mt):
    """⚠️ production 對非白名單 `sort_by` **回退 `created_at`**（:88-96），不是報錯。

    這一條同時殺掉 `getattr(record, user_supplied_field)` 這種寫法——
    白名單存在但 consumer 不吃它，就等於沒有白名單。
    """
    fallback = _run(mt.send("GET", BILLS, params={**ROLE, "sort_by": "created_at"}))
    bogus = _run(mt.send("GET", BILLS, params={**ROLE, "sort_by": "total_amount_evil"}))
    assert [r["id"] for r in bogus["data"]] == [r["id"] for r in fallback["data"]]


def test_invalid_sort_direction_falls_back_to_desc(mt):
    desc = _run(mt.send("GET", BILLS, params={**ROLE, "sort_direction": "desc"}))
    bogus = _run(mt.send("GET", BILLS, params={**ROLE, "sort_direction": "sideways"}))
    assert [r["id"] for r in bogus["data"]] == [r["id"] for r in desc["data"]]


# ── 分頁 ─────────────────────────────────────────────────────────────────
def test_per_page_is_capped_at_200(mt):
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "per_page": 5000}))
    assert resp["pagination"]["per_page"] == 200


def test_pagination_shape_and_has_more(mt):
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "per_page": 2, "page": 1}))
    assert len(resp["data"]) == 2
    p = resp["pagination"]
    assert p == {"current_page": 1, "per_page": 2, "total": 3,
                 "total_pages": 2, "has_more": True}


def test_default_per_page_is_50(mt):
    resp = _run(mt.send("GET", BILLS, params=ROLE))
    assert resp["pagination"]["per_page"] == 50


# ── detail ───────────────────────────────────────────────────────────────
def test_detail_returns_projected_bill_without_pagination(mt):
    resp = _run(mt.send("GET", f"{BILLS}/900001", params=ROLE))
    assert resp["success"] is True
    assert resp["data"]["id"] == 900001
    assert "pagination" not in resp, "detail 不得被補上 pagination（假對稱）"


def test_detail_unknown_id_is_ambiguous_404(mt):
    """⚠️ **資訊折疊照抄**：production 對「不存在」與「無權存取」回同一句（:230）。

    mock 不得拆成 404-not-found ／ 403-no-access——
    否則上層會取得 production 根本沒有的辨識能力（同 N1 的 E5：404 仍是 ambiguous fact）。
    """
    resp = _run(mt.send("GET", f"{BILLS}/123456789", params=ROLE))
    assert resp["success"] is False
    assert resp["error"] == {"code": 404, "message": "帳單不存在或無權存取"}


def test_detail_missing_role_id_is_400(mt):
    resp = _run(mt.send("GET", f"{BILLS}/900001", params={}))
    assert resp["error"]["code"] == 400


# ── 契約保真：不得長出 rag-side 便利欄位 ─────────────────────────────────
def test_no_bill_ref_in_list_items(mt):
    """`bill_ref` 是 rag 端 adapter 參數，真 API 不存在。

    危險寫法是組 response 時 `{**fixture, "bill_ref": requested}`——
    那會繞過 fixture 本體的 projection guard，故在 response 層再驗一次。
    """
    resp = _run(mt.send("GET", BILLS, params={**ROLE, "bill_ref": "900001"}))
    for row in resp["data"]:
        assert "bill_ref" not in row


def test_no_bill_ref_in_detail_item(mt):
    resp = _run(mt.send("GET", f"{BILLS}/900001", params={**ROLE, "bill_ref": "900001"}))
    assert "bill_ref" not in resp["data"]


def test_every_returned_row_stays_within_projection(mt):
    for row in _run(mt.send("GET", BILLS, params=ROLE))["data"]:
        assert set(row) <= EXTERNAL_BILL_FIELDS
    assert set(_run(mt.send("GET", f"{BILLS}/900003", params=ROLE))["data"]) <= EXTERNAL_BILL_FIELDS


def test_mapping_matches_production_labels(mt):
    resp = _run(mt.send("GET", BILLS, params=ROLE))
    assert resp["mapping"]["status"][8] == "待對帳"
    assert resp["mapping"]["invoice_status"][2] == "發票異常"
    assert resp["mapping"]["type"][2] == "點退"
