"""T2 主幹確定性：售前對話 SSE 事件序 characterization。

以函式層驅動 `_conversational_sse`（只用 engine + decision，不碰 DB/LLM/HTTP）→ unit。
釘住現況事件序 start→intent→answer_chunk(逐 chunk)→metadata→done。
對應 testing-traceability R5.5（SSE 串流事件序）。
"""
import json

import pytest
from unittest.mock import MagicMock

import routers.chat as chat

pytestmark = pytest.mark.unit


async def _collect(gen):
    events = []
    async for raw in gen:
        lines = raw.strip().split("\n")
        etype = lines[0].replace("event: ", "")
        data = json.loads(lines[1].replace("data: ", ""))
        events.append((etype, data))
    return events


def _engine_streaming(chunks):
    eng = MagicMock()

    async def _stream(decision):
        for c in chunks:
            yield c

    eng.stream_answer = _stream
    return eng


@pytest.mark.req("testing-traceability:5.5")
async def test_sse_event_sequence_is_start_intent_chunks_metadata_done():
    eng = _engine_streaming(["你好", "，這是", "建議"])
    events = await _collect(chat._conversational_sse(eng, decision=object(), request=None))
    types = [t for t, _ in events]

    assert types[0] == "start"
    assert types[1] == "intent"
    assert types[-2] == "metadata"
    assert types[-1] == "done"
    # answer_chunk 夾在 intent 與 metadata 之間，且逐 chunk 對應
    chunks = [d["chunk"] for t, d in events if t == "answer_chunk"]
    assert chunks == ["你好", "，這是", "建議"]
    assert types == ["start", "intent", "answer_chunk", "answer_chunk", "answer_chunk",
                     "metadata", "done"]


@pytest.mark.req("testing-traceability:5.5")
async def test_sse_skips_empty_chunks_but_keeps_framing():
    """空 chunk 不發 answer_chunk，但 start/intent/metadata/done 框架仍完整。"""
    eng = _engine_streaming(["", "有內容", ""])
    events = await _collect(chat._conversational_sse(eng, decision=object(), request=None))
    types = [t for t, _ in events]
    assert types == ["start", "intent", "answer_chunk", "metadata", "done"]
    assert [d["chunk"] for t, d in events if t == "answer_chunk"] == ["有內容"]


@pytest.mark.req("testing-traceability:5.5")
async def test_sse_emits_error_event_on_stream_failure():
    """串流中途拋錯 → 收斂為 error 事件（不中斷成未定義狀態）。"""
    eng = MagicMock()

    async def _boom(decision):
        yield "開頭"
        raise RuntimeError("stream broke")

    eng.stream_answer = _boom
    events = await _collect(chat._conversational_sse(eng, decision=object(), request=None))
    types = [t for t, _ in events]
    assert types[0] == "start"
    assert types[-1] == "error"
    assert any(d.get("success") is False for t, d in events if t == "error")
