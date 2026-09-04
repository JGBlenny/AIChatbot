"""unit 層：無 session 的 prospect 零命中 ⇒ 固定句＋handoff、⛔ 不呼叫 LLM（design.md 元件 7）。需求 1.5、2.5、7.1。

非 prospect 走既有兜底、`handoff is None`（逐位元不變）。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from routers.chat import VendorChatRequest
from services import conversational_config as cc
from services import usage_metering as um

pytestmark = pytest.mark.unit


def _req(**state):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


@pytest.fixture
def wired(monkeypatch):
    import routers.chat_shared as chat_shared
    monkeypatch.setattr(chat, "_record_no_knowledge_scenario", AsyncMock())
    monkeypatch.setattr(chat_shared, "check_param_question", AsyncMock(return_value=(None, None)))   # 函式內 import ⇒ 改來源模組
    monkeypatch.setattr(chat, "_meter_path", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(cc, "config_for_target_user", AsyncMock(return_value=cc.PRESALES_CONFIG))
    got = []
    monkeypatch.setattr(um, "set_decision", lambda snapshot=None, facet_event=None: got.append(snapshot))
    optimizer = MagicMock()
    optimizer.synthesize_presales_answer = MagicMock(return_value="LLM 不該被呼叫")
    resolver = MagicMock()
    resolver.get_vendor_parameters = MagicMock(return_value={})
    resolver.resolve_template_with_tracking = MagicMock(side_effect=lambda answer, vendor_id, raise_on_missing=False: (answer, []))
    return SimpleNamespace(req=_req(llm_answer_optimizer=optimizer, db_pool=MagicMock(), vendor_config_service=MagicMock()),
                           optimizer=optimizer,
                           resolver=resolver, cache=MagicMock(), snapshots=got)


@pytest.mark.req("presales-grounding-gate:2.5")
async def test_prospect_no_session_zero_hit_returns_fixed_sentence_without_llm(wired):
    request = VendorChatRequest(message="有沒有 600 戶客戶", mode="b2b", target_user="prospect")
    resp = await chat._handle_no_knowledge_found(request, wired.req, {"intent_name": "unknown", "confidence": 0.0},
                                                 wired.resolver, wired.cache, {"name": "JGB"}, decision={"type": "none"})
    assert resp.answer == cc.PRESALES_HANDOFF_MESSAGE
    assert resp.handoff is not None and resp.handoff.reason == "no_grounding" and resp.handoff.fact_class == "other"
    wired.optimizer.synthesize_presales_answer.assert_not_called()


@pytest.mark.req("presales-grounding-gate:7.1")
async def test_prospect_no_session_meters_presales_snapshot(wired):
    request = VendorChatRequest(message="q", mode="b2b", target_user="prospect")
    await chat._handle_no_knowledge_found(request, wired.req, {"intent_name": "unknown", "confidence": 0.0},
                                          wired.resolver, wired.cache, {"name": "JGB"}, decision={"type": "none"})
    pres = [s["presales"] for s in wired.snapshots if s and "presales" in s]
    assert pres and pres[-1]["path"] == "no_session" and pres[-1]["handoff"] == "no_grounding" and pres[-1]["grounding_hits"] == 0


@pytest.mark.req("presales-grounding-gate:1.5")
async def test_non_prospect_keeps_existing_fallback_and_no_handoff(wired):
    request = VendorChatRequest(message="q", mode="b2c", vendor_id=2, target_user="tenant")
    resp = await chat._handle_no_knowledge_found(request, wired.req, {"intent_name": "unknown", "confidence": 0.0},
                                                 wired.resolver, wired.cache, {"name": "V"}, decision={"type": "none"})
    assert "客服" in resp.answer and resp.handoff is None
    wired.optimizer.synthesize_presales_answer.assert_not_called()
