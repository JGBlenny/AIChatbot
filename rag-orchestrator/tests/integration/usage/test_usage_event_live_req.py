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


# 已知仲裁識別字串（chat.py _smart_retrieval_with_comparison 之 decision_case 全集）
_ARB_CASES = {
    "sop_cancelled_by_user", "sop_triggered_action_executed",
    "sop_waiting_for_keyword_use_knowledge", "sop_waiting_both_below_threshold",
    "sop_significantly_higher", "knowledge_significantly_higher",
    "close_scores_sop_has_action", "close_scores_sop_slightly_higher",
    "close_scores_knowledge_slightly_higher", "only_sop_qualified",
    "only_knowledge_qualified", "both_below_threshold",
}


def _post_b2c(session_id, message, vendor_id=2):
    """b2c 路徑：走 SOP vs 知識檢索仲裁（b2b 早退無 comparison）。"""
    import requests
    return requests.post(f"{RAG}/api/v1/message", json={
        "message": message, "vendor_id": vendor_id, "mode": "b2c",
        "target_user": "tenant", "session_id": session_id}, timeout=90)


def _fetch_scores(session_id, retries=15, want_scores=None):
    """撈回全部事件的分數欄；want_scores=True 時等到出現帶分數的事件才回。"""
    conn = _db()
    rows = []
    try:
        for _ in range(retries):
            with conn.cursor() as cur:
                cur.execute("""SELECT knowledge_score, sop_score, decision_case,
                                      duration_ms
                               FROM usage_events WHERE session_id=%s
                               ORDER BY ts""", (session_id,))
                rows = cur.fetchall()
            if rows:
                if want_scores is None:
                    return rows
                has = any(r[0] is not None or r[2] is not None for r in rows)
                if has == want_scores:
                    return rows
            time.sleep(1)
        return rows
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


# ════════════════════════════════════════════════════════════
# task 3.3：檢索仲裁分數埋點掛線（R3.1/3.2）
# 需 M1 已套（usage_events 有 knowledge_score/sop_score/decision_case 三欄）。
# ════════════════════════════════════════════════════════════

def _score_cols_exist():
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT count(*) FROM information_schema.columns
                           WHERE table_name='usage_events'
                             AND column_name IN
                                 ('knowledge_score','sop_score','decision_case')""")
            return cur.fetchone()[0] == 3
    finally:
        conn.close()


def test_arbitration_request_records_scores(live):
    """走檢索仲裁的**生產形狀**請求（不帶 include_debug_info）→ 事件帶三分數且
    decision_case 為既有仲裁識別字串。

    本案正是 task 3.3 修正要證明的：分數埋點已從 _build_debug_info（被 include_debug_info
    閘住）搬到 decision 誕生後的無條件生產點（_meter_comparison，chat.py handle_retrieval
    L745 旁），故不帶 debug flag 的正式流量亦記分數。b2c 模式才走 SOP↔知識仲裁
    （b2b 早退無 comparison）。
    """
    if not _score_cols_exist():
        pytest.skip("M1 未套（分數欄未建）——降級路徑另有 unit 覆蓋")
    sid = f"web_arb_{uuid.uuid4().hex[:10]}"
    import requests
    # b2c 繳租問句實測命中 knowledge_significantly_higher（必經 _smart_retrieval_with_comparison）
    # 生產形狀：刻意不帶 include_debug_info，證明正式流量也記分數。
    r = requests.post(f"{RAG}/api/v1/message", json={
        "message": "我要繳房租", "vendor_id": 2, "mode": "b2c",
        "target_user": "tenant", "session_id": sid}, timeout=90)
    assert r.status_code == 200
    rows = _fetch_scores(sid, want_scores=True)
    scored = [r for r in rows if r[0] is not None or r[2] is not None]
    assert scored, "走仲裁的請求應有一筆帶分數"
    k_score, s_score, case, _dur = scored[0]
    assert case in _ARB_CASES, f"decision_case 應為既有仲裁識別字串，實得 {case!r}"
    # 仲裁必有 knowledge/sop 至少一方有分；存在則落在 [0,1]（NUMERIC(4,3)）
    assert (k_score is not None) or (s_score is not None)
    for v in (k_score, s_score):
        if v is not None:
            assert 0.0 <= float(v) <= 1.0


def test_short_circuit_path_leaves_scores_null(live):
    """短路路徑（b2b 早退，不經 SOP↔知識仲裁）→ 該事件分數欄留 NULL。

    b2b 在 handle_retrieval 走 skip_sop else 分支／或早退，decision 無 'comparison' →
    _meter_comparison 以 falsy comparison 略過呼叫，三分數欄自然留 NULL。生產形狀（不帶
    include_debug_info）以確認正式流量下亦不誤埋。
    """
    if not _score_cols_exist():
        pytest.skip("M1 未套（分數欄未建）")
    sid = f"web_sc_{uuid.uuid4().hex[:10]}"
    import requests
    r = requests.post(f"{RAG}/api/v1/message", json={
        "message": "我要繳房租", "vendor_id": 2, "mode": "b2b",
        "target_user": "property_manager", "role_id": "37305",
        "session_id": sid}, timeout=90)
    assert r.status_code == 200
    rows = _fetch_scores(sid)
    assert rows, "短路路徑仍應落計量事件"
    for k_score, s_score, case, _dur in rows:
        assert k_score is None and s_score is None and case is None, \
            "短路路徑（b2b 早退）事件分數欄應為 NULL"
