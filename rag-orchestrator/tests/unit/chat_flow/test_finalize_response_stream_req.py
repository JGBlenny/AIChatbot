"""_finalize_response 串流分支回歸鎖。

背景：conversational-repair 接線時抽出的 _finalize_response 曾引用作用域外的
FastAPI `req`（NameError），所有走表單會話/收集中/圖片分支的 SSE 路徑 500——
unit 全 mock、修繕 e2e 走非串流，僅 e2e characterization 攔到。
本測試在 unit 層直接鎖住：stream=True 時必須能組出 StreamingResponse，
不得拋 NameError（req 必須由呼叫端顯式傳入）。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from routers.chat import VendorChatResponse, _finalize_response

pytestmark = pytest.mark.unit


def _make_response() -> VendorChatResponse:
    return VendorChatResponse(
        answer="測試回覆",
        intent_name="測試",
        intent_type="conversational",
        confidence=1.0,
        action_type="conversational",
        vendor_id=2,
        mode="b2c",
        session_id="unit-finalize-1",
        timestamp="2026-07-12T00:00:00",
    )


@pytest.mark.req("conversational-repair:8.1")
def test_stream_true_builds_streaming_response_without_scope_error():
    request = SimpleNamespace(stream=True)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_pool=MagicMock())))
    resp = _finalize_response(_make_response(), request, req)
    assert type(resp).__name__ == "StreamingResponse"
    assert resp.media_type == "text/event-stream"


@pytest.mark.req("conversational-repair:8.1")
def test_stream_false_returns_plain_response():
    request = SimpleNamespace(stream=False)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_pool=MagicMock())))
    original = _make_response()
    assert _finalize_response(original, request, req) is original
