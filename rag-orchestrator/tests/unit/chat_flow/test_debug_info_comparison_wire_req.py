"""unit：_meter_comparison 掛線 set_comparison（task 3.3｜R3.1/3.2）。

契約：分數埋點掛在 decision 誕生後的單一無條件生產點——_meter_comparison（同 _meter_path
繞開 include_debug_info 閘）。comparison 有值（走過檢索仲裁）→ 以 sop_score/knowledge_score/
decision_case 呼叫 set_comparison；短路路徑／b2b 回測（comparison=None／空 dict）→ 不呼叫，
分數欄自然留 NULL。

掛線必須在計量防護內：計量模組 import/呼叫失敗零影響回答（沿 _meter_path 同款 try/except）。
mock set_comparison 邊界 → 確定性 unit（無 DB、無 contextvar 真狀態）。
"""
from unittest.mock import MagicMock

import pytest

import routers.chat as chat

pytestmark = pytest.mark.unit


def _comparison(**kw):
    base = {"sop_score": 0.42, "knowledge_score": 0.71, "gap": 0.29,
            "decision_case": "knowledge_significantly_higher"}
    base.update(kw)
    return base


# ── 走檢索仲裁：comparison 有值 → 以三分數呼叫 set_comparison ──
def test_meter_calls_set_comparison_with_scores(monkeypatch):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_comparison", spy)

    chat._meter_comparison(_comparison())

    spy.assert_called_once()
    _, kw = spy.call_args
    assert kw["sop_score"] == 0.42
    assert kw["knowledge_score"] == 0.71
    assert kw["decision_case"] == "knowledge_significantly_higher"


# ── 短路路徑：comparison=None → 不呼叫（分數欄留 NULL） ──
def test_meter_skips_when_no_comparison(monkeypatch):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_comparison", spy)

    chat._meter_comparison(None)

    spy.assert_not_called()


# ── comparison 為空 dict（無分數 key，如 b2b 回測）→ 不呼叫 ──
def test_meter_skips_when_empty_comparison(monkeypatch):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_comparison", spy)

    chat._meter_comparison({})

    spy.assert_not_called()


# ── 計量防護：set_comparison 拋錯不得逸出（回答零影響） ──
def test_meter_metering_failure_is_isolated(monkeypatch):
    import services.usage_metering as um
    monkeypatch.setattr(um, "set_comparison",
                        MagicMock(side_effect=RuntimeError("metering down")))

    # 不得拋出——沿 _meter_path 同款 fire-and-forget
    chat._meter_comparison(_comparison())


# ── 回歸：_build_debug_info 不再自行呼叫 set_comparison（單一掛點乾淨） ──
def test_build_debug_info_no_longer_wires_comparison(monkeypatch):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_comparison", spy)

    chat._build_debug_info("knowledge", {"intent_name": "x", "confidence": 0.9},
                           comparison_metadata=_comparison())

    spy.assert_not_called()
