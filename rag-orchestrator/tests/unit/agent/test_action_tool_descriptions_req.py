"""unit：`jgb2.action.repair_create` 工具描述的三句定義（T4｜Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-walkthrough-fixes-batch2-20260909.md`
§5、H7）。

治的病灶：`description` 欄位被模型在缺照片／補問時丟掉原話；`emergency_status`
欄位模型自造「急迫值」這種內部欄位名講給使用者聽；`category_name` 定義鬆散。
這裡只釘**定義句本身在不在**、以及**不寫例子**（⛔ 提示詞只寫定義）。
"""
from __future__ import annotations

import pytest

from services.agent.tools import action as action_tools

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:T4"),
]

_EXAMPLE_MARKERS = ("（如", "(如", "例如", "例：", "像是")


def test_repair_create_description_contains_the_three_field_definitions():
    text = action_tools.REPAIR_CREATE_SPEC["description"]
    assert "description＝使用者口述的問題原文，⛔ 不因缺照片或補問而丟掉" in text
    assert "category_name＝口述能對上分類樹的一個分類時填該分類，對不上留空" in text
    assert "emergency_status＝急迫程度的系統值（選填），對使用者只說緊急／非緊急，" \
        "⛔ 不講欄位名或數值" in text


def test_category_name_definition_names_the_query_tool_as_registered():
    """分類樹要查得到——引用**登記在 registry 裡的實際工具名**
    （`jgb2.query.repairs`，⛔ 不是憑空杜撰的 `jgb2.query.repair_categories`）。"""
    text = action_tools.REPAIR_CREATE_SPEC["description"]
    assert "jgb2.query.repairs" in text


def test_no_example_markers_in_action_tool_descriptions():
    for spec in (action_tools.BILL_DUE_EXTEND_SPEC, action_tools.REPAIR_CREATE_SPEC):
        for marker in _EXAMPLE_MARKERS:
            assert marker not in spec["description"], (
                f"{spec['name']} 的 description 出現例子標記 {marker!r}"
            )


def test_example_marker_planted_text_fails_positive_control():
    """正對照：塞「例如」的字串必須被同一組標記命中——證明上面的檢查不是形同虛設。"""
    planted = action_tools.REPAIR_CREATE_SPEC["description"] + "例如這樣。"
    assert any(marker in planted for marker in _EXAMPLE_MARKERS)
