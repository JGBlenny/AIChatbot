"""unit:embedding 工具純函式(to_pgvector_format)。"""
import pytest

from services.embedding_utils import EmbeddingClient

pytestmark = pytest.mark.unit


def test_to_pgvector_format():
    c = EmbeddingClient()
    assert c.to_pgvector_format([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"


def test_to_pgvector_empty_raises():
    c = EmbeddingClient()
    with pytest.raises(ValueError):
        c.to_pgvector_format([])
