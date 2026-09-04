"""unit 層：handoff 文案與 channel 資料化（design.md 元件 6／conversational_config）。需求 2.1、4.1、4.3。

DB metadata 供給 → code 保底；channel 可由 env 覆寫。⛔ 不動既有 answer_rules／cta_rules 語義。
"""
import pytest

from services import conversational_config as cc
from services.conversational_config import ConversationalConfig, _config_from_row

pytestmark = pytest.mark.unit


@pytest.mark.req("presales-grounding-gate:2.1")
def test_code_default_has_handoff_message_and_channel(monkeypatch):
    monkeypatch.delenv("PRESALES_HANDOFF_CHANNEL", raising=False)
    cfg = cc.PRESALES_CONFIG
    assert cfg.handoff_message and "轉專人" in cfg.handoff_message       # D1 固定句；保留「轉專人」釘字
    assert cc.effective_handoff_channel(cfg) == "line_official"


@pytest.mark.req("presales-grounding-gate:4.1")
def test_env_overrides_channel_when_config_has_none(monkeypatch):
    monkeypatch.setenv("PRESALES_HANDOFF_CHANNEL", "web_form")
    cfg = ConversationalConfig(key="k", persona_role="prospect")
    assert cc.effective_handoff_channel(cfg) == "web_form"


@pytest.mark.req("presales-grounding-gate:4.3")
def test_db_metadata_supplies_message_and_channel():
    md = {"conversational_config": {"key": "presales", "persona_role": "prospect",
                                    "handoff_message": "DB 的句子", "handoff_channel": "line_official_v2"}}
    cfg = _config_from_row(["prospect"], md)
    assert cfg.handoff_message == "DB 的句子" and cfg.handoff_channel == "line_official_v2"
    assert cc.effective_handoff_message(cfg) == "DB 的句子"
    assert cc.effective_handoff_channel(cfg) == "line_official_v2"    # DB 優先於 env／保底


@pytest.mark.req("presales-grounding-gate:4.3")
def test_db_row_without_handoff_keys_falls_back_to_code_default(monkeypatch):
    monkeypatch.delenv("PRESALES_HANDOFF_CHANNEL", raising=False)
    md = {"conversational_config": {"key": "presales", "persona_role": "prospect"}}
    cfg = _config_from_row(["prospect"], md)
    assert cfg.handoff_message is None and cfg.handoff_channel is None
    assert cc.effective_handoff_message(cfg) == cc.PRESALES_HANDOFF_MESSAGE
    assert cc.effective_handoff_channel(cfg) == cc.PRESALES_HANDOFF_CHANNEL_DEFAULT == "line_official"


@pytest.mark.req("presales-grounding-gate:2.1")
def test_handoff_message_never_echoes_user_input():
    """固定句是常數，⛔ 不含任何格式化佔位（避免回顯使用者輸入）。"""
    assert "{" not in cc.PRESALES_HANDOFF_MESSAGE and "%s" not in cc.PRESALES_HANDOFF_MESSAGE
