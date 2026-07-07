"""核心檢索：SQL 過濾構建確定性 unit（spec unit-coverage-rebuild・任務 8・檢索安全網）。

攔截送進 DB 的 query 字串與參數，驗 vendor_knowledge_retriever_v2._vector_search
是否正確組裝：
- 保留分類排除（系統脈絡 / 對話規則）—— 任何模式都必須在
- is_b2b_mode 判定（target_user∈{property_manager,system_admin} 或 mode==b2b）
- b2b：嚴格 business_types(&&) + target_user 過濾（NULL 放行）
- b2c：寬鬆 business_types(IS NULL OR &&) + target_user 過濾(預設 tenant + all_users 放行;retrieval-fixes #5)

⚠️ 範圍：驗「過濾子句有無正確組進 SQL」（改壞離線即紅）；
   「SQL 對真實資料是否回傳正確列」仍由 integration（test_retrieval_invariants_req）驗。

不需真實 DB：以 __new__ 繞過 __init__ 的外部相依，攔截 cursor.execute。
"""
import pytest
from unittest.mock import MagicMock

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit


class _CaptureCursor:
    def __init__(self, store):
        self.store = store

    def execute(self, sql, params=None):
        self.store["sql"] = sql
        self.store["params"] = params

    def fetchall(self):
        return []

    def close(self):
        pass


class _CaptureConn:
    def __init__(self, store):
        self.store = store

    def cursor(self, *a, **k):
        return _CaptureCursor(self.store)

    def close(self):
        pass


def _make_retriever(store, vendor_business_types=None):
    """繞過 __init__（避開 embedding/rewriter 外部相依），只注入 _vector_search 需要的協作者。"""
    r = object.__new__(VendorKnowledgeRetrieverV2)
    r._get_db_connection = lambda: _CaptureConn(store)
    pr = MagicMock()
    pr.get_vendor_info.return_value = {"business_types": vendor_business_types or ["landlord_individual"]}
    r.param_resolver = pr
    return r


async def _run(r, **kwargs):
    return await r._vector_search([0.1, 0.2], vendor_id=1, top_k=5, similarity_threshold=0.6, **kwargs)


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_reserved_categories_always_excluded():
    """保留分類排除在任何模式都必須在 SQL（防有人改檢索時誤刪）。"""
    store = {}
    r = _make_retriever(store)
    await _run(r, target_user="tenant", mode="b2c")
    sql = store["sql"]
    assert VendorKnowledgeRetrieverV2.SYSTEM_DOC_CATEGORY in sql
    assert VendorKnowledgeRetrieverV2.RULES_DOC_CATEGORY in sql
    assert "IS DISTINCT FROM" in sql


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_b2b_role_applies_target_user_and_strict_business_types():
    """b2b（target_user=property_manager）：嚴格 business_types && + target_user 過濾（NULL 放行）。"""
    store = {}
    r = _make_retriever(store)
    await _run(r, target_user="property_manager")
    sql = store["sql"]
    assert "kb.target_user IS NULL OR kb.target_user && %s::text[]" in sql, "b2b 應套 target_user 過濾"
    assert "kb.business_types && %s::text[]" in sql, "b2b 應有 business_types 過濾"
    # 關鍵：b2b 為「嚴格」——business_types 不得有 IS NULL 放行（否則角色隔離被放寬）
    assert "kb.business_types IS NULL OR" not in sql, "b2b business_types 不應有 NULL 放行（須嚴格）"
    # 參數含 system_provider 業態與正規化後 target_user
    assert ["system_provider"] in store["params"]
    assert ["property_manager"] in store["params"]


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_mode_b2b_triggers_b2b_path_even_for_tenant():
    """is_b2b_mode：mode==b2b 即走 b2b 路徑（即使 target_user 非管理角色）。"""
    store = {}
    r = _make_retriever(store)
    await _run(r, target_user="tenant", mode="b2b")
    sql = store["sql"]
    assert "kb.target_user IS NULL OR kb.target_user && %s::text[]" in sql
    assert "kb.business_types && %s::text[]" in sql
    assert "kb.business_types IS NULL OR" not in sql, "mode=b2b 也須嚴格 business_types"


@pytest.mark.req("retrieval-fixes:5")
async def test_b2c_filters_target_user_default_tenant_with_all_users_passthrough():
    """b2c（retrieval-fixes #5）：過濾 target_user（預設 tenant）+ 通用 all_users 放行；寬鬆 business_types。"""
    store = {}
    r = _make_retriever(store, vendor_business_types=["landlord_individual"])
    await _run(r, target_user="tenant", mode="b2c")
    sql = store["sql"]
    assert "kb.target_user IS NULL OR kb.target_user && %s::text[]" in sql, "b2c 現應有 target_user 過濾"
    assert "kb.business_types IS NULL OR kb.business_types && %s::text[]" in sql, "b2c 應為寬鬆 business_types"
    # target_user 參數：預設 tenant + all_users 通用放行
    assert ["tenant", "all_users"] in store["params"], "b2c target_user 參數應為 [tenant, all_users]"
    # 用的是業者業態（非 system_provider）
    assert ["landlord_individual"] in store["params"]
    assert ["system_provider"] not in store["params"]


@pytest.mark.req("retrieval-fixes:5")
async def test_b2c_unknown_target_user_normalized_to_tenant():
    """b2c：未知/空 target_user 正規化為 tenant（不外洩其他角色知識）。"""
    store = {}
    r = _make_retriever(store, vendor_business_types=["landlord_individual"])
    await _run(r, target_user=None, mode="b2c")
    assert ["tenant", "all_users"] in store["params"], "未知 target_user 應預設 tenant"


@pytest.mark.req("retrieval-fixes:5")
async def test_b2c_landlord_role_preserved_not_forced_tenant():
    """b2c：landlord 為已知角色,不應被正規化成 tenant（房東看房東知識）。"""
    store = {}
    r = _make_retriever(store, vendor_business_types=["landlord_individual"])
    await _run(r, target_user="landlord", mode="b2c")
    assert ["landlord", "all_users"] in store["params"], "landlord 應保留,不被強制 tenant"
