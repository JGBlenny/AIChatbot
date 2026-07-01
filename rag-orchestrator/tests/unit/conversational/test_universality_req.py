"""unit:通用性零合約硬編（conversational-diagnosis 任務 10.1 / R6.1, R6.2, R6.3）。

(A) 第二個「假面向」設定（mock 端點 + 不同 result_mapping 欄位名）：僅加設定即走通
    ask→api→多筆與候選選擇，無需改任何程式 → 證明引擎不綁合約。
(B) 靜態掃描：診斷相關程式元件（①_has_basic_info ②_ground_by_api ③分類路由 ④config_for_category
    + _match_candidate/prepare）原始碼無合約欄位/端點字面硬編（合約字面只存在於設定/種子/測試）。
"""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc
from services import conversational_engine as ce
from services.conversational_engine import ConversationalEngine, _has_basic_info, _match_candidate
from services.conversational_config import ConversationalConfig
from routers import chat

pytestmark = pytest.mark.unit


# ── 第二個假面向：欄位名與合約全不同（端點 mock_widgets / list_path rows / id uid / label name）──
FAKE_GS = {
    "select": "api",
    "endpoint": "mock_widgets",
    "required_slots": ["widget_ref"],
    "params": {
        "role_id": "{session.role_id}",
        "widget_ids": "{form.widget_ref|if_numeric}",
        "q": "{form.widget_ref|if_text}",
    },
    "result_mapping": {"list_path": "rows", "id_field": "uid", "label_field": "name",
                       "refine_param": "widget_ids"},
}


def _engine(api_result):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value=api_result)
    return ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=handler)


def _cfg():
    return ConversationalConfig(
        key="widget_diag", persona_role="property_manager", grounding_scope=FAKE_GS,
        topic_scope={"mode": "category", "category": "條件診斷:小工具"})


def _state(**extra):
    return {"config_key": "widget_diag", "collected_fields": {"widget_ref": "藍色"},
            "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
            "asked_count": 1, **extra}


# ── (A) 走通三路：1/0/N，全由第二面向的 result_mapping 驅動 ──
@pytest.mark.req("conversational-diagnosis:6.3")
async def test_second_facet_one_row_converges_via_its_mapping():
    eng = _engine({"success": True, "data": {"rows": [{"uid": 7, "name": "藍色小工具"}]},
                   "formatted_response": "狀態：運轉中"})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "converge"
    assert "藍色小工具" in r["grounding"] and "運轉中" in r["grounding"]


@pytest.mark.req("conversational-diagnosis:6.1")
async def test_second_facet_zero_and_many_rows():
    eng0 = _engine({"success": True, "data": {"rows": []}})
    assert (await eng0._ground_by_api(_state(), _cfg()))["kind"] == "ask"

    engN = _engine({"success": True, "data": {"rows": [
        {"uid": 7, "name": "藍色小工具"}, {"uid": 8, "name": "紅色小工具"}]}})
    rN = await engN._ground_by_api(_state(), _cfg())
    assert rN["kind"] == "ask"
    assert rN["candidates"] == [{"id": 7, "label": "藍色小工具"}, {"id": 8, "label": "紅色小工具"}]


# ── (A) 候選選擇輪：第二面向同樣走通（required_slots 設選定 id）──
@pytest.mark.req("conversational-diagnosis:6.2")
async def test_second_facet_candidate_selection_no_code_change():
    eng = _engine({"success": True, "data": {"rows": [{"uid": 8, "name": "紅色小工具"}]}})
    eng._save = AsyncMock()
    state = _state(pending_candidates=[{"id": 7, "label": "藍色小工具"}, {"id": 8, "label": "紅色小工具"}])
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "2", config=_cfg())  # 選第 2 筆
    assert decision["kind"] == "converge"
    assert state["collected_fields"]["widget_ref"] == 8   # 設到第二面向的 required_slots[0]
    assert "pending_candidates" not in state


# ── (B) 靜態掃描：診斷程式元件無合約字面硬編 ──
_FORBIDDEN = ["jgb_contracts", "contract_ref", "contract_ids", "條件診斷"]


def _assert_no_contract_literal(src, where):
    for lit in _FORBIDDEN:
        assert lit not in src, f"{where} 不應出現合約字面硬編：{lit}"


@pytest.mark.req("conversational-diagnosis:6.1")
def test_no_contract_hardcode_in_engine_components():
    for fn in (_has_basic_info, _match_candidate, ce._ask_pick_again, ce._dig_path):
        _assert_no_contract_literal(inspect.getsource(fn), f"engine.{fn.__name__}")
    for m in (ConversationalEngine._ground_by_api, ConversationalEngine.prepare):
        _assert_no_contract_literal(inspect.getsource(m), f"ConversationalEngine.{m.__name__}")


@pytest.mark.req("conversational-diagnosis:6.2")
def test_no_contract_hardcode_in_config_and_routing():
    _assert_no_contract_literal(inspect.getsource(cc.config_for_category), "config_for_category")
    _assert_no_contract_literal(inspect.getsource(cc._load), "conversational_config._load")
    _assert_no_contract_literal(inspect.getsource(chat._knowledge_category), "_knowledge_category")
    _assert_no_contract_literal(
        inspect.getsource(chat._diagnosis_config_for_knowledge), "_diagnosis_config_for_knowledge")
