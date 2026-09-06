"""integration：內容已審謂詞在真 DB 上的行為（spec knowledge-outline-and-intent-architecture 3.1）。

真測試庫。**每個測試都在一筆交易裡跑完就 rollback**，⛔ 不留痕——包含
migration 那條（`ADD CONSTRAINT` 也在交易內，rollback 後測試庫沒有這個約束）。

本檔要證明的四件事（Plan §5）：
1. `fetch_visible_row` 真的多了一道閘門：現況 29 列用的 `owner-20260905`
   在新謂詞下**不可見**；同一列改成 `reviewed:test` 就可見（正對照）。
2. 那道閘門**不是**可見性謂詞在做事：一列在 `build_visibility_predicate`
   下可見但未審 ⇒ `NO_MATCH`；一列已審但在池外 ⇒ 仍 `NO_MATCH`（29 沒被削弱）。
3. Plan §3 真值表的 PG 側判定與 Python 鏡像逐值相同（含 U+3000 全形空白——
   兩邊分歧與否**以 DB 為準**，本檔記錄實查結果）。
4. migration 的 `NOT VALID` 是必要的：對含 `owner-20260905` 的表
   `ADD … NOT VALID` 成功、`VALIDATE` 失敗；重跑冪等。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗（⛔ 不得寫入非測試資料）。
"""
import os

import psycopg2
import pytest

from services.agent.canon.review_state import (
    DOMAIN_REGEX,
    REVIEWED_REGEX,
    is_domain_value,
    is_reviewed_value,
)
from services.agent.identity import Identity
from services.agent.outline import build_prospect_outline
from services.agent.tools.kb import fetch_visible_row, kb_get

pytestmark = pytest.mark.integration

_SPEC = "knowledge-outline-and-intent-architecture:3.1"

#: 明示 id 起點（與 test_kb_tools_req.py／test_outline_req.py 同理由：
#: ⛔ 不靠 serial 預設值）。本檔全程在交易內，用完 rollback。
BASE_ID = 9_400_000
LEGACY_MARK_ID = BASE_ID + 1      # outline_approved_by='owner-20260905'（現況 29 列的形狀）
UNREVIEWED_ID = BASE_ID + 2       # 可見性放行但未審
REVIEWED_OUT_OF_POOL_ID = BASE_ID + 3  # 已審但跨業者
REVIEWED_CONTROL_ID = BASE_ID + 4      # 已審且在池內（正對照）
PROSPECT_ROW_ID = BASE_ID + 5     # 售前池（b2b）用

VIEWER_VENDOR_ID = 1
OTHER_VENDOR_ID = 999

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260907_outline_approved_by_domain.sql",
)
_ROLLBACK = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations", "rollback",
    "20260907_outline_approved_by_domain_rollback.sql",
)
_CONSTRAINT_NAME = "chk_outline_approved_by_domain"

#: Plan §3 真值表（`None` 另測，SQL 的 NULL 不走 `~`）。
DOMAIN_TABLE = [
    "reviewed:owner",
    "reviewed:王",
    "reviewed:",
    "reviewed: ",
    "reviewed: alice",
    "reviewed:\tbob",
    "reviewed:　bob",   # U+3000
    "Reviewed:owner",
    " reviewed:owner",
    "REVIEWED:owner",
    "pool-marked-20260905",
    "pool-marked-2026",
    "owner-20260905",
    "",
]


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
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ 內容已審謂詞整合測試未驗")


class _SingleConnPool:
    """psycopg2 pool 介面的最小替身——⚠️ 交給被測程式的是**同一條交易連線**，
    它讀得到本交易未提交的寫入，rollback 後一併消失。"""

    def __init__(self, conn):
        self._conn = conn

    def getconn(self):
        return self._conn

    def putconn(self, conn):
        assert conn is self._conn


@pytest.fixture
def txn():
    """⛔ 不 autocommit：整個測試跑在一筆交易裡，teardown 一律 rollback。"""
    conn = _connect()
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        stale = cur.fetchone()[0]
        assert stale == 0, (
            f"id 區間 {BASE_ID}–{BASE_ID + 100} 已有 {stale} 列非本測試的資料——⛔ 拒絕覆蓋"
        )
        cur.close()
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _insert(cur, row_id, *, approved_by, vendor_ids=None, business_types=None,
            categories=None, question_summary="測試知識", answer="測試答案"):
    cur.execute(
        """
        INSERT INTO knowledge_base
            (id, question_summary, answer, categories, vendor_ids, business_types,
             target_user, is_active, category, outline_approved_by, outline_approved_at)
        VALUES (%s, %s, %s, %s::text[], %s::int[], %s::text[], NULL, TRUE, NULL, %s,
                CASE WHEN %s::text IS NULL THEN NULL ELSE now() END)
        """,
        (row_id, question_summary, answer, categories, vendor_ids, business_types,
         approved_by, approved_by),
    )


