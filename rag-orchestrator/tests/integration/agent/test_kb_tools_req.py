"""integration：`kb.get` 池外＝NO_MATCH（spec agentic-mcp-orchestration 任務 1.4）。

真測試庫。灌三列：
- 跨業者（`vendor_ids=[999]`）——vendor 1 租客身分應看不到。
- 保留分類（`category='系統脈絡'`）——vendor_ids 為 NULL（否則會被業者過濾先擋掉，
  無法單獨證明是分類把它擋下）。
- 正對照組：`vendor_ids IS NULL`、無保留分類——同一身分應命中
  （若這列也 NO_MATCH，代表謂詞或連線本身壞了，不是「池外」本身在起作用）。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗（⛔ 不得寫入非測試資料）。
用完在 finally 依 id 區間刪除，且開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import os

import psycopg2
import pytest

from services.agent.identity import Identity
from services.agent.tools.kb import kb_get

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:1.4"

#: 明示 id 起點，⛔ 不靠 serial 預設值（與 test_visibility_predicate_equiv.py 同理由：
#: 測試庫的 knowledge_base_id_seq 與既有列 max(id) 可能不同步）。
BASE_ID = 9_100_000
CROSS_VENDOR_ID = BASE_ID + 1
RESERVED_CATEGORY_ID = BASE_ID + 2
CONTROL_ID = BASE_ID + 3
_ALL_IDS = [CROSS_VENDOR_ID, RESERVED_CATEGORY_ID, CONTROL_ID]

VIEWER_VENDOR_ID = 1  # 查詢方（vendor 1 租客）
OTHER_VENDOR_ID = 999  # 列本身歸屬的跨業者


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
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ kb.get 池外整合測試未驗")


class _SingleConnPool:
    """psycopg2 pool 介面的最小替身，包一條真連線給 `fetch_visible_row` 用。"""

    def __init__(self, conn):
        self._conn = conn

    def getconn(self):
        return self._conn

    def putconn(self, conn):
        assert conn is self._conn


@pytest.fixture
def db_pool():
    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor()
    try:
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
                 is_active, category)
            VALUES (%s, %s, %s, %s::int[], NULL, NULL, TRUE, NULL)
            """,
            (CROSS_VENDOR_ID, "跨業者知識", "只有 vendor 999 看得到", [OTHER_VENDOR_ID]),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category)
            VALUES (%s, %s, %s, NULL, NULL, NULL, TRUE, %s)
            """,
            (RESERVED_CATEGORY_ID, "系統脈絡知識", "保留分類，agent 不得取回", "系統脈絡"),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category)
            VALUES (%s, %s, %s, NULL, NULL, NULL, TRUE, NULL)
            """,
            (CONTROL_ID, "正對照知識", "一般知識，人人可見"),
        )
        cur.close()
        yield _SingleConnPool(conn)
    finally:
        cleanup_cur = conn.cursor()
        cleanup_cur.execute(
            "DELETE FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        cleanup_cur.close()
        conn.close()


def _viewer():
    return Identity(vendor_id=VIEWER_VENDOR_ID, target_user="tenant", mode="b2c", api_key_id=1)


@pytest.mark.req(_SPEC)
async def test_cross_vendor_row_is_no_match(db_pool):
    result = await kb_get(_viewer(), {"kb_id": str(CROSS_VENDOR_ID)}, db_pool=db_pool)
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_reserved_category_row_is_no_match(db_pool):
    result = await kb_get(_viewer(), {"kb_id": str(RESERVED_CATEGORY_ID)}, db_pool=db_pool)
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_positive_control_row_is_visible(db_pool):
    """正對照組：若這列也 NO_MATCH，代表謂詞或連線本身壞了——上面兩條紅燈不能採信。"""
    result = await kb_get(_viewer(), {"kb_id": str(CONTROL_ID)}, db_pool=db_pool)
    assert result.ok is True, (
        "正對照組（vendor_ids IS NULL、無保留分類）也被擋下——"
        "上面的 NO_MATCH 斷言可能只是量尺本身壞了，不是池外機制在作用"
    )
    assert result.data["id"] == CONTROL_ID
    assert result.data["answer"] == "一般知識，人人可見"
