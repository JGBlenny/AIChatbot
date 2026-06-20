"""
Unit tests for FormManager._resolve_selected_route (option-routing task 1.1).
Feature: option-routing
Task: 1.1 - 選項路由解析 helper（純函式）

需求：1.1, 1.2, 2.1, 3.1, 3.2

此 helper 為純函式（不碰 DB）：給定已完成的表單定義與收集資料，
解出「被選中選項」的路由 {next_form_id?, answer_kb?}；無路由/無相符回 None。
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


def _select_schema(options):
    """單一 select 欄位表單，options 由參數帶入。"""
    return {
        "form_id": "presales_intro",
        "form_name": "起手式分流",
        "fields": [
            {
                "field_name": "identity",
                "field_type": "select",
                "prompt": "您是？\n1. 個人房東\n2. 公司團隊",
                "options": options,
            }
        ],
    }


def test_option_with_next_form_id_returns_subtree(manager):
    """選項含 next_form_id → 回子樹路由。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "presales_individual_units"},
        {"label": "公司團隊", "value": "team"},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "individual"})
    assert route == {"next_form_id": "presales_individual_units"}


def test_option_with_answer_kb_returns_leaf(manager):
    """選項含 answer_kb → 回葉答案路由。"""
    schema = _select_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "team"})
    assert route == {"answer_kb": 9001}


def test_option_with_both_returns_both(manager):
    """選項同時含 next_form_id 與 answer_kb → 兩者皆回。"""
    schema = _select_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001, "next_form_id": "demo_form"},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "team"})
    assert route == {"next_form_id": "demo_form", "answer_kb": 9001}


def test_option_without_route_returns_none(manager):
    """被選中選項無任何路由 → None（交由呼叫端 fallback 表單層）。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual"},
        {"label": "公司團隊", "value": "team"},
    ])
    assert manager._resolve_selected_route(schema, {"identity": "individual"}) is None


def test_value_mismatch_returns_none(manager):
    """collected value 在 options 中找不到相符 → None。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "x"},
    ])
    assert manager._resolve_selected_route(schema, {"identity": "unknown"}) is None


def test_terminal_non_select_falls_back_to_last_select(manager):
    """終端欄位非 select → 退取 fields 中最後一個 select 欄位。"""
    schema = {
        "form_id": "mixed_form",
        "fields": [
            {
                "field_name": "identity",
                "field_type": "select",
                "options": [
                    {"label": "個人", "value": "individual", "next_form_id": "subtree"},
                ],
            },
            {"field_name": "note", "field_type": "text"},
        ],
    }
    route = manager._resolve_selected_route(schema, {"identity": "individual", "note": "hi"})
    assert route == {"next_form_id": "subtree"}


def test_no_select_field_returns_none(manager):
    """表單完全沒有 select 欄位 → None。"""
    schema = {
        "form_id": "plain_form",
        "fields": [
            {"field_name": "name", "field_type": "text"},
        ],
    }
    assert manager._resolve_selected_route(schema, {"name": "Bob"}) is None


def test_value_matched_by_int_str_tolerance(manager):
    """value 型別差異（int vs str）以字串容錯比對。"""
    schema = _select_schema([
        {"label": "10 戶", "value": 10, "next_form_id": "trial_form"},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "10"})
    assert route == {"next_form_id": "trial_form"}


def test_empty_fields_returns_none(manager):
    """空 fields → None（穩健，不拋例外）。"""
    assert manager._resolve_selected_route({"form_id": "x", "fields": []}, {}) is None
