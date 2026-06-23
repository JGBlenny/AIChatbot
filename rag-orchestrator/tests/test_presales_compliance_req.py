"""補測試：對話引擎／售前 conversational（spec testing-traceability・任務 6・R5.1/5.2）。

聚焦純函式與合規鐵則（不依賴 LLM/DB → unit）：
- _has_basic_info 基本資訊門檻真值表
- MAX_ASKS 提問硬上限存在且合理
- 售前 prospect 規則內含四鐵則：不報價、IoT 被問才提、競品中立、CTA 連結一律 markdown（禁止裸網址）
"""
import re

import pytest

from services.conversational_engine import _has_basic_info, MAX_ASKS
from services.conversational_rules import CONVERSATIONAL_RULES_BY_ROLE

pytestmark = pytest.mark.unit


@pytest.mark.req("testing-traceability:5.2")
@pytest.mark.parametrize("fields,expected", [
    ({"identity": "個人房東", "scale": "30"}, True),     # 身分 + 規模
    ({"identity": "個人房東", "pain": "收租對帳"}, True),  # 身分 + 痛點
    ({"identity": "個人房東"}, False),                    # 只有身分
    ({"scale": "30", "pain": "對帳"}, False),             # 無身分
    ({}, False),
    (None, False),                                        # NULL-safe
])
def test_has_basic_info_truth_table(fields, expected):
    assert _has_basic_info(fields) is expected


@pytest.mark.req("testing-traceability:5.1")
def test_max_asks_is_sane_positive_int():
    """提問硬上限存在、為正整數（防無限追問失控）。"""
    assert isinstance(MAX_ASKS, int) and MAX_ASKS > 0


@pytest.fixture
def prospect_rules() -> str:
    rules = CONVERSATIONAL_RULES_BY_ROLE.get("prospect")
    assert rules, "prospect 售前規則應存在"
    return rules


@pytest.mark.req("testing-traceability:5.2")
def test_compliance_no_pricing_directive(prospect_rules):
    """合規：不報價（價格導引而非講數字）。"""
    assert "不報價" in prospect_rules


@pytest.mark.req("testing-traceability:5.2")
def test_compliance_iot_not_proactive(prospect_rules):
    """合規：IoT 不主動（被問才說）。"""
    assert "IoT" in prospect_rules and "不主動" in prospect_rules


@pytest.mark.req("testing-traceability:5.2")
def test_compliance_competitor_neutral(prospect_rules):
    """合規：競品中立。"""
    assert "競品中立" in prospect_rules


@pytest.mark.req("testing-traceability:5.2")
def test_compliance_cta_links_are_markdown_no_bare_url(prospect_rules):
    """合規鐵則：CTA 連結一律 markdown [標籤](網址)、禁止裸網址。

    規則文字本身須示範 markdown 連結；每個 URL 都應位於 markdown 連結語法內。
    """
    assert "markdown" in prospect_rules and "禁止裸網址" in prospect_rules
    urls = re.findall(r"https?://", prospect_rules)
    markdown_urls = re.findall(r"\]\(\s*https?://", prospect_rules)
    assert urls, "規則應含示範連結"
    # 每個出現的 URL 都應緊接在 markdown 連結的 ]( 之後（無裸網址）
    assert len(urls) == len(markdown_urls), "偵測到裸網址，違反 CTA markdown 鐵則"
