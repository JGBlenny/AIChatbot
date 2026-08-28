"""integration：`repair_create` 的 Face entry points（任務 9.2／9.3｜需求 5.3, 6.6）。

⚠️ **任務 9.1 的前提已過期**：spec 記載「`修繕報修` 目前 0 個知識進場點」，
但實查 dev DB（業主裁定本地≡線上）已有 **5 筆**，由 `conversational-repair` 任務 3.3
於 **2026-07-12**（commit 646743a0）以 `tools/seed_repair_facet_knowledge.py` 種下，
且正是設計決策 3 的**選項 C**（新增語義正確的租客向觸發知識，
`categories={修繕報修}`、`target_user={tenant}`），未替 3365／4249 加標。
本檔因此不再新增知識，改為**釘住既有進場點並驗證不誤進場**。

驅動 **production 進場決策鏈**（決定性、零 LLM）：
  `retrieve_knowledge_hybrid(top1)` → `routers.chat._diagnosis_config_for_knowledge`
門檻一律取自 production 唯一讀值點 `DecisionConfig.load()`，**不在本檔複刻**。

角色維度與帳務／合約面向不同：`repair_create` 是 **tenant／b2c**。
"""
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
PRODUCTION_TOP_K = 5
TARGET_USER = "tenant"
MODE = "b2c"
FACET_CATEGORY = "修繕報修"
FACET_KEY = "repair_create"

#: ① 明確記錄的 Face entry points（EntryPointChange.declared_entry_points）
DECLARED_ENTRY_POINTS = {
    4416: "報修 修繕 東西壞了 想報修",
    4418: "馬桶不通 排水堵塞 水管堵住",
    4420: "修繕進度 報修單 修得怎樣了 處理到哪",
    4421: "漏水 滲水 天花板漏水 水管漏水",
    4422: "冷氣壞了 電器壞了 家電故障",
}


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture(scope="module")
def retriever():
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    return VendorKnowledgeRetrieverV2()


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


async def _route(retriever, pool, question):
    """與 `test_facet_entry_routing_req._route` 同一條 production seam，只是角色維度不同。"""
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig

    cfg_thresholds = DecisionConfig.load()
    rows = await retriever.retrieve_knowledge_hybrid(
        query=question, vendor_id=VENDOR_ID, top_k=PRODUCTION_TOP_K,
        similarity_threshold=cfg_thresholds.kb_threshold,
        target_user=TARGET_USER, mode=MODE)
    best = rows[0] if rows else None
    if not best:
        return ("single", "no-hit", None)
    cfg, _face_authority = await _diagnosis_config_for_knowledge(
        pool, best, cfg_thresholds, user_message=question)
    if cfg is None:
        return ("single", "not-routed", best)
    return ("dialog", getattr(cfg, "key", "?"), best)


def _fmt(best):
    if not best:
        return "（無命中）"
    return (f"top1={best.get('question_summary', '')[:24]}｜"
            f"sim={best.get('similarity', 0):.3f}｜cats={best.get('categories')}")


# ════════ 9.2 ① 進場點確實存在且指向 repair_create ════════

@pytest.mark.req("conversational-routing-execution:5.3")
async def test_declared_entry_points_still_exist(pool):
    """進場點是**資料**，不是程式——任何人動了它就等於改了 routing（R6.6）。"""
    rows = await pool.fetch(
        "SELECT id, question_summary, target_user, action_type, is_active"
        " FROM knowledge_base WHERE categories @> ARRAY[$1]::text[] ORDER BY id",
        FACET_CATEGORY)
    found = {r["id"]: r for r in rows}
    missing = set(DECLARED_ENTRY_POINTS) - set(found)
    assert not missing, f"宣告的進場點消失：{sorted(missing)}"
    for kid in DECLARED_ENTRY_POINTS:
        r = found[kid]
        assert r["is_active"], f"kb{kid} 被停用"
        assert list(r["target_user"] or []) == ["tenant"], \
            f"kb{kid} 的 target_user 變了：{r['target_user']}——會替錯的角色開出進場路徑"
    extra = set(found) - set(DECLARED_ENTRY_POINTS)
    assert not extra, (f"出現未宣告的進場點 {sorted(extra)}："
                       "新增掛 修繕報修 的知識即新增 Face entry point，須走 R6.6 回歸")


@pytest.mark.req("conversational-routing-execution:5.3")
async def test_category_routes_to_the_repair_facet(pool):
    """`config_for_category('修繕報修')` → `repair_create`（by_category 索引，非重新推導）。"""
    from services.conversational_config import config_for_category
    cfg = await config_for_category(pool, FACET_CATEGORY)
    assert cfg is not None and cfg.key == FACET_KEY and cfg.enabled


# ════════ 9.2 ② 以現行 production routing 規則回歸 ════════

@pytest.mark.req("conversational-routing-execution:5.3")
@pytest.mark.parametrize("question", [
    "我房間的冷氣壞了想報修",
    "馬桶不通可以幫我處理嗎",
    "天花板在漏水",
    "東西壞了要怎麼報修",
])
async def test_tenant_repair_intent_enters_the_facet(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail == FACET_KEY, \
        f"「{question}」未進 {FACET_KEY}：{kind}/{detail}｜{_fmt(best)}"


# ════════ 9.3 ③ misroute probe：資訊型問題不得誤進交易面向 ════════
#
# ⚠️ 這條的後果不是「答錯」而是**替錯的人開報修單**——交易面向的誤進場成本高於資訊面向。

@pytest.mark.req("conversational-routing-execution:5.3")
@pytest.mark.parametrize("question", [
    "租金怎麼繳",
    "合約什麼時候到期",
    "押金什麼時候退",
    "電費怎麼算",
])
async def test_informational_questions_do_not_enter_repair(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert not (kind == "dialog" and detail == FACET_KEY), \
        f"「{question}」誤進 {FACET_KEY}（會替租客開報修單）：{_fmt(best)}"
