"""unit：對話引擎結果 → VendorChatResponse 的 quick_replies 透傳（conversational-repair Gap C）。

交易 confirm gate 的三顆按鈕（✅送出/✏️修改/❌取消）由引擎 handle() 回傳 dict 的
quick_replies 承載，必須透傳進 VendorChatResponse.quick_replies——否則到不了前端。
既有面向（無 quick_replies）行為不變（quick_replies 維持 None）。
"""
from types import SimpleNamespace

import pytest

from routers.chat import _conversational_to_response

pytestmark = pytest.mark.unit


def _request(**overrides):
    base = dict(include_sources=False, vendor_id=1, mode="b2c",
                session_id="s1")
    base.update(overrides)
    return SimpleNamespace(**base)


_CONFIRM_QR = [
    {"text": "✅ 確認送出", "value": "confirm_submit", "style": "success"},
    {"text": "✏️ 我要修改", "value": "confirm_edit", "style": "secondary"},
    {"text": "❌ 取消", "value": "confirm_cancel", "style": "danger"},
]


@pytest.mark.req("conversational-repair:4.1")
def test_confirm_response_surfaces_quick_replies():
    result = {"answer": "為您確認報修內容...", "conversational": True,
              "converged": False, "quick_replies": _CONFIRM_QR}
    resp = _conversational_to_response(result, _request())
    assert resp.quick_replies is not None
    values = [q.value for q in resp.quick_replies]
    assert values == ["confirm_submit", "confirm_edit", "confirm_cancel"]
    # 保留樣式（前端據此渲染主/次/危險按鈕）
    styles = [q.style for q in resp.quick_replies]
    assert styles == ["success", "secondary", "danger"]


@pytest.mark.req("conversational-repair:4.1")
def test_plain_facet_response_has_no_quick_replies():
    # 既有面向（無 quick_replies）→ 行為不變
    result = {"answer": "推薦方案...", "conversational": True, "converged": True}
    resp = _conversational_to_response(result, _request())
    assert resp.quick_replies is None


@pytest.mark.req("conversational-repair:4.1")
def test_empty_quick_replies_normalized_to_none():
    result = {"answer": "問句", "conversational": True, "converged": False,
              "quick_replies": []}
    resp = _conversational_to_response(result, _request())
    assert resp.quick_replies is None
