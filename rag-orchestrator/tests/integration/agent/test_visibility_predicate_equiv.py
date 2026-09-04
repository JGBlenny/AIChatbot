"""差分等價：抽出 `build_visibility_predicate` 前後，撈到的列**逐筆相同**。

spec agentic-mcp-orchestration・任務 1.1。⛔ 這是「重構不得改行為」的唯一硬證據——
unit 只驗條件表逐條產出，⛔ 不證明「對真實資料回同一批列」。

## 對照組是什麼

`_oracle_*` 是重構**前** `_vector_search`／`_keyword_search` 的**字面複製**
（見檔內註記）。⛔ 不得改成呼叫產線函式——那樣就變成拿產線碼驗產線碼，
測試會恆綠而什麼都沒驗到。

## 兩層驗證

1. **SQL 形狀等價**（`test_*_sql_shape_matches_oracle`）：攔截產線函式真正送進 DB 的
   query 與參數，與 oracle 組出來的逐條件比對。條件集合與參數完全相同 ⇒ 對**任何**
   輸入等價，不受測試資料涵蓋範圍限制。
2. **列集合等價**（`test_rowset_matches_oracle_over_matrix`）：在測試庫建固定矩陣列，
   兩邊各跑一次，比對 id 集合。

## 量尺自證（⛔ 少了這兩條，上面兩層可能只是「兩邊都瞎」）

- `test_matrix_actually_discriminates`：矩陣必須讓不同身分撈到**不同**的列，
  否則「處處相同」只是因為謂詞根本沒作用。
- `test_oracle_detects_a_planted_difference`：把 oracle 故意改一條（b2b 補 IS NULL 放行
  ＝ D-002 禁止的那個改動），比對必須**紅**。
"""
import os

import psycopg2
import pytest
from unittest.mock import MagicMock

from services.agent.identity import Identity
from services.vendor_knowledge_retriever_v2 import (
    VendorKnowledgeRetrieverV2 as KB,
    build_visibility_predicate,
)

pytestmark = [pytest.mark.integration]

_SPEC = "agentic-mcp-orchestration:1.1"

#: 測試列標記；`finally` 依此清理
MARKER = "__vispred_equiv__"
#: 明示 id 起點。⚠️ **不得靠 serial 預設值**——測試庫的 `knowledge_base_id_seq`
#: 與既有列的 max(id) 不同步（供裝腳本以明示 id 灌入未 setval），
#: 第二次跑就會撞 `duplicate key ... knowledge_base_pkey`（2026-09-04 實測）。
BASE_ID = 9_000_000
VENDOR_ID = 424242          # 矩陣用的假業者（⛔ 不碰真實業者列）
OTHER_VENDOR_ID = 424243


# ════════════════════════════════════════════════════════════════════
# 對照組：重構前的字面複製（⛔ 不得改成 import 產線碼）
# ════════════════════════════════════════════════════════════════════

#: 重構前 `VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS` 的字面複製
_ORACLE_KNOWN_TARGET_USERS = {
    'tenant', 'landlord', 'property_manager', 'system_admin', 'prospect'}


def _oracle_effective_target_user(target_user):
    """重構前 `_effective_target_user` 的字面複製。"""
    if isinstance(target_user, list):
        target_user = target_user[0] if target_user else None
    return target_user if target_user in _ORACLE_KNOWN_TARGET_USERS else 'tenant'


