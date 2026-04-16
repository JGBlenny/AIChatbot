"""
單元測試：BaseRetriever pipeline 改造（task 4.1–4.3）

涵蓋驗收標準：
- 4.1：_apply_keyword_boost 只寫 keyword_boost / keyword_matches，不覆寫 vector_similarity / similarity
- 4.2：_apply_semantic_reranker 只寫 rerank_score，不覆寫其他分數欄位；保留 SOP→KB 欄位映射
- 4.3：retrieve() 末端呼叫 _finalize_scores 並依 final similarity 過濾 threshold，最終回傳 top_k

對應規格：.kiro/specs/retriever-similarity-refactor/
"""
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.base_retriever import BaseRetriever


class _StubRetriever(BaseRetriever):
    """測試用 stub：可注入 _vector_search / _keyword_search 結果"""

    def __init__(self, vector_results=None, keyword_results=None,
                 reranker=None, embedding=None):
        self.semantic_reranker = reranker
        self.reranker = None
        self.default_top_k = 5
        self.default_similarity_threshold = 0.6
        self.keyword_fallback_enabled = True
        self.keyword_boost_enabled = True
        self._vector_payload = vector_results or []
        self._keyword_payload = keyword_results or []
        self._embedding_payload = embedding or [0.1, 0.2, 0.3]

    async def _vector_search(self, query_embedding, vendor_id, top_k,
                             similarity_threshold, **kwargs):
        return list(self._vector_payload)

    async def _keyword_search(self, query, vendor_id, limit, **kwargs):
        return list(self._keyword_payload)

    def _format_result(self, row):
        return row

    async def _get_embedding(self, text):
        return self._embedding_payload


# ════════════════════════════════════════════════
# Task 4.1: _apply_keyword_boost 不覆寫前階段欄位
# ════════════════════════════════════════════════

def _make_result(**overrides):
    base = {
        'id': 1,
        'vector_similarity': 0.6,
        'keyword_score': None,
        'keyword_boost': 1.0,
        'rerank_score': None,
        'similarity': 0.6,
        'keywords': ['退租', '解約'],
        'keyword_matches': [],
    }
    base.update(overrides)
    return base


def test_keyword_boost_does_not_modify_vector_similarity():
    r = _StubRetriever()
    results = [_make_result(vector_similarity=0.55)]
    asyncio.run(r._apply_keyword_boost(results, '退租'))
    assert results[0]['vector_similarity'] == 0.55, \
        "_apply_keyword_boost 不應修改 vector_similarity"


def test_keyword_boost_does_not_modify_keyword_score():
    r = _StubRetriever()
    results = [_make_result(keyword_score=0.7)]
    asyncio.run(r._apply_keyword_boost(results, '退租'))
    assert results[0]['keyword_score'] == 0.7, \
        "_apply_keyword_boost 不應修改 keyword_score"


def test_keyword_boost_does_not_modify_similarity():
    """task 4.1: 不再寫 result['similarity']（由 _finalize_scores 算）"""
    r = _StubRetriever()
    results = [_make_result(similarity=0.6)]
    asyncio.run(r._apply_keyword_boost(results, '退租'))
    assert results[0]['similarity'] == 0.6, \
        "_apply_keyword_boost 不應覆寫 similarity"


def test_keyword_boost_writes_keyword_boost_as_multiplier():
    """task 4.1: keyword_boost 應寫入「倍率」（1 + boost），非 raw boost"""
    r = _StubRetriever()
    # 命中 2 個關鍵字 → boost = min(0.3, 0.2) = 0.2 → multiplier = 1.2
    results = [_make_result(keywords=['退租', '解約'])]
    asyncio.run(r._apply_keyword_boost(results, '退租 解約'))
    assert results[0]['keyword_boost'] > 1.0, \
        f"應有 boost 倍率 > 1.0，實際: {results[0]['keyword_boost']}"
    # 倍率介於 1.0–1.3
    assert 1.0 < results[0]['keyword_boost'] <= 1.3


