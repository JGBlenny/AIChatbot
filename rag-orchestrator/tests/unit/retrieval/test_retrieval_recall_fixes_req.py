"""unit:對話檢索召回/穩定性修正(retrieval-fixes #1 keyword fallback、#4 b2c None vendor)。

- #1 base_retriever:keyword fallback 觸發條件應以「通過 threshold 的候選數」判斷,
  而非過濾前原始候選數(_vector_search 不卡門檻、固定回 ~20 筆,用原始數會讓 fallback 形同虛設)。
- #4 vendor_knowledge_retriever_v2:b2c 遇 get_vendor_info()→None 不得崩潰(AttributeError),降級為空業態。

全程 mock IO 邊界,不碰真實 DB → 確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.base_retriever import BaseRetriever
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit


# ─────────────────────────── #1 keyword fallback ───────────────────────────

class _PipelineStub(BaseRetriever):
    async def _vector_search(self, *a, **k):
        return []

    async def _keyword_search(self, *a, **k):
        return []

    def _format_result(self, row):
        return row


@pytest.fixture
def retriever():
    r = _PipelineStub()
    r.query_rewriter = None
    r.semantic_reranker = None
    r._get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return r


@pytest.mark.req("retrieval-fixes:1")
async def test_keyword_fallback_fires_when_relevant_below_top_k(retriever):
    """6 筆候選但僅 1 筆達 threshold → fallback 必觸發,補位量=top_k−達標數(而非 top_k−原始數)。"""
    retriever._vector_search = AsyncMock(return_value=[
        {"id": 1, "vector_similarity": 0.90},   # 達標
        {"id": 2, "vector_similarity": 0.50},
        {"id": 3, "vector_similarity": 0.40},
        {"id": 4, "vector_similarity": 0.30},
        {"id": 5, "vector_similarity": 0.20},
        {"id": 6, "vector_similarity": 0.10},
    ])
    retriever._keyword_search = AsyncMock(return_value=[{"id": 7, "keyword_score": 0.9}])

    await retriever.retrieve("q", 1, top_k=3, similarity_threshold=0.6,
                             enable_keyword_fallback=True, enable_keyword_boost=False)

    retriever._keyword_search.assert_awaited_once()
    # 達標僅 id1(≥0.6)→ 補位量 = top_k(3) − 達標(1) = 2(舊碼會用 6 筆原始數 → 不觸發)
    assert retriever._keyword_search.await_args.args[2] == 2


@pytest.mark.req("retrieval-fixes:1")
async def test_keyword_fallback_skipped_when_enough_relevant(retriever):
    """達標數已 >= top_k → 不啟動 fallback(避免無謂補位)。"""
    retriever._vector_search = AsyncMock(return_value=[
        {"id": 1, "vector_similarity": 0.90},
        {"id": 2, "vector_similarity": 0.85},
        {"id": 3, "vector_similarity": 0.80},
        {"id": 4, "vector_similarity": 0.10},
    ])
    retriever._keyword_search = AsyncMock(return_value=[{"id": 9, "keyword_score": 0.9}])

    await retriever.retrieve("q", 1, top_k=3, similarity_threshold=0.6,
                             enable_keyword_fallback=True, enable_keyword_boost=False)

    retriever._keyword_search.assert_not_awaited()


# ─────────────────────────── #4 b2c None vendor ───────────────────────────

class _CaptureCursor:
    def __init__(self, store):
        self.store = store

    def execute(self, sql, params=None):
        self.store["sql"] = sql
        self.store["params"] = params

    def fetchall(self):
        return []

    def close(self):
        pass


class _CaptureConn:
    def __init__(self, store):
        self.store = store

    def cursor(self, *a, **k):
        return _CaptureCursor(self.store)

    def close(self):
        pass


def _retriever_with_none_vendor(store):
    r = object.__new__(VendorKnowledgeRetrieverV2)
    r._get_db_connection = lambda: _CaptureConn(store)
    pr = MagicMock()
    pr.get_vendor_info.return_value = None  # 查無業者 → None
    r.param_resolver = pr
    return r


@pytest.mark.req("retrieval-fixes:4")
async def test_b2c_vector_search_none_vendor_info_no_crash():
    """b2c 遇 get_vendor_info()→None:_vector_search 不得 AttributeError,降級為空業態、回 []。"""
    store = {}
    r = _retriever_with_none_vendor(store)
    out = await r._vector_search([0.1, 0.2], vendor_id=999, top_k=5,
                                 similarity_threshold=0.6, target_user="tenant", mode="b2c")
    assert out == []
    assert [] in store["params"], "business_types 參數應降級為空陣列"


@pytest.mark.req("retrieval-fixes:4")
async def test_b2c_keyword_search_none_vendor_info_no_crash():
    """b2c keyword 分支同樣不得因 None vendor_info 崩潰。"""
    store = {}
    r = _retriever_with_none_vendor(store)
    out = await r._keyword_search("租金", 999, 5, target_user="tenant", mode="b2c")
    assert out == []
    assert [] in store["params"], "business_types 參數應降級為空陣列"
