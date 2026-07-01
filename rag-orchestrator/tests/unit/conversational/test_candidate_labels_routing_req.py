"""unit:多筆候選可辨識與過多分流（domain-conversational-facets 任務 3.1/3.2/3.3｜R4.1–4.4, R7.5）。

`_ground_by_api` 之 N 筆分支：
  - 候選 label 由 `result_mapping.label_fields` 依序以「｜」串接，`label_date_fields` 者 Ymd→Y/m/d；
    無 `label_fields` → 回退單 `label_field`（向後相容）。欄位一律讀 result_mapping（零硬編）。
  - `N ≤ candidate_cap` → 列候選（帶區別欄位）供選序號；
  - `N > cap` 首次 → 請補更明確識別重查（無 candidates）；已補過仍 > cap（同名多份）→ 截斷列前 cap 筆並提示可給編號；
  - `candidate_cap` 未設 → 不限（既有行為）。
mock api_handler，確定性 unit。
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
    s = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "基隆"},
         "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1", "asked_count": 1}
    if extra:
        s.update(extra)
    return s


def _cfg(mapping):
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "jgb_contracts", "params": {},
                         "result_mapping": mapping},
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


MAP_MULTI = {"list_path": "data", "id_field": "id", "label_field": "title",
             "label_fields": ["title", "date_start", "date_end", "status"],
             "label_date_fields": ["date_start", "date_end"], "candidate_cap": 3}


# ── 3.1 label_fields 串接 + 日期格式化（R4.1）──
@pytest.mark.req("domain-conversational-facets:4.1")
async def test_label_fields_joined_with_date_format():
    rows = [{"id": 1, "title": "基隆套房", "date_start": "20240115",
             "date_end": "20250114", "status": "生效"}]
    # 單筆走 converge，改測 2 筆以觀察候選 label
    rows2 = rows + [{"id": 2, "title": "基隆套房", "date_start": "20250201",
                     "date_end": "20260131", "status": "已簽待點交"}]
    eng = _engine(rows2)
    r = await eng._ground_by_api(_state(), _cfg(MAP_MULTI))
    assert r["kind"] == "ask"
    labels = [c["label"] for c in r["candidates"]]
    assert labels[0] == "基隆套房｜2024/01/15｜2025/01/14｜生效"
    assert labels[1] == "基隆套房｜2025/02/01｜2026/01/31｜已簽待點交"


# ── 3.1 同名多份靠區別欄位可辨識（R4.1）──
@pytest.mark.req("domain-conversational-facets:4.1")
async def test_same_name_distinguishable_by_extra_fields():
    rows = [{"id": 1, "title": "基隆溫馨一人宅套房", "date_start": "20230101", "date_end": "20240101", "status": "歷史"},
            {"id": 2, "title": "基隆溫馨一人宅套房", "date_start": "20240101", "date_end": "20250101", "status": "生效"}]
    eng = _engine(rows)
    r = await eng._ground_by_api(_state(), _cfg(MAP_MULTI))
    labels = [c["label"] for c in r["candidates"]]
    assert labels[0] != labels[1]          # 同名但可辨識
    assert r["candidates"][0]["id"] == 1 and r["candidates"][1]["id"] == 2


# ── 3.2 N ≤ cap → 列候選（全列）──
@pytest.mark.req("domain-conversational-facets:4.3")
async def test_within_cap_lists_all_candidates():
    rows = [{"id": i, "title": f"物件{i}", "date_start": "20240101", "date_end": "20250101", "status": "生效"}
            for i in range(1, 4)]  # 3 筆，cap=3
    eng = _engine(rows)
    r = await eng._ground_by_api(_state(), _cfg(MAP_MULTI))
    assert r["kind"] == "ask"
    assert len(r["candidates"]) == 3


# ── 3.2 N > cap 首次 → 請補更明確識別（無 candidates），標記 _refine_requested（R4.3）──
@pytest.mark.req("domain-conversational-facets:4.3")
async def test_over_cap_first_asks_to_refine():
    rows = [{"id": i, "title": f"套房{i}", "date_start": "20240101", "date_end": "20250101", "status": "生效"}
            for i in range(1, 6)]  # 5 筆 > cap=3
    st = _state()
    eng = _engine(rows)
    r = await eng._ground_by_api(st, _cfg(MAP_MULTI))
    assert r["kind"] == "ask"
    assert "candidates" not in r          # 不列長清單，改請補條件
    assert st.get("_refine_requested") is True


# ── 3.2 已補過仍 > cap（同名多份）→ 截斷列前 cap 筆 + 提示給編號（R4.3/R4.4）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_over_cap_after_refine_truncates_with_hint():
    rows = [{"id": i, "title": "基隆套房", "date_start": "20240101", "date_end": "20250101", "status": "生效"}
            for i in range(1, 6)]  # 補條件重查仍 5 筆同名
    st = _state({"_refine_requested": True})
    eng = _engine(rows)
    r = await eng._ground_by_api(st, _cfg(MAP_MULTI))
    assert r["kind"] == "ask"
    assert len(r["candidates"]) == 3      # 截斷至 cap
    assert "編號" in r["answer"]           # 提示可給合約編號直接指定


# ── 3.3 無 label_fields → 回退單 label_field（向後相容，R7.5）──
@pytest.mark.req("domain-conversational-facets:7.5")
async def test_no_label_fields_falls_back_to_single_label():
    rows = [{"id": 1, "title": "基隆物件"}, {"id": 2, "title": "台北物件"}]
    eng = _engine(rows)
    r = await eng._ground_by_api(_state(), _cfg(
        {"list_path": "data", "id_field": "id", "label_field": "title"}))
    assert r["candidates"] == [{"id": 1, "label": "基隆物件"}, {"id": 2, "label": "台北物件"}]


# ── 3.3 無 candidate_cap → 不限（既有行為，全列）──
@pytest.mark.req("domain-conversational-facets:7.5")
async def test_no_cap_lists_all():
    rows = [{"id": i, "title": f"物件{i}"} for i in range(1, 11)]  # 10 筆，無 cap
    eng = _engine(rows)
    r = await eng._ground_by_api(_state(), _cfg(
        {"list_path": "data", "id_field": "id", "label_field": "title"}))
    assert len(r["candidates"]) == 10
