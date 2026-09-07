"""`jgb2.query.<domain>` 出向轉發整合測試（spec agentic-mcp-orchestration・任務 1.5）。

用 `RecordingTransport(JGBMockTransport())` 包裝真的 `JGBSystemAPI`——驗的是
**有沒有轉發** `viewer_user_id`，不是圈定語義本身（那本機不可驗，見域映射表）。

⚠️ bills 對 `viewer_user_id` 的 `UnsupportedMockParameterError` 是**刻意保留的大聲
失敗**（`services/jgb/transport.py:_bills_index`），只是**觸發條件已經變窄**
（transport-extension-full-coverage）：fixture 現在用 `bill_visibility` 逐筆**宣告**
可見的 user_id ⇒ 宣告過的列改成依宣告過濾，**未宣告的列**才照樣 raise。
本檔因此把原本那條「送了 viewer_user_id 必 raise」拆成兩條、⛔ 不刪測試目的：
  ① 轉發真的發生 **且** 依宣告過濾（`test_bills_forwards_viewer_user_id_and_filters`）；
  ② 未宣告的列仍**大聲失敗**（`test_bills_undeclared_visibility_still_raises`）——
     這一條才是「⛔ 不放寬 mock」的證據。
"""
import types

import pytest

from services.agent.identity import Identity
from services.agent.tools import jgb2
from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.estate_fixtures import EstateFixtureTable
from services.jgb.fixtures import BillFixtureTable
from services.jgb.meter_fixtures import MeterFixtureTable
from services.jgb.repair_fixtures import RepairFixtureTable
from services.jgb.team_fixtures import TeamMemberFixtureTable
from services.jgb.transport import JGBMockTransport, RecordingTransport, UnsupportedMockParameterError
from services.jgb_system_api import JGBSystemAPI

pytestmark = [pytest.mark.integration, pytest.mark.req("agentic-mcp-orchestration:1.5")]


def _identity(role_id=None, user_id=None):
    """租客身分（`resolved_audience()` 缺 ⇒ jgb2 工具層 fail-closed 當 tenant）。"""
    return types.SimpleNamespace(role_id=role_id, user_id=user_id)


def _pm_identity(role_id=None, user_id=None):
    """房東／管理者身分——bills／contracts 走**單證**路徑（1.10 P1）。"""
    return Identity(vendor_id=1, target_user="property_manager", mode="b2c",
                    role_id=role_id, user_id=user_id, session_id="t")


@pytest.fixture()
def recorded_api(monkeypatch):
    """真 `JGBSystemAPI`＋mock transport，外包一層 `RecordingTransport`。

    ⚠️ **六張 fixture 表全部裝配**（transport-extension-full-coverage）：
    estates／meters／team_members／member_permissions／repairs 已遷入
    `MIGRATED_ENDPOINTS`，少裝一張表的失效形狀是 `MissingFixtureError`
    （替身的誠實紀律：⛔ 不靜默降級），而不是「這條路本來就查不到」。
    ⛔ 不得為了讓測試變綠而改回只裝兩張——那會讓下面三域的正對照組永遠是紅的。
    """
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    api = JGBSystemAPI()
    estate_fixtures = EstateFixtureTable()
    recording = RecordingTransport(JGBMockTransport(
        BillFixtureTable(), ContractFixtureTable(),
        estate_fixtures=estate_fixtures,
        meter_fixtures=MeterFixtureTable(),
        team_fixtures=TeamMemberFixtureTable(),
        repair_fixtures=RepairFixtureTable(),
    ))
    api._mock_transport = recording
    # `get_estate_detail` 走 `self._estate_fixtures`（見 `JGBSystemAPI.__init__` 註解：
    # estates／estate_detail 共用**同一個**實例）⇒ 這裡也換成同一份，
    # ⛔ 不留兩份互不同步的拷貝。
    api._estate_fixtures = estate_fixtures
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api, recording


# ══════════════════════════════════════════════════════════════════════
# bills：viewer_user_id 有轉發，mock 依契約 raise（不放寬的證據）
# ══════════════════════════════════════════════════════════════════════

