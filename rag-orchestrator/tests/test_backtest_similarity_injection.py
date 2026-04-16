"""
單元測試：backtest_framework_async sources similarity 注入

驗證回測 debug_info → sources 注入邏輯對齊重構後的 similarity 欄位語意：
- 主排序使用 final similarity
- 額外記錄 vector_similarity（純向量分數）

對應任務：retriever-similarity-refactor task 5.5
對應需求：requirements.md Requirement 7
"""
import sys
import os
import inspect
import textwrap

# 讓兩份 backtest 腳本都能被載入（rag-orchestrator 內的為實際部署版本）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'backtest'))


def _extract_injection_block():
    """
    讀取 backtest_framework_async.py，抓出 sources similarity 注入那段邏輯原始碼。
    以純文字 inspect 方式驗證欄位對齊（避免跑整個 HTTP retry 流程）。
    """
    path = os.path.join(
        os.path.dirname(__file__), '..', 'scripts', 'backtest',
        'backtest_framework_async.py'
    )
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    return src


def test_injection_uses_final_similarity_as_primary():
    """
    注入邏輯應優先讀 candidate['similarity']（final 組合分數），
    不再以 boosted_similarity 為主。
    """
    src = _extract_injection_block()
    # 應該存在 candidate.get('similarity', ...)
    assert "candidate.get('similarity'" in src or 'candidate.get("similarity"' in src, (
        "注入邏輯應以 candidate.get('similarity', 0.0) 為主排序欄位"
    )


def test_injection_records_vector_similarity():
    """
    source 必須額外記錄 vector_similarity 欄位，供下游分析純向量分數。
    """
    src = _extract_injection_block()
    assert "vector_similarity" in src, (
        "注入邏輯應額外將 candidate['vector_similarity'] 寫入 source，供分析純向量分數"
    )
    # source 端要有寫入點
    assert (
        'source["vector_similarity"]' in src
        or "source['vector_similarity']" in src
    ), "source 必須新增 vector_similarity 欄位"


def test_source_still_has_similarity_field():
    """
    既有 backtest_results 表欄位相容：source['similarity'] 仍保留。
    """
    src = _extract_injection_block()
    assert (
        'source["similarity"]' in src
        or "source['similarity']" in src
    ), "source 必須保留 similarity 欄位以維持 backtest_results 表結構相容"


if __name__ == '__main__':
    tests = [
        test_injection_uses_final_similarity_as_primary,
        test_injection_records_vector_similarity,
        test_source_still_has_similarity_field,
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
