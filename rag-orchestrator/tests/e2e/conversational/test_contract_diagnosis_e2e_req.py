"""e2e:對話式合約診斷（真 jgb2 API，role_id=20151）—— conversational-diagnosis 任務 9.1/9.2/9.3。

用 TestClient(app) 在程序內起整服務（真 DB pool + embedding + semantic-model + LLM + jgb2 API），
POST /api/v1/message 走完整條，驗證診斷對話三出口與多筆/0 筆/售前不回歸。
真 LLM/真 API → 只斷言「結構／契約／流程不變式／SSE 事件序」，不斷言合成文字內容（非決定性）。

需 RUN_E2E=1 + 整服務；預設由 conftest 略過。

═══ 執行前置（部署作業）═══
  1. 套用兩個種子（任務 8.1 / 8.2）：
       psql "$DATABASE_URL" -f database/migrations/seed_conversational_diagnosis_contract_rule.sql
       psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_diagnosis_category.sql
  2. 清快取（重啟服務，或經後台 /conversational-config 任一儲存）。
  3. 設 jgb2 API 環境變數（JGB_API_BASE_URL / JGB_API_KEY）指向可回 role_id=20151 資料之環境。
  4. 依該環境的真實合約資料設定下列 env（測試以此查真資料）：
       TEST_ROLE_ID=20151
       TEST_VENDOR_ID=<對應業者 id>
       TEST_DIAG_TARGET_USER=property_manager        # 合約知識可被此角色檢索到
       TEST_CONTRACT_REF_ONE=<會回「單筆」的合約編號或物件名稱>
       TEST_CONTRACT_REF_MULTI=<會回「多筆」的關鍵字（如共用物件名）>
       TEST_CONTRACT_REF_NONE=<會回「0 筆」的識別>
  若診斷設定未就緒（種子未套用/未清快取），測試自動 skip（不誤判失敗）。

斷言依據：對 live 端點之契約（沿用 tests/e2e/api 既有模式）。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_ROLE_ID", "20151")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")
REF_ONE = os.getenv("TEST_CONTRACT_REF_ONE", "")
REF_MULTI = os.getenv("TEST_CONTRACT_REF_MULTI", "")
REF_NONE = os.getenv("TEST_CONTRACT_REF_NONE", "查無此合約xyz")
DIAG_CATEGORY = "狀態判斷"  # 合約診斷面向（實作定名；同 test_domain_facets_e2e_req.py）


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
    with TestClient(app) as c:   # 進入觸發 lifespan：起真 DB pool + 服務
        yield c


@pytest.fixture(scope="module", autouse=True)
def _require_diagnosis_config():
    """前置：診斷設定須已就緒（種子套用 + 快取載入），否則整模組 skip。"""
    async def _check():
        import asyncpg
        from services.conversational_config import config_for_category, reset_cache
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        try:
            cfg = await config_for_category(pool, DIAG_CATEGORY)
            return cfg
        finally:
            await pool.close()
    try:
        cfg = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查診斷設定：{e}")
    if cfg is None:
        pytest.skip(f"診斷設定未就緒（{DIAG_CATEGORY} 未命中）；請先套用 8.1/8.2 種子並清快取")


def _post(client, message, sid, *, stream=False):
    return client.post("/api/v1/message", json={
        "message": message, "vendor_id": VENDOR_ID, "target_user": TARGET_USER,
        "role_id": ROLE_ID, "session_id": sid, "stream": stream,
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


def _sse_event_types(resp_text):
    return [ln[len("event: "):] for ln in resp_text.splitlines() if ln.startswith("event: ")]


# ══════════════════════ 9.1 模糊→追問→收齊→真實資訊 + 三出口 ══════════════════════

@pytest.mark.req("conversational-diagnosis:8.3")
def test_ambiguous_then_identify_converges(client):
    """模糊問句→追問（條件不足，不觸發表單）→提供識別→收齊→回真實狀態（非空答案）。"""
    if not REF_ONE:
        pytest.skip("未設 TEST_CONTRACT_REF_ONE（該環境會回單筆的合約識別）")
    sid = f"e2e-diag-{uuid.uuid4().hex[:8]}"
    try:
        # 第 1 輪：模糊問句 → 進診斷對話、回追問（非表單、未收斂）
        r1 = _post(client, "我的合約狀態怪怪的", sid)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert isinstance(d1.get("answer"), str) and d1["answer"].strip()
        assert not d1.get("form_triggered"), "條件不足應追問，而非觸發表單（R1.1/R2.2）"
        assert _conversational_rows(sid) >= 1, "應建立 conversational 會話（續對話接得上）"

        # 第 2 輪：提供識別 → 收齊 → 收斂回真實資訊（非空）
        r2 = _post(client, REF_ONE, sid)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert isinstance(d2.get("answer"), str) and d2["answer"].strip()
        assert not d2.get("form_triggered")
    finally:
        _cleanup(sid)


@pytest.mark.req("conversational-diagnosis:8.4")
def test_general_contract_knowledge_goes_static(client):
    """一般合約知識（非查某一份）→ 轉靜態知識回答（三出口分派），不卡在追問識別。"""
    sid = f"e2e-diag-gen-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "違約責任怎麼算？", sid)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("answer"), str) and d["answer"].strip()
        # 一般知識不應要求提供合約編號/物件名稱（不誤入識別追問迴圈）
        assert "編號" not in d["answer"] or "物件" not in d["answer"]
    finally:
        _cleanup(sid)


@pytest.mark.req("conversational-diagnosis:2.2")
def test_stream_contract_diagnosis_event_sequence(client):
    """串流契約：診斷對話 SSE 事件序 start→…→answer_chunk→…→done。"""
    sid = f"e2e-diag-sse-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "我的合約狀態怪怪的", sid, stream=True)
        assert r.status_code == 200, r.text
        types = _sse_event_types(r.text)
        assert types and types[0] == "start" and types[-1] == "done"
        assert "answer_chunk" in types
        assert types.index("start") < types.index("answer_chunk") < types.index("done")
    finally:
        _cleanup(sid)


# ══════════════════════ 9.2 0 筆重問 / 多筆列候選→選擇→單筆 ══════════════════════

@pytest.mark.req("conversational-diagnosis:3.4")
def test_zero_result_reasks(client):
    """API 回 0 筆 → 不杜撰，重問確認識別（仍為對話、未觸發表單）。"""
    sid = f"e2e-diag-zero-{uuid.uuid4().hex[:8]}"
    try:
        _post(client, "我要查我的合約", sid)               # 起對話
        r = _post(client, REF_NONE, sid)                   # 給查無的識別
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("answer"), str) and d["answer"].strip()
        assert not d.get("form_triggered")
    finally:
        _cleanup(sid)


@pytest.mark.req("conversational-diagnosis:3.5")
def test_multiple_results_list_then_select(client):
    """API 多筆 → 列候選反問 → 選擇序號 → 單筆收斂（pending_candidates 流程）。"""
    if not REF_MULTI:
        pytest.skip("未設 TEST_CONTRACT_REF_MULTI（該環境會回多筆的識別）")
    sid = f"e2e-diag-multi-{uuid.uuid4().hex[:8]}"
    try:
        _post(client, "我要查我的合約", sid)
        r_multi = _post(client, REF_MULTI, sid)            # → 列候選
        assert r_multi.status_code == 200, r_multi.text
        assert isinstance(r_multi.json().get("answer"), str) and r_multi.json()["answer"].strip()

        r_pick = _post(client, "1", sid)                   # 選第 1 筆 → 單筆收斂
        assert r_pick.status_code == 200, r_pick.text
        assert isinstance(r_pick.json().get("answer"), str) and r_pick.json()["answer"].strip()
    finally:
        _cleanup(sid)


# ══════════════════════ 9.3 售前不回歸 / 非診斷查詢不變 ══════════════════════

@pytest.mark.req("conversational-diagnosis:7.1")
def test_prospect_conversation_unchanged(client):
    """售前 prospect 串流仍為既有對話事件序（不受診斷面向影響）。"""
    sid = f"e2e-prospect-{uuid.uuid4().hex[:8]}"
    try:
        r = client.post("/api/v1/message", json={
            "message": "我管30戶想了解方案", "mode": "b2b",
            "target_user": "prospect", "session_id": sid, "stream": True})
        assert r.status_code == 200, r.text
        types = _sse_event_types(r.text)
        assert types and types[0] == "start" and types[-1] == "done" and "answer_chunk" in types
    finally:
        _cleanup(sid)


@pytest.mark.req("conversational-diagnosis:7.2")
def test_non_diagnosis_query_unchanged(client):
    """非診斷面向查詢（租客一般問題）→ 既有檢索/表單/直接知識，不進診斷對話。"""
    sid = f"e2e-nondiag-{uuid.uuid4().hex[:8]}"
    try:
        r = client.post("/api/v1/message", json={
            "message": "請問怎麼繳租金", "vendor_id": VENDOR_ID,
            "target_user": "tenant", "session_id": sid})
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("answer"), str) and d["answer"].strip()
        assert "intent_type" in d and "session_id" in d
    finally:
        _cleanup(sid)
