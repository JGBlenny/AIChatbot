"""
簡單的 embedding_client 功能驗證

繞過套件載入問題，直接測試 embedding_client 模組
"""

import sys
import asyncio
from unittest.mock import Mock, patch

# 直接導入 embedding_client 模組
from embedding_client import (
    KnowledgeLoopEmbeddingClient,
    generate_knowledge_embedding,
    generate_sop_embedding
)


def test_client_initialization():
    """測試 1: 客戶端初始化"""
    print("測試 1: 客戶端初始化...")
    client = KnowledgeLoopEmbeddingClient()
    assert client.embedding_api_url is not None
    assert "embedding" in client.embedding_api_url.lower()
    print("✅ 初始化成功")


async def test_generate_embedding_success():
    """測試 2: 成功生成 embedding"""
    print("\n測試 2: 成功生成 embedding...")
    client = KnowledgeLoopEmbeddingClient()

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'embedding': [0.1] * 1536}
        mock_client.post.return_value = mock_response

        embedding = await client.generate_embedding("租金如何繳納？")

        assert embedding is not None
        assert len(embedding) == 1536
        print(f"✅ 成功生成 {len(embedding)} 維向量")


async def test_generate_embedding_api_error():
    """測試 3: API 錯誤處理"""
    print("\n測試 3: API 錯誤處理...")
    client = KnowledgeLoopEmbeddingClient()

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.post.return_value = mock_response

        embedding = await client.generate_embedding("測試文本")

        assert embedding is None
        print("✅ 正確處理 API 錯誤")


async def test_generate_embedding_network_error_with_retry():
    """測試 4: 網路錯誤重試"""
    print("\n測試 4: 網路錯誤重試機制...")
    client = KnowledgeLoopEmbeddingClient()

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value

        # 前 2 次失敗，第 3 次成功
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                import httpx
                raise httpx.TimeoutException("Timeout")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'embedding': [0.5] * 1536}
                return mock_response

        mock_client.post.side_effect = side_effect

        embedding = await client.generate_embedding("測試重試")

        assert embedding is not None
        assert len(embedding) == 1536
        assert call_count[0] == 3  # 重試成功
        print(f"✅ 重試機制正常（共 {call_count[0]} 次調用）")


async def test_convenience_functions():
    """測試 5: 便利函數"""
    print("\n測試 5: 便利函數...")

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'embedding': [0.2] * 1536}
        mock_client.post.return_value = mock_response

        # 測試知識 embedding
        emb1 = await generate_knowledge_embedding("租金繳納日期？")
        assert emb1 is not None
        print("  ✅ generate_knowledge_embedding 正常")

        # 測試 SOP embedding
        emb2 = await generate_sop_embedding("停車位申請流程...")
        assert emb2 is not None
        print("  ✅ generate_sop_embedding 正常")


def test_pgvector_format():
    """測試 6: pgvector 格式轉換"""
    print("\n測試 6: pgvector 格式轉換...")
    client = KnowledgeLoopEmbeddingClient()

    embedding = [0.1, 0.2, 0.3]
    pgvector_str = client.to_pgvector_format(embedding)

    assert pgvector_str == '[0.1,0.2,0.3]'
    assert pgvector_str.startswith('[')
    assert pgvector_str.endswith(']')
    print(f"✅ 正確轉換為 pgvector 格式: {pgvector_str}")


async def run_all_tests():
    """運行所有測試"""
    print("="*60)
    print("Embedding Client 功能驗證")
    print("="*60)

    try:
        test_client_initialization()
        await test_generate_embedding_success()
        await test_generate_embedding_api_error()
        await test_generate_embedding_network_error_with_retry()
        await test_convenience_functions()
        test_pgvector_format()

        print("\n" + "="*60)
        print("✅ 所有測試通過！")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
