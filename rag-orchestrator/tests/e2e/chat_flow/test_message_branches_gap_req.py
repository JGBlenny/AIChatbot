"""e2e 缺口補驗:重構後「從未被真實實跑」的分支(chat-flow-refactor 收尾驗證)。

補齊先前只靠 mock/推理/被停用而未實跑的分支:
- handle_cache 命中(陷阱2:stream→stream_cached_answer SSE / 非 stream→JSON)
  ── 需 CACHE_ENABLED=true + redis;停用時自動 skip(不誤失敗)。
- handle_retrieval 知識**串流合成**路徑(Stage 3 動到、原 e2e 未涵蓋)。
- handle_form_session REVIEWING **確認**(原僅驗取消)。
- handle_image 損壞**非串流**(原僅驗損壞串流)。

需 RUN_E2E=1 + 整服務。真 LLM,故只斷言結構/契約/SSE 事件序。
"""
import json
import os

import psycopg2
import pytest

pytestmark = pytest.mark.e2e

V = int(os.getenv("TEST_VENDOR_ID", "2"))


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"), user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )
    conn.autocommit = True
    yield conn
    conn.close()


def _seed_session(db, session_id, state, current_field_index=0, collected=None):
    with db.cursor() as cur:
        cur.execute("DELETE FROM form_sessions WHERE session_id = %s", (session_id,))
        cur.execute(
            "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, current_field_index, collected_data) "
            "VALUES (%s,%s,%s,'demo_form',%s,%s,%s)",
            (session_id, "u-gap", V, state, current_field_index, json.dumps(collected or {})),
        )


def _cleanup(db, session_id):
    with db.cursor() as cur:
        cur.execute("DELETE FROM form_sessions WHERE session_id = %s", (session_id,))


# ── handle_cache 命中(陷阱2)── 需 cache 啟用,否則 skip ──────────────────

def _prime_cache(client, *, vendor_id, question, target_user, answer):
    """用 pipeline 同一把 cache_service + 同一 config_version 直接寫入命中內容。"""
    from routers.chat import _generate_config_version, VendorChatResponse
    cache_service = client.app.state.cache_service
    if not cache_service._is_available():
        pytest.skip("CACHE_ENABLED=false 或 redis 不可達 → 無法實測 handle_cache 命中(陷阱2)")
    cv = _generate_config_version()
    payload = VendorChatResponse(answer=answer, mode="b2c", timestamp="2026-06-28T00:00:00").dict()
    ok = cache_service.cache_answer(
        vendor_id=vendor_id, question=question, answer_data=payload,
        target_user=target_user, config_version=cv,
    )
    assert ok, "prime cache 應成功"
    return cache_service, cv


@pytest.mark.req("chat-flow-refactor:5.1")
def test_cache_hit_nonstream_returns_cached_json(client):
    """陷阱2:非串流命中 → handle_cache 回 _check_cache 的 JSON(跳過檢索)。"""
    q = "GAPTEST 緩存命中非串流問題"
    cache_service, cv = _prime_cache(client, vendor_id=V, question=q, target_user="tenant", answer="CACHED-NONSTREAM-SENTINEL")
    try:
        r = client.post("/api/v1/message", json={
            "message": q, "vendor_id": V, "target_user": "tenant", "stream": False})
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/json")
        assert r.json().get("answer") == "CACHED-NONSTREAM-SENTINEL", "應直接回緩存答案(證明走 handle_cache 命中、未進檢索)"
    finally:
        cache_service.redis_client.delete(cache_service._make_question_key(V, q, "tenant", cv))


@pytest.mark.req("chat-flow-refactor:5.1")
def test_cache_hit_stream_returns_sse(client):
    """陷阱2:串流命中 → handle_cache 回 stream_cached_answer 的 SSE(自有串流機制)。"""
    q = "GAPTEST 緩存命中串流問題"
    cache_service, cv = _prime_cache(client, vendor_id=V, question=q, target_user="tenant", answer="CACHED-STREAM-SENTINEL")
    try:
        r = client.post("/api/v1/message", json={
            "message": q, "vendor_id": V, "target_user": "tenant", "stream": True})
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/event-stream")
        # stream_cached_answer 逐 token 切片 → 重組 answer_chunk 還原緩存答案(陷阱2 自有串流機制)
        chunks = []
        for ln in r.text.splitlines():
            if ln.startswith("data: "):
                try:
                    obj = json.loads(ln[len("data: "):])
                except ValueError:
                    continue
                if "chunk" in obj:
                    chunks.append(obj["chunk"])
        assert "".join(chunks) == "CACHED-STREAM-SENTINEL", f"重組後應等於緩存答案,實得 {chunks}"
        assert '"cached": true' in r.text, "SSE 應標記來自緩存"
    finally:
        cache_service.redis_client.delete(cache_service._make_question_key(V, q, "tenant", cv))


# ── handle_retrieval 知識串流合成(Stage 3 動到、原 e2e 未涵蓋)──────────────

@pytest.mark.req("chat-flow-refactor:1.2")
def test_b2c_knowledge_stream_synthesis_event_sequence(client):
    """b2c 租客**串流**知識:走 handle_retrieval 知識串流合成 → SSE start…answer_chunk…done。"""
    r = client.post("/api/v1/message", json={
        "message": "請問怎麼繳租金",
        "vendor_id": V, "target_user": "tenant",
        "session_id": "gap-b2c-stream-1", "stream": True})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    types = [ln[len("event: "):] for ln in r.text.splitlines() if ln.startswith("event: ")]
    assert types, f"未收到任何 SSE 事件：{r.text[:200]}"
    assert types[0] == "start"
    assert "answer_chunk" in types
    assert types[-1] == "done"
    assert types.index("start") < types.index("answer_chunk") < types.index("done")


# ── handle_form_session REVIEWING 確認(原僅驗取消)──────────────────────

@pytest.mark.req("chat-flow-refactor:1.1")
def test_reviewing_confirm_nonstream_returns_json(client, db):
    """REVIEWING 確認 → _complete_form → _finalize_response(JSON)。釘住確認分支可跑通。"""
    sid = "gap-review-confirm-1"
    _seed_session(db, sid, "REVIEWING")
    try:
        r = client.post("/api/v1/message", json={
            "message": "確認", "vendor_id": V, "session_id": sid, "stream": False})
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/json")
        assert "answer" in r.json()
    finally:
        _cleanup(db, sid)


# ── handle_image 損壞非串流(原僅驗損壞串流)────────────────────────────

def _patch_image(monkeypatch, *, is_damage):
    import services.image_recognition_service as irs

    async def _fake_analyze(self, *a, **k):
        return {"is_damage": is_damage, "confidence": 0.9, "description": "測試辨識"}

    monkeypatch.setattr(irs, "is_image_recognition_enabled", lambda: True)
    monkeypatch.setattr(irs.ImageRecognitionService, "analyze_images", _fake_analyze)


@pytest.mark.req("chat-flow-refactor:1.1")
def test_image_damage_nonstream_returns_json(client, monkeypatch):
    """損壞圖片 + 非串流 → handle_image 回 _finalize_response(JSON)(原僅驗串流)。"""
    _patch_image(monkeypatch, is_damage=True)
    r = client.post("/api/v1/message", json={
        "message": "牆壁裂開了", "vendor_id": V, "image_urls": ["https://x/a.jpg"], "stream": False})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
