"""integration:embedding 生成(真實打 embedding-api 服務)。

填補對話檢索真空:embedding 生成先前無測。需 embedding-api 服務 + RUN_INTEGRATION=1。
"""
import pytest

from services.embedding_utils import EmbeddingClient

pytestmark = pytest.mark.integration


@pytest.mark.req("retrieval-embedding:1.1")
async def test_real_embedding_returns_1536_vector():
    vec = await EmbeddingClient().get_embedding("怎麼繳房租")
    assert vec is not None, "embedding-api 應回傳向量(服務可達時)"
    assert len(vec) == 1536, f"維度應為 1536,實得 {len(vec)}"


@pytest.mark.req("retrieval-embedding:1.1")
async def test_unreachable_api_returns_none_not_raise():
    # 壞 URL → 應吞例外回 None(不拋),供上游 fallback 關鍵字檢索
    c = EmbeddingClient(api_url="http://127.0.0.1:59999/nope")
    assert await c.get_embedding("x") is None