def _oracle_branch(kind, target_user, mode, vendor_business_types, *, b2b_null_pass=False):
    """重構前兩處的分支邏輯（字面複製）。

    ⚠️ 兩處的字串**本來就不完全一樣**：`_vector_search` 的業態片段不帶開頭 `AND`
    （由 SQL 側寫成 `AND {business_type_filter_sql}`），`_keyword_search` 的**自帶**
    （SQL 側只寫 `{business_type_filter_sql}`）。此處照抄兩份，⛔ 不「順手統一」——
    對照組一被整理過，就不再是對照組。

    Args:
        b2b_null_pass: **只給量尺自證用**——True 時把 b2b 業態改成 IS NULL 放行
            （D-002 禁止的改動），用來證明比對抓得到差異。⛔ 產線不得有此選項。
    """
    lead = "AND " if kind == "keyword" else ""
    is_b2b_mode = (target_user in ['property_manager', 'system_admin']) or (mode == 'b2b')
    target_user_param = [_oracle_effective_target_user(target_user)]
    if is_b2b_mode:
        bt = ['system_provider']
        business_type_filter_sql = (
            f"{lead}(kb.business_types IS NULL OR kb.business_types && %s::text[])"
            if b2b_null_pass else f"{lead}kb.business_types && %s::text[]"
        )
    else:
        bt = vendor_business_types
        business_type_filter_sql = (
            f"{lead}(kb.business_types IS NULL OR kb.business_types && %s::text[])")
        target_user_param = [_oracle_effective_target_user(target_user), 'all_users']
    target_user_filter_sql = "AND (kb.target_user IS NULL OR kb.target_user && %s::text[])"
    return business_type_filter_sql, target_user_filter_sql, bt, target_user_param


def _oracle_where(kind, target_user, mode, vendor_id, vendor_business_types, **kw):
    """重構前 `_vector_search`／`_keyword_search` 的 WHERE 與參數（字面複製）。"""
    bt_sql, tu_sql, bt, tu = _oracle_branch(kind, target_user, mode, vendor_business_types, **kw)
    if kind == "vector":
        where = f"""
                    (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])
                    AND kb.embedding IS NOT NULL
                    AND kb.is_active = TRUE
                    AND kb.category IS DISTINCT FROM '{KB.SYSTEM_DOC_CATEGORY}'
                    AND kb.category IS DISTINCT FROM '{KB.RULES_DOC_CATEGORY}'
                    AND {bt_sql}
                    {tu_sql}
        """
    else:
        where = f"""
                    (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])
                    AND kb.is_active = TRUE
                    AND kb.category IS DISTINCT FROM '{KB.SYSTEM_DOC_CATEGORY}'
                    AND kb.category IS DISTINCT FROM '{KB.RULES_DOC_CATEGORY}'
                    AND kb.keywords IS NOT NULL
                    AND array_length(kb.keywords, 1) > 0
                    {bt_sql}
                    {tu_sql}
        """
    return where, [[vendor_id], bt, tu]


# ════════════════════════════════════════════════════════════════════
# 重構後：產線碼組出的 WHERE 與參數
# ════════════════════════════════════════════════════════════════════

def _refactored_where(kind, target_user, mode, vendor_id, vendor_business_types, **_kw):
    resolver = MagicMock()
    resolver.get_vendor_info.return_value = (
        None if vendor_business_types is None else {"business_types": vendor_business_types})
    sql, params = build_visibility_predicate(
        Identity(vendor_id=vendor_id, target_user=target_user, mode=mode),
        param_resolver=resolver,
    )
    own = ("kb.embedding IS NOT NULL" if kind == "vector"
           else "kb.keywords IS NOT NULL\n AND array_length(kb.keywords, 1) > 0")
    return f"{own}\n{sql}", params


# ── 身分矩陣（brief 指定）───────────────────────────────────────────
IDENTITY_CELLS = [
    pytest.param(mode, tu, id=f"{mode}-{tu}")
    for mode in ("b2b", "b2c")
    for tu in ("property_manager", "tenant", "unknown_role")
]
#: b2c 分支的業態來源；None ⇒ 模擬 vendor_id 查無業者（fail-closed，`$bt=[]`）
VENDOR_BT = ["landlord_individual"]


# ════════════════════════════════════════════════════════════════════
# 第 1 層：SQL 形狀等價（不需 DB 資料，只需能組 SQL）
# ════════════════════════════════════════════════════════════════════

