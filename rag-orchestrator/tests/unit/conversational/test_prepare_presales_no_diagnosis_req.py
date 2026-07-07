"""unit:售前不觸發診斷兩插點（conversational-diagnosis 任務 5.3 / R7.1, 7.x 不回歸）。

售前（select≠api 且無 pending_candidates）時，prepare 完全走既有 LLM step + `_converge_grounding`：
插點 A（候選選擇）與插點 B（api grounding）皆不觸發，`_ground_by_api` 永不呼叫。

補充：插點 B 三路（converge/ask/存候選）、插點 A（命中→收斂/未命中→反問）、`_match_candidate`
序號/名稱/id 比對，已分別由 test_prepare_api_converge_req.py（5.1）、
test_prepare_candidate_selection_req.py、test_match_candidate_req.py（5.2）覆蓋（同 spec 需求標記）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine(step):
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = step
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value={"kind": "converge", "grounding": "SHOULD_NOT_USE"})
    eng._converge_grounding = AsyncMock(return_value=("KNOWLEDGE_G", None, "force"))
    return eng


def _presales_cfg():
    return ConversationalConfig(
        key="presales", persona_role="prospect",
        grounding_scope={"select": "vector", "target_user": "prospect", "mode": "b2b"})


def _presales_state():
    # 售前：無 pending_candidates；identity+scale 足夠（避免基本資訊門檻翻轉）
    return {"config_key": "presales",
            "collected_fields": {"identity": "個人房東", "scale": "30間"}, "asked_count": 3}


# ── 售前收斂：走既有 _converge_grounding，不觸發 api grounding ──
@pytest.mark.req("conversational-diagnosis:7.1")
async def test_presales_converge_uses_knowledge_grounding_not_api():
    eng = _engine({"action": "converge", "converge_kind": "recommend", "extracted_fields": {}})
    eng.get_state = AsyncMock(return_value=_presales_state())
    decision = await eng.prepare("s1", "u1", 7, "我想了解方案", config=_presales_cfg())
    assert decision["kind"] == "converge"
    assert decision["grounding"] == "KNOWLEDGE_G"
    eng._ground_by_api.assert_not_awaited()          # 插點 B 不觸發
    eng.optimizer.conversational_step.assert_called_once()
    eng._converge_grounding.assert_awaited_once()


# ── 售前追問：走既有 LLM ask 分支，兩插點皆不觸發 ──
@pytest.mark.req("conversational-diagnosis:7.1")
async def test_presales_ask_does_not_trigger_either_insertion_point():
    eng = _engine({"action": "ask", "next_question": "請問您的物件規模？", "extracted_fields": {}})
    eng.get_state = AsyncMock(return_value=_presales_state())
    decision = await eng.prepare("s1", "u1", 7, "想找系統", config=_presales_cfg())
    assert decision == {"kind": "ask", "answer": "請問您的物件規模？"}
    eng._ground_by_api.assert_not_awaited()          # 插點 B 不觸發
    eng._converge_grounding.assert_not_awaited()      # ask 分支提前返回
