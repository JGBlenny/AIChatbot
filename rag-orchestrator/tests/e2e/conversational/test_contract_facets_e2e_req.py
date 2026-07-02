"""e2e:合約 5 子面向（真管線：意圖分類→檢索→reranker→config_for_category→引擎→真 LLM＋真 jgb2）
—— contract-conversational-facets 任務 5.2/6.2（R2.4, R7.3, R7.4, R8.3, R11.4, R11.5）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線：
  - 每面向口語第一句進場（檢索命中錨點 → config_for_category 路由，非直呼引擎）；
  - 申請書出口關鍵 token 斷言（service@jgbsmart.com／異動前／異動後／合約 ID）；
  - grounding 缺欄位（G1–G4 未上線）降級不阻斷；
  - 進對話 vs 單發各一例。
真 LLM → 內容斷言僅限「關鍵 token／流程不變式」。

需 RUN_E2E=1 ＋ 整服務（DB/embedding/semantic-model/OPENAI/jgb2 preview）。
預設識別對應 preview 環境 role_id=20151 實盤（2026-07-02）：
  85174 已簽單筆（異動→申請書出口）／84908 點退中（退租收尾）／
  84981 已簽未過期（續約）／84927 等租客簽（簽署排障）。資料變動時以 env 覆寫。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_ROLE_ID", "20151")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")
REF_CHANGE = os.getenv("TEST_REF_CHANGE_SIGNED", "85174")     # status=8 已簽 → 申請書出口
REF_CLOSEOUT = os.getenv("TEST_REF_CLOSEOUT", "84908")        # status=64 點退中
REF_RENEW = os.getenv("TEST_REF_RENEW", "84981")              # status=8 未過期
REF_SIGN = os.getenv("TEST_REF_SIGN_PENDING", "84927")        # status=2 等租客簽


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
                    for c in ("合約異動", "退租收尾", "續約", "建約引導", "簽署排障")]
        finally:
            await pool.close()
    try:
        cfgs = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查面向設定：{e}")
    if any(c is None for c in cfgs):
        pytest.skip("面向設定未就緒；請套用第 3 節三支種子＋知識批次並清快取")


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


# ══════ 5.2 合約異動樹＋申請書出口關鍵 token（R2.4, R2.2）══════

@pytest.mark.req("contract-conversational-facets:2.4")
def test_change_tree_application_form_tokens(client):
    sid = f"e2e-chg-{uuid.uuid4().hex[:8]}"
    try:
        # 第 1 輪：帶識別的異動訴求 → 進面向、收斂三出口（已簽 → 不可直改）
        r1 = _post(client, f"我想改 {REF_CHANGE} 這份合約的租期", sid)
        assert r1.status_code == 200, r1.text
        a1 = r1.json().get("answer") or ""
        assert a1.strip() and not r1.json().get("form_triggered")
        assert _conversational_rows(sid) >= 1, "應進面向對話（非單發）"
        assert ("申請書" in a1) or ("複製" in a1), f"已簽分支應帶兩條出口，實得：{a1[:200]}"

        # 第 2 輪：給齊申請書槽位 → 收斂產出可抄錄內容（關鍵 token 斷言，防格式漂移）
        r2 = _post(client, "異動項目是租期，異動前租期到 2026/12/30，異動後改成 2028/12/30，幫我產申請書內容", sid)
        assert r2.status_code == 200, r2.text
        a2 = r2.json().get("answer") or ""
        for token in ("service@jgbsmart.com", "異動前", "異動後", REF_CHANGE):
            assert token in a2, f"申請書產出缺關鍵 token「{token}」：{a2[:300]}"
    finally:
        _cleanup(sid)


# ══════ 6.2 每面向口語第一句進場（正常管線，R8.3, R11.4）══════

@pytest.mark.req("contract-conversational-facets:8.3")
def test_closeout_colloquial_entry_then_ground(client):
    sid = f"e2e-clo-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客要退租了 接下來我要做什麼", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進退租收尾對話"

        r2 = _post(client, REF_CLOSEOUT, sid)
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()
        # 依該合約真實旗標答步驟：點退中 → 等租客同意/封存；已轉歷史 → 收尾完成。
        # （preview 資料會隨到期日推移轉歷史，兩態皆為正確 grounded 回答）
        assert any(k in a2 for k in ("點退", "租客同意", "封存", "收尾", "歷史合約")), \
            f"應依合約實際收尾狀態作答，實得：{a2[:200]}"
        # G3 secondary_call（7.3）：附掛真實 bills → 個人化封存 facts（該合約實測有未封存帳單；
        # 若日後資料被封存完，「皆已封存」亦為正確個人化輸出）
        assert ("未封存" in a2) or ("皆已封存" in a2), \
            f"G3 上線後封存應個人化（未封存清單/皆已封存），實得：{a2[:200]}"
    finally:
        _cleanup(sid)


@pytest.mark.req("contract-conversational-facets:8.3")
def test_renew_colloquial_entry_then_ground_degrades_without_g4(client):
    sid = f"e2e-rnw-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "合約快到期了要怎麼續約", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進續約對話"

        # G4（is_newest）未上線 → 降級不阻斷（R7.4/R10.3）
        r2 = _post(client, REF_RENEW, sid)
        a2 = (r2.json().get("answer") or "")
        assert r2.status_code == 200 and a2.strip()
        assert "續約" in a2
    finally:
        _cleanup(sid)


@pytest.mark.req("contract-conversational-facets:8.3")
def test_sign_trouble_colloquial_entry_degrades_without_g1_g2(client):
    sid = f"e2e-sgn-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客一直簽不了約怎麼辦", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進簽署排障對話"

        r2 = _post(client, REF_SIGN, sid)
        a2 = (r2.json().get("answer") or "")
        assert r2.status_code == 200 and a2.strip()
        assert ("租客" in a2) and ("簽" in a2)
        # G1 已上線（7.2）：邀請效期 facts 生效（未過期→效期至；過期→已過期＋退回清資料說明）
        assert any(k in a2 for k in ("效期", "有效", "過期", "期限")), \
            f"G1 上線後應帶效期判斷，實得：{a2[:200]}"
        # G2 防護（7.2）：preview 實測 to_user_login_email 為密文 → 略過比對，不得產生假錯配
        assert "不一致" not in a2, f"密文登入信箱不得判為錯配：{a2[:200]}"
    finally:
        _cleanup(sid)


@pytest.mark.req("contract-conversational-facets:8.3")
def test_create_guide_entry_then_scope_switch_reroute(client):
    sid = f"e2e-cgd-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "我要簽新合約 怎麼開始建", sid)
        assert r1.status_code == 200, r1.text
        a1 = (r1.json().get("answer") or "")
        assert a1.strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進建約引導對話"

        # 涉及特定合約現況 → scope=switch 關會話、當前訊息重路由（R8.1/R11.5）
        r2 = _post(client, f"我那份 {REF_CHANGE} 的合約現在能改嗎", sid)
        assert r2.status_code == 200, r2.text
        assert (r2.json().get("answer") or "").strip()   # 重路由後仍答得出（不阻斷）
    finally:
        _cleanup(sid)


# ══════ 進對話 vs 單發準則（R11.4；具體操作問句不進面向）══════

@pytest.mark.req("contract-conversational-facets:11.4")
def test_specific_operation_question_stays_single_shot(client):
    sid = f"e2e-single-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "點退押金的找補費用在哪裡操作", sid)
        assert r.status_code == 200, r.text
        a = (r.json().get("answer") or "")
        assert a.strip()
        assert _conversational_rows(sid) == 0, "具體操作問句應單發直答、不開面向對話"
        assert ("點退" in a) and ("找補" in a or "清單" in a)
    finally:
        _cleanup(sid)
