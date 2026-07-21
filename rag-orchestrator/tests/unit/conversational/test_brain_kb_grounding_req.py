"""unit：Brain search_kb 工具圈（spec brain-kb-grounding 元件 1｜R1.1/1.2/1.3/1.4/4.2/5.2）。

conversational_step 改 async 並掛載 search_kb 工具：
  - kb_search=None → 單次 json_object 呼叫，輸出與現行逐位一致（R1.3 回歸鎖）。
  - kb_search 提供 → 首呼帶 tools，回 tool_call → await kb_search → 續呼取最終 JSON（R1.1）。
  - 上限 MAX_TOOL_CALLS=1：模型連續要求 → 達限去 tools 強制收斂（R1.2）。
  - NO_MATCH → set_search_kb_status('miss')；命中 → 'hit'（R5.2）。
  - kb_search 拋錯／第二呼失敗 → conversational_step 回 None（R4.2 降級不建單）。
  - 最終 JSON 沿用既有驗證（action 列舉/型別/inline_answer/scope，R1.4）。
mock llm_provider，確定性 unit。
"""
import json

import pytest
from unittest.mock import MagicMock

from services import usage_metering as um
from services.llm_answer_optimizer import LLMAnswerOptimizer, NO_MATCH_SENTINEL

pytestmark = pytest.mark.unit


def _opt():
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    return opt


def _resp_toolcall(query, call_id="call_1"):
    """chat_completion 回傳：帶一個 search_kb tool_call（content=None）。"""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = "search_kb"
    tc.function.arguments = json.dumps({"query": query})
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    raw = MagicMock()
    raw.choices = [MagicMock(message=msg)]
    return {"content": None, "raw_response": raw, "usage": {}}


def _resp_final(obj):
    """chat_completion 回傳：最終 JSON（無 tool_calls）。"""
    msg = MagicMock()
    msg.content = json.dumps(obj)
    msg.tool_calls = None
    raw = MagicMock()
    raw.choices = [MagicMock(message=msg)]
    return {"content": json.dumps(obj), "raw_response": raw, "usage": {}}


@pytest.fixture(autouse=True)
def _clean_ctx(monkeypatch):
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    um._ctx.set(None)
    yield
    um._ctx.set(None)


# ════════════════════════════════════════════════════════════
# R1.3：kb_search=None → 單次呼叫、輸出與現行逐位一致（回歸鎖）
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:1.3")
async def test_no_kb_search_single_call_identical_output():
    opt = _opt()
    payload = {"action": "ask", "next_question": "發生多久了？", "extracted_fields": {"x": "1"}}
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(payload)})
    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "冷氣壞了")
    assert r["action"] == "ask"
    assert r["next_question"] == "發生多久了？"
    assert r["extracted_fields"] == {"x": "1"}
    assert r["scope"] == "stay"
    # 單次呼叫、且未帶 tools（現行行為）
    assert opt.llm_provider.chat_completion.call_count == 1
    _, kwargs = opt.llm_provider.chat_completion.call_args
    assert "tools" not in kwargs


@pytest.mark.req("brain-kb-grounding:1.3")
async def test_no_kb_search_unknown_action_still_none():
    """None 路徑的既有驗證不回歸：未知 action → None。"""
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(
        return_value={"content": json.dumps({"action": "submit", "extracted_fields": {}})})
    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "送出")
    assert r is None


# ════════════════════════════════════════════════════════════
# R1.1：命中路徑——首呼 tool_call → await kb_search → 續呼帶 tool result → 最終 JSON
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:1.1")
async def test_tool_call_then_final_json_with_hit():
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_toolcall("修繕費用歸屬"),
        _resp_final({"action": "ask", "next_question": "浴室嗎？",
                     "inline_answer": "自然損壞由房東負擔", "extracted_fields": {}}),
    ])
    seen = {}

    async def kb(q):
        seen["q"] = q
        return "自然損壞由房東負擔"

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}},
                                      "這要收費嗎", kb_search=kb)
    assert seen["q"] == "修繕費用歸屬"           # kb_search 收到模型擬的 query
    assert r["inline_answer"] == "自然損壞由房東負擔"
    assert r["next_question"] == "浴室嗎？"
    # 兩次呼叫：首呼帶 tools、續呼去 tools（達上限收斂）
    assert opt.llm_provider.chat_completion.call_count == 2
    first_kwargs = opt.llm_provider.chat_completion.call_args_list[0].kwargs
    second_kwargs = opt.llm_provider.chat_completion.call_args_list[1].kwargs
    assert "tools" in first_kwargs and first_kwargs["tool_choice"] == "auto"
    assert "tools" not in second_kwargs
    # 續呼 messages 帶入 assistant tool_call + tool 結果
    roles = [m["role"] for m in second_kwargs["messages"]]
    assert "tool" in roles


