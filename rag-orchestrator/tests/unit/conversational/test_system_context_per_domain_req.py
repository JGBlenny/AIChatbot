"""unit:面向化系統脈絡疊加（domain-conversational-facets 面向模型｜R2.1–2.5, R7.1）。

`get_system_context(db_pool, domain_key)`：
  - base = category='系統脈絡' 且 target_user IS NULL。
  - 角色級鍵（售前 'prospect'）→ target_user 命中，單層 append（base+售前）。
  - 診斷面向鍵（子分類 '狀態判斷'）→ 沿 category_config 父鏈疊加：base + 母共用『系統合約』+ 子面向『狀態判斷』。
  - 無鍵/無領域層 → 只回 base；base 缺 → MINIMAL_FALLBACK；per-key 快取；例外不快取。
mock db_pool（支援 target_user / categories / 父鏈 CTE），確定性 unit。
"""
import pytest

from services import system_context
from services.system_context import get_system_context, reset_cache, MINIMAL_FALLBACK

pytestmark = pytest.mark.unit


class FakeConn:
    """依 SQL 形狀回傳：base(target_user NULL) / 角色 append(target_user@>) /
    面向 append(=ANY(categories)) / 父鏈(WITH RECURSIVE)。"""

    def __init__(self, base=None, role_appends=None, category_docs=None, parents=None):
        self.base = base
        self.role_appends = role_appends or {}     # target_user 值 → answer
        self.category_docs = category_docs or {}    # categories 值 → answer
        self.parents = parents or {}                # child → parent（category_config 階層）

    async def fetchrow(self, sql, *args):
        if "target_user IS NULL" in sql:
            return {"answer": self.base} if self.base else None
        if "target_user @>" in sql:
            v = self.role_appends.get(args[1])
            return {"answer": v} if v else None
        if "= ANY(categories)" in sql:
            v = self.category_docs.get(args[1])
            return {"answer": v} if v else None
        return None

    async def fetch(self, sql, *args):
        if "WITH RECURSIVE chain" in sql:
            key = args[0]
            # 組父鏈（自身→根），再反轉成 母在前、子在後
            chain, cur = [], key
            seen = set()
            while cur and cur not in seen:
                seen.add(cur)
                chain.append(cur)
                cur = self.parents.get(cur)
            return [{"category_value": c} for c in reversed(chain)]
        return []


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


def _facet_pool():
    """base + 母『系統合約』+ 子『狀態判斷』(parent=系統合約) + 售前 target_user append。"""
    return FakePool(FakeConn(
        base="BASE通用",
        role_appends={"prospect": "售前APPEND"},
        category_docs={"系統合約": "母共用_合約框架", "狀態判斷": "子面向_狀態判斷"},
        parents={"狀態判斷": "系統合約"}))


@pytest.fixture(autouse=True)
def _clear():
    reset_cache()
    yield
    reset_cache()


# ── 診斷面向：三層疊加 base + 母共用 + 子面向（母在前、子在後）──
@pytest.mark.req("domain-conversational-facets:2.1")
async def test_facet_three_level_stack():
    md = await get_system_context(_facet_pool(), "狀態判斷")
    assert md == "BASE通用\n\n母共用_合約框架\n\n子面向_狀態判斷"


# ── 只給母分類鍵 → base + 母共用（無子）──
@pytest.mark.req("domain-conversational-facets:2.1")
async def test_parent_key_loads_base_plus_parent_only():
    md = await get_system_context(_facet_pool(), "系統合約")
    assert md == "BASE通用\n\n母共用_合約框架"
    assert "子面向" not in md


# ── 角色級鍵（售前）→ target_user 單層，不吃面向（不回歸）──
@pytest.mark.req("domain-conversational-facets:7.1")
async def test_role_key_single_layer():
    md = await get_system_context(_facet_pool(), "prospect")
    assert md == "BASE通用\n\n售前APPEND"
    assert "合約框架" not in md and "狀態判斷" not in md


# ── 無鍵 → 只回 base ──
@pytest.mark.req("domain-conversational-facets:7.1")
async def test_no_key_base_only():
    assert await get_system_context(_facet_pool()) == "BASE通用"


# ── 面向鍵但無對應面向列 → 只回 base（不阻斷）──
@pytest.mark.req("domain-conversational-facets:2.3")
async def test_unknown_facet_returns_base_only():
    pool = FakePool(FakeConn(base="BASE通用", category_docs={}, parents={}))
    assert await get_system_context(pool, "不存在面向") == "BASE通用"


# ── per-key 快取隔離 + reset 重載 ──
@pytest.mark.req("domain-conversational-facets:2.5")
async def test_per_key_cache_isolation_and_reset():
    conn = FakeConn(base="BASE通用", role_appends={"prospect": "售前V1"},
                    category_docs={"系統合約": "母V1", "狀態判斷": "子V1"}, parents={"狀態判斷": "系統合約"})
    pool = FakePool(conn)
    assert await get_system_context(pool, "狀態判斷") == "BASE通用\n\n母V1\n\n子V1"
    assert await get_system_context(pool, "prospect") == "BASE通用\n\n售前V1"
    # 改資料未 reset → 仍快取舊值（per-key）
    conn.category_docs["狀態判斷"] = "子V2"
    assert await get_system_context(pool, "狀態判斷") == "BASE通用\n\n母V1\n\n子V1"
    reset_cache()
    assert await get_system_context(pool, "狀態判斷") == "BASE通用\n\n母V1\n\n子V2"


# ── base 缺 → MINIMAL_FALLBACK ──
@pytest.mark.req("domain-conversational-facets:2.3")
async def test_missing_base_fallback():
    pool = FakePool(FakeConn(base=None, category_docs={"狀態判斷": "子"}))
    assert await get_system_context(pool, "狀態判斷") == MINIMAL_FALLBACK


# ── DB 例外 → fallback 且不快取 ──
@pytest.mark.req("domain-conversational-facets:2.3")
async def test_db_exception_not_cached():
    class _Boom:
        def acquire(self):
            class _Ctx:
                async def __aenter__(self):
                    raise RuntimeError("db down")

                async def __aexit__(self, *a):
                    return False

            return _Ctx()

    assert await get_system_context(_Boom(), "狀態判斷") == MINIMAL_FALLBACK
    assert "狀態判斷" not in system_context._cache
