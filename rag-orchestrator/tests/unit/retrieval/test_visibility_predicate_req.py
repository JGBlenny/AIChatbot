"""隔離謂詞單一來源的條件表 unit（spec agentic-mcp-orchestration・任務 1.1）。

驗 `build_visibility_predicate(identity)` 逐條產出 design 元件 3 條件表的 7 條，
⛔ 不驗「SQL 對真實資料回哪幾列」——那由差分等價 integration
（tests/integration/agent/test_visibility_predicate_equiv.py）負責。

⚠️ 本檔最重要的一條是 `test_b2b_business_types_has_no_null_pass`：
   b2b 業態 `&&` **無 `IS NULL` 放行**是刻意的跨業者隔離（D-002），
   補上去會打穿隔離。⛔ 這條變紅時該做的是把改動改回去，不是改測試。
"""
import pytest
from unittest.mock import MagicMock

from services.agent.identity import Identity
from services.vendor_knowledge_retriever_v2 import (
    VendorKnowledgeRetrieverV2 as KB,
    build_visibility_predicate,
)

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:1.1"


def _resolver(business_types=None):
    """param_resolver 替身；business_types=None ⇒ 模擬「vendor_id 查無業者」。"""
    pr = MagicMock()
    pr.get_vendor_info.return_value = (
        None if business_types is None else {"business_types": list(business_types)}
    )
    return pr


def _build(mode="b2c", target_user="tenant", vendor_id=1, business_types=("landlord_individual",)):
    return build_visibility_predicate(
        Identity(vendor_id=vendor_id, target_user=target_user, mode=mode),
        param_resolver=_resolver(business_types),
    )


# ── 條件 6a／6b：業態分支 ────────────────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_b2b_business_types_has_no_null_pass():
    """b2b：`business_types &&` 嚴格比對，⛔ 無 IS NULL 放行（D-002 勿改回）。"""
    for mode, target_user in (("b2b", "tenant"), ("b2c", "property_manager"),
                              ("b2c", "system_admin")):
        sql, _params = _build(mode=mode, target_user=target_user)
        assert "kb.business_types && %s::text[]" in sql
        assert "kb.business_types IS NULL" not in sql, (
            f"b2b 路徑（mode={mode} target_user={target_user}）出現 business_types "
            "IS NULL 放行——這會打穿跨業者隔離（D-002）"
        )


@pytest.mark.req(_SPEC)
def test_b2c_business_types_allows_null():
    """b2c：`business_types IS NULL OR &&`（通用知識放行）。"""
    sql, _params = _build(mode="b2c", target_user="tenant")
    assert "(kb.business_types IS NULL OR kb.business_types && %s::text[])" in sql


# ── 條件 7 ＋ b2b 業態參數 ──────────────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_b2b_business_types_param_is_system_provider():
    _sql, params = _build(mode="b2b", target_user="tenant")
    assert ["system_provider"] in params


@pytest.mark.req(_SPEC)
def test_b2c_unknown_vendor_yields_empty_business_types():
    """b2c 且 vendor_id 查無業者 ⇒ `$bt = []`（只剩 IS NULL 列，fail-closed）。"""
    sql, params = build_visibility_predicate(
        Identity(vendor_id=99999, target_user="tenant", mode="b2c"),
        param_resolver=_resolver(None),
    )
    assert "(kb.business_types IS NULL OR kb.business_types && %s::text[])" in sql
    assert [] in params, f"查無業者應降級為空業態，實得 params={params}"


@pytest.mark.req(_SPEC)
def test_b2c_uses_vendor_business_types_not_system_provider():
    _sql, params = _build(mode="b2c", target_user="tenant",
                          business_types=("landlord_individual",))
    assert ["landlord_individual"] in params
    assert ["system_provider"] not in params


# ── 條件 4：target_user ────────────────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_target_user_null_always_passes():
    """`kb.target_user IS NULL` 一律放行（通用知識），兩種模式都是。"""
    for mode in ("b2b", "b2c"):
        sql, _params = _build(mode=mode)
        assert "(kb.target_user IS NULL OR kb.target_user && %s::text[])" in sql


@pytest.mark.req(_SPEC)
def test_b2c_target_user_param_appends_all_users():
    _sql, params = _build(mode="b2c", target_user="tenant")
    assert ["tenant", "all_users"] in params


