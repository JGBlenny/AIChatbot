"""e2e:IoT 2 子面向（真管線：檢索→reranker→config_for_category→引擎→真 LLM＋真 jgb2 preview）
—— iot-conversational-facets 任務 4.2（R2.5, R5.2, R6.2, R9.3）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線：
  - 兩面向口語第一句進場；機制 token（每小時/自動復電/台科電）不被改寫；
  - 不代操作（回答給指路不代執行）；進對話 vs 單發各一例；跨域 switch。
  - **真電表多輪 gated（J-I0）**：/meters type 過濾 bug 致 preview 恆回空——
    本檔驗降級態（查無電表→誠實追問/降級不阻斷、不虛構）；J-I0 修復後以
    role 37305 補真資料分支驗證（任務 6.1*）。

需 RUN_E2E=1 ＋ 整服務。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_IOT_ROLE_ID", "37305")      # 有 DAE 綁定的業者（J-I0 修復後有電表）
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")


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
def _require_facet_configs():
    async def _check():
        import asyncpg
        from services.conversational_config import config_for_category, reset_cache
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        try:
            return [await config_for_category(pool, c)
                    for c in ("電表排障", "IoT設定引導")]
        finally:
            await pool.close()
    try:
        cfgs = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查面向設定：{e}")
    if any(c is None for c in cfgs):
        pytest.skip("IoT 面向設定未就緒；請套用第 2 節種子＋知識批次並清快取")


def _post(client, message, sid):
    return client.post("/api/v1/message", json={
        "message": message, "vendor_id": VENDOR_ID, "target_user": TARGET_USER,
        "role_id": ROLE_ID, "session_id": sid, "stream": False,
    })


def _conversational_rows(sid):
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            return await conn.fetchval(
                "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational'", sid)
        finally:
            await conn.close()
    return asyncio.run(_q())


def _cleanup(sid):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        finally:
            await conn.close()
    asyncio.run(_d())


# ══════ 電表排障：口語進場＋降級態不阻斷（J-I0 gated：真分支待 6.1*）══════

@pytest.mark.req("iot-conversational-facets:2.2")
def test_meter_entry_then_degraded_no_fabrication(client):
    sid = f"e2e-iotm-{uuid.uuid4().hex[:8]}"
    try:
        # 產品現實：「房間沒電」泛句由修繕 SOP 1166 先攔（既有設計，比分優先）——
        # 電表面向以「電表」強詞句進場；泛句走 SOP 屬正確行為不在此測。
        r1 = _post(client, "電表一直離線 度數不動", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "電表強詞句應進電表排障對話"

        # 給識別 → preview /meters 因 J-I0 恆回空 → 降級：誠實追問/查無，不虛構電表狀態
        r2 = _post(client, "海大質感獨立套房那間", sid)
        assert r2.status_code == 200, r2.text
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()                                        # 不阻斷
        for fab in ("已恢復供電", "餘額為", "已為您"):
            assert fab not in a2, f"降級態不得虛構/代操作：{a2[:200]}"
    finally:
        _cleanup(sid)


# ══════ 設定引導：口語進場＋機制 token＋不代操作（R3.1/R5.5）══════

@pytest.mark.req("iot-conversational-facets:3.1")
def test_setup_entry_then_mechanism_tokens(client):
    sid = f"e2e-iots-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "電表要怎麼串接進系統", sid)
        assert r1.status_code == 200, r1.text
        a1 = (r1.json().get("answer") or "")
        assert a1.strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進 IoT 設定引導對話"

        # 逐輪推進累計判定（LLM 可能首輪即收斂或先分流）
        transcript = [a1]
        for msg in ("就是台科電的電表", "所以要在哪裡綁定"):
            if any(k in transcript[-1] for k in ("IoT 裝置", "綁定", "台科電")):
                break
            r = _post(client, msg, sid)
            assert r.status_code == 200, r.text
            transcript.append(r.json().get("answer") or "")
        joined = "\n".join(transcript)
        assert any(k in joined for k in ("IoT 裝置", "綁定", "台科電")), \
            f"應給串接指路（機制 token），實得：{joined[-300:]}"
        assert "已為您綁定" not in joined                         # 不代操作
    finally:
        _cleanup(sid)


@pytest.mark.req("iot-conversational-facets:5.2")
def test_topup_price_question_mechanism(client):
    sid = f"e2e-iotp-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "儲值單價要在哪裡設定", sid)
        assert r1.status_code == 200, r1.text
        a1 = (r1.json().get("answer") or "")
        assert a1.strip()
        assert _conversational_rows(sid) >= 1
        # 單價機制：台科電端設定、JGB 鏡像（首輪或次輪出現）
        final = a1
        if "台科電" not in a1:
            r2 = _post(client, "台科電的儲值電表", sid)
            final = (r2.json().get("answer") or "")
        assert "台科電" in final, f"單價機制應指向廠商端設定：{final[:200]}"
    finally:
        _cleanup(sid)


# ══════ 跨域 switch：儲值金流話題 → 重路由不阻斷（R6.2）══════

@pytest.mark.req("iot-conversational-facets:6.2")
def test_cross_domain_switch_to_billing(client):
    sid = f"e2e-iotx-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "電表一直離線 度數不動", sid)
        assert r1.status_code == 200, r1.text
        assert _conversational_rows(sid) >= 1

        r2 = _post(client, "對了 租客儲值的錢到底入帳了沒", sid)
        assert r2.status_code == 200, r2.text
        assert (r2.json().get("answer") or "").strip()           # 重路由後仍答得出
    finally:
        _cleanup(sid)


# ══════ 進對話 vs 單發準則（門鎖硬體單發包）（R4.1/R9.2 佐證）══════

@pytest.mark.req("iot-conversational-facets:4.1")
def test_doorlock_hardware_stays_single_shot(client):
    sid = f"e2e-iotd-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "門鎖可以用悠遊卡嗎", sid)
        assert r.status_code == 200, r.text
        a = (r.json().get("answer") or "")
        assert a.strip()
        assert _conversational_rows(sid) == 0, "門鎖硬體問句應單發直答、不開面向對話"
        assert "廠商" in a or "型號" in a                         # 導廠商口徑
    finally:
        _cleanup(sid)
