"""unit glue：vendor_chat_message 派發器「依序嘗試 / 回 None 續下一個 / 首個命中即回 / 順序固定」
與各 handler「非此案回 None」契約(chat-flow-refactor 任務 4.3)。

純 mock(不碰 DB/服務):以 SimpleNamespace 假冒 req、monkeypatch handler 群觀察派發順序。
不驗業務內容(那由 integration/e2e 守),只驗 orchestration glue。
"""
from types import SimpleNamespace

import pytest

import routers.chat as chat
from routers.chat import (
    ChatRequestContext,
    VendorChatRequest,
    handle_form_session,
    handle_conversational_session,
    handle_collecting,
    handle_image,
    handle_conversational_entry,
    vendor_chat_message,
)

pytestmark = pytest.mark.unit

SENTINEL = object()  # 充當「最終 Response」的哨兵


def _req(**state):
    """假 FastAPI Request:req.app.state.<attr>。"""
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


def _msg(**kw):
    """建合法請求(b2b 免帶 vendor_id,避開 B2C 驗證)。"""
    kw.setdefault("mode", "b2b")
    return VendorChatRequest(message="hi", **kw)


# ── 各 handler「非此案回 None」契約 ──────────────────────────────────────

@pytest.mark.req("chat-flow-refactor:6.1")
async def test_form_session_no_state_returns_none():
    r = _msg()
    assert await handle_form_session(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("chat-flow-refactor:6.1")
async def test_conversational_session_no_state_returns_none():
    r = _msg()
    assert await handle_conversational_session(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("chat-flow-refactor:6.1")
async def test_collecting_no_state_returns_none():
    r = _msg()
    assert await handle_collecting(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("chat-flow-refactor:6.1")
async def test_image_no_urls_returns_none():
    r = _msg()  # image_urls=None → 非此案
    assert await handle_image(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("chat-flow-refactor:6.1")
async def test_conversational_entry_non_prospect_returns_none():
    r = _msg(target_user="tenant")
    assert await handle_conversational_entry(r, _req(), ChatRequestContext()) is None


# ── 派發器順序 / 首個命中即回 / 回 None 續下一個 ───────────────────────────

def _patch_chain(monkeypatch, calls, *, hit=None):
    """把對話/緩存/檢索三個 handler 換成記錄呼叫順序的 stub。
    hit=handler 名 → 該 handler 回 SENTINEL,其餘回 None(retrieval 預設回 SENTINEL 當終點)。"""
    def make(name, default):
        async def stub(request, req, ctx):
            calls.append(name)
            return SENTINEL if (hit == name or (hit is None and name == "retrieval" and default)) else None
        return stub
    monkeypatch.setattr(chat, "handle_conversational_entry", make("conv_entry", False))
    monkeypatch.setattr(chat, "handle_cache", make("cache", False))
    monkeypatch.setattr(chat, "handle_retrieval", make("retrieval", True))
    # 避開真實業者解析
    monkeypatch.setattr(chat, "get_vendor_param_resolver", lambda: object())


def _b2b_req():
    """b2b + 無 vendor_id + role_id 已給 + 無 session/圖片 → 直達 handler 群,不碰 req。"""
    return VendorChatRequest(message="你好", mode="b2b", role_id="x")


@pytest.mark.req("chat-flow-refactor:6.2")
async def test_dispatch_order_falls_through_to_retrieval(monkeypatch):
    """全部回 None 直到 retrieval(終點)命中:順序固定 conv_entry→cache→retrieval。"""
    calls = []
    _patch_chain(monkeypatch, calls)
    resp = await vendor_chat_message(_b2b_req(), _req())
    assert resp is SENTINEL
    assert calls == ["conv_entry", "cache", "retrieval"]


@pytest.mark.req("chat-flow-refactor:6.2")
async def test_dispatch_first_hit_short_circuits(monkeypatch):
    """cache 命中 → 立即回傳,retrieval 不應被呼叫。"""
    calls = []
    _patch_chain(monkeypatch, calls, hit="cache")
    resp = await vendor_chat_message(_b2b_req(), _req())
    assert resp is SENTINEL
    assert calls == ["conv_entry", "cache"]
    assert "retrieval" not in calls


@pytest.mark.req("chat-flow-refactor:6.2")
async def test_dispatch_conv_entry_first_hit_short_circuits(monkeypatch):
    """conv_entry 命中 → cache/retrieval 都不應被呼叫(首個命中即回)。"""
    calls = []
    _patch_chain(monkeypatch, calls, hit="conv_entry")
    resp = await vendor_chat_message(_b2b_req(), _req())
    assert resp is SENTINEL
    assert calls == ["conv_entry"]
