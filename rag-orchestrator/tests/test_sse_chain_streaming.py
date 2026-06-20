"""
SSE streaming verification for chained response (form-chaining task 6.3).
Feature: form-chaining
Task: 6.3 - 串接合併回應於串流模式正確輸出（answer + 旗標）

需求：3.3

驗證串接 turn 的 form_result 經 _convert_form_result_to_response → stream_response_wrapper
後，SSE 事件流能完整還原合併 answer 並帶上正確旗標/欄位中繼資料（設計元件 5：免改碼，僅驗證）。
"""

import json
import os

os.environ.setdefault("DB_HOST", "localhost")

import sys

import pytest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))

from routers.chat import (  # noqa: E402
    VendorChatRequest,
    _convert_form_result_to_response,
    stream_response_wrapper,
)
import routers.chat as chat_module  # noqa: E402


# 模擬 _complete_form 串接 turn 的回傳（合併 answer + 旗標契約）
SOURCE_ANSWER = "永豐的金流不是在 JGB 裡申請，而是先向永豐銀行申請收款服務。"
FOLLOWUP_PROMPT = (
    "📝 **金流追問選單**\n\n還想了解什麼？\n1. 手續費誰負擔\n2. 能不能綁多家\n3. 怎麼換金流商"
    "\n\n（或輸入「**取消**」結束填寫）"
)
MERGED_ANSWER = f"{SOURCE_ANSWER}\n\n---\n\n{FOLLOWUP_PROMPT}"


def _chained_form_result():
    return {
        "answer": MERGED_ANSWER,
        "form_completed": False,
        "form_triggered": True,
        "form_id": "payment_gateway_followup",
        "current_field": "followup_topic",
        "current_field_type": "select",
        "quick_replies": [
            {"text": "手續費誰負擔", "value": "fee", "style": "default"},
            {"text": "能不能綁多家", "value": "multi", "style": "default"},
            {"text": "怎麼換金流商", "value": "switch", "style": "default"},
        ],
        "next_form_id": "payment_gateway_followup",
        "submission_id": None,
        "collected_data": {"gateway": "sinopac"},
    }


async def _collect_events(response_dict):
    events = []
    async for raw in stream_response_wrapper(response_dict):
        # SSE 格式：event: <type>\ndata: <json>\n\n
        lines = raw.strip().split("\n")
        etype = lines[0].replace("event: ", "")
        data = json.loads(lines[1].replace("data: ", ""))
        events.append((etype, data))
    return events


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """串流每 token sleep 15ms；測試中改為 no-op 以加速。"""
    async def _noop(*_a, **_k):
        return None
    monkeypatch.setattr(chat_module.asyncio, "sleep", _noop)


@pytest.mark.asyncio
async def test_chained_response_streams_merged_answer_and_flags():
    # 經真實轉換層產生 response dict
    req = VendorChatRequest(message="永豐", session_id="sse-test", vendor_id=1)
    response = _convert_form_result_to_response(_chained_form_result(), req)
    events = await _collect_events(response.dict())

    etypes = [e[0] for e in events]
    assert "start" in etypes and "done" in etypes

    # 1. 還原 answer：所有 answer_chunk 串接 == 合併 answer（含分隔線 + 追問選單）
    reassembled = "".join(
        d["chunk"] for t, d in events if t == "answer_chunk"
    )
    assert reassembled == MERGED_ANSWER
    assert "\n\n---\n\n" in reassembled
    assert "手續費誰負擔" in reassembled

    # 2. metadata 事件帶上串接旗標契約
    meta = next(d for t, d in events if t == "metadata")
    assert meta["form_triggered"] is True
    assert meta["form_completed"] is False
    assert meta["form_id"] == "payment_gateway_followup"
    assert meta["current_field_type"] == "select"
    assert len(meta["quick_replies"]) == 3

    # 3. form_field 事件帶上欄位型別 + quick_replies（前端渲染選單按鈕）
    form_field = next(d for t, d in events if t == "form_field")
    assert form_field["current_field_type"] == "select"
    assert [q["value"] for q in form_field["quick_replies"]] == ["fee", "multi", "switch"]
