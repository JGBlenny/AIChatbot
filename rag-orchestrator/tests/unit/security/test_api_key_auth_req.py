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


# ---------------------------------------------------------------------------
# 1.10 P2：agent 作用域欄位偵測 ⛔ 不得永久快取 False
#
# 病灶（1.9 security review）：`vendor_ids` 缺欄時 `verify_api_key` 降級成
# `vendor_ids=None`，而那個值的語義是「**不限業者**」。原實作在「欄位不存在」
# 時把 False 寫進行程級快取且永不重試 ⇒ migration 套好之後，舊行程仍會一路
# 降級到重啟為止。修法：True 永久快取、False 只快取 TTL。
# ---------------------------------------------------------------------------

import services.api_key_auth as _aka  # noqa: E402


class _FakeConn:
    """`fetchval` 回可配置值；記錄被查了幾次。"""

    def __init__(self, values):
        self._values = list(values)
        self.calls = 0

    async def fetchval(self, _sql, *_args):
        self.calls += 1
        v = self._values[min(self.calls - 1, len(self._values) - 1)]
        if isinstance(v, Exception):
            raise v
        return v


@pytest.fixture()
def clean_scope_detection():
    _aka._reset_agent_scope_detection()
    yield
    _aka._reset_agent_scope_detection()


async def test_scope_cols_detected_true_is_cached_forever(clean_scope_detection):
    """正對照組：兩欄都在 ⇒ True，且只查一次（欄位不會自己消失）。"""
    conn = _FakeConn([2, 2])

    assert await _aka._detect_agent_scope_cols(conn) is True
    assert await _aka._detect_agent_scope_cols(conn) is True
    assert conn.calls == 1, "True 不該重查"
    assert _aka.agent_scope_cols_state() is True


async def test_scope_cols_missing_is_rechecked_after_ttl(monkeypatch, clean_scope_detection):
    """欄位不存在 ⇒ False，但 TTL 到期後**必須重查**（⛔ 不永久快取）。"""
    clock = {"t": 1000.0}
    monkeypatch.setattr(_aka.time, "monotonic", lambda: clock["t"])
    conn = _FakeConn([0, 2])          # 第一次缺欄；migration 套上後第二次兩欄都在

    assert await _aka._detect_agent_scope_cols(conn) is False
    assert conn.calls == 1

    # TTL 內：不重查（避免每個請求都打 information_schema）
    clock["t"] += _aka._AGENT_SCOPE_RECHECK_S - 1
    assert await _aka._detect_agent_scope_cols(conn) is False
    assert conn.calls == 1, "TTL 內不該重查"

    # TTL 到期：重查，並看到 migration 已套
    clock["t"] += 2
    assert await _aka._detect_agent_scope_cols(conn) is True
    assert conn.calls == 2, "TTL 到期沒重查——這正是被修掉的永久快取病灶"


async def test_scope_cols_detection_error_is_also_ttl_bounded(monkeypatch,
                                                              clean_scope_detection):
    """偵測本身失敗（連線／權限）⇒ 一樣是帶 TTL 的 False，不是永久。"""
    clock = {"t": 0.0}
    monkeypatch.setattr(_aka.time, "monotonic", lambda: clock["t"])
    conn = _FakeConn([RuntimeError("boom"), 2])

    assert await _aka._detect_agent_scope_cols(conn) is False
    clock["t"] += _aka._AGENT_SCOPE_RECHECK_S + 1
    assert await _aka._detect_agent_scope_cols(conn) is True
    assert conn.calls == 2


def test_agent_scope_cols_state_starts_unknown(clean_scope_detection):
    """尚未偵測 ⇒ `None`（健檢據此判定「不知道」，⛔ 不當成 ready）。"""
    assert _aka.agent_scope_cols_state() is None
