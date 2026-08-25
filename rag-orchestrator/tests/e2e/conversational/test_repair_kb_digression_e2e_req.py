"""e2e：修繕面向岔題查知識庫（brain-kb-grounding 任務 4.1｜R3.1/3.2/5.2/6.1）。

TestClient(app) 走正常管線（真 LLM），驗證交易面向（修繕）對話中的知識性岔題
會經 search_kb 工具查庫再答（而非憑印象），並埋點 search_kb_status：
  - 有命中/無命中：進面向後問費用（岔題）→ 回應含答案且對話續行（先答再接，R3.1）；
    usage_events.search_kb_status 於岔題輪為 'hit' 或 'miss'（R5.2），非 NULL。
  - 診斷面向零回歸由 unit（None 路徑逐位一致）＋既有五域診斷 e2e 保證，本檔不重複。

真 LLM → 斷言限「行為級不變式」（岔題被回答/對話續行/埋點落地），不逐字比對文案，
也不硬性要求 'hit'（知識可能未 seed；'miss' 亦為合法誠實回退，仍證明工具被呼叫）。
需 RUN_E2E=1 ＋ 整服務（DB/embedding/semantic-model/OPENAI）＋ USE_MOCK_JGB_API=true。
"""
import asyncio
import os

import pytest

pytestmark = pytest.mark.e2e

VENDOR_ID = int(os.getenv("TEST_REPAIR_VENDOR_ID", "1"))
ROLE_ID = os.getenv("TEST_REPAIR_ROLE_ID", "R001")
USER_ID = os.getenv("TEST_REPAIR_USER_ID", "9001")    # fixture 678 的 to_user_id（租約預填）


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def _require_repair_facet():
    if os.getenv("USE_MOCK_JGB_API", "").lower() != "true":
        pytest.skip("需 USE_MOCK_JGB_API=true（開發以 mock 驗流程）")

    async def _check():
        import asyncpg
        from services.conversational_config import config_for_category, reset_cache
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        try:
            return await config_for_category(pool, "修繕報修")
        finally:
            await pool.close()
    try:
        cfg = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查修繕面向設定：{e}")
    if cfg is None:
        pytest.skip("修繕面向設定未就緒；請套用面向配置＋錨點知識 seeds")


def _post(client, message, sid, *, trigger_facet_key=None):
    body = {"message": message, "vendor_id": VENDOR_ID, "target_user": "tenant", "mode": "b2c",
            "role_id": ROLE_ID, "user_id": USER_ID, "session_id": sid, "stream": False}
    if trigger_facet_key:
        body["trigger_facet_key"] = trigger_facet_key
    r = client.post("/api/v1/message", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _search_kb_statuses(sid):
    """該 session 所有 usage_events 的 search_kb_status（非 NULL 者＝岔題輪呼叫過工具）。"""
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            rows = await conn.fetch(
                "SELECT search_kb_status FROM usage_events "
                "WHERE session_id=$1 AND search_kb_status IS NOT NULL", sid)
            return [r["search_kb_status"] for r in rows]
        finally:
            await conn.close()
    return asyncio.run(_q())


def _cleanup(sid):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
            await conn.execute("DELETE FROM usage_events WHERE session_id=$1", sid)
        finally:
            await conn.close()
    try:
        asyncio.run(_d())
    except Exception:
        pass


# ── 岔題查庫：進面向 → 問費用（岔題）→ 回應含答案且對話續行；埋點 search_kb_status 落地 ──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_repair_digression_invokes_search_kb(client):
    import time
    sid = f"e2e_kbdigress_{int(time.time())}"
    try:
        # 進面向（直達參數，跳意圖辨識）
        r1 = _post(client, "馬桶不通要報修", sid, trigger_facet_key="repair_create")
        assert (r1.get("answer") or "").strip()      # 進面向、有回應
        # 岔題：問費用（事實性問題 → Brain 應呼叫 search_kb）
        r2 = _post(client, "這個修理要收費嗎", sid)
        ans = (r2.get("answer") or "").strip()
        assert ans                                    # 岔題被回答（先答，R3.1）
        # 埋點：岔題輪 search_kb_status 非 NULL（工具被呼叫），值為 hit 或 miss（R5.2）
        statuses = _search_kb_statuses(sid)
        assert statuses, "岔題輪應有 search_kb_status 埋點（工具被呼叫）"
        assert all(s in ("hit", "miss") for s in statuses)
    finally:
        _cleanup(sid)
