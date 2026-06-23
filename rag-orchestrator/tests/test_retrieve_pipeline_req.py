"""核心檢索 orchestration 確定性 unit（spec unit-coverage-rebuild・任務 7・R5/檢索 pipeline）。

驗 base_retriever.retrieve() 決定「撈回什麼」的編排邏輯——這是日常無保護的核心：
- reranker 輸入閘控（hotfix：下限砍除 / 上限截斷 / keyword_fallback 優先）← 最高優先
- embedding 失敗 → keyword fallback
- 改寫查詢聯集去重（依 id）
- 結果不足 top_k → 關鍵字補位
- threshold 過濾（含 return_unfiltered 繞過）
- top_k 依 final similarity 排序截斷

全程 mock IO 邊界（_get_embedding/_vector_search/_keyword_search/_apply_semantic_reranker），
不碰真實 DB / 不打 reranker 服務 → 確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.base_retriever import BaseRetriever

pytestmark = pytest.mark.unit


class _PipelineStub(BaseRetriever):
    """具體化 ABC 抽象方法；實際行為由各測試以 monkeypatch 覆寫。"""

    async def _vector_search(self, *a, **k):
        return []

    async def _keyword_search(self, *a, **k):
        return []

    def _format_result(self, row):
        return row


@pytest.fixture
def retriever():
    r = _PipelineStub()
    # 隔離外部相依：預設關閉 rewriter / reranker，由測試按需開啟
    r.query_rewriter = None
    r.semantic_reranker = None
    r._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return r


def _ids(results):
    return [r.get("id") for r in results]


# ---------------------------------------------------------------------------
# 7.1 reranker 輸入閘控（hotfix，最高優先）
# ---------------------------------------------------------------------------

@pytest.mark.req("unit-coverage-rebuild:5")
async def test_reranker_input_floor_drops_low_vector_keeps_keyword_fallback(retriever, monkeypatch):
    """下限砍除：vector_similarity < MIN 的 vector 項丟棄；keyword_fallback 項一律保留。"""
    monkeypatch.setenv("RERANKER_MIN_VECTOR_SIMILARITY", "0.3")
    monkeypatch.setenv("RERANKER_INPUT_LIMIT", "20")
    candidates = [
        {"id": 1, "vector_similarity": 0.5, "search_method": "vector"},
        {"id": 2, "vector_similarity": 0.4, "search_method": "vector"},
        {"id": 3, "vector_similarity": 0.1, "search_method": "vector"},          # 砍
        {"id": 4, "vector_similarity": 0.2, "search_method": "vector"},          # 砍
        {"id": 5, "vector_similarity": 0.0, "search_method": "keyword_fallback"},  # 留
    ]
    retriever._vector_search = AsyncMock(return_value=candidates)
    retriever.semantic_reranker = object()  # 觸發 Step 5 閘控
    spy = MagicMock(side_effect=lambda q, cands, k: cands)
    retriever._apply_semantic_reranker = spy

    await retriever.retrieve("q", 1, top_k=10,
                             enable_keyword_fallback=False, enable_keyword_boost=False)

    spy.assert_called_once()
    sent = spy.call_args.args[1]
    assert set(_ids(sent)) == {1, 2, 5}, f"下限砍除後送 rerank 的候選錯誤：{_ids(sent)}"


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_reranker_input_limit_prefers_keyword_then_top_vector(retriever, monkeypatch):
    """上限截斷：超過 LIMIT 時優先保留 keyword_fallback，再以 vector_similarity 由高補位。"""
    monkeypatch.setenv("RERANKER_MIN_VECTOR_SIMILARITY", "0.3")
    monkeypatch.setenv("RERANKER_INPUT_LIMIT", "2")
    candidates = [
        {"id": 1, "vector_similarity": 0.9, "search_method": "vector"},
        {"id": 2, "vector_similarity": 0.8, "search_method": "vector"},
        {"id": 3, "vector_similarity": 0.7, "search_method": "vector"},
        {"id": 4, "vector_similarity": 0.0, "search_method": "keyword_fallback"},
    ]
    retriever._vector_search = AsyncMock(return_value=candidates)
    retriever.semantic_reranker = object()
    spy = MagicMock(side_effect=lambda q, cands, k: cands)
    retriever._apply_semantic_reranker = spy

    await retriever.retrieve("q", 1, top_k=10,
                             enable_keyword_fallback=False, enable_keyword_boost=False)

    sent = spy.call_args.args[1]
    # keyword(4) 必留，vector 槽剩 1 → 取最高 vector(1)
    assert set(_ids(sent)) == {1, 4}, f"上限截斷選錯候選：{_ids(sent)}"


# ---------------------------------------------------------------------------
# 7.2 embedding fallback / 改寫聯集去重 / 不足補位
# ---------------------------------------------------------------------------

@pytest.mark.req("unit-coverage-rebuild:5")
async def test_embedding_failure_falls_back_to_keyword(retriever):
    """embedding 失敗且 fallback 啟用 → 直接走 _keyword_search 回傳。"""
    retriever._get_embedding = AsyncMock(return_value=None)
    sentinel = [{"id": 99, "similarity": 0.9}]
    retriever._keyword_search = AsyncMock(return_value=sentinel)

    out = await retriever.retrieve("q", 1, enable_keyword_fallback=True)
    assert out == sentinel
    retriever._keyword_search.assert_awaited_once()


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_embedding_failure_without_fallback_returns_empty(retriever):
    """embedding 失敗且 fallback 關閉 → 回 []（不臆測）。"""
    retriever._get_embedding = AsyncMock(return_value=None)
    retriever._keyword_search = AsyncMock(return_value=[{"id": 1}])

    out = await retriever.retrieve("q", 1, enable_keyword_fallback=False)
    assert out == []
    retriever._keyword_search.assert_not_awaited()


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_query_rewrite_union_dedups_by_id(retriever):
    """改寫查詢結果與原查詢取聯集、依 id 去重；新增項標 search_method=query_rewrite。"""
    retriever.query_rewriter = MagicMock()
    retriever.query_rewriter.rewrite.return_value = ["改寫查詢"]
    retriever._vector_search = AsyncMock(side_effect=[
        [{"id": 1, "vector_similarity": 0.9}, {"id": 2, "vector_similarity": 0.9}],  # 原查詢
        [{"id": 2, "vector_similarity": 0.9}, {"id": 3, "vector_similarity": 0.9}],  # 改寫（2 重複）
    ])

    out = await retriever.retrieve("q", 1, top_k=10,
                                   enable_keyword_fallback=False, enable_keyword_boost=False)
    assert set(_ids(out)) == {1, 2, 3}
    added = next(r for r in out if r["id"] == 3)
    assert added.get("search_method") == "query_rewrite"
    assert added.get("rewrite_source") == "改寫查詢"


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_keyword_fallback_tops_up_when_below_top_k(retriever):
    """向量結果不足 top_k → 以關鍵字補位，補入項標 search_method=keyword_fallback。"""
    retriever._vector_search = AsyncMock(return_value=[{"id": 1, "vector_similarity": 0.9}])
    retriever._keyword_search = AsyncMock(return_value=[
        {"id": 2, "keyword_score": 0.9},
        {"id": 3, "keyword_score": 0.9},
    ])

    out = await retriever.retrieve("q", 1, top_k=3,
                                   enable_keyword_fallback=True, enable_keyword_boost=False)
    assert set(_ids(out)) == {1, 2, 3}
    for r in out:
        if r["id"] in (2, 3):
            assert r.get("search_method") == "keyword_fallback"
    # 補位量＝top_k - 既有
    retriever._keyword_search.assert_awaited_once()
    assert retriever._keyword_search.await_args.args[2] == 2  # top_k(3) - 既有(1)


# ---------------------------------------------------------------------------
# 7.3 threshold 過濾 / return_unfiltered 繞過 / top_k 排序截斷
# ---------------------------------------------------------------------------

@pytest.mark.req("unit-coverage-rebuild:5")
async def test_threshold_filters_low_similarity(retriever):
    """final similarity < threshold 的項目被過濾。"""
    retriever._vector_search = AsyncMock(return_value=[
        {"id": 1, "vector_similarity": 0.9},
        {"id": 2, "vector_similarity": 0.2},
    ])
    out = await retriever.retrieve("q", 1, top_k=10, similarity_threshold=0.6,
                                   enable_keyword_fallback=False, enable_keyword_boost=False)
    assert set(_ids(out)) == {1}


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_return_unfiltered_bypasses_threshold(retriever):
    """return_unfiltered=True → 跳過 threshold 過濾，低分候選保留。"""
    retriever._vector_search = AsyncMock(return_value=[
        {"id": 1, "vector_similarity": 0.9},
        {"id": 2, "vector_similarity": 0.2},
    ])
    out = await retriever.retrieve("q", 1, top_k=10, similarity_threshold=0.6,
                                   enable_keyword_fallback=False, enable_keyword_boost=False,
                                   return_unfiltered=True)
    assert set(_ids(out)) == {1, 2}


@pytest.mark.req("unit-coverage-rebuild:5")
async def test_sorts_by_similarity_and_truncates_top_k(retriever):
    """依 final similarity 由高到低排序，截斷至 top_k。"""
    retriever._vector_search = AsyncMock(return_value=[
        {"id": 1, "vector_similarity": 0.9},
        {"id": 2, "vector_similarity": 0.6},
        {"id": 3, "vector_similarity": 0.7},
        {"id": 4, "vector_similarity": 0.8},
    ])
    out = await retriever.retrieve("q", 1, top_k=2, similarity_threshold=0.5,
                                   enable_keyword_fallback=False, enable_keyword_boost=False)
    assert _ids(out) == [1, 4]  # 0.9, 0.8 取前二且降序
