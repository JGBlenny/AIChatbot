"""unit:引擎 confirm/execute 交易分支（conversational-repair 元件 2/7｜任務 2.2）。

交易面向（grounding_scope.execute_endpoint 存在）在 confirm gate 與 execute 上的行為：
  - 收齊→confirm：brain 回 action='confirm' → 引擎組摘要（confirm_template 嵌槽位）＋三顆
    quick_replies（✅送出／✏️修改／❌取消，穩定機器值），**不呼叫** execute（收齊≠送出，R4.1）。
  - confirm 後同意（按鈕 value 或自然語）→ execute 呼叫一次、executed=True、回執含單號（R4.2）。
  - 冪等：executed=True 後再同意 → 不再呼叫 API、回單號（R4.4）。
  - execute 失敗 → executed 不設、誠實告知＋重試 quick reply；再同意可重試（R4.3）。
  - 修改 → 回 brain 帶否定/修正語境重出 confirm，已收槽位保留（R4.5）。
  - 取消 → _close、槽位不留殘單（R3.3）。
  - brain 回 None → 降級（回 None）、絕不呼叫 execute（R3.4）。
  - inline_answer 存在 → 回覆先含即答再含問題/摘要（R3.1）。
  - 非交易面向（無 execute_endpoint）→ 走既有路徑（回歸鎖）。
  - set_facet 每輪被呼叫且 turn_number 遞增（R7.1）。

全 mock brain/DB/api_handler；set_facet 以 monkeypatch 擷取。確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

import services.conversational_engine as ce_mod
from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig
from tests.support.brain_stub import stub_step

pytestmark = pytest.mark.unit

CONFIRM_TEMPLATE = "確認送出：{estate}／{item}／{urgency}——送出嗎？"
RECEIPT_TEMPLATE = "已建單 #{ticket_no}，之後隨時問「修得怎樣」可查進度。"


def _tx_scope():
    return {
        "select": "api",
        "required_slots": ["estate", "item", "urgency"],
        "execute_endpoint": "jgb_create_repair",
        "execute_params": {"item_id": "item", "role_id": "{session.role_id}"},
        "confirm_template": CONFIRM_TEMPLATE,
        "receipt_template": RECEIPT_TEMPLATE,
        "execute_result_path": "ticket_no",
        "facet_key": "repair",
    }


def _tx_cfg():
    return ConversationalConfig(
        key="repair", persona_role="tenant",
        grounding_scope=_tx_scope(),
        topic_scope={"mode": "category", "category": "修繕報修"})


def _plain_cfg():
    return ConversationalConfig(
        key="prospect", persona_role="prospect",
        grounding_scope={"select": "vector", "target_user": "prospect", "mode": "b2b"})


def _collected():
    return {"estate": "XX路5F", "item": "冷氣不製冷", "urgency": "急"}


def _engine(step_return=None, execute_result=None):
    optimizer = MagicMock()
    stub_step(optimizer, step_return)
    api_handler = MagicMock()
    api_handler.execute_api_call = AsyncMock(
        return_value=execute_result if execute_result is not None
        else {"success": True, "data": {"ticket_no": "R2071"}, "formatted_response": "已建單"})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=api_handler)
    eng._save = AsyncMock()
    eng._close = AsyncMock()
    eng._start = AsyncMock()
    return eng


@pytest.fixture
def facet_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(ce_mod, "set_facet",
                        lambda facet_key=None, turn_number=None: calls.append((facet_key, turn_number)),
                        raising=False)
    return calls


def _qr_values(decision):
    return [q.get("value") for q in (decision.get("quick_replies") or [])]


# ── 收齊→confirm：出摘要＋三 quick_replies，不呼叫 execute（收齊≠送出）──
@pytest.mark.req("conversational-repair:4.1")
async def test_slots_full_confirm_emits_summary_and_quick_replies_no_execute(facet_calls):
    eng = _engine(step_return={"action": "confirm", "extracted_fields": {}})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "asked_count": 2, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "好了", config=_tx_cfg())
    assert decision["kind"] == "ask"
    assert "XX路5F" in decision["answer"] and "冷氣不製冷" in decision["answer"]
    assert _qr_values(decision) == ["confirm_submit", "confirm_edit", "confirm_cancel"]
    eng.api_handler.execute_api_call.assert_not_awaited()   # 收齊≠送出
    assert state.get("awaiting_confirm") is True
    assert state.get("executed") is not True


# ── confirm 後同意（按鈕 value）→ execute 一次、executed=True、回執含單號 ──
@pytest.mark.req("conversational-repair:4.2")
async def test_consent_by_button_executes_once_and_returns_receipt():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1", "user_turns": 2}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "confirm_submit", config=_tx_cfg())
    assert decision["kind"] == "ask"
    assert "R2071" in decision["answer"]
    eng.api_handler.execute_api_call.assert_awaited_once()
    assert state["executed"] is True
    assert state.get("awaiting_confirm") is not True


# ── confirm 後同意（自然語「好」）→ 同上 ──
@pytest.mark.req("conversational-repair:4.2")
async def test_consent_by_natural_language_executes():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "好", config=_tx_cfg())
    assert "R2071" in decision["answer"]
    eng.api_handler.execute_api_call.assert_awaited_once()
    assert state["executed"] is True


# ── execute 呼叫時 slots→params 映射沿用 params_from_form 語彙 ──
@pytest.mark.req("conversational-repair:4.2")
async def test_execute_maps_slots_via_params_from_form():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s1", "u1", 7, "確認送出", config=_tx_cfg())
    api_cfg = eng.api_handler.execute_api_call.call_args.args[0]
    assert api_cfg["endpoint"] == "jgb_create_repair"
    # execute_params 走 params_from_form 通道（同款映射語彙）
    assert api_cfg["params_from_form"] == {"item_id": "item", "role_id": "{session.role_id}"}


# ── 冪等：executed=True 後再同意 → 不再呼叫 API、回單號 ──
@pytest.mark.req("conversational-repair:4.4")
async def test_idempotent_no_re_execute_after_executed():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "executed": True,
             "execute_result": {"success": True, "data": {"ticket_no": "R2071"}},
             "role_id": 30, "vendor_id": 7, "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "好", config=_tx_cfg())
    assert "R2071" in decision["answer"]
    eng.api_handler.execute_api_call.assert_not_awaited()   # 不重複建單


# ── execute 失敗 → executed 不設、誠實告知＋重試 quick reply；再同意可重試 ──
@pytest.mark.req("conversational-repair:4.3")
async def test_execute_failure_does_not_set_executed_and_offers_retry():
    eng = _engine(execute_result={"success": False, "error": "後端錯誤"})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "確認送出", config=_tx_cfg())
    assert decision["kind"] == "ask"
    assert state.get("executed") is not True   # 絕不假裝成功
    assert "confirm_submit" in _qr_values(decision)   # 提供再試一次
    # 再同意可重試（仍是 awaiting_confirm 狀態）
    assert state.get("awaiting_confirm") is True


@pytest.mark.req("conversational-repair:4.3")
async def test_execute_can_retry_after_failure():
    eng = _engine(execute_result={"success": False, "error": "x"})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s1", "u1", 7, "確認送出", config=_tx_cfg())
    # 第二次成功
    eng.api_handler.execute_api_call = AsyncMock(
        return_value={"success": True, "data": {"ticket_no": "R999"}, "formatted_response": "ok"})
    decision = await eng.prepare("s1", "u1", 7, "再試一次", config=_tx_cfg())
    assert state["executed"] is True
    assert "R999" in decision["answer"]


# ── 修改 → 回 brain 重出 confirm，已收槽位保留局部更新 ──
@pytest.mark.req("conversational-repair:4.5")
async def test_edit_reconfirms_via_brain_and_keeps_slots():
    # brain 收到修正後重出 confirm（更新 item）
    eng = _engine(step_return={"action": "confirm",
                               "extracted_fields": {"item": "冷氣漏水"}})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "不是不製冷，是漏水", config=_tx_cfg())
    # 走 brain（不是直接 execute）
    eng.optimizer.conversational_step_result.assert_called_once()
    eng.api_handler.execute_api_call.assert_not_awaited()
    # 局部更新：item 換新、estate/urgency 保留
    assert state["collected_fields"]["item"] == "冷氣漏水"
    assert state["collected_fields"]["estate"] == "XX路5F"
    # 重出 confirm 摘要＋quick_replies
    assert "冷氣漏水" in decision["answer"]
    assert _qr_values(decision) == ["confirm_submit", "confirm_edit", "confirm_cancel"]


# ── 明確按「修改」按鈕 → 回 brain 帶修正語境（不 execute）──
@pytest.mark.req("conversational-repair:4.5")
async def test_edit_button_routes_to_brain():
    eng = _engine(step_return={"action": "ask", "next_question": "要改哪一項呢？",
                               "extracted_fields": {}})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "confirm_edit", config=_tx_cfg())
    eng.optimizer.conversational_step_result.assert_called_once()
    eng.api_handler.execute_api_call.assert_not_awaited()
    assert state.get("awaiting_confirm") is not True   # 離開 confirm 待決


# ── 取消 → _close、槽位不留（不留殘單）──
@pytest.mark.req("conversational-repair:3.3")
async def test_cancel_closes_and_discards_slots():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "不報了", config=_tx_cfg())
    eng._close.assert_awaited_once()
    eng.api_handler.execute_api_call.assert_not_awaited()


@pytest.mark.req("conversational-repair:3.3")
async def test_cancel_button_closes():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": _collected(),
             "awaiting_confirm": True, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s1", "u1", 7, "confirm_cancel", config=_tx_cfg())
    eng._close.assert_awaited_once()


# ── brain 回 None → 降級（None），絕不 execute（R3.4）──
@pytest.mark.req("conversational-repair:3.4")
async def test_brain_none_degrades_and_never_executes():
    eng = _engine(step_return=None)
    state = {"config_key": "repair", "collected_fields": {"estate": "XX路5F"},
             "asked_count": 1, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "冷氣壞了", config=_tx_cfg())
    assert decision is None
    eng.api_handler.execute_api_call.assert_not_awaited()


# ── inline_answer 存在 → 回覆先含即答再含問題（R3.1）──
@pytest.mark.req("conversational-repair:3.1")
async def test_inline_answer_precedes_question():
    eng = _engine(step_return={"action": "ask", "next_question": "發生多久了？",
                               "inline_answer": "牆內管線由業者負責", "extracted_fields": {}})
    state = {"config_key": "repair", "collected_fields": {"estate": "XX路5F"},
             "asked_count": 1, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "要自己出錢嗎", config=_tx_cfg())
    ans = decision["answer"]
    assert "牆內管線由業者負責" in ans and "發生多久了" in ans
    assert ans.index("牆內管線由業者負責") < ans.index("發生多久了")


# ── inline_answer 也適用於 confirm（先答再接摘要）──
@pytest.mark.req("conversational-repair:3.1")
async def test_inline_answer_precedes_confirm_summary():
    eng = _engine(step_return={"action": "confirm", "extracted_fields": {},
                               "inline_answer": "費用由業者負責"})
    state = {"config_key": "repair", "collected_fields": _collected(),
             "asked_count": 2, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "要自己出錢嗎，好了送出吧", config=_tx_cfg())
    ans = decision["answer"]
    assert "費用由業者負責" in ans and "XX路5F" in ans
    assert ans.index("費用由業者負責") < ans.index("XX路5F")


# ── 非交易面向（無 execute_endpoint）→ 走既有路徑（回歸鎖）──
@pytest.mark.req("conversational-repair:8.1")
async def test_non_transaction_facet_uses_existing_path():
    # prospect converge 走既有向量 grounding（不進交易分支）
    eng = _engine(step_return={"action": "converge", "converge_kind": "recommend",
                               "extracted_fields": {"identity": "個人", "scale": "小"}})
    eng._converge_grounding = AsyncMock(return_value=("G", None, "force"))
    state = {"config_key": "prospect", "collected_fields": {"identity": "個人", "scale": "小"},
             "asked_count": 3, "session_id": "s1", "user_id": "u1", "vendor_id": 7}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "推薦方案", config=_plain_cfg())
    assert decision["kind"] == "converge"
    assert "awaiting_confirm" not in state
    eng.api_handler.execute_api_call.assert_not_awaited()


# ── 非交易面向：confirm 待決狀態不存在，一般同意詞不觸發 execute ──
@pytest.mark.req("conversational-repair:8.1")
async def test_non_transaction_consent_word_not_intercepted():
    eng = _engine(step_return={"action": "ask", "next_question": "您的規模是？",
                               "extracted_fields": {}})
    state = {"config_key": "prospect", "collected_fields": {"identity": "個人"},
             "asked_count": 1, "session_id": "s1", "user_id": "u1", "vendor_id": 7}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "好", config=_plain_cfg())
    # 一般面向「好」交 brain（不被交易攔截）
    eng.optimizer.conversational_step_result.assert_called_once()
    eng.api_handler.execute_api_call.assert_not_awaited()


# ── set_facet 每輪被呼叫且 turn_number 遞增（R7.1）──
@pytest.mark.req("conversational-repair:7.1")
async def test_set_facet_called_with_incrementing_turn(facet_calls):
    eng = _engine(step_return={"action": "ask", "next_question": "多久了？",
                               "extracted_fields": {}})
    state = {"config_key": "repair", "collected_fields": {"estate": "XX路5F"},
             "asked_count": 0, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s1", "u1", 7, "冷氣壞了", config=_tx_cfg())
    assert facet_calls[-1] == ("repair", 1)   # 第一輪 user_turns=1
    # 第二輪遞增
    state2 = dict(state, user_turns=1)
    eng.get_state = AsyncMock(return_value=state2)
    await eng.prepare("s1", "u1", 7, "昨天", config=_tx_cfg())
    assert facet_calls[-1] == ("repair", 2)


# ── set_facet 不因計量 ctx 缺失而中斷對話（fire-and-forget）──
@pytest.mark.req("conversational-repair:7.1")
async def test_set_facet_failure_does_not_break_dialog(monkeypatch):
    def _boom(facet_key=None, turn_number=None):
        raise RuntimeError("no ctx")
    monkeypatch.setattr(ce_mod, "set_facet", _boom, raising=False)
    eng = _engine(step_return={"action": "ask", "next_question": "多久了？",
                               "extracted_fields": {}})
    state = {"config_key": "repair", "collected_fields": {"estate": "XX路5F"},
             "asked_count": 0, "role_id": 30, "vendor_id": 7,
             "session_id": "s1", "user_id": "u1"}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "冷氣壞了", config=_tx_cfg())
    assert decision["kind"] == "ask"   # 對話未被 set_facet 例外中斷
