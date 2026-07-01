"""unit:不回歸——售前只吃 base、無新設定＝既有行為（domain-conversational-facets 任務 5.2｜R7.1–7.5）。

- 售前（prospect）：領域鍵 prospect 無領域 append → 只回 base（與現況一致，脈絡內容不變）。
- 向後相容：無 domain_key（chat.py 直答路徑）→ 只回 base。
- 診斷既有能力：select!='api' 走既有 `_converge_grounding`（不觸發 api 路）；
  未設 label_fields/candidate_cap → 候選回退既有單 label、全列（既有行為）。
mock，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.system_context import get_system_context, reset_cache
from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear():
    reset_cache()
    yield
    reset_cache()


class _Pool:
    def __init__(self, base, appends):
        self._base, self._appends = base, appends

    def acquire(self):
        base, appends = self._base, self._appends

        class _Conn:
            async def fetchrow(self, sql, *args):
                if "target_user IS NULL" in sql:
                    return {"answer": base}
                if "target_user @>" in sql:
                    v = appends.get(args[1])
                    return {"answer": v} if v else None
                return None

            async def fetch(self, sql, *args):
                return []

        conn = _Conn()

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


# ── R7.1/R7.4 售前只吃 base（不被領域化波及）──
@pytest.mark.req("domain-conversational-facets:7.1")
async def test_prospect_eats_base_only():
    pool = _Pool(base="售前系統脈絡BASE", appends={"property_manager": "合約架構（不該外洩到售前）"})
    md = await get_system_context(pool, "prospect")
    assert md == "售前系統脈絡BASE"
    assert "合約架構" not in md


# ── R7.5 向後相容：無 domain_key（直答路徑）→ 只回 base ──
@pytest.mark.req("domain-conversational-facets:7.5")
async def test_no_domain_key_backward_compatible():
    pool = _Pool(base="通用BASE", appends={"property_manager": "X"})
    assert await get_system_context(pool) == "通用BASE"


# ── R7.2 診斷既有能力：select!='api' 仍走既有知識 grounding（不觸發 api 路）──
@pytest.mark.req("domain-conversational-facets:7.2")
async def test_non_api_still_uses_existing_converge_grounding():
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "recommend", "extracted_fields": {}}
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock()
    eng._converge_grounding = AsyncMock(return_value=("KG", [{"field_label": "identity", "selected_label": "房東"}], "force"))
    eng.get_state = AsyncMock(return_value={
        "config_key": "presales", "collected_fields": {"identity": "房東", "scale": "50"}, "asked_count": 3})
    cfg = ConversationalConfig(key="presales", persona_role="prospect",
                               grounding_scope={"select": "vector", "target_user": "prospect", "mode": "b2b"})
    decision = await eng.prepare("s1", "u1", 7, "我想了解方案", config=cfg)
    assert decision["kind"] == "converge"
    eng._ground_by_api.assert_not_awaited()
    eng._converge_grounding.assert_awaited_once()


# ── R7.5 候選：未設 label_fields/candidate_cap → 回退既有單 label + 全列 ──
@pytest.mark.req("domain-conversational-facets:7.5")
async def test_candidate_backward_compat_single_label_all_listed():
    rows = [{"id": i, "title": f"物件{i}"} for i in range(1, 13)]  # 12 筆，無 cap
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={"success": True, "data": {"data": rows}})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    cfg = ConversationalConfig(key="d", persona_role="property_manager",
                               grounding_scope={"select": "api", "endpoint": "e", "params": {},
                                                "result_mapping": {"list_path": "data", "id_field": "id",
                                                                   "label_field": "title"}})
    state = {"config_key": "d", "collected_fields": {"contract_ref": "物件"},
             "role_id": 1, "vendor_id": 1, "session_id": "s", "user_id": "u", "asked_count": 1}
    r = await eng._ground_by_api(state, cfg)
    assert len(r["candidates"]) == 12                       # 無 cap → 全列（既有行為）
    assert r["candidates"][0] == {"id": 1, "label": "物件1"}  # 單 label_field（既有行為）
