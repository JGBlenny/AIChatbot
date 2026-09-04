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
