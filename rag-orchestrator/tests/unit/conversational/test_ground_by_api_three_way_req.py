"""unit:API grounding 三路結果語意（conversational-diagnosis 任務 4.2 / R3.4, R3.5, R3.6）。

`_ground_by_api` 依筆數三路：
  - 1 筆 → converge，grounding 以 result_mapping 欄位（label）+ formatted_response 組文字；
  - 0 筆 → ask（查無、重問識別，不杜撰，R3.4）；
  - N 筆 → ask + candidates（id/label 取自 result_mapping，R3.5）；
  - API 例外/逾時/失敗 → 安全 ask（不拋出、不阻斷，R3.6）。
mock api_handler，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


GSCOPE = {
    "select": "api",
    "endpoint": "jgb_contracts",
    "required_slots": ["contract_ref"],
    "params": {"role_id": "{session.role_id}", "keyword": "{form.contract_ref|if_text}"},
    "result_mapping": {
        "list_path": "data", "id_field": "id",
        "label_field": "title", "refine_param": "contract_ids",
    },
}


def _engine_with_handler(handler):
    return ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)


def _engine(api_result):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value=api_result)
    return _engine_with_handler(handler), handler


def _state():
    return {"config_key": "contract_diag", "collected_fields": {"contract_ref": "基隆"},
            "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
            "asked_count": 1}


def _cfg():
    return ConversationalConfig(
        key="contract_diag", grounding_scope=GSCOPE,
        topic_scope={"mode": "category", "category": "條件診斷:合約"})


# ── 1 筆：grounding 結合 result_mapping 欄位 + formatted_response ──
@pytest.mark.req("conversational-diagnosis:3.4")
async def test_one_row_grounding_combines_label_and_formatted_response():
    eng, _ = _engine({
        "success": True,
        "data": {"data": [{"id": 1, "title": "基隆物件"}]},
        "formatted_response": "狀態：已簽約待點交，月租 12,000"})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "converge"
    # result_mapping label_field（物件名）與 formatted_response 細節都進 grounding
    assert "基隆物件" in r["grounding"]
    assert "已簽約待點交" in r["grounding"]


# ── 0 筆：不杜撰，重問識別（R3.4）──
@pytest.mark.req("conversational-diagnosis:3.4")
async def test_zero_rows_reasks_identification():
    eng, _ = _engine({"success": True, "data": {"data": []}})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "ask"
    assert "candidates" not in r
    assert r.get("answer")  # 重問識別之文字


# ── N 筆：候選 id/label 取自 result_mapping（R3.5）──
@pytest.mark.req("conversational-diagnosis:3.5")
async def test_many_rows_return_candidates_from_mapping():
    eng, _ = _engine({"success": True, "data": {"data": [
        {"id": 1, "title": "基隆物件"}, {"id": 2, "title": "台北物件"}, {"id": 3, "title": "桃園物件"}]}})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "ask"
    assert r["candidates"] == [
        {"id": 1, "label": "基隆物件"}, {"id": 2, "label": "台北物件"}, {"id": 3, "label": "桃園物件"}]
    # 反問文字應列出候選標籤
    assert "基隆物件" in r["answer"] and "台北物件" in r["answer"]


# ── 例外/逾時：安全 ask，不拋出（R3.6）──
@pytest.mark.req("conversational-diagnosis:3.6")
async def test_api_exception_returns_safe_ask_without_raising():
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(side_effect=TimeoutError("upstream timeout"))
    eng = _engine_with_handler(handler)
    r = await eng._ground_by_api(_state(), _cfg())  # 不應拋出
    assert r["kind"] == "ask"
    assert "candidates" not in r
    assert r.get("answer")


# ── 失敗回應（success=False）：安全 ask 降級（R3.6）──
@pytest.mark.req("conversational-diagnosis:3.6")
async def test_api_unsuccessful_response_returns_safe_ask():
    eng, _ = _engine({"success": False, "error": "API 調用失敗"})
    r = await eng._ground_by_api(_state(), _cfg())
    assert r["kind"] == "ask"
    assert "candidates" not in r
