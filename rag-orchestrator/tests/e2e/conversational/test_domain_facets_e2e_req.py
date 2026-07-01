"""e2e:領域化對話面向（真 jgb2 API，role_id=20151）—— domain-conversational-facets 任務 5.3｜R5.3, R8.1–8.4。

在 conversational-diagnosis e2e 之上，驗證本 spec 三項增修對真實 API 的端到端效果：
  (1) per-領域系統脈絡：合約診斷收斂時注入合約領域基底架構（12 階段），LLM 可**解讀**真實
      bit_status（逐位元）而非僅複述——結構上驗證收斂回非空且不誤入識別迴圈；
  (2) 候選帶區別欄位：多筆同名→候選清單帶期間（date Y/m/d），可辨識；候選過多→請補更明確條件；
  (3) 一般合約知識→靜態知識（三出口）；售前（prospect）不回歸。
真 LLM/真 API → 只斷言「結構／契約／流程不變式」，不斷言合成文字內容（非決定性）。

需 RUN_E2E=1 + 整服務；預設由 conftest 略過。

═══ 執行前置（部署作業）═══
  1. 套用三個種子：
       psql "$DATABASE_URL" -f database/migrations/seed_conversational_diagnosis_contract_rule.sql   # 8.1（已含 label_fields/candidate_cap）
       psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_diagnosis_category.sql  # 8.2
       psql "$DATABASE_URL" -f database/migrations/seed_domain_contract_system_context.sql             # 4.2（合約領域系統脈絡）
  2. 清快取（重啟服務，或經後台 /conversational-config 任一儲存）。
  3. 設 jgb2 API env（JGB_API_BASE_URL / JGB_API_KEY）指向可回 role_id=20151 資料之環境。
  4. 依真實資料設定下列 env：
       TEST_ROLE_ID=20151  TEST_VENDOR_ID=<業者 id>  TEST_DIAG_TARGET_USER=property_manager
       TEST_CONTRACT_REF_ONE=<回單筆的識別>
       TEST_CONTRACT_REF_MULTI=<回多筆同名的關鍵字（如共用物件名）>
       TEST_CONTRACT_REF_MANY=<回超過 candidate_cap(8) 筆的寬關鍵字>（可選）
  設定未就緒→自動 skip（不誤判失敗）。
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
REF_MANY = os.getenv("TEST_CONTRACT_REF_MANY", "")
DIAG_CATEGORY = "狀態判斷"  # 合約診斷面向（子分類；領域鍵＝topic_scope.category）


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
def _require_domain_setup():
    """前置：診斷設定 + 合約領域系統脈絡種子須已就緒，否則整模組 skip。"""
    async def _check():
        import asyncpg
        from services.conversational_config import config_for_category, reset_cache
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        try:
            cfg = await config_for_category(pool, DIAG_CATEGORY)
            async with pool.acquire() as conn:
                # 面向系統脈絡：母『系統合約』+ 子『狀態判斷』兩列須就緒
                ctx = await conn.fetchval(
                    "SELECT count(*) FROM knowledge_base "
                    "WHERE category='系統脈絡' AND is_active=TRUE "
                    "AND (('系統合約'=ANY(categories)) OR ('狀態判斷'=ANY(categories)))")
            return cfg, ctx
        finally:
            await pool.close()
    try:
        cfg, ctx = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查領域設定：{e}")
    if cfg is None:
        pytest.skip(f"診斷設定未就緒（{DIAG_CATEGORY} 未命中）；請套用 8.1/8.2 種子並清快取")
    if not ctx:
        pytest.skip("合約領域系統脈絡種子未就緒；請套用 seed_domain_contract_system_context.sql 並清快取")


def _post(client, message, sid, *, stream=False):
    return client.post("/api/v1/message", json={
        "message": message, "vendor_id": VENDOR_ID, "target_user": TARGET_USER,
        "role_id": ROLE_ID, "session_id": sid, "stream": stream,
    })


def _cleanup(sid):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        finally:
            await conn.close()
    asyncio.run(_d())


# ══════ R5.3/R8.1 模糊→識別→單筆收斂：以領域架構解讀真實狀態（結構斷言）══════
@pytest.mark.req("domain-conversational-facets:5.3")
def test_single_contract_converges_with_domain_context(client):
    if not REF_ONE:
        pytest.skip("未設 TEST_CONTRACT_REF_ONE")
    sid = f"e2e-df-one-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "我的合約狀態怪怪的", sid)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("answer", "").strip()          # 追問（非空）
        r2 = _post(client, REF_ONE, sid)
        assert r2.status_code == 200, r2.text
        ans = r2.json().get("answer", "")
        assert ans.strip()                                   # 收斂回非空（以架構+API 現值合成）
        # 收斂後不應再卡在「請提供合約編號/物件名稱」識別迴圈
        assert not (("請" in ans) and ("編號" in ans and "物件名稱" in ans))
    finally:
        _cleanup(sid)


# ══════ R4.1/R8.1 多筆同名→候選帶區別欄位（期間 Y/m/d）══════
@pytest.mark.req("domain-conversational-facets:4.1")
def test_multi_candidates_carry_distinguishing_period(client):
    if not REF_MULTI:
        pytest.skip("未設 TEST_CONTRACT_REF_MULTI（回多筆同名的關鍵字）")
    sid = f"e2e-df-multi-{uuid.uuid4().hex[:8]}"
    try:
        _post(client, "我要查合約", sid)
        r = _post(client, REF_MULTI, sid)
        assert r.status_code == 200, r.text
        ans = r.json().get("answer", "")
        assert ans.strip()
        # 多筆時應列候選並帶區別資訊：出現序號清單且帶日期格式（Y/m/d）——同名靠此可辨識
        assert "1." in ans and "2." in ans, f"多筆應列候選序號：{ans[:200]}"
        assert "/" in ans, f"候選應帶期間（Y/m/d）以辨識同名：{ans[:200]}"
    finally:
        _cleanup(sid)


# ══════ R4.3/R8.3 候選過多→請補更明確條件（不列長清單）══════
@pytest.mark.req("domain-conversational-facets:8.3")
def test_too_many_candidates_asks_to_refine(client):
    if not REF_MANY:
        pytest.skip("未設 TEST_CONTRACT_REF_MANY（回超過 candidate_cap 筆的寬關鍵字）")
    sid = f"e2e-df-many-{uuid.uuid4().hex[:8]}"
    try:
        _post(client, "我要查合約", sid)
        r = _post(client, REF_MANY, sid)
        assert r.status_code == 200, r.text
        ans = r.json().get("answer", "")
        assert ans.strip()
        # 過多→請補更明確識別（縮小/更明確），而非一次列出全部
        assert ("更明確" in ans) or ("縮小" in ans) or ("較多" in ans), f"過多應請補條件：{ans[:200]}"
    finally:
        _cleanup(sid)


# ══════ R8.2 一般合約知識→靜態知識（三出口，不入識別迴圈）══════
@pytest.mark.req("domain-conversational-facets:8.2")
def test_general_contract_knowledge_goes_static(client):
    sid = f"e2e-df-gen-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "違約責任怎麼算？", sid)
        assert r.status_code == 200, r.text
        ans = r.json().get("answer", "")
        assert ans.strip()
        assert not ("請提供" in ans and "合約編號" in ans), "一般知識不應誤入識別追問"
    finally:
        _cleanup(sid)


# ══════ R7.1/R8.4 售前（prospect）不回歸 ══════
@pytest.mark.req("domain-conversational-facets:7.1")
def test_presales_not_regressed(client):
    sid = f"e2e-df-presales-{uuid.uuid4().hex[:8]}"
    try:
        r = client.post("/api/v1/message", json={
            "message": "你們系統適合小規模房東嗎？", "vendor_id": VENDOR_ID,
            "target_user": "prospect", "session_id": sid, "stream": False})
        assert r.status_code == 200, r.text
        ans = r.json().get("answer", "")
        assert ans.strip()
        # 售前不應要求提供合約編號（未被合約領域脈絡污染）
        assert "合約編號" not in ans
    finally:
        _cleanup(sid)
