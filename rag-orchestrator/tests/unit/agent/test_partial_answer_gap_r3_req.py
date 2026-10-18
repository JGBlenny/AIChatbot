"""R3 Fin 式部分回答（`.kiro/specs/agentic-mcp-orchestration/plan-partial-answer-gap-r3-20261018.md` §3）。

三句逐字只在業者／租客政策文；售前政策文（5.1 凍結）不含、長度與 `⛔` 上限不變；
`policy_provider` 依受眾分流。
"""
from __future__ import annotations

import pytest

from services.agent import agent_rules
from tests.unit.agent.test_ask_target_req import _identity

pytestmark = pytest.mark.unit

#: 逐字期望（換字即須重量，故寫死在測試裡）。
GAP_RULE = (
    "- 大綱章節有與問題相關的內容、但沒有直接回答到使用者問的那一項時：整則用 `kind=answer`，"
    "先用相關內容回答能答的部分（照常引用），再用一句以「資料裡沒有提到」開頭寫出使用者問的那一項，"
    "最後一句問使用者想確認的方向（句子 `kind=question`）；⛔ 由相關內容推論那一項有或沒有。"
    "查詢工具（帳單、合約、修繕單、物件等）的結果照既有規則處理；敏感五類不在此列、仍轉人。"
    "資料段與工具都沒有相關內容才轉真人。"
)
MULTI_RULE = (
    "- 一句多題：查得到的先答完；查不到的那一題若屬大綱章節的知識，以「資料裡沒有提到」寫出該題並指路，"
    "若屬工具查詢，照工具查無的規則明說查不到並指路；⛔ 不因一題查不到而整句反問。"
)
ASK_RULE = (
    "- 要資料或要選擇的句子用 `kind=ask`，⛔ 不用 `kind=answer` 提問；"
    "部分回答之後確認方向的那一句問句除外（整則仍為 `kind=answer`）。"
)
OLD_ASK_RULE = "- 要資料或要選擇的句子用 `kind=ask`，⛔ 不用 `kind=answer` 提問。\n"


@pytest.mark.parametrize("rule", [GAP_RULE, MULTI_RULE, ASK_RULE])
def test_rules_verbatim_in_non_prospect_only(rule):
    assert agent_rules._POLICY_TEXT_NON_PROSPECT.count(rule) == 1
    assert rule not in agent_rules._POLICY_TEXT


def test_old_ask_rule_replaced_not_duplicated():
    assert OLD_ASK_RULE not in agent_rules._POLICY_TEXT_NON_PROSPECT


@pytest.mark.parametrize("audience,has_rule", [
    ("property_manager", True),
    ("tenant", True),
    ("prospect", False),
])
def test_policy_provider_by_audience(audience, has_rule):
    text = agent_rules.policy_provider(_identity(target_user=audience))
    assert (GAP_RULE in text) is has_rule


def test_prospect_policy_limits_unchanged():
    assert len(agent_rules._POLICY_TEXT) <= 1584
    assert agent_rules._POLICY_TEXT.count("⛔") <= 8
