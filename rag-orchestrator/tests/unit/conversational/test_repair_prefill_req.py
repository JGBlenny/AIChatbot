"""TDD：槽位預填 Prefill 薄模組（spec conversational-repair 任務 2.3，R2.1–2.5）。

分型矩陣：
- 租約 1 筆 → estate 為 prefill 確認型槽位（source='prefill'）
- 租約 N 筆 → candidates（插點 A 形狀 id/label），estate 不預填
- 租約 0 筆 → degraded 文案 key（誠實降級）
- API 失敗（success=False/異常）→ 同 0 筆降級路徑，不拋出
- Vision 信心 0.8 ≥ 門檻 0.7 → 分類三槽（category/item/reason）＋急迫性推斷（source='inferred'）
- Vision 信心 0.5 < 門檻 0.7 → 候選 ≤ candidate_max（不退三層下拉）
- 無 Vision（None）→ 分類槽位留空（變詢問型，由 brain 開口問）
- 門檻從 config 覆蓋（0.9 時 0.8 不過 → 走候選）

驗證合約：prefill 只做槽位分型，不自己打 Vision（辨識結果由呼叫端傳入）。
"""
import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# fixtures：mock jgb_system_api + 基準 config（grounding_scope dict）
# ---------------------------------------------------------------------------

# 修繕分類樹（對齊 jgb_system_api._mock_get_repair_categories）
_CATEGORY_TREE = {"success": True, "data": [
    {"id": 1, "name": "家電維修", "items": [
        {"id": 101, "name": "冷氣機", "broken_reasons": ["不冷", "漏水", "異音"]},
        {"id": 102, "name": "洗衣機", "broken_reasons": ["不轉", "漏水"]},
    ]},
    {"id": 2, "name": "衛浴維修", "items": [
        {"id": 201, "name": "馬桶", "broken_reasons": ["堵塞", "漏水"]},
    ]},
]}


def _make_api(contracts_response: Optional[Dict[str, Any]] = None,
              raise_exc: bool = False,
              categories_response: Optional[Dict[str, Any]] = _CATEGORY_TREE,
              categories_raise: bool = False):
    api = AsyncMock()
    if raise_exc:
        api.get_tenant_contracts.side_effect = RuntimeError("boom")
    else:
        api.get_tenant_contracts.return_value = contracts_response
    if categories_raise:
        api.get_repair_categories.side_effect = RuntimeError("tree boom")
    else:
        api.get_repair_categories.return_value = categories_response
    return api


_ONE = {"success": True, "data": [
    {"contract_id": 678, "estate_id": 456, "estate_title": "信義區套房A",
     "display_address": "信義路五段7號", "room": "3F-1"},
]}
_MANY = {"success": True, "data": [
    {"contract_id": 678, "estate_id": 456, "estate_title": "信義區套房A",
     "display_address": "信義路五段7號", "room": "3F-1"},
    {"contract_id": 701, "estate_id": 512, "estate_title": "中山區雅房B",
     "display_address": "中山北路二段10號", "room": "5F-2"},
]}
_ZERO = {"success": True, "data": []}
_FAIL = {"success": False, "error": "degraded"}


def _config(**overrides) -> Dict[str, Any]:
    cfg = {
        "inference_confidence": 0.7,
        "candidate_max": 3,
        "degraded_messages": {"no_contract": "請與管理師確認租約狀態"},
    }
    cfg.update(overrides)
    return cfg


def _vision(confidence: float, **overrides):
    v = {
        "is_damage": True,
        "confidence": confidence,
        "suggested_category": "家電維修",
        "suggested_item": "冷氣機",
        "suggested_reason": "不冷",
        "suggested_emergency": 1,
        "secondary_damages": ["電力異常", "牆面發霉"],
    }
    v.update(overrides)
    return v


def _prefill(**kwargs):
    from services.jgb.repair_prefill import prefill_repair_slots
    base = dict(
        role_id="R001", user_id="U001", vendor_id=1,
        image_recognition=None, config=_config(),
    )
    base.update(kwargs)
    base["jgb_api"] = kwargs.get("jgb_api")  # required
    return _run(prefill_repair_slots(**base))