def _viewer():
    return Identity(vendor_id=VIEWER_VENDOR_ID, target_user="tenant", mode="b2c", api_key_id=1)


# ── ① 現況 29 列的標記在新謂詞下不可見；改成 reviewed: 就可見 ────────────

@pytest.mark.req(_SPEC)
def test_legacy_owner_mark_is_invisible_then_visible_after_rewrite(txn):
    """`owner-20260905`（現況 29 列的值）⇒ 取不到；同一列改 `reviewed:test` ⇒ 取得到。

    ⚠️ 這不是回歸：D1 前整池對 agent 路徑視為未審，是 Plan §3 明列的預期。
    後半段是**正對照**——若改成 `reviewed:test` 也取不到，代表謂詞或連線壞了，
    前半段的「取不到」就不能採信。
    """
    cur = txn.cursor()
    _insert(cur, LEGACY_MARK_ID, approved_by="owner-20260905")
    pool = _SingleConnPool(txn)

    assert fetch_visible_row(pool, _viewer(), LEGACY_MARK_ID) is None, (
        "值域外的舊標記 owner-20260905 竟然通過內容已審謂詞"
    )

    cur.execute(
        "UPDATE knowledge_base SET outline_approved_by = %s WHERE id = %s",
        ("reviewed:test", LEGACY_MARK_ID),
    )
    row = fetch_visible_row(pool, _viewer(), LEGACY_MARK_ID)
    assert row is not None, (
        "正對照失敗：改成 reviewed:test 後仍取不到——上面的「不可見」可能只是量尺壞了"
    )
    assert row[0] == LEGACY_MARK_ID
    cur.close()


@pytest.mark.req(_SPEC)
async def test_kb_get_returns_no_match_for_unreviewed_row(txn):
    """`kb.get` 對未審列回**同一個** `NO_MATCH`（⛔ 不對模型區分未審／不存在）。"""
    cur = txn.cursor()
    _insert(cur, LEGACY_MARK_ID, approved_by="owner-20260905")
    pool = _SingleConnPool(txn)
    result = await kb_get(_viewer(), {"kb_id": str(LEGACY_MARK_ID)}, db_pool=pool)
    assert result.ok is False and result.error == "NO_MATCH"
    cur.close()


# ── ② 證明是**第二道**謂詞在做事，且第一道沒被削弱 ──────────────────────

@pytest.mark.req(_SPEC)
def test_visible_but_unreviewed_row_is_no_match(txn):
    """一列在 `build_visibility_predicate` 下可見（形狀與正對照列相同）但未審 ⇒ 取不到。"""
    cur = txn.cursor()
    _insert(cur, UNREVIEWED_ID, approved_by=None)
    _insert(cur, REVIEWED_CONTROL_ID, approved_by="reviewed:test")
    pool = _SingleConnPool(txn)

    assert fetch_visible_row(pool, _viewer(), REVIEWED_CONTROL_ID) is not None, (
        "正對照列（同形狀、已審）取不到——量尺壞了，下面的斷言不可信"
    )
    assert fetch_visible_row(pool, _viewer(), UNREVIEWED_ID) is None, (
        "未審列被取回——第二道謂詞沒有在做事"
    )
    cur.close()


@pytest.mark.req(_SPEC)
def test_reviewed_row_outside_pool_is_still_no_match(txn):
    """已審但跨業者 ⇒ 仍 `NO_MATCH`——⛔ 新謂詞不得削弱既有的池隔離（不變量 29）。"""
    cur = txn.cursor()
    _insert(cur, REVIEWED_OUT_OF_POOL_ID, approved_by="reviewed:test",
            vendor_ids=[OTHER_VENDOR_ID])
    _insert(cur, REVIEWED_CONTROL_ID, approved_by="reviewed:test")
    pool = _SingleConnPool(txn)

    assert fetch_visible_row(pool, _viewer(), REVIEWED_CONTROL_ID) is not None, (
        "正對照列取不到——量尺壞了"
    )
    assert fetch_visible_row(pool, _viewer(), REVIEWED_OUT_OF_POOL_ID) is None, (
        "已審的跨業者列被取回——池隔離被新謂詞削弱了"
    )
    cur.close()


# ── ③ §3 真值表：PG 實查 vs Python 鏡像 ────────────────────────────────