def _conditions(where_sql):
    """把 WHERE 文字拆成正規化條件集合（去縮排、去開頭 AND、去空行）。

    ⚠️ 排序後比對＝**連言（AND）重排視為等價**。這對本重構成立（只搬動條件位置、
    未動連接詞），⛔ 但若哪天有人在 WHERE 裡引入 OR 分組，這個正規化就不再安全。
    """
    out = []
    for line in where_sql.splitlines():
        s = " ".join(line.split())
        if not s:
            continue
        if s.startswith("AND "):
            s = s[4:]
        out.append(s)
    return sorted(out)


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("kind", ["vector", "keyword"])
@pytest.mark.parametrize("mode,target_user", IDENTITY_CELLS)
@pytest.mark.parametrize("vendor_bt", [VENDOR_BT, None], ids=["vendor-found", "vendor-missing"])
def test_sql_shape_matches_oracle(kind, mode, target_user, vendor_bt):
    """條件集合與參數逐項相同 ⇒ 對任何輸入等價（⛔ 不受測試資料涵蓋率限制）。"""
    o_where, o_params = _oracle_where(
        kind, target_user, mode, VENDOR_ID, [] if vendor_bt is None else vendor_bt)
    r_where, r_params = _refactored_where(kind, target_user, mode, VENDOR_ID, vendor_bt)
    assert _conditions(r_where) == _conditions(o_where), (
        f"[{kind} {mode}/{target_user}] 條件集合與重構前不同\n"
        f"  多：{sorted(set(_conditions(r_where)) - set(_conditions(o_where)))}\n"
        f"  少：{sorted(set(_conditions(o_where)) - set(_conditions(r_where)))}"
    )
    assert r_params == o_params, f"[{kind} {mode}/{target_user}] 參數與重構前不同"


@pytest.mark.req(_SPEC)
def test_oracle_detects_a_planted_difference():
    """量尺自證：oracle 故意補上 b2b 的 IS NULL 放行（D-002 禁止），比對必須紅。

    ⛔ 這條若變綠，代表上面那批「相同」是瞎尺量出來的。
    """
    o_where, _ = _oracle_where("vector", "property_manager", "b2b", VENDOR_ID, [],
                               b2b_null_pass=True)
    r_where, _ = _refactored_where("vector", "property_manager", "b2b", VENDOR_ID, None)
    assert _conditions(r_where) != _conditions(o_where), (
        "植入的差異沒被抓到——比對函式是瞎的，上面所有『等價』結論一律作廢"
    )


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("kind", ["vector", "keyword"])
async def test_production_function_emits_the_predicate(kind):
    """產線搜尋函式**真的**送出這份謂詞（攔 cursor.execute 驗 SQL 與參數順序）。

    ⚠️ 上面驗的是「謂詞產出對」，這條驗「兩處呼叫點真的用它、且參數順序沒錯位」——
    參數錯位不會讓 SQL 語法錯，只會靜默把業態陣列餵給角色欄位。
    """
    store = {"calls": []}

    class _Cur:
        def execute(self, sql, params=None):
            store["calls"].append((sql, list(params or [])))

        def fetchall(self):
            return []

        def close(self):
            pass

    class _Conn:
        def cursor(self, *a, **k):
            return _Cur()

        def close(self):
            pass

    r = object.__new__(KB)
    r._get_db_connection = lambda: _Conn()
    pr = MagicMock()
    pr.get_vendor_info.return_value = {"business_types": VENDOR_BT}
    r.param_resolver = pr

    if kind == "vector":
        await r._vector_search([0.0] * 4, vendor_id=VENDOR_ID, top_k=5,
                               similarity_threshold=0.6, target_user="tenant", mode="b2c")
    else:
        await r._keyword_search("租金 繳費", vendor_id=VENDOR_ID, limit=5,
                                target_user="tenant", mode="b2c")

    assert store["calls"], "產線函式沒有送出任何 query——攔截壞了，⛔ 不得靜默通過"
    sql, params = store["calls"][0]
    expected_sql, expected_params = build_visibility_predicate(
        Identity(vendor_id=VENDOR_ID, target_user="tenant", mode="b2c"), param_resolver=pr)
    for cond in _conditions(expected_sql):
        assert cond in " ".join(sql.split()), f"[{kind}] 送出的 SQL 缺可見性條件：{cond}"
    for p in expected_params:
        assert p in params, f"[{kind}] 送出的參數缺 {p}（順序或內容錯位）"


