"""unit:確定性 contract_ref 抽取（等識別時純數字編號直接填槽，不靠 brain）。

問題：brain（LLM）對純數字識別抽取不穩（如「84800」3 次都沒抽到→一直追問）。
修法：診斷面向等待 required_slot、槽位未填、本句是明確識別（純數字編號）→ 確定性填槽走收斂，
繞過 brain（同插點A：確定性優先於 LLM）。含錯誤情況：查無、非識別、已填、候選選擇中。
mock 隔離，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine, _looks_like_identifier
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


# ── _looks_like_identifier：純數字編號 True；開場句/空/單字 False ──
@pytest.mark.req("domain-conversational-facets:4.4")
def test_looks_like_identifier():
    assert _looks_like_identifier("84800") is True
    assert _looks_like_identifier("678") is True
    assert _looks_like_identifier(" 84972 ") is True         # 去空白
    assert _looks_like_identifier("我的合約狀態怪怪的") is False  # 開場句
    assert _looks_like_identifier("基隆溫馨一人宅套房") is False  # 文字名稱交給 brain
    assert _looks_like_identifier("") is False
    assert _looks_like_identifier("2") is False              # 單字太短（避免誤catch）


# ── _extract_identifier：句中抽 id-like 編號（退掉語意 guard，後端當裁判）──
# 詳見 test_api_validation_flow_req.py：金額/單位不再靠清單擋，抽出交後端探查，
# 查無則回滾保留原合約（不誤切）——避免累積領域特例。此處僅守結構性判斷。
@pytest.mark.req("domain-conversational-facets:4.4")
def test_extract_identifier():
    from services.conversational_engine import _extract_identifier
    assert _extract_identifier("84800") == "84800"              # 純數字
    assert _extract_identifier("那換 84328 呢?") == "84328"      # 文字切換
    assert _extract_identifier("84328 的狀態?") == "84328"
    assert _extract_identifier("可以點退嗎?") is None            # 無 id-like token
    assert _extract_identifier("基隆溫馨一人宅套房") is None      # 文字名稱交 brain


def _engine(ground_result):
    optimizer = MagicMock()
    optimizer.conversational_step = MagicMock()  # 用來斷言「沒被呼叫」
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="MD"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value=ground_result)
    return eng


def _cfg():
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "e", "required_slots": ["contract_ref"],
                         "params": {}, "result_mapping": {"list_path": "data", "id_field": "id",
                                                          "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"})


# ── 純數字編號 → 確定性填槽收斂，brain 不被呼叫 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_pure_number_fills_slot_and_converges_without_brain():
    eng = _engine({"kind": "converge", "grounding": "G"})
    state = {"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "84800", config=_cfg())
    assert d["kind"] == "converge" and d["grounding"] == "G"
    assert state["collected_fields"]["contract_ref"] == "84800"   # 確定性填入
    eng.optimizer.conversational_step.assert_not_called()          # 沒經 brain


# ── 錯誤情況①：編號查無（0 筆）→ ask 查無，不崩 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_invalid_number_zero_rows_asks_not_crash():
    eng = _engine({"kind": "ask", "answer": "查無對應的資料，請再確認識別資訊是否正確？"})
    eng.get_state = AsyncMock(return_value={"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1})
    d = await eng.prepare("s", "u", 7, "99999999", config=_cfg())
    assert d["kind"] == "ask" and "查無" in d["answer"]
    eng.optimizer.conversational_step.assert_not_called()


# ── 錯誤情況②：編號查到多筆同名 → 存 pending_candidates + 列候選 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_number_many_rows_lists_candidates():
    cands = [{"id": 1, "label": "A"}, {"id": 2, "label": "B"}]
    eng = _engine({"kind": "ask", "answer": "找到多筆", "candidates": cands})
    state = {"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "84800", config=_cfg())
    assert d["kind"] == "ask"
    assert state["pending_candidates"] == cands


# ── 錯誤情況③：開場句（非識別）→ 不填槽、走 brain ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_opening_sentence_goes_to_brain():
    eng = _engine({"kind": "converge", "grounding": "G"})
    eng.optimizer.conversational_step.return_value = {
        "action": "ask", "next_question": "請提供合約編號或物件名稱", "extracted_fields": {}, "scope": "stay"}
    state = {"config_key": "contract_diag", "collected_fields": {}, "asked_count": 0}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "我的合約狀態怪怪的", config=_cfg())
    assert d["kind"] == "ask"
    assert "contract_ref" not in state.get("collected_fields", {})  # 未確定性填
    eng.optimizer.conversational_step.assert_called_once()           # 走了 brain


# ── 錯誤情況④：候選選擇中（pending_candidates）→ 插點A 處理，不誤走填槽 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_pending_candidates_not_intercepted_by_slot_fill():
    eng = _engine({"kind": "converge", "grounding": "G"})
    state = {"config_key": "contract_diag", "collected_fields": {},
             "pending_candidates": [{"id": 11, "label": "A"}, {"id": 22, "label": "B"}]}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "84800", config=_cfg())  # 數字但在候選選擇輪
    # 84800 非序號/id/label → 插點A 未命中 → 再列候選（不被 slot-fill 攔）
    assert d["kind"] == "ask" and "哪一筆" in d["answer"]


# ── 查無（0 筆）→ 清掉無效識別槽位（下一句可重新識別）──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_zero_rows_clears_identifier_slot():
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={"success": True, "data": {"data": []}})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    state = {"collected_fields": {"contract_ref": "99999999"}, "role_id": "20151",
             "vendor_id": 7, "session_id": "s", "user_id": "u", "asked_count": 1}
    r = await eng._ground_by_api(state, _cfg())
    assert r["kind"] == "ask" and "candidates" not in r
    assert "contract_ref" not in state["collected_fields"]   # 清掉無效值


# ── 查無後 prepare 存檔（確定性填槽路徑）→ 下一輪 slot 空、可重填 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_prepare_saves_after_zero_rows_so_slot_reusable():
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={"success": True, "data": {"data": []}})
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="MD"), rules_loader=AsyncMock(return_value="R"),
        api_handler=handler)
    eng._save = AsyncMock()
    state = {"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "99999999", config=_cfg())   # 純數字→確定性填→查無
    assert d["kind"] == "ask"
    assert "contract_ref" not in state.get("collected_fields", {})  # 已清
    eng._save.assert_awaited()                                       # 有存檔（清空持久化）


# ── 文字切換另一份合約：slot 已填 84921，句含新編號 84328 → 確定性換合約收斂 ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_switch_contract_via_text_number():
    eng = _engine({"kind": "converge", "grounding": "G"})
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "84921"},
             "asked_count": 2, "pending_candidates": None}
    eng.get_state = AsyncMock(return_value=state)
    d = await eng.prepare("s", "u", 7, "那換 84328 呢?", config=_cfg())
    assert d["kind"] == "converge"
    assert state["collected_fields"]["contract_ref"] == "84328"   # 換成新編號
    eng.optimizer.conversational_step.assert_not_called()


# ── 同一編號的追問（84328 已填 + 問題）→ 不攔截、走 brain ──
@pytest.mark.req("domain-conversational-facets:4.4")
async def test_same_number_followup_goes_to_brain():
    eng = _engine({"kind": "converge", "grounding": "G"})
    eng.optimizer.conversational_step.return_value = {
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}, "scope": "stay"}
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "84328"}, "asked_count": 2}
    eng.get_state = AsyncMock(return_value=state)
    await eng.prepare("s", "u", 7, "84328 可以點退嗎?", config=_cfg())  # 同編號 → 非切換
    eng.optimizer.conversational_step.assert_called_once()  # 走 brain（追問，非重新識別）
