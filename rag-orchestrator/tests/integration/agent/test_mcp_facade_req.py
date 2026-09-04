"""integration：MCP 門面兩道閘與額度落點（spec agentic-mcp-orchestration 任務 1.7）。

真測試庫 + 真 HTTP（ASGI transport）。涵蓋 tasks 1.7 指定的六案 ＋ SDK 端到端：
① `RAG_API_AUTH_ENFORCE` 關時 `/mcp` 缺 key 仍 401（不變量 28）
② Origin 三態（缺 ⇒ 過、白名單 ⇒ 過、非白名單 ⇒ 403）
③ `X-JGB-Identity` fail-closed 三型（400／403／未知 target_user ⇒ tenant）
④ 一次工具呼叫 ⇒ **恰一列** `usage_events`（不變量 31）
⑤ `session_id="backtest_…"` 在 `/mcp` 仍計額（`is_internal=false`；決策 13）
⑥ key 的 `vendor_ids=[2]` 對 header vendor 1 ⇒ 403
⑦ 以 MCP client 真的 `list_tools` ＋ `call_tool`（SDK 未裝 ⇒ skip，見下）

⚠️ **⑦ 目前必然 skip**：2026-09-04 實查 `mcp==2.1.1` 與 `fastapi==0.104.1`
相依衝突（`pip install --dry-run 'fastapi==0.104.1' 'mcp==2.1.1'` ⇒
ResolutionImpossible：anyio<4 vs anyio>=4.9），正式 image 未裝 SDK。
詳見 `rag-orchestrator/requirements.txt` 的說明區塊——這是待業主裁決的相依升級，
⛔ 不得以「skip 了就算過」帶過。①–⑥ 不依賴 SDK，全部實跑。

清理：本檔寫入的 `api_keys`／`usage_events` 列一律在 finally 依名稱／session 前綴刪除；
開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import asyncio
import os
import uuid

import pytest

from services.agent import mcp_facade as F
from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.api_key_auth import _reset_agent_scope_detection, hash_key

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:1.7"

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260904_api_keys_agent_scope.sql",
)

_KEY_NAME = "test-mcp-facade-1-7"
_KEY_NAME_SCOPED = "test-mcp-facade-1-7-scoped"
_PLAIN_KEY = "mcp-facade-integration-plain-key"
_PLAIN_KEY_SCOPED = "mcp-facade-integration-scoped-key"
_SESSION_PREFIX = "backtest_mcp17_"

VENDOR_OK = 1          # 存在於 vendors
VENDOR_SCOPED = 2      # 存在於 vendors；scoped key 只准這個
VENDOR_MISSING = 424242  # 不在 vendors


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg

    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=4)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"測試 DB 不可達（{type(e).__name__}）→ MCP 門面整合測試未驗")
        return

    with open(_MIGRATION, encoding="utf-8") as f:
        await p.execute(f.read())
    _reset_agent_scope_detection()

    # 正對照組：vendors 必須有 1 與 2，否則後面「vendor 不存在 ⇒ 403」證明不了東西
    present = await p.fetchval(
        "SELECT count(*) FROM vendors WHERE id = ANY($1::int[])", [VENDOR_OK, VENDOR_SCOPED])
    if present != 2:
        pytest.skip(f"[env] 測試庫 vendors 缺 {VENDOR_OK}／{VENDOR_SCOPED}（實得 {present}）")
    assert not await p.fetchval("SELECT 1 FROM vendors WHERE id = $1", VENDOR_MISSING), \
        f"vendor {VENDOR_MISSING} 竟然存在——本測試的「不存在」前提已破"

    await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                    [_KEY_NAME, _KEY_NAME_SCOPED])
    await p.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
        " VALUES ($1,$2,$3,TRUE,FALSE,NULL)",
        _KEY_NAME, hash_key(_PLAIN_KEY), _PLAIN_KEY[:8])
    await p.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
        " VALUES ($1,$2,$3,TRUE,FALSE,$4::int[])",
        _KEY_NAME_SCOPED, hash_key(_PLAIN_KEY_SCOPED), _PLAIN_KEY_SCOPED[:8], [VENDOR_SCOPED])

    try:
        yield p
    finally:
        await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                        [_KEY_NAME, _KEY_NAME_SCOPED])
        await p.execute("DELETE FROM usage_events WHERE session_id LIKE $1",
                        _SESSION_PREFIX + "%")
        await p.close()
        _reset_agent_scope_detection()


# ════════════════════════════════════════════════════════════════════
# 受測 app：逐字鏡射 app.py 對 /mcp 的兩件事（服務層閘 ＋ 額度短路）
# ════════════════════════════════════════════════════════════════════
def _build_app(pool):
    """與 `app.py` 同構的最小 app。

    ⚠️ 刻意**不**啟動整個 `app.py`：那會連帶初始化 embedding／semantic-model／
    OpenAI 等外部相依，讓「閘有沒有生效」的結論被無關的環境問題淹掉。
    這裡鏡射的是 app.py 裡與 `/mcp` 有關的兩段：`McpServiceGate`（最外層）
    與 `usage_metering_middleware` 的 `/mcp` 額度短路。
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI()
    app.state.db_pool = pool

    # ⚠️ 路由掛在 `"/mcp/"`（帶尾斜線）而測試一律 POST `"/mcp"`：production 把
    #    MCP 子 app `Mount("/mcp", …)` 上去後，實際命中的就是 `/mcp/`，
    #    而 `McpServiceGate` 會把 `/mcp` 改寫成 `/mcp/`（否則外層 router 會 307，
    #    MCP client 不跟隨轉址而握手失敗）。這樣寫等於順便驗那段改寫。
    @app.post("/mcp/")
    async def _echo(request: Request):
        call = getattr(request.state, "mcp_call", None)
        assert call is not None, "過了閘卻沒有 mcp_call——scope['state'] 傳遞壞了"
        return {
            "vendor_id": call.identity.vendor_id,
            "target_user": call.identity.target_user,
            "mode": call.identity.mode,
            "session_id": call.identity.session_id,
            "api_key_id": call.api_key_id,
            "is_internal": call.is_internal,
        }

    @app.middleware("http")
    async def _metering(request: Request, call_next):
        from services import usage_metering as _um
        if request.url.path.startswith("/mcp"):
            _mcp_call = getattr(request.state, "mcp_call", None)
            if _mcp_call is not None and _um.is_enabled():
                _qs = await _um.quota_check(pool, _mcp_call.identity.vendor_id,
                                            _mcp_call.is_internal)
                if _qs.state == "blocked":
                    return JSONResponse(status_code=429,
                                        content={"detail": "QUOTA_EXCEEDED",
                                                 "code": "QUOTA_EXCEEDED"})
            return await call_next(request)
        return await call_next(request)

    app.add_middleware(F.McpServiceGate, get_pool=lambda: pool)
    return app


