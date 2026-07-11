"""unit:brain 交易語義（conversational-repair 元件 1｜R3.1/R4.1）。

`conversational_step` 為交易面向長出第三種 action `confirm`（槽位收齊→出確認摘要，
收齊≠送出）與岔題即答欄位 `inline_answer`（使用者岔題問費用等，先答再接著收槽位）：
  - action='confirm' 合法解析透傳（confirm 不需 next_question/converge_kind）。
  - inline_answer 合法透傳；非 str 丟棄（絕不半吊子透傳）。
  - 未知 action（如 'submit'）→ None（舊行為保留：拒絕未知值，不寬鬆回退）。
  - action='ask' 無 next_question → None（既有行為不回歸）。
mock llm_provider，確定性 unit。
"""
import json

import pytest
from unittest.mock import MagicMock

from services.llm_answer_optimizer import LLMAnswerOptimizer

pytestmark = pytest.mark.unit


def _opt(llm_json: dict):
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(llm_json)})
    return opt


# ── action='confirm' 合法解析透傳（收齊→確認摘要）──
@pytest.mark.req("conversational-repair:4.1")
def test_confirm_action_passed_through():
    opt = _opt({"action": "confirm", "extracted_fields": {"urgency": "急"}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "蠻急的")
    assert r is not None
    assert r["action"] == "confirm"
    assert r["extracted_fields"] == {"urgency": "急"}


# ── confirm 無 next_question 仍合法（confirm 不需下一題）──
@pytest.mark.req("conversational-repair:4.1")
def test_confirm_without_next_question_is_valid():
    opt = _opt({"action": "confirm", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "好")
    assert r is not None
    assert r["action"] == "confirm"


# ── inline_answer 合法透傳（岔題先答）──
@pytest.mark.req("conversational-repair:3.1")
def test_inline_answer_passed_through():
    opt = _opt({"action": "ask", "next_question": "發生多久了？",
                "inline_answer": "牆內管線由業者負責", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "要自己出錢嗎")
    assert r["inline_answer"] == "牆內管線由業者負責"


# ── inline_answer 非 str → 丟棄（不半吊子透傳）──
@pytest.mark.req("conversational-repair:3.1")
def test_inline_answer_non_str_dropped():
    opt = _opt({"action": "ask", "next_question": "q",
                "inline_answer": {"bad": 1}, "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x")
    assert r is not None
    assert "inline_answer" not in r


# ── inline_answer 缺省 → 輸出不含該鍵（向後相容）──
@pytest.mark.req("conversational-repair:3.1")
def test_inline_answer_absent_no_key():
    opt = _opt({"action": "converge", "converge_kind": "answer", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x")
    assert "inline_answer" not in r


# ── 未知 action（'submit'）→ None（拒絕未知值，不寬鬆回退）──
@pytest.mark.req("conversational-repair:4.1")
def test_unknown_action_rejected():
    opt = _opt({"action": "submit", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "送出")
    assert r is None


# ── action='ask' 無 next_question → None（既有行為不回歸）──
@pytest.mark.req("conversational-repair:4.1")
def test_ask_without_next_question_still_none():
    opt = _opt({"action": "ask", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x")
    assert r is None
