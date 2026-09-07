"""`GET /bills` 的兩個 viewer／tenant 過濾：一個改為 raise，一個具名登記為缺口。

2026-08-25 盤查（transport-migration-inventory.md）發現：
- `viewer_user_id` production 有圈定、替身沒有 → 舊行為是**靜默忽略**，
  而 `get_bill_visibility` 又在 mock 端自行回 `data: []`＝**捏造一個「看不到」**；
  兩者疊起來讓 account 面向對使用者講一個沒有證據的結論。
- `user_id` production 是 `whereHas('belongContract', ...)`，替身同樣沒有（**GAP-B1**）。

本檔把這兩件事釘住：能忠實模擬的就模擬，不能的就**拒答**，絕不回一個編出來的答案。
"""
import asyncio

import pytest

from services.jgb.fixtures import BillFixtureTable
from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.transport import JGBMockTransport, UnsupportedMockParameterError

pytestmark = pytest.mark.unit

PATH = "/api/external/v1/bills"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _transport():
    return JGBMockTransport(BillFixtureTable(), ContractFixtureTable())


@pytest.mark.req("face-exit-before-grounding:1")
def test_viewer_user_id_is_refused_when_malformed():
    """`viewer_user_id` 非合法整數 → raise（不得忽略後回資料）。"""
    with pytest.raises(UnsupportedMockParameterError):
        _run(_transport().send("GET", PATH,
                               params={"role_id": "R1", "viewer_user_id": "U9", "bill_id": "900001"}))


@pytest.mark.req("face-exit-before-grounding:1")
def test_viewer_user_id_filters_by_fixture_declared_visibility():
    """transport-extension-full-coverage（2026-09-08）：fixture 宣告過可見性後，
    `viewer_user_id` 從「一律 raise」改為**依宣告過濾**——900001 宣告可見 [9001, 100]，
    9001 看得到、9002 看不到（過濾後空集，非例外）。
    """
    r_visible = _run(_transport().send(
        "GET", PATH, params={"role_id": "R1", "viewer_user_id": "9001", "bill_id": "900001"}))
    assert r_visible["success"] is True
    assert [r["id"] for r in r_visible["data"]] == [900001]

    r_hidden = _run(_transport().send(
        "GET", PATH, params={"role_id": "R1", "viewer_user_id": "9002", "bill_id": "900001"}))
    assert r_hidden["success"] is True
    assert r_hidden["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_viewer_user_id_raises_for_undeclared_bill():
    """**未宣告**可見性的帳單仍 raise——不得因為其他帳單已宣告就放寬誠實紀律。

    以本測試自建的 fixture 表模擬「有一筆未宣告」的狀態，
    不動 `demo_vendor4.json`（三筆現行帳單皆已宣告，是刻意的 demo 資料決策）。
    """
    class _PartiallyDeclaredBills:
        def rows(self):
            return [
                {**BillFixtureTable().by_id(900001)},          # type: ignore[dict-item]
            ]

        def by_id(self, bill_id):
            return self.rows()[0] if bill_id == 900001 else None

        def visible_to(self, bill_id):
            return None   # 刻意：未宣告

    with pytest.raises(UnsupportedMockParameterError):
        _run(JGBMockTransport(_PartiallyDeclaredBills()).send(
            "GET", PATH, params={"role_id": "R1", "viewer_user_id": "9001"}))


@pytest.mark.req("face-exit-before-grounding:1")
def test_bills_without_viewer_scope_still_works():
    """沒帶 viewer_user_id 的既有路徑不受影響（零回歸）。"""
    r = _run(_transport().send("GET", PATH, params={"role_id": "R1"}))
    assert r["success"] is True and r["data"]


@pytest.mark.req("face-exit-before-grounding:1")
def test_bill_visibility_does_not_fabricate_an_answer(monkeypatch):
    """mock 模式下 `get_bill_visibility` 回降級，而不是捏造的「看不到」。

    ⚠️ 這條**刻意**斷言 success is False：secondary attach 只在 success 時掛，
    面向因此走「未確認具體資源」措辭。若日後有人把它改回 `data: []`，
    等於讓系統再次無證據地宣稱某成員看不到某張帳單。
    """
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    from services.jgb_system_api import JGBSystemAPI
    result = _run(JGBSystemAPI().get_bill_visibility(
        role_id="R1", viewer_user_id="U9", bill_id="900001"))
    assert result["success"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_gap_b1_user_id_is_not_filtered_yet():
    """**GAP-B1（已登記缺口，非已證行為）**：`user_id` 目前不過濾。

    production：`whereHas('belongContract', to_user_id = user_id AND active = 1)`。
    ⚠️ **跨域連貫修正（2026-09-08）後現況更新**：帳單已改指向既有 contract
    fixture 的真實 id（678／600，見 `demo_vendor4.json`），三個 fixture 宇宙
    不再互不連通——但這**只解了資料連貫**，`_bills_index`／`get_bills` 本身
    仍未實作 `to_user_id` 過濾邏輯，`user_id` 參數依舊被忽略（GAP-B1 本體，
    邏輯缺口，非資料缺口，屬另一個需要授權的 slice）。
    故此處鎖住**現況**並標明它是缺口——任何人讀到這條測試綠燈，
    **不得**推論「帳單的租客過濾已驗」。
    """
    all_rows = _run(_transport().send("GET", PATH, params={"role_id": "R1"}))["data"]
    filtered = _run(_transport().send("GET", PATH,
                                      params={"role_id": "R1", "user_id": "9001"}))["data"]
    assert [r["id"] for r in filtered] == [r["id"] for r in all_rows]
