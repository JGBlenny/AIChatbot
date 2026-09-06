"""integration：`FineIndex.visible_subset` ≡ `build_visibility_predicate`（任務 3.3b）。

Plan `inputs/plan-3.3-fine-index-selector-20260907.md` §1.7／§4.6。

## 這條測什麼
記憶體側的可見性（正本細目 → `canon_assembler.canon_visible`）與 SQL 側的可見性
（DB 列 → `build_visibility_predicate`）在**同一批等價資料**上撈到**同一個集合**。
⛔ 這不是拿產線碼驗產線碼：兩側是兩份**獨立實作**（一份是 Python 集合運算、
一份是 Postgres 陣列謂詞），本檔在真測試庫上比對它們的結果。

## 材料
合成正本 15 格矩陣：`target_user ∈ {[prospect],[property_manager],[tenant],[all_users],[]}`
×`business_types ∈ {[system_provider],[rental],[]}`，全部 `reviewed`；
另加**一列未審**細目當單向正對照。DB 側插等價列，
`generation_metadata->>'canon_ref'` ＝細目 id（回映用）。

⚠️ **空清單一律寫 NULL**（業主 2026-09-07 §8.2 裁）：記憶體規則的「空＝不設限」對應
SQL 的 `IS NULL` 放行；寫成 `'{}'` 空陣列會讓 `&&` 恆假、兩側立刻分歧。
⚠️ 匯入工具 `tools/import_facet_knowledge.py` 目前把空 `business_types` 預設成
`["system_provider"]`——與此假設**方向相反**，對帳留給不變量 33（3.5），本片不動它。

## 刻意的單向不對稱（⛔ 不得以放寬記憶體側來收斂）
`canon_visible` 首行以 `reviewed_by` 閘門，`build_visibility_predicate` **刻意沒有**
審核謂詞（正本無上架旗標，「未審＝不可引用」由 `reviewed_by` 承擔）。故未審細目
**只出現在 SQL 側**。比對集合一律取「已審細目」的交集，未審那列另以斷言釘住方向。

## 量尺自證
- `test_matrix_discriminates`：三組身分必須撈到**不同**且**非空**的集合，
  否則「處處相等」只是因為兩邊都瞎。
- `test_mutation_control_*`：翻一列業態 ⇒ 兩側同動；**只翻 DB 側** ⇒ 等式必須變紅。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗。用完在 `finally` 依 id 區間刪除。
⚠️ 全程只用 INSERT／DELETE，⛔ 不用 UPDATE——`update_kb_updated_at` trigger 會動
`updated_at`（不變量 10 連鎖的已知陷阱）。
"""
import json
import os
from pathlib import Path

import psycopg2
import pytest
from unittest.mock import MagicMock

from services.agent.canon.canon_parser import parse_canon, parse_canon_text
from services.agent.canon.fine_index import FineIndex
from services.agent.identity import Identity
from services.vendor_knowledge_retriever_v2 import build_visibility_predicate

pytestmark = [pytest.mark.integration]

_SPEC = "knowledge-outline-and-intent-architecture:3.3"

#: 測試列標記；`finally` 依此清理（⛔ 與 test_visibility_predicate_equiv.py 的標記不同）
MARKER = "__canon_vis_equiv__"
#: 明示 id 起點。⚠️ ⛔ 不靠 serial 預設值——測試庫的 `knowledge_base_id_seq` 與既有列
#: 的 max(id) 不同步（見 test_visibility_predicate_equiv.py 的實測註記）。
#: 9_000_000（差分等價）與 9_300_000（outline）已被占用，本檔取 9_100_000。
BASE_ID = 9_100_000
VENDOR_ID = 424244
#: b2c 業者的業態（`param_resolver` 替身注入；記憶體側同值傳入 `vendor_business_types`）
VENDOR_BT = ["rental"]


