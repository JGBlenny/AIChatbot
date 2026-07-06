"""integration：usage-metering 事件落地（任務 2.2｜R1.1/1.2/3.1/8.2）。

活體模式：需 RAG 服務與 DB 在線（env RAG_API_URL/DB_*），不可達則 skip——
沿 repo integration 層慣例（真實相依）。斷言鏈：真請求→事件恰一筆→維度齊→
內部前綴標記→非 /message 路徑零事件。
"""
import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.integration

RAG = os.getenv("RAG_API_URL", "http://localhost:8100")


def _db():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"))


def _post(session_id, message="測試計量"):
    import requests
    return requests.post(f"{RAG}/api/v1/message", json={
        "message": message, "vendor_id": 2, "mode": "b2b",
        "target_user": "property_manager", "role_id": "37305",
        "session_id": session_id}, timeout=90)


@pytest.fixture(scope="module")
def live():
    import requests
    try:
        r = requests.get(f"{RAG}/api/v1/vendors", timeout=5)
        assert r.status_code == 200
    except Exception:
        pytest.skip("RAG 服務不可達（integration 需真實相依）")
    try:
        _db().close()
    except Exception:
        pytest.skip("DB 不可達")


def _fetch(session_id, retries=10):
    conn = _db()
    try:
        for _ in range(retries):
            with conn.cursor() as cur:
                cur.execute("""SELECT vendor_id, mode, user_type, is_internal, internal_kind,
                                      status, duration_ms, llm_calls, message_len
                               FROM usage_events WHERE session_id=%s""", (session_id,))
                rows = cur.fetchall()
            if rows:
                return rows
            time.sleep(1)
        return []
    finally:
        conn.close()


def test_one_request_one_event_with_dimensions(live):
    sid = f"web_it_{uuid.uuid4().hex[:10]}"
    assert _post(sid).status_code == 200
    rows = _fetch(sid)
    assert len(rows) == 1, "一次請求恰落一筆（R1.1；冪等鍵防重）"
    vendor_id, mode, user_type, is_internal, kind, status, dur, llm_calls, mlen = rows[0]
    assert (vendor_id, mode, user_type) == (2, "b2b", "property_manager")
    assert is_internal is False and status == "success"
    assert dur and dur > 0 and mlen == len("測試計量")


def test_internal_prefix_marked(live):
    sid = f"backtest_it_{uuid.uuid4().hex[:10]}"
    assert _post(sid).status_code == 200
    rows = _fetch(sid)
    assert len(rows) == 1
    assert rows[0][3] is True and rows[0][4] == "backtest"   # is_internal / internal_kind


def test_non_message_path_zero_event(live):
    import requests
    requests.get(f"{RAG}/api/v1/vendors", timeout=10)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM usage_events WHERE session_id IS NULL AND message_len=0 AND ts > now() - interval '30 seconds'")
            # 無 session 的零長度事件不應因 GET /vendors 出現（白名單外零觸碰）
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()
