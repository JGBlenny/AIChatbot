"""
單元測試：LLMAnswerOptimizer._should_synthesize

驗證 _should_synthesize 使用 final similarity（r['similarity']）判定合成觸發，
而非 vector_similarity。

對應任務：retriever-similarity-refactor task 5.4
對應需求：requirements.md Requirement 5
"""
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.llm_answer_optimizer as llm_mod  # noqa: E402
from services.llm_answer_optimizer import LLMAnswerOptimizer  # noqa: E402


def _make_optimizer(synthesis_threshold=0.70, synthesis_min_results=2):
    with patch.object(llm_mod, 'get_llm_provider', return_value=MagicMock()):
        opt = LLMAnswerOptimizer()
    opt.config['synthesis_threshold'] = synthesis_threshold
    opt.config['synthesis_min_results'] = synthesis_min_results
    opt.config['enable_synthesis'] = True
    return opt


def test_should_synthesize_uses_final_similarity_not_vector():
    """
    high similarity（含 rerank/boost）、low vector_similarity：
    合成觸發應依 final similarity 計算 → similarity 0.95 > 0.70 → no_perfect_match=False → 不觸發合成
    """
    opt = _make_optimizer(synthesis_threshold=0.70)
    results = [
        {'similarity': 0.95, 'vector_similarity': 0.3},
        {'similarity': 0.90, 'vector_similarity': 0.2},
    ]
    # "流程" 觸發 complex_pattern；若此時 max_final=0.95 >= threshold → 不合成
    assert opt._should_synthesize("流程是什麼", results) is False


def test_should_synthesize_triggers_when_final_similarity_low():
    """
    final similarity 低於 threshold + complex_pattern → 應觸發合成
    """
    opt = _make_optimizer(synthesis_threshold=0.70)
    results = [
        {'similarity': 0.50, 'vector_similarity': 0.95},  # vector 高但 final 低
        {'similarity': 0.55, 'vector_similarity': 0.90},
    ]
    # max_final_similarity = 0.55 < 0.70 → 觸發
    assert opt._should_synthesize("流程是什麼", results) is True


def test_should_synthesize_no_complex_pattern():
    """
    無複合問題關鍵字 → 不觸發，不管分數多低
    """
    opt = _make_optimizer(synthesis_threshold=0.70)
    results = [
        {'similarity': 0.1, 'vector_similarity': 0.1},
        {'similarity': 0.1, 'vector_similarity': 0.1},
    ]
    assert opt._should_synthesize("你好", results) is False


if __name__ == '__main__':
    tests = [
        test_should_synthesize_uses_final_similarity_not_vector,
        test_should_synthesize_triggers_when_final_similarity_low,
        test_should_synthesize_no_complex_pattern,
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
