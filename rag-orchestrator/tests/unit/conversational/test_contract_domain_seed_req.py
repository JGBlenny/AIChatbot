"""unit:合約領域系統脈絡種子（面向：母共用 系統合約 + 子面向 狀態判斷）+ 三層疊加（domain-conversational-facets 面向模型｜R5.1, R5.3, R5.4, R1.3）。

驗證：
  - 種子兩列：母『系統合約』(狀態模型/12 里程碑/續約/欄位) + 子『狀態判斷』(各階段下一步/可否操作)；
  - 違約金・滯納金金額試算框架不放常駐脈絡（不支援金額試算，避免通則數字幻覺）；
  - get_system_context('狀態判斷') 沿父鏈疊加 base + 母共用 + 子面向；bit_status 可由母共用逐位元解讀（12 階段）；
  - 種子僅新增 category='系統脈絡'（不動一般合約知識＝direct_answer 三出口不變）。
mock db_pool（target_user / categories / 父鏈），確定性 unit。
"""
import os
import re

import pytest

from services import system_context
from services.system_context import get_system_context, reset_cache

pytestmark = pytest.mark.unit

SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "database", "migrations", "seed_domain_contract_system_context.sql")


def _seed_sql():
    with open(SEED, encoding="utf-8") as f:
        return f.read()


def _seed_bodies():
    """回 (母共用, 子面向) 兩段 $CTX$ 本文（依種子出現順序：母在前、子在後）。"""
    blocks = re.findall(r"\$CTX\$(.*?)\$CTX\$", _seed_sql(), re.DOTALL)
    assert len(blocks) == 2, "種子應有兩列面向（母共用 + 子面向）"
    return blocks[0], blocks[1]


class _Conn:
    def __init__(self, base, category_docs, parents):
        self.base, self.category_docs, self.parents = base, category_docs, parents

    async def fetchrow(self, sql, *args):
        if "target_user IS NULL" in sql:
            return {"answer": self.base} if self.base else None
        if "target_user @>" in sql:
            return None  # 面向走 categories，非 target_user
        if "= ANY(categories)" in sql:
            v = self.category_docs.get(args[1])
            return {"answer": v} if v else None
        return None

    async def fetch(self, sql, *args):
        if "WITH RECURSIVE chain" in sql:
            chain, cur, seen = [], args[0], set()
            while cur and cur not in seen:
                seen.add(cur)
                chain.append(cur)
                cur = self.parents.get(cur)
            return [{"category_value": c} for c in reversed(chain)]
        return []


class _Pool:
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


@pytest.fixture(autouse=True)
def _clear():
    reset_cache()
    yield
    reset_cache()


# ── R5.1 母共用『系統合約』涵蓋狀態模型/12 里程碑/續約/欄位 ──
@pytest.mark.req("domain-conversational-facets:5.1")
def test_parent_shared_covers_structure():
    parent, _ = _seed_bodies()
    # 母共用＝制度框架（12 里程碑表供解釋參考）；解碼/可否操作由 formatter 決定性算，不放 base
    for v in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048):
        assert str(v) in parent, f"母共用缺里程碑值 {v}"
    for stage in ("簽約前", "執行中", "歷史"):
        assert stage in parent
    assert "father_id" in parent and "同名多份" in parent
    assert "點交＝交屋" in parent and "點退＝退租" in parent


# ── R5.1 子面向『狀態判斷』＝各階段下一步/可否操作 ──
@pytest.mark.req("domain-conversational-facets:5.1")
def test_child_facet_is_status_judgment():
    _, child = _seed_bodies()
    assert "下一步" in child or "能做什麼" in child
    assert "可否動作前提" in child or "可否" in child
    # 面向不重複塞入母共用的 12 里程碑表（各司其職，精簡）
    assert "| 值 | 里程碑" not in child


# ── 金額試算框架不放常駐脈絡（母子都不含）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_no_penalty_latefee_calc_framework():
    parent, child = _seed_bodies()
    for body in (parent, child):
        assert "型態0" not in body and "型態1" not in body
        assert "違約金" not in body and "滯納金" not in body


# ── R5.4 種子僅 INSERT 系統脈絡列（不動一般合約知識出口）──
@pytest.mark.req("domain-conversational-facets:5.4")
def test_seed_only_inserts_system_context():
    sql = _seed_sql()
    assert sql.count("INSERT INTO knowledge_base") == 2  # 母 + 子
    assert "'系統脈絡'" in sql
    assert "UPDATE knowledge_base" not in sql and "DELETE FROM knowledge_base" not in sql


# ── R5.3/R1.3 三層疊加：base + 母共用 + 子面向；bit_status 逐位元可由母共用解讀 ──
@pytest.mark.req("domain-conversational-facets:5.3")
async def test_three_level_stack_and_bit_status_decodable():
    parent, child = _seed_bodies()
    pool = _Pool(_Conn(base="通用BASE",
                       category_docs={"系統合約": parent, "狀態判斷": child},
                       parents={"狀態判斷": "系統合約"}))
    md = await get_system_context(pool, "狀態判斷")
    assert md.startswith("通用BASE")
    assert parent in md and child in md
    # bit_status=7 → 1+2+4：三里程碑語義都在（母共用提供 12 階段對照）
    assert "合約建立" in md and "已送簽約邀請" in md and "租客已簽" in md


# ── 疊加後仍守大小上限（每輪注入；面向讓每次只載命中的那個）──
@pytest.mark.req("domain-conversational-facets:5.1")
async def test_layered_size_within_budget():
    parent, child = _seed_bodies()
    pool = _Pool(_Conn(base="x" * 560, category_docs={"系統合約": parent, "狀態判斷": child},
                       parents={"狀態判斷": "系統合約"}))
    md = await get_system_context(pool, "狀態判斷")
    assert len(md) <= system_context.MAX_CHARS_WARN, f"疊加 {len(md)} 超上限"