@pytest.mark.req(_SPEC)
def test_b2b_target_user_param_has_no_all_users():
    _sql, params = _build(mode="b2b", target_user="property_manager")
    assert ["property_manager"] in params
    assert not any(isinstance(p, list) and "all_users" in p for p in params), (
        f"b2b ⛔ 不得追加 all_users，實得 params={params}"
    )


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("raw", [None, "", "unknown_role", "TENANT", []])
def test_unknown_target_user_normalized_to_tenant(raw):
    """未知／空 target_user ⇒ 參數側正規化為 tenant（fail-safe，⛔ 不另寫第二份）。"""
    _sql, params = _build(mode="b2c", target_user=raw)
    assert ["tenant", "all_users"] in params


@pytest.mark.req(_SPEC)
def test_known_role_not_forced_to_tenant():
    """正對照組：已知角色不得被正規化掉（否則上一條是把所有輸入都變 tenant 的瞎尺）。"""
    _sql, params = _build(mode="b2c", target_user="landlord")
    assert ["landlord", "all_users"] in params


# ── 條件 5：is_b2b 兩條件 OR ───────────────────────────────────────────

@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("mode,target_user,expect_b2b", [
    ("b2c", "property_manager", True),
    ("b2c", "system_admin", True),
    ("b2b", "tenant", True),
    ("b2b", "prospect", True),
    ("b2c", "tenant", False),
    ("b2c", "landlord", False),
    ("b2c", "prospect", False),
])
def test_is_b2b_is_two_condition_or(mode, target_user, expect_b2b):
    sql, params = _build(mode=mode, target_user=target_user)
    strict = "kb.business_types IS NULL" not in sql
    assert strict is expect_b2b, (
        f"mode={mode} target_user={target_user} 期待 b2b={expect_b2b}，實得嚴格分支={strict}"
    )
    assert (["system_provider"] in params) is expect_b2b


# ── 條件 1／2／3：is_active、保留分類、vendor_ids ──────────────────────

@pytest.mark.req(_SPEC)
def test_is_active_filter_present():
    for mode in ("b2b", "b2c"):
        sql, _params = _build(mode=mode)
        assert "kb.is_active = TRUE" in sql


@pytest.mark.req(_SPEC)
def test_reserved_categories_always_excluded():
    """兩個保留分類值在任何模式都必須出現在排除句（決策 11／R19）。"""
    for mode in ("b2b", "b2c"):
        sql, _params = _build(mode=mode)
        for cat in (KB.SYSTEM_DOC_CATEGORY, KB.RULES_DOC_CATEGORY):
            assert f"kb.category IS DISTINCT FROM '{cat}'" in sql, (
                f"mode={mode} 缺保留分類排除：{cat}"
            )


@pytest.mark.req(_SPEC)
def test_vendor_ids_filter_and_param():
    sql, params = _build(vendor_id=7)
    assert "(array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])" in sql
    assert params[0] == [7]


# ── 形狀契約：片段可直接拼進 WHERE、佔位符與參數對齊 ────────────────────

@pytest.mark.req(_SPEC)
def test_fragment_starts_with_and_and_param_order_is_fixed():
    """片段以 AND 起首（可直拼 WHERE）；參數順序＝vendor_ids → business_types → target_user。"""
    sql, params = _build(mode="b2c", target_user="tenant", vendor_id=3,
                         business_types=("landlord_individual",))
    assert sql.lstrip().startswith("AND ")
    assert params == [[3], ["landlord_individual"], ["tenant", "all_users"]]
    assert sql.count("%s") == len(params), "佔位符數與參數數必須相等"
    assert "$1" not in sql, "本檔案用 psycopg2 %s 風格，⛔ 不得混用 $n"


@pytest.mark.req(_SPEC)
def test_embedding_and_keywords_conditions_stay_out_of_predicate():
    """`embedding`／`keywords` 是呼叫端的相關性條件，⛔ 不進謂詞（條件表最後一列）。"""
    for mode in ("b2b", "b2c"):
        sql, _params = _build(mode=mode)
        assert "embedding" not in sql
        assert "keywords" not in sql


# ════════════════════════════════════════════════════════════════════
# 1.1 留項①：把差分等價的「不需 DB」那半搬進 unit（spec 1.2）
# ════════════════════════════════════════════════════════════════════
# 源起：`tests/integration/agent/test_visibility_predicate_equiv.py` 的
# SQL 形狀等價比對（`test_sql_shape_matches_oracle`）不碰 DB，卻只掛在
# integration 層——CI 主力只跑 unit（見 `scripts/run-tests.sh` 檔頭），
# 這代表謂詞回歸要等 integration 才被擋到。本節把「重構前字面 oracle」
# 複製一份到 unit（⛔ 不 import integration 檔——那樣量尺會跟著production
# 碼一起漂移，變成拿產線碼驗產線碼）。
#
# ⚠️ 這是**獨立的第二份**字面複製，不是同一份被兩檔共用：
# `test_visibility_predicate_equiv.py` 的 oracle 若被改動（含刻意植入的
# 回歸），本節不會跟著變——這正是「單元測試不依賴整合測試環境」的代價，
# 兩邊各自維護、⛔ 改一邊不必然帶動另一邊，需人工同步。

