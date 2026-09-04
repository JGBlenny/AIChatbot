"""unit 層：brain 輸出的 `fact_class`（design.md 元件 4）。需求 3.1、3.2、3.4。

strict schema 必列 required；解析層唯一正規化點；非法／缺值 → other；⛔ 不因新欄位讓既有 ask／converge 500。
"""
import json

import pytest
from unittest.mock import MagicMock

from services.llm_answer_optimizer import CONVERSATIONAL_STEP_SCHEMA, LLMAnswerOptimizer
from services.presales_gate import FactClass

pytestmark = pytest.mark.unit

SEVEN = ["customer_reference", "pricing", "contract_sla", "compliance", "security", "feature", "other"]


def _base(**over):
    d = {"action": "converge", "converge_kind": "answer", "scope": "stay", "face": "",
         "delegate_facet_key": "", "next_question": "", "inline_answer": "", "extracted_fields": []}
    d.update(over)
    return d


# ── schema（R3.1）──────────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.1")
def test_schema_requires_fact_class_with_closed_enum():
    body = CONVERSATIONAL_STEP_SCHEMA["json_schema"]["schema"]
    assert "fact_class" in body["required"] and "fact_class" in body["properties"]
    assert body["properties"]["fact_class"]["enum"] == SEVEN
    assert set(body["properties"]) == set(body["required"])          # strict：properties 與 required 逐一對應


# ── 解析層（R3.2）──────────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.2")
@pytest.mark.parametrize("raw", SEVEN)
def test_parse_keeps_exact_enum_value(raw):
    r = LLMAnswerOptimizer._parse_conversational_step(_base(fact_class=raw))
    assert r is not None and r.payload is not None
    assert r.payload["fact_class"] is FactClass(raw)


@pytest.mark.req("presales-grounding-gate:3.2")
@pytest.mark.parametrize("raw", ["Pricing", "price", "", None, 7, ["pricing"]])
def test_parse_normalizes_invalid_to_other(raw):
    r = LLMAnswerOptimizer._parse_conversational_step(_base(fact_class=raw))
    assert r.payload["fact_class"] is FactClass.other


@pytest.mark.req("presales-grounding-gate:3.2")
def test_parse_missing_key_is_other():
    """`BRAIN_STRICT_SCHEMA` 關閉（json_object）時模型可能不給此鍵 ⇒ other，⛔ 不 KeyError。"""
    d = _base(); d.pop("fact_class", None)
    r = LLMAnswerOptimizer._parse_conversational_step(d)
    assert r.payload["fact_class"] is FactClass.other


# ── 既有流程不受影響（R3.4）─────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.4")
def test_ask_action_still_valid_and_carries_fact_class():
    r = LLMAnswerOptimizer._parse_conversational_step(_base(action="ask", next_question="請問戶數？", fact_class="other"))
    assert r.payload["action"] == "ask" and r.payload["fact_class"] is FactClass.other


@pytest.mark.req("presales-grounding-gate:3.4")
def test_action_out_of_range_still_rejected_not_crashed():
    r = LLMAnswerOptimizer._parse_conversational_step(_base(action="fly", fact_class="pricing"))
    assert r is not None and r.payload is None and r.reject_reason == "action_out_of_range"


@pytest.mark.req("presales-grounding-gate:3.4")
def test_non_dict_still_returns_none():
    assert LLMAnswerOptimizer._parse_conversational_step("not json") is None


@pytest.mark.req("presales-grounding-gate:3.4")
async def test_end_to_end_step_result_exposes_fact_class(monkeypatch):
    """經 conversational_step_result（假 LLM 回 strict JSON）⇒ payload 帶 enum，既有鍵不變。"""
    monkeypatch.delenv("BRAIN_STRICT_SCHEMA", raising=False)
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(_base(fact_class="security"))})
    r = await opt.conversational_step_result(rules_text="r", system_context_md="s", state={}, user_message="資料放哪")
    assert r is not None and r.payload["fact_class"] is FactClass.security
    assert r.payload["action"] == "converge" and r.payload["converge_kind"] == "answer"