# ════════════════════════════════════════════════════════════════════
# 合成正本：15 格矩陣 ＋ 一列未審
# ════════════════════════════════════════════════════════════════════

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.equiv
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 等價矩陣 {#A}
"""

#: 矩陣兩軸（Plan §1.7 指定的 5×3）
_TARGET_USERS = [("prospect",), ("property_manager",), ("tenant",), ("all_users",), ()]
_BUSINESS_TYPES = [("system_provider",), ("rental",), ()]

_TU_SLUG = {("prospect",): "prospect", ("property_manager",): "pm", ("tenant",): "tenant",
            ("all_users",): "allusers", (): "notu"}
_BT_SLUG = {("system_provider",): "sysprov", ("rental",): "rental", (): "nobt"}

#: 未審細目：形狀與 `cell-prospect-sysprov` 相同，**只差沒有 `reviewed`**
UNREVIEWED_SLUG = "unreviewed-prospect-sysprov"
UNREVIEWED_TU, UNREVIEWED_BT = ("prospect",), ("system_provider",)


def _fid(slug: str) -> str:
    return f"prospect/A/{slug}"


def _cell_slug(tu, bt) -> str:
    return f"cell-{_TU_SLUG[tu]}-{_BT_SLUG[bt]}"


def _cells():
    """15 格，順序固定（⛔ 可重跑）。"""
    return [(tu, bt) for tu in _TARGET_USERS for bt in _BUSINESS_TYPES]


def _fine_block(slug, tu, bt, *, reviewed=True):
    lines = [
        f"### 矩陣細目{slug} {{#{_fid(slug)}}}",
        "- sources: [kb:1]",
        f"- target_user: [{', '.join(tu)}]",
        f"- business_types: [{', '.join(bt)}]",
    ]
    if reviewed:
        lines.append("- reviewed: {by: test, at: 2026-09-07}")
    lines += ["- instance_applicability: general", f"矩陣內容句{slug}", ""]
    return "\n".join(lines)


def _canon_text(overrides=None):
    """矩陣正本全文；`overrides={slug: (tu, bt)}` 用於突變控制。"""
    overrides = overrides or {}
    blocks = []
    for tu, bt in _cells():
        slug = _cell_slug(tu, bt)
        o_tu, o_bt = overrides.get(slug, (tu, bt))
        blocks.append(_fine_block(slug, o_tu, o_bt))
    blocks.append(_fine_block(UNREVIEWED_SLUG, UNREVIEWED_TU, UNREVIEWED_BT, reviewed=False))
    return _FRONT_MATTER + "".join(blocks)


def _doc(overrides=None):
    return parse_canon_text(_canon_text(overrides))


def _reviewed_ids(doc) -> frozenset:
    return frozenset(f.id for f in doc.fines() if f.reviewed_by is not None)


# ════════════════════════════════════════════════════════════════════
# 身分（三組）
# ════════════════════════════════════════════════════════════════════

IDENTITIES = {
    "b2b-pm": Identity(vendor_id=VENDOR_ID, target_user="property_manager", mode="b2b"),
    "b2b-prospect": Identity(vendor_id=VENDOR_ID, target_user="prospect", mode="b2b"),
    "b2c-tenant": Identity(vendor_id=VENDOR_ID, target_user="tenant", mode="b2c"),
}
#: 記憶體側的業者業態；b2b 分支不看它（嚴格 `system_provider`），b2c 分支才用得到。
MEM_VENDOR_BT = frozenset(VENDOR_BT)


def _sql_where(identity):
    """SQL 側謂詞（`param_resolver` 替身注入業態，樣式同 `_refactored_where`）。"""
    resolver = MagicMock()
    resolver.get_vendor_info.return_value = {"business_types": list(VENDOR_BT)}
    return build_visibility_predicate(identity, param_resolver=resolver)


def _sql_visible(conn, identity, ids) -> frozenset:
    """SQL 側撈到的細目 id 集合（經 `generation_metadata->>'canon_ref'` 回映）。"""
    sql, params = _sql_where(identity)
    cur = conn.cursor()
    cur.execute(
        "SELECT kb.generation_metadata->>'canon_ref' FROM knowledge_base kb "
        f"WHERE kb.id = ANY(%s::int[]) {sql}",
        tuple([list(ids)] + params),
    )
    got = frozenset(r[0] for r in cur.fetchall())
    cur.close()
    assert None not in got, "有列的 canon_ref 是 NULL ⇒ 回映壞了，⛔ 不得當成集合相等"
    return got


def _mem_visible(doc, identity) -> frozenset:
    return FineIndex(_NullBackend()).visible_subset(
        identity, doc, vendor_business_types=MEM_VENDOR_BT
    )


class _NullBackend:
    """`visible_subset` ⛔ 不打 embedding；給個永不被呼叫的後端就夠了。"""

    async def embed(self, texts):    # pragma: no cover — ⛔ 不該被呼叫
        raise AssertionError("visible_subset 不得觸發 embedding")


# ════════════════════════════════════════════════════════════════════
# DB 連線與矩陣列
# ════════════════════════════════════════════════════════════════════

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
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ 記憶體／SQL 等價未驗")


#: 正本細目 → DB 列的插入順序（id ＝ BASE_ID + index）
def _row_plan(doc):
    return [(BASE_ID + n, f.id, f.target_user, f.business_types)
            for n, f in enumerate(doc.fines())]


def _insert_row(cur, row_id, fine_id, tu, bt):
    """一列等價 `knowledge_base`。⚠️ **空清單寫 NULL**（§8.2），⛔ 不寫 `'{}'`。"""
    cur.execute(
        """
        INSERT INTO knowledge_base
            (id, question_summary, answer, target_user, business_types, vendor_ids,
             is_active, category, generation_metadata)
        VALUES (%s, %s, %s, %s::text[], %s::text[], %s::int[], %s, %s, %s::jsonb)
        """,
        (row_id, f"{MARKER}{fine_id}", "等價測試列",
         list(tu) or None, list(bt) or None, None, True, None,
         json.dumps({"canon_ref": fine_id})),
    )


@pytest.fixture(scope="module")
def matrix():
    """插入 16 列（15 格 ＋ 1 未審），yield `(doc, ids)`；`finally` 依 id 區間刪除。"""
    doc = _doc()
    plan = _row_plan(doc)
    conn = _connect()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_base WHERE question_summary LIKE %s", (MARKER + "%",))
        cur.execute("SELECT count(*) FROM knowledge_base WHERE id BETWEEN %s AND %s",
                    (BASE_ID, BASE_ID + len(plan)))
        stale = cur.fetchone()[0]
        assert stale == 0, (
            f"id 區間 {BASE_ID}–{BASE_ID + len(plan)} 已有 {stale} 列非本測試的資料——"
            "⛔ 拒絕覆蓋，請先確認來源")
        for row_id, fine_id, tu, bt in plan:
            _insert_row(cur, row_id, fine_id, tu, bt)
        cur.execute("SELECT count(*) FROM knowledge_base WHERE question_summary LIKE %s",
                    (MARKER + "%",))
        inserted = cur.fetchone()[0]
        cur.close()
        assert inserted == len(plan), f"矩陣列沒有全部插入（{inserted}/{len(plan)}）——⛔ 不得帶半套跑"
        yield doc, [r[0] for r in plan]
    finally:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_base WHERE id BETWEEN %s AND %s",
                        (BASE_ID, BASE_ID + len(plan)))
            cur.execute("DELETE FROM knowledge_base WHERE question_summary LIKE %s",
                        (MARKER + "%",))
            cur.close()
        finally:
            conn.close()


@pytest.fixture(scope="module")
def sets(matrix):
    """三組身分各一份 `(記憶體集合, SQL 集合)`（同一批列上各算一次）。"""
    doc, ids = matrix
    conn = _connect()
    try:
        return {
            label: (_mem_visible(doc, identity), _sql_visible(conn, identity, ids))
            for label, identity in IDENTITIES.items()
        }
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════
# 主張 1：15 格 × 3 身分，逐格相等（比對集合＝已審細目）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("label", sorted(IDENTITIES))
@pytest.mark.parametrize("tu,bt", _cells(), ids=[_cell_slug(tu, bt) for tu, bt in _cells()])
def test_cell_memory_matches_sql(matrix, sets, label, tu, bt):
    """單一格：記憶體可見 ⇔ SQL 可見。"""
    fine_id = _fid(_cell_slug(tu, bt))
    mem, sql = sets[label]
    assert (fine_id in mem) == (fine_id in sql), (
        f"[{label}] {fine_id}：記憶體={fine_id in mem}、SQL={fine_id in sql}"
    )


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("label", sorted(IDENTITIES))
def test_reviewed_sets_are_equal(matrix, sets, label):
    """整體集合相等（SQL 側取已審細目的交集，見模組 docstring 的單向不對稱）。"""
    doc, _ids = matrix
    mem, sql = sets[label]
    assert sql & _reviewed_ids(doc) == mem, (
        f"[{label}] 集合不同：\n  SQL 多：{sorted((sql & _reviewed_ids(doc)) - mem)}"
        f"\n  記憶體多：{sorted(mem - sql)}"
    )


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("label,expected", [
    # b2b：嚴格業態 `system_provider`（⛔ 無 IS NULL 放行，D-002）＋角色相符或 target_user 空
    ("b2b-pm", {"cell-pm-sysprov", "cell-notu-sysprov"}),
    ("b2b-prospect", {"cell-prospect-sysprov", "cell-notu-sysprov"}),
    # b2c：業態寬鬆（空放行）＋角色 tenant／all_users／空
    ("b2c-tenant", {
        "cell-tenant-rental", "cell-tenant-nobt",
        "cell-allusers-rental", "cell-allusers-nobt",
        "cell-notu-rental", "cell-notu-nobt",
    }),
])
def test_expected_sets_are_pinned_literally(matrix, sets, label, expected):
    """⚠️ 期望值寫死：⛔ 不得只比「兩側相等」——兩側同時錯成一樣時那條會綠。"""
    mem, _sql = sets[label]
    assert mem == frozenset(_fid(s) for s in expected), sorted(mem)


@pytest.mark.req(_SPEC)
def test_matrix_discriminates(sets):
    """量尺自證：三組身分必須撈到不同且非空的集合。"""
    mems = {label: mem for label, (mem, _sql) in sets.items()}
    for label, mem in mems.items():
        assert mem, f"[{label}] 記憶體側撈到空集合 ⇒ 比對沒有意義"
    assert len({frozenset(m) for m in mems.values()}) == len(mems), mems


# ════════════════════════════════════════════════════════════════════
# 主張 2：未審細目的單向不對稱（刻意，⛔ 不得放寬記憶體側收斂）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req(_SPEC)
def test_unreviewed_fine_is_sql_visible_but_memory_invisible(matrix, sets):
    """未審列在 SQL 側可見、記憶體側不可見——`canon_visible` 有 `reviewed_by` 閘門，
    `build_visibility_predicate` **刻意沒有**審核謂詞。"""
    doc, _ids = matrix
    unreviewed = _fid(UNREVIEWED_SLUG)
    assert unreviewed not in _reviewed_ids(doc)             # 正對照：它真的沒 reviewed

    mem, sql = sets["b2b-prospect"]                          # 該列形狀對 b2b prospect 可見
    assert unreviewed in sql, "未審列在 SQL 側也撈不到 ⇒ 這條測不到不對稱（材料或謂詞有問題）"
    assert unreviewed not in mem
    # 其餘兩組身分：記憶體側同樣不可見
    for label in ("b2b-pm", "b2c-tenant"):
        assert unreviewed not in sets[label][0]


# ════════════════════════════════════════════════════════════════════
# 主張 3：突變控制（兩側同動；只動一側必須變紅）
# ════════════════════════════════════════════════════════════════════

#: 被翻的那一格：對 b2b 兩組身分原本可見，翻成 `rental` 後兩側都該消失
MUTATED_SLUG = "cell-prospect-sysprov"
MUTATED_TO = (("prospect",), ("rental",))


def _reinsert(conn, row_id, fine_id, tu, bt):
    """DELETE＋INSERT 取代 UPDATE（⛔ 避開 `update_kb_updated_at` trigger）。"""
    cur = conn.cursor()
    cur.execute("DELETE FROM knowledge_base WHERE id = %s", (row_id,))
    _insert_row(cur, row_id, fine_id, tu, bt)
    cur.close()


@pytest.mark.req(_SPEC)
def test_mutation_control_both_sides_move_together(matrix):
    """翻一列業態（正本＋DB 同步）⇒ 兩側同時失去該細目，且等式仍成立。"""
    doc, ids = matrix
    fine_id = _fid(MUTATED_SLUG)
    row_id = dict((f, i) for i, f, _t, _b in _row_plan(doc))[fine_id]
    original = [(f.target_user, f.business_types) for f in doc.fines() if f.id == fine_id][0]

    conn = _connect()
    try:
        conn.autocommit = True
        # 前置正對照：翻之前，該細目對 b2b prospect 兩側都可見
        before_mem = _mem_visible(doc, IDENTITIES["b2b-prospect"])
        before_sql = _sql_visible(conn, IDENTITIES["b2b-prospect"], ids)
        assert fine_id in before_mem and fine_id in before_sql

        mutated_doc = _doc({MUTATED_SLUG: MUTATED_TO})
        _reinsert(conn, row_id, fine_id, *MUTATED_TO)

        for label, identity in IDENTITIES.items():
            mem = _mem_visible(mutated_doc, identity)
            sql = _sql_visible(conn, identity, ids)
            assert sql & _reviewed_ids(mutated_doc) == mem, f"[{label}] 突變後集合不同"
        assert fine_id not in _mem_visible(mutated_doc, IDENTITIES["b2b-prospect"])
        assert fine_id not in _sql_visible(conn, IDENTITIES["b2b-prospect"], ids)
    finally:
        _reinsert(conn, row_id, fine_id, *original)          # 還原 DB 側
        conn.close()


@pytest.mark.req(_SPEC)
def test_mutation_control_db_only_change_makes_the_equality_fail(matrix):
    """量尺自證：**只翻 DB 側**（正本不動）⇒ 集合相等必須變紅。

    ⛔ 這條若變綠，代表上面所有「相等」是瞎尺量出來的。
    """
    doc, ids = matrix
    fine_id = _fid(MUTATED_SLUG)
    row_id = dict((f, i) for i, f, _t, _b in _row_plan(doc))[fine_id]
    original = [(f.target_user, f.business_types) for f in doc.fines() if f.id == fine_id][0]

    conn = _connect()
    try:
        conn.autocommit = True
        _reinsert(conn, row_id, fine_id, *MUTATED_TO)        # 只動 DB
        mem = _mem_visible(doc, IDENTITIES["b2b-prospect"])  # 正本仍是原始的
        sql = _sql_visible(conn, IDENTITIES["b2b-prospect"], ids)
        assert sql & _reviewed_ids(doc) != mem, (
            "只翻 DB 側卻仍然相等 ⇒ 比對函式或回映是瞎的，上面所有結論一律作廢"
        )
        assert fine_id in mem and fine_id not in sql          # 差異就在這一格
    finally:
        _reinsert(conn, row_id, fine_id, *original)
        conn.close()


# ════════════════════════════════════════════════════════════════════
# 主張 4：版控正本（Plan §4.6）
# ════════════════════════════════════════════════════════════════════

CANON_DIR = Path(__file__).resolve().parents[3] / "canon"
#: 版控正本現況細目數（⛔ 不寫成 `len(fines)` 自證——那會讓「正本被砍剩 1 個」也綠）
CANON_FINE_COUNT = 38


@pytest.mark.req(_SPEC)
def test_real_prospect_canon_visibility():
    """b2b prospect ⇒ 全 38；b2b pm ⇒ ∅。

    ⚠️ **pm 那一半不具鑑別力**：售前正本每一列都是 `target_user: [prospect]`，
    pm 本來就撈不到任何一列，空集合＝空集合。⛔ 不得拿它當「規則有生效」的證據——
    真正的鑑別力在上面的 15 格合成矩陣（`test_expected_sets_are_pinned_literally`）。
    ⚠️ 本條只讀正本的**中繼資料**（id／角色／業態），⛔ 不讀也不印任何講法文字。
    """
    doc = parse_canon(str(CANON_DIR / "prospect.md"))
    assert len(doc.fines()) == CANON_FINE_COUNT, [f.id for f in doc.fines()]

    prospect = _mem_visible(doc, IDENTITIES["b2b-prospect"])
    assert prospect == frozenset(f.id for f in doc.fines())
    assert len(prospect) == CANON_FINE_COUNT

    assert _mem_visible(doc, IDENTITIES["b2b-pm"]) == frozenset()