#: 重構前 `VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS` 的字面複製
_UNIT_ORACLE_KNOWN_TARGET_USERS = {
    'tenant', 'landlord', 'property_manager', 'system_admin', 'prospect'}


def _unit_oracle_effective_target_user(target_user):
    if isinstance(target_user, list):
        target_user = target_user[0] if target_user else None
    return target_user if target_user in _UNIT_ORACLE_KNOWN_TARGET_USERS else 'tenant'


def _unit_oracle_branch(kind, target_user, mode, vendor_business_types):
    """重構前兩處分支邏輯的字面複製（⛔ 不「順手統一」兩處字串差異）。"""
    lead = "AND " if kind == "keyword" else ""
    is_b2b_mode = (target_user in ['property_manager', 'system_admin']) or (mode == 'b2b')
    target_user_param = [_unit_oracle_effective_target_user(target_user)]
    if is_b2b_mode:
        bt = ['system_provider']
        business_type_filter_sql = f"{lead}kb.business_types && %s::text[]"
    else:
        bt = vendor_business_types
        business_type_filter_sql = (
            f"{lead}(kb.business_types IS NULL OR kb.business_types && %s::text[])")
        target_user_param = [_unit_oracle_effective_target_user(target_user), 'all_users']
    target_user_filter_sql = "AND (kb.target_user IS NULL OR kb.target_user && %s::text[])"
    return business_type_filter_sql, target_user_filter_sql, bt, target_user_param


def _unit_oracle_where(kind, target_user, mode, vendor_id, vendor_business_types):
    bt_sql, tu_sql, bt, tu = _unit_oracle_branch(kind, target_user, mode, vendor_business_types)
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


def _unit_refactored_where(kind, target_user, mode, vendor_id, vendor_business_types):
    resolver = _resolver(vendor_business_types)
    sql, params = build_visibility_predicate(
        Identity(vendor_id=vendor_id, target_user=target_user, mode=mode),
        param_resolver=resolver,
    )
    own = ("kb.embedding IS NOT NULL" if kind == "vector"
           else "kb.keywords IS NOT NULL\n AND array_length(kb.keywords, 1) > 0")
    return f"{own}\n{sql}", params


def _unit_conditions(where_sql):
    """WHERE 文字 → 正規化條件集合（去縮排／開頭 AND／空行後排序）。"""
    out = []
    for line in where_sql.splitlines():
        s = " ".join(line.split())
        if not s:
            continue
        if s.startswith("AND "):
            s = s[4:]
        out.append(s)
    return sorted(out)


_UNIT_IDENTITY_CELLS = [
    pytest.param(mode, tu, id=f"{mode}-{tu}")
    for mode in ("b2b", "b2c")
    for tu in ("property_manager", "tenant", "unknown_role")
]


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("kind", ["vector", "keyword"])
@pytest.mark.parametrize("mode,target_user", _UNIT_IDENTITY_CELLS)
@pytest.mark.parametrize("vendor_bt", [["landlord_individual"], None],
                         ids=["vendor-found", "vendor-missing"])
def test_sql_shape_matches_oracle_unit(kind, mode, target_user, vendor_bt):
    """CI unit 層版本的差分等價：條件集合與參數與重構前字面 oracle 逐項相同。

    ⛔ 這條紅了不是「改壞了謂詞」就是「oracle 需要跟 production 一起演化」——
    兩者都要人裁決，不得直接改本測試讓它變綠。
    """
    o_where, o_params = _unit_oracle_where(
        kind, target_user, mode, 42, [] if vendor_bt is None else vendor_bt)
    r_where, r_params = _unit_refactored_where(kind, target_user, mode, 42, vendor_bt)
    assert _unit_conditions(r_where) == _unit_conditions(o_where), (
        f"[{kind} {mode}/{target_user}] 條件集合與重構前 oracle 不同\n"
        f"  多：{sorted(set(_unit_conditions(r_where)) - set(_unit_conditions(o_where)))}\n"
        f"  少：{sorted(set(_unit_conditions(o_where)) - set(_unit_conditions(r_where)))}"
    )
    assert r_params == o_params, f"[{kind} {mode}/{target_user}] 參數與重構前 oracle 不同"


