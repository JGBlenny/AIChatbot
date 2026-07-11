"""unit：修繕交易面向三路進場＋repair_enabled gate＋續跑補圖（conversational-repair 任務 3.1/3.2/2.4）。

覆蓋（全 mock，不碰 DB/服務）：
- trigger_facet_key 命中/未命中/未啟用（R1.3 防呆）。
- repair_enabled gate：false→降級文案不開面向；true/缺值→開（R1.5）。
- Step 0.5 損傷高信心→seed 面向不打 SOP；無面向配置→SOP 安全網；非損傷→現行降級（R1.1/決策6）。
- 續跑帶圖→辨識結果經 engine.ingest_recognition 併槽（R2.6）。
- gate 只對「宣告 enabled_gate 的面向」生效（配置驅動，非修繕字樣硬編）。

驗證合約：進場邏輯（gate/prefill/seed）本身，不驗 brain 內容（那由 integration/e2e 守）。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from routers.chat import (
    ChatRequestContext,
    VendorChatRequest,
    handle_trigger_facet,
    handle_image,
    handle_conversational_session,
    _repair_gate_open,
    _seed_repair_facet,
)
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit

SENTINEL = object()


# ── fixtures ────────────────────────────────────────────────────────────

def _repair_cfg(enabled=True, gate=True, prefill=True):
    scope = {
        "select": "api",
        "required_slots": ["estate", "item", "urgency"],
        "execute_endpoint": "jgb_create_repair",
    }
    if gate:
        scope["enabled_gate"] = "repair_enabled"
    if prefill:
        scope["prefill_api"] = "get_tenant_contracts"
    return ConversationalConfig(
        key="repair", persona_role="tenant", grounding_scope=scope, enabled=enabled,
        topic_scope={"mode": "category", "category": "修繕報修"})


def _vendor_config_service(monkeypatch, *, configs):
    """把 VendorConfigService 換成回傳指定 configs 的 stub。"""
    svc = MagicMock()
    svc.get_vendor_configs = AsyncMock(return_value=configs)
    import services.vendor_config_service as vcs
    monkeypatch.setattr(vcs, "VendorConfigService", lambda db_pool: svc)
    return svc


def _req(**state):
    state.setdefault("db_pool", MagicMock())
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


def _msg(**kw):
    kw.setdefault("mode", "b2b")
    return VendorChatRequest(message="冷氣壞了", **kw)


# ── (3.1) trigger_facet_key 命中/未命中/未啟用 ─────────────────────────────

@pytest.mark.req("conversational-repair:1.3")
async def test_trigger_facet_key_absent_returns_none():
    """無 trigger_facet_key → 非此案，回 None（照常走既有管線）。"""
    assert await handle_trigger_facet(_msg(), _req(), ChatRequestContext()) is None


@pytest.mark.req("conversational-repair:1.3")
async def test_trigger_facet_key_miss_returns_none_no_error(monkeypatch):
    """未命中 config registry → 回 None、不報錯（防呆）。"""
    monkeypatch.setattr(chat, "config_for_key", AsyncMock(return_value=None), raising=False)
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "config_for_key", AsyncMock(return_value=None))
    r = _msg(trigger_facet_key="does_not_exist")
    assert await handle_trigger_facet(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("conversational-repair:1.3")
async def test_trigger_facet_key_disabled_returns_none(monkeypatch):
    """命中但 enabled=false → 回 None（照常管線，防呆）。"""
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "config_for_key",
                        AsyncMock(return_value=_repair_cfg(enabled=False)))
    r = _msg(trigger_facet_key="repair")
    assert await handle_trigger_facet(r, _req(), ChatRequestContext()) is None


@pytest.mark.req("conversational-repair:1.3")
async def test_trigger_facet_key_hit_seeds_facet(monkeypatch):
    """命中且 enabled → 呼叫 _seed_repair_facet（跳過意圖辨識直達面向）。"""
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "config_for_key", AsyncMock(return_value=_repair_cfg()))
    seed = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_seed_repair_facet", seed)
    r = _msg(trigger_facet_key="repair")
    resp = await handle_trigger_facet(r, _req(), ChatRequestContext())
    assert resp is SENTINEL
    assert seed.await_count == 1


# ── (3.1) repair_enabled gate ─────────────────────────────────────────────

@pytest.mark.req("conversational-repair:1.5")
async def test_gate_false_closed(monkeypatch):
    """repair_enabled=false → gate 關。"""
    _vendor_config_service(monkeypatch, configs={"repair_enabled": {"value": False}})
    assert await _repair_gate_open(MagicMock(), 2, _repair_cfg()) is False


@pytest.mark.req("conversational-repair:1.5")
async def test_gate_true_open(monkeypatch):
    """repair_enabled=true → gate 開。"""
    _vendor_config_service(monkeypatch, configs={"repair_enabled": {"value": True}})
    assert await _repair_gate_open(MagicMock(), 2, _repair_cfg()) is True


@pytest.mark.req("conversational-repair:1.5")
async def test_gate_missing_defaults_open(monkeypatch):
    """值不存在 → 預設 true（gate 開）。"""
    _vendor_config_service(monkeypatch, configs={})
    assert await _repair_gate_open(MagicMock(), 2, _repair_cfg()) is True


@pytest.mark.req("conversational-repair:1.5")
async def test_gate_not_declared_always_open():
    """面向未宣告 enabled_gate → 不檢查、恆放行（非受控面向）。"""
    cfg = _repair_cfg(gate=False)
    assert await _repair_gate_open(MagicMock(), 2, cfg) is True


@pytest.mark.req("conversational-repair:1.5")
async def test_gate_closed_returns_degraded_not_facet(monkeypatch):
    """gate 關 → _seed_repair_facet 回降級文案 Response、不進面向（不呼叫 _conversational_respond）。"""
    _vendor_config_service(
        monkeypatch,
        configs={"repair_enabled": {"value": False},
                 "service_hotline": {"value": "04-8765-4321"}})
    respond = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_conversational_respond", respond)
    r = _msg(vendor_id=2, mode="b2c")
    resp = await _seed_repair_facet(r, _req(), _repair_cfg())
    assert resp is not None and resp is not SENTINEL, "應回降級 Response 而非進面向"
    assert respond.await_count == 0, "gate 關時不得進面向"
    assert "04-8765-4321" in resp.answer, "降級文案應注入客服管道參數"


@pytest.mark.req("conversational-repair:1.5")
async def test_gate_open_seeds_facet_with_prefill(monkeypatch):
    """gate 開 → 跑 prefill 後進面向（_conversational_respond 帶 prefill）。"""
    _vendor_config_service(monkeypatch, configs={"repair_enabled": {"value": True}})
    monkeypatch.setattr(chat, "_recognize_repair_image", AsyncMock(return_value=None))
    _prefill = {"slots": {"estate": {"value": "X", "source": "prefill"}},
                "candidates": None, "degraded": None}
    monkeypatch.setattr(chat, "_run_repair_prefill", AsyncMock(return_value=_prefill))
    respond = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_conversational_respond", respond)
    r = _msg(vendor_id=2, mode="b2c")
    resp = await _seed_repair_facet(r, _req(), _repair_cfg())
    assert resp is SENTINEL
    assert respond.await_args.kwargs.get("prefill") is _prefill
    assert respond.await_args.kwargs.get("start_if_absent") is True


@pytest.mark.req("conversational-repair:1.5")
async def test_prefill_degraded_no_contract_does_not_open_facet(monkeypatch):
    """prefill degraded（0 租約）→ 回降級文案、不硬開面向（R2.1/R2.2）。"""
    _vendor_config_service(monkeypatch, configs={"repair_enabled": {"value": True}})
    monkeypatch.setattr(chat, "_recognize_repair_image", AsyncMock(return_value=None))
    monkeypatch.setattr(chat, "_run_repair_prefill", AsyncMock(return_value={
        "slots": {}, "candidates": None, "degraded": "請與管理師確認租約狀態"}))
    respond = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_conversational_respond", respond)
    r = _msg(vendor_id=2, mode="b2c")
    resp = await _seed_repair_facet(r, _req(), _repair_cfg())
    assert resp is not SENTINEL and resp is not None
    assert respond.await_count == 0
    assert "租約" in resp.answer


# ── (3.2) Step 0.5 改道 ────────────────────────────────────────────────────

def _patch_image(monkeypatch, *, is_damage, confidence=0.9):
    import services.image_recognition_service as irs
    rec = {"is_damage": is_damage, "confidence": confidence, "description": "冷氣漏水",
           "suggested_category": "冷氣", "suggested_emergency": 1}

    async def _fake(self, *a, **k):
        return rec
    monkeypatch.setattr(irs, "is_image_recognition_enabled", lambda: True)
    # 建構子需 OPENAI_API_KEY（unit 無金鑰）→ 一併 stub，隔離外部相依。
    monkeypatch.setattr(irs.ImageRecognitionService, "__init__", lambda self: None)
    monkeypatch.setattr(irs.ImageRecognitionService, "analyze_images", _fake)
    return rec


@pytest.mark.req("conversational-repair:1.1")
async def test_step05_damage_seeds_facet_not_sop(monkeypatch):
    """損傷高信心 且 有面向配置 → seed 面向（不打 SOP）。"""
    _patch_image(monkeypatch, is_damage=True)
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "config_for_category", AsyncMock(return_value=_repair_cfg()))
    seed = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_seed_repair_facet", seed)
    sop = SimpleNamespace(process_message=AsyncMock(return_value={"answer": "SOP"}))
    r = _msg(vendor_id=2, mode="b2c", image_urls=["https://x/a.jpg"])
    resp = await handle_image(r, _req(sop_orchestrator=sop), ChatRequestContext())
    assert resp is SENTINEL
    assert seed.await_count == 1
    assert seed.await_args.kwargs.get("recognition") is not None, "應攜帶辨識結果給 prefill"
    assert sop.process_message.await_count == 0, "改道後不得打 SOP"


@pytest.mark.req("conversational-repair:1.1")
async def test_step05_damage_no_config_falls_back_to_sop(monkeypatch):
    """損傷高信心 但無面向配置（3.3 未 seed）→ 落回現行 SOP 安全網。"""
    _patch_image(monkeypatch, is_damage=True)
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "config_for_category", AsyncMock(return_value=None))
    sop = SimpleNamespace(process_message=AsyncMock(return_value={
        "answer": "SOP 排查", "intent_name": "repair", "action_type": "form_fill"}))
    r = _msg(vendor_id=2, mode="b2c", image_urls=["https://x/a.jpg"])
    resp = await handle_image(r, _req(sop_orchestrator=sop), ChatRequestContext())
    assert resp is not None
    assert sop.process_message.await_count == 1, "無配置時安全網仍打 SOP"


@pytest.mark.req("conversational-repair:1.1")
async def test_step05_non_damage_keeps_current_degradation(monkeypatch):
    """非損傷 → 現行降級提示不變（不進面向、不打 SOP）。"""
    _patch_image(monkeypatch, is_damage=False, confidence=0.9)
    import services.conversational_config as cc
    cfg_call = AsyncMock(return_value=_repair_cfg())
    monkeypatch.setattr(cc, "config_for_category", cfg_call)
    seed = AsyncMock(return_value=SENTINEL)
    monkeypatch.setattr(chat, "_seed_repair_facet", seed)
    r = _msg(vendor_id=2, mode="b2c", image_urls=["https://x/a.jpg"])
    resp = await handle_image(r, _req(), ChatRequestContext())
    assert resp is not None, "非損傷仍回既有提示 Response"
    assert seed.await_count == 0, "非損傷不進面向"
    assert "僅支援修繕報修" in resp.answer or "無法確定" in resp.answer


# ── (2.4) 續跑帶圖 → 併槽 ──────────────────────────────────────────────────

@pytest.mark.req("conversational-repair:2.6")
async def test_continuation_image_ingested(monkeypatch):
    """對話進行中補圖 → engine.ingest_recognition 被呼叫、辨識結果併入現有會話。"""
    rec = {"is_damage": True, "confidence": 0.9, "suggested_category": "冷氣"}
    monkeypatch.setattr(chat, "_recognize_repair_image", AsyncMock(return_value=rec))
    import services.conversational_config as cc
    monkeypatch.setattr(cc, "get_config", AsyncMock(return_value=_repair_cfg()))
    engine = MagicMock()
    engine._close = AsyncMock()
    engine.ingest_recognition = AsyncMock()
    monkeypatch.setattr(chat, "_conversational_respond", AsyncMock(return_value=SENTINEL))
    r = _msg(vendor_id=2, mode="b2c", session_id="s1", image_urls=["https://x/a.jpg"])
    ctx = ChatRequestContext(session_state={
        "form_id": "conversational", "state": "COLLECTING", "config_key": "repair"})
    resp = await handle_conversational_session(r, _req(conversational_engine=engine), ctx)
    assert resp is SENTINEL
    assert engine.ingest_recognition.await_count == 1
    assert engine.ingest_recognition.await_args.args[1] is rec


@pytest.mark.req("conversational-repair:2.6")
async def test_continuation_no_image_no_ingest(monkeypatch):
    """續跑無圖 → 不呼叫 ingest_recognition（既有行為零影響）。"""
    engine = MagicMock()
    engine._close = AsyncMock()
    engine.ingest_recognition = AsyncMock()
    monkeypatch.setattr(chat, "_conversational_respond", AsyncMock(return_value=SENTINEL))
    r = _msg(vendor_id=2, mode="b2c", session_id="s1")
    ctx = ChatRequestContext(session_state={
        "form_id": "conversational", "state": "COLLECTING", "config_key": "repair"})
    resp = await handle_conversational_session(r, _req(conversational_engine=engine), ctx)
    assert resp is SENTINEL
    assert engine.ingest_recognition.await_count == 0
