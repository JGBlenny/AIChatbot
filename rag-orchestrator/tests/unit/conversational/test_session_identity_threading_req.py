"""unit:會話識別（role_id 等）注入 state（conversational-diagnosis 9.x 前置修正 / R3.1）。

`_ground_by_api` 僅收 (state, config)，session_data（role_id/vendor_id/session_id/user_id）必須
來自 state。修正：`_start` 將會話識別寫入 state；`prepare`/`handle` 新增 `role_id` 參數並下傳，
使診斷面向打 jgb2 API 帶得到 role_id（資料權限過濾）。售前 role_id 預設 None，不受影響。
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine():
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=MagicMock())
    # _start 會 INSERT；以 mock pool 取代真 DB
    conn = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    eng.db_pool = MagicMock()
    eng.db_pool.acquire = MagicMock(return_value=cm)
    return eng, conn


@pytest.mark.req("conversational-diagnosis:3.1")
async def test_start_persists_session_identity_into_state():
    eng, conn = _engine()
    state = await eng._start("s1", "u1", 7, "contract_diag", role_id="20151")
    assert state["session_id"] == "s1"
    assert state["user_id"] == "u1"
    assert state["vendor_id"] == 7
    assert state["role_id"] == "20151"
    # 寫入 DB 的 collected_data 也含這些識別（續對話 _ground_by_api 取得 session_data）
    persisted = json.loads(conn.execute.await_args.args[-1])
    assert persisted["role_id"] == "20151" and persisted["session_id"] == "s1"


@pytest.mark.req("conversational-diagnosis:3.1")
async def test_prepare_threads_role_id_to_start():
    eng, _ = _engine()
    eng.get_state = AsyncMock(return_value=None)          # 新會話 → 走 _start
    eng._start = AsyncMock(return_value={"config_key": "contract_diag", "collected_fields": {},
                                         "asked_count": 0, "role_id": "20151"})
    eng._get_system_context = AsyncMock(return_value="SYS")
    eng._load_rules = AsyncMock(return_value=None)        # 無規則 → 早降級（只驗 _start 收到 role_id）
    cfg = ConversationalConfig(key="contract_diag", persona_role="property_manager",
                               grounding_scope={"select": "api"})
    await eng.prepare("s1", "u1", 7, "查我合約", config=cfg, role_id="20151")
    assert eng._start.await_args.kwargs["role_id"] == "20151"


@pytest.mark.req("conversational-diagnosis:3.1")
async def test_ground_by_api_reads_threaded_role_id_from_state():
    """端到端鏈路：_start 注入 → _ground_by_api 的 session_data 帶到 role_id。"""
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(
        return_value={"success": True, "data": {"data": [{"id": 1, "title": "X"}]}})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "基隆"},
             "session_id": "s1", "user_id": "u1", "vendor_id": 7, "role_id": "20151"}
    cfg = ConversationalConfig(
        key="contract_diag",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}})
    await eng._ground_by_api(state, cfg)
    session_data = handler.execute_api_call.await_args.args[1]
    assert session_data["role_id"] == "20151"
