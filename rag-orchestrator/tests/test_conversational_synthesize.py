"""
單元測試：售前 grounded 合成（option-routing task 9.7 / 元件 9 / R11.2-11.3, 13.5）。

驗證 synthesize_presales_answer：
- grounding 與系統脈絡 md、合規鐵則注入 prompt；事實來源限「md + 提供的知識」（不外加）。
- 競品情境只用本次傳入的知識（E1），函式本身不另撈/不杜撰。
- 空 grounding、LLM 例外 → 回 None（呼叫端降級原文）。

以 patch get_llm_provider 隔離真實 LLM。
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.llm_answer_optimizer as llm_mod  # noqa: E402
from services.llm_answer_optimizer import LLMAnswerOptimizer  # noqa: E402


def _make_optimizer(content="合成後的回覆"):
    with patch.object(llm_mod, "get_llm_provider", return_value=MagicMock()):
        opt = LLMAnswerOptimizer()
    opt.llm_provider.chat_completion = MagicMock(return_value={"content": content})
    return opt


def _messages(opt):
    _, kwargs = opt.llm_provider.chat_completion.call_args
    msgs = kwargs.get("messages") or []
    sys_p = next((m["content"] for m in msgs if m["role"] == "system"), "")
    usr_p = next((m["content"] for m in msgs if m["role"] == "user"), "")
    return sys_p, usr_p


def test_md_and_compliance_injected_in_system_prompt():
    opt = _make_optimizer()
    opt.synthesize_presales_answer(
        grounding_knowledge="帳務模組支援自動帳單與多元金流",
        accumulated_context=[{"field_label": "身分", "selected_label": "個人房東"}],
        system_context_md="【系統脈絡】品牌語氣：顧問式",
        user_question="適合我嗎",
    )
    sys_p, usr_p = _messages(opt)
    # 系統 prompt = md + 合規鐵則（PRESALES_SYNTH_RULES）
    assert "【系統脈絡】品牌語氣：顧問式" in sys_p
    assert opt.PRESALES_SYNTH_RULES in sys_p
    # user prompt 帶情境、知識（標示唯一事實來源）、問題
    assert "個人房東" in usr_p
    assert "帳務模組支援自動帳單與多元金流" in usr_p
    assert "唯一事實來源" in usr_p
    assert "適合我嗎" in usr_p


def test_competitor_grounding_limited_to_provided_knowledge():
    """競品情境：函式只把『本次傳入的 E1』放進知識區，不外加其他競品事實。"""
    opt = _make_optimizer()
    e1 = "金箍棒支援藍新/永豐/中信；合約涵蓋一般租賃/社宅/委託。"
    opt.synthesize_presales_answer(
        grounding_knowledge=e1, system_context_md="md", user_question="你們跟別家差在哪",
    )
    _, usr_p = _messages(opt)
    # 知識區內容即為傳入的 E1；未出現任何未提供的競品名稱（函式不杜撰）
    assert e1 in usr_p
    assert "Bananas" not in usr_p and "屋我也" not in usr_p


def test_empty_grounding_returns_none_without_llm_call():
    opt = _make_optimizer()
    assert opt.synthesize_presales_answer("", system_context_md="md") is None
    opt.llm_provider.chat_completion.assert_not_called()


def test_llm_exception_returns_none():
    opt = _make_optimizer()
    opt.llm_provider.chat_completion = MagicMock(side_effect=RuntimeError("timeout"))
    assert opt.synthesize_presales_answer("知識", system_context_md="md") is None


def test_returns_stripped_content():
    opt = _make_optimizer(content="  個人化推薦內容  ")
    out = opt.synthesize_presales_answer("知識", system_context_md="md")
    assert out == "個人化推薦內容"


def test_empty_llm_content_returns_none():
    opt = _make_optimizer(content="")
    assert opt.synthesize_presales_answer("知識", system_context_md="md") is None
