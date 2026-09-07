"""TDD：`BillFixtureTable`（spec conversational-routing-execution 任務 4.4，R4.1／R4.2）。

本組驗三件事，全部機器判定、不靠 code review 肉眼確認：

1. **契約保真**：每筆的鍵 ⊆ External 白名單投影（`formatBill` 逐鍵）；
2. **identity 穩定**：取用一律經 `by_id()`，不得靠 list position；
3. **差異足以咬到過濾**：任何單一過濾條件都不能複製另一條件的結果集。

⚠️ 另含 negative control：證明白名單 guard **真的會咬**，
否則就是「whitelist exists ≠ whitelist can bite」。
"""
import pytest

from services.jgb.fixtures import (
    EXTERNAL_BILL_FIELDS,
    BillFixtureTable,
    ForeignFixtureFieldError,
    assert_external_projection,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def table():
    return BillFixtureTable()


# ── 1. 契約保真 ───────────────────────────────────────────────────────────
def test_every_row_is_within_external_projection(table):
    for row in table.rows():
        assert set(row) <= EXTERNAL_BILL_FIELDS, f"bill {row['id']} 含非白名單欄位"


def test_projection_guard_bites_on_foreign_field():
    """negative control：刻意放一個真 API 不存在的欄位，guard 必須拒絕。"""
    with pytest.raises(ForeignFixtureFieldError) as ei:
        assert_external_projection({"id": 1, "bill_ref": "900001"})
    assert "bill_ref" in str(ei.value)


def test_archive_at_is_not_in_projection():
    """真 API 輸出的是衍生的 `is_archived`，**不是** `archive_at`（BillApiController:163）。"""
    assert "archive_at" not in EXTERNAL_BILL_FIELDS
    assert "is_archived" in EXTERNAL_BILL_FIELDS


def test_all_rows_share_the_same_key_set(table):
    """各筆鍵集一致——避免「某筆剛好沒有該欄」讓過濾測試看起來通過。"""
    key_sets = {frozenset(row) for row in table.rows()}
    assert len(key_sets) == 1


# ── 2. identity 穩定 ──────────────────────────────────────────────────────
def test_lookup_is_by_id_not_position(table):
    # 跨域連貫修正（transport-agent-mcp-orchestration 收案修正 4）：帳單改指向
    # 既有 contract fixture 的真實 id（678／600），不再是孤立的合成 id。
    assert table.by_id(900001)["contract_id"] == 678
    assert table.by_id(900003)["contract_id"] == 600


def test_unknown_id_returns_none(table):
    assert table.by_id(123456789) is None


def test_ids_are_unique(table):
    ids = [row["id"] for row in table.rows()]
    assert len(ids) == len(set(ids))


def test_rows_returns_a_copy(table):
    """`rows()` 回傳副本——測試改動不得污染後續測試。

    ⚠️ 不再斷言固定筆數（真資料子集併入後 `rows()` 不止 3 筆）；
    改驗「對回傳值的變動不影響內部狀態」這個原本要驗的性質本身。
    """
    before_ids = {r["id"] for r in table.rows()}
    rows = table.rows()
    rows.append({"id": -1})
    after_ids = {r["id"] for r in table.rows()}
    assert after_ids == before_ids
    assert -1 not in after_ids


# ── 3. 差異足以咬到過濾 ───────────────────────────────────────────────────
def test_minimum_shape_requirements(table):
    """frozen constraints：≥3 筆、≥2 個 contract_id、bit_status 與 invoice_status 皆有差異。"""
    rows = table.rows()
    assert len(rows) >= 3
    assert len({r["contract_id"] for r in rows}) >= 2
    assert len({r["bit_status"] for r in rows}) >= 2
    assert len({r["invoice_status"] for r in rows}) >= 2


def _ids(rows, **eq):
    return {r["id"] for r in rows if all(r[k] == v for k, v in eq.items())}


def test_no_single_filter_reproduces_another_filters_result(table):
    """核心：任兩個不同維度的過濾**不得**得到相同集合。

    若三筆只是 id 不同，任何 filter 寫錯都會剛好得到相同集合——那種 fixture 驗不出東西。
    """
    rows = table.rows()
    by_contract = _ids(rows, contract_id=678)
    by_bit = _ids(rows, bit_status=3)
    by_invoice = _ids(rows, invoice_status=1)

    assert by_contract == {900001, 900002}
    assert by_bit == {900001, 900003}
    assert by_invoice == {900002, 900003}
    assert by_contract != by_bit != by_invoice != by_contract


def test_each_pair_shares_exactly_one_dimension(table):
    """每一對只共用一個維度——這是上一條之所以成立的結構原因。"""
    rows = {r["id"]: r for r in table.rows()}
    dims = ("contract_id", "bit_status", "invoice_status")

    for a, b in ((900001, 900002), (900001, 900003), (900002, 900003)):
        shared = [d for d in dims if rows[a][d] == rows[b][d]]
        assert len(shared) == 1, f"{a} 與 {b} 共用 {shared}，應恰為 1 個維度"


def test_month_filter_is_observable(table):
    """`month` 過濾（YYYYMM 比對 `date_expire` 區間）亦須能分辨。

    ⚠️ 真資料子集併入後 8 月／9 月區間可能各再多出其他真實列，
    不再斷言精確集合——只驗核心合成三筆仍落在原設計的月份、
    且兩個月份彼此不重疊（分辨力仍在）。
    """
    rows = table.rows()
    aug = {r["id"] for r in rows if 20260801 <= r["date_expire"] <= 20260831}
    sep = {r["id"] for r in rows if 20260901 <= r["date_expire"] <= 20260931}
    assert {900001} <= aug
    assert {900002, 900003} <= sep
    assert not (aug & sep)
    assert 900002 not in aug and 900003 not in aug
    assert 900001 not in sep


# ── 合成資料 ─────────────────────────────────────────────────────────────
def test_ids_are_synthetic_ranges(table):
    """帳單自身 id 落在明顯非 production 的區段，避免與真資料混淆。

    ⚠️ `contract_id`／`estate_id` **不再**斷言落在 700000／800000 以上——
    跨域連貫修正（transport-agent-mcp-orchestration 收案修正 4）刻意讓帳單
    指向既有 contract（678／600）／estate（456／400）fixture 的真實 id，
    使三個 fixture 宇宙相連（見 fixture_data 頂端註解）；孤立區段是舊設計，
    與「跨域可查得到同一戶」的新要求互斥，此處放寬為只驗帳單自身 id。

    ⚠️ 真資料子集（role_id=20151/user_id=12291 可見）併入後不再是「全部 ≥900000」——
    合成三筆（900001-900003）仍須落在合成區段；真資料列改用
    `bill_visibility` 對 12291 的宣告來認定，不硬寫死其 id 集合。
    """
    synthetic_ids = {900001, 900002, 900003}
    for row in table.rows():
        if row["id"] in synthetic_ids:
            assert row["id"] >= 900000
        else:
            # 非合成列必須是真資料子集：對 12291 宣告可見。
            assert 12291 in (table.visible_to(row["id"]) or []), \
                f"bill {row['id']} 既非合成範圍也未對 12291 宣告可見——不明列"
    assert synthetic_ids <= {r["id"] for r in table.rows()}
