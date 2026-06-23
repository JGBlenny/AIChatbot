"""統一測試前置（spec testing-traceability・元件 1・R1.1, R1.3, R2）。

責任：
1. 統一匯入路徑——讓測試可直接 `from services.x import ...` / `from routers.x import ...`，
   以及既有以 `services/` 為根的 bare import（`from form_manager import ...`），
   取代各檔案散落的 `sys.path.insert`（既有檔仍可保留，屬冗餘但無害；R9.1 不改其行為）。
2. 提供共用 fixtures（mock_db_pool / mock_llm / anyio_backend），新測試可直接取用。

本檔僅新增測試前置，不觸碰任何產品執行邏輯（R9.1）。
"""
import os
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock

# rag-orchestrator 根目錄（本檔位於 rag-orchestrator/tests/）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVICES = os.path.join(_ROOT, "services")
for _p in (_ROOT, _SERVICES):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# 既有測試分層（spec testing-traceability 元件 3・R2・任務 2.1–2.3）
#
# 集中於 conftest 以 add_marker 指派 layer，不逐檔改既有測試（最大化 R9.1：零行為改動）。
# 分類依據：於 dev compose（無 DB/redis/外部服務）離線實跑的結果——
#   全綠 → unit；需真實相依（連線錯誤/網路）→ integration；經整服務 → e2e。
# 漸進（R2.5/6.5）：未列入者不報錯，視為「待標記」。
# 新測試（任務 6–9）一律用顯式 @pytest.mark.unit/integration/e2e/req(...)。
# ---------------------------------------------------------------------------

_UNIT_FILES = {
    "test_backtest_similarity_injection.py",
    "test_branch_answer.py",
    "test_chat_debug_fields.py",
    "test_chat_role_id.py",
    "test_chat_shared_has_sop_results.py",
    "test_complete_form_chaining.py",
    "test_complete_form_option_routing.py",
    "test_conversational_chain_context.py",
    "test_conversational_step_and_engine.py",
    "test_conversational_synthesize.py",
    "test_finalize_scores.py",
    "test_form_services.py",
    "test_jgb_api_integration.py",
    "test_llm_answer_optimizer_perfect_match.py",
    "test_llm_answer_optimizer_should_synthesize.py",
    "test_maybe_chain_next_form.py",
    "test_maybe_chain_option_routing.py",
    "test_option_routing_protections.py",
    "test_present_first_field.py",
    "test_resolve_selected_route.py",
    "test_retrieval_types.py",
    "test_sse_chain_streaming.py",
    "test_vendor_retriever_target_user.py",
    "test_vendor_sop_retriever_fields.py",
}

_INTEGRATION_FILES = {
    "test_answer_synthesis.py",
    "test_backward_compat_chaining.py",
    "test_complete_form_chaining_integration.py",
    "test_complete_form_option_routing_integration.py",
    "test_followup_cancel_and_digression.py",
    "test_intent_manager.py",
    "test_intent_suggestion.py",
    "test_leaf_outlets_integration.py",
    "test_loop_knowledge_integration.py",
    "test_migration_1_1.py",
    "test_migration_form_chaining.py",
    "test_migration_form_chaining_db.py",
    "test_payment_gateway_chain_link.py",
    "test_payment_gateway_followup_form.py",
    "test_sop_orchestrator.py",
    "test_sop_orchestrator_simple.py",
    "test_synthesis_override.py",
    # test_real_database.py 已於檔內自標 integration+skip，不在此重複。
}

_E2E_FILES = {
    "test_e2e_payment_gateway_chain.py",
}

