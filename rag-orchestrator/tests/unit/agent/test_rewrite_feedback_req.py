"""迴圈內回模型的回饋一律走 `rewrite_feedback()` 外殼（2026-09-09 線上回歸）。

病灶：改寫提示句（定義句）以 role="user" 回模型，模型把它讀成使用者說的話而
**回覆它**——線上實測「所以租客到底看不看得到」得到「收到，我會把本對話最近出現的
編號當成那筆…」，原題沒答。修法在契約層：四個改寫點（SCHEMA／VERIFIER_REJECT／
資料段改寫／最近編號改寫）一律組成 `<TAG>: <內容>` ＋固定外殼，外殼講清楚這是系統
回饋、⛔ 不回覆／不複述／不確認、請重新回答使用者最後一則訊息。

正對照：每個功能測試都先證明「該改寫真的發生」（hint 內容在送出的訊息裡），再驗形狀。
"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.runtime import (
    HANDOFF_DATA_REWRITE_HINT,
    RECENT_REFS_REWRITE_HINT,
    REWRITE_FEEDBACK_SUFFIX,
    rewrite_feedback,
)
from services.agent.tools.registry import ToolResult

from tests.unit.agent.test_handoff_data_exits_req import (
    _handoff_no_grounding_response as _handoff_response_with_data,
)
from tests.unit.agent.test_recent_refs_req import (
    _dialog_state,
    _handoff_no_grounding_response,
    _runtime,
)
from tests.unit.agent.test_runtime_req import (
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    VerifierVerdict,
    _fake_message,
    _fake_response,
    _final_response,
    _identity,
    _tool_call_response,
)

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:V2"


def _user_messages_after_first(provider, user_message: str) -> list[str]:
    """最後一次模型呼叫的 messages 裡、使用者那則原話**之後**的所有 role="user" 內容
    ——迴圈內回模型的回饋都在這裡（資料段也是 role="user"，但都在原話之前）。"""
    msgs = provider.calls[-1]["messages"]
    idx = [i for i, m in enumerate(msgs) if m.get("role") == "user" and m.get("content") == user_message]
    assert idx, "最後一次呼叫裡找不到使用者原話——前提不成立"
    return [str(m.get("content") or "") for m in msgs[idx[-1] + 1:] if m.get("role") == "user"]


# ---------------------------------------------------------------------------
# 1. 外殼本身：形狀固定、講明身分與該做的事、⛔ 無插值範例
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_rewrite_feedback_shape_is_tag_body_suffix():
    assert rewrite_feedback("T", "內容。") == "T: 內容。" + REWRITE_FEEDBACK_SUFFIX


@pytest.mark.req(_REQ)
def test_suffix_declares_system_feedback_and_forbids_replying_to_it():
    assert "系統回饋" in REWRITE_FEEDBACK_SUFFIX
    assert "不是使用者說的話" in REWRITE_FEEDBACK_SUFFIX
    assert "⛔ 不回覆、不複述、不確認" in REWRITE_FEEDBACK_SUFFIX
    assert "重新回答使用者最後一則訊息" in REWRITE_FEEDBACK_SUFFIX
    assert "AgentOutput" in REWRITE_FEEDBACK_SUFFIX
    # 定義句紀律：外殼裡不得出現任何數字編號／範例值
    assert not any(ch.isdigit() for ch in REWRITE_FEEDBACK_SUFFIX)


# ---------------------------------------------------------------------------
# 2. 最近編號改寫（線上病灶那條）：送出的不是裸定義句，而是帶外殼的回饋
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_recent_refs_rewrite_is_wrapped_not_bare_hint():
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢，到期日已延。")
    provider = FakeProvider(
        [
            _handoff_no_grounding_response(),
            _final_response(answer="依資料段，756248 已延期。"),
        ]
    )
    runtime = _runtime(provider=provider, verifier=FakeVerifier([VerifierVerdict(ok=True)]),
                       budget=Budget(max_rewrites=1))
    result = await runtime.run_turn(_identity(), "那我要不要打電話給他", state)

    assert result.kind == "answer"
    feedback = _user_messages_after_first(provider, "那我要不要打電話給他")
    assert feedback, "改寫沒發生——前提不成立"
    assert feedback == [rewrite_feedback("RECENT_REFS", RECENT_REFS_REWRITE_HINT)]
    assert RECENT_REFS_REWRITE_HINT not in feedback[0].replace(REWRITE_FEEDBACK_SUFFIX, "").replace(
        "RECENT_REFS: " + RECENT_REFS_REWRITE_HINT, ""
    )  # 定義句只出現一次、且只在外殼裡


# ---------------------------------------------------------------------------
# 3. 資料段改寫（T2）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_handoff_data_rewrite_is_wrapped():
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "1"}),
            _handoff_response_with_data(),
            _final_response(answer="依系統資料，押金全額退還。"),
        ]
    )
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "押金全額退還政策"}, text_for_model="押金政策原文")]
    )
    runtime = _runtime(provider=provider, registry=registry,
                       verifier=FakeVerifier([VerifierVerdict(ok=True)]), budget=Budget(max_rewrites=2))
    result = await runtime.run_turn(_identity(), "我的押金到底會不會退", {})

    assert result.kind == "answer"
    feedback = _user_messages_after_first(provider, "我的押金到底會不會退")
    assert feedback, "改寫沒發生——前提不成立"
    assert feedback == [rewrite_feedback("HANDOFF_DATA", HANDOFF_DATA_REWRITE_HINT)]


# ---------------------------------------------------------------------------
# 4. Verifier 拒因改寫：TAG＋結構化拒因＋外殼；⛔ 無被拒原文
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_verifier_reject_rewrite_is_wrapped_without_rejected_text():
    rejected = "這是一個包含捏造事實的答案"
    provider = FakeProvider([_final_response(answer=rejected), _final_response(answer="好的。")])
    verifier = FakeVerifier([VerifierVerdict(ok=False, reason="UNCITED_ASSERTION"), VerifierVerdict(ok=True)])
    runtime = _runtime(provider=provider, verifier=verifier, budget=Budget(max_rewrites=2))
    result = await runtime.run_turn(_identity(), "有什麼保證", {})

    assert result.kind == "answer"
    feedback = _user_messages_after_first(provider, "有什麼保證")
    assert len(feedback) == 1, feedback
    assert feedback[0].startswith("VERIFIER_REJECT: ")
    assert feedback[0].endswith(REWRITE_FEEDBACK_SUFFIX)
    assert "UNCITED_ASSERTION" in feedback[0]
    assert rejected not in feedback[0]


# ---------------------------------------------------------------------------
# 5. SCHEMA 解析失敗改寫
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_schema_parse_rewrite_is_wrapped():
    provider = FakeProvider(
        [
            _fake_response(_fake_message(content="這不是 JSON")),
            _final_response(answer="好的。"),
        ]
    )
    runtime = _runtime(provider=provider, verifier=FakeVerifier([VerifierVerdict(ok=True)]),
                       budget=Budget(max_rewrites=2))
    result = await runtime.run_turn(_identity(), "有什麼保證", {})

    assert result.kind == "answer"
    feedback = _user_messages_after_first(provider, "有什麼保證")
    assert feedback == [rewrite_feedback("SCHEMA", "輸出不符 AgentOutput schema。")]


# ---------------------------------------------------------------------------
# 6. 不變量：迴圈內任何回模型的 user 訊息都帶外殼（⛔ 不准再出現裸定義句）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_every_in_loop_user_message_carries_the_suffix():
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢。")
    provider = FakeProvider(
        [
            _fake_response(_fake_message(content="不是 JSON")),
            _handoff_no_grounding_response(),
            _final_response(answer="第一版"),
            _final_response(answer="第二版"),
        ]
    )
    verifier = FakeVerifier([VerifierVerdict(ok=False, reason="UNCITED_ASSERTION"), VerifierVerdict(ok=True)])
    runtime = _runtime(provider=provider, verifier=verifier, budget=Budget(max_rewrites=4))
    result = await runtime.run_turn(_identity(), "那我要不要打電話給他", state)

    assert result.kind == "answer" and result.answer == "第二版"
    feedback = _user_messages_after_first(provider, "那我要不要打電話給他")
    assert len(feedback) == 3, feedback  # SCHEMA → RECENT_REFS → VERIFIER_REJECT
    assert [f.split(":", 1)[0] for f in feedback] == ["SCHEMA", "RECENT_REFS", "VERIFIER_REJECT"]
    assert all(f.endswith(REWRITE_FEEDBACK_SUFFIX) for f in feedback)