def _client(app):
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                             base_url="http://mcp-test")


def _ident(vendor_id=VENDOR_OK, session_id="s1", **extra):
    import json

    payload = {"vendor_id": vendor_id, "session_id": session_id}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# ① enforce 關時 /mcp 缺 key 仍 401
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_mcp_requires_api_key_even_when_enforce_flag_is_off(pool, monkeypatch):
    monkeypatch.delenv("RAG_API_AUTH_ENFORCE", raising=False)
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    app = _build_app(pool)
    async with _client(app) as c:
        r = await c.post("/mcp", headers={"X-JGB-Identity": _ident()})
        assert r.status_code == 401, r.text
        assert r.json()["code"] == F.ERR_API_KEY

        r = await c.post("/mcp", headers={"X-API-Key": "wrong", "X-JGB-Identity": _ident()})
        assert r.status_code == 401

        # 正對照組：帶對 key 就過（否則上面兩行可能只是 app 整個壞了）
        r = await c.post("/mcp", headers={"X-API-Key": _PLAIN_KEY,
                                          "X-JGB-Identity": _ident()})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════════════
# ② Origin 三態
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_origin_three_states_over_http(pool, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://panel.example")
    app = _build_app(pool)
    base = {"X-API-Key": _PLAIN_KEY, "X-JGB-Identity": _ident()}
    async with _client(app) as c:
        assert (await c.post("/mcp", headers=base)).status_code == 200          # 缺 Origin
        assert (await c.post("/mcp", headers={**base, "Origin": "https://panel.example"})
                ).status_code == 200                                            # 白名單
        bad = await c.post("/mcp", headers={**base, "Origin": "https://evil.example"})
        assert bad.status_code == 403 and bad.json()["code"] == F.ERR_ORIGIN     # 非白名單


@pytest.mark.req(_SPEC)
async def test_empty_origin_set_still_allows_missing_origin(pool, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    app = _build_app(pool)
    base = {"X-API-Key": _PLAIN_KEY, "X-JGB-Identity": _ident()}
    async with _client(app) as c:
        assert (await c.post("/mcp", headers=base)).status_code == 200
        assert (await c.post("/mcp", headers={**base, "Origin": "https://panel.example"})
                ).status_code == 403


# ════════════════════════════════════════════════════════════════════
# ③ header fail-closed 三型
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_identity_header_fail_closed_over_http(pool, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    F.reset_premise_stats()
    app = _build_app(pool)
    async with _client(app) as c:
        malformed = await c.post("/mcp", headers={"X-API-Key": _PLAIN_KEY,
                                                  "X-JGB-Identity": "{oops"})
        assert malformed.status_code == 400
        assert malformed.json()["code"] == F.ERR_IDENTITY_MALFORMED

        no_session = await c.post("/mcp", headers={
            "X-API-Key": _PLAIN_KEY, "X-JGB-Identity": '{"vendor_id": 1}'})
        assert no_session.status_code == 400
        assert no_session.json()["code"] == F.ERR_IDENTITY_NO_SESSION

        unknown_vendor = await c.post("/mcp", headers={
            "X-API-Key": _PLAIN_KEY, "X-JGB-Identity": _ident(vendor_id=VENDOR_MISSING)})
        assert unknown_vendor.status_code == 403
        assert unknown_vendor.json()["code"] == F.ERR_VENDOR_UNKNOWN

        normalized = await c.post("/mcp", headers={
            "X-API-Key": _PLAIN_KEY,
            "X-JGB-Identity": _ident(target_user="who-am-i", mode="nonsense")})
        assert normalized.status_code == 200
        assert normalized.json()["target_user"] == "tenant"
        assert normalized.json()["mode"] == "b2c"

    stats = F.premise_stats()
    assert stats["vendor_not_in_table"] == 1
    assert stats["enforce_off_with_mcp_traffic"] is True or F._enforce_flag_is_on()


# ════════════════════════════════════════════════════════════════════
# ⑥ key 綁 vendor 錯配
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_key_vendor_scope_mismatch_is_403_over_http(pool, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    app = _build_app(pool)
    async with _client(app) as c:
        mismatch = await c.post("/mcp", headers={
            "X-API-Key": _PLAIN_KEY_SCOPED, "X-JGB-Identity": _ident(vendor_id=VENDOR_OK)})
        assert mismatch.status_code == 403
        assert mismatch.json()["code"] == F.ERR_VENDOR_OUT_OF_KEY_SCOPE

        # 正對照組：同一把 key 對它被授權的 vendor 必須放行
        ok = await c.post("/mcp", headers={
            "X-API-Key": _PLAIN_KEY_SCOPED, "X-JGB-Identity": _ident(vendor_id=VENDOR_SCOPED)})
        assert ok.status_code == 200 and ok.json()["vendor_id"] == VENDOR_SCOPED

        # 不限 vendor 的 key（vendor_ids IS NULL）對兩個 vendor 都放行
        for vid in (VENDOR_OK, VENDOR_SCOPED):
            r = await c.post("/mcp", headers={"X-API-Key": _PLAIN_KEY,
                                              "X-JGB-Identity": _ident(vendor_id=vid)})
            assert r.status_code == 200


# ════════════════════════════════════════════════════════════════════
# ④⑤ 額度落點：一呼叫一列；backtest_ 前綴仍計額
# ════════════════════════════════════════════════════════════════════
async def _count_events(pool, session_id):
    return await pool.fetchval(
        "SELECT count(*) FROM usage_events WHERE session_id = $1", session_id)


async def _wait_for_events(pool, session_id, expected, timeout_s=8.0):
    """`finalize` 是 fire-and-forget（create_task）⇒ 輪詢等它落地。"""
    deadline = asyncio.get_event_loop().time() + timeout_s
    n = 0
    while asyncio.get_event_loop().time() < deadline:
        n = await _count_events(pool, session_id)
        if n >= expected:
            break
        await asyncio.sleep(0.15)
    # 再等一小段，確認**沒有第二列**偷偷落地（不變量 31 要的是「恰一列」）
    await asyncio.sleep(0.5)
    return await _count_events(pool, session_id)


class _FakeCtx:
    """MCP `Context` 的最小替身：門面只用到 `.headers`（見 mcp_facade 的 SDK 用法）。"""

    def __init__(self, headers):
        self.headers = headers


def _stub_registry():
    """⚠️ 2026-09-04（任務 1.7b）加回 `kb.search`：⑦ 過去恆 skip（SDK 未裝），
    這支替身一直只註冊了 `kb.get`——SDK 裝上後才第一次真的跑到，才發現
    `test_real_mcp_client_lists_and_calls_tools` 的 tenant 斷言
    （`names == {"kb.get", "kb.search"}`）與 prospect 斷言（`call_tool("kb.search")`
    應被拒）都預期 `kb.search` 存在。這是替身遺漏，不是斷言錯——照
    `services/agent/tools/kb.py` 的 `KB_SEARCH_SPEC` 補上（prospect 缺鍵＝
    design 決策 3：prospect 不用向量檢索）。
    """
    reg = ToolRegistry()
    spec = {
        "name": "kb.get",
        "description": "stub",
        "input_schema": {"type": "object", "properties": {"kb_id": {"type": "string"}},
                         "required": ["kb_id"], "additionalProperties": False},
        "scope": "read",
        "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
    }
    search_spec = {
        "name": "kb.search",
        "description": "stub",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"},
                           "k": {"type": "integer", "minimum": 1, "maximum": 5}},
            "required": ["query", "k"], "additionalProperties": False,
        },
        "scope": "read",
        # prospect 缺鍵＝永不可見（同 KB_SEARCH_SPEC，design 決策 3）。
        "stage": {"property_manager": "M0", "tenant": "M0"},
    }

    async def _fn(identity: Identity, args: dict) -> ToolResult:
        return ToolResult(ok=True, data={"id": args["kb_id"]}, text_for_model="x")

    async def _search_fn(identity: Identity, args: dict) -> ToolResult:
        return ToolResult(ok=True, data=[], text_for_model="x")

    reg.register(spec, _fn)
    reg.register(search_spec, _search_fn)
    return reg


@pytest.mark.req(_SPEC)
async def test_one_tool_call_writes_exactly_one_usage_event(pool, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    assert await _count_events(pool, session_id) == 0, "起跑前該 session 就有事件——區間不乾淨"

    deps = F.FacadeDeps(get_db_pool=lambda: pool)
    invoke = F._make_invoke(_stub_registry(), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY, "x-jgb-identity": _ident(session_id=session_id)})

    out = await invoke("kb.get", ctx, {"kb_id": "1"})
    assert out == {"id": "1"}

    assert await _wait_for_events(pool, session_id, 1) == 1


@pytest.mark.req(_SPEC)
async def test_failed_tool_call_also_writes_exactly_one_event(pool, monkeypatch):
    """NO_MATCH 也要留一列——否則「查不到」的呼叫就變成免費的探測管道。"""
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]

    deps = F.FacadeDeps(get_db_pool=lambda: pool)
    invoke = F._make_invoke(_stub_registry(), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY, "x-jgb-identity": _ident(session_id=session_id)})

    with pytest.raises(Exception) as e:      # 未註冊的工具名 ⇒ NO_MATCH ⇒ ToolError
        await invoke("jgb2.query.bills", ctx, {"face": "帳單診斷"})
    assert str(e.value) == "NO_MATCH", "ToolError 訊息 ⛔ 只能含業務代碼"

    assert await _wait_for_events(pool, session_id, 1) == 1


