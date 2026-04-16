"""
單元測試：VendorKnowledgeRetrieverV2 分數欄位重構（task 3.1–3.3）

涵蓋驗收標準：
- 3.1：_vector_search SQL 移除 threshold、加 LIMIT 100、SQL alias 改 vector_similarity
- 3.2：_keyword_search 不再 cap、寫入 keyword_score；vector_similarity 預設 0.0
- 3.3：_format_result 含所有新欄位（vector_similarity、keyword_score、keyword_boost、
       rerank_score、similarity、original_similarity）

對應規格：.kiro/specs/retriever-similarity-refactor/
"""
import sys
import os
import re
import inspect
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2


def _make_retriever_no_init():
    r = VendorKnowledgeRetrieverV2.__new__(VendorKnowledgeRetrieverV2)
    r.semantic_reranker = None
    r.reranker = None
    r.param_resolver = None
    return r


# ════════════════════════════════════════════════
# Task 3.3: _format_result 包含所有新欄位
# ════════════════════════════════════════════════

def test_format_result_vector_path_reads_vector_similarity_column():
    r = _make_retriever_no_init()
    row = {
        'id': 1, 'question_summary': 'Q', 'answer': 'A',
        'vector_similarity': 0.78, 'keywords': ['退租'],
    }
    result = r._format_result(row)
    assert result['vector_similarity'] == 0.78


def test_format_result_keyword_path_default_vector_similarity_zero():
    r = _make_retriever_no_init()
    row = {'id': 1, 'question_summary': 'Q', 'answer': 'A', 'keywords': []}
    result = r._format_result(row)
    assert result['vector_similarity'] == 0.0


def test_format_result_default_keyword_score_is_none():
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'question_summary': 'Q', 'answer': 'A'})
    assert result['keyword_score'] is None


def test_format_result_default_rerank_score_is_none():
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'question_summary': 'Q', 'answer': 'A'})
    assert result['rerank_score'] is None


def test_format_result_default_keyword_boost_is_one():
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'question_summary': 'Q', 'answer': 'A'})
    assert result['keyword_boost'] == 1.0


def test_format_result_similarity_starts_as_vector_similarity():
    r = _make_retriever_no_init()
    row = {'id': 1, 'question_summary': 'Q', 'answer': 'A', 'vector_similarity': 0.65}
    result = r._format_result(row)
    assert result['similarity'] == 0.65


def test_format_result_original_similarity_alias_of_vector_similarity():
    r = _make_retriever_no_init()
    row = {'id': 1, 'question_summary': 'Q', 'answer': 'A', 'vector_similarity': 0.55}
    result = r._format_result(row)
    assert result['original_similarity'] == 0.55


def test_format_result_preserves_existing_kb_metadata():
    """KB 特有欄位（question_summary, answer, scope, video_url 等）正確傳遞"""
    r = _make_retriever_no_init()
    row = {
        'id': 99, 'question_summary': '退租 Q', 'answer': '退租流程說明',
        'scope': 'vendor_knowledge', 'priority': 5,
        'vendor_ids': [2], 'business_types': ['system_provider'],
        'target_user': ['tenant'], 'keywords': ['退租'],
        'video_url': 'https://...', 'form_id': None, 'action_type': None,
        'api_config': None, 'intent_id': None,
        'vector_similarity': 0.7,
    }
    result = r._format_result(row)
    assert result['id'] == 99
    assert result['question_summary'] == '退租 Q'
    assert result['answer'] == '退租流程說明'
    assert result['scope'] == 'vendor_knowledge'
    assert result['priority'] == 5
    assert result['video_url'] == 'https://...'


# ════════════════════════════════════════════════
# Task 3.1: _vector_search SQL 結構驗證
# ════════════════════════════════════════════════

def _get_vector_search_source() -> str:
    return inspect.getsource(VendorKnowledgeRetrieverV2._vector_search)


def test_vector_search_sql_renames_similarity_to_vector_similarity():
    """task 3.1: SELECT 應用 `as vector_similarity` 別名"""
    src = _get_vector_search_source()
    sql_match = re.search(r'sql_query\s*=\s*f?"""(.*?)"""', src, re.DOTALL)
    assert sql_match, "找不到 sql_query SQL 字串"
    sql = sql_match.group(1)
    assert re.search(r'\bas\s+vector_similarity\b', sql), \
        "SQL SELECT 應有 `as vector_similarity` 別名"
    assert not re.search(r'\)\s+as\s+similarity\b', sql), \
        "不應再使用 `) as similarity` 別名"


