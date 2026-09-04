"""unit 層：合成 prompt 帶上一輪 Q/A（design.md 元件 5）。需求 5.2、5.3。

`prev_turn=None` 時 prompt 必須與改前逐字相同（既有三處直呼不受影響）。
"""
import inspect
from unittest.mock import MagicMock

import pytest

from services.llm_answer_optimizer import LLMAnswerOptimizer

pytestmark = pytest.mark.unit
PREV = {"u": "舊系統的資料能匯進來嗎？", "a": "可以透過批次匯入表格匯入。"}


def _opt():
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": "答"})
    return opt


@pytest.mark.req("presales-grounding-gate:5.2")
def test_prev_turn_block_is_added_only_when_given():
    opt = _opt()
    base = opt._build_presales_synth("知識", None, "md", "那物件跟合約呢？", "suppress")
    with_prev = opt._build_presales_synth("知識", None, "md", "那物件跟合約呢？", "suppress", prev_turn=PREV)
    up_base, up_prev = base[0][1]["content"], with_prev[0][1]["content"]
    assert "【上一輪】" not in up_base
    assert "【上一輪】" in up_prev and PREV["u"] in up_prev and PREV["a"] in up_prev
    assert base[1:] == with_prev[1:]                                       # model／temperature 不因此改變


@pytest.mark.req("presales-grounding-gate:5.3")
def test_prev_turn_block_states_intent_continuity_and_no_topic_swap():
    opt = _opt()
    up = opt._build_presales_synth("知識", None, "md", "那物件跟合約呢？", "suppress", prev_turn=PREV)[0][1]["content"]
    assert "延續上一輪的動作意圖" in up and "這部分我沒有資料" in up and "不得換一組功能" in up


@pytest.mark.req("presales-grounding-gate:5.2")
def test_default_signature_is_backward_compatible():
    for fn in (LLMAnswerOptimizer._build_presales_synth, LLMAnswerOptimizer.synthesize_presales_answer,
               LLMAnswerOptimizer.synthesize_presales_answer_stream):
        p = inspect.signature(fn).parameters["prev_turn"]
        assert p.default is None and p.kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.req("presales-grounding-gate:5.2")
def test_synthesize_passes_prev_turn_to_prompt():
    opt = _opt()
    opt.synthesize_presales_answer("知識", None, "md", "那物件跟合約呢？", "suppress", prev_turn=PREV)
    sent = opt.llm_provider.chat_completion.call_args.kwargs["messages"][1]["content"]
    assert "【上一輪】" in sent and PREV["u"] in sent


@pytest.mark.req("presales-grounding-gate:2.3")
def test_fact_answers_carry_item_by_item_instruction():
    """e2e 回測：多項目問題被 LLM 用「等／都」補齊 ⇒ 事實型（suppress）合成一律帶逐項對照指令；推薦型（force）不帶。"""
    opt = _opt()
    sup = opt._build_presales_synth("知識", None, "md", "房東租客合約帳單能匯嗎", "suppress")[0][1]["content"]
    frc = opt._build_presales_synth("知識", None, "md", "適合我嗎", "force")[0][1]["content"]
    assert "【逐項對照】" in sup and "這部分我沒有資料" in sup and "不得把某一項目的能力推廣" in sup
    assert "【逐項對照】" in frc                                    # 推薦型也會順著功能索引補齊清單 ⇒ 一樣帶


@pytest.mark.req("presales-grounding-gate:5.2")
def test_prev_turn_with_empty_strings_is_ignored():
    opt = _opt()
    up = opt._build_presales_synth("知識", None, "md", "Q", "suppress", prev_turn={"u": "", "a": ""})[0][1]["content"]
    assert "【上一輪】" not in up
