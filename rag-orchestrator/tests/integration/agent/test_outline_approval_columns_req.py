"""integration：knowledge_base 審核旗標欄位可寫可讀（agentic-mcp-orchestration 任務 3.3，R11.6）。

真測試庫。套 migration（冪等）→ 插兩列：
- 已標記：`outline_approved_by`／`outline_approved_at` 皆有值 → 讀回應非 NULL。
- 未標記：兩欄皆 NULL（正對照組——若這列也讀到非 NULL，代表 migration 給錯了
  DEFAULT 或測試本身寫壞，不是欄位「本來就有值」）。

⛔ 本測試不驗 31 這個數字——那是 admin DB 的一次性 UPDATE 結果，不是本欄位本身
的契約，且測試庫沒有那 31 筆售前池資料。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗（⛔ 不得寫入非測試資料）。
用完在 finally 依 id 區間刪除，且開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import os

import psycopg2
import pytest

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:3.3"

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260905_knowledge_base_outline_approval.sql",
)

#: 明示 id 起點，⛔ 不靠 serial 預設值（與 test_kb_tools_req.py 同理由）。
BASE_ID = 9_200_000
APPROVED_ID = BASE_ID + 1
UNAPPROVED_ID = BASE_ID + 2
_ALL_IDS = [APPROVED_ID, UNAPPROVED_ID]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _connect():
    """連測試庫；不可達 ⇒ skip（⛔ 不是 fail），連到非測試庫 ⇒ 大聲失敗。"""
    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        return psycopg2.connect(**_conn_kwargs())
    except psycopg2.Error as e:
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ knowledge_base 審核旗標整合測試未驗")


@pytest.fixture
def db_conn():
    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        with open(_MIGRATION, encoding="utf-8") as f:
            cur.execute(f.read())

        cur.execute(
            "SELECT count(*) FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        stale = cur.fetchone()[0]
        assert stale == 0, (
            f"id 區間 {BASE_ID}–{BASE_ID + 100} 已有 {stale} 列非本測試的資料——"
            "⛔ 拒絕覆蓋，請先確認來源"
        )

        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, NULL, NULL, NULL, TRUE, NULL, %s, now())
            """,
            (APPROVED_ID, "已審核售前知識", "已標記進大綱", "owner-20260905"),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, NULL, NULL, NULL, TRUE, NULL, NULL, NULL)
            """,
            (UNAPPROVED_ID, "未審核售前知識", "未標記——正對照組"),
        )
        cur.close()
        yield conn
    finally:
        cleanup_cur = conn.cursor()
        cleanup_cur.execute(
            "DELETE FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        cleanup_cur.close()
        conn.close()


@pytest.mark.req(_SPEC)
def test_migration_is_idempotent(db_conn):
    """重跑 migration 不報錯（ADD COLUMN IF NOT EXISTS 冪等）。"""
    cur = db_conn.cursor()
    with open(_MIGRATION, encoding="utf-8") as f:
        cur.execute(f.read())  # 第二次套用不應丟例外
    cur.close()


@pytest.mark.req(_SPEC)
def test_outline_approved_columns_readable(db_conn):
    """已標記列讀回非 NULL；未標記列（正對照組）讀回 NULL——證明欄位本身不是預設有值。"""
    cur = db_conn.cursor()
    cur.execute(
        "SELECT outline_approved_by, outline_approved_at FROM knowledge_base WHERE id = %s",
        (APPROVED_ID,),
    )
    approved_by, approved_at = cur.fetchone()
    assert approved_by == "owner-20260905"
    assert approved_at is not None

    cur.execute(
        "SELECT outline_approved_by, outline_approved_at FROM knowledge_base WHERE id = %s",
        (UNAPPROVED_ID,),
    )
    unapproved_by, unapproved_at = cur.fetchone()
    assert unapproved_by is None
    assert unapproved_at is None
    cur.close()


@pytest.mark.req(_SPEC)
def test_columns_writable_via_update(db_conn):
    """欄位可事後 UPDATE 寫入（模擬一次性標記的寫入路徑，非驗證 31 這個數字）。"""
    cur = db_conn.cursor()
    cur.execute(
        """
        UPDATE knowledge_base
        SET outline_approved_by = 'owner-20260905', outline_approved_at = now()
        WHERE id = %s AND outline_approved_by IS NULL
        """,
        (UNAPPROVED_ID,),
    )
    assert cur.rowcount == 1

    cur.execute(
        "SELECT outline_approved_by FROM knowledge_base WHERE id = %s", (UNAPPROVED_ID,),
    )
    assert cur.fetchone()[0] == "owner-20260905"
    cur.close()
