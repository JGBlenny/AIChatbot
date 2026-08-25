"""unit：`skip_refine` 語義重現（spec conversational-routing-execution 任務 7.1）。

⚠️ **本檔不主張哪一邊是正確語義**（那是 7.2 的裁決）；只把 7.1 要求的情境**重現成證據**：

```text
候選 > candidate_cap → 分流列候選 → 選定候選 → **重查** → 是否收斂單筆？
```

⚠️ 為何走 `prepare()` 而不是只呼 `_ground_by_api`：「選定後重查」發生在 prepare 的
**插點 A**（pre-LLM 候選選擇輪）。只測 `_ground_by_api` 會漏掉真正要驗的那一段。

⚠️ 零 OpenAI、零 DB：brain 不參與（插點 A 在 brain 之前返回），api_handler 為替身。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.unit

CAP = 8
MAPPING = {"list_path": "data", "id_field": "id", "label_field": "title",
           "label_fields": ["title", "date_expire", "total"],
           "label_date_fields": ["date_expire"], "candidate_cap": CAP,
           "skip_refine": True, "entity_noun": "帳單"}


def _cfg():
    """對齊 production `bill_diagnosis` 的形狀（含 required_slots，插點 A 靠它填槽）。"""
    return ConversationalConfig(
        key="bill_diagnosis", persona_role="pm_bill_diagnosis",
        grounding_scope={"select": "api", "endpoint": "jgb_bills",
                         "params": {"role_id": "{session.role_id}"},
                         "search_params": [{"bill_ref": "{form.bill_ref}"}],
                         "required_slots": ["bill_ref"], "result_mapping": MAPPING},
        topic_scope={"mode": "category", "category": "條件診斷：帳單"})


def _bills(n):
    return [{"id": 900000 + i, "title": f"2026-{i:02d} 房租", "date_expire": "20260731",
             "total": 20000} for i in range(1, n + 1)]


def _engine(responses):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(side_effect=responses)
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="ctx"),
        rules_loader=AsyncMock(return_value="rules"), api_handler=handler)
    eng._save = AsyncMock()
    return eng


def _state():
    return {"config_key": "bill_diagnosis",
            "collected_fields": {"bill_ref": "重慶北137-503"},
            "role_id": 37305, "vendor_id": 2, "session_id": "s1", "user_id": "u1",
            "asked_count": 1}


@pytest.mark.req("conversational-routing-execution:5.1")
async def test_over_cap_then_pick_then_requery_converges_to_single_row():
    """7.1 重現：26 筆 > cap → 直接列候選 → 回「3」→ 重查 → **收斂單筆**。"""
    picked_row = {"id": 900003, "title": "2026-03 房租", "date_expire": "20260731",
                  "total": 20000}
    eng = _engine([
        {"success": True, "data": {"data": _bills(26)}},                     # 第一查：26 筆
        {"success": True, "data": {"data": [picked_row]},                    # 重查：1 筆
         "formatted_response": "帳單「2026-03 房租」狀態：待繳費。"},
    ])
    cfg, st = _cfg(), _state()

    # ── 第一輪：分流列候選（skip_refine=True → 不進補識別輪）──
    r1 = await eng._ground_by_api(st, cfg)
    assert r1["kind"] == "ask"
    cands = r1["candidates"]
    assert len(cands) == CAP and st.get("_refine_requested") is None

    # ── 第二輪：使用者回序號 → 走 prepare 的插點 A（pre-LLM，brain 不參與）──
    st["pending_candidates"] = cands
    eng.get_state = AsyncMock(return_value=st)
    decision = await eng.prepare(session_id="s1", user_id="u1", vendor_id=2,
                                 user_message="3", config=cfg, start_if_absent=False)

    assert decision is not None and decision["kind"] == "converge", \
        f"選定候選後未收斂：{decision}"
    assert st["collected_fields"]["bill_ref"] == cands[2]["id"], "選定值未填入 required_slots[0]"
    assert st.get("pending_candidates") is None, "候選未清除（會影響下一輪）"
    assert "2026-03 房租" in decision["grounding"]
    # brain 未被呼叫——插點 A 是 pre-LLM
    eng.optimizer.conversational_step_result.assert_not_called()


@pytest.mark.req("conversational-routing-execution:5.1")
async def test_skip_refine_does_not_change_the_result_set():
    """語義定位證據：skip_refine 只影響**是否多問一輪**，不影響候選集合本身。"""
    rows = _bills(26)
    legacy_map = {k: v for k, v in MAPPING.items() if k != "skip_refine"}

    eng_a = _engine([{"success": True, "data": {"data": rows}}])
    cfg_a = _cfg()
    r_skip = await eng_a._ground_by_api(_state(), cfg_a)

    eng_b = _engine([{"success": True, "data": {"data": rows}},
                     {"success": True, "data": {"data": rows}}])
    cfg_b = _cfg()
    cfg_b.grounding_scope["result_mapping"] = legacy_map
    st_b = _state()
    r_ask = await eng_b._ground_by_api(st_b, cfg_b)          # 先被要求補識別
    assert "更明確的識別" in r_ask["answer"] and st_b["_refine_requested"] is True
    r_legacy = await eng_b._ground_by_api(st_b, cfg_b)       # 補不動 → 仍列候選

    assert [c["id"] for c in r_skip["candidates"]] == [c["id"] for c in r_legacy["candidates"]], \
        "兩條路徑的候選集合不同——那 skip_refine 就不只是省一輪"