@pytest.mark.req("brain-kb-grounding:5.2")
async def test_hit_sets_search_kb_status_hit():
    opt = _opt()
    um.begin({"message": "m", "vendor_id": 2, "mode": "b2c", "session_id": "s"})
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_toolcall("費用"),
        _resp_final({"action": "converge", "converge_kind": "answer", "extracted_fields": {}}),
    ])

    async def kb(q):
        return "房東負擔"

    await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "費用", kb_search=kb)
    assert um._ctx.get().search_kb_status == "hit"


# ════════════════════════════════════════════════════════════
# R3.2/R5.2：NO_MATCH → set_search_kb_status('miss')，最終 JSON 仍解析
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:5.2")
async def test_no_match_sets_status_miss():
    opt = _opt()
    um.begin({"message": "m", "vendor_id": 2, "mode": "b2c", "session_id": "s"})
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_toolcall("冷門規定"),
        _resp_final({"action": "ask", "next_question": "還有其他問題嗎？", "extracted_fields": {}}),
    ])

    async def kb(q):
        return NO_MATCH_SENTINEL

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "問規定", kb_search=kb)
    assert um._ctx.get().search_kb_status == "miss"
    assert r["action"] == "ask"


# ════════════════════════════════════════════════════════════
# R1.2：上限——模型連續要求 tool_call，達 1 次後去 tools 強制收斂
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:1.2")
async def test_max_one_tool_call_forces_convergence():
    opt = _opt()
    # 首呼 tool_call；第二呼若仍給 tool_call 應被忽略（去 tools 後模型只能回 JSON）——
    # 這裡第二呼回 JSON，驗證恰好 2 次呼叫、kb_search 恰好 1 次。
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_toolcall("q1"),
        _resp_final({"action": "converge", "converge_kind": "answer", "extracted_fields": {}}),
    ])
    calls = {"n": 0}

    async def kb(q):
        calls["n"] += 1
        return "ans"

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x", kb_search=kb)
    assert calls["n"] == 1                        # kb_search 至多 1 次
    assert opt.llm_provider.chat_completion.call_count == 2
    assert r is not None


# ════════════════════════════════════════════════════════════
# R4.2：kb_search 拋錯 / 第二呼失敗 → conversational_step 回 None（降級不建單）
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:4.2")
async def test_kb_search_raises_returns_none():
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(side_effect=[_resp_toolcall("q")])

    async def kb(q):
        raise RuntimeError("retriever down")

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x", kb_search=kb)
    assert r is None


@pytest.mark.req("brain-kb-grounding:4.2")
async def test_second_call_failure_returns_none():
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_toolcall("q"),
        Exception("2nd call boom"),
    ])

    async def kb(q):
        return "ans"

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x", kb_search=kb)
    assert r is None


# ════════════════════════════════════════════════════════════
# R1.1：模型不呼叫工具（首呼即回 JSON）→ kb_search 未被呼叫、單次收斂
# ════════════════════════════════════════════════════════════
@pytest.mark.req("brain-kb-grounding:1.1")
async def test_model_declines_tool_single_call():
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_final({"action": "ask", "next_question": "多久了？", "extracted_fields": {}}),
    ])
    called = {"n": 0}

    async def kb(q):
        called["n"] += 1
        return "x"

    r = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "冷氣壞了", kb_search=kb)
    assert called["n"] == 0                        # 模型沒岔題就不查
    assert r["action"] == "ask"
    assert opt.llm_provider.chat_completion.call_count == 1


# ════════════════════════════════════════════════════════════
# R1.3/R3.2：prompt 契約——tool_note 僅在 kb_search 注入時附加（None 路徑 prompt 逐字一致）
# ════════════════════════════════════════════════════════════
def _capture_system_prompt(opt):
    """取最後一次 chat_completion 的 system message 內容。"""
    _, kwargs = opt.llm_provider.chat_completion.call_args
    for m in kwargs["messages"]:
        if m["role"] == "system":
            return m["content"]
    return ""


@pytest.mark.req("brain-kb-grounding:1.3")
async def test_none_path_prompt_has_no_tool_contract():
    """kb_search=None → prompt 不含 search_kb 工具契約（現行 prompt 逐字不變）。"""
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(
        return_value={"content": json.dumps({"action": "converge", "converge_kind": "answer",
                                              "extracted_fields": {}})})
    await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x")
    sysprompt = _capture_system_prompt(opt)
    assert "search_kb" not in sysprompt
    assert "知識查詢工具" not in sysprompt


@pytest.mark.req("brain-kb-grounding:3.2")
async def test_tool_path_prompt_carries_contract():
    """kb_search 提供 → prompt 含 search_kb 契約與 NO_MATCH 誠實回退指示。"""
    opt = _opt()
    opt.llm_provider.chat_completion = MagicMock(side_effect=[
        _resp_final({"action": "ask", "next_question": "多久了？", "extracted_fields": {}}),
    ])

    async def kb(q):
        return "x"

    await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "x", kb_search=kb)
    sysprompt = _capture_system_prompt(opt)
    assert "search_kb" in sysprompt
    assert "NO_MATCH" in sysprompt                 # 誠實回退契約在 prompt（R3.2）
