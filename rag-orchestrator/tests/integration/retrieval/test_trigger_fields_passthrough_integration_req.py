"""integration：觸發配置欄位透傳（spec trigger-vocabulary-debt task 1.2｜R1.1）。

1.1 已補 `vendor_knowledge_retriever_v2.py` 兩處 SELECT ＋ `_format_result` 三欄映射
（trigger_mode / trigger_keywords / immediate_prompt）。本測試以真 DB 驗證斷鏈已修：
無論走向量或關鍵詞路徑，回傳的每筆 dict 都帶這三個 key（值可為 None，key 必存在），
且 reranker 啟用（重排路徑）下欄位不因映射流程遺失。

只斷言「三 key 恆在」這條永成立的契約——不斷言值，因 dev 庫多數列為預設值（None）。
前提資料（可檢索列）不存在時明確 skip（不假綠燈），沿用既有 integration 慣例。

需 RUN_INTEGRATION=1 ＋ 可連 DB；reranker 一案另需 semantic-model 服務（不可用則 skip 該案，
不誤紅——reranker 本身健康由 test_reranker_health_req.py 專責把關）。
"""
import os

import pytest

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2 as KB

pytestmark = [pytest.mark.integration]

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))

# 1.1 補上的三個透傳欄位——消費層 chat.py:2969/2997/2998 依賴其存在。
TRIGGER_KEYS = ("trigger_mode", "trigger_keywords", "immediate_prompt")


def _assert_trigger_keys(results, path_label):
    """每筆結果 dict 都必須含三個觸發 key（值可 None，key 不可缺）。"""
    for r in results:
        for k in TRIGGER_KEYS:
            assert k in r, (
                f"{path_label} 路徑結果 id={r.get('id')} 缺觸發欄位 key {k!r} "
                f"（1.1 透傳斷鏈未修或路徑遺漏）"
            )


@pytest.mark.req("trigger-vocabulary-debt:1.1")
async def test_vector_path_carries_trigger_fields():
    """向量路徑：真 DB 檢索回傳的每筆 dict 均含三個觸發 key。"""
    retriever = KB()
    # 走完整 retrieve（真 embedding + 真 DB）；embedding 服務不可用時 vector 路徑回空。
    results = await retriever.retrieve(
        "怎麼繳房租", vendor_id=VENDOR_ID, top_k=5,
        target_user="tenant", mode="b2c")
    if not results:
        pytest.skip("向量路徑無結果（embedding-api / DB 環境）→ 無法實質驗證透傳")
    _assert_trigger_keys(results, "向量")


@pytest.mark.req("trigger-vocabulary-debt:1.1")
async def test_keyword_path_carries_trigger_fields():
    """關鍵詞路徑：直呼 _keyword_search（免 embedding），每筆 dict 均含三個觸發 key。"""
    retriever = KB()
    results = await retriever._keyword_search(
        "租金 繳費 方式", vendor_id=VENDOR_ID, limit=5,
        target_user="tenant", mode="b2c")
    if not results:
        pytest.skip("關鍵詞路徑無結果（DB 無匹配 keywords 列）→ 無法實質驗證透傳")
    _assert_trigger_keys(results, "關鍵詞")


@pytest.mark.req("trigger-vocabulary-debt:1.1")
async def test_reranker_path_carries_trigger_fields():
    """reranker 啟用路徑：重排後每筆 dict 仍含三個觸發 key（映射流程不吞欄位）。

    reranker 服務不可用（semantic-model 未起）→ skip（reranker 健康另有專責測試把關，
    此處不重複判其死活，只驗「有 reranker 時透傳不丟」）。
    """
    from services.semantic_reranker import get_semantic_reranker
    reranker = get_semantic_reranker()
    if not reranker._check_service():
        pytest.skip("semantic-model reranker 服務不可用 → 由 test_reranker_health 專責，本案略過")

    retriever = KB()
    # 手動掛上 reranker（避免依賴 ENABLE_RERANKER 環境旗標於測試容器的設定狀態）。
    retriever.semantic_reranker = reranker

    results = await retriever.retrieve(
        "怎麼繳房租", vendor_id=VENDOR_ID, top_k=5,
        target_user="tenant", mode="b2c")
    if not results:
        pytest.skip("重排路徑無結果（embedding-api / DB 環境）→ 無法實質驗證透傳")
    # 至少一筆確實走了 rerank（rerank_score 非 None）才算真的驗到重排路徑透傳。
    if not any(r.get("rerank_score") is not None for r in results):
        pytest.skip("結果無 rerank_score（候選未進 reranker）→ 未實質走重排路徑")
    _assert_trigger_keys(results, "reranker")
