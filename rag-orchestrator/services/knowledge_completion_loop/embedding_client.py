"""
知識完善迴圈 Embedding 客戶端

專門為知識完善迴圈設計的 embedding 生成客戶端，提供以下功能：
- 調用外部 embedding API（EMBEDDING_API_URL）
- 支援一般知識 embedding（question_summary）
- 支援 SOP embedding（content）
- 自動重試機制（使用 tenacity）
- 返回 1536 維向量

與 services/embedding_utils.py 的差異：
- 專為知識迴圈設計，帶有 tenacity 重試機制
- 針對知識生成場景優化（長時間運行，需要可靠性）

Author: AI Assistant
Created: 2026-03-27
"""

import os
import httpx
from typing import Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class KnowledgeLoopEmbeddingClient:
    """
    知識完善迴圈專用的 Embedding 客戶端

    特點：
    - 自動重試機制（最多 3 次）
    - 指數退避策略（2^x 秒）
    - 適用於長時間運行的知識生成任務
    """

    def __init__(self, api_url: Optional[str] = None, timeout: float = 30.0):
        """
        初始化 Embedding 客戶端

        Args:
            api_url: Embedding API URL（可選，默認使用環境變數）
            timeout: HTTP 請求超時時間（秒）
        """
        self.embedding_api_url = api_url or os.getenv(
            "EMBEDDING_API_URL",
            "http://embedding-api:5000/api/v1/embeddings"
        )
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False
    )
    async def generate_embedding(
        self,
        text: str,
        verbose: bool = False
    ) -> Optional[List[float]]:
        """
        生成文本的 embedding（帶自動重試）

        使用 tenacity 提供以下重試策略：
        - 最多重試 3 次
        - 指數退避：1秒, 2秒, 4秒
        - 僅對網路錯誤重試（HTTPError, TimeoutException）

        Args:
            text: 要生成 embedding 的文本
            verbose: 是否顯示詳細日誌（默認 False）

        Returns:
            embedding 向量（List[float]），失敗時返回 None
        """
        try:
            if verbose:
                print(f"🔍 [Embedding Client] 呼叫 API: {self.embedding_api_url}")
                print(f"   文本: {text[:50]}...")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.embedding_api_url,
                    json={"text": text}
                )

                if response.status_code != 200:
                    if verbose:
                        print(f"⚠️ Embedding API 錯誤: {response.status_code}")
                    return None

                data = response.json()
                embedding = data.get('embedding')

                if embedding:
                    if verbose:
                        print(f"✅ 成功獲得向量: 維度 {len(embedding)}")
                    return embedding
                else:
                    if verbose:
                        print(f"⚠️ 回應中無 embedding 欄位")
                    return None

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            # 這些異常會被 tenacity 捕獲並重試
            if verbose:
                print(f"⚠️ 網路錯誤（將重試）: {e}")
            raise  # 拋出讓 tenacity 處理重試

        except Exception as e:
            # 其他異常不重試，直接返回 None
            print(f"❌ Embedding API 呼叫失敗: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return None

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        verbose: bool = False
    ) -> List[Optional[List[float]]]:
        """
        批量生成 embeddings（並發執行，每個帶重試）

        Args:
            texts: 文本列表
            verbose: 是否顯示詳細日誌

        Returns:
            embedding 向量列表，每個可能為 None（如果失敗）
        """
        import asyncio

        tasks = [self.generate_embedding(text, verbose=False) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理異常
        embeddings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"⚠️ 第 {i+1} 個文本 embedding 生成失敗: {result}")
                embeddings.append(None)
            else:
                embeddings.append(result)

        if verbose:
            success_count = sum(1 for e in embeddings if e is not None)
            print(f"✅ 批量生成完成: {success_count}/{len(texts)} 成功")

        return embeddings

    def to_pgvector_format(self, embedding: List[float]) -> str:
        """
        將 embedding 轉換為 PostgreSQL pgvector 格式字串

        Args:
            embedding: embedding 向量

        Returns:
            PostgreSQL vector 格式字串，例如: '[0.1,0.2,0.3]'

        Raises:
            ValueError: 如果 embedding 為空
        """
        if not embedding:
            raise ValueError("Embedding is empty")

        return '[' + ','.join(map(str, embedding)) + ']'