@pytest.mark.req(_SPEC)
async def test_backtest_session_prefix_is_still_metered_on_mcp(pool, monkeypatch):
    """決策 13：`/mcp` 的 is_internal 由 **API key 紀錄**決定，
    ⛔ 不由呼叫方自己取的 `session_id` 前綴決定（否則額度可被自己關掉）。"""
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    assert session_id.startswith("backtest_"), "本測試的前提就是這個前綴"

    deps = F.FacadeDeps(get_db_pool=lambda: pool)
    invoke = F._make_invoke(_stub_registry(), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY, "x-jgb-identity": _ident(session_id=session_id)})
    await invoke("kb.get", ctx, {"kb_id": "1"})
    assert await _wait_for_events(pool, session_id, 1) == 1

    row = await pool.fetchrow(
        "SELECT is_internal, internal_kind, vendor_id, channel, processing_path "
        "FROM usage_events WHERE session_id = $1", session_id)
    assert row["is_internal"] is False, "backtest_ 前綴不得讓 /mcp 流量變成免額度"
    assert row["internal_kind"] is None
    assert row["vendor_id"] == VENDOR_OK
    assert row["channel"] == "mcp"
    assert row["processing_path"] == "mcp:kb.get"


@pytest.mark.req(_SPEC)
async def test_internal_api_key_marks_traffic_internal(pool, monkeypatch):
    """反對照：同一個 session 前綴，改用 `is_internal=true` 的 key 才會標內部。"""
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    await pool.execute("UPDATE api_keys SET is_internal = TRUE WHERE name = $1", _KEY_NAME)
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    try:
        deps = F.FacadeDeps(get_db_pool=lambda: pool)
        invoke = F._make_invoke(_stub_registry(), deps)
        ctx = _FakeCtx({"x-api-key": _PLAIN_KEY,
                        "x-jgb-identity": _ident(session_id=session_id)})
        await invoke("kb.get", ctx, {"kb_id": "1"})
        assert await _wait_for_events(pool, session_id, 1) == 1
        row = await pool.fetchrow(
            "SELECT is_internal, internal_kind FROM usage_events WHERE session_id = $1",
            session_id)
        assert row["is_internal"] is True and row["internal_kind"] == "api_key"
    finally:
        await pool.execute("UPDATE api_keys SET is_internal = FALSE WHERE name = $1", _KEY_NAME)