@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("value", DOMAIN_TABLE)
def test_domain_table_matches_python_mirror(txn, value):
    """PG 的 `~` 與 Python `re.fullmatch` 對每個值判定相同。

    ⚠️ U+3000（全形空白）是已知的潛在分歧點（PG 的 `[[:space:]]` 依 locale，
    Python 的 `\\S` 依 unicode 屬性）。2026-09-07 實查兩邊皆判**不合法**，
    本測試把這個結果釘住——**以 DB 為準**：日後 DB 側若改變，這條會紅，
    ⛔ 屆時要改的是 Python 鏡像，不是把這條測試放寬。
    """
    cur = txn.cursor()
    cur.execute("SELECT %s ~ %s, %s ~ %s", (value, REVIEWED_REGEX, value, DOMAIN_REGEX))
    pg_reviewed, pg_domain = cur.fetchone()
    cur.close()
    assert pg_reviewed == is_reviewed_value(value), (
        f"{value!r}：PG 判可見={pg_reviewed}，Python 鏡像={is_reviewed_value(value)}"
    )
    assert pg_domain == is_domain_value(value), (
        f"{value!r}：PG 判值域={pg_domain}，Python 鏡像={is_domain_value(value)}"
    )


@pytest.mark.req(_SPEC)
def test_visible_set_is_subset_of_domain_in_postgres(txn):
    """可見 ⊂ CHECK 允許——含 `pool-marked-` 反例（允許但不可見）。"""
    cur = txn.cursor()
    for value in DOMAIN_TABLE:
        cur.execute("SELECT %s ~ %s, %s ~ %s", (value, REVIEWED_REGEX, value, DOMAIN_REGEX))
        visible, allowed = cur.fetchone()
        if visible:
            assert allowed, f"{value!r} 可見卻不在值域內"
    cur.execute("SELECT %s ~ %s, %s ~ %s",
                ("pool-marked-20260905", REVIEWED_REGEX,
                 "pool-marked-20260905", DOMAIN_REGEX))
    visible, allowed = cur.fetchone()
    assert (visible, allowed) == (False, True), "池標記必須是「允許但不可見」"
    cur.close()


# ── ④ 0 列已審時的售前大綱（兩個固定節仍在，⛔ 不 raise）─────────────────

def _prospect_row_kwargs():
    return dict(
        approved_by="reviewed:test",
        business_types=["system_provider"],   # 售前池＝b2b 池
        categories=["售前模組"],
        question_summary="修繕系統 線上報修",
        answer="可線上報修並追蹤進度。",
    )


@pytest.mark.req(_SPEC)
async def test_prospect_outline_with_zero_reviewed_rows_keeps_fixed_sections(txn):
    """已審 0 列 ⇒ 不 raise、只剩兩個固定節、所有 `source_ids` 皆空。

    ⛔ 這不是「空大綱」：`outline:deliberate-gaps`（DSP-009）與 `outline:cta`
    是常數文字、無資料來源，無論池內幾列都會附上。
    """
    cur = txn.cursor()
    # 交易內把所有已審列清成 NULL——⛔ rollback 後不留痕。
    cur.execute(
        "UPDATE knowledge_base SET outline_approved_by = NULL WHERE outline_approved_by ~ %s",
        (REVIEWED_REGEX,),
    )
    cur.execute("SELECT count(*) FROM knowledge_base WHERE outline_approved_by ~ %s",
                (REVIEWED_REGEX,))
    assert cur.fetchone()[0] == 0, "前置條件沒達成：交易內仍有已審列"

    doc = await build_prospect_outline(_SingleConnPool(txn))
    assert len(doc.sections) == 2, [s.id for s in doc.sections]
    assert {s.id for s in doc.sections} == {"outline:deliberate-gaps", "outline:cta"}
    assert all(not s.source_ids for s in doc.sections)
    cur.close()


@pytest.mark.req(_SPEC)
async def test_prospect_outline_with_one_reviewed_row_gains_a_section(txn):
    """正對照：交易內塞一列 `reviewed:test` ⇒ 3 節，新增節帶 1 個 source id。"""
    cur = txn.cursor()
    cur.execute(
        "UPDATE knowledge_base SET outline_approved_by = NULL WHERE outline_approved_by ~ %s",
        (REVIEWED_REGEX,),
    )
    _insert(cur, PROSPECT_ROW_ID, **_prospect_row_kwargs())

    doc = await build_prospect_outline(_SingleConnPool(txn))
    assert len(doc.sections) == 3, [s.id for s in doc.sections]
    new_sections = [s for s in doc.sections
                    if s.id not in ("outline:deliberate-gaps", "outline:cta")]
    assert len(new_sections) == 1
    assert new_sections[0].source_ids == [PROSPECT_ROW_ID]
    cur.close()


