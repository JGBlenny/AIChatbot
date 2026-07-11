"""e2e：知識層 manual 觸發全流程（spec trigger-vocabulary-debt task 5.1｜R1.2, R4.2）。

驗收本 spec 的核心：修斷鏈（task 1.1）後，一筆 `trigger_mode='manual'` ＋
`trigger_keywords` 的表單知識，其觸發配置**終於生效**——命中不再直觸發表單，
而是走 SOP orchestrator 的關鍵詞確認流程（chat.py:2984 → sop_orchestrator
.handle_knowledge_trigger → trigger_handler）。

真打 /api/v1/message（HTTP，非程序內 TestClient）：沿用前置執行者作法，
以當前源碼另起臨時 rag 容器接 aichatbot_default 網路對真 DB／embedding／Redis
測——常駐容器是舊碼（無 1.1 透傳），會靜默降級為 auto 直觸發，測不到本行為。

三段斷言（同一筆自建自清的 fixture 知識）：
  a. 問句命中（用 question_summary 原文，相似度最穩 ≥0.75 表單觸發線）
     → **等待確認**：form_triggered 不為 true、回應含關鍵詞引導語。
  b. 同 session 回「確認」（trigger_keywords 之一）→ 表單觸發（form_triggered
     或 current_field 出現）。
  c. 新 session 重新命中（→ 等待）後回「不用了」（非關鍵詞）→ 不觸發表單
     （走 sop_orchestrator 的 wait_for_keywords 拒絕分支）。

fixture 自建自清：建知識列（含 embedding）→ 測 → finally 刪知識列＋清該
session 的 form_sessions 測試列＋清 SOP context（Redis 由 TTL 自然過期，另
以獨特 session id 隔離）。

環境（皆可 env 覆寫）：
  RAG_BASE_URL      預設 http://localhost:8111（臨時容器）
  EMBEDDING_URL     預設 http://localhost:5001/api/v1/embeddings（embedding-api 對外埠）
  DB_*              預設 localhost:5432 / aichatbot / aichatbot_admin
需 RUN_E2E=1；相依（容器／embedding／DB）不可用時明確 skip，不假綠燈。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

RAG_BASE_URL = os.getenv("RAG_BASE_URL", "http://localhost:8111")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:5001/api/v1/embeddings")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))

# 挑 dev 庫存在、欄位最簡（單欄）的表單當觸發標的——避免多欄流程雜訊。
FIXTURE_FORM_ID = os.getenv("TEST_TRIGGER_FORM_ID", "deposit_info_form_v2")
# 獨特詞避免撞既有知識，且作為問句原文求最高相似度。
FIXTURE_QUESTION = "觸發語彙測試報修九九"
FIXTURE_ANSWER = "這是 trigger-vocabulary-debt e2e 專用的測試知識，請忽略。"
TRIGGER_KEYWORDS = ["確認", "開始"]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _require_deps():
    """相依健檢：DB 可連、embedding-api 可用、rag 端點活著；缺任一 → skip。"""
    try:
        import psycopg2  # noqa: F401
        import httpx  # noqa: F401
    except ImportError as e:  # pragma: no cover
        pytest.skip(f"缺測試套件（psycopg2/httpx）：{e}")

    import httpx
    import psycopg2

    try:
        conn = psycopg2.connect(**_conn_kwargs())
        conn.close()
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")

    try:
        r = httpx.post(EMBEDDING_URL, json={"text": "健檢"}, timeout=20.0)
        if r.status_code != 200 or not r.json().get("embedding"):
            pytest.skip(f"embedding-api 不可用（{EMBEDDING_URL} → {r.status_code}）")
    except Exception as e:
        pytest.skip(f"embedding-api 不可連（{EMBEDDING_URL}）：{e}")

    try:
        r = httpx.post(
            f"{RAG_BASE_URL}/api/v1/message",
            json={"message": "健檢", "vendor_id": VENDOR_ID,
                  "target_user": "tenant", "session_id": f"trigvocab-ping-{uuid.uuid4().hex[:8]}",
                  "stream": False},
            timeout=60.0)
        if r.status_code != 200:
            pytest.skip(f"rag /message 不健康（{RAG_BASE_URL} → {r.status_code}）")
    except Exception as e:
        pytest.skip(f"rag 端點不可連（{RAG_BASE_URL}）：{e}")


def _embed(text):
    import httpx
    r = httpx.post(EMBEDDING_URL, json={"text": text}, timeout=30.0)
    r.raise_for_status()
    return r.json()["embedding"]


def _insert_fixture():
    """建一筆 manual 觸發的表單知識（含 embedding），回傳知識 id。"""
    import psycopg2
    embedding = _embed(FIXTURE_QUESTION)
    conn = psycopg2.connect(**_conn_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base
                    (question_summary, answer, business_types, target_user,
                     category, is_active, form_id, action_type,
                     trigger_mode, trigger_keywords, vendor_ids, embedding)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, 'form_fill',
                        'manual', %s, '{}'::int[], %s::vector)
                RETURNING id
                """,
                (FIXTURE_QUESTION, FIXTURE_ANSWER,
                 ["property_management"], ["tenant"],
                 "測試", FIXTURE_FORM_ID, TRIGGER_KEYWORDS, str(embedding)),
            )
            kid = cur.fetchone()[0]
        conn.commit()
        return kid
    finally:
        conn.close()


