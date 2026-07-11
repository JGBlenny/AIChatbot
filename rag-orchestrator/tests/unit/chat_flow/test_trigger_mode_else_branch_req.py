"""unit：非 manual/immediate 的表單知識仍走直觸發 else 分支（task 1.3｜R1.3/1.4/4.3）。

1.1 透傳斷鏈修好後，chat.py 消費層（_build_knowledge_response，chat.py:2965-3052）拿到的
best_knowledge 會帶 trigger_mode key（含 NULL→None）。本測試鎖定「零行為改變」不變式：
trigger_mode ∈ {'none', 'auto', NULL} 的**表單知識**（有 form_id 且達觸發門檻）必須走
else 分支——直接呼叫 form_manager.trigger_form_by_knowledge（自動觸發），
**不得**落入 manual/immediate 的 SOP orchestrator 分支。

契約點：chat.py:2969 `trigger_mode = best_knowledge.get('trigger_mode', 'auto')`
→ 2984 `if trigger_mode in ['manual', 'immediate']`。
- 'none'/'auto' → 非成員 → else（直觸發）
- NULL → key 存在值 None（1.1 透傳後）→ .get 回 None → 非成員 → else（直觸發）

mock form_manager / sop_orchestrator 邊界 → 確定性 unit（無 DB、無真表單）。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from routers.chat import VendorChatRequest

pytestmark = pytest.mark.unit


def _req_state(form_manager, sop_orchestrator):
    """組 req.app.state：本路徑只讀 llm_answer_optimizer/confidence_evaluator/
    form_manager/sop_orchestrator。前兩者不參與表單直觸發分支，給 MagicMock 即可。"""
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        llm_answer_optimizer=MagicMock(),
        confidence_evaluator=MagicMock(),
        form_manager=form_manager,
        sop_orchestrator=sop_orchestrator,
    )))


def _form_knowledge(trigger_mode_present, trigger_mode_value):
    """一筆達觸發門檻（similarity ≥ 0.75）的表單知識。

    trigger_mode_present=False 模擬「key 存在但值為 None」（NULL 透傳後的真實形態，
    1.1 之後 _format_result 一律帶 key）。我們以顯式 None 值表達 NULL。
    """
    k = {
        "id": 999,
        "question_summary": "報修申請",
        "answer": "請填寫報修表單",
        "action_type": "form_fill",
        "form_id": 7,
        "similarity": 0.92,  # ≥ FORM_TRIGGER_THRESHOLD(0.75) → 走表單優先分支
        "trigger_keywords": None,
        "immediate_prompt": None,
    }
    k["trigger_mode"] = trigger_mode_value  # None 表示 NULL；字串表示明確值
    return k


@pytest.mark.parametrize("case_label, trigger_mode_value", [
    ("none 值", "none"),
    ("auto 值", "auto"),
    ("NULL（None 值）", None),
])
@pytest.mark.req("trigger-vocabulary-debt:1.3")
async def test_form_knowledge_non_manual_goes_to_auto_else_branch(
    case_label, trigger_mode_value, monkeypatch
):
    """trigger_mode 為 none/auto/NULL 的表單知識 → 直觸發（else 分支），不走 SOP orchestrator。"""
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.75")

    form_manager = SimpleNamespace(
        trigger_form_by_knowledge=AsyncMock(return_value={
            "answer": "AUTO-TRIGGERED-SENTINEL",
            "form_triggered": True,
            "form_id": "7",  # VendorChatResponse.form_id 型別為 str
        })
    )
    # manual/immediate 分支才會碰 sop_orchestrator——本案不該被呼叫。
    sop_orchestrator = SimpleNamespace(handle_knowledge_trigger=AsyncMock())

    req = _req_state(form_manager, sop_orchestrator)
    request = VendorChatRequest(
        message="我要報修", mode="b2c", vendor_id=2, target_user="tenant",
        session_id="sess-1", user_id="u-1",
    )
    knowledge_list = [_form_knowledge(True, trigger_mode_value)]

    resp = await chat._build_knowledge_response(
        request, req, {"intent_name": "報修", "confidence": 0.9},
        knowledge_list, MagicMock(), {"name": "測試業者"}, MagicMock(),
        decision={"type": "knowledge"},
    )

    # 直觸發：走 form_manager，回自動觸發結果
    form_manager.trigger_form_by_knowledge.assert_awaited_once(), (
        f"[{case_label}] 應走 else 直觸發分支呼叫 trigger_form_by_knowledge"
    )
    assert resp.answer == "AUTO-TRIGGERED-SENTINEL", (
        f"[{case_label}] 應回自動觸發結果"
    )
    # 不得落入 manual/immediate 的 SOP orchestrator 分支
    sop_orchestrator.handle_knowledge_trigger.assert_not_awaited(), (
        f"[{case_label}] trigger_mode={trigger_mode_value!r} 不應走 SOP orchestrator（manual/immediate）分支"
    )
