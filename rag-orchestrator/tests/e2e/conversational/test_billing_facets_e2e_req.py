"""e2e:帳務 5 子面向（真管線：意圖分類→檢索→reranker→config_for_category→引擎→真 LLM＋真 jgb2 preview）
—— billing-conversational-facets 任務 6.2（R7.4, R8.3, R11.3）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線：
  - 每面向口語第一句進場（檢索命中錨點 → config_for_category 路由，非直呼引擎）；
  - 金流排障多輪真資料（709739 待繳費無 pay_at → 查無繳費核對引導分支）；
  - **金額原樣 token 斷言**（facts 金額出現於回答且未被改寫）；
  - pay_info/cvs_info 值為 null（未取號）→ 存在性驅動降級不阻斷；
  - 進對話 vs 單發各一例。
真 LLM → 內容斷言僅限「關鍵 token／流程不變式」。

需 RUN_E2E=1 ＋ 整服務（DB/embedding/semantic-model/OPENAI/jgb2 preview）。
預設識別對應 preview 環境 role_id=20151 實盤（2026-07-03）：
  709739 status=2 待繳費、無 pay_at、total=24800（查無繳費分支＋金額 token）／
  709742 status=16 已到帳、pay_at 2026-06-30（正常入帳對照）。資料變動時以 env 覆寫。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_ROLE_ID", "20151")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")
REF_BILL_READY = os.getenv("TEST_REF_BILL_READY", "709739")      # status=2 無 pay_at
AMT_BILL_READY = os.getenv("TEST_AMT_BILL_READY", "24,800")      # 對應 total（千分位）
REF_BILL_PAID = os.getenv("TEST_REF_BILL_PAID", "709742")        # status=16 已到帳


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
                    for c in ("繳費金流排障", "帳單異常", "發票", "滯納金", "帳單設定引導")]
        finally:
            await pool.close()
    try:
        cfgs = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查面向設定：{e}")
    if any(c is None for c in cfgs):
        pytest.skip("帳務面向設定未就緒；請套用第 4 節種子＋知識批次並清快取")


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


# ══════ 金流排障多輪真資料＋金額原樣 token（R2.2, R7.4, R11.3）══════

@pytest.mark.req("billing-conversational-facets:2.2")
def test_payment_flow_multiturn_real_data_amount_verbatim(client):
    sid = f"e2e-bpay-{uuid.uuid4().hex[:8]}"
    try:
        # 第 1 輪：口語現象起手 → 進金流排障對話（非單發）
        r1 = _post(client, "租客說錢繳了 可是帳一直沒進來", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進金流排障對話"

        # 第 2 輪：給帳單編號 → 直查 ground（709739 待繳費、查無繳費紀錄）
        r2 = _post(client, REF_BILL_READY, sid)
        assert r2.status_code == 200, r2.text
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()
        # 查無繳費分支：核對引導（帳號/上限/入帳時間差）或收回重發，不得臆測已入帳
        assert any(k in a2 for k in ("查無", "帳號", "上限", "重發", "核對", "確認")), \
            f"待繳費無繳費紀錄應給核對引導，實得：{a2[:200]}"
        assert "已到帳" not in a2, f"查無繳費不得臆測入帳：{a2[:200]}"
        # 金額原樣 token：facts 金額出現且未被改寫（千分位或原數字皆收）
        assert (AMT_BILL_READY in a2) or (AMT_BILL_READY.replace(",", "") in a2), \
            f"金額應原樣出現（{AMT_BILL_READY}），實得：{a2[:300]}"
    finally:
        _cleanup(sid)


# ══════ 每面向口語第一句進場（正常管線含 reranker，R8.3）══════

@pytest.mark.req("billing-conversational-facets:8.3")
def test_bill_anomaly_colloquial_entry(client):
    sid = f"e2e-bano-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "租客說他在系統裡看不到這期帳單", sid)
        assert r.status_code == 200, r.text
        assert (r.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進帳單異常對話"
    finally:
        _cleanup(sid)


@pytest.mark.req("billing-conversational-facets:8.3")
def test_invoice_colloquial_entry_then_ground(client):
    sid = f"e2e-binv-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "這期的發票一直沒開出來", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進發票對話"

        # 已到帳單 ground（發票 invoice_status=0 → 依真值作答；降級不阻斷）
        r2 = _post(client, REF_BILL_PAID, sid)
        assert r2.status_code == 200, r2.text
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()
        assert "發票" in a2
    finally:
        _cleanup(sid)


@pytest.mark.req("billing-conversational-facets:8.3")
def test_late_fee_colloquial_entry(client):
    sid = f"e2e-blf-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "為什麼這個月滯納金收這麼多", sid)
        assert r.status_code == 200, r.text
        assert (r.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進滯納金對話"
    finally:
        _cleanup(sid)


@pytest.mark.req("billing-conversational-facets:8.3")
def test_setup_guide_colloquial_entry(client):
    sid = f"e2e-bset-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "我要怎麼設定每個月幾號出帳單", sid)
        assert r.status_code == 200, r.text
        a = (r.json().get("answer") or "")
        assert a.strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進帳單設定引導對話"
    finally:
        _cleanup(sid)


# ══════ 進對話 vs 單發準則（R11.3；教學/制度問句不進面向）══════

@pytest.mark.req("billing-conversational-facets:11.3")
def test_teaching_question_stays_single_shot(client):
    sid = f"e2e-bsingle-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "帳單可以批次匯入嗎 怎麼操作", sid)
        assert r.status_code == 200, r.text
        a = (r.json().get("answer") or "")
        assert a.strip()
        assert _conversational_rows(sid) == 0, "教學/制度問句應單發直答、不開面向對話"
        assert ("匯入" in a) or ("批次" in a)
    finally:
        _cleanup(sid)
