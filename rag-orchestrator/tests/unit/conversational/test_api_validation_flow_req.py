"""unit:API 驗證式識別流程（後端當裁判，退掉 client 端 id/名稱分類 guard）。

依業界實務（backend match、present candidates、先搜後提交）重構合約識別：
  - `_ground_by_api` 依 `search_params` 依序試（先當 id、查無再當名稱），第一組有結果即止——
    因後端 id 與關鍵字為 AND 不能同送。→ 數字名稱（如 '0626'）當 id 查無會回退當名稱查，不再漏。
  - `_extract_identifier` 拿掉金額/單位語意 guard（特例）：抽到 id-like token 即回，交後端驗。
  - `prepare` 切換識別「先搜後提交」：探查 0 筆則回滾保留原合約、落回 brain，不誤切/不清有效槽。
mock 隔離，確定性 unit。全讀設定，程式不硬編面向欄位。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine, _extract_identifier
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


# ════════ _extract_identifier：退掉語意 guard（結構性判斷保留）════════
@pytest.mark.req("domain-conversational-facets:4.4")
def test_extract_identifier_no_semantic_guard():
    # 明確識別照抽
    assert _extract_identifier("84800") == "84800"            # 純數字
    assert _extract_identifier("那換 84328 呢?") == "84328"    # 句中切換
    assert _extract_identifier("0626") == "0626"              # 數字名稱（後端會當名稱查）
    # 退掉 guard：金額/單位不再靠清單擋，一律抽出交後端判（查無則回滾，不誤切）
    assert _extract_identifier("月租 27000 對嗎?") == "27000"
    assert _extract_identifier("27000元") == "27000"
    # 結構性判斷（非領域特例）：無 id-like token → None 交 brain
    assert _extract_identifier("可以點退嗎?") is None
    assert _extract_identifier("基隆溫馨一人宅套房") is None    # 純文字名稱交 brain
    assert _extract_identifier("") is None


# ── 日期不是識別（結構性 guard）：申請書槽位/租期回答常含日期，抽成識別會誤觸切換探查
#    （e2e 真跑揪出：「異動前租期到 2026/12/30」→ keyword=2026 誤中「20260624實價登錄」多筆）──
@pytest.mark.req("contract-conversational-facets:2.4")
def test_extract_identifier_ignores_date_tokens():
    assert _extract_identifier("異動前租期到 2026/12/30，異動後改成 2028/12/30") is None
    assert _extract_identifier("租期 2027/8/31 改 2029/8/31") is None
    assert _extract_identifier("2026-12-30 到期") is None
    # 日期旁另有獨立識別 → 仍抽得到識別本身
    assert _extract_identifier("83315 租期改到 2028/12/30") == "83315"
    # 純數字整句照舊（含日期整數形——後端當裁判）
    assert _extract_identifier("20260731") == "20260731"


# ════════ _ground_by_api：search_params 依序試（後端當裁判）════════
def _engine_with_handler(side_effect):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(side_effect=side_effect)
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, handler


def _cfg_attempts():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={
            "select": "api", "endpoint": "jgb_contracts", "required_slots": ["contract_ref"],
            "params": {"role_id": "{session.role_id}"},
            "search_params": [
                {"contract_ids": "{form.contract_ref}"},
                {"keyword": "{form.contract_ref}"},
            ],
            "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"},
        },
        topic_scope={"mode": "category", "category": "狀態判斷"})


def _rows_result(rows, formatted="FR"):
    return {"success": True, "data": {"data": rows}, "formatted_response": formatted}


def _state(ref):
    return {"collected_fields": {"contract_ref": ref}, "role_id": "20151",
            "vendor_id": 7, "session_id": "s", "user_id": "u"}


# ── 數字名稱 0626：先當 id 查（0 筆）→ 回退當名稱查（命中）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_numeric_name_falls_back_to_keyword():
    seen = []

    async def side(api_config, session_data, form_data, **kwargs):
        seen.append(api_config["params"])
        if "contract_ids" in api_config["params"]:
            return _rows_result([])                              # 當 id → 查無
        return _rows_result([{"id": 1, "title": "0626"}])        # 當名稱 → 命中

    eng, handler = _engine_with_handler(side)
    r = await eng._ground_by_api(_state("0626"), _cfg_attempts())
    assert r["kind"] == "converge"
    assert handler.execute_api_call.await_count == 2             # 試了兩組
    assert "contract_ids" in seen[0] and "keyword" in seen[1]    # id 先、名稱後


# ── 真 id 84800：第一組（id）即命中 → 不再試名稱組；grounding 開頭帶「id｜名稱」──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_id_hit_skips_name_attempt():
    async def side(api_config, session_data, form_data, **kwargs):
        return _rows_result([{"id": 84800, "title": "台北信義-單人房"}])

    eng, handler = _engine_with_handler(side)
    r = await eng._ground_by_api(_state("84800"), _cfg_attempts())
    assert r["kind"] == "converge"
    assert handler.execute_api_call.await_count == 1            # 命中即止
    # grounding 開頭帶識別值｜名稱 → 讓 LLM 能把使用者用的編號對回這筆事實（不誤判成別筆）
    assert r["grounding"].startswith("84800｜台北信義-單人房")


# ── 名稱多筆同名：第二組命中多筆 → 列候選（帶 candidates）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_name_many_rows_lists_candidates():
    async def side(api_config, session_data, form_data, **kwargs):
        if "contract_ids" in api_config["params"]:
            return _rows_result([])
        return _rows_result([{"id": 1, "title": "0626"}, {"id": 2, "title": "0626"}])

    eng, handler = _engine_with_handler(side)
    r = await eng._ground_by_api(_state("0626"), _cfg_attempts())
    assert r["kind"] == "ask" and len(r.get("candidates") or []) == 2


# ── 兩組都查無 → 0 筆路徑：清無效槽、回追問（不杜撰）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_all_attempts_zero_clears_slot():
    async def side(api_config, session_data, form_data, **kwargs):
        return _rows_result([])

    eng, handler = _engine_with_handler(side)
    st = _state("99999999")
    r = await eng._ground_by_api(st, _cfg_attempts())
    assert r["kind"] == "ask" and "candidates" not in r
    assert handler.execute_api_call.await_count == 2
    assert "contract_ref" not in st["collected_fields"]        # 清無效值


# ── 向後相容：無 search_params → 單組 params 單次呼叫（既有 config 不受影響）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_backward_compat_single_params():
    async def side(api_config, session_data, form_data, **kwargs):
        return _rows_result([{"id": 1, "title": "X"}])

    eng, handler = _engine_with_handler(side)
    cfg = ConversationalConfig(
        key="k", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "e", "required_slots": ["contract_ref"],
                         "params": {"contract_ids": "{form.contract_ref}"},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})
    r = await eng._ground_by_api(_state("1"), cfg)
    assert r["kind"] == "converge"
    assert handler.execute_api_call.await_count == 1


# ════════ prepare 切換識別：先搜後提交（rollback / commit）════════
def _engine_prepare(ground_side):
    optimizer = MagicMock()
    optimizer.conversational_step = MagicMock(return_value={
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}, "scope": "stay"})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="MD"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(side_effect=ground_side)
    return eng


def _cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "e", "required_slots": ["contract_ref"],
                         "params": {}, "result_mapping": {"list_path": "data", "id_field": "id",
                                                          "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})


# ── 切換識別命中 → 提交換合約收斂（不落 brain）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_switch_hit_commits_new_contract():
    async def ground(state, config, **kwargs):
        return {"kind": "converge", "grounding": "G"}

    eng = _engine_prepare(ground)
    state = {"config_key": "contract_diag",
             "collected_fields": {"contract_ref": "84921"}, "asked_count": 2}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "那換 84328 呢?", config=_cfg())
    assert d["kind"] == "converge"
    assert state["collected_fields"]["contract_ref"] == "84328"   # 換成新合約
    eng.optimizer.conversational_step.assert_not_called()          # 命中即止、不經 brain


# ── 切換識別查無（0 筆）→ 回滾保留原合約、落回 brain（不誤切、不清有效槽）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_switch_zero_rows_rolls_back_and_falls_to_brain():
    async def ground(state, config, **kwargs):
        # 模擬真 _ground_by_api：84921 有效→converge；27000 查無→清該槽回 ask（回滾後 brain
        # 對原合約 84921 追問會再打一次 _ground_by_api，此時應命中、不清槽）。
        ref = (state.get("collected_fields") or {}).get("contract_ref")
        if ref == "84921":
            return {"kind": "converge", "grounding": "G(84921)"}
        (state.get("collected_fields") or {}).pop("contract_ref", None)
        return {"kind": "ask", "answer": "查無…"}

    eng = _engine_prepare(ground)
    state = {"config_key": "contract_diag",
             "collected_fields": {"contract_ref": "84921"}, "asked_count": 2}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s", "u", 7, "月租 27000 對嗎?", config=_cfg())
    # 先搜後提交：27000 查無 → 回滾原合約、當作對 84921 的追問走 brain
    assert state["collected_fields"]["contract_ref"] == "84921"    # 原合約保留
    eng.optimizer.conversational_step.assert_called_once()          # 落回 brain


# ── 首次識別查無（原槽本空）→ 回追問請重新識別（無可回滾）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_first_identify_zero_rows_asks_again():
    async def ground(state, config, **kwargs):
        (state.get("collected_fields") or {}).pop("contract_ref", None)
        return {"kind": "ask", "answer": "查無對應的資料…"}

    eng = _engine_prepare(ground)
    state = {"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "99999999", config=_cfg())
    assert d["kind"] == "ask" and "查無" in d["answer"]
    assert "contract_ref" not in state["collected_fields"]         # 清空、下句可重識別
    eng.optimizer.conversational_step.assert_not_called()           # 首次查無不必走 brain
