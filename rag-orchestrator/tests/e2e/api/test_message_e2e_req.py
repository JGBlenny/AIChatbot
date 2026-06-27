"""完整 /api/v1/message e2e：真打端點、跑完整 pipeline、斷言真實回應。

用 TestClient(app) 在程序內啟動 app（觸發 lifespan → 真 DB pool + 服務），
POST /api/v1/message 走完整條（驗證→對話/檢索→reranker→合成→串流）。

需整服務（DB/embedding/semantic-model/LLM）→ e2e；預設 RUN_E2E!=1 由 conftest 略過。
用真實 LLM，故只斷言「結構／契約／SSE 事件序」，不斷言合成文字內容（非決定性）。
斷言依據：對 live 端點實測的真實回應結構（非臆測）。
對應 testing-traceability R5.5（/message 非串流 + SSE 串流事件序）。
"""
import asyncio
import os

import pytest

pytestmark = pytest.mark.e2e

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _conversational_session(session_id):
    """回 (列數, 最大 asked_count) — 驗多輪狀態用。"""
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            row = await conn.fetchrow(
                "SELECT count(*) AS n, max((collected_data->>'asked_count')::int) AS asked "
                "FROM form_sessions WHERE session_id=$1 AND form_id='conversational'",
                session_id)
            return row["n"], row["asked"]
        finally:
            await conn.close()
    return asyncio.run(_q())


def _cleanup_session(session_id):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", session_id)
        finally:
            await conn.close()
    asyncio.run(_d())


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:   # 進入時觸發 lifespan：起真 DB pool + 服務
        yield c