@pytest.mark.req(_SPEC)
def test_oracle_unit_detects_a_planted_difference():
    """量尺自證：oracle 若被改壞（例如漏掉業態分支），比對必須紅——
    否則上面那批「相同」是瞎尺量出來的。"""
    o_where, o_params = _unit_oracle_where("vector", "property_manager", "b2b", 42, [])
    # 植入差異：把 oracle 的業態條件改成永遠不過濾（模擬「有人把過濾拿掉」）
    broken_where = o_where.replace(
        "kb.business_types && %s::text[]", "TRUE")
    assert _unit_conditions(broken_where) != _unit_conditions(o_where), (
        "植入的差異沒被抓到——比對函式本身是瞎的，上面所有『等價』結論一律作廢"
    )


# ════════════════════════════════════════════════════════════════════
# 1.1 留項②：production 函式送出的 params 改為位置斷言（spec 1.2）
# ════════════════════════════════════════════════════════════════════
# 源起：`test_visibility_predicate_equiv.py::test_production_function_emits_the_predicate`
# 用 `for p in expected_params: assert p in params`——membership 測試，
# ⛔ 抓不到「參數順序被打亂」（例如 business_types 與 target_user 兩個
# list 剛好等長時互換，membership 兩邊都成立、位置斷言才會紅）。

@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("kind", ["vector", "keyword"])
async def test_production_function_emits_predicate_params_in_order(kind):
    """攔 cursor.execute 驗 production 函式送出的 SQL 與**參數順序**。

    ⚠️ 與 integration 版本的差異：這裡用位置比對
    （`params[-len(expected_params):] == expected_params`），membership
    測試（`p in params`）抓不到參數順序錯位（例如 business_types 與
    target_user 兩個 list 剛好等長時互換）。
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
    r.param_resolver = _resolver(("landlord_individual",))

    vendor_id = 42
    if kind == "vector":
        await r._vector_search([0.0] * 4, vendor_id=vendor_id, top_k=5,
                               similarity_threshold=0.6, target_user="tenant", mode="b2c")
    else:
        await r._keyword_search("租金 繳費", vendor_id=vendor_id, limit=5,
                                target_user="tenant", mode="b2c")

    assert store["calls"], "產線函式沒有送出任何 query——攔截壞了，⛔ 不得靜默通過"
    sql, params = store["calls"][0]
    expected_sql, expected_params = build_visibility_predicate(
        Identity(vendor_id=vendor_id, target_user="tenant", mode="b2c"),
        param_resolver=_resolver(("landlord_individual",)))
    for cond in _unit_conditions(expected_sql):
        assert cond in " ".join(sql.split()), f"[{kind}] 送出的 SQL 缺可見性條件：{cond}"

    # 位置斷言：可見性謂詞的參數必須是送出參數列裡**連續且順序不變**的子序列
    # ——⛔ 不是「每個都出現在某處」（membership），是「照這個順序連續出現」。
    # ⚠️ 不假設在頭或尾：vector 路徑謂詞夾在 [vector_str, ...謂詞..., vector_str,
    # limit] 中間、keyword 路徑謂詞前面還有 query token 陣列，兩處位置本就不同，
    # 位置斷言驗的是「順序不變」而非「固定偏移」。
    n = len(expected_params)
    windows = [params[i:i + n] for i in range(len(params) - n + 1)]
    assert expected_params in windows, (
        f"[{kind}] 可見性謂詞參數未以原順序連續出現：實得 {params}，"
        f"期待子序列 {expected_params}（membership 測試會漏抓這種順序/連續性錯位）"
    )


@pytest.mark.req(_SPEC)
async def test_positional_assertion_catches_swapped_params():
    """量尺自證：位置斷言必須抓得到「兩個等長 list 互換」——
    membership 測試（`p in params`）在這個案例仍然會綠，是它的已知盲點。"""
    expected_params = [[1], ["a", "b"], ["c", "d"]]
    swapped = [[1], ["c", "d"], ["a", "b"]]  # 後兩個 list 互換位置
    # membership 兩邊都成立（正是舊斷言抓不到錯位的原因）
    assert all(p in swapped for p in expected_params)
    # 位置比對必須紅
    assert swapped != expected_params, "互換過的參數序列不該與期待值相等"
