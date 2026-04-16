"""
單元測試：LLMAnswerOptimizer 的 perfect_match 判定欄位

驗證 optimize_answer 內的 perfect_match 判定改用 vector_similarity
（而非 original_similarity 或 similarity），避免含 boost/rerank 的分數
誤觸 perfect_match。

對應任務：retriever-similarity-refactor task 5.3
對應需求：requirements.md Requirement 5
"""
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


import services.llm_answer_optimizer as llm_mod  # noqa: E402
from services.llm_answer_optimizer import LLMAnswerOptimizer  # noqa: E402


def _make_optimizer(perfect_match_threshold=0.90, synthesis_threshold=0.80):
    """建立已繞過 LLM Provider 初始化的 LLMAnswerOptimizer 實例"""
    with patch.object(llm_mod, 'get_llm_provider', return_value=MagicMock()):
        opt = LLMAnswerOptimizer()
    # 覆寫關鍵閾值，避免環境變數干擾
    opt.config['perfect_match_threshold'] = perfect_match_threshold
    opt.config['synthesis_threshold'] = synthesis_threshold
    opt.config['enable_synthesis'] = True
    return opt


def test_perfect_match_uses_vector_similarity_not_composite():
    """
    high similarity 但低 vector_similarity → 不應被視為 perfect_match。

    舊行為：max(r.get('original_similarity', r['similarity'])) 會讀到 0.95 → 誤判 perfect_match
    新行為：max(r.get('vector_similarity', 0)) → 0.55 < 0.90 → 不是 perfect_match
    """
    opt = _make_optimizer(perfect_match_threshold=0.90, synthesis_threshold=0.80)

    # 兩筆 high_quality（similarity > 0.80），但 vector_similarity 都低
    search_results = [
        {
            'id': 1, 'item_name': 'A', 'content': 'ans-a',
            'similarity': 0.95,          # final score（含 rerank/boost）
            'vector_similarity': 0.55,   # 純向量分數（真實語義相似度）
        },
        {
            'id': 2, 'item_name': 'B', 'content': 'ans-b',
            'similarity': 0.92,
            'vector_similarity': 0.50,
        },
    ]

    result = opt.optimize_answer(
        question="流程如何？",
        search_results=search_results,
        confidence_level="high",
        intent_info={},
    )

    # perfect_match 不該觸發 → optimization_method 不能是 "perfect_match"
    assert result.get('optimization_method') != 'perfect_match', (
        f"perfect_match 不該被 composite similarity 觸發，"
        f"實際 optimization_method={result.get('optimization_method')}"
    )


def test_perfect_match_triggers_when_vector_similarity_above_threshold():
    """
    vector_similarity >= threshold → 應觸發 perfect_match，回傳 optimization_method='perfect_match'
    """
    opt = _make_optimizer(perfect_match_threshold=0.90, synthesis_threshold=0.80)

    search_results = [
        {
            'id': 1, 'item_name': 'A', 'content': 'ans-a',
            'similarity': 0.85,
            'vector_similarity': 0.95,   # >= threshold → perfect_match
        },
        {
            'id': 2, 'item_name': 'B', 'content': 'ans-b',
            'similarity': 0.82,
            'vector_similarity': 0.50,
        },
    ]

    result = opt.optimize_answer(
        question="你好嗎？",  # 避開 process_keywords / broad_keywords 強制合成
        search_results=search_results,
        confidence_level="high",
        intent_info={},
    )

    assert result.get('optimization_method') == 'perfect_match', (
        f"vector_similarity=0.95 >= 0.90 應觸發 perfect_match，"
        f"實際 optimization_method={result.get('optimization_method')}"
    )


def test_perfect_match_missing_vector_similarity_defaults_to_zero():
    """
    當結果不含 vector_similarity 欄位 → 預設為 0 → 不可能觸發 perfect_match
    （防止缺欄位時退回舊行為誤觸）
    """
    opt = _make_optimizer(perfect_match_threshold=0.90, synthesis_threshold=0.80)

    search_results = [
        {'id': 1, 'item_name': 'A', 'content': 'ans-a', 'similarity': 0.99},
        {'id': 2, 'item_name': 'B', 'content': 'ans-b', 'similarity': 0.95},
    ]

    result = opt.optimize_answer(
        question="你好嗎？",
        search_results=search_results,
        confidence_level="high",
        intent_info={},
    )

    assert result.get('optimization_method') != 'perfect_match', (
        f"缺 vector_similarity 時不該誤觸 perfect_match，"
        f"實際 optimization_method={result.get('optimization_method')}"
    )


if __name__ == '__main__':
    tests = [
        test_perfect_match_uses_vector_similarity_not_composite,
        test_perfect_match_triggers_when_vector_similarity_above_threshold,
        test_perfect_match_missing_vector_similarity_defaults_to_zero,
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
