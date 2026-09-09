"""unit：句末標點正規化（T4｜Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-walkthrough-fixes-batch2-20260909.md`
§5、H7）。

治的病灶：模型逐句輸出偶爾在句尾標點後又補一個句號，拼接後變成「嗎？。」這種
畸形結尾（走查實測）。封閉規則：連續終結標點（`。？！`）收斂成第一個；半形
`?`／`!` 後面接全形 `。` 視為同一種情況。
"""
from __future__ import annotations

import pytest

from services.agent.text_norm import normalize_terminal_punctuation

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:T4"),
]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("今天有空嗎？。", "今天有空嗎？"),
        ("好的。。", "好的。"),
        ("要繼續嗎？！", "要繼續嗎？"),
        ("單身狗?。", "單身狗?"),
        ("真的假的!。", "真的假的!"),
        # 三個以上連續也收斂成第一個。
        ("等等。。。", "等等。"),
    ],
)
def test_collapses_runs_of_terminal_punctuation(raw, expected):
    assert normalize_terminal_punctuation(raw) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "沒有標點的一段話",
        "單一句尾。",
        "單一問號？",
        "單一驚嘆號！",
        "半形問號?",
        "中間逗號，後面句號。",
        "問號後面不是句點的字：？喔",
    ],
)
def test_no_op_on_inputs_without_a_collapsible_run(text):
    assert normalize_terminal_punctuation(text) == text


def test_only_collapses_the_terminal_punctuation_not_surrounding_text():
    assert normalize_terminal_punctuation("這是第一句。。這是第二句？！") == (
        "這是第一句。這是第二句？"
    )


def test_mutation_positive_control():
    """正對照：故意留下兩個標點的字串必須被判定「還沒收斂」——證明比對不是恆真。"""
    not_collapsed = "嗎？。"
    assert normalize_terminal_punctuation(not_collapsed) != not_collapsed