def test_keyword_boost_writes_keyword_matches():
    """task 4.1: keyword_matches 必須記錄命中的關鍵字"""
    r = _StubRetriever()
    results = [_make_result(keywords=['退租', '解約'])]
    asyncio.run(r._apply_keyword_boost(results, '我想退租'))
    assert '退租' in results[0]['keyword_matches']


def test_keyword_boost_no_match_keeps_boost_one():
    """無命中時 keyword_boost 維持 1.0"""
    r = _StubRetriever()
    results = [_make_result(keywords=['退租'])]
    asyncio.run(r._apply_keyword_boost(results, '完全無關的查詢'))
    assert results[0]['keyword_boost'] == 1.0


# ════════════════════════════════════════════════
# Task 4.2: _apply_semantic_reranker 不覆寫前階段欄位
# ════════════════════════════════════════════════

def _make_mock_reranker(scores):
    """建立 mock semantic_reranker，rerank() 回傳含 semantic_score 的 candidates"""
    mock = MagicMock()
    mock.is_available = True

    def fake_rerank(query, candidates, top_k=None):
        out = []
        for i, c in enumerate(candidates):
            item = dict(c)
            item['semantic_score'] = scores[i] if i < len(scores) else 0.0
            out.append(item)
        return out

    mock.rerank.side_effect = fake_rerank
    return mock


def test_reranker_writes_rerank_score():
    """task 4.2: 必須寫入 rerank_score"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.95]))
    candidates = [_make_result(content='退租流程說明', item_name='退租')]
    out = r._apply_semantic_reranker('退租', candidates, top_k=5)
    assert out[0]['rerank_score'] == 0.95


def test_reranker_does_not_modify_vector_similarity():
    """task 4.2: 不可修改 vector_similarity"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.9]))
    candidates = [_make_result(vector_similarity=0.55, content='X', item_name='Y')]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)
    assert out[0]['vector_similarity'] == 0.55


def test_reranker_does_not_modify_keyword_score():
    """task 4.2: 不可修改 keyword_score"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.9]))
    candidates = [_make_result(keyword_score=0.8, content='X', item_name='Y')]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)
    assert out[0]['keyword_score'] == 0.8


def test_reranker_does_not_modify_keyword_boost():
    """task 4.2: 不可修改 keyword_boost"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.9]))
    candidates = [_make_result(keyword_boost=1.2, content='X', item_name='Y')]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)
    assert out[0]['keyword_boost'] == 1.2


