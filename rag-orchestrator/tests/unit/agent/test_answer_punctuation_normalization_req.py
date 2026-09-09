"""unit：`out.answer` 唯一組裝點套句末標點正規化（T4｜Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-walkthrough-fixes-batch2-20260909.md`
§5、H7）。

治的病灶：模型逐句輸出偶爾在句尾標點後又補一個句號，`"".join(s.text ...)`
拼接後變成「嗎？。」這種畸形結尾（走查實測）。這裡驅動一次完整的
`AgentRuntime.run_turn`，證明正規化真的套在 `TurnResult.answer` 上
（⛔ 不是只測 `text_norm.py` 這個純函式本身——那是 `test_text_norm_req.py` 的事）。
"""
from __future__ import annotations

import json

import pytest

from tests.unit.agent.test_runtime_req import (
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _identity,
    _runtime,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:T4"),
]


def _answer_response(text: str):
    """同 `test_runtime_req._final_response`，只是允許自訂句尾文字
    （`_final_response` 的 `answer` 參數不夠用來塞畸形標點）。"""
    payload = {
        "kind": "answer",
        "sentences": [{"text": text, "kind": "greeting", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


async def test_run_turn_collapses_terminal_punctuation_run_at_the_join_site():
    provider = FakeProvider([_answer_response("需要我幫你查一下嗎？。")])
    runtime = _runtime(provider=provider, registry=FakeRegistry(), verifier=FakeVerifier())

    result = await runtime.run_turn(_identity(), "你好", {})

    assert result.kind == "answer"
    assert result.answer == "需要我幫你查一下嗎？"


async def test_run_turn_leaves_single_terminal_punctuation_untouched():
    """正對照：沒有連續標點的句子完全不受影響——證明上一條不是巧合。"""
    provider = FakeProvider([_answer_response("需要我幫你查一下嗎？")])
    runtime = _runtime(provider=provider, registry=FakeRegistry(), verifier=FakeVerifier())

    result = await runtime.run_turn(_identity(), "你好", {})

    assert result.answer == "需要我幫你查一下嗎？"
