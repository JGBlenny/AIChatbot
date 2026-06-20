"""
Unit tests for FormManager._present_first_field (form-chaining task 2.1).
Feature: form-chaining
Task: 2.1 - 抽取第一欄組裝邏輯為共用 helper，供串接與既有觸發共用

需求：2.2, 3.1, 3.2

此 helper 為純函式（不碰 DB）：給定表單定義，回傳第一欄呈現契約
{prompt, current_field, current_field_type, quick_replies}。
"""

import os
import sys

import pytest

# 既有測試慣例：services 上 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from form_manager import FormManager  # noqa: E402


@pytest.fixture
def manager():
    return FormManager()


def _select_schema():
    return {
        "form_id": "payment_gateway_followup",
        "form_name": "金流追問選單",
        "default_intro": "還想了解什麼嗎？",
        "fields": [
            {
                "field_name": "followup_topic",
                "field_label": "追問主題",
                "field_type": "select",
                "prompt": "還想了解什麼？\n1. 手續費誰負擔\n2. 能不能綁多家\n3. 怎麼換金流商",
                "required": True,
                "options": [
                    {"label": "手續費誰負擔", "value": "fee"},
                    {"label": "能不能綁多家", "value": "multi"},
                    {"label": "怎麼換金流商", "value": "switch"},
                ],
            }
        ],
    }


def test_returns_contract_keys(manager):
    result = manager._present_first_field(_select_schema())
    assert set(result.keys()) >= {
        "prompt",
        "current_field",
        "current_field_type",
        "quick_replies",
    }


def test_select_prompt_includes_options_and_cancel_hint(manager):
    result = manager._present_first_field(_select_schema())
    prompt = result["prompt"]
    # 表單名稱
    assert "金流追問選單" in prompt
    # 1./2./3. 選項（沿用欄位 prompt 內建編號）
    assert "1. 手續費誰負擔" in prompt
    assert "2. 能不能綁多家" in prompt
    assert "3. 怎麼換金流商" in prompt
    # 取消提示
    assert "取消" in prompt


def test_field_metadata(manager):
    result = manager._present_first_field(_select_schema())
    assert result["current_field"] == "followup_topic"
    assert result["current_field_type"] == "select"


def test_quick_replies_label_value(manager):
    result = manager._present_first_field(_select_schema())
    qr = result["quick_replies"]
    assert qr is not None and len(qr) == 3
    texts = [r["text"] for r in qr]
    values = [r["value"] for r in qr]
    assert texts == ["手續費誰負擔", "能不能綁多家", "怎麼換金流商"]
    assert values == ["fee", "multi", "switch"]


def test_non_select_has_no_quick_replies(manager):
    schema = {
        "form_id": "plain_form",
        "form_name": "純文字表單",
        "default_intro": "",
        "fields": [
            {
                "field_name": "name",
                "field_type": "text",
                "prompt": "請輸入您的姓名",
                "required": True,
            }
        ],
    }
    result = manager._present_first_field(schema)
    assert result["current_field_type"] == "text"
    assert result["quick_replies"] is None
    assert "請輸入您的姓名" in result["prompt"]
    assert "取消" in result["prompt"]
