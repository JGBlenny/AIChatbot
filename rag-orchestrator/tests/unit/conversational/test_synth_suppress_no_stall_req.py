"""unit:收斂作答鐵則的「歸屬」守門——住 config.answer_rules，不污染共用合成、不混入面向脈絡。

演進：鐵則（底稿在手直接答/禁推託/只有一份時比較請補識別）曾試放共用 `_build_presales_synth`
（會讓售前也吃到→退回）、再試放面向系統脈絡（換面向會消失、新領域得各抄→再搬）。
**定案：config.answer_rules（per 對話，見 test_answer_rules_req）。** 本檔守兩個「不在」：
  1. 共用售前合成保持通用（無合約特例）；
  2. 面向系統脈絡種子回歸純領域框架（作答行為不住這）。
"""
import os
from unittest.mock import MagicMock

import pytest

from services.llm_answer_optimizer import LLMAnswerOptimizer

pytestmark = pytest.mark.unit

SEED_CTX = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        "database", "migrations", "seed_domain_contract_system_context.sql")


# ── 面向系統脈絡＝純領域框架：作答行為鐵則不在此（住 config.answer_rules）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_facet_context_stays_domain_framing_only():
    with open(SEED_CTX, encoding="utf-8") as f:
        sql = f.read()
    tail = sql.split("狀態判斷(子面向)", 1)[1]
    ctx = tail.split("$CTX$", 2)[1]
    assert "以系統的判定與原因為準" in ctx      # 領域框架保留
    assert "編號｜名稱" not in ctx              # 底稿識別頭說明＝對話層，不在面向脈絡
    assert "比較" not in ctx                    # 比較處置＝對話層，不在面向脈絡


# ── 共用售前合成 suppress 分支保持通用：不含合約/診斷特例（售前不受影響）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_presales_suppress_branch_stays_generic():
    opt = LLMAnswerOptimizer(config={}, llm_provider=MagicMock())
    messages, _m, _t = opt._build_presales_synth(
        grounding_knowledge="某知識", accumulated_context=None, system_context_md="SYS",
        user_question="問題", cta_mode="suppress")
    p = "\n".join(m["content"] for m in messages)
    assert "不要附上 demo" in p                 # suppress 既有語意保留
    for contract_only in ("編號｜名稱", "查無", "另一份"):
        assert contract_only not in p           # 對話層鐵則不得混入共用函式


# ── force（推薦型）也通用化：CTA/排版塊已外移 config.cta_rules（見 test_presales_rules_extraction）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_force_branch_generic_no_hardcoded_cta():
    opt = LLMAnswerOptimizer(config={}, llm_provider=MagicMock())
    messages, _m, _t = opt._build_presales_synth(
        grounding_knowledge="方案知識", accumulated_context=None, system_context_md="SYS",
        user_question="有什麼方案", cta_mode="force")
    p = "\n".join(m["content"] for m in messages)
    assert "jgbsmart.com" not in p      # 業務網址不再硬編在共用程式
