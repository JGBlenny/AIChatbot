"""unit:收斂槽位程式保底（contract-conversational-facets 收尾加固／R2.1, R7.3）。

背景（回測 Run 285/288 揪出）：persona 要求「先取得識別才收斂」，但 LLM 機率性越權——
沒識別就 converge → 引擎打 API 時識別參數空 → 全量撈取後仍只能列候選反問（最貴的查詢
做了追問就能做的事）；無 role_id 情境更直接炸成「忙線」降級句。

保底（決定性，讀設定零硬編）：插點 B（brain converge、select=api）呼叫 API 前檢查
`required_slots` 是否收齊；未齊 → 轉 ask（用 brain 的備用問句），不打 API。
邊界：asked 已達 MAX_ASKS 時不擋（保留強制收斂防死問迴圈的既有行為）；
select=category（建約引導）與無 required_slots 設定（售前）不受影響。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine, MAX_ASKS
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine(brain_step, ground=None):
    optimizer = MagicMock()
    optimizer.conversational_step = MagicMock(return_value=brain_step)
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="MD"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._domain_faces_impl = None
    eng._ground_by_api = AsyncMock(side_effect=ground or
                                   (lambda *a, **k: {"kind": "converge", "grounding": "G"}))
    return eng


def _cfg(select="api", required=("contract_ref",)):
    gs = {"select": select, "endpoint": "jgb_contracts",
          "params": {}, "result_mapping": {"list_path": "data", "id_field": "id",
                                           "label_field": "title"}}
    if required is not None:
        gs["required_slots"] = list(required)
    return ConversationalConfig(key="contract_diag", persona_role="property_manager",
                                grounding_scope=gs,
                                topic_scope={"mode": "category", "category": "狀態判斷"})


def _state(fields=None, asked=1):
    return {"config_key": "contract_diag", "collected_fields": dict(fields or {}),
            "asked_count": asked}


def _converge_step(next_q="請提供合約編號或物件名稱？"):
    return {"action": "converge", "converge_kind": "answer", "extracted_fields": {},
            "scope": "stay", "next_question": next_q}


# ── 越權收斂（識別未齊）→ 轉追問、不打 API（R7.3）──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_converge_without_required_slot_asks_without_api():
    eng = _engine(_converge_step())
    eng.get_state = AsyncMock(return_value=_state())
    d = await eng.prepare("s", "u", 7, "批次續約要怎麼做", config=_cfg(), role_id="20151")
    assert d["kind"] == "ask"
    assert "合約編號" in d["answer"]                      # 用 brain 備用問句
    eng._ground_by_api.assert_not_awaited()               # 不打 API（省全量查詢）


# ── 轉追問計入 asked_count 並保存（維持提問上限保護）──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_guard_ask_counts_and_saves():
    eng = _engine(_converge_step())
    state = _state(asked=2)
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s", "u", 7, "怎麼續約", config=_cfg(), role_id="20151")
    assert state["asked_count"] == 3
    eng._save.assert_awaited()


# ── brain 沒給備用問句 → 通用識別追問（不硬編面向字面）──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_guard_fallback_question_when_brain_gives_none():
    eng = _engine(_converge_step(next_q=None))
    eng.get_state = AsyncMock(return_value=_state())
    d = await eng.prepare("s", "u", 7, "怎麼退租", config=_cfg(), role_id="20151")
    assert d["kind"] == "ask" and "識別" in d["answer"]


# ── 識別已齊 → 照常收斂打 API（零回歸）──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_converge_with_slot_filled_grounds_normally():
    eng = _engine(_converge_step())
    eng.get_state = AsyncMock(return_value=_state({"contract_ref": "85174"}))
    d = await eng.prepare("s", "u", 7, "可以點交嗎", config=_cfg(), role_id="20151")
    assert d["kind"] == "converge"
    eng._ground_by_api.assert_awaited_once()


# ── select=category（建約引導型）不受影響：無識別照樣收斂 ──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_category_select_converges_without_slots():
    eng = _engine(_converge_step())
    eng._converge_grounding = AsyncMock(return_value=("G", None, "suppress"))
    eng.get_state = AsyncMock(return_value=_state())
    d = await eng.prepare("s", "u", 7, "要怎麼開始建約", config=_cfg(select="category"),
                          role_id="20151")
    assert d["kind"] == "converge"


# ── 無 required_slots 設定（售前等）不受影響 ──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_no_required_slots_config_unaffected():
    eng = _engine(_converge_step())
    eng.get_state = AsyncMock(return_value=_state())
    d = await eng.prepare("s", "u", 7, "推薦方案", config=_cfg(required=None), role_id="20151")
    assert d["kind"] == "converge"
    eng._ground_by_api.assert_awaited_once()


# ════════ 身分參數保底：設定要求的 {session.*} 缺值 → 禁打 API、誠實降級 ════════
# （先前行為：參數被靜默丟棄 → 端點 TypeError → 誤導性「忙線」句；零硬編：掃設定模板）

def _engine_ground(api_result=None):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value=api_result or {
        "success": True, "data": {"data": [{"id": 1, "title": "T"}]},
        "formatted_response": "FR"})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, handler


def _gstate(role_id=None):
    s = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "85174"},
         "vendor_id": 7, "session_id": "s1", "user_id": "u1"}
    if role_id is not None:
        s["role_id"] = role_id
    return s


def _gcfg(params=None):
    return ConversationalConfig(
        key="contract_diag",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts",
                         "required_slots": ["contract_ref"],
                         "params": params if params is not None
                         else {"role_id": "{session.role_id}",
                               "contract_ids": "{form.contract_ref}"},
                         "result_mapping": {"list_path": "data", "id_field": "id",
                                            "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})


@pytest.mark.req("contract-conversational-facets:7.3")
async def test_missing_session_param_blocks_api_with_honest_degrade():
    eng, handler = _engine_ground()
    r = await eng._ground_by_api(_gstate(role_id=None), _gcfg(), user_message="狀態")
    assert r["kind"] == "ask"
    assert "身分" in r["answer"]                          # 誠實說明，不是「忙線」
    assert "忙線" not in r["answer"]
    handler.execute_api_call.assert_not_awaited()          # 禁打 API


@pytest.mark.req("contract-conversational-facets:7.3")
async def test_session_param_present_grounds_normally():
    eng, handler = _engine_ground()
    r = await eng._ground_by_api(_gstate(role_id="20151"), _gcfg(), user_message="狀態")
    assert r["kind"] == "converge"
    handler.execute_api_call.assert_awaited_once()


@pytest.mark.req("contract-conversational-facets:7.3")
async def test_config_without_session_templates_unaffected():
    eng, handler = _engine_ground()
    r = await eng._ground_by_api(_gstate(role_id=None),
                                 _gcfg(params={"contract_ids": "{form.contract_ref}"}),
                                 user_message="狀態")
    assert r["kind"] == "converge"                         # 設定沒要 session 參數 → 不擋
    handler.execute_api_call.assert_awaited_once()


# ── 達 MAX_ASKS 強制收斂時不擋（保留防死問迴圈的絕對上限行為）──
@pytest.mark.req("contract-conversational-facets:7.3")
async def test_guard_yields_at_max_asks():
    eng = _engine(_converge_step())
    eng.get_state = AsyncMock(return_value=_state(asked=MAX_ASKS))
    d = await eng.prepare("s", "u", 7, "就是不給編號", config=_cfg(), role_id="20151")
    assert d["kind"] == "converge"                        # 上限 → 放行（列候選總比卡死好）
    eng._ground_by_api.assert_awaited_once()
