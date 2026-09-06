"""integration：`OutlineAssembler`（spec agentic-mcp-orchestration 任務 3.2）。

真測試庫。灌三列：
- 已審列（`outline_approved_by='reviewed:test'`、`category IS NULL`）——prospect 大綱
  應含它（`source_ids` 含它、`outline_sha` 隨它變）。
- 未標記一般列（同形狀、`outline_approved_by IS NULL`）——正對照組的反面：
  它會被 `build_visibility_predicate(prospect)` 放行（形狀與已標記列相同），
  差別只在審核旗標；若它也進了大綱，代表 R11.6 的過濾沒接上。
- `系統脈絡` 列（`vendor_ids=[OWN_VENDOR_ID]`）——只給 `build_toc` 用；
  vendor 相符時應出現，vendor 不符時不應出現。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗（⛔ 不得寫入非測試資料）。
用完在 finally 依 id 區間刪除，且開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import os

import psycopg2
import pytest

from services.agent.outline import build_prospect_outline, build_toc

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:3.2"

#: 明示 id 起點，⛔ 不靠 serial 預設值（與 test_kb_tools_req.py／
#: test_outline_approval_columns_req.py 同理由）。
BASE_ID = 9_300_000
APPROVED_ID = BASE_ID + 1
UNAPPROVED_ID = BASE_ID + 2
SYSTEM_CONTEXT_ID = BASE_ID + 3
_ALL_IDS = [APPROVED_ID, UNAPPROVED_ID, SYSTEM_CONTEXT_ID]

OWN_VENDOR_ID = 4242
OTHER_VENDOR_ID = 4243


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
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ OutlineAssembler 整合測試未驗")


class _SingleConnPool:
    """psycopg2 pool 介面的最小替身，包一條真連線給 `outline.py` 的取列函式用。"""

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
                (id, question_summary, answer, categories, vendor_ids, business_types,
                 target_user, is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, %s::text[], NULL, ARRAY['system_provider']::text[], NULL, TRUE, NULL, %s, now())  -- 售前池是 b2b 池（business_types && ['system_provider']）
            """,
            (
                APPROVED_ID, "修繕系統 線上報修", "可線上報修並追蹤進度。",
                # ⚠️ 2026-09-07 起「已審」＝ `reviewed:<who>`（值域見
                # services/agent/canon/review_state.py）；⛔ 不能再用
                # `owner-20260905`——那是值域外的舊標記，新謂詞視為未審。
                ["售前模組"], "reviewed:test",
            ),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, categories, vendor_ids, business_types,
                 target_user, is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, %s::text[], NULL, ARRAY['system_provider']::text[], NULL, TRUE, NULL, NULL, NULL)
            """,
            (
                UNAPPROVED_ID, "未審核的售前知識", "這句不該進大綱。",
                ["售前模組"],
            ),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category)
            VALUES (%s, %s, %s, %s::int[], NULL, NULL, TRUE, %s)
            """,
            (
                SYSTEM_CONTEXT_ID, "系統整體介紹（測試用）", "這是系統脈絡測試內容。",
                [OWN_VENDOR_ID], "系統脈絡",
            ),
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


@pytest.mark.req(_SPEC)
async def test_prospect_outline_includes_only_approved_row(db_pool):
    doc = await build_prospect_outline(db_pool)
    all_source_ids = {sid for section in doc.sections for sid in section.source_ids}
    assert APPROVED_ID in all_source_ids
    assert UNAPPROVED_ID not in all_source_ids, (
        "未審核列（outline_approved_by IS NULL）出現在大綱 source_ids 裡——"
        "R11.6 的過濾沒接上"
    )
    assert SYSTEM_CONTEXT_ID not in all_source_ids, (
        "系統脈絡列出現在 prospect 大綱裡——build_visibility_predicate 應排除保留分類"
    )
    # 正對照組：至少要有一個非空 section 命中已標記列，否則上面兩個「不含」
    # 斷言可能只是查詢本身壞掉而非過濾機制在作用。
    repair_section = next(s for s in doc.sections if s.id == "outline:repair")
    assert repair_section.source_ids == [APPROVED_ID]


@pytest.mark.req(_SPEC)
async def test_prospect_outline_sha_reflects_pool_membership(db_pool):
    """把已標記列的內容改掉再重跑，sha 應變（快取失效判準）。"""
    doc_before = await build_prospect_outline(db_pool)

    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE knowledge_base SET answer = %s, updated_at = now() WHERE id = %s",
        ("可線上報修並追蹤進度（已更新）。", APPROVED_ID),
    )
    cur.close()
    db_pool.putconn(conn)

    doc_after = await build_prospect_outline(db_pool)
    assert doc_after.sha256 != doc_before.sha256
    assert doc_after.version != doc_before.version


@pytest.mark.req(_SPEC)
async def test_toc_includes_system_context_row_for_matching_vendor(db_pool):
    doc = await build_toc(db_pool, "property_manager", vendor_id=OWN_VENDOR_ID)
    ids = {sid for section in doc.sections for sid in section.source_ids}
    assert SYSTEM_CONTEXT_ID in ids
    matched = next(s for s in doc.sections if SYSTEM_CONTEXT_ID in s.source_ids)
    assert matched.citable is False


@pytest.mark.req(_SPEC)
async def test_toc_excludes_system_context_row_for_other_vendor(db_pool):
    doc = await build_toc(db_pool, "property_manager", vendor_id=OTHER_VENDOR_ID)
    ids = {sid for section in doc.sections for sid in section.source_ids}
    assert SYSTEM_CONTEXT_ID not in ids, (
        "vendor_ids=[OWN_VENDOR_ID] 的系統脈絡列被非該業者的 vendor_id 看到——"
        "build_toc 的 vendor 過濾沒生效"
    )
