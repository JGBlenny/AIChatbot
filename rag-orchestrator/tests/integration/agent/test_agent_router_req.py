"""integration：`/api/v1/agent/openapi.json`・`/api/v1/agent/health`
（spec agentic-mcp-orchestration・任務 1.8）。

真測試庫 + 真 HTTP（ASGI transport，`TestClient` 起 app）。⛔ 不起整個 `app.py`
（會連帶初始化 embedding／semantic-model／OpenAI 等外部相依，讓「這兩個端點
有沒有生效」的結論被無關的環境問題淹掉）——鏡射 `test_mcp_facade_req.py` 的
做法：只掛 `routers.agent.router`，`app.state.db_pool` 指向測試庫的真 pool。

涵蓋：
① `openapi.json` 實打一次：真的帶 `X-API-Key` ＋ `X-JGB-Identity`，200，
   `paths` 含預期工具。
② `health` 實打一次：200（HTTP 一律 200，紅以 body 表達），body 形狀正確、
   `checks.tools.spec_count > 0`。
③ `agent_boundary.py` 不變量 28 仍綠（`routers/agent.py` 已存在後才有意義驗）。

無 DB ⇒ skip（同構 `test_mcp_facade_req.py` 的 `pool` fixture）。
"""
import os

import pytest

from services.agent import mcp_facade as F
from services.api_key_auth import _reset_agent_scope_detection, hash_key

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:1.8"

_KEY_NAME = "test-agent-router-1-8"
_PLAIN_KEY = "agent-router-integration-plain-key"

VENDOR_OK = 1


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
        pytest.skip(f"測試 DB 不可達（{type(e).__name__}）→ agent router 整合測試未驗")
        return

    # 正對照組：VENDOR_OK 必須存在，否則後面的 200 案例證明不了東西
    present = await p.fetchval("SELECT count(*) FROM vendors WHERE id = $1", VENDOR_OK)
    if not present:
        pytest.skip(f"[env] 測試庫 vendors 缺 {VENDOR_OK}")

    _reset_agent_scope_detection()
    await p.execute("DELETE FROM api_keys WHERE name = $1", _KEY_NAME)
    await p.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
        " VALUES ($1,$2,$3,TRUE,FALSE,NULL)",
        _KEY_NAME, hash_key(_PLAIN_KEY), _PLAIN_KEY[:8])
    try:
        yield p
    finally:
        await p.execute("DELETE FROM api_keys WHERE name = $1", _KEY_NAME)
        await p.close()
        _reset_agent_scope_detection()


def _build_app(pool):
    from fastapi import FastAPI

    from routers import agent as agent_router

    agent_router.reset_registry_cache()
    app = FastAPI()
    app.state.db_pool = pool
    app.include_router(agent_router.router)
    return app


def _client(app):
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                             base_url="http://agent-router-test")


def _ident(vendor_id=VENDOR_OK, session_id="s1", **extra):
    import json

    payload = {"vendor_id": vendor_id, "session_id": session_id}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# ① openapi.json 實打
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_openapi_endpoint_over_http(pool):
    app = _build_app(pool)
    async with _client(app) as c:
        # 正對照：先確認缺 key 仍 401（否則下面的 200 可能只是 app 沒掛認證）
        r = await c.get("/api/v1/agent/openapi.json",
                        headers={"X-JGB-Identity": _ident()})
        assert r.status_code == 401

        r = await c.get(
            "/api/v1/agent/openapi.json",
            headers={"X-API-Key": _PLAIN_KEY,
                     "X-JGB-Identity": _ident(target_user="tenant")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "/tools/kb.get" in body["paths"]
        assert "/tools/kb.search" in body["paths"]        # tenant 可見（正對照）


@pytest.mark.req(_SPEC)
async def test_openapi_prospect_excludes_kb_search_over_http(pool):
    app = _build_app(pool)
    async with _client(app) as c:
        r = await c.get(
            "/api/v1/agent/openapi.json",
            headers={"X-API-Key": _PLAIN_KEY,
                     "X-JGB-Identity": _ident(target_user="prospect")},
        )
        assert r.status_code == 200, r.text
        paths = r.json()["paths"]
        assert "/tools/kb.get" in paths                    # 正對照
        assert "/tools/kb.search" not in paths
        assert not any(p.startswith("/tools/jgb2.query.") for p in paths)


# ════════════════════════════════════════════════════════════════════
# ② health 實打
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_health_endpoint_over_http(pool):
    app = _build_app(pool)
    async with _client(app) as c:
        r = await c.get("/api/v1/agent/health")
        assert r.status_code == 401                        # 正對照：缺 key

        r = await c.get("/api/v1/agent/health", headers={"X-API-Key": _PLAIN_KEY})
        assert r.status_code == 200, r.text                # HTTP 一律 200
        body = r.json()
        assert body["status"] in ("ok", "red")
        assert body["checks"]["tools"]["spec_count"] > 0
        assert body["checks"]["outline_version"] == "pending"
        assert body["checks"]["rules_sha"] == "pending"
        assert "red_flags" in body["checks"]["premise"]


# ════════════════════════════════════════════════════════════════════
# ③ agent_boundary.py 不變量 28 仍綠
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_invariant_28_still_green_with_agent_router_present():
    import importlib.util

    repo_root = os.path.dirname(  # rag-orchestrator/
        os.path.dirname(  # tests/
            os.path.dirname(  # tests/integration/
                os.path.dirname(os.path.abspath(__file__))  # tests/integration/agent/
            )
        )
    )
    checker_py = os.path.join(os.path.dirname(repo_root), "scripts", "audit",
                              "checks", "agent_boundary.py")
    assert os.path.exists(checker_py), f"{checker_py} 不存在——盤查腳本位置變了"
    spec = importlib.util.spec_from_file_location("agent_boundary_checker_1_8", checker_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ok, msg = mod.check_28_mcp_auth_unconditional()
    assert ok, msg
    assert "routers/agent.py" not in msg or "尚未建立" not in msg  # 檔案應已被掃到而非略過