def test_reranker_does_not_overwrite_original_similarity():
    """task 4.2: 不再寫 item['original_similarity']（由 _format_result 設定）"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.9]))
    candidates = [_make_result(
        vector_similarity=0.55, original_similarity=0.55,
        content='X', item_name='Y',
    )]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)
    # original_similarity 應保持 _format_result 設定的值（= vector_similarity）
    assert out[0]['original_similarity'] == 0.55, \
        "original_similarity 應保持 _format_result 的設定值"


def test_reranker_does_not_write_similarity():
    """task 4.2: 不再寫 item['similarity']（由 _finalize_scores 算）"""
    r = _StubRetriever(reranker=_make_mock_reranker([0.9]))
    candidates = [_make_result(similarity=0.55, content='X', item_name='Y')]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)
    # similarity 不應被 reranker 公式覆寫（即 0.1×0.55 + 0.9×0.9 = 0.865）
    assert abs(out[0]['similarity'] - 0.865) > 1e-6, \
        "_apply_semantic_reranker 不應覆寫 similarity"


# ════════════════════════════════════════════════
# Issue: reranker-returning-zero（防護：全 0 視為失敗）
# ════════════════════════════════════════════════

def test_reranker_all_zero_scores_falls_back_to_original_candidates():
    """
    .kiro/issues/reranker-returning-zero.md 暫行解法：
    若 reranker 回傳的所有項目 semantic_score 都是 0，視同失敗，
    不寫入 rerank_score，讓 _finalize_scores 走 vector / keyword 分支。
    """
    r = _StubRetriever(reranker=_make_mock_reranker([0.0, 0.0, 0.0]))
    candidates = [
        _make_result(id=1, vector_similarity=0.8, content='A', item_name='A-item'),
        _make_result(id=2, vector_similarity=0.6, content='B', item_name='B-item'),
        _make_result(id=3, vector_similarity=0.4, content='C', item_name='C-item'),
    ]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)

    # 所有項目 rerank_score 不應被寫成 0（應保持 None 讓 finalize 走 vector 分支）
    for item in out:
        assert item.get('rerank_score') is None, (
            f"reranker 全 0 應視為失敗，rerank_score 須保持 None，"
            f"實際: id={item.get('id')} rerank_score={item.get('rerank_score')}"
        )

    # 回傳筆數等於輸入（fallback 到原 candidates）
    assert len(out) == len(candidates), \
        f"fallback 時應回傳所有原 candidates，實際: {len(out)}"


def test_reranker_mixed_zero_and_nonzero_still_writes_scores():
    """
    只要有一項 semantic_score > 0，就視為 reranker 正常工作，全部寫入 rerank_score。
    （避免誤傷合理的低分候選，例如完全不相關的項目本來就該得 0）
    """
    r = _StubRetriever(reranker=_make_mock_reranker([0.9, 0.0, 0.0]))
    candidates = [
        _make_result(id=1, vector_similarity=0.8, content='A', item_name='A'),
        _make_result(id=2, vector_similarity=0.6, content='B', item_name='B'),
        _make_result(id=3, vector_similarity=0.4, content='C', item_name='C'),
    ]
    out = r._apply_semantic_reranker('q', candidates, top_k=5)

    # 正常情況應全部寫入 rerank_score（包含 0）
    scores_by_id = {item['id']: item.get('rerank_score') for item in out}
    assert scores_by_id[1] == 0.9
    assert scores_by_id[2] == 0.0
    assert scores_by_id[3] == 0.0


def test_reranker_empty_candidates_no_crash():
    """空 candidates 時，防護不應觸發 edge case"""
    r = _StubRetriever(reranker=_make_mock_reranker([]))
    out = r._apply_semantic_reranker('q', [], top_k=5)
    assert out == []


def test_reranker_preserves_sop_to_kb_field_mapping():
    """task 4.2 ⚠️: 必須保留 SOP→KB 欄位映射（content→answer、item_name→question_summary）"""
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def capture_rerank(query, candidates, top_k=None):
        # 記錄傳給 reranker 的 candidates
        captured['candidates'] = list(candidates)
        return [dict(c, semantic_score=0.9) for c in candidates]

    mock_reranker.rerank.side_effect = capture_rerank

    r = _StubRetriever(reranker=mock_reranker)
    # SOP 結構：有 content 與 item_name，但無 answer / question_summary
    sop_candidate = _make_result(
        content='退租流程詳細內容',
        item_name='退租 SOP',
    )
    sop_candidate.pop('answer', None)
    sop_candidate.pop('question_summary', None)

    r._apply_semantic_reranker('退租', [sop_candidate], top_k=5)

    # reranker 收到的 candidates 必須有 answer 與 question_summary
    sent = captured['candidates'][0]
    assert sent.get('answer') == '退租流程詳細內容', \
        "必須將 content 映射到 answer 供 reranker 使用"
    assert sent.get('question_summary') == '退租 SOP', \
        "必須將 item_name 映射到 question_summary 供 reranker 使用"


# ════════════════════════════════════════════════
# Task 4.3: retrieve() 末端呼叫 _finalize_scores + threshold 過濾
# ════════════════════════════════════════════════

def test_retrieve_calls_finalize_scores():
    """task 4.3: retrieve 必須呼叫 _finalize_scores"""
    r = _StubRetriever(
        vector_results=[_make_result(id=1, vector_similarity=0.8)],
    )
    with patch.object(r, '_finalize_scores', wraps=r._finalize_scores) as spy:
        asyncio.run(r.retrieve('q', vendor_id=1, top_k=5, similarity_threshold=0.0))
    assert spy.called, "retrieve 必須呼叫 _finalize_scores"


def test_retrieve_filters_by_final_similarity_threshold():
    """task 4.3: 套用 application 端 threshold 比對 final similarity"""
    r = _StubRetriever(
        vector_results=[
            _make_result(id=1, vector_similarity=0.9),  # final = 0.9 → 保留
            _make_result(id=2, vector_similarity=0.5),  # final = 0.5 → 過濾掉
            _make_result(id=3, vector_similarity=0.7),  # final = 0.7 → 保留
        ],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=10, similarity_threshold=0.65,
        enable_keyword_fallback=False,
    ))
    ids = [x['id'] for x in out]
    assert 1 in ids and 3 in ids, "≥0.65 的 SOP 應被保留"
    assert 2 not in ids, "<0.65 的 SOP 應被過濾"


def test_retrieve_returns_top_k_after_finalize():
    """task 4.3: 最終回傳 top_k 筆，依 final similarity 排序"""
    r = _StubRetriever(
        vector_results=[
            _make_result(id=i, vector_similarity=0.5 + i * 0.05)
            for i in range(10)
        ],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=3, similarity_threshold=0.0,
        enable_keyword_fallback=False,
    ))
    assert len(out) == 3, f"應回傳 top_k=3 筆，實際: {len(out)}"
    # 依 final similarity 由高至低
    sims = [x['similarity'] for x in out]
    assert sims == sorted(sims, reverse=True), "結果應依 final similarity 由高至低排序"


def test_retrieve_finalize_runs_before_threshold_filter():
    """task 4.3: finalize 後過濾，未 finalize 前的 similarity 不可作為過濾依據"""
    # 設計案例：vector=0.5，但 finalize 公式（無 rerank/keyword）= 0.5 × 1.0 = 0.5
    # threshold=0.5 應可保留（>=）
    r = _StubRetriever(
        vector_results=[_make_result(id=1, vector_similarity=0.5, similarity=0.0)],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=5, similarity_threshold=0.5,
        enable_keyword_fallback=False,
    ))
    assert len(out) == 1, \
        "_finalize_scores 應在 threshold 過濾之前重算 similarity（從 0 → 0.5）"
    assert out[0]['similarity'] == 0.5


# ════════════════════════════════════════════════
# Followup（選項 A）：return_unfiltered 旁路
# ════════════════════════════════════════════════

def test_retrieve_return_unfiltered_skips_threshold_filter():
    """followup-debug-visibility (選項 A):
    return_unfiltered=True 時，threshold 過濾器必須被跳過，低分候選保留在回傳值中。
    """
    r = _StubRetriever(
        vector_results=[
            _make_result(id=1, vector_similarity=0.9),  # final = 0.9
            _make_result(id=2, vector_similarity=0.3),  # final = 0.3（本該被 0.65 擋）
            _make_result(id=3, vector_similarity=0.1),  # final = 0.1（本該被 0.65 擋）
        ],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=10, similarity_threshold=0.65,
        enable_keyword_fallback=False,
        return_unfiltered=True,
    ))
    ids = {x['id'] for x in out}
    assert ids == {1, 2, 3}, \
        f"return_unfiltered=True 應保留所有候選（含低分），實際: {ids}"


def test_retrieve_default_behavior_still_filters():
    """return_unfiltered=False (預設) 時，threshold 過濾行為必須維持不變（回歸保護）"""
    r = _StubRetriever(
        vector_results=[
            _make_result(id=1, vector_similarity=0.9),
            _make_result(id=2, vector_similarity=0.3),  # 應被過濾
        ],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=10, similarity_threshold=0.65,
        enable_keyword_fallback=False,
    ))
    ids = {x['id'] for x in out}
    assert ids == {1}, f"預設行為：低分候選應被過濾掉，實際: {ids}"


# ════════════════════════════════════════════════
# Issue: reranker-returning-zero hotfix
# retrieve() 送進 reranker 前截斷候選數（避免超時）
# ════════════════════════════════════════════════

def test_retrieve_caps_candidates_sent_to_reranker():
    """
    hotfix: 送進 reranker 的 candidates 數量必須被 RERANKER_INPUT_LIMIT 限制。
    當候選超過上限，應依 vector_similarity 截斷，保留最高分的 N 筆。
    """
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['count'] = len(candidates)
        captured['ids'] = [c.get('id') for c in candidates]
        return [dict(c, semantic_score=0.9) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    r = _StubRetriever(
        reranker=mock_reranker,
        # 50 筆候選，vector_similarity 從 0.1 到 5.0 分布（id=1 最低、id=50 最高）
        vector_results=[
            _make_result(id=i, vector_similarity=0.1 * i)
            for i in range(1, 51)
        ],
    )

    # 設定限制為 20
    old = os.environ.get('RERANKER_INPUT_LIMIT')
    os.environ['RERANKER_INPUT_LIMIT'] = '20'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=5, similarity_threshold=0.0,
            enable_keyword_fallback=False,
        ))
    finally:
        if old is None:
            os.environ.pop('RERANKER_INPUT_LIMIT', None)
        else:
            os.environ['RERANKER_INPUT_LIMIT'] = old

    # reranker 收到的 candidate 數量必須 = 20
    assert captured['count'] == 20, (
        f"送進 reranker 的候選應被限制到 20，實際: {captured['count']}"
    )

    # 被保留的應是 vector_similarity 最高的 20 筆（id 31–50）
    kept_ids = set(captured['ids'])
    expected_kept = set(range(31, 51))
    assert kept_ids == expected_kept, (
        f"截斷時應保留 vector_similarity 最高的候選，預期 id {sorted(expected_kept)}，"
        f"實際 {sorted(kept_ids)}"
    )


def test_retrieve_truncation_preserves_keyword_fallback_items():
    """
    hotfix 嚴謹版：截斷時優先保留 keyword_fallback 命中項目，
    避免因為 vector_similarity=0.0（keyword 預設值）而被誤砍。

    情境：20 筆 vector（vec=0.1~2.0）+ 3 筆 keyword（vec=0，keyword_score=高）
    限制 20 → 應保留 3 筆 keyword + 17 筆最高分 vector
    """
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['ids'] = [c.get('id') for c in candidates]
        captured['search_methods'] = [c.get('search_method') for c in candidates]
        return [dict(c, semantic_score=0.5) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    # 20 筆 vector（id 1-20，vec 0.1~2.0）
    vector_results = [
        _make_result(id=i, vector_similarity=0.1 * i)
        for i in range(1, 21)
    ]
    # 3 筆 keyword fallback（id 100-102，vec=0，但有 keyword_score）
    keyword_results = [
        _make_result(id=100 + i, vector_similarity=0.0, keyword_score=0.8)
        for i in range(3)
    ]
    # 模擬 base_retriever 合併後的 search_method 標記
    for k in keyword_results:
        k['search_method'] = 'keyword_fallback'

    r = _StubRetriever(
        reranker=mock_reranker,
        vector_results=vector_results,
        keyword_results=keyword_results,
    )

    old = os.environ.get('RERANKER_INPUT_LIMIT')
    os.environ['RERANKER_INPUT_LIMIT'] = '20'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=23, similarity_threshold=0.0,
            enable_keyword_fallback=True,  # 啟用 keyword fallback
        ))
    finally:
        if old is None:
            os.environ.pop('RERANKER_INPUT_LIMIT', None)
        else:
            os.environ['RERANKER_INPUT_LIMIT'] = old

    kept_ids = set(captured['ids'])
    # 3 筆 keyword fallback 必須全數保留
    keyword_ids = {100, 101, 102}
    assert keyword_ids.issubset(kept_ids), (
        f"keyword_fallback 項目應全數保留，預期包含 {keyword_ids}，"
        f"實際 {sorted(kept_ids)}"
    )
    # 總數等於 limit（20）
    assert len(kept_ids) == 20, f"總數應為 20，實際: {len(kept_ids)}"
    # vector 項目應保留最高分的 17 筆（id 4-20），最低分 3 筆（id 1-3）被砍
    expected_vector_kept = set(range(4, 21))
    actual_vector_kept = kept_ids - keyword_ids
    assert actual_vector_kept == expected_vector_kept, (
        f"vector 項目應保留 vector_similarity 最高的 17 筆（id 4-20），"
        f"實際 {sorted(actual_vector_kept)}"
    )


def test_retrieve_truncation_keyword_items_do_not_exceed_limit():
    """極端情境：keyword 項目自身就超過 limit，全保留 keyword，vector 全砍"""
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['ids'] = [c.get('id') for c in candidates]
        return [dict(c, semantic_score=0.5) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    # 只有 1 筆 vector、22 筆 keyword（在現實中極罕見，但設計要安全）
    vector_results = [_make_result(id=1, vector_similarity=0.9)]
    keyword_results = [
        _make_result(id=100 + i, vector_similarity=0.0, keyword_score=0.8)
        for i in range(22)
    ]
    for k in keyword_results:
        k['search_method'] = 'keyword_fallback'

    r = _StubRetriever(
        reranker=mock_reranker,
        vector_results=vector_results,
        keyword_results=keyword_results,
    )

    old = os.environ.get('RERANKER_INPUT_LIMIT')
    os.environ['RERANKER_INPUT_LIMIT'] = '20'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=23, similarity_threshold=0.0,
            enable_keyword_fallback=True,
        ))
    finally:
        if old is None:
            os.environ.pop('RERANKER_INPUT_LIMIT', None)
        else:
            os.environ['RERANKER_INPUT_LIMIT'] = old

    # 當 keyword > limit 時，仍應回傳恰好 limit 筆（避免無限制暴衝 reranker）
    # vector 被砍（因為 keyword 已滿）
    assert len(captured['ids']) == 20, (
        f"keyword 過多時，總數仍應被 limit 限制，實際: {len(captured['ids'])}"
    )
    # vector 項（id=1）被砍
    assert 1 not in captured['ids'], \
        f"keyword 滿額時 vector 項應被砍，但 id=1 仍在結果中"


def test_retrieve_filters_low_vector_similarity_before_rerank():
    """
    hotfix: 送進 rerank 前過濾 vector_similarity < RERANKER_MIN_VECTOR_SIMILARITY 的項目。
    這些低分向量項目 rerank 後幾乎一定排不到 top_k，送進去只是浪費推論時間。
    """
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['ids'] = [c.get('id') for c in candidates]
        return [dict(c, semantic_score=0.5) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    # 10 筆候選，vector_similarity 從 0.05 到 0.95（間隔 0.1）
    r = _StubRetriever(
        reranker=mock_reranker,
        vector_results=[
            _make_result(id=i, vector_similarity=0.05 + 0.1 * (i - 1))
            for i in range(1, 11)  # id=1 → 0.05; id=10 → 0.95
        ],
    )

    old_min = os.environ.get('RERANKER_MIN_VECTOR_SIMILARITY')
    os.environ['RERANKER_MIN_VECTOR_SIMILARITY'] = '0.3'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=5, similarity_threshold=0.0,
            enable_keyword_fallback=False,
        ))
    finally:
        if old_min is None:
            os.environ.pop('RERANKER_MIN_VECTOR_SIMILARITY', None)
        else:
            os.environ['RERANKER_MIN_VECTOR_SIMILARITY'] = old_min

    # vector_similarity >= 0.3 的應保留（id 4–10，即 0.35 以上）
    # id=1 (0.05), id=2 (0.15), id=3 (0.25) 應被過濾
    kept_ids = set(captured['ids'])
    assert kept_ids == set(range(4, 11)), (
        f"應只送進 vector_similarity >= 0.3 的候選，實際: {sorted(kept_ids)}"
    )


def test_retrieve_min_vector_filter_does_not_drop_keyword_fallback():
    """
    下限過濾不應誤傷 keyword_fallback 項目（它們 vector_similarity=0.0 是設計預設值，
    不代表「低相關」，而是代表「走 keyword 路徑」）。
    """
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['ids'] = [c.get('id') for c in candidates]
        return [dict(c, semantic_score=0.5) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    # 1 筆 vector（低分，會被過濾）+ 3 筆 keyword（vec=0 但 keyword_score 高）
    vector_results = [_make_result(id=1, vector_similarity=0.1)]
    keyword_results = [
        _make_result(id=100 + i, vector_similarity=0.0, keyword_score=0.9)
        for i in range(3)
    ]
    for k in keyword_results:
        k['search_method'] = 'keyword_fallback'

    r = _StubRetriever(
        reranker=mock_reranker,
        vector_results=vector_results,
        keyword_results=keyword_results,
    )

    old_min = os.environ.get('RERANKER_MIN_VECTOR_SIMILARITY')
    os.environ['RERANKER_MIN_VECTOR_SIMILARITY'] = '0.3'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=5, similarity_threshold=0.0,
            enable_keyword_fallback=True,
        ))
    finally:
        if old_min is None:
            os.environ.pop('RERANKER_MIN_VECTOR_SIMILARITY', None)
        else:
            os.environ['RERANKER_MIN_VECTOR_SIMILARITY'] = old_min

    kept_ids = set(captured['ids'])
    # vector id=1（0.1 < 0.3）應被過濾
    assert 1 not in kept_ids, f"低分 vector 應被過濾，但 id=1 仍送進 rerank"
    # 3 筆 keyword_fallback 應保留
    assert {100, 101, 102}.issubset(kept_ids), (
        f"keyword_fallback 項不應被下限誤砍，實際: {sorted(kept_ids)}"
    )


def test_retrieve_does_not_truncate_when_under_limit():
    """候選數 ≤ 限制時，不截斷（全部送進 reranker）"""
    import os
    captured = {}

    mock_reranker = MagicMock()
    mock_reranker.is_available = True

    def spy_rerank(query, candidates, top_k=None):
        captured['count'] = len(candidates)
        return [dict(c, semantic_score=0.9) for c in candidates]

    mock_reranker.rerank.side_effect = spy_rerank

    r = _StubRetriever(
        reranker=mock_reranker,
        vector_results=[
            _make_result(id=i, vector_similarity=0.1 * i)
            for i in range(1, 11)  # 10 筆（< 20）
        ],
    )

    # 本測試專注「不截斷」行為，把下限設 0.0 避免影響計數
    old_limit = os.environ.get('RERANKER_INPUT_LIMIT')
    old_min = os.environ.get('RERANKER_MIN_VECTOR_SIMILARITY')
    os.environ['RERANKER_INPUT_LIMIT'] = '20'
    os.environ['RERANKER_MIN_VECTOR_SIMILARITY'] = '0.0'
    try:
        asyncio.run(r.retrieve(
            'q', vendor_id=1, top_k=5, similarity_threshold=0.0,
            enable_keyword_fallback=False,
        ))
    finally:
        for k, v in [('RERANKER_INPUT_LIMIT', old_limit),
                     ('RERANKER_MIN_VECTOR_SIMILARITY', old_min)]:
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    assert captured['count'] == 10, (
        f"候選 10 筆 < 限制 20 時不應截斷，實際送進 rerank: {captured['count']}"
    )


def test_retrieve_return_unfiltered_still_sorts_and_top_k():
    """return_unfiltered=True 仍然應依 final similarity 排序並套用 top_k"""
    r = _StubRetriever(
        vector_results=[
            _make_result(id=i, vector_similarity=0.1 * i)
            for i in range(1, 11)  # vector 0.1 ~ 1.0
        ],
    )
    out = asyncio.run(r.retrieve(
        'q', vendor_id=1, top_k=3, similarity_threshold=0.65,
        enable_keyword_fallback=False,
        return_unfiltered=True,
    ))
    assert len(out) == 3, f"top_k=3 應只回 3 筆（排序後），實際: {len(out)}"
    sims = [x['similarity'] for x in out]
    assert sims == sorted(sims, reverse=True), "應依 final similarity 降序"
    # 最高分的 id=10（vector=1.0）必須在結果中
    assert out[0]['id'] == 10, f"排序後第一筆應為 id=10，實際: {out[0]['id']}"


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