# ============================================================
# 便利函數（專用於知識迴圈）
# ============================================================

_loop_client = None


def get_loop_embedding_client(api_url: Optional[str] = None) -> KnowledgeLoopEmbeddingClient:
    """
    獲取知識迴圈專用的 embedding 客戶端（單例模式）

    Args:
        api_url: 可選的 API URL（首次呼叫時設定）

    Returns:
        KnowledgeLoopEmbeddingClient 實例
    """
    global _loop_client
    if _loop_client is None:
        _loop_client = KnowledgeLoopEmbeddingClient(api_url)
    return _loop_client


async def generate_knowledge_embedding(
    question_summary: str,
    api_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[List[float]]:
    """
    生成一般知識的 embedding（便利函數）

    用於一般知識庫項目，對 question_summary 生成向量

    Args:
        question_summary: 知識問題摘要
        api_url: 可選的 API URL
        verbose: 是否顯示詳細日誌

    Returns:
        embedding 向量，失敗時返回 None
    """
    client = get_loop_embedding_client(api_url)
    return await client.generate_embedding(question_summary, verbose=verbose)


async def generate_sop_embedding(
    sop_content: str,
    api_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[List[float]]:
    """
    生成 SOP 的 embedding（便利函數）

    用於 SOP 項目，對 SOP content 生成向量

    Args:
        sop_content: SOP 內容文本
        api_url: 可選的 API URL
        verbose: 是否顯示詳細日誌

    Returns:
        embedding 向量，失敗時返回 None
    """
    client = get_loop_embedding_client(api_url)
    return await client.generate_embedding(sop_content, verbose=verbose)


async def generate_embedding_with_pgvector(
    text: str,
    api_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[str]:
    """
    生成 embedding 並轉換為 pgvector 格式（便利函數）

    適用於直接插入 PostgreSQL 的場景

    Args:
        text: 要生成 embedding 的文本
        api_url: 可選的 API URL
        verbose: 是否顯示詳細日誌

    Returns:
        pgvector 格式字串（如 '[0.1,0.2,...]'），失敗時返回 None
    """
    client = get_loop_embedding_client(api_url)
    embedding = await client.generate_embedding(text, verbose=verbose)

    if embedding:
        return client.to_pgvector_format(embedding)
    else:
        return None


# ============================================================
# 使用範例與測試
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_loop_embedding_client():
        """測試知識迴圈 embedding 客戶端"""
        print("="*60)
        print("測試知識迴圈 Embedding Client")
        print("="*60)

        # 測試 1: 一般知識 embedding
        print("\n📝 測試 1: 生成一般知識 embedding")
        question = "租金每月幾號繳納？"
        embedding = await generate_knowledge_embedding(question, verbose=True)

        if embedding:
            print(f"✅ 成功生成 embedding，維度: {len(embedding)}")
            print(f"   前 5 個值: {embedding[:5]}")
        else:
            print("❌ 生成失敗")

        # 測試 2: SOP embedding
        print("\n📝 測試 2: 生成 SOP embedding")
        sop_content = "停車位申請流程：1. 填寫申請表 2. 提交管理處 3. 等待審核"
        embedding = await generate_sop_embedding(sop_content, verbose=True)

        if embedding:
            print(f"✅ 成功生成 SOP embedding，維度: {len(embedding)}")
        else:
            print("❌ 生成失敗")

        # 測試 3: pgvector 格式
        print("\n📝 測試 3: 生成 pgvector 格式")
        pgvector = await generate_embedding_with_pgvector("測試文本", verbose=True)

        if pgvector:
            print(f"✅ 成功生成 pgvector 格式")
            print(f"   格式: {pgvector[:50]}...")
        else:
            print("❌ 生成失敗")

        # 測試 4: 批量生成
        print("\n📝 測試 4: 批量生成 embeddings")
        texts = [
            "租金繳納日期",
            "寵物飼養規定",
            "停車位申請流程"
        ]

        client = get_loop_embedding_client()
        embeddings = await client.generate_embeddings_batch(texts, verbose=True)

        print(f"   成功: {sum(1 for e in embeddings if e is not None)}/{len(texts)}")

        print("\n" + "="*60)
        print("測試完成！")
        print("="*60)

    # 執行測試
    asyncio.run(test_loop_embedding_client())