# ════════════════════════════════════════════════════════════════════
# 第 2 層：列集合等價（需測試 DB）
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
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ 差分等價未驗")


#: 矩陣維度（brief 指定）
_TARGET_USERS = [None, ["property_manager"], ["tenant"], ["all_users"]]
_BUSINESS_TYPES = [None, ["system_provider"], ["landlord_individual"]]
_VENDOR_IDS = [None, [VENDOR_ID], [OTHER_VENDOR_ID]]
_IS_ACTIVE = [True, False]
_CATEGORIES = [None, KB.SYSTEM_DOC_CATEGORY, KB.RULES_DOC_CATEGORY]


def _matrix_rows():
    """固定矩陣（⛔ 順序固定＝可重跑）。

    ⚠️ 每個隔離組合**各出兩列**：`full`（有 embedding 也有 keywords）與
    `bare`（兩者皆 NULL）。⛔ 不得改回「依索引交錯給值」——第一版用 `i % 3`
    決定 keywords，實測結果是**所有會洩漏的組合剛好都落在 keywords=NULL**
    ⇒ 詞面路的列集合對 D-002 那個改動完全看不見（假綠燈，2026-09-04 逼出）。
    `bare` 列同時讓兩條路自己的 NOT NULL 條件真的咬得到。
    """
    rows = []
    i = 0
    for tu in _TARGET_USERS:
        for bt in _BUSINESS_TYPES:
            for vids in _VENDOR_IDS:
                for act in _IS_ACTIVE:
                    for cat in _CATEGORIES:
                        for variant in ("full", "bare"):
                            rows.append({
                                "q": f"{MARKER}{i}",
                                "target_user": tu, "business_types": bt, "vendor_ids": vids,
                                "is_active": act, "category": cat,
                                "has_embedding": variant == "full",
                                "has_keywords": variant == "full",
                            })
                            i += 1
    return rows


@pytest.fixture(scope="module")
def matrix_ids():
    conn = _connect()
    ids = []
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_base WHERE question_summary LIKE %s", (MARKER + "%",))
        rows = _matrix_rows()
        cur.execute("SELECT count(*) FROM knowledge_base WHERE id BETWEEN %s AND %s",
                    (BASE_ID, BASE_ID + len(rows)))
        stale = cur.fetchone()[0]
        assert stale == 0, (
            f"id 區間 {BASE_ID}–{BASE_ID + len(rows)} 已有 {stale} 列非本測試的資料——"
            "⛔ 拒絕覆蓋，請先確認來源")
        zero_vec = "[" + ",".join(["0"] * 1536) + "]"
        for n, r in enumerate(rows):
            cur.execute(
                """
                INSERT INTO knowledge_base
                    (id, question_summary, answer, target_user, business_types, vendor_ids,
                     is_active, category, embedding, keywords)
                VALUES (%s, %s, %s, %s::text[], %s::text[], %s::int[], %s, %s,
                        %s::vector, %s::text[])
                RETURNING id
                """,
                (BASE_ID + n, r["q"], "差分等價測試列", r["target_user"], r["business_types"],
                 r["vendor_ids"], r["is_active"], r["category"],
                 zero_vec if r["has_embedding"] else None,
                 ["租金"] if r["has_keywords"] else None),
            )
            ids.append(cur.fetchone()[0])
        cur.close()
        assert len(ids) == len(_matrix_rows()), "矩陣列沒有全部插入——⛔ 不得帶著半套矩陣往下跑"
        yield ids
    finally:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_base WHERE question_summary LIKE %s",
                        (MARKER + "%",))
            cur.close()
        finally:
            conn.close()


