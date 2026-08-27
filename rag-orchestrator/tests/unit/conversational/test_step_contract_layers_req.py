"""unit：`conversational_step` 契約分層（任務 8／需求 5.2）。

修的缺陷：`action` 越界時舊碼 `return None`，把**同一包裡正確的 `scope=switch`
一起丟掉**——實測 brain 5/5 正確輸出 `scope=switch` 全遭丟棄，呼叫端只看得到
「引擎降級」，看不到「使用者已離題、該換面向」。

三條不變量（本檔逐條鎖住）：
  ① `payload` 非 None ⇒ `payload['action'] ∈ VALID_ACTIONS`，**永不出現 action=None 或越界值**
  ② 解析結果非 None ⇒ `scope ∈ {'stay','switch'}` 永遠有值
  ③ 相容層 `conversational_step()` 與改動前**逐位一致**
"""
import json

import pytest
from unittest.mock import MagicMock

from services.llm_answer_optimizer import LLMAnswerOptimizer, StepResult

pytestmark = pytest.mark.unit


def _opt(llm_json: dict):
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(llm_json)})
    return opt


async def _step(llm_json: dict, **kw):
    return await _opt(llm_json).conversational_step_result(
        "RULES", "SYS", {"collected_fields": {}}, "使用者訊息", **kw)


# ════════ 8.1 解析層：先正規化 scope，再驗 action ════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_invalid_action_keeps_scope_switch():
    """**本任務的核心**：action 越界（模型把 'switch' 填進 action）時，

    payload 為 None，但 scope **仍然是 switch**——舊碼會把兩者一起丟掉。
    """
    r = await _step({"action": "switch", "scope": "switch", "extracted_fields": {}})
    assert isinstance(r, StepResult)
    assert r.payload is None
    assert r.scope == "switch"
    assert r.reject_reason == "action_out_of_range"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_invalid_action_with_stay_scope_still_reports_stay():
    r = await _step({"action": "bogus", "extracted_fields": {}})
    assert r.payload is None and r.scope == "stay"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_payload_never_carries_invalid_action():
    """不變量①：payload 存在即代表 action 合法——**不引入 action=None 的半合法狀態**。"""
    for bad in ("switch", "", None, 123, "ASK"):
        r = await _step({"action": bad, "scope": "switch", "extracted_fields": {}})
        assert r.payload is None, f"action={bad!r} 不該產生 payload"
    for good in LLMAnswerOptimizer.VALID_ACTIONS:
        body = {"action": good, "extracted_fields": {}}
        if good == "ask":
            body["next_question"] = "q"
        r = await _step(body)
        assert r.payload is not None and r.payload["action"] in LLMAnswerOptimizer.VALID_ACTIONS


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_ask_without_next_question_is_rejected_but_scope_survives():
    r = await _step({"action": "ask", "scope": "switch", "extracted_fields": {}})
    assert r.payload is None and r.scope == "switch"
    assert r.reject_reason == "missing_next_question"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_unparseable_model_output_returns_none_not_stepresult():
    """語義區分：模型連可解析的東西都沒給 → **回 None**（非 StepResult）。"""
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": "[]"})
    r = await opt.conversational_step_result("RULES", "SYS", {"collected_fields": {}}, "訊息")
    assert r is None


# ════════ delegate 正規化仍受 scope 與白名單雙重約束 ════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_delegate_survives_invalid_action_when_whitelisted():
    """action 越界時 delegate 也要保住——否則責任委派鏈仍然斷在這裡。"""
    r = await _step({"action": "switch", "scope": "switch",
                     "delegate_facet_key": "contract_closeout", "extracted_fields": {}},
                    delegates=["contract_closeout"])
    assert r.payload is None and r.scope == "switch"
    assert r.delegate_facet_key == "contract_closeout"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_delegate_outside_whitelist_is_dropped():
    r = await _step({"action": "switch", "scope": "switch",
                     "delegate_facet_key": "self_invented", "extracted_fields": {}},
                    delegates=["contract_closeout"])
    assert r.delegate_facet_key is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_delegate_ignored_when_scope_is_stay():
    r = await _step({"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "delegate_facet_key": "contract_closeout", "extracted_fields": {}},
                    delegates=["contract_closeout"])
    assert r.delegate_facet_key is None and "delegate_facet_key" not in r.payload


# ════════ 8.2 相容層：與改動前逐位一致（零回歸鎖）════════

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_compat_layer_returns_same_payload_for_valid_action():
    body = {"action": "ask", "next_question": "請提供合約編號",
            "extracted_fields": {"a": 1}, "scope": "stay"}
    opt = _opt(body)
    payload = await opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "訊息")
    assert payload["action"] == "ask" and payload["next_question"] == "請提供合約編號"
    assert payload["extracted_fields"] == {"a": 1} and payload["scope"] == "stay"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_compat_layer_returns_none_for_invalid_action():
    """相容層必須維持舊行為回 None——現有 caller 零感知。"""
    payload = await _opt({"action": "switch", "scope": "switch", "extracted_fields": {}}) \
        .conversational_step("RULES", "SYS", {"collected_fields": {}}, "訊息")
    assert payload is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_extracted_fields_non_dict_is_normalized():
    r = await _step({"action": "converge", "converge_kind": "answer",
                     "extracted_fields": "not-a-dict"})
    assert r.payload["extracted_fields"] == {}


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_inline_answer_non_str_is_dropped():
    r = await _step({"action": "converge", "converge_kind": "answer",
                     "extracted_fields": {}, "inline_answer": {"x": 1}})
    assert "inline_answer" not in r.payload


