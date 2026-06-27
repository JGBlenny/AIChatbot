"""knowledge-admin 後端測試前置（layer-first 架構,對齊 rag-orchestrator 慣例）。

- 匯入路徑:把 backend/ 加進 sys.path,測試可 `from app import app`。
- `client` fixture:FastAPI TestClient + 以 dependency_overrides 蓋掉 JWT 登入(測試免 token)。
- `db` fixture:psycopg2 連線(autocommit)供測試 setup/assert/cleanup。
- integration 層在未設 RUN_INTEGRATION=1 時標示略過(避免無 DB 時假失敗)。
"""
import os
import sys

import pytest

# backend/ 根目錄(本檔位於 backend/tests/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def pytest_collection_modifyitems(config, items):
    """integration 預設略過,除非 RUN_INTEGRATION=1。"""
    run_integration = os.getenv("RUN_INTEGRATION") == "1"
    skip_integration = pytest.mark.skip(
        reason="需真實 DB,未設 RUN_INTEGRATION=1 → 標示略過"
    )
    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)


@pytest.fixture
def client():
    """TestClient + 蓋掉登入依賴(get_current_user)。"""
    from fastapi.testclient import TestClient
    from app import app
    from routes_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": 0, "username": "__test__"}
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """測試用 DB 連線(autocommit;供 setup/assert/cleanup)。"""
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )
    conn.autocommit = True
    yield conn
    conn.close()