@pytest.mark.req(_SPEC)
async def test_metering_disabled_refuses_service(pool, monkeypatch):
    """計量關掉 ⇒ 拒絕服務（⛔ 不靜默略過）：額度是本系統唯一的控制。"""
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    monkeypatch.setenv("USAGE_METERING_ENABLED", "false")
    F.reset_premise_stats()
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]

    deps = F.FacadeDeps(get_db_pool=lambda: pool)
    invoke = F._make_invoke(_stub_registry(), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY, "x-jgb-identity": _ident(session_id=session_id)})
    with pytest.raises(Exception) as e:
        await invoke("kb.get", ctx, {"kb_id": "1"})
    assert str(e.value) == F.ERR_METERING
    assert F.premise_stats()["metering_unavailable"] == 1


@pytest.mark.req(_SPEC)
async def test_verify_api_key_returns_agent_scope_columns(pool):
    from services.api_key_auth import verify_api_key

    row = await verify_api_key(pool, _PLAIN_KEY_SCOPED)
    assert row is not None
    assert set(row) == {"id", "name", "is_internal", "vendor_ids"}
    assert row["is_internal"] is False
    assert row["vendor_ids"] == [VENDOR_SCOPED]
    # 正對照組：不限 vendor 的 key 回 None（⛔ 不是空 list）
    assert (await verify_api_key(pool, _PLAIN_KEY))["vendor_ids"] is None


