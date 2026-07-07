"""unit:通用性零硬編（domain-conversational-facets 任務 5.1｜R6.1, R6.2, R6.3）。

(A) 第二個「假領域」（欄位名與合約全不同）僅加資料即得：
    - per-領域系統脈絡疊加（領域鍵＝任意 target_user）；
    - 候選 label_fields 帶區別欄位（欄位名全由 result_mapping 指定）——無需改任何程式。
(B) 靜態掃描：新程式（system_context 疊加載入 + _ground_by_api 候選建構 _build_candidate_label/_fmt_ymd）
    無合約端點/欄位/分類字面硬編（合約字面只存在於設定/種子/測試）。
mock，確定性 unit。
"""
import inspect

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import system_context as sc
from services.system_context import get_system_context, reset_cache
from services import conversational_engine as ce
from services.conversational_engine import ConversationalEngine, _build_candidate_label, _fmt_ymd
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear():
    reset_cache()
    yield
    reset_cache()


# ── 假領域的疊加脈絡 pool（欄位名/鍵與合約無關）──
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

        conn = _Conn()

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


# ── (A1) 假領域 per-領域脈絡疊加：只加資料即得（R6.2）──
@pytest.mark.req("domain-conversational-facets:6.2")
async def test_fake_domain_layering_data_only():
    pool = _Pool(base="共用BASE", appends={"gadget_agent": "小工具領域架構KB"})
    md = await get_system_context(pool, "gadget_agent")
    assert md == "共用BASE\n\n小工具領域架構KB"      # 假領域也疊加，無需改程式


# ── (A2) 假領域候選 label_fields：欄位名全由 result_mapping 指定（R6.1/R6.3）──
FAKE_MAP = {"list_path": "rows", "id_field": "uid", "label_field": "name",
            "label_fields": ["name", "color", "expiry"], "label_date_fields": ["expiry"],
            "candidate_cap": 5}


def _engine(rows):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={"success": True, "data": {"rows": rows}})
    return ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)


@pytest.mark.req("domain-conversational-facets:6.1")
async def test_fake_domain_candidate_labels_from_mapping():
    rows = [{"uid": 7, "name": "小工具", "color": "藍", "expiry": "20260101"},
            {"uid": 8, "name": "小工具", "color": "紅", "expiry": "20270101"}]
    eng = _engine(rows)
    state = {"config_key": "gadget", "collected_fields": {"widget_ref": "小工具"},
             "role_id": 1, "vendor_id": 1, "session_id": "s", "user_id": "u", "asked_count": 1}
    cfg = ConversationalConfig(key="gadget", persona_role="gadget_agent",
                               grounding_scope={"select": "api", "endpoint": "mock_widgets",
                                                "params": {}, "result_mapping": FAKE_MAP})
    r = await eng._ground_by_api(state, cfg)
    labels = [c["label"] for c in r["candidates"]]
    assert labels == ["小工具｜藍｜2026/01/01", "小工具｜紅｜2027/01/01"]   # 全由 mapping 驅動


# ── (B) 靜態掃描：新程式無合約字面硬編 ──
_FORBIDDEN = ["jgb_contracts", "contract_ref", "contract_ids", "條件診斷",
              "bit_status", "father_id", "里程碑"]


def _scan(src, where):
    for lit in _FORBIDDEN:
        assert lit not in src, f"{where} 不應出現領域字面硬編：{lit}"


@pytest.mark.req("domain-conversational-facets:6.1")
def test_no_domain_literal_in_system_context():
    for fn in (sc.get_system_context, sc._fetch_base, sc._fetch_appends, sc._fetch_category_chain):
        _scan(inspect.getsource(fn), f"system_context.{fn.__name__}")


@pytest.mark.req("domain-conversational-facets:6.1")
def test_no_domain_literal_in_candidate_builders():
    for fn in (_build_candidate_label, _fmt_ymd, ce.ConversationalEngine._ground_by_api):
        _scan(inspect.getsource(fn), f"engine.{getattr(fn, '__name__', fn)}")
