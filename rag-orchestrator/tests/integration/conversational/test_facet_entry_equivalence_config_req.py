"""integration：任務 2.5 等價判定的**配置側前提**（spec conversational-routing-execution 任務 2.4）。

任務 2.5 證明 `trigger_facet_key` 直達與分類路由在 C4b 標的上等價，但該結論**取決於 DB seed**：
只有當面向**未宣告** `enabled_gate` 與 `prefill_api` 時，`_seed_repair_facet` 的三個前置
才會退化為 no-op、兩路才收斂到同一個 `_conversational_respond` 呼叫。

程式側前提由 `tests/unit/conversational/test_facet_entry_path_equivalence_req.py` 鎖住。
**本檔鎖配置側**：直接自 DB 載入兩個 Face config 斷言四項宣告仍然缺席。

⚠️ 這不是新增設計，而是測「2.5 已成立之判定的外部前提仍然成立」。
若日後有人只改 seed（例如替 billing_anomaly 補上 enabled_gate），即使程式碼完全沒變，
本檔也會立刻紅——而不會讓 C4b 繼續用一條已不等價的入口。
"""
import os

import pytest

pytestmark = pytest.mark.integration

#: 依賴直達進場等價性的面向（C4b 的兩個標的）
EQUIVALENCE_DEPENDENT_FACETS = ("bill_diagnosis", "billing_anomaly")

#: 一旦宣告即破壞等價的鍵——`_seed_repair_facet` 會因此執行額外前置
EQUIVALENCE_BREAKING_KEYS = ("enabled_gate", "prefill_api")


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_test"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    from services import conversational_config as cc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache()
    yield p
    cc.reset_cache()
    await p.close()


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("facet_key", EQUIVALENCE_DEPENDENT_FACETS)
async def test_facet_declares_no_equivalence_breaking_keys(pool, facet_key):
    """兩個 C4b 面向皆不得宣告 enabled_gate／prefill_api，否則直達進場不再等價。"""
    from services.conversational_config import config_for_key
    cfg = await config_for_key(pool, facet_key)
    if cfg is None:
        pytest.skip(f"面向 {facet_key} 未供裝（見 scripts/provision-test-db.sh）")
    scope = getattr(cfg, "grounding_scope", None) or {}
    declared = [k for k in EQUIVALENCE_BREAKING_KEYS if scope.get(k)]
    assert not declared, (
        f"面向 {facet_key} 宣告了 {declared}——任務 2.5 的直達進場等價性已失效。"
        f"C4b 不得再以 trigger_facet_key 進場，須改回分類路由（並重新評估 2.4 的供裝深度）。")


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("facet_key", EQUIVALENCE_DEPENDENT_FACETS)
async def test_both_config_indexes_resolve_to_same_object(pool, facet_key):
    """by_key（直達）與 by_category（分類路由）必須解析到同一份 config。

    兩路若拿到不同物件，即使欄位值相同也可能因快取／載入時機而分歧。
    """
    from services.conversational_config import config_for_category, config_for_key
    by_key = await config_for_key(pool, facet_key)
    if by_key is None:
        pytest.skip(f"面向 {facet_key} 未供裝")
    topic = (getattr(by_key, "topic_scope", None) or {}).get("category")
    assert topic, f"{facet_key} 未宣告 topic_scope.category，分類路由無法進場"
    by_cat = await config_for_category(pool, topic)
    assert by_cat is by_key, (
        f"{facet_key}：by_category('{topic}') 與 by_key 非同一物件——兩條進場路徑已分歧")
