"""unit:通用 base 拆出售前 → 合約不吃售前脈絡（domain-conversational-facets 後續修正｜R2.2, R7.1, R6.1）。

背景：id 3622（target_user=NULL）實為「售前系統脈絡」（競品協定/CTA/功能索引），疊加後合約仍吃到售前。
修正：migration 把 3622 切成「真通用 base」＋「售前 append(target_user=prospect)」。
  - 售前 = base + 售前 append = 原文（不回歸）；
  - 合約 = base + 合約 append（不含售前）。
  - chat.py 三處售前合成改傳領域鍵 target_user（不再 bare 呼叫、不硬編 'prospect'）。
mock 疊加後資料，確定性 unit。
"""
import inspect
import os

import pytest

from services.system_context import get_system_context, reset_cache
from routers import chat

pytestmark = pytest.mark.unit

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                         "database", "migrations", "split_base_system_context_extract_presales.sql")

BASE_UNIVERSAL = "## 1. 定位\n產品是什麼\n## 5. 合規\n不報價、不杜撰"
PRESALES_APPEND = "## 5b. 競品處理協定\n不主動點名\n## 6. CTA 出口\ntrial_form\n## 7. 功能對照索引\n痛點→功能"
CONTRACT_APPEND = "## 12 里程碑\nbit_status 逐位元\n續約 father_id"


class _Pool:
    def __init__(self, base, appends):
        self._base, self._appends = base, appends

    def acquire(self):
        base, appends = self._base, self._appends

        class _Conn:
            async def fetchrow(self, sql, *args):
                if "target_user IS NULL" in sql:
                    return {"answer": base}
                if "target_user @>" in sql:
                    v = appends.get(args[1])
                    return {"answer": v} if v else None
                return None

        conn = _Conn()

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


# ── 售前疊加＝base＋售前 append（含競品/CTA/功能索引 → 不回歸）──
@pytest.mark.req("domain-conversational-facets:7.1")
async def test_presales_gets_base_plus_presales_append():
    pool = _Pool(BASE_UNIVERSAL, {"prospect": PRESALES_APPEND, "property_manager": CONTRACT_APPEND})
    md = await get_system_context(pool, "prospect")
    assert md == BASE_UNIVERSAL + "\n\n" + PRESALES_APPEND
    for m in ("競品處理協定", "CTA", "功能對照索引"):   # 售前能力仍在
        assert m in md


# ── 合約疊加＝base＋合約 append，且**不含**售前銷售內容（缺口 2 真正解掉）──
@pytest.mark.req("domain-conversational-facets:2.2")
async def test_contract_excludes_presales_content():
    pool = _Pool(BASE_UNIVERSAL, {"prospect": PRESALES_APPEND, "property_manager": CONTRACT_APPEND})
    md = await get_system_context(pool, "property_manager")
    assert "bit_status" in md and "續約" in md              # 有合約架構
    for m in ("競品處理協定", "CTA", "功能對照索引", "trial_form"):
        assert m not in md, f"合約不應吃到售前內容：{m}"


# ── chat.py 售前合成不得 bare 呼叫（須傳領域鍵；否則拆分後售前拿不到售前 append）──
@pytest.mark.req("domain-conversational-facets:7.1")
def test_chat_no_bare_system_context_call():
    src = inspect.getsource(chat)
    assert "get_system_context(db_pool)" not in src
    assert "get_system_context(req.app.state.db_pool)" not in src


# ── migration 具內容保全自檢（不可逆則中止，避免售前回歸）+ 邊界標記 ──
@pytest.mark.req("domain-conversational-facets:7.1")
def test_migration_has_content_preserving_guard():
    sql = open(MIGRATION, encoding="utf-8").read()
    assert "## 5b" in sql                       # 切分邊界
    assert "RAISE EXCEPTION" in sql             # 不可逆則中止
    assert "ARRAY['prospect']" in sql           # 售前 append 落 target_user=prospect
