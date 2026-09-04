"""unit：`routers/agent.py`（`/api/v1/agent/openapi.json`・`/health`，
spec agentic-mcp-orchestration・任務 1.8）。

涵蓋：
- 無 key ⇒ 401（即使 `RAG_API_AUTH_ENFORCE` 關）——兩端點皆用
  `require_api_key_unconditional`，⛔ 不看該旗標。
- `openapi.json` 只列該身分可見工具（prospect vs tenant 對照，正對照組見
  `kb.get`／`help.read` 兩者皆可見）。
- `health` 紅燈條件各一（DSP-011 前提偵測四項，monkeypatch `premise_stats`）；
  `pending` 欄位（大綱／rules_sha 尚未落地）不算紅。
- AST：本檔（`routers/agent.py`）不得出現 `auth_enforced`（不變量 28）。

⛔ 不重複 `test_mcp_facade_unit_req.py` 已覆蓋的 `parse_identity`／`check_origin`
細節——本檔只驗router 這一層的接線（呼叫哪個函式、回傳形狀對不對）。
"""
import os

import pytest
from fastapi import HTTPException

from routers import agent
from services.agent import mcp_facade as F

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:1.8"


# ════════════════════════════════════════════════════════════════════
# 測試替身：最小 Request（router 只用 `.headers`／`.app.state`）
# ════════════════════════════════════════════════════════════════════
class _FakeState:
    def __init__(self, db_pool=None):
        self.db_pool = db_pool


class _FakeApp:
    def __init__(self, db_pool=None):
        self.state = _FakeState(db_pool)


class _FakeRequest:
    def __init__(self, headers=None, db_pool=None):
        self.headers = headers or {}
        self.app = _FakeApp(db_pool)


@pytest.fixture(autouse=True)
def _reset_caches():
    """每個測試前清掉行程內快取＋前提偵測計數，測試互不干擾。"""
    agent.reset_registry_cache()
    F.reset_premise_stats()
    yield
    agent.reset_registry_cache()
    F.reset_premise_stats()


def _bypass_key_and_vendor(monkeypatch, key=None):
    """monkeypatch 掉 DB 相依：key 驗證與 vendor 存在性檢查。"""
    key = key or {"id": 1, "name": "test", "is_internal": False, "vendor_ids": None}

    async def _fake_require_key(request, pool):
        return key

    async def _fake_vendor_exists(pool, vendor_id):
        return True

    monkeypatch.setattr(agent, "require_api_key_unconditional", _fake_require_key)
    monkeypatch.setattr(F, "vendor_exists", _fake_vendor_exists)
    return key


# ════════════════════════════════════════════════════════════════════
# 無 key ⇒ 401（即使 RAG_API_AUTH_ENFORCE 關）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_openapi_no_key_is_401_even_when_enforce_off(monkeypatch):
    monkeypatch.delenv("RAG_API_AUTH_ENFORCE", raising=False)
    req = _FakeRequest(headers={}, db_pool=None)
    with pytest.raises(HTTPException) as e:
        await agent.agent_openapi(req)
    assert e.value.status_code == 401


@pytest.mark.req(_SPEC)
async def test_health_no_key_is_401_even_when_enforce_off(monkeypatch):
    monkeypatch.setenv("RAG_API_AUTH_ENFORCE", "true")  # 開著也一樣 401：這兩端點不看它
    req = _FakeRequest(headers={}, db_pool=None)
    with pytest.raises(HTTPException) as e:
        await agent.agent_health(req)
    assert e.value.status_code == 401


@pytest.mark.req(_SPEC)
async def test_openapi_invalid_key_is_401():
    """key 存在但 pool 為 None（驗不了）⇒ `require_api_key_unconditional` 401。

    ⛔ 不 monkeypatch——這條測的是「沒 DB 時 fail-closed」，不是「router 有沒有呼叫函式」。
    """
    req = _FakeRequest(headers={"x-api-key": "whatever"}, db_pool=None)
    with pytest.raises(HTTPException) as e:
        await agent.agent_openapi(req)
    assert e.value.status_code == 401


# ════════════════════════════════════════════════════════════════════
# openapi.json：只列可見（prospect vs tenant 對照）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_openapi_prospect_cannot_see_kb_search_or_jgb2(monkeypatch):
    _bypass_key_and_vendor(monkeypatch)
    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "prospect"}',
        },
        db_pool=None,
    )
    result = await agent.agent_openapi(req)
    paths = result["paths"]
    assert "/tools/kb.get" in paths and "/tools/help.read" in paths  # 正對照組
    assert "/tools/kb.search" not in paths
    assert not any(p.startswith("/tools/jgb2.query.") for p in paths)


@pytest.mark.req(_SPEC)
async def test_openapi_tenant_can_see_kb_search(monkeypatch):
    """正對照：同一份 registry，換身分就看得到——不是 kb.search 整體壞掉。"""
    _bypass_key_and_vendor(monkeypatch)
    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "tenant"}',
        },
        db_pool=None,
    )
    result = await agent.agent_openapi(req)
    assert "/tools/kb.search" in result["paths"]
    assert "/tools/jgb2.query.bills" in result["paths"]


@pytest.mark.req(_SPEC)
async def test_openapi_missing_identity_header_is_400(monkeypatch):
    _bypass_key_and_vendor(monkeypatch)
    req = _FakeRequest(headers={"x-api-key": "k"}, db_pool=None)
    with pytest.raises(HTTPException) as e:
        await agent.agent_openapi(req)
    assert e.value.status_code == 400


