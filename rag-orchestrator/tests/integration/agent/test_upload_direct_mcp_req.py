"""integration：瀏覽器直傳附件走**真 `/mcp` client ＋真 HTTP 上傳**（UD-1 A2）。

一個 uvicorn（真 socket）同時掛：
  - `/mcp`：真 MCP server（`build_mcp_server`），註冊 `agent.upload_ticket` 與 `agent.turn`；
  - `POST /api/v1/agent/uploads`：真上傳路由；
  - 外層：真 `McpServiceGate(exempt_upload=True)`（真測試庫的 `api_keys`）。

驗（A2）：
  ① 缺 `user_id` 取票被拒（S7）；有 `user_id` ⇒ 回傳欄位與契約一致。
  ② `upload_id` 綁定：key、vendor、user、role、session、用途，任一不同 ⇒
     `agent.turn` 整回合 `INVALID_INPUT`，訊息點名是哪一個 `upload_ids[i]`，且**不消耗**；
     正確身分 ⇒ 成功；同一個再用 ⇒ `INVALID_INPUT`（單次）。
  ③ 三種刪除時機：document 在引用回合結束即刪；repair 保留到 `release`（UD-3 接卡）；
     未引用者 30 分鐘後刪（保留中的最長也 30 分鐘）。
  ④ 真 socket 對照：同前綴 `/api/v1/agent/trace` 無金鑰仍 401（A1(b) 正對照）；
     `https://evil.example` 預檢無 ACAO（A1(e)）。

只有 LLM／辨識／擷取是假的（⛔ 呼叫真 OpenAI）。
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import uuid
from io import BytesIO

import httpx
import pytest
from PIL import Image

from routers import agent_uploads
from services.agent import image_fetch
from services.agent import mcp_facade as F
from services.agent import upload_store as US
from services.agent.tools.registry import ToolRegistry
from services.api_key_auth import _reset_agent_scope_detection, hash_key

from tests.integration.agent.test_agent_turn_req import (
    _MIGRATION,
    _MIGRATION_TOKENS,
    _MIGRATION_TOKENS_PENDING_ID,
    _agent_output,
    _app,
    _conn_kwargs,
    _deps,
    _fake_response,
    _make_runtime,
)
from tests.unit.agent.test_document_turn_req import FakeExtractor, _bill_result, _synth_pdf
from tests.unit.agent.test_image_entry_req import FakeRecognizer, _recognition

pytestmark = pytest.mark.integration

_REQ = "agentic-mcp-orchestration:UD-1"

_PORT = 8913
ORIGIN = "https://www.jgbsmart.com"
PUBLIC_URL = "https://chatai.jgbsmart.com/rag-api/v1/agent/uploads"

_KEY_NAME_A = "test-upload-direct-ud1-key-a"
_KEY_NAME_B = "test-upload-direct-ud1-key-b"
_PLAIN_KEY_A = "upload-direct-ud1-integration-key-a"     # vendor 1 與 2
_PLAIN_KEY_B = "upload-direct-ud1-integration-key-b"     # vendor 1
_SESSION_PREFIX = "backtest_uploadud1_"
_ROW_PREFIX = "mcp:"

VENDOR_A = 1
VENDOR_B = 2


# ════════════════════════════════════════════════════════════════════
# 測試庫與環境
# ════════════════════════════════════════════════════════════════════
@pytest.fixture
async def pool():
    import asyncpg

    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=4)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"測試 DB 不可達（{type(e).__name__}）→ 直傳整合測試未驗")
        return
    for migration in (_MIGRATION, _MIGRATION_TOKENS, _MIGRATION_TOKENS_PENDING_ID):
        with open(migration, encoding="utf-8") as f:
            await p.execute(f.read())
    _reset_agent_scope_detection()
    present = await p.fetchval(
        "SELECT count(*) FROM vendors WHERE id = ANY($1::int[])", [VENDOR_A, VENDOR_B])
    if present != 2:
        pytest.skip(f"[env] 測試庫 vendors 缺 {VENDOR_A}／{VENDOR_B}（實得 {present}）")
    assert await p.fetchval(
        "SELECT 1 FROM form_schemas WHERE form_id = 'conversational'"), \
        "form_schemas 缺 'conversational'——`_start` 會因外鍵而失敗"

    await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                    [_KEY_NAME_A, _KEY_NAME_B])
    for name, plain, vendors in ((_KEY_NAME_A, _PLAIN_KEY_A, [VENDOR_A, VENDOR_B]),
                                 (_KEY_NAME_B, _PLAIN_KEY_B, [VENDOR_A])):
        await p.execute(
            "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
            " VALUES ($1,$2,$3,TRUE,FALSE,$4::int[])",
            name, hash_key(plain), plain[:8], vendors)
    try:
        yield p
    finally:
        await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                        [_KEY_NAME_A, _KEY_NAME_B])
        await p.execute("DELETE FROM usage_events WHERE session_id LIKE $1",
                        _SESSION_PREFIX + "%")
        await p.execute("DELETE FROM form_sessions WHERE session_id LIKE $1",
                        _ROW_PREFIX + "%" + _SESSION_PREFIX + "%")
        await p.execute("DELETE FROM agent_confirmation_tokens WHERE session_id LIKE $1",
                        _ROW_PREFIX + "%" + _SESSION_PREFIX + "%")
        await p.close()
        _reset_agent_scope_detection()


class Clock:
    def __init__(self, start=10_000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, dt):
        self.now += dt


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    monkeypatch.setenv("AGENT_STAGE", "M1")
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "30")
    monkeypatch.setenv("AGENT_TURN_CAP", "500")
    monkeypatch.setenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, ORIGIN)
    monkeypatch.setenv(US.UPLOAD_PUBLIC_URL_ENV, PUBLIC_URL)
    monkeypatch.delenv(US.ATTACHMENT_INPUT_ENV, raising=False)
    F.reset_agent_turn_cap()
    F.reset_premise_stats()
    image_fetch.reset_image_count_cap()
    image_fetch.reset_file_count_cap()
    image_fetch.reset_image_failures()
    US.STORE.reset()
    clock = Clock()
    US.STORE.set_clock(clock, wall=lambda: 1_793_184_400.0 + clock.now)
    # 辨識／擷取一律假的（⛔ 呼叫真 OpenAI）
    recognizer = FakeRecognizer([_recognition()])
    extractor = FakeExtractor(_bill_result())
    monkeypatch.setattr(F, "_image_recognize_batch", recognizer)
    monkeypatch.setattr(F, "_document_extract_pages", extractor)

    async def _no_net(url, *, timeout_s):
        raise AssertionError(f"直傳路徑 ⛔ 連網抓檔：{url}")

    monkeypatch.setattr(F, "_image_fetch_one", _no_net)
    monkeypatch.setattr(F, "_document_fetch_one", _no_net)
    yield {"clock": clock, "recognizer": recognizer, "extractor": extractor}
    US.STORE.reset()
    import time as _t
    US.STORE.set_clock(_t.monotonic, wall=_t.time)


# ════════════════════════════════════════════════════════════════════
# 真 server（MCP ＋上傳路由 ＋服務層閘）
# ════════════════════════════════════════════════════════════════════
def _registry(deps) -> ToolRegistry:
    """與 `build_registry(upload_enabled=True)` 註冊的是**同一份 spec 與同一支工具工廠**；
    只取這兩支，避免把要連 JGB 的分類樹閉包一起帶進來。"""
    reg = ToolRegistry()
    reg.register(F.UPLOAD_TICKET_SPEC, F._make_upload_ticket())
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    return reg


@contextlib.asynccontextmanager
async def _serve(pool):
    import uvicorn
    from fastapi import FastAPI

    runtime = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))] * 40)
    deps = _deps(_app(pool, runtime), pool)
    registry = _registry(deps)
    server = F.build_mcp_server(registry, deps)
    inner = FastAPI()
    inner.include_router(agent_uploads.router)
    inner.mount("/mcp", F.build_asgi_app(server))
    asgi = F.McpServiceGate(inner, get_pool=lambda: pool, exempt_upload=True)
    async with server.session_manager.run():
        uv = uvicorn.Server(uvicorn.Config(asgi, host="127.0.0.1", port=_PORT,
                                           log_level="warning"))
        task = asyncio.create_task(uv.serve())
        try:
            for _ in range(200):
                if uv.started:
                    break
                await asyncio.sleep(0.05)
            assert uv.started, "uvicorn 沒起來"
            yield f"http://127.0.0.1:{_PORT}"
        finally:
            uv.should_exit = True
            await task


def _ident(*, vendor_id=VENDOR_A, session_id, user_id="88", role_id="20151",
           target_user="prospect", mode="b2c"):
    body = {"vendor_id": vendor_id, "session_id": session_id,
            "target_user": target_user, "mode": mode, "role_id": role_id}
    if user_id is not None:
        body["user_id"] = user_id
    return json.dumps(body, ensure_ascii=False)


async def _mcp(base, key, ident, calls):
    """開一個真 MCP session，依序呼叫 `calls`（`[(name, args), ...]`）。"""
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    http = httpx2.AsyncClient(headers={"X-API-Key": key, "X-JGB-Identity": ident})
    out = []
    try:
        async with Client(streamable_http_client(base + "/mcp", http_client=http),
                          raise_exceptions=True) as client:
            for name, args in calls:
                out.append(await client.call_tool(name, args))
    finally:
        await http.aclose()
    return out


def _data(res) -> dict:
    sc = getattr(res, "structured_content", None)
    if isinstance(sc, dict):
        if set(sc) == {"result"} and isinstance(sc["result"], dict):
            return sc["result"]
        return sc
    return json.loads(res.content[0].text)


def _text(res) -> str:
    return " ".join(getattr(c, "text", "") or "" for c in (res.content or []))


def _jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 48), (100, 120, 140)).save(buf, format="JPEG")
    return buf.getvalue()


async def _http_upload(base, token, data, *, origin=ORIGIN):
    async with httpx.AsyncClient(base_url=base) as c:
        return await c.post(US.UPLOAD_PATH,
                            headers={"Origin": origin, "Authorization": f"Bearer {token}"},
                            files={"file": ("x.bin", data, "application/octet-stream")})


async def _ticket(base, *, key=_PLAIN_KEY_A, purpose="repair", **ident):
    (res,) = await _mcp(base, key, _ident(**ident),
                        [(F.UPLOAD_TICKET_NAME, {"attachment_purpose": purpose})])
    assert res.is_error is False, _text(res)
    return _data(res)


def _session():
    return _SESSION_PREFIX + uuid.uuid4().hex[:12]


def _selector(upload_id: str) -> str:
    return upload_id.split(".", 1)[0][len(US.UPLOAD_ID_PREFIX):]


# ════════════════════════════════════════════════════════════════════
# ① 取票：S7 與回傳形狀
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_ticket_over_real_mcp_requires_user_id_and_matches_contract(pool, env):
    ok, why = F.mcp_sdk_available()
    if not ok:
        pytest.skip(f"[env] MCP SDK 匯入失敗（{why}）——供裝壞了")
    session = _session()
    async with _serve(pool) as base:
        (no_user,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session, user_id=None),
                                [(F.UPLOAD_TICKET_NAME, {"attachment_purpose": "repair"})])
        assert no_user.is_error is True
        assert F.USER_ID_REQUIRED_DETAIL in _text(no_user)
        assert US.STORE.counts()["tickets"] == 0

        rep = await _ticket(base, session_id=session, purpose="repair")
        assert set(rep) == {"upload_url", "upload_token", "expires_at", "max_files",
                            "max_bytes", "accept"}
        assert rep["max_files"] == 10 and rep["max_bytes"] == 5_000_000
        assert rep["accept"] == ["image/jpeg", "image/png", "image/webp"]
        assert rep["expires_at"] == int(1_793_184_400.0 + env["clock"].now + 600)
        assert rep["upload_token"] not in rep["upload_url"]
        assert rep["upload_url"] == PUBLIC_URL
        doc = await _ticket(base, session_id=session, purpose="document")
        assert doc["max_files"] == 1
        assert doc["accept"] == ["application/pdf", "image/jpeg", "image/png"]

        # 正對照：拿到的票真的能在真 socket 上傳成功
        r = await _http_upload(base, rep["upload_token"], _jpeg())
        assert r.status_code == 201, r.text
        assert r.headers["access-control-allow-origin"] == ORIGIN


# ════════════════════════════════════════════════════════════════════
# ② 綁定矩陣（S6）＋單次使用
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_upload_id_binding_over_real_mcp(pool, env):
    session = _session()
    async with _serve(pool) as base:
        t = await _ticket(base, session_id=session)
        r = await _http_upload(base, t["upload_token"], _jpeg())
        assert r.status_code == 201, r.text
        uid = r.json()["upload_id"]
        args = {"message": "漏水", "upload_ids": [uid]}

        mismatches = {
            "key": (_PLAIN_KEY_B, _ident(session_id=session)),
            "vendor": (_PLAIN_KEY_A, _ident(session_id=session, vendor_id=VENDOR_B)),
            "user": (_PLAIN_KEY_A, _ident(session_id=session, user_id="89")),
            "role": (_PLAIN_KEY_A, _ident(session_id=session, role_id="20152")),
            "session": (_PLAIN_KEY_A, _ident(session_id=session + "x")),
            "no_user": (_PLAIN_KEY_A, _ident(session_id=session, user_id=None)),
        }
        for label, (key, ident) in mismatches.items():
            (res,) = await _mcp(base, key, ident, [(F.AGENT_TURN_NAME, args)])
            assert res.is_error is True, label
            if label == "no_user":
                assert F.USER_ID_REQUIRED_DETAIL in _text(res), _text(res)
                continue
            assert "upload_ids[0]" in _text(res), (label, _text(res))
            assert f"upl_{_selector(uid)}" in _text(res), label
            assert uid.split(".", 1)[1] not in _text(res), "⛔ 回顯 upload_id 的祕密段"

        # 用途不符（同一身分，宣告 document）
        (res,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session), [
            (F.AGENT_TURN_NAME, {"message": "幫我看", "attachment_purpose": "document",
                                 "upload_ids": [uid]})])
        assert res.is_error is True and "upload_ids[0]" in _text(res)

        assert env["recognizer"].batches == [], "被拒的回合 ⛔ 部分處理"
        assert US.STORE.counts()[US.STATE_UNREFERENCED] == 1, "被拒的回合 ⛔ 消耗 upload_id"

        # 正對照：正確身分 ⇒ 成功；同一個再用 ⇒ 無效（單次）
        ok, again = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session),
                               [(F.AGENT_TURN_NAME, args), (F.AGENT_TURN_NAME, args)])
        assert ok.is_error is False, _text(ok)
        assert len(env["recognizer"].batches) == 1
        assert again.is_error is True and "upload_ids[0]" in _text(again)


@pytest.mark.req(_REQ)
async def test_default_mode_rejects_urls_over_real_mcp(pool, env):
    """A3 經真 `/mcp`：預設 `upload_ids` 模式 ⇒ `image_urls` 整回合 `INVALID_INPUT`。"""
    session = _session()
    async with _serve(pool) as base:
        (res,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session), [
            (F.AGENT_TURN_NAME, {"message": "看照片",
                                 "image_urls": ["https://relay.jgbsmart.com/a.jpg"]})])
        assert res.is_error is True
        assert F.URL_INPUT_DISABLED_DETAIL in _text(res)
        (plain,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session),
                              [(F.AGENT_TURN_NAME, {"message": "你好"})])
        assert plain.is_error is False, _text(plain)


# ════════════════════════════════════════════════════════════════════
# ③ 三種刪除時機
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_three_deletion_timings_over_real_mcp(pool, env):
    clock = env["clock"]
    session = _session()
    async with _serve(pool) as base:
        # (a) document：引用回合結束即刪
        d = await _ticket(base, session_id=session, purpose="document")
        r = await _http_upload(base, d["upload_token"], _synth_pdf(pages=1))
        assert r.status_code == 201 and r.json()["content_type"] == "application/pdf"
        assert US.STORE.counts()["uploads"] == 1
        (res,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session), [
            (F.AGENT_TURN_NAME, {"message": "幫我看", "attachment_purpose": "document",
                                 "upload_ids": [r.json()["upload_id"]]})])
        assert res.is_error is False, _text(res)
        assert len(env["extractor"].batches) == 1
        assert US.STORE.counts()["uploads"] == 0, "document 應在引用回合結束即刪"

        # (b) repair：回合結束後保留，release（卡兌現／作廢）才刪
        t = await _ticket(base, session_id=session)
        ids = []
        for _ in range(2):
            rr = await _http_upload(base, t["upload_token"], _jpeg())
            assert rr.status_code == 201
            ids.append(rr.json()["upload_id"])
        (res,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session),
                            [(F.AGENT_TURN_NAME, {"message": "漏水", "upload_ids": ids})])
        assert res.is_error is False, _text(res)
        c = US.STORE.counts()
        assert c[US.STATE_RETAINED] == 2 and c["uploads"] == 2
        US.STORE.release([_selector(i) for i in ids])
        assert US.STORE.counts()["uploads"] == 0

        # (c) 未引用：30 分鐘後刪；保留中的最長也 30 分鐘
        t2 = await _ticket(base, session_id=session)
        idle = (await _http_upload(base, t2["upload_token"], _jpeg())).json()["upload_id"]
        kept = (await _http_upload(base, t2["upload_token"], _jpeg())).json()["upload_id"]
        (res,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session),
                            [(F.AGENT_TURN_NAME, {"message": "漏水", "upload_ids": [kept]})])
        assert res.is_error is False, _text(res)
        c = US.STORE.counts()
        assert c[US.STATE_UNREFERENCED] == 1 and c[US.STATE_RETAINED] == 1
        clock.advance(1799)
        US.STORE.sweep()
        assert US.STORE.counts()["uploads"] == 2                 # 正對照：未滿 30 分鐘
        clock.advance(2)
        US.STORE.sweep()
        assert US.STORE.counts()["uploads"] == 0, "滿 30 分鐘：未引用與保留中都應刪除"
        (late,) = await _mcp(base, _PLAIN_KEY_A, _ident(session_id=session),
                             [(F.AGENT_TURN_NAME, {"message": "漏水", "upload_ids": [idle]})])
        assert late.is_error is True and "upload_ids[0]" in _text(late)


# ════════════════════════════════════════════════════════════════════
# ④ 真 socket 對照：同前綴仍過閘、evil 預檢無 ACAO
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_gate_and_cors_over_real_socket(pool, env):
    async with _serve(pool) as base:
        async with httpx.AsyncClient(base_url=base) as c:
            trace = await c.get("/api/v1/agent/trace")
            assert trace.status_code == 401 and trace.json()["code"] == "API_KEY_REQUIRED"
            sub = await c.post(US.UPLOAD_PATH + "/x", headers={"Origin": ORIGIN})
            assert sub.status_code == 401 and sub.json()["code"] == "API_KEY_REQUIRED"
            evil = await c.options(US.UPLOAD_PATH, headers={
                "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
            assert "access-control-allow-origin" not in evil.headers
            good = await c.options(US.UPLOAD_PATH, headers={
                "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization"})
            assert good.status_code == 204
            assert good.headers["access-control-allow-origin"] == ORIGIN
            assert "access-control-allow-credentials" not in good.headers
            no_origin = await c.post(US.UPLOAD_PATH, headers={"Authorization": "Bearer x"},
                                     files={"file": ("a", _jpeg(), "image/jpeg")})
            assert no_origin.status_code == 403
            assert no_origin.json()["error_code"] == "ORIGIN_NOT_ALLOWED"
