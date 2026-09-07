"""TDD：`demo_vendor4.json` 真資料子集的可見性與跨域連貫（任務契約 2026-09-08）。

驗三件事：
1. 12291（demo 使用者）視角：可見帳單皆為真資料列、不含既有合成列 900001-900003；
2. 既有合成列對其原本宣告的使用者（9001／9002 等）仍可見——12291 不可見不等於全體不可見；
3. 真資料子集跨域連貫：每筆帳單的 contract_id／estate_id 在對應表裡都查得到列、
   每顆電錶／修繕單的 estate_id 在 estates 表裡也查得到列。
"""
import json
from pathlib import Path

import pytest

from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.estate_fixtures import EstateFixtureTable
from services.jgb.fixtures import BillFixtureTable
from services.jgb.meter_fixtures import MeterFixtureTable
from services.jgb.repair_fixtures import RepairFixtureTable

pytestmark = pytest.mark.unit

DEMO_USER_ID = 12291
LEGACY_BILL_IDS = {900001, 900002, 900003}
REAL_BILL_IDS = {769258, 769246, 769249, 756248, 756242, 727606, 750524}
REAL_CONTRACT_IDS = {89481, 85894, 84921, 88247}
REAL_ESTATE_IDS = {68926, 67649, 67651, 67652, 45728}

_FIXTURE_PATH = (Path(__file__).resolve().parents[3]
                 / "services" / "jgb" / "fixture_data" / "demo_vendor4.json")


@pytest.fixture
def raw_fixture():
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


# ── 1. 12291 視角：可見帳單皆為真資料列 ─────────────────────────────────────

def test_12291_visible_bills_are_all_real_rows_not_legacy(raw_fixture):
    visible_bill_ids = {int(bid) for bid, viewers in raw_fixture["bill_visibility"].items()
                         if DEMO_USER_ID in viewers}
    assert visible_bill_ids, "12291 視角查無任何可見帳單——先確認 fixture 已跑過建置腳本"
    assert visible_bill_ids & LEGACY_BILL_IDS == set(), \
        f"12291 仍看得到既有合成帳單：{visible_bill_ids & LEGACY_BILL_IDS}"
    assert visible_bill_ids <= REAL_BILL_IDS, \
        f"12291 可見帳單出現非預期 id：{visible_bill_ids - REAL_BILL_IDS}"


def test_12291_visible_contracts_and_estates_are_all_real_rows(raw_fixture):
    visible_contract_ids = {int(cid) for cid, viewers in raw_fixture["contract_visibility"].items()
                             if DEMO_USER_ID in viewers}
    visible_estate_ids = {int(eid) for eid, viewers in raw_fixture["estate_visibility"].items()
                           if DEMO_USER_ID in viewers}
    assert visible_contract_ids == REAL_CONTRACT_IDS
    assert visible_estate_ids == REAL_ESTATE_IDS


# ── 2. 既有合成列對原本宣告的使用者仍可見 ────────────────────────────────────

def test_legacy_synthetic_bills_still_visible_to_9001_and_9002(raw_fixture):
    assert 9001 in raw_fixture["bill_visibility"]["900001"]
    assert 9001 in raw_fixture["bill_visibility"]["900002"]
    assert 9002 in raw_fixture["bill_visibility"]["900003"]
    # 12291 已從三筆既有合成帳單移除（改為只看真資料）。
    for bid in ("900001", "900002", "900003"):
        assert DEMO_USER_ID not in raw_fixture["bill_visibility"][bid]


def test_legacy_synthetic_contracts_still_visible_to_original_tenants(raw_fixture):
    assert 9001 in raw_fixture["contract_visibility"]["678"]
    assert 9002 in raw_fixture["contract_visibility"]["600"]
    assert DEMO_USER_ID not in raw_fixture["contract_visibility"]["678"]
    assert DEMO_USER_ID not in raw_fixture["contract_visibility"]["600"]


def test_legacy_synthetic_estates_still_visible_to_original_owner(raw_fixture):
    assert 1001 in raw_fixture["estate_visibility"]["456"]
    assert 1001 in raw_fixture["estate_visibility"]["400"]
    assert DEMO_USER_ID not in raw_fixture["estate_visibility"]["456"]
    assert DEMO_USER_ID not in raw_fixture["estate_visibility"]["400"]


