"""unit：conversational-step 的 **strict output contract**（業主 2026-08-26 裁定）。

P3 第 2 次付費執行 3/3 都踩到 `action=ask` 卻**沒有 next_question**——
`json_object` 只保證「是 JSON」，欄位在不在全靠模型自律，mini 不可靠。
strict `json_schema` 把形狀交給 **API 契約**強制。

四層分工在本檔逐條釘住，**不得混在一起**：

```text
Structured Outputs      → 保證 shape（欄位在不在、值域對不對）
mini                    → 判 semantic intent
responsibility contract → singleton machine mapping
parser                  → 抓 cross-field semantic contradiction
```
"""
import json

import pytest
from unittest.mock import MagicMock

from services.llm_answer_optimizer import (
    CONVERSATIONAL_STEP_SCHEMA,
    LLMAnswerOptimizer,
)

pytestmark = pytest.mark.unit


def _opt(llm_json: dict):
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(llm_json)})
    return opt


# ════════ schema 本身 ════════

@pytest.mark.req("conversational-routing-execution:5.2")
def test_schema_is_strict_and_requires_every_field():
    js = CONVERSATIONAL_STEP_SCHEMA["json_schema"]
    assert js["strict"] is True
    body = js["schema"]
    assert body["additionalProperties"] is False
    # 業主列的 7 個 ＋ inline_answer（交易面向的岔題即答；漏掉等於靜默停用該能力）
    assert set(body["required"]) == {
        "action", "scope", "face", "delegate_facet_key",
        "extracted_fields", "next_question", "converge_kind", "inline_answer"}
    assert set(body["properties"]) == set(body["required"]), \
        "strict 模式下 properties 與 required 必須逐一對應"


@pytest.mark.req("conversational-routing-execution:5.2")
def test_schema_pins_the_two_enums():
    props = CONVERSATIONAL_STEP_SCHEMA["json_schema"]["schema"]["properties"]
    assert props["action"]["enum"] == ["ask", "converge", "confirm"]
    assert props["scope"]["enum"] == ["stay", "switch"]


@pytest.mark.req("conversational-routing-execution:5.2")
def test_nested_object_is_also_strict():
    """strict 模式要求**每個** object 都 additionalProperties:false 且列全 required。"""
    item = CONVERSATIONAL_STEP_SCHEMA["json_schema"]["schema"]["properties"]["extracted_fields"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"field", "value"} == set(item["properties"])


# ════════ 真的送到 provider ════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_evaluator_sends_strict_schema(monkeypatch):
    monkeypatch.delenv("BRAIN_STRICT_SCHEMA", raising=False)
    opt = _opt({"action": "converge", "converge_kind": "answer", "scope": "stay",
                "face": "", "delegate_facet_key": "", "next_question": "",
                "inline_answer": "", "extracted_fields": []})
    await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息")
    fmt = opt.llm_provider.chat_completion.call_args.kwargs["response_format"]
    assert fmt is CONVERSATIONAL_STEP_SCHEMA


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_flag_off_falls_back_to_json_object(monkeypatch):
    """可回退：改的是 production 的 provider 呼叫形狀，必須留得住退路。"""
    monkeypatch.setenv("BRAIN_STRICT_SCHEMA", "false")
    opt = _opt({"action": "converge", "converge_kind": "answer", "extracted_fields": {}})
    await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息")
    assert opt.llm_provider.chat_completion.call_args.kwargs["response_format"] == {"type": "json_object"}


# ════════ extracted_fields 的兩種形狀 ════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_array_shape_is_restored_to_dict():
    """API 邊界用 `[{field,value}]`（strict 不允許自由 key 的物件）；**內部契約仍是 dict**。"""
    opt = _opt({"action": "converge", "converge_kind": "answer", "scope": "stay",
                "face": "", "delegate_facet_key": "", "next_question": "", "inline_answer": "",
                "extracted_fields": [{"field": "bill_ref", "value": "678"},
                                     {"field": "month", "value": "2026-08"}]})
    r = await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息")
    assert r.payload["extracted_fields"] == {"bill_ref": "678", "month": "2026-08"}


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_dict_shape_still_accepted():
    """旗標關閉或非 OpenAI provider 時形狀本來就是 dict——不得被轉換破壞（零回歸）。"""
    opt = _opt({"action": "converge", "converge_kind": "answer",
                "extracted_fields": {"bill_ref": "678"}})
    r = await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息")
    assert r.payload["extracted_fields"] == {"bill_ref": "678"}


# ════════ parser **不得**因為有了 schema 就放寬 ════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_empty_next_question_is_still_a_semantic_rejection():
    """`action=ask` ＋ `next_question=""` **structurally 合 schema**，但違反產品契約。

    ⚠️ 這正是分層的意義：schema failure 屬 API 層，cross-field 矛盾屬 parser 層。
    負向鎖：**不准默默當成正常 StepResult**。
    """
    opt = _opt({"action": "ask", "next_question": "", "scope": "switch",
                "face": "", "delegate_facet_key": "", "converge_kind": "",
                "inline_answer": "", "extracted_fields": []})
    r = await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息")
    assert r.payload is None, "空 next_question 被當成正常輸出——parser 被放寬了"
    assert r.reject_reason == "missing_next_question"
    assert r.scope == "switch", "scope 仍須保住（任務 8 的不變量）"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_empty_delegate_still_reported_as_missing_for_singleton():
    """schema 保證鍵存在，值仍可能是空字串——singleton 決定性補值**不得**被移除。"""
    opt = _opt({"action": "ask", "next_question": "q", "scope": "switch",
                "face": "", "delegate_facet_key": "", "converge_kind": "",
                "inline_answer": "", "extracted_fields": []})
    r = await opt.conversational_step_result("R", "S", {"collected_fields": {}}, "訊息",
                                             delegates=["billing_anomaly"])
    assert r.delegate_facet_key is None and r.delegate_drop_reason == "missing"
