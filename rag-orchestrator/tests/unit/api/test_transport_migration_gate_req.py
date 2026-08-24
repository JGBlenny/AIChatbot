"""TDD：未遷移端點 fail loudly（spec conversational-routing-execution 任務 4.3，R4.1/R4.3）。

本組證明的 invariant 是**兩層分離**：

    endpoint 已被辨識  ≠  endpoint 已允許由 mock transport 接管

⚠️ **最重要的不是「有拋例外」，而是「真網路在拋例外之前沒有被碰到」。**
表面相同的失效模式是：先發真請求 → 出錯 → wrapper 轉成 `UnmigratedMockEndpointError`；
例外一樣，外部副作用已經發生。故本組以 **sentinel real transport** 反證：
只要真 transport 被碰一下就拋 `RealNetworkTouched`，測試若拿到 sentinel 即代表 invariant 失敗。
"""
import asyncio

import pytest

from services.jgb.transport import (
    MIGRATED_ENDPOINTS,
    JGBMockTransport,
    MissingFixtureError,
    UnmigratedMockEndpointError,
    UnresolvedEndpointError,
    resolve_endpoint,
)

pytestmark = pytest.mark.unit

BILLS = "/api/external/v1/bills"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class RealNetworkTouched(AssertionError):
    """sentinel：真 transport 被碰到就拋——測試拿到它即代表 invariant 失敗。"""


class SentinelRealTransport:
    """一被呼叫就炸的假 real transport；同時記錄呼叫次數供反事實斷言。"""

    def __init__(self) -> None:
        self.calls = 0

    async def send(self, method, path, *, params=None, data=None):
        self.calls += 1
        raise RealNetworkTouched(f"真網路被碰到：{method} {path}")


@pytest.fixture
def mock_transport():
    return JGBMockTransport()          # 4.4 之前不裝配 fixture


# ── 三態：resolve → admission → fixture ───────────────────────────────────
def test_unresolvable_endpoint_fails_loudly(mock_transport):
    """1. 無法 resolve → UnresolvedEndpointError（reason='no_match'）。"""
    with pytest.raises(UnresolvedEndpointError) as ei:
        _run(mock_transport.send("GET", "/api/external/v1/contracts/12345"))
    assert ei.value.reason == "no_match"


def test_resolved_but_unmigrated_endpoint_fails_loudly(monkeypatch, mock_transport):
    """2. 可 resolve、但不在 MIGRATED_ENDPOINTS → UnmigratedMockEndpointError。"""
    import services.jgb.transport as t

    monkeypatch.setattr(t, "ROUTES", (
        ("GET", "/api/external/v1/repairs", "repairs"),   # 刻意不入 admission set
    ))
    assert "repairs" not in MIGRATED_ENDPOINTS
    with pytest.raises(UnmigratedMockEndpointError):
        _run(mock_transport.send("GET", "/api/external/v1/repairs"))


def test_migrated_but_missing_fixture_fails_loudly(mock_transport):
    """3. 已遷移但 fixture 不存在 → MissingFixtureError（**不得**退回 real HTTP）。"""
    with pytest.raises(MissingFixtureError):
        _run(mock_transport.send("GET", BILLS))


# ── 4. 反事實：真網路 call count == 0 ─────────────────────────────────────
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/external/v1/contracts/12345"),   # unresolved
    ("GET", BILLS),                                # migrated 但缺 fixture
    ("GET", f"{BILLS}/987654321"),                 # 同上（detail 樣板）
])
def test_no_real_network_touched_on_any_failure(method, path):
    """任何失敗路徑下，real transport 的呼叫次數 MUST 為 0。

    ⚠️ 這一條才是本 task 的核心；只斷言「有拋例外」會漏掉
    「先打真請求、再把錯誤包成正確例外」這種假綠。
    """
    import os

    os.environ["USE_MOCK_JGB_API"] = "true"
    from services.jgb_system_api import JGBSystemAPI

    api = JGBSystemAPI()
    spy = SentinelRealTransport()
    api._real_transport = spy

    with pytest.raises(Exception) as ei:
        _run(api._send(method, path))

    assert not isinstance(ei.value, RealNetworkTouched), "invariant 失敗：真網路被碰到"
    assert spy.calls == 0, f"真 transport 被呼叫 {spy.calls} 次"


def test_mock_transport_holds_no_real_transport(mock_transport):
    """結構性保證：替身**不持有** real transport，故 fallback 不是「沒寫」而是「不可達」。"""
    assert not any(
        "real" in name.lower() for name in vars(mock_transport)
    ), f"替身不應持有 real transport：{vars(mock_transport)}"


# ── 層次分離：4.3 不得改動 4.2 的 endpoint identity 語義 ──────────────────
def test_resolver_still_ignores_migration_state(monkeypatch):
    """4.2 的守衛，改寫成**行為證明**：未遷移的 endpoint 仍能被正確 resolve。

    （原 `test_resolver_does_not_consult_migration_state` 以 `hasattr` 判定；
    4.3 定義 `MIGRATED_ENDPOINTS` 後，改由行為直接證明 resolver 未消費它。）
    """
    import services.jgb.transport as t

    monkeypatch.setattr(t, "ROUTES", (
        ("GET", "/api/external/v1/repairs", "repairs"),
    ))
    assert "repairs" not in MIGRATED_ENDPOINTS
    assert t.resolve_endpoint("GET", "/api/external/v1/repairs") == "repairs"


def test_migrated_endpoints_holds_identities_not_paths():
    """admission set 只放 endpoint identity，不得放 concrete path／樣板。"""
    assert MIGRATED_ENDPOINTS == frozenset({"bills", "bill_detail"})
    assert not any("/" in key for key in MIGRATED_ENDPOINTS)


def test_admission_set_keys_all_exist_in_routes():
    """admission set 不得列出 ROUTES 沒有的 endpoint（避免死條目）。"""
    from services.jgb.transport import ROUTES

    assert MIGRATED_ENDPOINTS <= {key for _, _, key in ROUTES}


def test_detail_identity_unchanged_by_43():
    """4.2 的核心結果不得被 4.3 改動。"""
    assert resolve_endpoint("GET", f"{BILLS}/987654321") == "bill_detail"
