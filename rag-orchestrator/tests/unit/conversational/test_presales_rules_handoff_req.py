"""unit 層：售前規則文字四處同步（design.md 元件 6）＋業主 SQL 與 code 同源。需求 3.3、4.3。

⛔ 既有釘字（不報價／不杜撰／競品中立／IoT 不主動／markdown 禁裸網址）不得掉；「導專人」要指到入口。
"""
from pathlib import Path

import pytest

from services import conversational_config as cc
from services.conversational_rules import CONVERSATIONAL_RULES_BY_ROLE
from services.system_context import MINIMAL_FALLBACK

pytestmark = pytest.mark.unit
SEVEN = ["customer_reference", "pricing", "contract_sla", "compliance", "security", "feature", "other"]
SQL = Path(__file__).resolve().parents[3].parent / ".kiro" / "specs" / "presales-grounding-gate" / "sql" / "rules-20260904.sql"
ENTRY = "找真人"


@pytest.fixture
def prospect_rules():
    return CONVERSATIONAL_RULES_BY_ROLE["prospect"]


# ── fact_class 段（R3.3）────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.3")
def test_prospect_rules_define_all_seven_fact_classes(prospect_rules):
    assert "【fact_class" in prospect_rules
    for v in SEVEN:
        assert v in prospect_rules, v
    assert '"fact_class"' in prospect_rules                              # 輸出 JSON 規格也列了


@pytest.mark.req("presales-grounding-gate:3.3")
def test_prospect_rules_keep_existing_compliance_anchors(prospect_rules):
    for anchor in ("不報價", "不杜撰", "競品中立", "IoT", "不主動", "markdown", "禁止裸網址"):
        assert anchor in prospect_rules, anchor


# ── 導專人話術指向入口（R4.3）──────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:4.3")
def test_all_four_rule_texts_point_handoff_to_entry(prospect_rules):
    for name, text in (("rules", prospect_rules), ("answer_rules", cc.PRESALES_ANSWER_RULES),
                       ("cta_rules", cc.PRESALES_CTA_RULES), ("system_context", MINIMAL_FALLBACK)):
        assert ENTRY in text, name
        assert "專人" in text, name                                       # 釘字保留


@pytest.mark.req("presales-grounding-gate:4.3")
def test_answer_rules_no_longer_say_only_go_ask_staff():
    assert "才導 demo/專人" not in cc.PRESALES_ANSWER_RULES              # 舊句：只留「專人」不指路


# ── 業主 SQL 與 code 同源（R3.3／4.3）──────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.3")
def test_owner_sql_exists_and_mirrors_code_fallback(prospect_rules):
    assert SQL.exists(), SQL
    sql = SQL.read_text(encoding="utf-8")
    assert "UPDATE knowledge_base" in sql and "id = 3645" in sql and "id = 3798" in sql
    assert prospect_rules.strip() in sql                                 # 3645 的 answer ＝ code fallback 逐字
    assert ENTRY in sql and "【fact_class" in sql
    assert "reset_cache" in sql or "重啟" in sql                          # 提醒清快取