async def test_bills_forwards_viewer_user_id_and_filters(recorded_api):
    """轉發真的發生，**且**替身依 fixture 宣告的可見性過濾（不是忽略該參數）。"""
    api, recording = recorded_api

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9001"), {"face": "帳單異常"})

    assert recording.calls, "沒有任何出向呼叫被記錄——轉發沒有發生"
    method, path, params = recording.calls[-1]
    assert method == "GET"
    assert path == "/api/external/v1/bills"
    assert params.get("viewer_user_id") == "9001"

    # 依 `bill_visibility` 宣告：9001 看得到 900001／900002，看不到 900003。
    # ⛔ 不只斷言「有回東西」——那樣把 viewer_user_id 整個忽略掉也會過。
    fixtures = recording.inner.fixtures
    visible_ids = {r["id"] for r in fixtures.rows() if 9001 in (fixtures.visible_to(r["id"]) or [])}
    hidden_ids = {r["id"] for r in fixtures.rows()} - visible_ids
    assert hidden_ids, "fixture 沒有任何一列對 9001 不可見 ⇒ 這條對照組驗不到過濾"
    assert result["ok"] is True
    returned = {str(row.get("id")) for row in (result["data"]["candidates"] or [])}
    assert returned, "沒有任何候選列 ⇒ 這條斷言驗不到過濾（⛔ 不得以空集合當通過）"
    assert returned == {str(i) for i in visible_ids}
    assert not (returned & {str(i) for i in hidden_ids})


async def test_bills_undeclared_visibility_still_raises(recorded_api):
    """⛔ **不放寬 mock**：`bill_visibility` 未宣告的列，帶 viewer_user_id 一律
    大聲失敗——替身算不出可見性時不得以「忽略該參數的結果」回答可見性問題。"""
    api, recording = recorded_api
    fixtures = recording.inner.fixtures
    fixtures._visibility.pop("900001", None)      # noqa: SLF001 — 刻意製造未宣告列
    assert fixtures.visible_to(900001) is None, "正對照：這一列現在確實是未宣告"

    with pytest.raises(UnsupportedMockParameterError):
        await jgb2.query_bills(
            _identity(role_id="1", user_id="9001"), {"face": "帳單異常"})


async def test_bills_without_viewer_user_id_does_not_raise(recorded_api):
    """正對照組：**pm 單證**（缺 user_id）⇒ 不轉發 viewer_user_id ⇒ mock 不 raise
    （證明上一條的 raise 是因為參數真的被送出，不是 mock 本身壞掉逢 bills 必炸）。

    ⚠️ **1.10 P1 改過身分**：原本用 `_identity(role_id="1", user_id=None)`＝租客缺
    user_id。那個組合現在被工具層的雙證閘擋在出向之前（正是這次修掉的洩漏），
    拿它當「mock 不會逢 bills 必炸」的對照組等於什麼都沒驗到——一通呼叫都不會發生。
    改用 pm 身分：pm 是**刻意保留的單證路徑**（1.5 收案裁定，帶 user_id 反而會被
    jgb2 的 to_user_id 圈定成空），`user_id=None` 合法且會真的發出向呼叫。
    """
    api, recording = recorded_api

    result = await jgb2.query_bills(_pm_identity(role_id="1", user_id=None),
                                    {"face": "帳單異常", "ref": "678"})

    # pm 單證：工具層不擋 ⇒ 真的出向查詢；沒有 user_id ⇒ viewer_user_id 不轉發
    # ⇒ mock 的 UnsupportedMockParameterError 不會被觸發（本函式沒 raise 就是證據）。
    assert recording.calls, "pm 單證應該真的發出向呼叫——沒有紀錄等於這條對照組是空的"
    for _method, _path, params in recording.calls:
        assert "viewer_user_id" not in params, f"pm 不該圈定 viewer_user_id：{params}"
    assert isinstance(result, dict) and "ok" in result


