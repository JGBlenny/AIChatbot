"""unit:依分類查對話設定（conversational-diagnosis 任務 1 / R1.3, R6.2）。

驗 `config_for_category` 與 `by_category` 索引：topic_scope.mode=='category' 且 enabled 者
以其 category 入索引；非 category 模式/未啟用/未命中→None；多面向各自索引；reset 後重載。

以假 db_pool 注入「對話規則」列（target_user + generation_metadata.conversational_config），
不碰真實 DB → 確定性 unit。
"""
import pytest

from services import conversational_config as cc

pytestmark = pytest.mark.unit


# ── 假 db_pool（acquire() async context → conn.fetch 回固定列）──
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


def _row(role, key, mode, category=None, enabled=True):
    cfg = {"key": key, "persona_role": role, "answer_mode": "conversational",
           "enabled": enabled, "topic_scope": {"mode": mode}}
    if category:
        cfg["topic_scope"]["category"] = category
    return {"target_user": [role], "generation_metadata": {"conversational_config": cfg}}


@pytest.fixture(autouse=True)
def _reset_cache():
    cc.reset_cache()
    yield
    cc.reset_cache()


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_category_hit_returns_config():
    pool = _FakePool([_row("property_manager", "contract_diag", "category", "條件診斷:合約")])
    cfg = await cc.config_for_category(pool, "條件診斷:合約")
    assert cfg is not None and cfg.key == "contract_diag"


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_category_miss_returns_none():
    pool = _FakePool([_row("property_manager", "contract_diag", "category", "條件診斷:合約")])
    assert await cc.config_for_category(pool, "不存在的分類") is None


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_mode_all_not_indexed():
    """topic_scope.mode='all'（如售前）不進 by_category。"""
    pool = _FakePool([_row("prospect", "presales", "all")])
    assert await cc.config_for_category(pool, "條件診斷:合約") is None


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_disabled_not_indexed():
    pool = _FakePool([_row("property_manager", "contract_diag", "category", "條件診斷:合約", enabled=False)])
    assert await cc.config_for_category(pool, "條件診斷:合約") is None


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_multiple_facets_each_indexed():
    pool = _FakePool([
        _row("property_manager", "contract_diag", "category", "條件診斷:合約"),
        _row("property_manager", "bill_diag", "category", "條件診斷:帳單"),
    ])
    assert (await cc.config_for_category(pool, "條件診斷:合約")).key == "contract_diag"
    assert (await cc.config_for_category(pool, "條件診斷:帳單")).key == "bill_diag"


@pytest.mark.req("conversational-diagnosis:1.3")
async def test_none_category_returns_none():
    pool = _FakePool([])
    assert await cc.config_for_category(pool, None) is None
