"""unit:SOP trigger_mode 分派(對話流程核心:純資訊/排查等待/立即確認)。

填補 SOP 對話流程真空。redis 以 mock 注入(只驗分派決策,不驗真實儲存)。
"""
from unittest.mock import MagicMock

import pytest

from services.sop_trigger_handler import SOPTriggerHandler, TriggerMode, NextAction

pytestmark = pytest.mark.unit


def _handler():
    return SOPTriggerHandler(redis_client=MagicMock())


def _item(**kw):
    base = {"id": 1, "item_name": "退租流程", "content": "退租步驟說明", "next_action": NextAction.NONE}
    base.update(kw)
    return base


def test_none_mode_when_no_trigger_mode():
    r = _handler().handle(_item(), "怎麼退租", "s1", "u1", 1)
    assert r["action"] == "completed"
    assert r["context_saved"] is False
    assert r["response"] == "退租步驟說明"


def test_none_mode_when_next_action_none():
    r = _handler().handle(_item(trigger_mode="manual", next_action=NextAction.NONE), "x", "s", "u", 1)
    assert r["action"] == "completed"
    assert r["context_saved"] is False


def test_manual_mode_waits_for_keywords():
    r = _handler().handle(_item(trigger_mode=TriggerMode.MANUAL, next_action=NextAction.FORM_FILL), "x", "s", "u", 1)
    assert r["action"] == "wait_for_keywords"
    assert r["context_saved"] is True
    assert r["trigger_mode"] == TriggerMode.MANUAL
    assert "退租步驟說明" in r["response"]


def test_immediate_mode_asks_confirmation():
    r = _handler().handle(_item(trigger_mode=TriggerMode.IMMEDIATE, next_action=NextAction.FORM_FILL), "x", "s", "u", 1)
    assert r["action"] == "wait_for_confirmation"
    assert r["context_saved"] is True
    assert r["trigger_mode"] == TriggerMode.IMMEDIATE
    assert "immediate_prompt" in r


def test_unknown_mode_falls_back_to_none():
    r = _handler().handle(_item(trigger_mode="weird", next_action=NextAction.FORM_FILL), "x", "s", "u", 1)
    assert r["action"] == "completed"
    assert r["context_saved"] is False