def test_vector_search_sql_removes_threshold_where_clause():
    """task 3.1: SQL WHERE 不應再有 `>= %s` threshold 過濾"""
    src = _get_vector_search_source()
    sql_match = re.search(r'sql_query\s*=\s*f?"""(.*?)"""', src, re.DOTALL)
    assert sql_match, "找不到 sql_query SQL 字串"
    sql = sql_match.group(1)
    where_match = re.search(r'\bWHERE\b(.*?)\bORDER BY\b', sql, re.DOTALL)
    assert where_match, "SQL 應仍有 WHERE 與 ORDER BY"
    where_clause = where_match.group(1)
    assert '>=' not in where_clause, \
        f"WHERE 不應含 `>=` threshold 過濾，實際: {where_clause!r}"


def test_vector_search_sql_still_computes_cosine_similarity():
    """task 3.1: SQL 仍須計算 cosine similarity"""
    src = _get_vector_search_source()
    assert 'embedding <=>' in src or 'embedding<=>' in src.replace(' ', ''), \
        "SQL 應保留 embedding cosine 計算"


def test_vector_search_uses_limit_100_default():
    """task 3.1: KB SQL LIMIT 預設應為 100（資料量較大）"""
    src = _get_vector_search_source()
    has_default = (
        "vector_limit, 100" in src
        or "vector_limit\", 100" in src
        or "'vector_limit', 100" in src
        or 'vector_limit", 100' in src
    )
    has_literal = bool(re.search(r"\bLIMIT\s+100\b", src))
    assert has_default or has_literal, \
        f"應有 LIMIT 100（字面值或預設參數），原始碼:\n{src}"


# ════════════════════════════════════════════════
# Task 3.2: _keyword_search 寫入 keyword_score
# ════════════════════════════════════════════════

def _get_keyword_search_source() -> str:
    return inspect.getsource(VendorKnowledgeRetrieverV2._keyword_search)


def test_keyword_search_no_similarity_assignment():
    """task 3.2: 不應再把 normalized_score 寫到 result['similarity']"""
    src = _get_keyword_search_source()
    src_no_comments = re.sub(r'#.*$', '', src, flags=re.MULTILINE)
    # 確認不再有 result['similarity'] = normalized_score
    assert "result['similarity'] = normalized_score" not in src_no_comments, \
        "_keyword_search 不應再把 normalized_score 寫入 similarity"


def _run_keyword_search(retriever, mock_rows, query='退租'):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = mock_rows
    mock_cursor.execute.return_value = None
    mock_cursor.close.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.close.return_value = None
    with patch.object(retriever, '_get_db_connection', return_value=mock_conn):
        return asyncio.run(retriever._keyword_search(query, vendor_id=1, limit=10))


def _make_kb_row(**overrides):
    """KB row 預設模板"""
    base = {
        'id': 1, 'question_summary': 'Q', 'answer': 'A', 'scope': 'vendor_knowledge',
        'priority': 0, 'vendor_ids': [1], 'business_types': None,
        'target_user': None, 'keywords': ['退租'],
        'video_url': None, 'form_id': None, 'action_type': None,
        'api_config': None, 'intent_id': None,
    }
    base.update(overrides)
    return base


def test_keyword_search_writes_keyword_score_field():
    """task 3.2: keyword 命中項目須有 keyword_score"""
    r = _make_retriever_no_init()
    out = _run_keyword_search(r, [_make_kb_row()], query='退租')
    assert len(out) >= 1
    assert 'keyword_score' in out[0]
    assert out[0]['keyword_score'] is not None


def test_keyword_search_vector_similarity_defaults_zero():
    """task 3.2: vector_similarity 預設 0.0"""
    r = _make_retriever_no_init()
    out = _run_keyword_search(r, [_make_kb_row()], query='退租')
    assert out[0]['vector_similarity'] == 0.0


def test_keyword_search_keeps_search_method_keyword():
    """task 3.2: search_method 仍為 'keyword'"""
    r = _make_retriever_no_init()
    out = _run_keyword_search(r, [_make_kb_row()], query='退租')
    assert out[0]['search_method'] == 'keyword'


def test_keyword_search_preserves_keyword_matches():
    """task 3.2: keyword_matches 紀錄命中關鍵字"""
    r = _make_retriever_no_init()
    out = _run_keyword_search(r, [_make_kb_row(keywords=['退租', '解約'])], query='退租')
    assert '退租' in out[0]['keyword_matches']


# ────────────────────────────────────────────────
if __name__ == '__main__':
    tests = [v for k, v in globals().items() if k.startswith('test_') and callable(v)]
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