@pytest.mark.req(_SPEC)
async def test_prospect_outline_ignores_legacy_owner_mark(txn):
    """`owner-20260905` 的列 ⛔ 不得進大綱（F1：`IS NOT NULL` 會把 29 列當已審）。"""
    cur = txn.cursor()
    cur.execute(
        "UPDATE knowledge_base SET outline_approved_by = NULL WHERE outline_approved_by ~ %s",
        (REVIEWED_REGEX,),
    )
    kwargs = _prospect_row_kwargs()
    kwargs["approved_by"] = "owner-20260905"
    _insert(cur, PROSPECT_ROW_ID, **kwargs)

    doc = await build_prospect_outline(_SingleConnPool(txn))
    assert len(doc.sections) == 2, [s.id for s in doc.sections]
    assert all(PROSPECT_ROW_ID not in s.source_ids for s in doc.sections)
    cur.close()


# ── ⑤ migration：NOT VALID 成功、VALIDATE 失敗、重跑冪等 ────────────────

@pytest.mark.req(_SPEC)
def test_migration_not_valid_succeeds_validate_fails_and_is_idempotent(txn):
    """交易內套 migration：`ADD … NOT VALID` 過、`VALIDATE` 撞既有列、重跑冪等。

    ⚠️ 全程在交易內，rollback 後測試庫**沒有**這個約束（其他測試不受影響）。
    """
    with open(_MIGRATION, encoding="utf-8") as f:
        migration_sql = f.read()

    cur = txn.cursor()
    # 先造一列值域外的資料——這正是 live DB 現況 29 列的形狀。
    _insert(cur, LEGACY_MARK_ID, approved_by="owner-20260905")

    # ① ADD … NOT VALID：即使表內有違規列也必須成功
    cur.execute(migration_sql)
    cur.execute(
        "SELECT convalidated FROM pg_constraint "
        "WHERE conname = %s AND conrelid = 'knowledge_base'::regclass",
        (_CONSTRAINT_NAME,),
    )
    row = cur.fetchone()
    assert row is not None, "約束沒被加上"
    assert row[0] is False, "約束不該是 validated——少了 NOT VALID，D1 前會炸"

    # ② 冪等：再套一次不報錯、仍只有一筆
    cur.execute(migration_sql)
    cur.execute(
        "SELECT count(*) FROM pg_constraint "
        "WHERE conname = %s AND conrelid = 'knowledge_base'::regclass",
        (_CONSTRAINT_NAME,),
    )
    assert cur.fetchone()[0] == 1

    # ③ 對新寫入即刻生效：值域外的值寫不進去，值域內的寫得進去
    cur.execute("SAVEPOINT sp_bad_insert")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert(cur, UNREVIEWED_ID, approved_by="owner-20260905")
    cur.execute("ROLLBACK TO SAVEPOINT sp_bad_insert")
    _insert(cur, UNREVIEWED_ID, approved_by="reviewed:test")   # 正對照：值域內寫得進去

    # ④ VALIDATE 在 D1 改寫既有列之前必須失敗（那 29 列還在）
    cur.execute("SAVEPOINT sp_validate")
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute(f"ALTER TABLE knowledge_base VALIDATE CONSTRAINT {_CONSTRAINT_NAME}")
    cur.execute("ROLLBACK TO SAVEPOINT sp_validate")

    # ⑤ D1 之後（改寫成 pool-marked-<date>）VALIDATE 才會過
    cur.execute(
        "UPDATE knowledge_base SET outline_approved_by = %s WHERE outline_approved_by = %s",
        ("pool-marked-20260905", "owner-20260905"),
    )
    cur.execute(f"ALTER TABLE knowledge_base VALIDATE CONSTRAINT {_CONSTRAINT_NAME}")
    cur.execute(
        "SELECT convalidated FROM pg_constraint "
        "WHERE conname = %s AND conrelid = 'knowledge_base'::regclass",
        (_CONSTRAINT_NAME,),
    )
    assert cur.fetchone()[0] is True

    # ⑥ 回滾檔真的拆得掉（⛔ 不只是「檔案存在」）
    with open(_ROLLBACK, encoding="utf-8") as f:
        cur.execute(f.read())
    cur.execute(
        "SELECT count(*) FROM pg_constraint "
        "WHERE conname = %s AND conrelid = 'knowledge_base'::regclass",
        (_CONSTRAINT_NAME,),
    )
    assert cur.fetchone()[0] == 0
    cur.close()
