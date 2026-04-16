"""
單元測試：services/retrieval_types.py

驗證 RetrievalResult TypedDict 與 make_default_result() 工廠函式。

對應任務：retriever-similarity-refactor task 1.1
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.retrieval_types import RetrievalResult, make_default_result


def test_make_default_result_returns_dict():
    """工廠函式必須回傳 dict（TypedDict 在 runtime 即 dict）"""
    result = make_default_result()
    assert isinstance(result, dict), "回傳值必須是 dict"


def test_make_default_result_has_all_score_fields():
    """預設結果必須包含所有分數欄位"""
    result = make_default_result()
    expected_fields = {
        'vector_similarity',
        'keyword_score',
        'keyword_boost',
        'rerank_score',
        'similarity',
        'score_source',
        'original_similarity',
    }
    missing = expected_fields - set(result.keys())
    assert not missing, f"缺少必要欄位: {missing}"


def test_make_default_result_default_values():
    """預設值應符合設計規範"""
    result = make_default_result()
    # vector_similarity 預設 0.0（無向量結果）
    assert result['vector_similarity'] == 0.0
    # keyword_score 預設 None（未走 keyword）
    assert result['keyword_score'] is None
    # keyword_boost 預設 1.0（未套用 boost）
    assert result['keyword_boost'] == 1.0
    # rerank_score 預設 None（未經 rerank）
    assert result['rerank_score'] is None
    # similarity 預設 0.0（待 _finalize_scores 重算）
    assert result['similarity'] == 0.0
    # score_source 預設為 vector
    assert result['score_source'] == 'vector'
    # original_similarity 為 vector_similarity 的 alias
    assert result['original_similarity'] == 0.0


def test_make_default_result_has_metadata_fields():
    """預設結果應包含必要的 metadata 欄位（即使為空）"""
    result = make_default_result()
    # keyword_matches 預設空 list
    assert result.get('keyword_matches') == []


def test_make_default_result_independent_instances():
    """多次呼叫應回傳獨立 dict（不共享 mutable state）"""
    r1 = make_default_result()
    r2 = make_default_result()
    r1['vector_similarity'] = 0.5
    r1['keyword_matches'].append('test')
    assert r2['vector_similarity'] == 0.0, "r1 修改不應影響 r2"
    assert r2['keyword_matches'] == [], "r1 keyword_matches 修改不應影響 r2"


def test_retrieval_result_is_typed_dict():
    """RetrievalResult 必須是 TypedDict（runtime 為 dict 子型別）"""
    # TypedDict 在 runtime 仍是 dict，但需可被當作型別註解使用
    # 透過 __required_keys__ 或 __annotations__ 驗證 TypedDict 特性
    assert hasattr(RetrievalResult, '__annotations__'), "RetrievalResult 應有 __annotations__"
    annotations = RetrievalResult.__annotations__
    # 核心分數欄位必須在型別定義中
    for field in ['vector_similarity', 'keyword_score', 'keyword_boost',
                  'rerank_score', 'similarity', 'score_source']:
        assert field in annotations, f"RetrievalResult 型別應宣告 {field}"


if __name__ == '__main__':
    # 簡易執行入口（不依賴 pytest）
    tests = [
        test_make_default_result_returns_dict,
        test_make_default_result_has_all_score_fields,
        test_make_default_result_default_values,
        test_make_default_result_has_metadata_fields,
        test_make_default_result_independent_instances,
        test_retrieval_result_is_typed_dict,
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
