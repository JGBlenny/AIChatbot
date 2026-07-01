"""unit:引擎注入 per-領域系統脈絡鍵（domain-conversational-facets 任務 1.2 / R2.1, R2.2）。

引擎兩處呼叫 `_get_system_context` 皆須傳領域鍵（= config.persona_role），使合約診斷
注入合約領域脈絡、售前注入售前（base）脈絡：
  - prepare 主流程收斂前取 system_md；
  - 插點 A（pending_candidates 選擇輪）單筆收斂前取 system_md。
mock 隔離，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine():
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}}
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value={"kind": "converge", "grounding": "G"})
    return eng


def _api_cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})


# ── prepare 主流程：以 persona_role 為領域鍵取 system_md（R2.1/R2.2）──
@pytest.mark.req("domain-conversational-facets:2.2")
async def test_prepare_threads_persona_role_as_domain_key():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {"contract_ref": "基隆"}, "asked_count": 2})
    decision = await eng.prepare("s1", "u1", 7, "查我合約", config=_api_cfg())
    assert decision["kind"] == "converge"
    eng._get_system_context.assert_awaited_with(eng.db_pool, "狀態判斷")


# ── 插點 A（候選選擇輪）：單筆收斂前亦以領域鍵取 system_md（R2.2）──
@pytest.mark.req("domain-conversational-facets:2.2")
async def test_candidate_selection_threads_persona_role():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {},
        "pending_candidates": [{"id": 11, "label": "基隆A"}, {"id": 22, "label": "基隆B"}]})
    decision = await eng.prepare("s1", "u1", 7, "2", config=_api_cfg())  # 選第 2 筆
    assert decision["kind"] == "converge"
    eng._get_system_context.assert_awaited_with(eng.db_pool, "狀態判斷")
