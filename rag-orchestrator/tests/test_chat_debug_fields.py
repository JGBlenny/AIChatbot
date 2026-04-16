"""
單元測試：chat.py debug_info 分數欄位

驗證 chat.py 的 debug response 構建：
- base_similarity 改用 vector_similarity（純向量分數）
- 新增 score_source 欄位

對應任務：retriever-similarity-refactor task 5.1
對應需求：requirements.md Requirement 6
"""
import os
import re


def _read_chat_source():
    path = os.path.join(
        os.path.dirname(__file__), '..', 'routers', 'chat.py'
    )
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def test_base_similarity_not_read_from_old_similarity_field():
    """
    base_similarity 不應再直接從 'similarity' 或 'original_similarity' 讀取
    （這些在重構後分別是 final similarity / alias，不是純向量分數）。
    """
    src = _read_chat_source()

    # 這些舊 pattern 代表「從 final similarity 讀 base_similarity」— 必須移除
    bad_patterns = [
        r"'base_similarity':\s*[A-Za-z_][A-Za-z0-9_]*\.get\('similarity',",
        r'"base_similarity":\s*[A-Za-z_][A-Za-z0-9_]*\.get\("similarity",',
    ]
    for pat in bad_patterns:
        matches = re.findall(pat, src)
        assert not matches, (
            f"base_similarity 不應從 .get('similarity', ...) 讀取（應改用 vector_similarity），"
            f"但發現 {len(matches)} 處：{matches[:3]}"
        )


def test_base_similarity_reads_from_vector_similarity():
    """
    所有 base_similarity 欄位構建點都應優先讀 vector_similarity
    （至少要有幾處使用新欄位，代表已經切換）。
    """
    src = _read_chat_source()
    # 匹配 'base_similarity': X.get('vector_similarity', ...)
    matches = re.findall(
        r"'base_similarity':\s*[A-Za-z_][A-Za-z0-9_]*\.get\('vector_similarity'",
        src,
    )
    # chat.py 有多個 debug 構建點（task 說 ~10 處），切換後至少應有 > 5 處使用 vector_similarity
    assert len(matches) >= 5, (
        f"切換後 base_similarity 應從 vector_similarity 讀取，"
        f"實際只找到 {len(matches)} 處"
    )


def test_debug_dict_includes_score_source():
    """
    debug 字典應新增 score_source 欄位（值來自 retriever 的 score_source）。
    """
    src = _read_chat_source()
    matches = re.findall(r"'score_source'", src)
    assert len(matches) >= 5, (
        f"debug 字典應新增 score_source 欄位，"
        f"實際只找到 {len(matches)} 處"
    )


def test_pydantic_candidate_models_have_score_source_field():
    """
    CandidateSOP 與 CandidateKnowledge Pydantic 模型應有 score_source 欄位。
    """
    src = _read_chat_source()
    # Pydantic 定義區段
    # 簡單以 class 名 + score_source 欄位命中驗證
    assert re.search(
        r'class\s+CandidateSOP\b.*?score_source',
        src,
        flags=re.DOTALL,
    ), "CandidateSOP 應包含 score_source 欄位"
    assert re.search(
        r'class\s+CandidateKnowledge\b.*?score_source',
        src,
        flags=re.DOTALL,
    ), "CandidateKnowledge 應包含 score_source 欄位"


if __name__ == '__main__':
    tests = [
        test_base_similarity_not_read_from_old_similarity_field,
        test_base_similarity_reads_from_vector_similarity,
        test_debug_dict_includes_score_source,
        test_pydantic_candidate_models_have_score_source_field,
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
    import sys
    sys.exit(failed)
