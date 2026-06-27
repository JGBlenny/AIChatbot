"""補測試：售前 grounding 三態選材 + 收斂行為（spec testing-traceability・任務 6.2/6.4・R5.2）。

以 AsyncMock 隔離 DB/檢索/LLM（unit）。驗證：
- grounding 三態：select=ids/category/vector 走對應決定性／向量路徑
- cta_mode：推薦型 force、事實型 suppress；事實型不帶情境 ctx
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.unit


def _engine():
    eng = ConversationalEngine(
        db_pool=MagicMock(),
        optimizer=MagicMock(),
        retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="md"),
        rules_loader=AsyncMock(return_value="規則"),
    )
    eng._grounding_by_ids = AsyncMock(return_value="IDS_GROUNDING")
    eng._grounding_by_category = AsyncMock(return_value="CAT_GROUNDING")
    eng.retriever.embedding_client.get_embedding = AsyncMock(return_value=[0.1, 0.2])
    eng.retriever._vector_search = AsyncMock(return_value=[{"answer": "VEC_GROUNDING"}])
    return eng


_STATE = {"collected_fields": {"identity": "個人房東", "scale": "30"}}


@pytest.mark.req("testing-traceability:5.2")
async def test_grounding_select_ids_uses_deterministic_ids_path():
    eng = _engine()
    cfg = SimpleNamespace(grounding_scope={"select": "ids", "kb_ids": [1, 2]})
    grounding, _ctx, cta = await eng._converge_grounding(_STATE, None, "訊息", cfg, "recommend")
    assert grounding == "IDS_GROUNDING"
    eng._grounding_by_ids.assert_awaited()
    eng.retriever._vector_search.assert_not_awaited()
    assert cta == "force"


@pytest.mark.req("testing-traceability:5.2")
async def test_grounding_select_category_uses_category_path():
    eng = _engine()
    cfg = SimpleNamespace(grounding_scope={"select": "category", "category": "方案"})
    grounding, _ctx, _cta = await eng._converge_grounding(_STATE, None, "訊息", cfg, "recommend")
    assert grounding == "CAT_GROUNDING"
    eng._grounding_by_category.assert_awaited()
    eng.retriever._vector_search.assert_not_awaited()


@pytest.mark.req("testing-traceability:5.2")
async def test_grounding_default_vector_path():
    eng = _engine()
    cfg = SimpleNamespace(grounding_scope={"select": "vector"})
    grounding, _ctx, _cta = await eng._converge_grounding(_STATE, None, "訊息", cfg, "recommend")
    assert "VEC_GROUNDING" in grounding
    eng.retriever._vector_search.assert_awaited()


@pytest.mark.req("testing-traceability:5.2")
async def test_answer_kind_suppresses_cta_and_drops_context():
    """事實型（answer）：cta_mode=suppress、不帶情境 ctx（避免回答前複述舊 profile）。"""
    eng = _engine()
    cfg = SimpleNamespace(grounding_scope={"select": "vector"})
    _grounding, ctx, cta = await eng._converge_grounding(_STATE, None, "價格多少", cfg, "answer")
    assert cta == "suppress"
    assert ctx is None


@pytest.mark.req("testing-traceability:5.2")
async def test_recommend_kind_carries_context_for_personalization():
    """推薦型：帶入已收集情境 ctx 做個人化。"""
    eng = _engine()
    cfg = SimpleNamespace(grounding_scope={"select": "vector"})
    _grounding, ctx, cta = await eng._converge_grounding(_STATE, None, "幫我推薦", cfg, "recommend")
    assert cta == "force"
    assert ctx and any(c["field_label"] == "identity" for c in ctx)