# 混合檔：檔內特定測試需真實相依 → 標 integration（離線略過）；其餘留待標記（仍會在預設/all 跑且綠）。
_INTEGRATION_TESTS_EXACT = {
    "test_vendor_knowledge_retriever_fields.py": {
        "test_vector_search_uses_limit_100_default",
        "test_keyword_search_writes_keyword_score_field",
        "test_keyword_search_vector_similarity_defaults_zero",
        "test_keyword_search_keeps_search_method_keyword",
        "test_keyword_search_preserves_keyword_matches",
    },
    "test_sop_modules.py": {
        "test_sop_next_action_handler",
        "test_integrated_flow",
    },
}
# 以函式名前綴標 integration（整段 retrieve() pipeline 需真實相依）
_INTEGRATION_PREFIX = {
    "test_base_retriever_pipeline.py": ("test_retrieve_",),
}
# 以類別名標 integration（nodeid 含該類別）
_INTEGRATION_CLASS = {
    "test_jgb_system_api.py": {"TestErrorHandling"},
}


def _assign_layer(item) -> None:
    """為單一測試項目指派 layer marker（若尚未顯式標記）。"""
    # 已顯式標 layer 的（新測試或自標檔）不覆蓋
    existing = {m.name for m in item.iter_markers()}
    if existing & {"unit", "integration", "e2e"}:
        return
    fname = os.path.basename(str(item.fspath))
    func = item.originalname or item.name.split("[")[0]

    # 混合檔：特定測試 → integration
    if func in _INTEGRATION_TESTS_EXACT.get(fname, set()):
        item.add_marker(pytest.mark.integration)
        return
    for pref in _INTEGRATION_PREFIX.get(fname, ()):  # 前綴
        if func.startswith(pref):
            item.add_marker(pytest.mark.integration)
            return
    for cls in _INTEGRATION_CLASS.get(fname, set()):  # 類別
        if "::%s::" % cls in item.nodeid:
            item.add_marker(pytest.mark.integration)
            return

    if fname in _UNIT_FILES:
        item.add_marker(pytest.mark.unit)
    elif fname in _INTEGRATION_FILES:
        item.add_marker(pytest.mark.integration)
    elif fname in _E2E_FILES:
        item.add_marker(pytest.mark.e2e)
    # 其餘：留白（待標記，漸進，不報錯）


def pytest_collection_modifyitems(config, items):
    """指派 layer，並對需真實相依的層在無相依時標示略過（R4.5/任務 2.3）。

    integration 預設略過，除非 RUN_INTEGRATION=1；e2e 預設略過，除非 RUN_E2E=1。
    如此 CI 預設只跑 unit、離線全綠；真實相依層「標示略過」而非假綠燈。
    """
    for item in items:
        _assign_layer(item)

    run_integration = os.getenv("RUN_INTEGRATION") == "1"
    run_e2e = os.getenv("RUN_E2E") == "1"
    skip_integration = pytest.mark.skip(
        reason="需真實相依（DB/外部服務），未設 RUN_INTEGRATION=1 → 標示略過（R4.5）"
    )
    skip_e2e = pytest.mark.skip(
        reason="需整服務（API/SSE），未設 RUN_E2E=1 → 標示略過（R4.5）"
    )
    for item in items:
        keywords = item.keywords
        if "integration" in keywords and not run_integration:
            item.add_marker(skip_integration)
        if "e2e" in keywords and not run_e2e:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """anyio/pytest-asyncio backend；統一用 asyncio。"""
    return "asyncio"


@pytest.fixture
def mock_db_pool() -> "AsyncMock":
    """共用 asyncpg pool mock。

    支援 `async with pool.acquire() as conn:` 與 conn.fetch/fetchrow/fetchval/execute，
    皆回傳 AsyncMock，測試可依需要覆寫回傳值。
    """
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="")

    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)
    # 方便測試取用底層 conn：pool._conn
    pool._conn = conn
    return pool


@pytest.fixture
def mock_llm() -> "MagicMock":
    """共用 LLM provider mock（決定性回傳）。

    預設 chat_completion 回固定內容；測試可覆寫 return_value 模擬不同決策。
    """
    llm = MagicMock()
    llm.chat_completion = MagicMock(return_value={"content": ""})
    return llm
