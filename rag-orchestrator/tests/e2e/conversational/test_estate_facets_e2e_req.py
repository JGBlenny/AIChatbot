"""e2e:物件 2 子面向（真管線：檢索→reranker→config_for_category→引擎→真 LLM＋真 jgb2 preview）
—— estate-conversational-facets 任務 4.2（R2.2, R3.1, R4.2, R4.3, R7.2, R8.3）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線：
  - 引導：地址雙層錨點句直答（「完整地址/對外」token）＋儲存行為冷問；
  - 診斷：真物件（role 37305 名下刊登中）識別→現況 facts；個資負斷言（完整地址不出口）；
  - sentinel：查無→「非刊登中」口徑＋不斷言已刪除→打錯字更正流程；
  - 誤吸邊界：合約域對比句不進物件面向。
斷言模式：逐輪推進＋全輪累計判定＋機制 token＋紅線負斷言。
批次上傳範圍外（使用者裁定 2026-07-04）——無批次案。
需 RUN_E2E=1 ＋ 整服務（真 DB/embedding/reranker/OpenAI/jgb2 preview）。
"""
import asyncio
import os
import re
import uuid

import pytest

pytestmark = pytest.mark.e2e

ROLE_ID = os.getenv("TEST_ESTATE_ROLE_ID", "37305")   # 125 物件（status {8,2,4} 真資料）
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = "property_manager"


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
                    for c in ("物件操作引導", "物件現況診斷")]
        finally:
            await pool.close()
    try:
        cfgs = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查面向設定：{e}")
    if any(c is None for c in cfgs):
        pytest.skip("物件面向設定未就緒；請套用第 2 節種子＋知識批次並清快取")


@pytest.fixture(scope="module")
def real_estate():
    """真資料前置：從 preview 取 role 名下一筆 status=2（合約軸刊登中）物件。"""
    async def _pick():
        from services.jgb_system_api import JGBSystemAPI
        api = JGBSystemAPI()
        api.use_mock = False
        r = await api.get_estate_status(role_id=ROLE_ID)
        rows = [e for e in (r.get("data") or []) if e.get("found") is not False]
        pub = [e for e in rows if e.get("status") == 2] or rows
        return pub[0] if pub else None
    try:
        e = asyncio.run(_pick())
    except Exception as ex:
        pytest.skip(f"preview estates 不可用：{ex}")
    if not e:
        pytest.skip(f"role {ROLE_ID} 無可用物件")
    return e


def _post(client, message, sid):
    r = client.post("/api/v1/message", json={
        "message": message, "vendor_id": VENDOR_ID, "target_user": TARGET_USER,
        "role_id": ROLE_ID, "session_id": sid, "stream": False})
    assert r.status_code == 200, r.text
    return (r.json().get("answer") or "").strip()


def _cleanup(sid):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        finally:
            await conn.close()
    asyncio.run(_d())


# ══════ ① 引導：地址雙層錨點句直答＋stay 追問（R3.1/R2.2）══════

@pytest.mark.req("estate-conversational-facets:3.1")
def test_guide_display_address_multiturn(client):
    sid = f"e2e-estg-{uuid.uuid4().hex[:8]}"
    try:
        a1 = _post(client, "我改了對外顯示地址 怎麼系統上還是顯示完整地址", sid)
        a2 = _post(client, "那租客那邊看到的會是哪個地址", sid)
        acc = a1 + a2
        assert "對外" in acc and ("完整地址" in acc or "後台" in acc), f"雙層行為未講清：{acc[:160]}"
        assert "廣告頁" in acc or "對外頁" in acc or "店舖" in acc      # 指路確認方法
        assert "幫您修改" not in acc and "我來設定" not in acc          # 不代操作
    finally:
        _cleanup(sid)


# ══════ ② 引導：儲存行為冷問（R2.6）══════

@pytest.mark.req("estate-conversational-facets:2.2")
def test_guide_save_behavior_cold(client):
    sid = f"e2e-ests-{uuid.uuid4().hex[:8]}"
    try:
        a = _post(client, "編輯物件改完之後怎麼都沒有存到 資料不見了", sid)
        assert "儲存" in a, f"未講儲存行為：{a[:160]}"
    finally:
        _cleanup(sid)


# ══════ ③ 診斷：真物件識別→現況 facts＋個資負斷言（R4.2/R4.3）══════

@pytest.mark.req("estate-conversational-facets:4.2")
def test_diag_real_estate_status(client, real_estate):
    sid = f"e2e-estd-{uuid.uuid4().hex[:8]}"
    title = real_estate["title"]
    try:
        a1 = _post(client, "我要查一個物件現在的狀態 租客看得到嗎", sid)
        a2 = _post(client, f"幫我看 {title} 這間", sid)
        answers = [a1, a2]
        # 候選（同名多筆）→ 選 1 再收斂
        if re.search(r"哪一筆|哪一個|請問您指的", a2):
            answers.append(_post(client, "1", sid))
        acc = "".join(answers)
        assert any(t in acc for t in ("刊登中", "洽談中", "租約中")), f"未回狀態轉譯：{acc[:200]}"
        # 個資紅線：真完整地址不出口（display 版允許——只斷言 full 版特徵「號」+樓層全址不出現）
        full = real_estate.get("full_address") or real_estate.get("address") or ""
        if full and full != (real_estate.get("display_address") or ""):
            assert full not in acc, "完整地址外洩"
    finally:
        _cleanup(sid)


# ══════ ④ sentinel：查無→非刊登中口徑→打錯字更正（R4.2 / design Issue 1）══════

@pytest.mark.req("estate-conversational-facets:4.2")
def test_diag_sentinel_then_correction(client, real_estate):
    sid = f"e2e-estn-{uuid.uuid4().hex[:8]}"
    title = real_estate["title"]
    try:
        a1 = _post(client, "幫我看一下「不存在的華廈999」這個物件現在什麼狀態", sid)
        assert "非刊登中" in a1 or "找不到" in a1 or "名稱" in a1, f"sentinel 口徑未觸發：{a1[:160]}"
        assert "已刪除" not in a1                                  # 紅線：不斷言刪除
        assert "查無對應的資料，請再確認一下識別資訊" not in a1      # 不出引擎通用句
        # 打錯字更正：給真物件名 → 應恢復查詢（候選或直答狀態）
        a2 = _post(client, f"打錯了 是{title}", sid)
        acc = a1 + a2
        ok = any(t in a2 for t in ("刊登中", "洽談中", "租約中")) or \
             re.search(r"哪一筆|哪一個|請問您指的", a2)
        assert ok, f"更正後未恢復查詢：{a2[:200]}"
        assert "已刪除" not in acc
    finally:
        _cleanup(sid)


# ══════ ⑤ 誤吸邊界：合約域對比句不進物件面向（R7.2）══════

@pytest.mark.req("estate-conversational-facets:7.2")
def test_boundary_contract_sentence_not_estate(client):
    sid = f"e2e-estb-{uuid.uuid4().hex[:8]}"
    try:
        a = _post(client, "這份合約上面的物件地址寫錯了 要怎麼改", sid)
        # 不得進物件現況診斷（不問物件識別查刊登現值）；合約快照/資料異動/客服方向皆可
        assert "非刊登中" not in a and "刊登清單" not in a, f"被吸進物件診斷：{a[:160]}"
    finally:
        _cleanup(sid)
