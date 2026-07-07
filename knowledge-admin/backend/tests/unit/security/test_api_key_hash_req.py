"""unit:API 金鑰雜湊(_hash_api_key 為 sha256,與 rag 驗證端一致)。"""
import hashlib

import pytest

from app import _hash_api_key

pytestmark = pytest.mark.unit


def test_hash_is_sha256_hex():
    assert _hash_api_key("abc") == hashlib.sha256(b"abc").hexdigest()
    h = _hash_api_key("secret-key-123")
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
    assert _hash_api_key("x") != _hash_api_key("y")
