"""補測試：rag 服務對服務 API Key 認證邏輯（純函式 unit）。

涵蓋：豁免路徑、sha256 雜湊、enforcement 開關。DB 驗證 verify_api_key 走 integration。
"""
import pytest

from services.api_key_auth import is_exempt, hash_key, auth_enforced

pytestmark = pytest.mark.unit


def test_exempt_paths():
    assert is_exempt("/")
    assert is_exempt("/api/v1/health")
    assert is_exempt("/docs")
    assert is_exempt("/openapi.json")
    assert not is_exempt("/api/v1/message")
    assert not is_exempt("/api/v1/loops/123")


def test_hash_key_is_sha256_hex_and_stable():
    h = hash_key("secret123")
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
    assert hash_key("secret123") == h           # 穩定
    assert hash_key("other") != h               # 不同輸入不同


def test_auth_enforced_toggle(monkeypatch):
    for v in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("RAG_API_AUTH_ENFORCE", v)
        assert auth_enforced() is True
    for v in ("", "0", "false", "off", "no"):
        monkeypatch.setenv("RAG_API_AUTH_ENFORCE", v)
        assert auth_enforced() is False
    monkeypatch.delenv("RAG_API_AUTH_ENFORCE", raising=False)
    assert auth_enforced() is False
