"""
單元測試：對話 brain 與引擎決策邏輯（option-routing task 10.5 / R14-R19）。

A. LLMAnswerOptimizer.conversational_step：JSON 解析/驗證、越界輸出被拒、規則缺失回 None。
B. ConversationalEngine.handle 決策邏輯：
   - 推薦型收斂但基本資訊不足 → 改先補問（不收斂）
   - 推薦型且基本資訊足 → 收斂並關閉會話
   - 事實型（answer）收斂 → 答完不關閉會話（保留上下文）
   - 提問達硬上限 MAX_ASKS → 強制收斂

以 patch/AsyncMock 隔離 LLM 與 DB。
"""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.llm_answer_optimizer as llm_mod  # noqa: E402
from services.llm_answer_optimizer import LLMAnswerOptimizer  # noqa: E402
from services.conversational_engine import ConversationalEngine, MAX_ASKS  # noqa: E402
from services.conversational_config import PRESALES_CONFIG  # noqa: E402


# ============ A. conversational_step（brain） ============

def _make_optimizer(content):
    with patch.object(llm_mod, "get_llm_provider", return_value=MagicMock()):
        opt = LLMAnswerOptimizer()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": content})
    return opt


def _step(content, rules="規則", md="md", state=None, msg="哈囉"):
    opt = _make_optimizer(content)
    return opt.conversational_step(rules, md, state or {"collected_fields": {}, "asked_count": 0}, msg)


def test_step_valid_ask():
    out = _step(json.dumps({"extracted_fields": {"identity": "個人房東"},
                            "action": "ask", "next_question": "管幾戶？"}))
    assert out["action"] == "ask"
    assert out["next_question"] == "管幾戶？"
    assert out["extracted_fields"]["identity"] == "個人房東"


def test_step_valid_converge():
    out = _step(json.dumps({"extracted_fields": {}, "action": "converge",
                            "converge_kind": "recommend", "next_question": "備用"}))
    assert out["action"] == "converge"
    assert out["converge_kind"] == "recommend"


def test_step_invalid_action_rejected():
    """越界 action → None。"""
    assert _step(json.dumps({"action": "foobar", "next_question": "x"})) is None


def test_step_ask_without_next_question_rejected():
    assert _step(json.dumps({"action": "ask", "extracted_fields": {}})) is None


def test_step_extracted_fields_coerced_to_dict():
    out = _step(json.dumps({"action": "converge", "converge_kind": "answer",
                            "extracted_fields": "壞掉的型別"}))
    assert out["extracted_fields"] == {}


def test_step_empty_rules_returns_none():
    opt = _make_optimizer(json.dumps({"action": "ask", "next_question": "x"}))
    assert opt.conversational_step("", "md", {"collected_fields": {}, "asked_count": 0}, "hi") is None


def test_step_bad_json_returns_none():
    assert _step("這不是 JSON") is None


# ============ B. ConversationalEngine.handle 決策邏輯 ============

def _engine(step_return):
    eng = ConversationalEngine(
        db_pool=MagicMock(),
        optimizer=MagicMock(),
        retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="md"),
        rules_loader=AsyncMock(return_value="規則"),
    )
    eng.optimizer.conversational_step = MagicMock(return_value=step_return)
    eng.optimizer.synthesize_presales_answer = MagicMock(return_value="合成內容")
    eng._save = AsyncMock()
    eng._close = AsyncMock()
    # 隔離檢索：converge 取 grounding 改 mock（回 grounding/ctx/cta_mode）
    eng._converge_grounding = AsyncMock(return_value=("grounding", None, "force"))
    return eng


async def _run(eng, state):
    eng.get_state = AsyncMock(return_value=state)
    return await eng.handle("sess", "u", 0, "訊息", config=PRESALES_CONFIG, start_if_absent=False)


@pytest.mark.asyncio
async def test_recommend_without_basic_info_flips_to_ask():
    """推薦型收斂但缺基本資訊 → 改先補問，不收斂、不關會話、不合成。"""
    eng = _engine({"action": "converge", "converge_kind": "recommend",
                   "next_question": "請問您的身分是？", "extracted_fields": {}})
    out = await _run(eng, {"collected_fields": {}, "asked_count": 1})
    assert out["converged"] is False
    assert out["answer"] == "請問您的身分是？"
    eng._converge_grounding.assert_not_awaited()
    eng._close.assert_not_awaited()
    eng._save.assert_awaited()


@pytest.mark.asyncio
async def test_recommend_with_basic_info_converges():
    """推薦型且已具備 identity+scale → 收斂；**不關閉會話**（保留上下文供後續追問），改 _save。"""
    eng = _engine({"action": "converge", "converge_kind": "recommend",
                   "next_question": "備用", "extracted_fields": {}})
    out = await _run(eng, {"collected_fields": {"identity": "個人房東", "scale": "20"},
                           "asked_count": 2})
    assert out["converged"] is True
    assert out["answer"] == "合成內容"
    eng._converge_grounding.assert_awaited_once()
    eng._close.assert_not_awaited()
    eng._save.assert_awaited()


@pytest.mark.asyncio
async def test_answer_kind_does_not_close_session():
    """事實型收斂（answer）→ 答完不關閉會話（保留上下文），converged=False。"""
    eng = _engine({"action": "converge", "converge_kind": "answer",
                   "next_question": "備用", "extracted_fields": {}})
    out = await _run(eng, {"collected_fields": {}, "asked_count": 1})
    assert out["converged"] is False
    assert out["answer"] == "合成內容"
    eng._converge_grounding.assert_awaited_once()
    eng._close.assert_not_awaited()
    eng._save.assert_awaited()


@pytest.mark.asyncio
async def test_ask_cap_forces_converge_at_max():
    """提問達硬上限 MAX_ASKS → ask 被強制改為收斂。"""
    eng = _engine({"action": "ask", "next_question": "再問一題", "extracted_fields": {}})
    out = await _run(eng, {"collected_fields": {}, "asked_count": MAX_ASKS})
    assert out["converged"] is True
    eng._converge_grounding.assert_awaited_once()
    eng._close.assert_not_awaited()  # 收斂不關閉會話（保留上下文）


@pytest.mark.asyncio
async def test_brain_failure_first_turn_closes_session():
    """brain 回 None 且為首輪（asked_count=0）→ 關閉殘留會話、回 None 降級。"""
    eng = _engine(None)
    out = await _run(eng, {"collected_fields": {}, "asked_count": 0})
    assert out is None
    eng._close.assert_awaited_once()
