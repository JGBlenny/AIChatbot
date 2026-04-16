"""
單元測試：BaseRetriever._finalize_scores

驗證 _finalize_scores 三分支公式（rerank → keyword → vector）正確性，
以及 score_source 標記與 log 輸出。

對應任務：retriever-similarity-refactor task 1.2
對應需求：requirements.md Requirement 4
對應設計：design.md 決策 4
"""
import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.base_retriever import BaseRetriever


class _StubRetriever(BaseRetriever):
    """測試用 stub：實作抽象方法但不實際執行 DB / embedding"""

    def __init__(self):
        # 跳過 BaseRetriever.__init__（避免依賴 DB / embedding 客戶端）
        self.semantic_reranker = None
        self.reranker = None

    async def _vector_search(self, *args, **kwargs):
        return []

    async def _keyword_search(self, *args, **kwargs):
        return []

    def _format_result(self, row):
        return row


def _capture_stdout(fn, *args, **kwargs):
    """捕捉 print 輸出供 log 驗證"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


# ─────────── 公式三分支驗證 ───────────

def test_rerank_branch_formula():
    """case 1：有 rerank_score → similarity = 0.1 × vector + 0.9 × rerank，score_source='rerank'"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.6,
        'keyword_score': 0.5,
        'keyword_boost': 1.2,  # boost 應被忽略（rerank 分支不套）
        'rerank_score': 0.9,
        'similarity': 0.0,
    }]
    out = retriever._finalize_scores(results)
    expected = 0.1 * 0.6 + 0.9 * 0.9  # = 0.87
    assert abs(out[0]['similarity'] - expected) < 1e-9, \
        f"預期 {expected}，實際 {out[0]['similarity']}"
    assert out[0]['score_source'] == 'rerank'


def test_keyword_branch_formula():
    """case 2：無 rerank、有 keyword → similarity = max(vector, keyword) × boost"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.4,
        'keyword_score': 0.8,
        'keyword_boost': 1.1,
        'rerank_score': None,
        'similarity': 0.0,
    }]
    out = retriever._finalize_scores(results)
    expected = max(0.4, 0.8) * 1.1  # = 0.88
    assert abs(out[0]['similarity'] - expected) < 1e-9, \
        f"預期 {expected}，實際 {out[0]['similarity']}"
    assert out[0]['score_source'] == 'keyword'


def test_vector_branch_formula():
    """case 3：純 vector → similarity = vector × boost，score_source='vector'"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.7,
        'keyword_score': None,
        'keyword_boost': 1.2,
        'rerank_score': None,
        'similarity': 0.0,
    }]
    out = retriever._finalize_scores(results)
    expected = 0.7 * 1.2  # = 0.84
    assert abs(out[0]['similarity'] - expected) < 1e-9
    assert out[0]['score_source'] == 'vector'


# ─────────── Edge cases ───────────

def test_keyword_branch_caps_at_1():
    """keyword 分支結果若超過 1.0，必須 cap 在 1.0"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.0,
        'keyword_score': 0.95,
        'keyword_boost': 1.3,  # 0.95 × 1.3 = 1.235 → cap 1.0
        'rerank_score': None,
        'similarity': 0.0,
    }]
    out = retriever._finalize_scores(results)
    assert out[0]['similarity'] == 1.0


def test_vector_branch_caps_at_1():
    """vector 分支結果若超過 1.0，必須 cap 在 1.0"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.9,
        'keyword_score': None,
        'keyword_boost': 1.5,  # 1.35 → cap
        'rerank_score': None,
        'similarity': 0.0,
    }]
    out = retriever._finalize_scores(results)
    assert out[0]['similarity'] == 1.0


def test_missing_keyword_boost_defaults_to_1():
    """缺少 keyword_boost 欄位時，視同 1.0（向後相容）"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.7,
        # keyword_boost 缺失
    }]
    out = retriever._finalize_scores(results)
    assert abs(out[0]['similarity'] - 0.7) < 1e-9
    assert out[0]['score_source'] == 'vector'


def test_empty_results_safe():
    """空輸入應安全返回空 list、不拋例外"""
    retriever = _StubRetriever()
    out = retriever._finalize_scores([])
    assert out == []


def test_does_not_mutate_pre_stage_fields():
    """_finalize_scores 只寫 similarity 與 score_source，不可動其他欄位"""
    retriever = _StubRetriever()
    results = [{
        'vector_similarity': 0.55,
        'keyword_score': 0.7,
        'keyword_boost': 1.1,
        'rerank_score': 0.8,
        'similarity': 0.0,
    }]
    retriever._finalize_scores(results)
    # 前階段欄位不變
    assert results[0]['vector_similarity'] == 0.55
    assert results[0]['keyword_score'] == 0.7
    assert results[0]['keyword_boost'] == 1.1
    assert results[0]['rerank_score'] == 0.8


# ─────────── 多筆混合與 log 驗證 ───────────

def test_mixed_branches_and_log_format():
    """log 必須輸出 [Finalize] 計算 N 筆，分數來源: rerank=X, keyword=Y, vector=Z"""
    retriever = _StubRetriever()
    results = [
        # 2 筆 rerank
        {'vector_similarity': 0.5, 'rerank_score': 0.9, 'keyword_boost': 1.0, 'keyword_score': None},
        {'vector_similarity': 0.6, 'rerank_score': 0.85, 'keyword_boost': 1.0, 'keyword_score': None},
        # 1 筆 keyword
        {'vector_similarity': 0.3, 'rerank_score': None, 'keyword_score': 0.7, 'keyword_boost': 1.1},
        # 3 筆 vector
        {'vector_similarity': 0.65, 'rerank_score': None, 'keyword_score': None, 'keyword_boost': 1.0},
        {'vector_similarity': 0.55, 'rerank_score': None, 'keyword_score': None, 'keyword_boost': 1.0},
        {'vector_similarity': 0.45, 'rerank_score': None, 'keyword_score': None, 'keyword_boost': 1.0},
    ]
    out, log_output = _capture_stdout(retriever._finalize_scores, results)

    # 分支歸類正確
    sources = [r['score_source'] for r in out]
    assert sources.count('rerank') == 2
    assert sources.count('keyword') == 1
    assert sources.count('vector') == 3

    # log 格式驗證
    assert '[Finalize]' in log_output, f"log 缺少 [Finalize] 標籤: {log_output!r}"
    assert '計算 6 筆' in log_output, f"log 應顯示總筆數 6: {log_output!r}"
    assert 'rerank=2' in log_output, f"log 應顯示 rerank=2: {log_output!r}"
    assert 'keyword=1' in log_output, f"log 應顯示 keyword=1: {log_output!r}"
    assert 'vector=3' in log_output, f"log 應顯示 vector=3: {log_output!r}"


if __name__ == '__main__':
    tests = [
        test_rerank_branch_formula,
        test_keyword_branch_formula,
        test_vector_branch_formula,
        test_keyword_branch_caps_at_1,
        test_vector_branch_caps_at_1,
        test_missing_keyword_boost_defaults_to_1,
        test_empty_results_safe,
        test_does_not_mutate_pre_stage_fields,
        test_mixed_branches_and_log_format,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✅ {t.__name__}")
        except AssertionError as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(failed)
