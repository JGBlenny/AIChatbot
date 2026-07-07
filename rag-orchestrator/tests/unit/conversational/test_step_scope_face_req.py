"""unit:brain 輸出 scope/face 訊號（mid-session-switch 方案B｜元件 3.1）。

`conversational_step` 於既有輸出上多帶 scope(stay|switch) 與 face：
  - scope 正規化：缺省/越界 → 'stay'（向後相容、防越界）。
  - face 原樣帶出（引擎再依面向集合驗證）。
  - 有給 faces 清單時注入 prompt（供 brain 從中選面向）。
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


# ── scope='switch' 原樣帶出 ──
@pytest.mark.req("mid-session-switch:3.1")
def test_scope_switch_passed_through():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}, "scope": "switch"})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "我帳單怎麼繳")
    assert r["scope"] == "switch"


# ── scope 缺省 → 'stay'（向後相容）──
@pytest.mark.req("mid-session-switch:3.1")
def test_scope_defaults_to_stay():
    opt = _opt({"action": "converge", "converge_kind": "answer", "extracted_fields": {}})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "查我合約 678")
    assert r["scope"] == "stay"


# ── scope 越界值 → 正規化為 'stay'（防越界）──
@pytest.mark.req("mid-session-switch:3.1")
def test_scope_invalid_normalized_to_stay():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}, "scope": "亂填"})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x")
    assert r["scope"] == "stay"


# ── face 原樣帶出（引擎再驗證面向集合）──
@pytest.mark.req("mid-session-switch:3.1")
def test_face_passed_through():
    opt = _opt({"action": "converge", "converge_kind": "answer", "extracted_fields": {}, "face": "違約金"})
    r = opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "提前解約違約金怎算")
    assert r["face"] == "違約金"


# ── 有 faces 清單 → 注入 prompt（供 brain 選面向）──
@pytest.mark.req("mid-session-switch:3.1")
def test_faces_injected_into_prompt():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}})
    opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x", faces=["狀態判斷", "違約金"])
    sent = opt.llm_provider.chat_completion.call_args.kwargs["messages"]
    joined = "\n".join(m["content"] for m in sent)
    assert "狀態判斷" in joined and "違約金" in joined
