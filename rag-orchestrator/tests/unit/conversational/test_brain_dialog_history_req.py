"""unit:brain 對話史注入（2026-07-07 線上實測缺陷修復）。

實彈根因：`conversational_step` 的 prompt 只帶「已知欄位＋asked_count＋最新一句」，
brain 不知道自己上一輪問了什麼——純中文名稱識別（「捷仕堂大一廳一房」）無法對應到
contract_ref 槽位（帶數字識別有決定性抽取兜底所以未現形）、且會原句重問（線上逐字稿）。

修復契約：
  - 引擎每個 ask 返回點把（使用者句, 追問句）記入 state.dialog（滾動上限 6）。
  - conversational_step 將 state.dialog 尾段渲染進 user_prompt（含「最新訊息是在回答
    你上一題」的指示）；無 dialog 時 prompt 不含該塊（向後相容）。
mock 隔離，確定性 unit。
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.llm_answer_optimizer import LLMAnswerOptimizer
from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


# ────────────────────── optimizer：prompt 注入 ──────────────────────

def _opt(llm_json: dict):
    opt = LLMAnswerOptimizer.__new__(LLMAnswerOptimizer)
    opt.config = {"model": "m", "max_tokens": 800}
    opt.llm_provider = MagicMock()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": json.dumps(llm_json)})
    return opt


def _sent_user_prompt(opt) -> str:
    msgs = opt.llm_provider.chat_completion.call_args.kwargs["messages"]
    return [m for m in msgs if m["role"] == "user"][0]["content"]


@pytest.mark.req("conversational-diagnosis:2.4")
def test_dialog_history_rendered_into_prompt():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}})
    state = {"collected_fields": {},
             "dialog": [{"u": "想把租期延長", "a": "請問合約編號或物件名稱是什麼？"}]}
    opt.conversational_step("RULES", "SYS", state, "捷仕堂大一廳一房")
    up = _sent_user_prompt(opt)
    assert "最近對話" in up
    assert "請問合約編號或物件名稱是什麼？" in up
    assert "回答你上一題" in up          # 指示：最新訊息對應上一題
    # 歷史塊必須在最新訊息之前（閱讀順序）
    assert up.index("最近對話") < up.index("捷仕堂大一廳一房")


@pytest.mark.req("conversational-diagnosis:2.4")
def test_no_dialog_no_history_block():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}})
    opt.conversational_step("RULES", "SYS", {"collected_fields": {}}, "我想改合約")
    up = _sent_user_prompt(opt)
    assert "最近對話" not in up


@pytest.mark.req("conversational-diagnosis:2.4")
def test_dialog_renders_only_recent_tail():
    opt = _opt({"action": "ask", "next_question": "q", "extracted_fields": {}})
    dialog = [{"u": f"u{i}", "a": f"a{i}"} for i in range(10)]
    opt.conversational_step("RULES", "SYS", {"collected_fields": {}, "dialog": dialog}, "x")
    up = _sent_user_prompt(opt)
    assert "a9" in up and "a6" in up     # 尾段在
    assert "a0" not in up                # 遠古的不在（只渲染尾 4 輪）


# ────────────────────── engine：ask 返回點記史 ──────────────────────

def _engine(step_result):
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = step_result
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    return eng


def _api_cfg():
    return ConversationalConfig(
        key="contract_change", persona_role="pm_contract_change",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "required_slots": ["contract_ref"],
                         "result_mapping": {"list_path": "data", "id_field": "id",
                                            "label_field": "title"}},
        topic_scope={"mode": "category", "category": "合約異動"})


@pytest.mark.req("conversational-diagnosis:2.4")
async def test_brain_ask_records_dialog():
    eng = _engine({"action": "ask", "next_question": "請問要改哪一項？", "extracted_fields": {}})
    state = {"config_key": "contract_change", "collected_fields": {}, "asked_count": 0}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "我想改合約", config=_api_cfg())
    assert decision["kind"] == "ask"
    assert state["dialog"][-1] == {"u": "我想改合約", "a": "請問要改哪一項？"}


@pytest.mark.req("conversational-diagnosis:2.4")
async def test_slot_guard_ask_records_dialog():
    # brain 越權 converge 但槽位未齊 → 程式保底轉追問，仍須記史
    eng = _engine({"action": "converge", "converge_kind": "answer",
                   "extracted_fields": {}, "next_question": "請提供合約編號或物件名稱？"})
    state = {"config_key": "contract_change", "collected_fields": {}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "就幫我改吧", config=_api_cfg())
    assert decision["kind"] == "ask"
    assert state["dialog"][-1]["u"] == "就幫我改吧"
    assert state["dialog"][-1]["a"] == "請提供合約編號或物件名稱？"


@pytest.mark.req("conversational-diagnosis:2.4")
async def test_dialog_capped_at_six():
    eng = _engine({"action": "ask", "next_question": "Q", "extracted_fields": {}})
    state = {"config_key": "contract_change", "collected_fields": {}, "asked_count": 0,
             "dialog": [{"u": f"u{i}", "a": f"a{i}"} for i in range(6)]}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s1", "u1", 7, "第七句", config=_api_cfg())
    assert len(state["dialog"]) == 6                 # 滾動上限
    assert state["dialog"][-1]["u"] == "第七句"      # 新的進
    assert state["dialog"][0]["u"] == "u1"           # 最舊的出
