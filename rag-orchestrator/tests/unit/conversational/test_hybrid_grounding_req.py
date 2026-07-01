"""unit:混合 grounding —— 收斂底稿＝API 現值 ＋ 領域 system_md（domain-conversational-facets 任務 2.1/2.4｜R3.1, R3.5）。

走選項 A（spike 0.1 決策）：領域基底架構走 per-領域 system_md（元件1），混合發生於
`synthesize(grounding=API, system_md=base+領域架構)`——`_ground_by_api` 零改。
本測試驗證：api 收斂決策的 grounding＝API、system_md＝領域脈絡，且 handle 兩者皆傳入 synthesize。
未設 knowledge_ref → 走 system_md（向後相容，不另撈知識）。
mock 隔離 optimizer/_ground_by_api/_get_system_context，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit

DOMAIN_MD = "BASE_PRODUCT\n\n合約架構：12 里程碑…（領域）"


def _engine():
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}}
    optimizer.synthesize_presales_answer = MagicMock(return_value="合成後回覆")
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value=DOMAIN_MD),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value={"kind": "converge", "grounding": "API_現值資料"})
    eng._converge_grounding = AsyncMock()
    return eng


def _cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


# ── 收斂決策：grounding＝API、system_md＝領域脈絡（混合底稿兩者皆備，R3.1）──
@pytest.mark.req("domain-conversational-facets:3.1")
async def test_converge_decision_carries_api_grounding_and_domain_system_md():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {"contract_ref": "678"}, "asked_count": 1})
    decision = await eng.prepare("s1", "u1", 7, "查我合約 678", config=_cfg())
    assert decision["kind"] == "converge"
    assert decision["grounding"] == "API_現值資料"   # API 即時現值
    assert decision["system_md"] == DOMAIN_MD        # 領域基底架構（base+append）
    eng._converge_grounding.assert_not_awaited()      # api 路不另走既有知識 grounding（未設 knowledge_ref）


# ── handle：API grounding 與領域 system_md 兩者皆傳入 synthesize（混合底稿，R3.1/R3.5）──
@pytest.mark.req("domain-conversational-facets:3.1")
async def test_handle_passes_both_api_grounding_and_domain_system_md_to_synthesize():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {"contract_ref": "678"}, "asked_count": 1})
    result = await eng.handle("s1", "u1", 7, "查我合約 678", config=_cfg())
    assert result and result["converged"] is False  # 事實型
    args, _ = eng.optimizer.synthesize_presales_answer.call_args
    # 位置參數：(grounding, ctx, system_md, user_question, cta_mode)
    assert args[0] == "API_現值資料"   # grounding=API 現值
    assert args[2] == DOMAIN_MD        # system_md=領域架構 → LLM 有框架可判斷（非複述）
