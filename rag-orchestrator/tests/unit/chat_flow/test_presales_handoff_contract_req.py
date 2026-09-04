"""unit 層：`handoff` 回應契約與 SSE 透傳（design.md 元件 7）。需求 4.1、4.4。

⛔ 欄位可選：既有呼叫端不升級不受影響（值 null）；SSE 與非串流同語義；`quick_replies` 行為不變。
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import routers.chat as chat
from routers.chat import HandoffSignal, VendorChatRequest, VendorChatResponse, _conversational_to_response

pytestmark = pytest.mark.unit
HANDOFF = {"reason": "sensitive_no_grounding", "fact_class": "customer_reference",
           "channel": "line_official", "message": "固定句"}


def _request(**over):
    base = dict(message="q", mode="b2b", target_user="prospect", session_id="backtest_session_c1")
    base.update(over)
    return VendorChatRequest(**base)


# ── 非串流（R4.1）─────────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:4.1")
def test_response_model_has_optional_handoff_with_closed_enums():
    r = VendorChatResponse(answer="a", mode="b2b", timestamp="t")
    assert r.handoff is None and "handoff" in json.loads(r.json())        # 鍵存在、值 null
    h = HandoffSignal(**HANDOFF)
    assert h.reason == "sensitive_no_grounding" and h.fact_class == "customer_reference"
    with pytest.raises(Exception):
        HandoffSignal(**{**HANDOFF, "reason": "whatever"})                 # enum 封閉
    with pytest.raises(Exception):
        HandoffSignal(**{**HANDOFF, "fact_class": "Pricing"})


@pytest.mark.req("presales-grounding-gate:4.1")
def test_conversational_result_handoff_is_passed_through():
    resp = _conversational_to_response({"answer": "固定句", "converged": False, "handoff": HANDOFF}, _request())
    assert resp.handoff is not None and resp.handoff.dict() == HANDOFF
    assert resp.intent_type == "conversational" and resp.quick_replies is None


@pytest.mark.req("presales-grounding-gate:4.1")
def test_conversational_result_without_handoff_is_none_and_quick_replies_unchanged():
    resp = _conversational_to_response({"answer": "a", "converged": True,
                                        "quick_replies": [{"text": "✅", "value": "confirm_submit"}]}, _request())
    assert resp.handoff is None and resp.quick_replies and resp.quick_replies[0].value == "confirm_submit"


# ── SSE（R4.4）────────────────────────────────────────────────────────────────
async def _collect(gen):
    events = []
    async for raw in gen:
        lines = raw.strip().split("\n")
        events.append((lines[0].replace("event: ", ""), json.loads(lines[1].replace("data: ", ""))))
    return events


def _engine(chunks):
    eng = MagicMock()

    async def _stream(decision):
        for c in chunks:
            yield c
    eng.stream_answer = _stream
    return eng


@pytest.mark.req("presales-grounding-gate:4.4")
async def test_sse_metadata_carries_handoff_for_handoff_decision():
    decision = {"kind": "handoff", "answer": "固定句", "handoff": HANDOFF}
    events = await _collect(chat._conversational_sse(_engine(["固定句"]), decision, _request()))
    meta = dict(events)["metadata"]
    assert meta["handoff"] == HANDOFF and [e for e, _ in events] == ["start", "intent", "answer_chunk", "metadata", "done"]


@pytest.mark.req("presales-grounding-gate:4.4")
async def test_sse_metadata_has_no_handoff_key_when_absent():
    decision = {"kind": "converge", "converge_kind": "answer", "handoff": None}
    events = await _collect(chat._conversational_sse(_engine(["電子發票可自動開立"]), decision, _request()))
    assert "handoff" not in dict(events)["metadata"]


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_sse_scans_streamed_text_and_adds_llm_mention_handoff():
    """引擎 stub 不會做後置掃描 ⇒ SSE 層自己補（與非串流同語義，只加訊號不改文字）。"""
    decision = {"kind": "converge", "converge_kind": "answer", "handoff": None, "fact_class": "feature"}
    events = await _collect(chat._conversational_sse(_engine(["細節建議洽", "專人確認。"]), decision, _request()))
    meta = dict(events)["metadata"]
    assert meta["handoff"]["reason"] == "llm_mentioned_handoff" and meta["handoff"]["fact_class"] == "feature"
    assert "".join(d["chunk"] for e, d in events if e == "answer_chunk") == "細節建議洽專人確認。"
