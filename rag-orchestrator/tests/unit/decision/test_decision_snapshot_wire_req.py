"""unit：決策快照掛線（retrieval-decision-layer 任務 1.3｜R8.3）。

契約：
- `_meter_decision` 比照 `_meter_comparison` 房式——計量模組 import/呼叫失敗零影響回答；
- `_smart_retrieval_with_comparison` 的 **b2b 短路**也是決策點——凍結語料全走此路，
  必落快照（rule_version/config_hash/kb_top1_final/kb_threshold/verdict/decision_case）；
- b2c 六 case 仲裁路徑落 `decide_arbitration` 產出的完整快照（verdict/decision_case 同構）。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from services.decision_layer import DECISION_RULE_VERSION

pytestmark = pytest.mark.unit


# ── _meter_decision 房式：正常轉呼叫 set_decision ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_meter_decision_calls_set_decision(monkeypatch):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_decision", spy)

    chat._meter_decision(snapshot={"verdict": "knowledge"}, facet_event="enter")

    spy.assert_called_once()
    _, kw = spy.call_args
    assert kw["snapshot"] == {"verdict": "knowledge"}
    assert kw["facet_event"] == "enter"


# ── 計量失敗零影響（同 _meter_path/_meter_comparison 防護）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_meter_decision_swallows_metering_failure(monkeypatch):
    import services.usage_metering as um
    monkeypatch.setattr(um, "set_decision",
                        MagicMock(side_effect=RuntimeError("metering down")))
    chat._meter_decision(snapshot={"verdict": "none"})    # 不得外拋


# ── b2b 短路：決策點必落快照（凍結語料全走此路，E-5 歸因不能漏）──
@pytest.mark.req("retrieval-decision-layer:8.3")
@pytest.mark.parametrize("kb_list,verdict,top1", [
    ([{"id": 1, "similarity": 0.87}], "knowledge", 0.87),
    ([], "none", None),
])
async def test_b2b_short_circuit_records_snapshot(monkeypatch, kb_list, verdict, top1):
    import services.usage_metering as um
    spy = MagicMock()
    monkeypatch.setattr(um, "set_decision", spy)
    monkeypatch.setattr(chat, "_retrieve_knowledge",
                        AsyncMock(return_value=(kb_list, None)))

    request = MagicMock()
    request.mode = "b2b"
    result = await chat._smart_retrieval_with_comparison(
        request=request, intent_result={}, sop_orchestrator=MagicMock(),
        resolver=MagicMock())

    assert result["type"] == verdict                     # 判定原樣（快照不改行為）
    assert result["reason"] == "B2B 模式，走 JGB 知識"
    spy.assert_called_once()
    snap = spy.call_args.kwargs["snapshot"]
    assert snap["rule_version"] == DECISION_RULE_VERSION
    assert snap["decision_case"] == "b2b_knowledge_only"
    assert snap["verdict"] == verdict
    assert snap["kb_top1_final"] == top1
    assert "config_hash" in snap and "kb_threshold" in snap
