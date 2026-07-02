"""unit:secondary_call 通用二次查詢（contract-conversational-facets 任務 7.3 / R3.3, R10.2, R10.3）。

grounding_scope 宣告式（未宣告＝不執行，零回歸）：
  {"secondary_call": {"endpoint","params"（支援 {row.<field>} 以主查詢結果列插值；
   {session.*}/{form.*} 留給 handler 既有解析）,"list_path","attach_as"}}
單筆收斂後執行 → 結果 rows 掛在主列 attach_as 鍵 → 以 handler.format_api_result 重格式化
（face 貫穿），facts 含二次資料；失敗/非單筆 → 不執行或沿用主底稿（降級不阻斷）。
formatter 端：build_closeout_facts 讀 attach 的 bills → 個人化未封存清單（G3）；
未 attach → 通用指引（現行降級態）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine, _resolve_row_template
from services.jgb.contracts import ContractBit, build_closeout_facts

pytestmark = pytest.mark.unit


# ── {row.*} 模板插值（通用，不硬編欄位）──
@pytest.mark.req("contract-conversational-facets:10.2")
def test_row_template_resolution():
    row = {"id": 84908, "title": "基隆"}
    assert _resolve_row_template("{row.id}", row) == "84908"
    assert _resolve_row_template("c-{row.id}-{row.title}", row) == "c-84908-基隆"
    assert _resolve_row_template("{session.role_id}", row) == "{session.role_id}"  # 留給 handler
    assert _resolve_row_template(123, row) == 123


def _scope(with_secondary=True):
    s = {
        "select": "api", "endpoint": "jgb_contracts",
        "required_slots": ["contract_ref"],
        "params": {"contract_ids": "{form.contract_ref}"},
        "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"},
    }
    if with_secondary:
        s["secondary_call"] = {"endpoint": "jgb_bills",
                               "params": {"role_id": "{session.role_id}", "contract_ids": "{row.id}"},
                               "list_path": "data", "attach_as": "bills"}
    return s


def _cfg(scope):
    return ConversationalConfig(key="closeout", grounding_scope=scope,
                                topic_scope={"mode": "category", "category": "退租收尾"})


def _engine(primary_rows, sec_result=None, sec_exc=None):
    handler = MagicMock()

    async def route(api_config, session_data, form_data, **kwargs):
        if api_config["endpoint"] == "jgb_bills":
            if sec_exc:
                raise sec_exc
            return sec_result
        return {"success": True, "data": {"data": primary_rows},
                "formatted_response": "PRIMARY"}

    handler.execute_api_call = AsyncMock(side_effect=route)
    handler.format_api_result = MagicMock(return_value="REFORMATTED-WITH-BILLS")
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), api_handler=handler)
    return eng, handler


def _state():
    return {"config_key": "closeout", "collected_fields": {"contract_ref": "84908"},
            "role_id": 20151, "vendor_id": 7, "session_id": "s1", "user_id": "u1",
            "face": "退租收尾"}


# ── 單筆＋宣告 → 執行二次查詢（{row.id} 插值）、attach、重格式化進底稿 ──
@pytest.mark.req("contract-conversational-facets:3.3")
async def test_secondary_runs_attaches_and_reformats():
    row = {"id": 84908, "title": "基隆雅房"}
    bills = [{"id": 714100, "is_archived": False}, {"id": 714096, "is_archived": True}]
    eng, handler = _engine([row], sec_result={"success": True, "data": {"data": bills}})
    r = await eng._ground_by_api(_state(), _cfg(_scope()), user_message="退租收尾")
    assert r["kind"] == "converge"
    # 二次呼叫參數：{row.id} 已插值；{session.*} 原樣留給 handler
    sec_call = [c for c in handler.execute_api_call.call_args_list
                if c.args[0]["endpoint"] == "jgb_bills"]
    assert len(sec_call) == 1
    assert sec_call[0].args[0]["params"]["contract_ids"] == "84908"
    assert sec_call[0].args[0]["params"]["role_id"] == "{session.role_id}"
    # attach 在主列上（formatter 由此取得）
    assert row["bills"] == bills
    # 重格式化（face 傳遞）取代主底稿
    assert "REFORMATTED-WITH-BILLS" in r["grounding"]
    assert handler.format_api_result.call_args.kwargs.get("face") == "退租收尾"


# ── 未宣告 → 只打主查詢、行為與現行完全一致（零回歸）──
@pytest.mark.req("contract-conversational-facets:10.2")
async def test_no_declaration_single_call_unchanged():
    eng, handler = _engine([{"id": 84908, "title": "基隆雅房"}])
    r = await eng._ground_by_api(_state(), _cfg(_scope(with_secondary=False)),
                                 user_message="退租收尾")
    assert r["kind"] == "converge"
    assert handler.execute_api_call.await_count == 1
    assert "PRIMARY" in r["grounding"]
    handler.format_api_result.assert_not_called()


# ── 二次查詢失敗/例外 → 沿用主底稿，不阻斷（R10.3 降級）──
@pytest.mark.req("contract-conversational-facets:10.3")
@pytest.mark.parametrize("sec_kw", [
    {"sec_result": {"success": False, "error": "boom"}},
    {"sec_exc": TimeoutError("upstream")},
])
async def test_secondary_failure_degrades_to_primary(sec_kw):
    eng, handler = _engine([{"id": 84908, "title": "基隆雅房"}], **sec_kw)
    r = await eng._ground_by_api(_state(), _cfg(_scope()), user_message="退租收尾")
    assert r["kind"] == "converge"
    assert "PRIMARY" in r["grounding"]          # 主底稿仍在


# ── 非單筆（N 筆候選）→ 不執行二次查詢 ──
@pytest.mark.req("contract-conversational-facets:3.3")
async def test_secondary_skipped_when_many_rows():
    eng, handler = _engine([{"id": 1, "title": "A"}, {"id": 2, "title": "B"}])
    r = await eng._ground_by_api(_state(), _cfg(_scope()), user_message="退租")
    assert r["kind"] == "ask"
    assert all(c.args[0]["endpoint"] != "jgb_bills"
               for c in handler.execute_api_call.call_args_list)


# ── get_bills 支援 per-contract 查詢（e2e 真跑揪出：不收 contract_ids、硬要 user_id，
#    secondary_call 被靜默降級）：比照 get_contracts——role_id 為 b2b 授權主體、轉送過濾參數 ──
@pytest.mark.req("contract-conversational-facets:3.3")
async def test_get_bills_forwards_contract_ids_without_user_id(monkeypatch):
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    captured = {}

    async def fake_request(path, params):
        captured.update({"path": path, "params": params})
        return {"success": True, "data": []}

    monkeypatch.setattr(api, "_request", fake_request)
    r = await api.get_bills(role_id="20151", contract_ids="84908")
    assert r["success"] is True                       # 不因缺 user_id 降級
    assert captured["params"]["contract_ids"] == "84908"
    assert captured["params"]["role_id"] == "20151"

    # 原有租客情境不變：無 contract_ids 時仍需 user_id（身分保護）
    r2 = await api.get_bills(role_id="20151", user_id=None)
    assert r2["success"] is False


# ── formatter 端：bills attach → 個人化封存 facts（G3；未 attach → 通用指引）──
def _closeout_contract(**over):
    bits = (ContractBit.READY | ContractBit.INVITING | ContractBit.INVITING_NEXT |
            ContractBit.SIGNED | ContractBit.MOVE_OUT | ContractBit.MOVE_OUT_DONE)
    c = {"id": 84908, "title": "基隆雅房", "status": 8, "bit_status": bits,
         "is_history": 0, "is_history_done": 0, "date_start": 20240101,
         "date_end": 99991231, "rent": 20000, "to_user_connect": 1}
    c.update(over)
    return c


@pytest.mark.req("contract-conversational-facets:3.3")
def test_closeout_facts_personalized_unarchived_bills():
    bills = [{"id": 714100, "is_archived": False}, {"id": 714096, "is_archived": False},
             {"id": 713817, "is_archived": True}]
    out = build_closeout_facts(_closeout_contract(bills=bills), "還要封存嗎")
    assert "2 筆" in out and "未封存" in out
    assert "714100" in out and "714096" in out      # 指名未封存帳單
    assert "713817" not in out                       # 已封存不列


@pytest.mark.req("contract-conversational-facets:3.3")
def test_closeout_facts_all_archived():
    out = build_closeout_facts(
        _closeout_contract(bills=[{"id": 1, "is_archived": True}]), "")
    assert "皆已封存" in out


@pytest.mark.req("contract-conversational-facets:10.3")
def test_closeout_facts_without_bills_keeps_generic_guide():
    out = build_closeout_facts(_closeout_contract(), "")
    assert "帳單總表" in out                          # 通用指引（G3 前降級態不變）


@pytest.mark.req("contract-conversational-facets:3.3")
def test_history_contract_still_reminds_unarchived_bills():
    out = build_closeout_facts(
        _closeout_contract(is_history=1, bills=[{"id": 9, "is_archived": False}]), "")
    assert "歷史合約" in out
    assert "未封存" in out and "9" in out             # 轉歷史與封存互不相依，仍提醒
