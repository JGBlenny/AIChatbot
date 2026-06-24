"""reranker（semantic-model）健康/行為測試（integration）。

正面驗證 reranker **本身**是系統的一部分，要被測、要被看見：
- 服務可達（health）
- 對已知 query 正確排序（相關候選分數明顯高於不相關）

刻意「失敗即紅、可歸因」而**非 skip**——reranker 掛/降級時這條會明確指出問題，
不讓它躲在其他測試（如表單觸發 e2e）的莫名失敗背後。

需 RUN_INTEGRATION=1 + semantic-model 服務；對應 testing-traceability R5.3（reranker 排序）。
"""
import pytest

from services.semantic_reranker import get_semantic_reranker

pytestmark = pytest.mark.integration


@pytest.mark.req("testing-traceability:5.3")
def test_reranker_service_reachable():
    """reranker 服務可達且健康（不可達＝真問題，明確失敗）。"""
    reranker = get_semantic_reranker()
    assert reranker._check_service() is True, \
        "semantic-model reranker 服務不可達/不健康 — 這是真實系統問題，需排查（非略過）"


@pytest.mark.req("testing-traceability:5.3")
def test_reranker_ranks_relevant_candidate_highest():
    """對已知 query，相關候選應排第一且分數明顯高於不相關候選。"""
    reranker = get_semantic_reranker()
    assert reranker._check_service() is True, "reranker 不可用 — 無法驗證排序（真問題，非略過）"

    candidates = [
        {"id": 1, "question_summary": "停車場在哪裡", "answer": "停車場位於 B1"},
        {"id": 2, "question_summary": "租金繳納方式", "answer": "租金可用轉帳或現金繳納"},
        {"id": 3, "question_summary": "合約續約規定", "answer": "續約請於到期前一個月通知"},
    ]
    reranked = reranker.rerank("租金怎麼繳費", candidates, top_k=3)

    assert reranked, "reranker 回傳空結果"
    assert reranked[0]["id"] == 2, \
        f"相關候選（租金繳納）應排第一，實得順序 {[c['id'] for c in reranked]}"

    top_score = reranked[0].get("semantic_score", 0.0)
    others = [c.get("semantic_score", 0.0) for c in reranked[1:]]
    assert top_score > 0.5, f"相關候選分數應明顯偏高，實得 {top_score}"
    assert all(top_score > s for s in others), \
        f"相關候選分數應高於所有不相關候選，top={top_score} others={others}"