@pytest.mark.req("testing-traceability:5.5")
def test_message_b2c_nonstream_returns_wellformed_response(client):
    """b2c 租客非串流：整條跑完、回傳結構完整的答案契約。"""
    r = client.post("/api/v1/message", json={
        "message": "請問怎麼繳租金",
        "vendor_id": VENDOR_ID,
        "target_user": "tenant",
        "session_id": "e2e-b2c-1",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d.get("answer"), str) and d["answer"].strip(), "answer 應為非空字串"
    # intent 可能無法分類（intent_type=None / intent_name='unknown'）——契約是「欄位存在」而非「必有值」
    assert "intent_type" in d and "intent_name" in d, "應有 intent 欄位（值可為 unknown/None）"
    assert d.get("vendor_id") == VENDOR_ID
    assert d.get("session_id") == "e2e-b2c-1"
    assert isinstance(d.get("sources"), list), "sources 應為 list"


@pytest.mark.req("testing-traceability:5.5")
def test_message_prospect_stream_event_sequence(client):
    """售前 prospect 串流：SSE 事件序 start→intent→answer_chunk→metadata→done。"""
    r = client.post("/api/v1/message", json={
        "message": "我管30戶想了解方案",
        "mode": "b2b",
        "target_user": "prospect",
        "session_id": "e2e-prospect-1",
        "stream": True,
    })
    assert r.status_code == 200, r.text
    types = [ln[len("event: "):] for ln in r.text.splitlines() if ln.startswith("event: ")]
    assert types, f"未收到任何 SSE 事件：{r.text[:200]}"
    assert types[0] == "start"
    assert "intent" in types
    assert "answer_chunk" in types
    assert types[-1] == "done"
    # 順序不變式：start 在最前、answer_chunk 在中、done 在最後
    assert types.index("start") < types.index("answer_chunk") < types.index("done")
    assert types.index("metadata") < types.index("done")


@pytest.mark.req("testing-traceability:5.5")
def test_multiturn_same_session_accumulates_state(client):
    """多輪同 session_id：狀態存於單一 conversational session 並累積（asked_count 不重置）。

    驗的是「跨輪狀態接續」這個確定性事實（查 form_sessions），非 LLM 內容。
    用語意模糊的訊息維持在補問（ask）路徑，使 asked_count 遞增可觀察。
    """
    sid = "e2e-multiturn-1"
    _cleanup_session(sid)
    try:
        r1 = client.post("/api/v1/message", json={
            "message": "你好，我想了解一下你們的服務",
            "mode": "b2b", "target_user": "prospect", "session_id": sid})
        assert r1.status_code == 200, r1.text
        n1, asked1 = _conversational_session(sid)
        assert n1 == 1, "turn1 應建立單一 conversational session"
        assert asked1 and asked1 >= 1, "turn1 後應有 asked_count"

        r2 = client.post("/api/v1/message", json={
            "message": "可以再多說一點嗎",
            "mode": "b2b", "target_user": "prospect", "session_id": sid})
        assert r2.status_code == 200, r2.text
        n2, asked2 = _conversational_session(sid)
        assert n2 == 1, "turn2 應重用同一 session（不重建、不重複）"
        assert asked2 >= asked1, "asked_count 應跨輪累積、未重置"
        assert asked2 >= 2, "兩輪補問後 asked_count 應 >= 2"
    finally:
        _cleanup_session(sid)


@pytest.mark.req("testing-traceability:5.5")
def test_conversation_to_form_transition(client):
    """對話導向表單轉場：命中 form_fill 知識（>= 門檻）→ 回傳表單收集結構。"""
    sid = "e2e-form-1"
    _cleanup_session(sid)
    try:
        r = client.post("/api/v1/message", json={
            "message": "租金資訊查詢：金額和繳費日期",   # form_fill 知識，必觸發 rent_info_form_v2
            "vendor_id": VENDOR_ID, "target_user": "tenant", "session_id": sid})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("form_triggered") is True, f"應觸發表單，實得 {d.get('form_triggered')}"
        assert d.get("form_id"), "觸發後應有 form_id"
        assert d.get("current_field"), "應有當前收集欄位"
        assert d.get("current_field_type"), "應有欄位型別"
    finally:
        _cleanup_session(sid)


@pytest.mark.req("testing-traceability:5.3")
def test_sop_triggered_returns_vendor_sop_source(client):
    """SOP 觸發：命中 vendor SOP（trigger_keywords）→ sources 含 scope='vendor_sop' + SOP 步驟答案。

    斷言「有用到 vendor_sop 來源」這個確定性事實，不斷言 LLM 合成的步驟文字。
    """
    sid = "e2e-sop-1"
    _cleanup_session(sid)
    try:
        r = client.post("/api/v1/message", json={
            "message": "大樓停水怎麼辦",        # vendor 2 SOP（trigger_keywords 含「大樓停水」）
            "vendor_id": VENDOR_ID, "target_user": "tenant", "session_id": sid})
        assert r.status_code == 200, r.text
        d = r.json()
        scopes = [s.get("scope") for s in d.get("sources", [])]
        assert "vendor_sop" in scopes, f"應命中 vendor_sop 來源，實得 {scopes}"
        assert isinstance(d.get("answer"), str) and d["answer"].strip(), "應回 SOP 步驟答案"
    finally:
        _cleanup_session(sid)


@pytest.mark.req("testing-traceability:5.4")
def test_form_fill_drives_to_completion(client):
    """表單填寫完成全流程：觸發 → 提供必填欄位 → 表單結束收集並產出結果。

    rent_info_form_v2 僅一個必填欄位 address；提供後表單離開收集狀態
    （current_field=None、form_triggered=False）並回傳查詢結果（此查詢型表單的「完成」
    ＝API 查詢結果，故 form_completed 旗標為 False——驗的是流程確實推進到結束。
    """
    sid = "e2e-formfill-1"
    _cleanup_session(sid)
    try:
        r1 = client.post("/api/v1/message", json={
            "message": "租金資訊查詢：金額和繳費日期",
            "vendor_id": VENDOR_ID, "target_user": "tenant", "session_id": sid})
        d1 = r1.json()
        assert d1.get("form_triggered") is True
        assert d1.get("current_field") == "address", f"應先收集 address，實得 {d1.get('current_field')}"

        r2 = client.post("/api/v1/message", json={
            "message": "新北市板橋區忠孝路48巷4弄8號一樓",
            "vendor_id": VENDOR_ID, "target_user": "tenant", "session_id": sid})
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        # 提供唯一必填欄位後，表單流程推進到結束（不再停在收集同一欄位）並產出結果答案
        assert d2.get("current_field") is None, "提供欄位後不應再停在收集 address"
        assert d2.get("form_triggered") is False, "表單流程應已結束、非再次觸發"
        assert isinstance(d2.get("answer"), str) and d2["answer"].strip(), "表單結束應產出結果答案"
    finally:
        _cleanup_session(sid)


@pytest.mark.req("testing-traceability:5.5")
@pytest.mark.parametrize("body,desc", [
    ({"message": "hi", "vendor_id": 2, "target_user": "not_a_role"}, "非法 target_user"),
    ({"message": "hi", "mode": "b2c"}, "b2c 缺 vendor_id"),
    ({"message": "", "vendor_id": 2}, "空訊息"),
    ({"message": "hi", "vendor_id": 2,
      "image_urls": ["https://a/1", "https://a/2", "https://a/3", "https://a/4"]}, "圖片超過 3 張"),
])
def test_message_invalid_requests_rejected_with_422(client, body, desc):
    """錯誤/邊界路徑：不合法請求於 API 層被擋（422），不進入 pipeline。"""
    r = client.post("/api/v1/message", json=body)
    assert r.status_code == 422, f"{desc} 應回 422，實得 {r.status_code}：{r.text[:160]}"
