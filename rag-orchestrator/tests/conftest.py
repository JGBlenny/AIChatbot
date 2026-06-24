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
# 測試分層（spec testing-traceability 元件 3・R2）
#
# 全測試一律以顯式 @pytest.mark.unit/integration/e2e 標記層級（檔頭 pytestmark 或逐函式）。
# 舊有「按檔名集中指派 layer」的清單已隨舊測試移除而退場——不再需要。
# 本檔只負責：依顯式 marker 套用 skip gate（integration/e2e 在無相依時標示略過）。
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """依顯式 marker 套用 skip gate（R4.5）。

    integration 預設略過，除非 RUN_INTEGRATION=1；e2e 預設略過，除非 RUN_E2E=1。
    如此 CI 預設只跑 unit、離線全綠；真實相依層「標示略過」而非假綠燈。
    層級一律由各測試以顯式 @pytest.mark.unit/integration/e2e 自標，conftest 不再代為指派。
    """
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
