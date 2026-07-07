"""unit:prepare 插點 B — select=='api' 收斂控制流（conversational-diagnosis 任務 5.1 / R3.4, R3.5, R2.4）。

收斂時若 grounding_scope.select=='api'：呼叫 `_ground_by_api`（而非 `_converge_grounding`）：
  - 回 converge → 以其 grounding 合成（ctx=None、cta 抑制；事實型）；
  - 回 ask（0/N/失敗）→ 發 ask-decision（非 converge）；有 candidates 則寫入
    state['pending_candidates'] 並存檔；維持提問次數保護（asked_count+1，R2.4）。
  - select!='api' → 走既有 `_converge_grounding` 不變。
以 mock 隔離 `_ground_by_api`/`_converge_grounding`，專測 prepare 控制流。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine(ground_result=None, converge_grounding=("KG", None, "force")):
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}}
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value=ground_result)
    eng._converge_grounding = AsyncMock(return_value=converge_grounding)
    return eng


def _state():
    return {"config_key": "contract_diag",
            "collected_fields": {"contract_ref": "基隆"}, "asked_count": 2}


def _api_cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


def _vector_cfg():
    return ConversationalConfig(
        key="presales", persona_role="prospect",
        grounding_scope={"select": "vector", "target_user": "prospect", "mode": "b2b"})


async def _prepare(eng, cfg):
    eng.get_state = AsyncMock(return_value=_state())
    return await eng.prepare("s1", "u1", 7, "我的合約狀態怪怪的", config=cfg)


# ── 1 筆 converge → 以 API grounding 合成 ──
@pytest.mark.req("conversational-diagnosis:3.4")
async def test_api_converge_uses_api_grounding():
    eng = _engine(ground_result={"kind": "converge", "grounding": "API_G"})
    eng.get_state = AsyncMock(return_value=_state())
    decision = await eng.prepare("s1", "u1", 7, "查我合約", config=_api_cfg())
    assert decision["kind"] == "converge"
    assert decision["grounding"] == "API_G"
    assert decision["ctx"] is None
    assert decision["cta_mode"] == "suppress"
    eng._ground_by_api.assert_awaited_once()
    eng._converge_grounding.assert_not_awaited()  # api 路不走既有知識 grounding


# ── 0 筆 ask 降級 → ask-decision、無 candidates、計數+1 ──
@pytest.mark.req("conversational-diagnosis:3.4")
async def test_api_zero_degrades_to_ask_decision():
    eng = _engine(ground_result={"kind": "ask", "answer": "查無，請確認識別資訊"})
    state = _state()
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "查我合約", config=_api_cfg())
    assert decision == {"kind": "ask", "answer": "查無，請確認識別資訊"}
    assert "pending_candidates" not in state
    assert state["asked_count"] == 3          # 提問上限保護維持（R2.4）
    eng._save.assert_awaited()


# ── N 筆 ask 降級 → 寫入 pending_candidates 並存檔 ──
@pytest.mark.req("conversational-diagnosis:3.5")
async def test_api_many_writes_pending_candidates_and_saves():
    cands = [{"id": 1, "label": "基隆物件"}, {"id": 2, "label": "台北物件"}]
    eng = _engine(ground_result={"kind": "ask", "answer": "找到多筆", "candidates": cands})
    state = _state()
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "查我合約", config=_api_cfg())
    assert decision["kind"] == "ask"
    assert state["pending_candidates"] == cands   # 供下一輪選擇（任務 5.2）
    assert state["asked_count"] == 3
    eng._save.assert_awaited()


# ── select!='api' → 既有 _converge_grounding 不變（不觸發 _ground_by_api）──
@pytest.mark.req("conversational-diagnosis:2.4")
async def test_non_api_uses_existing_converge_grounding():
    eng = _engine(converge_grounding=("KNOWLEDGE_G", None, "force"))
    eng.get_state = AsyncMock(return_value=_state())
    decision = await eng.prepare("s1", "u1", 7, "我想了解方案", config=_vector_cfg())
    assert decision["kind"] == "converge"
    assert decision["grounding"] == "KNOWLEDGE_G"
    eng._ground_by_api.assert_not_awaited()
    eng._converge_grounding.assert_awaited_once()
