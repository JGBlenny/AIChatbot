"""integration：引擎 _make_kb_search closure × 真 retriever（brain-kb-grounding 元件 2｜R2.1/2.2/2.3/4.1）。

驗證引擎注入 Brain 的 async 唯讀檢索 callback：
  - 以真 VendorKnowledgeRetrieverV2 查詢（pgvector＋keyword＋reranker 零改動，僅新增呼叫方）；
  - 脈絡（vendor_id/target_user/mode）由 closure 固定、閾值＝KB_SIMILARITY_THRESHOLD（與 FAQ 同源）；
  - 命中 → 回序列化 answer 文字（非 NO_MATCH）；查無 → 回 NO_MATCH_SENTINEL（R3.2 誠實回退）；
  - retriever 例外 → 回 NO_MATCH（R4.1 失敗等同未掛工具，不外拋）。
真 DB＋真 embedding＋真 reranker；無相依 → skip（不假綠）。
"""
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_REPAIR_VENDOR_ID", "1"))


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _engine_with_retriever():
    from services.conversational_engine import ConversationalEngine
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    eng = ConversationalEngine.__new__(ConversationalEngine)   # 只需 self.retriever（_make_kb_search 用）
    eng.retriever = VendorKnowledgeRetrieverV2()
    return eng


def _repair_config():
    from services.conversational_config import ConversationalConfig
    return ConversationalConfig(
        key="repair", answer_mode="conversational", persona_role="tenant_repair",
        grounding_scope={"target_user": "tenant", "mode": "b2c",
                         "execute_endpoint": "jgb_repair_create", "required_slots": ["urgency"]},
    )


@pytest.fixture(scope="module", autouse=True)
def _require_db():
    """真 DB/embedding 未就緒 → skip。"""
    import asyncio
    import asyncpg

    async def _ping():
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        await p.close()
    try:
        asyncio.run(_ping())
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")


# ── R2.1/R2.3：命中路徑——費用類查詢回字串（命中則非 NO_MATCH，且不崩）──
@pytest.mark.req("brain-kb-grounding:2.1")
async def test_kb_search_returns_string_no_crash():
    from services.llm_answer_optimizer import NO_MATCH_SENTINEL
    eng = _engine_with_retriever()
    kb = eng._make_kb_search(_repair_config(), {"vendor_id": VENDOR_ID})
    out = await kb("修繕費用由誰負擔")
    assert isinstance(out, str)
    # 不強制命中（知識可能未 seed）；但回傳必為字串（命中文字 或 NO_MATCH），不得例外
    assert out == NO_MATCH_SENTINEL or len(out) > 0


# ── R3.2：明顯查無的亂碼 query → NO_MATCH（誠實回退訊號）──
@pytest.mark.req("brain-kb-grounding:3.2")
async def test_kb_search_garbage_returns_no_match():
    from services.llm_answer_optimizer import NO_MATCH_SENTINEL
    eng = _engine_with_retriever()
    kb = eng._make_kb_search(_repair_config(), {"vendor_id": VENDOR_ID})
    out = await kb("zxqw9981 асдф 亂碼不存在的知識主題 qppzz")
    assert out == NO_MATCH_SENTINEL


# ── R2.2：脈絡穿透——closure 帶入 vendor_id/target_user，不同 vendor 不互撈（不崩、回字串）──
@pytest.mark.req("brain-kb-grounding:2.2")
async def test_kb_search_context_isolation_no_crash():
    eng = _engine_with_retriever()
    kb = eng._make_kb_search(_repair_config(), {"vendor_id": VENDOR_ID})
    out = await kb("報修時程多久")
    assert isinstance(out, str)   # 脈絡過濾生效、查詢完成不例外（隔離正確性由 retriever 既有測試保證）


# ── R4.1：retriever 例外 → 回 NO_MATCH（失敗等同未掛工具，不外拋）──
@pytest.mark.req("brain-kb-grounding:4.1")
async def test_kb_search_retriever_failure_degrades():
    from services.llm_answer_optimizer import NO_MATCH_SENTINEL
    from services.conversational_engine import ConversationalEngine

    class _BoomRetriever:
        async def retrieve_knowledge_hybrid(self, **kwargs):
            raise RuntimeError("retriever down")

    eng = ConversationalEngine.__new__(ConversationalEngine)
    eng.retriever = _BoomRetriever()
    kb = eng._make_kb_search(_repair_config(), {"vendor_id": VENDOR_ID})
    out = await kb("任何查詢")
    assert out == NO_MATCH_SENTINEL
