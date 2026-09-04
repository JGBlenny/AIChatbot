"""`jgb2.query.<domain>` 出向轉發整合測試（spec agentic-mcp-orchestration・任務 1.5）。

用 `RecordingTransport(JGBMockTransport())` 包裝真的 `JGBSystemAPI`——驗的是
**有沒有轉發** `viewer_user_id`，不是圈定語義本身（那本機不可驗，見域映射表）。

⚠️ bills 對 `viewer_user_id` 的 `UnsupportedMockParameterError` 是**刻意保留的大聲
失敗**（`services/jgb/transport.py:_bills_index`）——本測試斷言它「有記到參數且
例外正是這一種」，不是把它當 bug 修掉。⛔ 不放寬 mock。
"""
import types

import pytest

from services.agent.tools import jgb2
from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.fixtures import BillFixtureTable
from services.jgb.transport import JGBMockTransport, RecordingTransport, UnsupportedMockParameterError
from services.jgb_system_api import JGBSystemAPI

pytestmark = [pytest.mark.integration, pytest.mark.req("agentic-mcp-orchestration:1.5")]


def _identity(role_id=None, user_id=None):
    return types.SimpleNamespace(role_id=role_id, user_id=user_id)


@pytest.fixture()
def recorded_api(monkeypatch):
    """真 `JGBSystemAPI`＋mock transport，外包一層 `RecordingTransport`。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    api = JGBSystemAPI()
    recording = RecordingTransport(JGBMockTransport(BillFixtureTable(), ContractFixtureTable()))
    api._mock_transport = recording
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api, recording


# ══════════════════════════════════════════════════════════════════════
# bills：viewer_user_id 有轉發，mock 依契約 raise（不放寬的證據）
# ══════════════════════════════════════════════════════════════════════

async def test_bills_forwards_viewer_user_id_and_mock_raises(recorded_api):
    api, recording = recorded_api

    with pytest.raises(UnsupportedMockParameterError):
        await jgb2.query_bills(
            _identity(role_id="1", user_id="9001"), {"face": "帳單異常"})

    # 例外前 RecordingTransport 已記到這通呼叫——證明轉發真的發生，不是被吞掉。
    assert recording.calls, "沒有任何出向呼叫被記錄——轉發沒有發生"
    method, path, params = recording.calls[-1]
    assert method == "GET"
    assert path == "/api/external/v1/bills"
    assert params.get("viewer_user_id") == "9001"


async def test_bills_without_viewer_user_id_does_not_raise(recorded_api):
    """正對照組：identity 缺 user_id ⇒ 不轉發 viewer_user_id ⇒ mock 不 raise
    （證明上一條的 raise 是因為參數真的被送出，不是 mock 本身壞掉逢 bills 必炸）。
    """
    api, recording = recorded_api

    result = await jgb2.query_bills(_identity(role_id="1", user_id=None), {"face": "帳單異常"})

    # 沒有 identity.user_id：get_bills 的 _validate_identity(role_id, None) 為假、
    # 且無 bill_ref/contract_ids ⇒ API 端降級（success False）⇒ 工具層收斂為 NO_MATCH。
    assert result == {"ok": False, "error": "NO_MATCH"}
    if recording.calls:
        _, _, params = recording.calls[-1]
        assert "viewer_user_id" not in params


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
# ⚠️ accounts／meters／estates 的三個 API（get_member_permissions／get_meters／
# get_estate_status／get_estate_detail）**尚未遷入** `Transport`（`MIGRATED_
# ENDPOINTS` 只有 `bills`／`bill_detail`／`contracts`，見 transport.py:240）——
# 它們在 mock 模式走方法級 `if self.use_mock:` 短路，根本不經 `_send`／
# `RecordingTransport`。故這裡不能用「recording.calls 有沒有紀錄」當正對照組，
# 改用「補上 user_id 後是否真的取得 fixture 資料」證明 gate 不是恆假陰性。
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
