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


# ── 陷阱4:handle_collecting 取消+pending → 換 request.message 並續跑(回 None)──
#
# 註:此 fall-through 在「真實 DB」目前走不到——form_sessions 缺 pending_question 欄位,
# _get_pending_question_sync 例外被吞 → 永遠回 None → 取消時無 pending(見回覆說明)。
# 故以 unit 確定性驗「重構後 handle_collecting 對 cancel+pending 結果的處置」本身。

def _collecting_req():
    return VendorChatRequest(message="取消", mode="b2b", session_id="trap4-sid")


def _collecting_req_env(monkeypatch, *, form_result):
    """假 req:form_manager.collect_field_data 回 form_result;隔離 presales leaf 合成。"""
    async def _collect(**kw):
        return form_result

    async def _passthrough(fr, request, req):
        return fr

    monkeypatch.setattr(chat, "_maybe_synthesize_presales_leaf", _passthrough)
    fm = SimpleNamespace(collect_field_data=_collect)
    ic = SimpleNamespace(classify=lambda msg: {})
    sop = SimpleNamespace(trigger_handler=SimpleNamespace(delete_context=lambda sid: None))
    return _req(form_manager=fm, intent_classifier=ic, sop_orchestrator=sop)


@pytest.mark.req("chat-flow-refactor:3.2")
async def test_collecting_cancel_with_pending_swaps_message_and_continues(monkeypatch):
    """陷阱4:取消且有 pending_question → 換 request.message 為待處理問題、回 None(交由後續檢索續答)。"""
    req = _collecting_req_env(monkeypatch, form_result={
        "form_cancelled": True, "pending_question": "大樓停水怎麼辦"})
    request = _collecting_req()
    ctx = ChatRequestContext(session_state={"state": "COLLECTING", "form_id": "demo_form"})

    resp = await handle_collecting(request, req, ctx)

    assert resp is None, "取消+pending 應回 None(續跑),而非直接回應"
    assert request.message == "大樓停水怎麼辦", "request.message 應被替換為待處理問題(陷阱4)"


@pytest.mark.req("chat-flow-refactor:3.2")
async def test_collecting_cancel_without_pending_returns_response(monkeypatch):
    """對照:取消但無 pending → 直接回最終 Response(不續跑、不改 message)。"""
    req = _collecting_req_env(monkeypatch, form_result={
        "form_cancelled": True, "answer": "已取消表單"})
    request = _collecting_req()
    ctx = ChatRequestContext(session_state={"state": "COLLECTING", "form_id": "demo_form"})

    resp = await handle_collecting(request, req, ctx)

    assert resp is not None, "取消但無 pending → 應直接回應(非 None)"
    assert request.message == "取消", "無 pending 時不應改 request.message"
