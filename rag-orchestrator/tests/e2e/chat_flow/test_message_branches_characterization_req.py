"""e2e 特徵化(golden-master):釘住 /api/v1/message 分支的「現況行為」,作為重構安全網。

Stage 0(chat-flow-refactor 任務 1.1)。用 psycopg2 直接 seed form_sessions 狀態 → TestClient 打
/message → 斷言「現況」可觀察行為。重點守住:會話分支的串流/非串流、以及 EDITING **忽略串流**(陷阱1)。
需 RUN_E2E=1 + DB(app import 需 OPENAI_API_KEY,可 dummy;本檔分支不呼叫真 LLM)。
"""
import json
import os

import psycopg2
import pytest

pytestmark = pytest.mark.e2e

V = 2  # demo_form 所屬 vendor


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
            (session_id, "u-char", V, state, current_field_index, json.dumps(collected or {})),
        )


def _cleanup(db, session_id):
    with db.cursor() as cur:
        cur.execute("DELETE FROM form_sessions WHERE session_id = %s", (session_id,))


@pytest.mark.req("chat-flow-refactor:1.1")
def test_reviewing_cancel_nonstream_returns_json(client, db):
    sid = "char-review-cancel-1"
    _seed_session(db, sid, "REVIEWING")
    try:
        r = client.post("/api/v1/message", json={
            "message": "取消", "vendor_id": V, "session_id": sid, "stream": False})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        assert "answer" in r.json()
    finally:
        _cleanup(db, sid)


@pytest.mark.req("chat-flow-refactor:1.1")
def test_reviewing_cancel_stream_returns_sse(client, db):
    sid = "char-review-cancel-2"
    _seed_session(db, sid, "REVIEWING")
    try:
        r = client.post("/api/v1/message", json={
            "message": "取消", "vendor_id": V, "session_id": sid, "stream": True})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
    finally:
        _cleanup(db, sid)


@pytest.mark.req("chat-flow-refactor:1.1")
def test_editing_ignores_stream_returns_json(client, db):
    """陷阱1:EDITING 分支目前**不吃 stream**,即使 stream=True 也回 JSON。重構須保留此行為。"""
    sid = "char-editing-1"
    _seed_session(db, sid, "EDITING", current_field_index=0)
    try:
        r = client.post("/api/v1/message", json={
            "message": "個人房東", "vendor_id": V, "session_id": sid, "stream": True})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json"), \
            "EDITING 現況忽略 stream → 應回 JSON 而非 SSE(陷阱1)"
    finally:
        _cleanup(db, sid)