# ════════ 8.3／8.4 呼叫端：FACET_SCOPE_SALVAGE 兩態 ════════
#
# 旗標**只管呼叫端要不要行動**——解析層一律照新順序執行，回退時不需回退解析層。

import os
from unittest.mock import AsyncMock, patch

from services.conversational_config import ConversationalConfig
from services.responsibility import evaluate_responsibility


def _cfg(key, delegates=()):
    return ConversationalConfig(
        key=key, persona_role=f"pm_{key}", enabled=True,
        topic_scope={"mode": "category", "category": f"cat_{key}"},
        responsibility={"delegates": [{"target": t} for t in delegates]})


def _brain_rejecting_with_switch(delegate=None):
    """模擬實測病灶：模型把 'switch' 填進 action，但 scope 是對的。"""
    brain = MagicMock()
    brain.conversational_step_result = AsyncMock(return_value=StepResult(
        payload=None, scope="switch", delegate_facet_key=delegate,
        reject_reason="action_out_of_range"))
    return brain


async def _decide(brain, cfg):
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value="R")), \
         patch("services.system_context.get_system_context", new=AsyncMock(return_value="C")):
        return await evaluate_responsibility(MagicMock(), cfg, "停用租客帳號", optimizer=brain)


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_responsibility_stays_when_salvage_disabled(monkeypatch):
    """預設 off：行為與修改前一致（fail-open 成 stay），但 **reason 說得出真正原因**。"""
    monkeypatch.delenv("FACET_SCOPE_SALVAGE", raising=False)
    d = await _decide(_brain_rejecting_with_switch(), _cfg("a"))
    assert d.stay
    assert d.reason == "action_rejected_fail_open:action_out_of_range"
    # 裁定 001 ④：這種 stay 是技術故障頂上去的，不得取得 commit authority
    assert d.is_technical_fail_open and not d.has_commit_authority


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_responsibility_switches_when_salvage_enabled(monkeypatch):
    """開旗標：責任委派鏈不再被 action 越界靜默斷掉——**這正是 Task 8 要啟用的能力**。"""
    monkeypatch.setenv("FACET_SCOPE_SALVAGE", "true")
    d = await _decide(_brain_rejecting_with_switch("contract_closeout"),
                      _cfg("a", delegates=("contract_closeout",)))
    assert not d.stay and d.delegate_to == "contract_closeout"
    assert d.reason == "responsibility_contract_salvaged:action_out_of_range"
    # salvage 是**契約**救援，不是技術故障；但它是 switch，一樣沒有 commit authority
    from services.responsibility import DECISION_SOURCE_CONTRACT_SALVAGE
    assert d.decision_source == DECISION_SOURCE_CONTRACT_SALVAGE
    assert not d.is_technical_fail_open and not d.has_commit_authority


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_unparseable_output_still_fails_open_regardless_of_flag(monkeypatch):
    """模型沒給可解析內容 → 無論旗標如何都 fail-open（不得憑空 switch）。"""
    brain = MagicMock()
    brain.conversational_step_result = AsyncMock(return_value=None)
    for flag in ("false", "true"):
        monkeypatch.setenv("FACET_SCOPE_SALVAGE", flag)
        d = await _decide(brain, _cfg("a"))
        assert d.stay and d.reason == "brain_unavailable_fail_open"
        assert d.is_technical_fail_open and not d.has_commit_authority


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_preentry_gate_respects_both_flags(monkeypatch):
    """`_preentry_routable`：GATE 與 SALVAGE 二重保護。

    · GATE 未開 → 恆 True（照舊進場），與本修復無關
    · GATE 開、SALVAGE 未開 → action 越界時**照舊進場**（行為與修改前一致）
    · GATE 開、SALVAGE 開   → 依 scope 擋下進場（舊碼取不到這個訊號）
    """
    from routers import chat as chat_mod

    brain = _brain_rejecting_with_switch()
    rctx = MagicMock(rules_text="R", system_md="C")

    async def _build_ctx(_pool, _cfg_):
        return rctx

    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "false")
    with patch("services.responsibility.build_responsibility_context", new=_build_ctx), \
         patch("services.llm_answer_optimizer.LLMAnswerOptimizer", return_value=brain):
        assert await chat_mod._preentry_routable(MagicMock(), _cfg("a"), "停用租客帳號") is True

        monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
        monkeypatch.setenv("FACET_SCOPE_SALVAGE", "false")
        assert await chat_mod._preentry_routable(MagicMock(), _cfg("a"), "停用租客帳號") is True

        monkeypatch.setenv("FACET_SCOPE_SALVAGE", "true")
        assert await chat_mod._preentry_routable(MagicMock(), _cfg("a"), "停用租客帳號") is False
