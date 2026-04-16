"""
單元測試：chat_shared.has_sop_results

驗證 has_sop_results 改用 scope == 'vendor_sop' 判定，
不再依賴 similarity == 1.0。

對應任務：retriever-similarity-refactor task 5.2
對應需求：requirements.md Requirement 5
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routers.chat_shared import has_sop_results


def test_returns_true_when_any_result_has_vendor_sop_scope():
    """有任一筆 scope='vendor_sop' 就回傳 True"""
    results = [
        {'id': 1, 'scope': 'global', 'similarity': 0.9},
        {'id': 2, 'scope': 'vendor_sop', 'similarity': 0.5},  # 非 1.0 也要命中
    ]
    assert has_sop_results(results) is True


def test_returns_false_when_no_vendor_sop_scope():
    """全部皆非 vendor_sop → False"""
    results = [
        {'id': 1, 'scope': 'global', 'similarity': 1.0},
        {'id': 2, 'scope': 'vendor_kb', 'similarity': 0.9},
    ]
    assert has_sop_results(results) is False


def test_returns_false_on_empty_list():
    """空輸入 → False"""
    assert has_sop_results([]) is False


def test_does_not_depend_on_similarity_equals_one():
    """scope='vendor_sop' 但 similarity 遠低於 1.0 也要命中（回歸防護）"""
    results = [{'id': 1, 'scope': 'vendor_sop', 'similarity': 0.3}]
    assert has_sop_results(results) is True


def test_missing_scope_treated_as_non_sop():
    """沒有 scope 欄位 → 視為非 SOP"""
    results = [{'id': 1, 'similarity': 1.0}]
    assert has_sop_results(results) is False


if __name__ == '__main__':
    tests = [
        test_returns_true_when_any_result_has_vendor_sop_scope,
        test_returns_false_when_no_vendor_sop_scope,
        test_returns_false_on_empty_list,
        test_does_not_depend_on_similarity_equals_one,
        test_missing_scope_treated_as_non_sop,
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
