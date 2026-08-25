"""unit：responsibility contract 的 structured delegation（slice 2）。

要鎖的命題：

> **轉交目標由 contract 的白名單決定，不是模型自由發揮。**

背景：`billing_anomaly → contract_closeout` 這條 delegation edge 原本只存在於 persona
的自然語言裡（實測要讀 LLM 輸出才發現），routing 層拿不到。本 slice 讓它成為結構化資料。
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from services.conversational_config import ConversationalConfig, _config_from_row
from services.llm_answer_optimizer import LLMAnswerOptimizer
from services.responsibility import allowed_delegates

pytestmark = pytest.mark.unit


def _cfg(delegates=None):
    return ConversationalConfig(
        key="billing_anomaly", persona_role="pm_billing_anomaly",
        topic_scope={"mode": "category", "category": "帳單異常"},
        responsibility={"delegates": [{"target": t} for t in (delegates or [])]})


# ── 契約解析 ──────────────────────────────────────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
def test_responsibility_parsed_from_metadata():
    cfg = _config_from_row(["pm_billing_anomaly"], {"conversational_config": {
        "key": "billing_anomaly",
        "responsibility": {"delegates": [{"target": "contract_closeout"}]}}})
    assert allowed_delegates(cfg) == ("contract_closeout",)


@pytest.mark.req("face-exit-before-grounding:1")
def test_delegates_absent_is_empty_not_error():
    """未宣告 responsibility → 空白名單（向後相容，既有面向零影響）。"""
    assert allowed_delegates(ConversationalConfig(key="x")) == ()


@pytest.mark.req("face-exit-before-grounding:1")
def test_delegates_accepts_plain_strings_and_dedupes():
    cfg = ConversationalConfig(key="x", responsibility={
        "delegates": ["a", {"target": "b"}, {"target": "a"}, {"nope": 1}, ""]})
    assert allowed_delegates(cfg) == ("a", "b")


# ── brain 側：白名單強制 ──────────────────────────────────────────────────────
def _optimizer(payload):
    opt = LLMAnswerOptimizer(llm_provider=MagicMock())
    opt.llm_provider.chat_completion = MagicMock(
        return_value={"content": json.dumps(payload, ensure_ascii=False)})
    return opt


async def _step(opt, **kw):
    return await opt.conversational_step("RULES", "CTX", {"collected_fields": {},
                                                          "asked_count": 0}, "問句", **kw)


@pytest.mark.req("face-exit-before-grounding:1")
async def test_delegate_kept_when_in_whitelist():
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "switch",
                      "delegate_facet_key": "contract_closeout"})
    out = await _step(opt, delegates=["contract_closeout"])
    assert out["scope"] == "switch" and out["delegate_facet_key"] == "contract_closeout"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_invented_delegate_is_dropped():
    """模型自創 Face key → **丟棄**（不得讓它決定候選集合）。"""
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "switch",
                      "delegate_facet_key": "totally_made_up_face"})
    out = await _step(opt, delegates=["contract_closeout"])
    assert out["scope"] == "switch" and "delegate_facet_key" not in out


@pytest.mark.req("face-exit-before-grounding:1")
async def test_delegate_dropped_when_scope_is_stay():
    """stay 時指定轉交沒有意義 → 丟棄（避免 resolver 誤跳）。"""
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "stay",
                      "delegate_facet_key": "contract_closeout"})
    out = await _step(opt, delegates=["contract_closeout"])
    assert out["scope"] == "stay" and "delegate_facet_key" not in out


@pytest.mark.req("face-exit-before-grounding:1")
async def test_delegate_dropped_when_no_whitelist_declared():
    """面向未宣告 delegates → 即使模型回了也丟棄。"""
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "switch",
                      "delegate_facet_key": "contract_closeout"})
    out = await _step(opt)
    assert "delegate_facet_key" not in out


# ── 回歸鎖：未提供 delegates 時 prompt 逐字不變 ─────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_prompt_unchanged_when_no_delegates():
    seen = {}

    def capture(**kw):
        seen.setdefault("calls", []).append(kw["messages"][0]["content"])
        return {"content": json.dumps({"action": "ask", "next_question": "q"})}

    opt = LLMAnswerOptimizer(llm_provider=MagicMock())
    opt.llm_provider.chat_completion = MagicMock(side_effect=lambda **kw: capture(**kw))
    await _step(opt)                       # 不帶 delegates
    await _step(opt, delegates=[])         # 空白名單亦視同不帶
    base, empty = seen["calls"]
    assert base == empty, "空白名單不得改變 prompt"
    assert "轉交對象" not in base, "未宣告 delegates 時不得注入 delegation 段落"

    await _step(opt, delegates=["contract_closeout"])
    assert "轉交對象" in seen["calls"][2] and "contract_closeout" in seen["calls"][2]


# ── `when`：語義條件（v2 修法）─────────────────────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
def test_delegate_specs_carry_when_and_allowed_keys_ignore_it():
    from services.responsibility import allowed_delegates as keys, delegate_specs
    cfg = ConversationalConfig(key="x", responsibility={"delegates": [
        {"target": "billing_anomaly", "when": "帳單金額組成/看不到帳單"},
        {"target": "contract_closeout"}, "plain_key"]})
    assert delegate_specs(cfg) == (("billing_anomaly", "帳單金額組成/看不到帳單"),
                                   ("contract_closeout", None), ("plain_key", None))
    assert keys(cfg) == ("billing_anomaly", "contract_closeout", "plain_key")


@pytest.mark.req("face-exit-before-grounding:1")
async def test_when_is_rendered_into_the_prompt():
    """第一次 gated validation 3/3 停在第一跳的直接修法：把語義條件寫進 prompt。"""
    seen = {}

    def capture(**kw):
        seen["sys"] = kw["messages"][0]["content"]
        return {"content": json.dumps({"action": "ask", "next_question": "q"})}

    opt = LLMAnswerOptimizer(llm_provider=MagicMock())
    opt.llm_provider.chat_completion = MagicMock(side_effect=lambda **kw: capture(**kw))
    await _step(opt, delegates=[("billing_anomaly", "帳單金額組成/看不到帳單")])
    assert "billing_anomaly（帳單金額組成/看不到帳單）" in seen["sys"]


@pytest.mark.req("face-exit-before-grounding:1")
async def test_when_does_not_widen_the_whitelist():
    """`when` 只增加理解——**不得**讓模型獲得自創 destination 的能力。"""
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "switch",
                      "delegate_facet_key": "帳單金額組成/看不到帳單"})   # 拿 when 當 key
    out = await _step(opt, delegates=[("billing_anomaly", "帳單金額組成/看不到帳單")])
    assert "delegate_facet_key" not in out


@pytest.mark.req("face-exit-before-grounding:1")
async def test_tuple_form_still_validates_against_target_only():
    opt = _optimizer({"action": "ask", "next_question": "q", "scope": "switch",
                      "delegate_facet_key": "billing_anomaly"})
    out = await _step(opt, delegates=[("billing_anomaly", "帳單金額組成/看不到帳單")])
    assert out["delegate_facet_key"] == "billing_anomaly"
