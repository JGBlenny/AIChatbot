"""unit：引擎 prefill 進場種子 ＋ 續跑補圖併槽薄接口（conversational-repair 任務 2.4）。

- prepare 帶 prefill：新開會話時把 slots→collected_fields、candidates→pending_candidates。
- prepare 帶 prefill 但會話已存在（續對話）：不套用（進場一次性種子）。
- ingest_recognition：交易面向、信心足→分類三槽併入空槽（不覆蓋已填）；信心不足→pending_candidates；
  無辨識/非交易面向/無會話→靜默 no-op；門檻沿用 repair_prefill.classify_recognition（單一真源）。

全 mock brain/DB；不打 Vision（辨識結果由呼叫端傳入）。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.conversational_engine import ConversationalEngine, _apply_prefill
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _tx_scope():
    return {
        "select": "api",
        "required_slots": ["estate", "item", "urgency"],
        "execute_endpoint": "jgb_create_repair",
        "inference_confidence": 0.7,
        "candidate_max": 3,
        "facet_key": "repair",
    }


def _tx_cfg():
    return ConversationalConfig(key="repair", persona_role="tenant",
                                grounding_scope=_tx_scope())


def _plain_cfg():
    return ConversationalConfig(key="prospect", persona_role="prospect",
                                grounding_scope={"select": "vector"})


_CATEGORY_TREE = {"success": True, "data": [
    {"id": 1, "name": "家電維修", "items": [
        {"id": 101, "name": "冷氣機", "broken_reasons": ["不冷", "漏水", "異音"]},
    ]},
]}


def _engine(with_jgb_api: bool = False):
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"))
    eng._save = AsyncMock()
    eng._close = AsyncMock()
    if with_jgb_api:
        # ingest 名稱→id 解析需 api_handler.jgb_api.get_repair_categories（Gap B）。
        jgb_api = MagicMock()
        jgb_api.get_repair_categories = AsyncMock(return_value=_CATEGORY_TREE)
        eng.api_handler = MagicMock(jgb_api=jgb_api)
    return eng


# ── _apply_prefill（進場種子純函式）─────────────────────────────────────────

@pytest.mark.req("conversational-repair:2.6")
def test_apply_prefill_slots_and_candidates():
    state = {"collected_fields": {}}
    _apply_prefill(state, {
        "slots": {"estate": {"value": "X路5F", "source": "prefill", "confirmed": False},
                  "category": {"value": "冷氣", "source": "inferred", "confirmed": False}},
        "candidates": [{"id": 1, "label": "A"}], "degraded": None})
    assert state["collected_fields"]["estate"]["value"] == "X路5F"
    assert state["collected_fields"]["category"]["value"] == "冷氣"
    assert state["pending_candidates"] == [{"id": 1, "label": "A"}]


@pytest.mark.req("conversational-repair:2.6")
def test_apply_prefill_none_is_noop():
    state = {"collected_fields": {"x": 1}}
    _apply_prefill(state, None)
    assert state == {"collected_fields": {"x": 1}}


# ── prepare 帶 prefill：新開套用 / 續對話不套用 ──────────────────────────────

@pytest.mark.req("conversational-repair:2.6")
async def test_prepare_seeds_prefill_on_new_session(monkeypatch):
    eng = _engine()
    eng.get_state = AsyncMock(return_value=None)   # 無既有會話 → 新開
    started = {}

    async def _start(session_id, user_id, vendor_id, config_key, seed_topic=None, role_id=None):
        started["state"] = {"config_key": config_key, "collected_fields": {},
                            "asked_count": 0, "session_id": session_id}
        return started["state"]
    eng._start = _start
    # brain 回 ask（避免走 API grounding）；驗證進場時 state 已含 prefill 槽位。
    eng.optimizer.conversational_step = AsyncMock(return_value={
        "action": "ask", "next_question": "急迫程度？", "extracted_fields": {}, "scope": "stay"})
    prefill = {"slots": {"estate": {"value": "信義套房", "source": "prefill"}},
               "candidates": None, "degraded": None}
    await eng.prepare("s1", "u1", 2, "冷氣壞了", config=_tx_cfg(),
                      start_if_absent=True, prefill=prefill)
    assert started["state"]["collected_fields"]["estate"]["value"] == "信義套房"


@pytest.mark.req("conversational-repair:2.6")
async def test_prepare_ignores_prefill_on_existing_session():
    eng = _engine()
    existing = {"config_key": "repair", "collected_fields": {"estate": {"value": "OLD"}},
                "asked_count": 1, "session_id": "s1"}
    eng.get_state = AsyncMock(return_value=existing)
    eng._start = AsyncMock()
    eng.optimizer.conversational_step = AsyncMock(return_value={
        "action": "ask", "next_question": "?", "extracted_fields": {}, "scope": "stay"})
    prefill = {"slots": {"estate": {"value": "NEW"}}, "candidates": None, "degraded": None}
    await eng.prepare("s1", "u1", 2, "續問", config=_tx_cfg(),
                      start_if_absent=True, prefill=prefill)
    eng._start.assert_not_awaited()
    assert existing["collected_fields"]["estate"]["value"] == "OLD", "續對話不得被 prefill 覆蓋"


# ── ingest_recognition（續跑補圖併槽薄接口）─────────────────────────────────

@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_high_confidence_resolves_id_slots_with_jgb_api():
    # Gap B：ingest 路徑有 jgb_api → 名稱→id 解析，併入 id 槽（category_id/item_id）＋顯示槽。
    eng = _engine(with_jgb_api=True)
    state = {"config_key": "repair", "collected_fields": {}}
    eng.get_state = AsyncMock(return_value=state)
    rec = {"confidence": 0.9, "suggested_category": "家電維修", "suggested_item": "冷氣機",
           "suggested_reason": "不冷", "suggested_emergency": 1}
    await eng.ingest_recognition("s1", rec, _tx_cfg())
    cf = state["collected_fields"]
    assert cf["category_id"]["value"] == 1 and cf["category_id"]["source"] == "inferred"
    assert cf["item_id"]["value"] == 101
    assert cf["broken_reason"]["value"] == "不冷"
    assert cf["category"]["value"] == "家電維修"  # 顯示槽
    assert cf["emergency_status"]["value"] == 1
    eng._save.assert_awaited()


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_no_jgb_api_degrades_to_candidates():
    # Gap B：ingest 拿不到 jgb_api（api_handler 無 jgb_api）→ 不硬塞 id，退化為顯示名候選。
    eng = _engine(with_jgb_api=False)
    state = {"config_key": "repair", "collected_fields": {}}
    eng.get_state = AsyncMock(return_value=state)
    rec = {"confidence": 0.9, "suggested_category": "家電維修",
           "secondary_damages": ["牆面", "地板"]}
    await eng.ingest_recognition("s1", rec, _tx_cfg())
    assert "category_id" not in state["collected_fields"]
    assert state.get("pending_candidates"), "無分類樹解析應退化為候選"


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_does_not_overwrite_user_slot():
    eng = _engine(with_jgb_api=True)
    state = {"config_key": "repair",
             "collected_fields": {"category": {"value": "使用者說的", "source": "user"}}}
    eng.get_state = AsyncMock(return_value=state)
    rec = {"confidence": 0.9, "suggested_category": "家電維修"}
    await eng.ingest_recognition("s1", rec, _tx_cfg())
    assert state["collected_fields"]["category"]["value"] == "使用者說的", "已填槽位（顯示槽）不被辨識覆蓋"


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_low_confidence_sets_candidates():
    eng = _engine()
    state = {"config_key": "repair", "collected_fields": {}}
    eng.get_state = AsyncMock(return_value=state)
    rec = {"confidence": 0.4, "suggested_category": "冷氣",
           "secondary_damages": ["牆面", "地板"]}
    await eng.ingest_recognition("s1", rec, _tx_cfg())
    assert state.get("pending_candidates"), "信心不足應寫候選"
    assert "category" not in state["collected_fields"], "信心不足不推斷分類槽"


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_none_recognition_noop():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={"collected_fields": {}})
    await eng.ingest_recognition("s1", None, _tx_cfg())
    eng._save.assert_not_awaited()


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_non_transaction_facet_noop():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={"collected_fields": {}})
    rec = {"confidence": 0.9, "suggested_category": "冷氣"}
    await eng.ingest_recognition("s1", rec, _plain_cfg())
    eng.get_state.assert_not_awaited()  # 非交易面向 → 提早返回，連 state 都不查
    eng._save.assert_not_awaited()


@pytest.mark.req("conversational-repair:2.6")
async def test_ingest_no_session_noop():
    eng = _engine()
    eng.get_state = AsyncMock(return_value=None)
    rec = {"confidence": 0.9, "suggested_category": "冷氣"}
    await eng.ingest_recognition("s1", rec, _tx_cfg())
    eng._save.assert_not_awaited()
