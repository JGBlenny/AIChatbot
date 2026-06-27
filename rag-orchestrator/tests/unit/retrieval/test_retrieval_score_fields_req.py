"""補測試：檢索 pipeline／reranker（spec testing-traceability・任務 7・R5.3）。

聚焦 _finalize_scores 的三分支分數欄位語意與保留分類常數（純函式 → unit）：
- rerank / keyword / vector 三分支 similarity 公式與 score_source
- 只寫 similarity/score_source，不汙染既有分數欄位
- NULL-safe（vector_similarity 為 None 時當 0.0）
- 保留分類（系統脈絡／對話規則）常數存在，供排除於檢索
"""
import pytest

from services.base_retriever import BaseRetriever
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit


def _finalize(results):
    # _finalize_scores 不使用 self → 以 unbound 方式呼叫，免實例化（避免 reranker 連線副作用）
    return BaseRetriever._finalize_scores(None, results)


@pytest.mark.req("testing-traceability:5.3")
def test_rerank_branch_formula_and_source():
    r = _finalize([{"vector_similarity": 0.8, "rerank_score": 0.5}])[0]
    assert r["score_source"] == "rerank"
    assert r["similarity"] == pytest.approx(0.1 * 0.8 + 0.9 * 0.5)


@pytest.mark.req("testing-traceability:5.3")
def test_keyword_branch_formula_and_source():
    r = _finalize([{"vector_similarity": 0.4, "keyword_score": 0.6, "keyword_boost": 1.2}])[0]
    assert r["score_source"] == "keyword"
    assert r["similarity"] == pytest.approx(min(1.0, max(0.4, 0.6) * 1.2))


@pytest.mark.req("testing-traceability:5.3")
def test_vector_branch_formula_and_source():
    r = _finalize([{"vector_similarity": 0.7, "keyword_boost": 1.0}])[0]
    assert r["score_source"] == "vector"
    assert r["similarity"] == pytest.approx(0.7)


@pytest.mark.req("testing-traceability:5.3")
def test_similarity_capped_at_one():
    r = _finalize([{"vector_similarity": 0.95, "keyword_score": 0.95, "keyword_boost": 2.0}])[0]
    assert r["similarity"] == 1.0


@pytest.mark.req("testing-traceability:5.3")
def test_finalize_does_not_mutate_source_score_fields():
    src = {"vector_similarity": 0.4, "keyword_score": 0.6, "keyword_boost": 1.2, "rerank_score": 0.5}
    r = _finalize([dict(src)])[0]
    for field in ("vector_similarity", "keyword_score", "keyword_boost", "rerank_score"):
        assert r[field] == src[field]


@pytest.mark.req("testing-traceability:5.3")
def test_finalize_is_null_safe_on_missing_vector():
    r = _finalize([{"vector_similarity": None}])[0]
    assert r["score_source"] == "vector"
    assert r["similarity"] == 0.0


@pytest.mark.req("testing-traceability:5.3")
def test_reserved_categories_defined_for_exclusion():
    """保留分類（系統脈絡／對話規則）常數存在 → 排除於檢索，永不被當答案。"""
    assert VendorKnowledgeRetrieverV2.SYSTEM_DOC_CATEGORY == "系統脈絡"
    assert VendorKnowledgeRetrieverV2.RULES_DOC_CATEGORY == "對話規則"


@pytest.mark.req("testing-traceability:5.3")
def test_known_target_users_include_prospect():
    """target_user 路由：prospect 與業者角色皆為可信角色（區分售前/業者）。"""
    known = VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS
    assert "prospect" in known
    assert {"tenant", "landlord", "property_manager"} <= known