def _fetch(conn, where_sql, params, ids):
    cur = conn.cursor()
    cur.execute(
        f"SELECT kb.id FROM knowledge_base kb WHERE kb.id = ANY(%s::int[]) AND ({where_sql})",
        tuple([ids] + params),
    )
    got = {r[0] for r in cur.fetchall()}
    cur.close()
    return got


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("kind", ["vector", "keyword"])
@pytest.mark.parametrize("mode,target_user", IDENTITY_CELLS)
@pytest.mark.parametrize("vendor_bt", [VENDOR_BT, None], ids=["vendor-found", "vendor-missing"])
def test_rowset_matches_oracle_over_matrix(matrix_ids, kind, mode, target_user, vendor_bt):
    """矩陣列上，重構前後撈到的 id 集合逐筆相同。"""
    conn = _connect()
    try:
        o_where, o_params = _oracle_where(
            kind, target_user, mode, VENDOR_ID, [] if vendor_bt is None else vendor_bt)
        r_where, r_params = _refactored_where(kind, target_user, mode, VENDOR_ID, vendor_bt)
        before = _fetch(conn, o_where, o_params, matrix_ids)
        after = _fetch(conn, r_where, r_params, matrix_ids)
        assert after == before, (
            f"[{kind} {mode}/{target_user} bt={vendor_bt}] 列集合不同：\n"
            f"  重構後多撈：{sorted(after - before)}\n  重構後少撈：{sorted(before - after)}"
        )
    finally:
        conn.close()


@pytest.mark.req(_SPEC)
def test_matrix_actually_discriminates(matrix_ids):
    """量尺自證：矩陣必須讓不同身分撈到不同的列，且都不是空集合。

    ⛔ 少了這條，「處處相同」可能只是因為兩邊都撈不到東西（假綠燈）。
    """
    conn = _connect()
    try:
        b2b, b2b_p = _refactored_where("vector", "property_manager", "b2b", VENDOR_ID, VENDOR_BT)
        b2c, b2c_p = _refactored_where("vector", "tenant", "b2c", VENDOR_ID, VENDOR_BT)
        got_b2b = _fetch(conn, b2b, b2b_p, matrix_ids)
        got_b2c = _fetch(conn, b2c, b2c_p, matrix_ids)
        assert got_b2b, "b2b 身分在矩陣上撈到 0 列——矩陣沒有可見的列，比對沒有意義"
        assert got_b2c, "b2c 身分在矩陣上撈到 0 列——同上"
        assert got_b2b != got_b2c, "兩種身分撈到完全一樣的列——謂詞在矩陣上不起作用，⛔ 比對無效"
    finally:
        conn.close()


@pytest.mark.req(_SPEC)
def test_reserved_categories_and_inactive_never_returned(matrix_ids):
    """釘死兩條硬條件在真資料上成立：保留分類與 is_active=false 一列都不得回。"""
    conn = _connect()
    try:
        for mode, tu in (("b2b", "property_manager"), ("b2c", "tenant")):
            where, params = _refactored_where("vector", tu, mode, VENDOR_ID, VENDOR_BT)
            got = _fetch(conn, where, params, matrix_ids)
            if not got:
                pytest.fail(f"[{mode}/{tu}] 撈到 0 列——正對照組失效，⛔ 不得當成『沒有洩漏』")
            cur = conn.cursor()
            cur.execute(
                "SELECT id, category, is_active FROM knowledge_base "
                "WHERE id = ANY(%s::int[]) AND (category IS NOT NULL OR is_active = FALSE)",
                (list(got),))
            leaked = [r for r in cur.fetchall() if r[1] is not None or r[2] is False]
            cur.close()
            assert not leaked, f"[{mode}/{tu}] 洩漏保留分類或停用列：{leaked}"
    finally:
        conn.close()
