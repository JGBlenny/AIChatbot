"""
Embedding 工具模組
統一處理所有 embedding 相關功能，避免代碼重複
"""
import os
import httpx
from typing import Optional, List


class EmbeddingClient:
    """
    Embedding 客戶端
    提供統一的 embedding 生成介面
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        初始化 Embedding 客戶端

        Args:
            api_url: Embedding API URL（可選，默認使用環境變數）
        """
        self.embedding_api_url = api_url or os.getenv(
            "EMBEDDING_API_URL",
            "http://embedding-api:5000/api/v1/embeddings"
        )

    async def get_embedding(
        self,
        text: str,
        verbose: bool = False
    ) -> Optional[List[float]]:
        """
        生成文本的 embedding

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

            async with httpx.AsyncClient(timeout=30.0) as client:
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

        except Exception as e:
            print(f"❌ Embedding API 呼叫失敗: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return None

    async def get_embeddings_batch(
        self,
        texts: List[str],
        verbose: bool = False
    ) -> List[Optional[List[float]]]:
        """
        批量生成 embeddings（並發執行）

        Args:
            texts: 文本列表
            verbose: 是否顯示詳細日誌

        Returns:
            embedding 向量列表，每個可能為 None（如果失敗）
        """
        import asyncio

        tasks = [self.get_embedding(text, verbose=False) for text in texts]
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
        """
        if not embedding:
            raise ValueError("Embedding is empty")

        return '[' + ','.join(map(str, embedding)) + ']'


# ============================================================
# 全域單例模式（推薦使用方式）
# ============================================================

_default_client = None


def get_embedding_client(api_url: Optional[str] = None) -> EmbeddingClient:
    """
    獲取默認的 embedding 客戶端（單例模式）

    Args:
        api_url: 可選的 API URL（首次呼叫時設定）

    Returns:
        EmbeddingClient 實例
    """
    global _default_client
    if _default_client is None:
        _default_client = EmbeddingClient(api_url)
    return _default_client


# ============================================================
# 便利函數（向後兼容）
# ============================================================

async def generate_embedding(
    text: str,
    api_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[List[float]]:
    """
    生成單個文本的 embedding（便利函數）

    這是一個簡化的介面，內部使用全域 EmbeddingClient

    Args:
        text: 要生成 embedding 的文本
        api_url: 可選的 API URL
        verbose: 是否顯示詳細日誌

    Returns:
        embedding 向量，失敗時返回 None
    """
    client = get_embedding_client(api_url)
    return await client.get_embedding(text, verbose=verbose)


async def generate_embedding_with_pgvector(
    text: str,
    api_url: Optional[str] = None,
    verbose: bool = False
) -> Optional[str]:
    """
    生成 embedding 並轉換為 pgvector 格式（便利函數）

    這是知識庫插入常用的格式

    Args:
        text: 要生成 embedding 的文本
        api_url: 可選的 API URL
        verbose: 是否顯示詳細日誌

    Returns:
        pgvector 格式字串（如 '[0.1,0.2,...]'），失敗時返回 None
    """
    client = get_embedding_client(api_url)
    embedding = await client.get_embedding(text, verbose=verbose)

    if embedding:
        return client.to_pgvector_format(embedding)
    else:
        return None


# ============================================================
# 使用範例與測試
# ============================================================

if __name__ == "__main__":
    import asyncio

    async def test_embedding_utils():
        """測試 embedding 工具"""
        print("="*60)
        print("測試 Embedding Utils")
        print("="*60)

        # 測試 1: 單個 embedding
        print("\n📝 測試 1: 生成單個 embedding")
        text = "我想知道如何繳納租金"
        embedding = await generate_embedding(text, verbose=True)

        if embedding:
            print(f"✅ 成功生成 embedding，維度: {len(embedding)}")
            print(f"   前 5 個值: {embedding[:5]}")

            # 轉換為 pgvector 格式
            client = get_embedding_client()
            pgvector_str = client.to_pgvector_format(embedding)
            print(f"   PG Vector 格式長度: {len(pgvector_str)} 字元")
            print(f"   前 50 字元: {pgvector_str[:50]}...")
        else:
            print("❌ 生成失敗")

        # 測試 2: 批量 embedding
        print("\n📝 測試 2: 批量生成 embeddings")
        texts = [
            "租金如何計算",
            "寵物飼養規定",
            "退租流程說明"
        ]

        client = get_embedding_client()
        embeddings = await client.get_embeddings_batch(texts, verbose=True)

        print(f"   成功: {sum(1 for e in embeddings if e is not None)}/{len(texts)}")

        # 測試 3: pgvector 便利函數
        print("\n📝 測試 3: pgvector 便利函數")
        pgvector = await generate_embedding_with_pgvector("測試文本", verbose=True)

        if pgvector:
            print(f"✅ 成功生成 pgvector 格式")
            print(f"   格式: {pgvector[:30]}...")
        else:
            print("❌ 生成失敗")

        print("\n" + "="*60)
        print("測試完成！")
        print("="*60)

    # 執行測試
    asyncio.run(test_embedding_utils())
