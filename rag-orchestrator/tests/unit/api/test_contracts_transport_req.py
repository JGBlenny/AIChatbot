"""unit：contracts 遷入 `JGBMockTransport` 後的 production-equivalent filtering。

要鎖的命題：

> **第一次無識別回全部；adapter 帶識別重查時，transport 依 request 收斂。**

方法級 mock 的簽章不吃 `contract_ids`／`keyword`，恆回全部——那正好吃掉了
「重查收斂」這段要驗的 execution 行為（v4 實測逼出：候選列永遠 2 筆、無法收斂）。
"""
import pytest

from services.jgb.contract_fixtures import (
    ContractFixtureTable,
    ForeignContractFieldError,
    assert_contract_projection,
)
from services.jgb.transport import (
    MIGRATED_ENDPOINTS,
    JGBMockTransport,
    MissingFixtureError,
    resolve_endpoint,
)

pytestmark = pytest.mark.unit

PATH = "/api/external/v1/contracts/status-overview"


def _t():
    return JGBMockTransport(fixtures=object(), contract_fixtures=ContractFixtureTable())


@pytest.mark.req("face-exit-before-grounding:1")
def test_route_and_admission():
    assert resolve_endpoint("GET", PATH) == "contracts"
    assert "contracts" in MIGRATED_ENDPOINTS


@pytest.mark.req("face-exit-before-grounding:1")
async def test_no_identifier_returns_all():
    """⚠️ 真資料子集併入後（同為 active=1／is_newest=1）不再是封閉的兩筆——
    改驗「678／600 仍在結果內、相對順序不變、整體仍是 id desc」。
    """
    r = await _t().send("GET", PATH, params={"role_id": "20151"})
    ids = [x["id"] for x in r["data"]]
    assert r["success"]
    assert 678 in ids and 600 in ids
    assert ids.index(678) < ids.index(600)
    assert ids == sorted(ids, reverse=True)


@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("ids,expected", [
    ("678", [678]), ("600", [600]), ("678,600", [678, 600]), ("999", []),
    (" 678 ", [678]),                       # adapter 可能夾空白
    ("678abc", [678]),                      # ★ PHP intval 取前綴數字（照抄 production）
    ("abc", []),                            # intval("abc")=0 → 匹配不到
])
async def test_contract_ids_converges(ids, expected):
    """★ 這條就是 v4 卡住的地方：帶 id 重查必須收斂。"""
    r = await _t().send("GET", PATH, params={"role_id": "20151", "contract_ids": ids})
    assert [x["id"] for x in r["data"]] == expected


@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("kw,expected", [
    ("信義區套房A", [678]), ("中山區雅房B", [600]), ("區", [678, 600]),
    # ★ M2 source audit：production 只比 title（`title LIKE %kw%`），**不含 address**
    ("信義路五段", []),
    ("不存在的物件", []),
])
async def test_keyword_filters(kw, expected):
    r = await _t().send("GET", PATH, params={"role_id": "20151", "keyword": kw})
    assert [x["id"] for x in r["data"]] == expected


@pytest.mark.req("face-exit-before-grounding:1")
async def test_role_id_required_like_production():
    r = await _t().send("GET", PATH, params={})
    assert r["success"] is False and r["error"]["code"] == 400


@pytest.mark.req("face-exit-before-grounding:1")
async def test_missing_contract_fixture_fails_closed():
    t = JGBMockTransport(fixtures=object())          # 未裝配合約 fixture
    with pytest.raises(MissingFixtureError):
        await t.send("GET", PATH, params={"role_id": "20151"})


@pytest.mark.req("face-exit-before-grounding:1")
def test_projection_guard_bites():
    with pytest.raises(ForeignContractFieldError):
        assert_contract_projection({"id": 1, "not_a_real_column": "x"})


@pytest.mark.req("face-exit-before-grounding:1")
def test_envelope_shape_matches_adapter_expectations():
    """adapter 讀 data 清單與 mapping；envelope 形狀不得漂。

    ⚠️ `total`／確切集合不再斷言固定為合成兩筆——真資料子集併入後全部
    active／is_newest 合約都會出現；改以 `ContractFixtureTable().rows()`
    的實際筆數推導期望值，並驗 678／600 仍在其中、順序仍是 id desc。
    """
    total_rows = len(ContractFixtureTable().rows())
    t = _t()
    r = t._contracts_index({"role_id": "20151"})
    assert set(r) == {"success", "mapping", "data", "pagination"}
    assert "bit_status" in r["mapping"] and r["pagination"]["total"] == total_rows
    assert r["pagination"]["total_pages"] == 1 and r["pagination"]["has_more"] is False
    ids = [x["id"] for x in r["data"]]
    assert ids == sorted(ids, reverse=True)          # orderBy id desc
    assert 678 in ids and 600 in ids


@pytest.mark.req("face-exit-before-grounding:1")
def test_empty_result_pagination_matches_production():
    """production：total=0 時 total_pages 為 **0**（非 1）。"""
    r = _t()._contracts_index({"role_id": "20151", "keyword": "查無此物件"})
    assert r["pagination"]["total"] == 0 and r["pagination"]["total_pages"] == 0
    assert r["pagination"]["has_more"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_projection_matches_formatcontract_keys():
    """M2：fixture 欄位集需覆蓋 formatContract 逐鍵（含 G1/G2/G4 三組）。"""
    from services.jgb.contract_fixtures import EXTERNAL_CONTRACT_FIELDS
    for k in ("contract_inviting_at", "contract_inviting_expire_at",
              "contract_inviting_sign_at", "contract_finish_sign_at",
              "to_user_login_email", "is_newest"):
        assert k in EXTERNAL_CONTRACT_FIELDS, f"投影缺 {k}"
    row = ContractFixtureTable().by_id(678)
    assert row["is_newest"] == 1 and row["to_user_login_email"]
