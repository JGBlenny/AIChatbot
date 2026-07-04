"""e2e:帳號 4 子面向（真管線：檢索→reranker→config_for_category→引擎→真 LLM＋真 jgb2 preview）
—— account-conversational-facets 任務 4.2（R2.2, R6.3, R6.4, R10.3, R10.5）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線：
  - 每面向口語第一句進場；登入排障多輪真資料（preview is_tenant_registered 實值）；
  - 機制 token 斷言（識別碼/5 分鐘/三次/72 小時——LLM 不得改寫機制數字）；
  - 申請書出口 token（service@jgbsmart.com）；
  - **驗證碼紅線**：回答不得出現驗證碼值樣式；
  - 跨域 switch（簽約頁話題 → 合約簽署排障）；進對話 vs 單發各一例。
真 LLM → 內容斷言僅限「關鍵 token／流程不變式」。

需 RUN_E2E=1 ＋ 整服務。preview role_id=20151 實盤（2026-07-03）：
  85174 is_tenant_registered=False（未註冊分支）／84981 =True 且登入=邀請信箱（一致分支）。
資料變動時以 env 覆寫。
"""
import asyncio
import os
import re
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_ROLE_ID", "20151")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")
REF_UNREGISTERED = os.getenv("TEST_REF_TENANT_UNREGISTERED", "85174")
REF_REGISTERED_OK = os.getenv("TEST_REF_TENANT_REGISTERED", "84981")

_CODE_PATTERN = re.compile(r"驗證碼[^\n]{0,6}\d{4}")


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
                    for c in ("註冊驗證排障", "登入排障", "帳號綁定異動", "團隊成員權限")]
        finally:
            await pool.close()
    try:
        cfgs = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查面向設定：{e}")
    if any(c is None for c in cfgs):
        pytest.skip("帳號面向設定未就緒；請套用第 2 節種子＋知識批次並清快取")


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


# ══════ 登入排障多輪真資料：未註冊分支＋一致分支（R3.3, R6.4）══════

@pytest.mark.req("account-conversational-facets:3.3")
def test_login_multiturn_unregistered_branch(client):
    sid = f"e2e-alog-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客說他登不進去系統", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進登入排障對話"

        r2 = _post(client, REF_UNREGISTERED, sid)
        assert r2.status_code == 200, r2.text
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()
        assert "註冊" in a2 and ("尚未" in a2 or "未註冊" in a2 or "還沒" in a2), \
            f"未註冊分支應照系統判定，實得：{a2[:200]}"
        assert "72" in a2, f"快速驗證信效期機制數字應保留：{a2[:200]}"
        assert "登錯" not in a2                                   # 未註冊不談錯配
        assert not _CODE_PATTERN.search(a2)                       # 驗證碼紅線
        # G-A1 嚴格遮罩：85174 真實 lessee_name「1測試股份有限公司」不得出現於回話
        assert "測試股份有限公司" not in a2, f"G-A1 姓名外洩：{a2[:200]}"
    finally:
        _cleanup(sid)


@pytest.mark.req("account-conversational-facets:3.3")
def test_login_multiturn_registered_ok_branch(client):
    sid = f"e2e-alog2-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客登入後什麼都看不到 畫面空空的", sid)
        assert r1.status_code == 200, r1.text
        assert _conversational_rows(sid) >= 1

        r2 = _post(client, REF_REGISTERED_OK, sid)
        a2 = (r2.json().get("answer") or "")
        assert a2.strip()
        assert "已註冊" in a2 or "一致" in a2 or "正常" in a2, f"應照系統判定帳號正常：{a2[:200]}"
        assert ("身分" in a2 or "角色" in a2 or "確切寫法" in a2), f"應轉向登入操作排查：{a2[:200]}"
        # G-A1 嚴格遮罩：84981 真實 lessee_name「JGBDemo」不得出現於回話
        assert "JGBDemo" not in a2, f"G-A1 姓名外洩：{a2[:200]}"
    finally:
        _cleanup(sid)


# ══════ 註冊驗證排障：口語進場＋機制 token（R2.2, R2.5）══════