# ---------------------------------------------------------------------------
# estate 預填分型（租約筆數）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.1")
def test_single_contract_prefills_flat_scalar_estate_slots():
    # Gap A：estate 拆為扁平標量槽（estate_id/contract_id/estate_display），無 dict 形 estate 槽。
    res = _prefill(jgb_api=_make_api(_ONE))
    slots = res["slots"]
    assert "estate" not in slots  # 不再產 dict 槽
    assert slots["estate_id"]["source"] == "prefill"
    assert slots["estate_id"]["confirmed"] is False
    assert slots["estate_id"]["value"] == 456
    assert slots["contract_id"]["source"] == "prefill"
    assert slots["contract_id"]["value"] == 678
    # estate_display 為標量字串供 confirm_template {estate_display} 嵌值
    ed = slots["estate_display"]
    assert ed["source"] == "prefill"
    assert isinstance(ed["value"], str) and ed["value"]
    # 全數槽位值為標量（非 dict）——api_call_handler {form.<slot>} 才吃得到
    for name in ("estate_id", "contract_id", "estate_display"):
        assert not isinstance(slots[name]["value"], dict)
    assert res.get("degraded") is None


@pytest.mark.req("conversational-repair:2.2")
def test_multiple_contracts_yield_candidates_not_prefill():
    res = _prefill(jgb_api=_make_api(_MANY))
    assert "estate" not in res["slots"]
    assert "estate_id" not in res["slots"]
    cands = res["candidates"]
    assert cands is not None and len(cands) == 2
    # 插點 A 形狀：id/label
    for c in cands:
        assert "id" in c and "label" in c
    assert res.get("degraded") is None


@pytest.mark.req("conversational-repair:2.1")
def test_zero_contracts_degrades():
    res = _prefill(jgb_api=_make_api(_ZERO))
    assert "estate" not in res["slots"]
    assert res["degraded"] == "請與管理師確認租約狀態"


@pytest.mark.req("conversational-repair:2.1")
def test_api_failure_degrades_same_path():
    res = _prefill(jgb_api=_make_api(_FAIL))
    assert "estate" not in res["slots"]
    assert res["degraded"] == "請與管理師確認租約狀態"


@pytest.mark.req("conversational-repair:2.1")
def test_api_exception_degrades_not_raise():
    res = _prefill(jgb_api=_make_api(raise_exc=True))
    assert "estate" not in res["slots"]
    assert res["degraded"] == "請與管理師確認租約狀態"


# ---------------------------------------------------------------------------
# 分類三槽 + 急迫性推斷（Vision 信心）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.3")
def test_high_confidence_infers_id_slots_and_display():
    # Gap B：名稱→id 解析命中 → 產 category_id/item_id（int）＋ broken_reason（字串）
    #   ＋顯示槽 category/item（confirm_template 用）；emergency 槽名為 emergency_status。
    res = _prefill(jgb_api=_make_api(_ONE), image_recognition=_vision(0.8))
    slots = res["slots"]
    assert slots["category_id"]["source"] == "inferred"
    assert slots["category_id"]["value"] == 1
    assert slots["item_id"]["source"] == "inferred"
    assert slots["item_id"]["value"] == 101
    # broken_reason 為字串（對齊 create_repair 期待）
    assert slots["broken_reason"]["value"] == "不冷"
    assert isinstance(slots["broken_reason"]["value"], str)
    # 顯示槽（confirm_template {category}/{item}）
    assert slots["category"]["value"] == "家電維修"
    assert slots["item"]["value"] == "冷氣機"
    # 急迫性槽名為 emergency_status（對齊 required_slots/execute_params）
    assert slots["emergency_status"]["source"] == "inferred"
    assert slots["emergency_status"]["value"] == 1
    # 舊槽名不再產出
    for old in ("category", "item"):
        assert slots[old]["value"] != ""  # 顯示槽存在
    assert "reason" not in slots
    assert "emergency" not in slots
    # 高信心＋解析命中不出候選
    assert res.get("candidates") is None


