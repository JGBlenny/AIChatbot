"""unit：候選過多分流之 skip_refine 旗標（帳單診斷 e2e 逼出）。

真相：引擎 N > candidate_cap 的第一輪固定「請補更明確識別」再查——對合約這招有效
（關鍵字可縮小），對「同一合約的多期帳單」無效（補租期/物件名縮不了 26 期），
白耗一輪且訊息寫死「合約較多」。修法：`result_mapping.skip_refine`（設定驅動，
預設關＝零回歸）→ 直接截斷列前 cap 筆供選序號；`entity_noun` 讓訊息名詞跟面向走。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _engine(rows):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(
        return_value={"success": True, "data": {"data": rows}})
    return ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)


def _state(extra=None):
    s = {"config_key": "bill_diagnosis", "collected_fields": {"bill_ref": "重慶北137-503"},
         "role_id": 37305, "vendor_id": 2, "session_id": "s1", "user_id": "u1", "asked_count": 1}
    if extra:
        s.update(extra)
    return s


def _cfg(mapping):
    return ConversationalConfig(
        key="bill_diagnosis", persona_role="pm_bill_diagnosis",
        grounding_scope={"select": "api", "endpoint": "jgb_bills", "params": {},
                         "result_mapping": mapping},
        topic_scope={"mode": "category", "category": "條件診斷：帳單"})


def _bills(n):
    return [{"id": 700 + i, "title": f"2026-{i:02d} 房租", "date_expire": "20260731",
             "total": 20000} for i in range(1, n + 1)]


MAP = {"list_path": "data", "id_field": "id", "label_field": "title",
       "label_fields": ["title", "date_expire", "total"],
       "label_date_fields": ["date_expire"], "candidate_cap": 8,
       "skip_refine": True, "entity_noun": "帳單"}


async def test_skip_refine_lists_candidates_directly():
    """26 筆 > cap=8 且 skip_refine → 不請補識別，直接列前 8 筆候選供選序號。"""
    eng = _engine(_bills(26))
    st = _state()
    r = await eng._ground_by_api(st, _cfg(MAP))
    assert r["kind"] == "ask"
    assert len(r.get("candidates") or []) == 8
    assert "更明確的識別" not in r["answer"]
    assert st.get("_refine_requested") is None      # 不進補識別輪


async def test_entity_noun_in_truncation_message():
    """訊息名詞跟設定走：帳單面向不得出現寫死的「合約」。"""
    eng = _engine(_bills(26))
    r = await eng._ground_by_api(_state(), _cfg(MAP))
    assert "合約" not in r["answer"]
    assert "帳單" in r["answer"]


async def test_default_refine_flow_unchanged():
    """零回歸：未設 skip_refine → 第一輪仍請補更明確識別（既有行為）。"""
    legacy = {k: v for k, v in MAP.items() if k not in ("skip_refine", "entity_noun")}
    eng = _engine(_bills(26))
    st = _state()
    r = await eng._ground_by_api(st, _cfg(legacy))
    assert "更明確的識別" in r["answer"]
    assert st.get("_refine_requested") is True
