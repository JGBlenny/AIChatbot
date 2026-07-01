"""unit:prepare 插點 A — pre-LLM 候選選擇輪（conversational-diagnosis 任務 5.2 / R3.5, R2.2, R2.3）。

state 有 pending_candidates 時，本輪為「選擇」：以 `_match_candidate` 確定性比對（不經 LLM step）：
  - 命中 → 設 id 槽位（讀 required_slots，不硬編）、清候選 → 走單筆 api 收斂；
  - 未命中 → 再次列出反問（仍不收斂，保留候選）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit

CANDS = [{"id": 1, "label": "基隆物件"}, {"id": 2, "label": "台北物件"}]


def _engine(ground_result):
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}}
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value=ground_result)
    return eng


def _state_with_candidates():
    return {"config_key": "contract_diag", "collected_fields": {"contract_ref": "基隆"},
            "asked_count": 1, "pending_candidates": [dict(c) for c in CANDS]}


def _api_cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts",
                         "required_slots": ["contract_ref"], "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


# ── 命中 → 設 id 槽位、清候選、單筆收斂（不經 LLM step）──
@pytest.mark.req("conversational-diagnosis:3.5")
async def test_hit_sets_slot_clears_candidates_and_converges():
    eng = _engine(ground_result={"kind": "converge", "grounding": "PICKED_G"})
    state = _state_with_candidates()
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "2", config=_api_cfg())  # 選第 2 筆
    assert decision["kind"] == "converge"
    assert decision["grounding"] == "PICKED_G"
    # required_slots[0] 設為選定 id（讀設定，不硬編欄位）
    assert state["collected_fields"]["contract_ref"] == 2
    assert "pending_candidates" not in state
    eng._ground_by_api.assert_awaited_once()
    eng.optimizer.conversational_step.assert_not_called()  # 不依賴 LLM step


@pytest.mark.req("conversational-diagnosis:2.3")
async def test_hit_by_label_substring_converges():
    eng = _engine(ground_result={"kind": "converge", "grounding": "G"})
    state = _state_with_candidates()
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "台北", config=_api_cfg())
    assert decision["kind"] == "converge"
    assert state["collected_fields"]["contract_ref"] == 2  # 台北物件 → id 2
    eng.optimizer.conversational_step.assert_not_called()


# ── 未命中 → 再次列出反問，保留候選，不收斂 ──
@pytest.mark.req("conversational-diagnosis:2.2")
async def test_miss_reasks_and_retains_candidates():
    eng = _engine(ground_result={"kind": "converge", "grounding": "X"})
    state = _state_with_candidates()
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "看不懂", config=_api_cfg())
    assert decision["kind"] == "ask"
    assert "基隆物件" in decision["answer"] and "台北物件" in decision["answer"]
    assert state["pending_candidates"] == CANDS      # 候選保留
    eng._ground_by_api.assert_not_awaited()
    eng.optimizer.conversational_step.assert_not_called()