def test_legacy_rows_unchanged_values(raw_fixture):
    """既有合成列的**值**沒被動過（13 個凍結回歸測試引用它們的具體值）。"""
    bills_by_id = {b["id"]: b for b in raw_fixture["bills"]}
    assert bills_by_id[900001]["total"] == 18000.0
    assert bills_by_id[900001]["contract_id"] == 678
    contracts_by_id = {c["id"]: c for c in raw_fixture["contracts"]}
    assert contracts_by_id[678]["title"] == "信義區套房A"
    assert contracts_by_id[678]["to_user_phone"] == "0912345678"
    repairs_by_id = {r["id"]: r for r in raw_fixture["repairs"]}
    assert repairs_by_id[3001]["category_name"] == "衛浴維修"
    assert repairs_by_id[3002]["item_name"] == "冷氣機"


# ── 3. 真資料子集跨域連貫 ────────────────────────────────────────────────────

def test_every_real_bill_has_existing_contract_and_estate():
    bills = BillFixtureTable()
    contracts = ContractFixtureTable()
    estates = EstateFixtureTable()
    real_bills = [b for b in bills.rows() if b["id"] in REAL_BILL_IDS]
    assert len(real_bills) == len(REAL_BILL_IDS)
    for b in real_bills:
        assert contracts.by_id(b["contract_id"]) is not None, \
            f"bill {b['id']} 的 contract_id={b['contract_id']} 查無合約列"
        assert any(e["id"] == b["estate_id"] for e in estates.rows()), \
            f"bill {b['id']} 的 estate_id={b['estate_id']} 查無物件列"


def test_every_real_meter_and_repair_has_existing_estate():
    estates = EstateFixtureTable()
    estate_ids = {e["id"] for e in estates.rows()}
    meters = MeterFixtureTable()
    repairs = RepairFixtureTable()
    real_meters = [m for m in meters.rows() if m["id"] == 1061]
    real_repairs = [r for r in repairs.rows() if r["id"] in (8591, 7628)]
    assert len(real_meters) == 1
    assert len(real_repairs) == 2
    for m in real_meters:
        assert m["estate_id"] in estate_ids, f"meter {m['id']} 的 estate_id 查無物件列"
    for r in real_repairs:
        assert r["estate_id"] in estate_ids, f"repair {r['id']} 的 estate_id 查無物件列"


def test_real_bill_statuses_cover_overdue_paid_and_pending():
    """帳單狀態涵蓋未繳且逾期／已繳／未到期或待對帳（見任務契約驗收標準）。"""
    bills = BillFixtureTable()
    real_bills = {b["id"]: b for b in bills.rows() if b["id"] in REAL_BILL_IDS}
    # 逾期未繳：status=2（待繳費），date_expire 早於今天（今天 2026-09-08）。
    assert real_bills[756248]["status"] == 2
    assert real_bills[756248]["date_expire"] < 20260908
    # 已繳：status=16，pay_at 有值。
    for bid in (769246, 756242, 727606):
        assert real_bills[bid]["status"] == 16
        assert real_bills[bid]["pay_at"]
    # 未到期：status=1（待發送），date_expire 晚於今天。
    assert real_bills[769249]["status"] == 1
    assert real_bills[769249]["date_expire"] > 20260908


def test_one_real_contract_expires_within_90_to_150_days_of_today():
    """一份合約 90-150 天內到期（今天 2026-09-08 → 2026-12-07 ~ 2027-02-05）。"""
    contracts = ContractFixtureTable()
    c = contracts.by_id(89481)
    assert c is not None
    assert 20261207 <= c["date_end"] <= 20270205, c["date_end"]


def test_repairs_cover_processing_and_closed():
    """修繕一張處理中、一張已結。"""
    repairs = RepairFixtureTable()
    processing = repairs.by_id(8591)
    closed = repairs.by_id(7628)
    assert processing["status"] == 1        # 申請中
    assert closed["status"] == 16            # 完成修繕


def test_one_real_meter_has_positive_balance():
    meters = MeterFixtureTable()
    m = meters.by_id(1061)
    assert m is not None
    assert m["balance"] > 0
