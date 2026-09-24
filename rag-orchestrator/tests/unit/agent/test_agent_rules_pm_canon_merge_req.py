"""unit：任務 9.5①「安置」——pm 正本 D/E/C/G 十一條細目要移出正本的**對話規則**，
併進 `agent_rules._POLICY_TEXT_NON_PROSPECT`（DSP-049／DSP-051；
knowledge-outline-and-intent-architecture:9.5）。

⛔ 本檔不驗真模型輸出——只釘：三句新定義句逐字在 `_POLICY_TEXT_NON_PROSPECT`
（⛔ 不在 `_POLICY_TEXT`，prospect 版凍結不動）、不含例子標記（沿用既有
`_EXAMPLE_MARKERS` 尺）、`_POLICY_TEXT` 逐字不動（長度與 `⛔` 計數仍在 5.1 上限）。

三句對應來源（逐句比對後判定「已有同題」的九條 ⛔ 不重複、只補這三句真正
缺的定義——見 diff 摘要）：
1. `property_manager/E/number-data-provenance-rule` 的「推算值要標明」半句
   （「來自 JGB」「沒有的欄位就說沒有」已有同題句涵蓋，⛔ 不重複）。
2. `property_manager/D/prohibited-statements` 的「不用系統時間冒充業務事實」
   ＋ `property_manager/C/followup-missing-data-in-jgb` 的「不用更新時間冒充
   入帳日」——同一命題兩處重複出現，併成一句泛化定義。
3. `property_manager/C/followup-session-end` 聊天直接進場段的收尾行為
   （清單進場「結束鈕」段是 UI 事件、非 LLM 決策，⛔ 不進本檔）。
"""
from __future__ import annotations

import pytest

from services.agent import agent_rules

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:9.5"),
]

#: 與 `test_agent_rules_definitions_req.py` / `test_ask_target_req.py` 同一組標記
#: （⛔ 不另立第二把尺）。
_EXAMPLE_MARKERS = ("（如", "(如", "例如", "例：", "像是")

_PM_CANON_MERGE_SENTENCES = (
    "依規則推算的金額要標明是推算值，並註明實際以查詢結果為準。",
    "系統時間戳不是業務發生時間，⛔ 不得替代查詢結果作答。",
    "使用者說結束、好了、謝謝等收尾語，簡短收尾即可，⛔ 不追問或重述。",
)


@pytest.mark.parametrize("sentence", _PM_CANON_MERGE_SENTENCES)
def test_sentence_in_non_prospect_policy_only(sentence):
    assert sentence in agent_rules._POLICY_TEXT_NON_PROSPECT
    assert sentence not in agent_rules._POLICY_TEXT


@pytest.mark.parametrize("sentence", _PM_CANON_MERGE_SENTENCES)
def test_sentence_carries_no_example_marker(sentence):
    for marker in _EXAMPLE_MARKERS:
        assert marker not in sentence


def test_example_marker_ruler_is_not_a_no_op():
    """正對照：把「例如」塞進同一句，同一組標記必須抓得到。"""
    planted = _PM_CANON_MERGE_SENTENCES[0] + "例如信仰。"
    assert any(marker in planted for marker in _EXAMPLE_MARKERS)


def test_prospect_policy_text_untouched():
    """`_POLICY_TEXT`（prospect，5.1 凍結）逐字不動——長度與 `⛔` 計數仍在原上限。"""
    assert len(agent_rules._POLICY_TEXT) <= 1584
    assert agent_rules._POLICY_TEXT.count("⛔") <= 8


def test_new_sentences_add_no_more_than_200_chars():
    """收案任務 9.5① 的長度紀律：新增總量 ≤ 200 字（含標點）。"""
    added = sum(len(s) for s in _PM_CANON_MERGE_SENTENCES)
    assert added <= 200