async def test_tenant_missing_user_id_blocked_before_outbound(recorded_api):
    """1.10 P1：租客缺 user_id ⇒ NO_MATCH，且**出向呼叫一通都沒有**。

    ⚠️ 這是本檔對 P1 的整合層證據：擋在工具層、不是靠 jgb2 API 端降級——
    後者只在「無 bill_ref」時成立，帶 ref 就會真的把整個 role 的帳單查回來。
    """
    api, recording = recorded_api

    result = await jgb2.query_bills(_identity(role_id="1", user_id=None),
                                    {"face": "帳單異常", "ref": "678"})

    assert result == {"ok": False, "error": "NO_MATCH"}
    assert recording.calls == [], f"閘門沒擋住，仍發出向呼叫：{recording.calls}"


# ══════════════════════════════════════════════════════════════════════
# contracts：viewer_user_id 有轉發，mock 不設防（不 raise，只驗轉發）
# ══════════════════════════════════════════════════════════════════════

async def test_contracts_forwards_viewer_user_id_no_raise(recorded_api):
    api, recording = recorded_api

    result = await jgb2.query_contracts(
        _identity(role_id="1", user_id="9001"),
        {"face": "合約異動", "keyword": "信義區套房A"})

    assert result["ok"] is True   # 命中 fixture 的 678 號合約
    method, path, params = recording.calls[-1]
    assert path == "/api/external/v1/contracts/status-overview"
    assert params.get("viewer_user_id") == "9001"
    assert params.get("keyword") == "信義區套房A"


async def test_contracts_ref_uses_contract_ids_and_forwards_viewer(recorded_api):
    api, recording = recorded_api

    result = await jgb2.query_contracts(
        _identity(role_id="1", user_id="9001"), {"face": "合約異動", "ref": "678"})

    assert result["ok"] is True
    assert result["data"]["facts"]   # builder 對真合約列有產出非空 facts
    method, path, params = recording.calls[-1]
    assert params.get("contract_ids") == "678"
    assert params.get("viewer_user_id") == "9001"


# ══════════════════════════════════════════════════════════════════════
# 其餘三域缺 user_id ⇒ NO_MATCH（雙證閘門在工具層擋下）
#
# ⚠️ **現況更新（transport-extension-full-coverage）**：accounts／meters／estates
# 的四個 API（get_member_permissions／get_meters／get_estate_status／
# get_estate_detail）**都已遷入** `MIGRATED_ENDPOINTS`，改走 `_send` ⇒
# `RecordingTransport` 會記到它們。正對照組仍維持「補上 user_id 後是否真的取得
# fixture 資料」——它比「有沒有紀錄」更強（能同時證明 fixture 表真的裝配了）。
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("fn,face,args_extra", [
    (jgb2.query_accounts, "團隊成員權限", {"ref": "292"}),
    (jgb2.query_meters, "電表排障", {"ref": "501"}),
    (jgb2.query_estates, "物件現況診斷", {"ref": "54126"}),
])
async def test_dual_proof_domains_missing_user_id_no_match(recorded_api, fn, face, args_extra):
    api, recording = recorded_api
    args = {"face": face, **args_extra}

    result = await fn(_identity(role_id="1", user_id=None), args)

    assert result == {"ok": False, "error": "NO_MATCH"}


@pytest.mark.parametrize("fn,face,args_extra", [
    (jgb2.query_accounts, "團隊成員權限", {"ref": "292"}),
    (jgb2.query_meters, "電表排障", {"ref": "501"}),
    (jgb2.query_estates, "物件現況診斷", {"ref": "54126"}),
])
async def test_dual_proof_domains_positive_control(recorded_api, fn, face, args_extra):
    """正對照組：同一請求補上 user_id、且 ref 對到真 fixture 資料，就該拿到 facts
    （不是恆 NO_MATCH 的假陰性——證明上一條真的是被雙證 gate 擋下，而非資料本來就查不到）。
    """
    api, recording = recorded_api
    args = {"face": face, **args_extra}

    result = await fn(_identity(role_id="1", user_id="9001"), args)

    assert result["ok"] is True, f"補上 user_id 後應命中 fixture：{result}"
    assert result["data"]["facts"]