def _cleanup(kid, session_ids):
    import psycopg2
    conn = psycopg2.connect(**_conn_kwargs())
    try:
        with conn.cursor() as cur:
            if kid is not None:
                cur.execute("DELETE FROM knowledge_base WHERE id = %s", (kid,))
            for sid in session_ids:
                cur.execute("DELETE FROM form_sessions WHERE session_id = %s", (sid,))
        conn.commit()
    finally:
        conn.close()


def _post(message, session_id):
    import httpx
    r = httpx.post(
        f"{RAG_BASE_URL}/api/v1/message",
        json={"message": message, "vendor_id": VENDOR_ID, "target_user": "tenant",
              "mode": "b2c", "session_id": session_id, "stream": False,
              "include_debug_info": True},
        timeout=90.0)
    assert r.status_code == 200, f"/message {r.status_code}: {r.text[:500]}"
    return r.json()


def _is_form_triggered(resp):
    """表單是否真的開始收欄位：form_triggered 為真、或 current_field 已出現。"""
    return bool(resp.get("form_triggered")) or bool(resp.get("current_field"))


@pytest.mark.req("trigger-vocabulary-debt:1.2")
@pytest.mark.req("trigger-vocabulary-debt:4.2")
def test_manual_trigger_full_flow():
    _require_deps()

    sid_a = f"trigvocab-manual-{uuid.uuid4().hex[:8]}"   # 段 a/b：命中→等待→確認→觸發
    sid_c = f"trigvocab-reject-{uuid.uuid4().hex[:8]}"   # 段 c：命中→等待→非關鍵詞→不觸發
    kid = None
    try:
        kid = _insert_fixture()

        # ── 段 a：問句命中 → 等待確認（不直觸發表單）──────────────────
        r1 = _post(FIXTURE_QUESTION, sid_a)
        assert not _is_form_triggered(r1), (
            "manual 知識命中應等待確認、不直觸發表單，但 form_triggered/current_field "
            f"已出現：form_triggered={r1.get('form_triggered')}, "
            f"current_field={r1.get('current_field')}, answer={r1.get('answer', '')[:200]}"
        )
        answer1 = r1.get("answer") or ""
        assert any(k in answer1 for k in TRIGGER_KEYWORDS), (
            "等待確認回應應含關鍵詞引導語（trigger_handler manual 模式自動附觸發詞提示），"
            f"實得 answer={answer1[:300]}"
        )

        # ── 段 b：同 session 回關鍵詞「確認」→ 表單觸發 ────────────────
        r2 = _post("確認", sid_a)
        assert _is_form_triggered(r2), (
            "回覆關鍵詞後應觸發表單（form_triggered=true 或 current_field 出現），"
            f"實得 form_triggered={r2.get('form_triggered')}, "
            f"current_field={r2.get('current_field')}, answer={r2.get('answer', '')[:300]}"
        )

        # ── 段 c：新 session 命中→等待→回非關鍵詞「不用了」→ 不觸發 ────
        r3 = _post(FIXTURE_QUESTION, sid_c)
        assert not _is_form_triggered(r3), (
            "新 session 首次命中應等待確認、不直觸發，"
            f"實得 form_triggered={r3.get('form_triggered')}, current_field={r3.get('current_field')}"
        )
        r4 = _post("不用了", sid_c)
        assert not _is_form_triggered(r4), (
            "回覆非關鍵詞不應觸發表單（sop_orchestrator wait_for_keywords 拒絕分支），"
            f"實得 form_triggered={r4.get('form_triggered')}, "
            f"current_field={r4.get('current_field')}, answer={r4.get('answer', '')[:300]}"
        )
    finally:
        _cleanup(kid, [sid_a, sid_c])