@pytest.mark.req("conversational-repair:2.3")
def test_name_not_in_tree_leaves_id_slot_empty():
    # Gap B：名稱在分類樹對不到 → 該 id 槽不產（不硬塞），退化為候選。
    res = _prefill(jgb_api=_make_api(_ONE),
                   image_recognition=_vision(0.8, suggested_category="不存在的分類"))
    slots = res["slots"]
    assert "category_id" not in slots
    assert "item_id" not in slots
    # 完全解不出 id → 退化為顯示名候選
    assert res.get("candidates") is not None


@pytest.mark.req("conversational-repair:2.3")
def test_category_tree_query_failure_degrades_to_candidates():
    # Gap B：分類樹查詢失敗（異常）→ 全數降級為顯示名候選，不拋錯、不硬塞 id。
    res = _prefill(jgb_api=_make_api(_ONE, categories_raise=True),
                   image_recognition=_vision(0.8))
    slots = res["slots"]
    for name in ("category_id", "item_id", "broken_reason"):
        assert name not in slots
    cands = res["candidates"]
    assert cands is not None
    for c in cands:
        assert "id" in c and "label" in c


@pytest.mark.req("conversational-repair:2.3")
def test_reason_not_in_tree_still_produces_ids():
    # broken_reason 名稱對不到 → broken_reason 槽留空，但 category_id/item_id 仍產出。
    res = _prefill(jgb_api=_make_api(_ONE),
                   image_recognition=_vision(0.8, suggested_reason="莫名其妙的原因"))
    slots = res["slots"]
    assert slots["category_id"]["value"] == 1
    assert slots["item_id"]["value"] == 101
    assert "broken_reason" not in slots


@pytest.mark.req("conversational-repair:2.4")
def test_low_confidence_yields_candidates_capped():
    res = _prefill(jgb_api=_make_api(_ONE),
                   image_recognition=_vision(0.5), config=_config(candidate_max=3))
    # 不推斷分類 id 槽
    for name in ("category_id", "item_id", "broken_reason"):
        assert name not in res["slots"]
    cands = res["candidates"]
    assert cands is not None
    assert 2 <= len(cands) <= 3
    for c in cands:
        assert "id" in c and "label" in c


@pytest.mark.req("conversational-repair:2.4")
def test_low_confidence_respects_candidate_max():
    res = _prefill(jgb_api=_make_api(_ONE),
                   image_recognition=_vision(0.5), config=_config(candidate_max=2))
    assert len(res["candidates"]) <= 2


@pytest.mark.req("conversational-repair:2.5")
def test_no_vision_leaves_category_slots_empty():
    res = _prefill(jgb_api=_make_api(_ONE), image_recognition=None)
    # 分類槽位留空（變詢問型，由 brain 開口問）
    for name in ("category", "item", "category_id", "item_id",
                 "broken_reason", "emergency_status"):
        assert name not in res["slots"]
    # estate 仍預填（扁平標量）
    assert res["slots"]["estate_id"]["source"] == "prefill"
    assert res.get("candidates") is None


@pytest.mark.req("conversational-repair:2.3")
def test_threshold_override_from_config():
    # 門檻 0.9 → 0.8 不過 → 走候選而非推斷
    res = _prefill(jgb_api=_make_api(_ONE),
                   image_recognition=_vision(0.8), config=_config(inference_confidence=0.9))
    assert "category_id" not in res["slots"]
    assert res["candidates"] is not None


@pytest.mark.req("conversational-repair:2.3")
def test_defaults_used_when_config_keys_absent():
    # 空 config → 預設門檻 0.7、candidate_max 3、degraded 預設文案
    res = _prefill(jgb_api=_make_api(_ONE), image_recognition=_vision(0.8), config={})
    assert res["slots"]["category_id"]["source"] == "inferred"
    # 0 筆 + 空 config → 仍有降級文案（模組內建預設）
    res0 = _prefill(jgb_api=_make_api(_ZERO), image_recognition=None, config={})
    assert isinstance(res0["degraded"], str) and res0["degraded"]