# ════════════════════════════════════════════════════════════════════
# ⑦ 真 MCP client（SDK 未裝 ⇒ skip，理由見檔頭）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_real_mcp_client_lists_and_calls_tools(pool, monkeypatch):
    """真 MCP client 走完 initialize → tools/list → tools/call，並驗身分過濾。

    ⚠️ 這段的形狀已在**裝了 SDK 的獨立 image** 實跑驗證過（見檔頭）：
    `/mcp` 401／403、tenant 看得到 `kb.search`、prospect 看不到、
    `call_tool` 回 structured result、`usage_events` 一呼叫一列。
    ⛔ 但那個 image 的 fastapi／starlette／pydantic 與 production 不同，
    故**不當作 production 綠**；本測試在 production 相依裝上 SDK 後才會真的跑。
    """
    available, reason = F.mcp_sdk_available()
    if not available:
        pytest.skip(
            f"[env] MCP SDK 未安裝（{reason}）——mcp==2.1.1 與 fastapi==0.104.1 相依衝突"
            "（anyio<4 vs anyio>=4.9），待業主裁決是否升 fastapi；見 requirements.txt")

    import uvicorn
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    from starlette.applications import Starlette
    from starlette.routing import Mount

    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    session_id = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    deps = F.FacadeDeps(get_db_pool=lambda: pool)
    server = F.build_mcp_server(_stub_registry(), deps)
    inner = Starlette(routes=[Mount("/mcp", app=F.build_asgi_app(server))])
    app = F.McpServiceGate(inner, get_pool=lambda: pool)

    async with server.session_manager.run():
        # ⚠️ uvicorn 跑在**同一個 event loop**：另開執行緒會讓 asyncpg pool 跨 loop
        #    （"attached to a different loop"），那是測試缺陷不是產品缺陷。
        config = uvicorn.Config(app, host="127.0.0.1", port=8899, log_level="warning")
        uv = uvicorn.Server(config)
        serve_task = asyncio.create_task(uv.serve())
        try:
            for _ in range(200):
                if uv.started:
                    break
                await asyncio.sleep(0.05)
            base = "http://127.0.0.1:8899/mcp"

            import httpx2

            http = httpx2.AsyncClient(headers={
                "X-API-Key": _PLAIN_KEY,
                "X-JGB-Identity": _ident(session_id=session_id, target_user="tenant")})
            async with Client(streamable_http_client(base, http_client=http),
                              raise_exceptions=True) as client:
                names = {t.name for t in (await client.list_tools()).tools}
                assert names == {"kb.get", "kb.search"}
                result = await client.call_tool("kb.get", {"kb_id": "1"})
                assert result.is_error is False
            await http.aclose()

            # prospect：`kb.search` 既不在清單、呼叫也拒（design 決策 3）
            http2 = httpx2.AsyncClient(headers={
                "X-API-Key": _PLAIN_KEY,
                "X-JGB-Identity": _ident(session_id=session_id + "p",
                                         target_user="prospect")})
            async with Client(streamable_http_client(base, http_client=http2),
                              raise_exceptions=True) as client:
                names = {t.name for t in (await client.list_tools()).tools}
                assert names == {"kb.get"}
                denied = await client.call_tool("kb.search", {"query": "x"})
                assert denied.is_error is True
            await http2.aclose()

            assert await _wait_for_events(pool, session_id, 1) == 1
        finally:
            uv.should_exit = True
            await serve_task
