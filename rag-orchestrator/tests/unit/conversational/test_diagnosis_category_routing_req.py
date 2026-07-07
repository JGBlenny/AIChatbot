"""unit:分類路由出口決策（conversational-diagnosis 任務 6.1 / R1.1, R1.2, R1.4, R4.4, R7.2）。

`_knowledge_category(best_knowledge)`：取知識分類候選（categories 多值優先，退 category 單值）。
`_diagnosis_config_for_knowledge(db_pool, best_knowledge, threshold)`：最高順位知識達門檻且分類
命中診斷面向 → 回該對話設定；未達門檻/未命中 → None（落回既有處理）。
以假 db_pool 注入「對話規則」列，確定性 unit。
"""
import pytest

from routers.chat import _knowledge_category, _diagnosis_config_for_knowledge
from services import conversational_config as cc

pytestmark = pytest.mark.unit


# ── 假 db_pool（同 test_config_for_category_req.py 樣式）──
class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, *a, **k):
        return self._rows


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def __init__(self, rows):
        self._conn = _FakeConn(rows)

    def acquire(self):
        return _FakeAcquire(self._conn)


def _diag_row(category="條件診斷:合約", key="contract_diag"):
    cfg = {"key": key, "persona_role": "property_manager", "answer_mode": "conversational",
           "enabled": True, "topic_scope": {"mode": "category", "category": category}}
    return {"target_user": ["property_manager"], "generation_metadata": {"conversational_config": cfg}}


@pytest.fixture(autouse=True)
def _reset_cache():
    cc.reset_cache()
    yield
    cc.reset_cache()


# ── _knowledge_category：多值/單值/皆無 ──
@pytest.mark.req("conversational-diagnosis:1.3")
def test_knowledge_category_multi_value_preferred():
    assert _knowledge_category({"categories": ["條件診斷:合約", "其他"], "category": "單值"}) == \
        ["條件診斷:合約", "其他"]


@pytest.mark.req("conversational-diagnosis:1.3")
def test_knowledge_category_single_fallback():
    assert _knowledge_category({"category": "條件診斷:合約"}) == ["條件診斷:合約"]


@pytest.mark.req("conversational-diagnosis:1.3")
def test_knowledge_category_none():
    assert _knowledge_category({}) == []
    assert _knowledge_category(None) == []


# ── _diagnosis_config_for_knowledge：門檻 + 分類命中 ──
@pytest.mark.req("conversational-diagnosis:1.1")
async def test_routes_when_threshold_met_and_category_hits():
    pool = _FakePool([_diag_row()])
    bk = {"id": 1, "similarity": 0.9, "categories": ["條件診斷:合約"]}
    cfg = await _diagnosis_config_for_knowledge(pool, bk, threshold=0.75)
    assert cfg is not None and cfg.key == "contract_diag"


@pytest.mark.req("conversational-diagnosis:7.2")
async def test_no_route_below_threshold():
    pool = _FakePool([_diag_row()])
    bk = {"id": 1, "similarity": 0.5, "categories": ["條件診斷:合約"]}  # < 門檻
    assert await _diagnosis_config_for_knowledge(pool, bk, threshold=0.75) is None


@pytest.mark.req("conversational-diagnosis:1.2")
async def test_no_route_when_category_misses():
    pool = _FakePool([_diag_row()])
    bk = {"id": 1, "similarity": 0.9, "categories": ["一般合約知識"]}  # 非診斷分類
    assert await _diagnosis_config_for_knowledge(pool, bk, threshold=0.75) is None


@pytest.mark.req("conversational-diagnosis:1.4")
async def test_multi_category_second_hits():
    pool = _FakePool([_diag_row()])
    bk = {"id": 1, "similarity": 0.9, "categories": ["一般合約知識", "條件診斷:合約"]}
    cfg = await _diagnosis_config_for_knowledge(pool, bk, threshold=0.75)
    assert cfg is not None and cfg.key == "contract_diag"


@pytest.mark.req("conversational-diagnosis:7.2")
async def test_no_route_when_best_knowledge_none():
    pool = _FakePool([_diag_row()])
    assert await _diagnosis_config_for_knowledge(pool, None, threshold=0.75) is None
