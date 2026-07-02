"""unit:事實作答不推託——鐵則住在「合約領域系統脈絡」（per-領域），非共用售前合成函式。

根因（真環境揪出）：切換到新合約時，grounding 事實只帶**名稱**、使用者用**編號**稱呼，
LLM 連不起來 → 誤判非同一筆 → 推託（請稍等/查無/請再提供）。兩處修正、各歸其位：
  1. 引擎 grounding 開頭帶「id｜名稱」→ LLM 能把使用者的編號對回這筆（見 test_api_validation_flow_req）。
  2. 「事實在手就直接答、不推託；只有一份時比較才請補另一份」鐵則放進**合約領域系統脈絡**
     （狀態判斷子面向 md），只有合約診斷會載入——**售前不受影響**（分別吃不同脈絡）。
共用的 `_build_presales_synth` 保持通用（不含合約特例）。此測試守「鐵則在對的檔、且沒污染共用函式」。
"""
import os
from unittest.mock import MagicMock

import pytest

from services.llm_answer_optimizer import LLMAnswerOptimizer

pytestmark = pytest.mark.unit

SEED_CTX = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        "database", "migrations", "seed_domain_contract_system_context.sql")


def _seed_text():
    with open(SEED_CTX, encoding="utf-8") as f:
        return f.read()


# ── 鐵則住在合約系統脈絡（狀態判斷子面向）：資料在手直接答、禁推託、只有一份時比較才補 ──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_contract_context_carries_answer_discipline():
    sql = _seed_text()
    # 定位子面向『狀態判斷』md（作答行為住這裡，只有合約診斷會載）
    assert "狀態判斷(子面向)" in sql
    tail = sql.split("狀態判斷(子面向)", 1)[1]
    ctx = tail.split("$CTX$", 2)[1] if "$CTX$" in tail else tail
    # 資料在手→直接答、禁推託語
    assert "編號｜名稱" in ctx                      # 對回使用者的編號/名稱
    for stall in ("查無", "查詢", "稍等"):
        assert stall in ctx                         # 明列禁語
    # 只有一份→比較才請補另一份（條件化：確實不在資料裡才問）
    assert "比較" in ctx and "不在上方" in ctx
    assert "轉專人" in ctx                          # 轉專人限縮到「缺細節」


# ── 共用售前合成 suppress 分支保持通用：不含合約特例（不污染 售前）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_presales_suppress_branch_stays_generic():
    opt = LLMAnswerOptimizer(config={}, llm_provider=MagicMock())
    messages, _m, _t = opt._build_presales_synth(
        grounding_knowledge="某知識", accumulated_context=None, system_context_md="SYS",
        user_question="問題", cta_mode="suppress")
    p = "\n".join(m["content"] for m in messages)
    assert "不要附上 demo" in p                     # suppress 既有語意保留
    # 合約診斷專屬鐵則不得混入共用函式（避免售前也吃到）
    for contract_only in ("編號｜名稱", "查無", "另一份"):
        assert contract_only not in p


# ── force（推薦型）不受影響：仍帶 CTA/demo ──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_force_branch_unaffected():
    opt = LLMAnswerOptimizer(config={}, llm_provider=MagicMock())
    messages, _m, _t = opt._build_presales_synth(
        grounding_knowledge="方案知識", accumulated_context=None, system_context_md="SYS",
        user_question="有什麼方案", cta_mode="force")
    p = "\n".join(m["content"] for m in messages)
    assert "demo" in p.lower()
