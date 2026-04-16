"""
單元測試：VendorSOPRetrieverV2 分數欄位重構（task 2.1–2.4）

涵蓋驗收標準：
- 2.1：_vector_search SQL 移除 threshold 過濾、加 LIMIT 50（可覆寫）、保留 GREATEST 計算
- 2.2：SQL `as similarity` 改名 `as vector_similarity`，_format_result 從 vector_similarity 取
- 2.3：_keyword_search 不再 cap 0.70，寫入 keyword_score；vector_similarity 預設 0.0
- 2.4：_format_result 含所有新欄位（vector_similarity、keyword_score、keyword_boost、
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

from services.vendor_sop_retriever_v2 import VendorSOPRetrieverV2


# ────────────────────────────────────────────────
# 共用 fixture
# ────────────────────────────────────────────────

def _make_retriever_no_init():
    """繞過 __init__（避免 DB / embedding 依賴）"""
    r = VendorSOPRetrieverV2.__new__(VendorSOPRetrieverV2)
    r.semantic_reranker = None
    r.reranker = None
    r.sop_similarity_threshold = 0.75
    return r


# ════════════════════════════════════════════════
# Task 2.4: _format_result 包含所有新欄位
# ════════════════════════════════════════════════

def test_format_result_vector_path_reads_vector_similarity_column():
    """vector path：row['vector_similarity'] 應被讀入 result['vector_similarity']"""
    r = _make_retriever_no_init()
    row = {
        'id': 1, 'item_name': '測試 SOP', 'content': '...',
        'vector_similarity': 0.83,  # 由 SQL 算出
        'keywords': ['退租'],
    }
    result = r._format_result(row)
    assert result['vector_similarity'] == 0.83


def test_format_result_keyword_path_default_vector_similarity_zero():
    """keyword path（row 無 vector_similarity）：vector_similarity 預設為 0.0"""
    r = _make_retriever_no_init()
    row = {'id': 1, 'item_name': 'X', 'content': '...', 'keywords': []}
    result = r._format_result(row)
    assert result['vector_similarity'] == 0.0


def test_format_result_default_keyword_score_is_none():
    """keyword_score 預設 None（由 _keyword_search 設定）"""
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'item_name': 'X', 'content': ''})
    assert result['keyword_score'] is None


def test_format_result_default_rerank_score_is_none():
    """rerank_score 預設 None（由 _apply_semantic_reranker 設定）"""
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'item_name': 'X', 'content': ''})
    assert result['rerank_score'] is None


def test_format_result_default_keyword_boost_is_one():
    """keyword_boost 預設 1.0（由 _apply_keyword_boost 設定）"""
    r = _make_retriever_no_init()
    result = r._format_result({'id': 1, 'item_name': 'X', 'content': ''})
    assert result['keyword_boost'] == 1.0


def test_format_result_similarity_starts_as_vector_similarity():
    """similarity 暫時 = vector_similarity（待 _finalize_scores 重算）"""
    r = _make_retriever_no_init()
    row = {'id': 1, 'item_name': 'X', 'content': '', 'vector_similarity': 0.62}
    result = r._format_result(row)
    assert result['similarity'] == 0.62


def test_format_result_original_similarity_alias_of_vector_similarity():
    """original_similarity 為 vector_similarity 的向後相容 alias"""
    r = _make_retriever_no_init()
    row = {'id': 1, 'item_name': 'X', 'content': '', 'vector_similarity': 0.55}
    result = r._format_result(row)
    assert result['original_similarity'] == 0.55


def test_format_result_preserves_search_method():
    """search_method 預設 'vector'，可被 row 覆寫為 'keyword' / 'keyword_fallback'"""
    r = _make_retriever_no_init()
    assert r._format_result({'id': 1, 'item_name': '', 'content': ''})['search_method'] == 'vector'
    assert r._format_result({
        'id': 2, 'item_name': '', 'content': '', 'search_method': 'keyword'
    })['search_method'] == 'keyword'


def test_format_result_preserves_existing_metadata():
    """既有欄位（item_name, category_name, priority 等）仍正確傳遞"""
    r = _make_retriever_no_init()
    row = {
        'id': 42, 'item_name': '退租', 'content': '...',
        'category_name': '租賃', 'group_name': '退租流程',
        'priority': 5, 'keywords': ['退租', '解約'],
        'trigger_mode': 'auto', 'next_action': 'form',
        'vector_similarity': 0.7,
    }
    result = r._format_result(row)
    assert result['id'] == 42
    assert result['item_name'] == '退租'
    assert result['category_name'] == '租賃'
    assert result['priority'] == 5
    assert result['keywords'] == ['退租', '解約']


# ════════════════════════════════════════════════
# Task 2.1 & 2.2: _vector_search SQL 結構驗證
# ════════════════════════════════════════════════

def _get_vector_search_source() -> str:
    """取得 _vector_search 方法原始碼（含 SQL 字串）"""
    return inspect.getsource(VendorSOPRetrieverV2._vector_search)


def test_vector_search_sql_renames_similarity_to_vector_similarity():
    """task 2.2: SELECT clause 必須用 `as vector_similarity`"""
    src = _get_vector_search_source()
    assert re.search(r'\bas\s+vector_similarity\b', src), \
        "SELECT 應有 `as vector_similarity` 別名"
    # 不應再有作為主分數別名的 `as similarity`（intent_boost 不算）
    # 用更嚴謹的判定：不應出現 `) as similarity\b`
    assert not re.search(r'\)\s+as\s+similarity\b', src), \
        "不應再使用 `) as similarity` 別名（應改為 vector_similarity）"


def test_vector_search_sql_removes_threshold_where_clause():
    """task 2.1: SQL WHERE 不應再有 `>= %s` 的 GREATEST threshold 條件"""
    src = _get_vector_search_source()
    # 抓取三引號 SQL 字串（避開 docstring 與註解誤匹配）
    sql_match = re.search(r'cursor\.execute\(\s*"""(.*?)"""', src, re.DOTALL)
    assert sql_match, "找不到 cursor.execute 的 SQL 字串"
    sql = sql_match.group(1)
    # SQL 中找 WHERE...ORDER BY 區段
    where_match = re.search(r'\bWHERE\b(.*?)\bORDER BY\b', sql, re.DOTALL)
    assert where_match, "SQL 應仍有 WHERE 與 ORDER BY"
    where_clause = where_match.group(1)
    assert '>=' not in where_clause, \
        f"WHERE 子句不應含 `>=` threshold 過濾，實際: {where_clause!r}"


def test_vector_search_sql_still_computes_greatest_for_vector_similarity():
    """task 2.1: SQL 仍須計算 GREATEST(primary, fallback) 作為 vector_similarity"""
    src = _get_vector_search_source()
    assert 'GREATEST' in src, "SQL 應保留 GREATEST(primary, fallback) 計算"
    assert 'primary_embedding' in src and 'fallback_embedding' in src


def test_vector_search_uses_limit_50_default():
    """task 2.1: SQL LIMIT 預設應為 50"""
    src = _get_vector_search_source()
    # 接受 `LIMIT 50` 字面常數，或變數預設值 50
    has_literal = bool(re.search(r'\bLIMIT\s+50\b', src))
    has_default = bool(re.search(r"vector_limit['\"]?\s*[,=]\s*50", src)) \
        or 'vector_limit, 50' in src or 'vector_limit", 50' in src \
        or "'vector_limit', 50" in src
    assert has_literal or has_default, \
        f"應有 LIMIT 50（字面值或預設參數），原始碼:\n{src}"


# ════════════════════════════════════════════════
# Task 2.3: _keyword_search 寫入 keyword_score、不 cap 0.70
# ════════════════════════════════════════════════

def _get_keyword_search_source() -> str:
    return inspect.getsource(VendorSOPRetrieverV2._keyword_search)


def test_keyword_search_source_no_070_cap():
    """task 2.3: 程式碼不應再有 `min(0.70, ...)` 的 cap"""
    src = _get_keyword_search_source()
    # 移除註解後再檢查（中文註解可能提到 0.70）
    src_no_comments = re.sub(r'#.*$', '', src, flags=re.MULTILINE)
    assert not re.search(r'min\(\s*0\.70?\s*,', src_no_comments), \
        "_keyword_search 不應再有 min(0.70, ...) cap"


def _run_keyword_search(retriever, mock_rows, query='退租 流程'):
    """執行 _keyword_search 並用 mock 取代 DB 連線"""
    mock_cursor = MagicMock()
    # 第一次（精確配對）回傳 rows
    mock_cursor.fetchall.return_value = mock_rows
    mock_cursor.execute.return_value = None
    mock_cursor.close.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.close.return_value = None

    with patch.object(retriever, '_get_db_connection', return_value=mock_conn):
        return asyncio.run(retriever._keyword_search(query, vendor_id=1, limit=10))


def test_keyword_search_writes_keyword_score_field():
    """task 2.3: keyword 命中項目必須有 keyword_score 欄位"""
    r = _make_retriever_no_init()
    rows = [{
        'id': 1, 'item_name': '退租流程', 'content': '...',
        'keywords': ['退租', '退租 流程'],
        'category_id': 1, 'category_name': '', 'group_id': None, 'group_name': None,
        'item_number': 1, 'priority': 0, 'trigger_mode': None,
        'next_action': None, 'next_form_id': None, 'next_api_config': None,
        'trigger_keywords': None, 'immediate_prompt': None, 'followup_prompt': None,
        'intent_id': None, 'vendor_id': 1,
    }]
    out = _run_keyword_search(r, rows)
    assert len(out) >= 1
    assert 'keyword_score' in out[0], "keyword_search 結果應有 keyword_score 欄位"
    assert out[0]['keyword_score'] is not None


def test_keyword_search_keyword_score_not_capped_at_070():
    """task 2.3: keyword_score 可超過 0.70（之前的硬上限）"""
    r = _make_retriever_no_init()
    # 設計一個 query 與 keyword 完全相同的情況，normalized_score 應接近 1.0
    rows = [{
        'id': 1, 'item_name': '退租', 'content': '...',
        'keywords': ['退租'],
        'category_id': 1, 'category_name': '', 'group_id': None, 'group_name': None,
        'item_number': 1, 'priority': 0, 'trigger_mode': None,
        'next_action': None, 'next_form_id': None, 'next_api_config': None,
        'trigger_keywords': None, 'immediate_prompt': None, 'followup_prompt': None,
        'intent_id': None, 'vendor_id': 1,
    }]
    out = _run_keyword_search(r, rows, query='退租')
    assert len(out) >= 1
    # 完全配對下應 > 0.70，而不再被 cap
    assert out[0]['keyword_score'] > 0.70, \
        f"完全配對的 keyword_score 應 > 0.70，實際: {out[0]['keyword_score']}"


def test_keyword_search_vector_similarity_defaults_zero():
    """task 2.3: 純 keyword 命中項目，vector_similarity 預設為 0.0"""
    r = _make_retriever_no_init()
    rows = [{
        'id': 1, 'item_name': '退租', 'content': '...',
        'keywords': ['退租'],
        'category_id': 1, 'category_name': '', 'group_id': None, 'group_name': None,
        'item_number': 1, 'priority': 0, 'trigger_mode': None,
        'next_action': None, 'next_form_id': None, 'next_api_config': None,
        'trigger_keywords': None, 'immediate_prompt': None, 'followup_prompt': None,
        'intent_id': None, 'vendor_id': 1,
    }]
    out = _run_keyword_search(r, rows, query='退租')
    assert out[0]['vector_similarity'] == 0.0


def test_keyword_search_keeps_search_method_keyword():
    """task 2.3: search_method 仍為 'keyword'"""
    r = _make_retriever_no_init()
    rows = [{
        'id': 1, 'item_name': '退租', 'content': '...',
        'keywords': ['退租'],
        'category_id': 1, 'category_name': '', 'group_id': None, 'group_name': None,
        'item_number': 1, 'priority': 0, 'trigger_mode': None,
        'next_action': None, 'next_form_id': None, 'next_api_config': None,
        'trigger_keywords': None, 'immediate_prompt': None, 'followup_prompt': None,
        'intent_id': None, 'vendor_id': 1,
    }]
    out = _run_keyword_search(r, rows, query='退租')
    assert out[0]['search_method'] == 'keyword'


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