@pytest.mark.req("account-conversational-facets:2.2")
def test_register_entry_then_mechanism_tokens(client):
    sid = f"e2e-areg-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客一直沒辦法註冊 卡住了", sid)
        assert r1.status_code == 200, r1.text
        assert (r1.json().get("answer") or "").strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進註冊驗證排障對話"

        # persona 允許至多兩輪分流（管道×現象）：逐輪補資訊，最後直問機制
        MECH = ("識別碼", "5 分鐘", "三次", "3 次", "重新取得", "120", "失效")
        final = ""
        for msg in ("他有收到驗證碼 但輸入一直失敗", "簡訊",
                    "為什麼會一直失敗 驗證碼機制是怎麼運作的"):
            r = _post(client, msg, sid)
            assert r.status_code == 200, r.text
            final = (r.json().get("answer") or "")
            assert not _CODE_PATTERN.search(final)                # 每輪都不得出現驗證碼值樣式
            if any(k in final for k in MECH):
                break
        assert any(k in final for k in MECH), \
            f"機制說明應含脈絡寫死的規則，實得：{final[:200]}"
    finally:
        _cleanup(sid)


# ══════ 綁定異動：口語進場＋申請書出口 token（R4.2）══════

@pytest.mark.req("account-conversational-facets:4.2")
def test_binding_entry_then_application_form_tokens(client):
    sid = f"e2e-abind-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "手機被綁定過了 要解綁換綁", sid)
        assert r1.status_code == 200, r1.text
        a1 = (r1.json().get("answer") or "")
        assert a1.strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進帳號綁定異動對話"

        # 走申請書出口方向即可（進面向＋收斂到「申請 → JGB 後台/客服處理」）。
        # 申請書關鍵 token（service@jgbsmart.com/修改前後值）已於整合層決定性斷言
        # （test_binding_converge_carries_application_form_tokens），此處不綁真 LLM 時序。
        transcript = [a1]
        for msg in ("要把 0912345678 換成 0987654321 要怎麼申請",
                    "帳號是 0912345678 合約 ID 84981"):
            r = _post(client, msg, sid)
            assert r.status_code == 200, r.text
            transcript.append(r.json().get("answer") or "")
        joined = "\n".join(transcript)
        assert "申請" in joined and ("service@jgbsmart.com" in joined or "客服" in joined or "後台" in joined), \
            f"綁定異動應走申請書/後台出口：{joined[-300:]}"
        assert "另開" not in joined and "分身" not in joined       # 不建議繞過綁定
    finally:
        _cleanup(sid)


# ══════ 團隊權限：口語進場＋最高頻真因（R5.1）══════

@pytest.mark.req("account-conversational-facets:5.1")
def test_team_entry_then_role_assignment_cause(client):
    sid = f"e2e-ateam-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "加了團隊成員 他什麼都看不到", sid)
        assert r1.status_code == 200, r1.text
        a1 = (r1.json().get("answer") or "")
        assert a1.strip()
        assert _conversational_rows(sid) >= 1, "口語第一句應進團隊成員權限對話"
        # 首輪或次輪內容擇一驗（LLM 可能直接收斂）：最高頻真因要出現
        if "變更角色" not in a1 and "指派" not in a1:
            r2 = _post(client, "他是加入之後就一直看不到社區", sid)
            a2 = (r2.json().get("answer") or "")
            assert "變更角色" in a2 or "指派" in a2, \
                f"應指向角色指派真因，實得：{a2[:200]}"
    finally:
        _cleanup(sid)


# ══════ 跨域 switch：簽約頁話題 → 合約簽署排障（R10.5）══════

@pytest.mark.req("account-conversational-facets:10.5")
def test_cross_domain_switch_to_contract_sign(client):
    sid = f"e2e-axd-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "租客說他登不進去系統", sid)
        assert r1.status_code == 200, r1.text
        assert _conversational_rows(sid) >= 1

        r2 = _post(client, "他是在簽約頁上傳身分證一直跳錯誤 簽不了約", sid)
        assert r2.status_code == 200, r2.text
        assert (r2.json().get("answer") or "").strip()            # 重路由後仍答得出（不阻斷）
    finally:
        _cleanup(sid)


# ══════ 進對話 vs 單發準則（R10.2 佐證；教學問句不進面向）══════

@pytest.mark.req("account-conversational-facets:10.3")
def test_teaching_question_stays_single_shot(client):
    sid = f"e2e-asingle-{uuid.uuid4().hex[:8]}"
    try:
        r = _post(client, "帳號要怎麼註冊 流程是什麼", sid)
        assert r.status_code == 200, r.text
        a = (r.json().get("answer") or "")
        assert a.strip()
        assert _conversational_rows(sid) == 0, "教學問句應單發直答、不開面向對話"
        assert "註冊" in a
    finally:
        _cleanup(sid)