# ════════════════════════════════════════════════════════════════════
# health：紅燈條件各一 ＋ pending 欄位不算紅
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_health_red_when_kb_probe_raises(monkeypatch):
    """`kb.get` 探針本身丟例外（DB 不可達等）⇒ 紅，且與 pending 欄位無關。

    ⛔ 不靠環境「剛好沒有 DB」——顯式塞一個 `getconn()` 必炸的假 pool，
    否則這條測試在真的有 DB 可連的環境會靜默通過假結論（否定結論須正對照，
    這裡就是正對照本身：故意讓它壞掉，驗證 health 真的看得見）。
    """
    _bypass_key_and_vendor(monkeypatch)

    class _BrokenPool:
        def getconn(self):
            raise RuntimeError("boom: no db in unit test")

    monkeypatch.setattr(agent, "_build_deps", lambda app: F.FacadeDeps(
        get_db_pool=lambda: None,
        get_kb_pool=lambda: _BrokenPool(),
        get_retriever=None,
        stage=F.current_stage(),
    ))
    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "tenant"}',
        },
        db_pool=None,
    )
    result = await agent.agent_health(req)
    assert result["status"] == "red"
    assert result["checks"]["tools"]["kb_get_reachable"] is False
    assert "RuntimeError" in result["checks"]["tools"]["detail"]


@pytest.mark.req(_SPEC)
async def test_health_pending_fields_do_not_cause_red(monkeypatch):
    """大綱／rules_sha 尚未落地 ⇒ `"pending"`，且**不**是紅燈觸發原因
    （只有 `tools`／`premise` 兩類會致紅，見 `services/agent/health.py`）。
    """
    _bypass_key_and_vendor(monkeypatch)

    class _FakePool:
        def getconn(self):
            class _Conn:
                def cursor(self):
                    class _Cur:
                        def execute(self, *a, **k):
                            pass

                        def fetchone(self):
                            return None

                        def close(self):
                            pass
                    return _Cur()
            return _Conn()

        def putconn(self, conn):
            pass

    monkeypatch.setattr(agent, "_build_deps", lambda app: F.FacadeDeps(
        get_db_pool=lambda: None,
        get_kb_pool=lambda: _FakePool(),
        get_retriever=None,
        stage=F.current_stage(),
    ))
    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "tenant"}',
        },
        db_pool=None,
    )
    result = await agent.agent_health(req)
    assert result["checks"]["outline_version"] == "pending"
    assert result["checks"]["rules_sha"] == "pending"
    assert result["status"] == "ok"          # kb 可達＋前提乾淨 ⇒ 不因 pending 而紅


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("stat_key,stat_value,flag", [
    ("vendor_not_in_table", 1, "vendor_not_in_table"),
    ("origin_not_allowed", 1, "origin_not_allowed"),
    ("enforce_off_with_mcp_traffic", True, "enforce_off_with_mcp_traffic"),
])
async def test_health_red_on_each_premise_flag(monkeypatch, stat_key, stat_value, flag):
    """DSP-011 前提偵測四項各一：任一非零／為真 ⇒ status=red 且列出該項。"""
    _bypass_key_and_vendor(monkeypatch)
    setattr(F._STATS, stat_key, stat_value)

    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "tenant"}',
        },
        db_pool=None,
    )
    result = await agent.agent_health(req)
    assert result["status"] == "red"
    assert flag in result["checks"]["premise"]["red_flags"]


@pytest.mark.req(_SPEC)
async def test_health_red_on_mcp_calls_by_api_key_nonempty(monkeypatch):
    """第一項：`/mcp` 有任何呼叫紀錄（含失敗記在 'unknown'）就列入 red_flags——
    這是「有流量了，去看一眼」的告警，⛔ 不是說一定出事（見 health.py docstring）。"""
    _bypass_key_and_vendor(monkeypatch)
    F.note_mcp_traffic(7)

    req = _FakeRequest(
        headers={
            "x-api-key": "k",
            "X-JGB-Identity": '{"vendor_id": 1, "session_id": "s1", "target_user": "tenant"}',
        },
        db_pool=None,
    )
    result = await agent.agent_health(req)
    assert result["status"] == "red"
    assert "mcp_calls_by_api_key" in result["checks"]["premise"]["red_flags"]


@pytest.mark.req(_SPEC)
async def test_health_mcp_sdk_field_reflects_availability():
    available, _ = F.mcp_sdk_available()
    req = _FakeRequest(headers={}, db_pool=None)
    # 走到這裡前就會 401（無 key），改直接呼叫 compute_agent_health 驗欄位語意
    from services.agent.health import compute_agent_health

    result = await compute_agent_health(
        registry=F.build_registry(F.FacadeDeps(get_db_pool=lambda: None,
                                               get_kb_pool=lambda: None,
                                               get_retriever=None)),
        get_kb_pool=lambda: None,
        stage="M0",
    )
    if available:
        assert result["checks"]["mcp_sdk"] == "ok"
    else:
        assert result["checks"]["mcp_sdk"] == "unavailable (DSP-014)"


# ════════════════════════════════════════════════════════════════════
# AST：本檔不得出現 `auth_enforced`（不變量 28）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_routers_agent_has_no_auth_enforced_reference():
    path = os.path.join(os.path.dirname(agent.__file__), "agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "auth_enforced" not in src
    # 正對照組：require_api_key_unconditional 確實有被引用（不是整段被刪空）
    assert "require_api_key_unconditional" in src
