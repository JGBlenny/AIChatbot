"""unit：主線第 3 步 A+ 片——出卡只由程式依草稿觸發（模型自呼 `confirm.request` 改為提議）。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-card-program-only-aplus-20261019.md` §4.1 AP-0～AP-6；
凍結驗收清單同目錄 `acceptance-card-program-only-aplus-20261019.md` 的**單元＋DB 證據**：
V1（AP-R1／AP-R2）、V4 (a)～(m)（AP-R3／AP-R7）、V5（AP-R4）、V8 新增條目 (1)～(7)、V9 開關 off 正對照；
r3（計畫 §9）：V13 (A) (a)～(o)（AP-R10）。

裝置沿用 `test_step3_write_lifecycle_req.py`：`_World`＝同一張 `FakeTokenDB`（有狀態的
`agent_confirmation_tokens`，只認 `tools/confirm.py` 的 SQL 常數）＋真 `mcp_facade.build_registry`＋
真 `JGBSystemAPI`／`JGBMockTransport`（`assistant_demo_vendor4.json`）；全部離線。
「寫入次數」＝`_Reg.results` 中 `jgb2.action.*` 的呼叫數（兌現段唯一的寫入出口）。
期望值由測試自己寫死（fixture 人工查證，同 step3 檔）：67338「學生獨立套房可租補」、67652「基隆溫馨
一人宅套房」帳單 709744（2026-11 那期，到期 2026-11-01）、合約 89481。
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from datetime import date

import pytest

from services.agent import name_match as NM
from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.agent_session import (
    DOCUMENT_CARRY_KEY, ESTATE_CARRY_KEY, IMAGE_SUGGESTION_KEY, LAST_SUBMITTED_KEY,
    PENDING_CONFIRM_KEY, SELECT_SCOPE_KEY, WRITE_DRAFT_KEY, AgentSession,
)
from services.agent.budget import Budget
from services.agent.confirm_card import CONFIRMATION_REQUIRED_TEXT, ConfirmCardError
from services.agent.runtime import (
    PENDING_DRAFT_PAYLOAD_KEY, WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY,
    AgentRuntime,
)
from services.agent.tools import confirm as C
from services.jgb import bills as _bills

from tests.unit.agent.test_assistant_documents_photos_req import _meta
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeVerifier, VerifierVerdict, _fake_message, _fake_response,
    _fake_tool_call,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — fixture 匯入
    CORRECT_TEXT, NEW_DESC, REPAIR_TEXT, TODAY, _correct_intent, _env, _intent_mod,
    _manual_bill_card, _submitted, _two_cards, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    KEELUNG_ESTATE, STUDENT_ESTATE, _call, _confirm_args, _intent, _out, _Provider, _RulesVerifier,
)
from tests.unit.agent.token_db_double import FakeTokenDB

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-card-program-only-aplus")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


PROPOSAL_ENV = WF.WRITE_PROPOSAL_ENV
REPAIR_FIELDS = {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷"}


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
async def _turn_p(w: _World, message, script, *, intents=None, budget=None,
                  program_first: bool = False, readonly_view: bool = False, state=None):
    """同 `_World.turn`，另回 provider（看送給模型的 tool 結果）並可換 `Budget`。"""
    provider = _Provider(list(script), intents)
    verifier = (_RulesVerifier if program_first else FakeVerifier)([VerifierVerdict(ok=True)] * 6)
    rt = AgentRuntime(provider, w.reg, verifier, FakeAssembler(), budget or Budget(), stage="M1",
                      clock=FakeClock(), db_pool=w.db, readonly_view=readonly_view)
    res = await rt.run_turn(w.ident, message, w.state if state is None else state)
    assert rt._write_intent_calls == {}
    return res, provider


def _multi(*calls):
    """一則 message 帶多個 tool_calls：`calls`＝[(name, args, id), …]。"""
    return _fake_response(_fake_message(tool_calls=[
        _fake_tool_call(name, args, call_id=cid) for name, args, cid in calls]))


def _proposal(payload: dict, call_id: str = "c1"):
    return _call("confirm.request", _confirm_args(payload), call_id=call_id)


def _tool_contents(provider) -> list:
    """最後一次送給主模型的訊息中所有 tool 訊息內容（含資料段包裝；訊息串逐回累積，取最後一次即全部）。"""
    if not provider.calls:
        return []
    return [str(m.get("content")) for m in provider.calls[-1].get("messages") or []
            if isinstance(m, dict) and m.get("role") == "tool"]


def _sent_payload(args: dict) -> dict:
    return json.loads(args["payload"])


def _render_fails(*_a, **_kw):
    raise ConfirmCardError("injected")


def _restate(w: _World, *, program_first: bool = True, **extra):
    """使用者重述同樣的值（意圖呼叫回同值）。"""
    fields = {**REPAIR_FIELDS, **extra}
    return w.turn(REPAIR_TEXT, script=[_out()], intents=[_intent("repair_create", **fields)],
                  program_first=program_first)


def _still_valid(res, pid, lead=WF.CARD_STILL_VALID_TEXT):
    assert res.answer.startswith(lead + "\n"), res.answer
    assert res.outcome["state"] == "confirm_pending", res.outcome
    assert res.trace.pending_id == pid
    assert WF.V_CARD_STILL_VALID in res.trace.violations
    assert res.quick_replies == C.confirm_quick_replies(pid)
    assert len(res.quick_replies) == 3 and all(pid in r["value"] for r in res.quick_replies)


@pytest.fixture()
def _b_reply_off(monkeypatch):
    """B 片（`AGENT_WRITE_REPLY_PROGRAM`）開關 off＝改前行為：本檔以「提議未發／程式呼叫非終結後交回模型」
    為載具的測試在 off 下照舊驗（正對照）；開關 on 的程式狀態回話由 `test_b_write_replies_program_req.py` 驗。"""
    monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")


# ════════════════════════════════════════════════════════════════════
# V1（AP-R1、AP-R2）：模型自呼 `confirm.request` 只當提議
# ════════════════════════════════════════════════════════════════════
#: 每支動作一組「使用者原話＋模型提議的好值」（好值都在原話裡）。
GOOD = {
    "repair_create": (f"{STUDENT_ESTATE} 冷氣不冷 分類 家電維修 不急",
                      {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷",
                       "category_name": "家電維修", "emergency_status": "1"}),
    "bill_due_extend": (f"{KEELUNG_ESTATE} 11月那期 帳單 709744 延後 7 天",
                        {"estate_name": KEELUNG_ESTATE, "period": "11月那期", "days": 7,
                         "bill_id": 709744}),
    "estate_create": ("新增物件 測試新物件甲 台北市 大安區 某路 1 號 住家 套房 某大樓 2 房 租金 12000 3F",
                      {"title": "測試新物件甲", "city": "台北市", "district": "大安區",
                       "address": "某路 1 號", "use_for": "residential", "space_type": "套房",
                       "building": "某大樓", "room_count": 2, "rent": 12000, "floor": "3F"}),
    "contract_create": (f"{STUDENT_ESTATE} 開合約 2026-11-01 到 2027-10-31 租金 12000 押金 24000 "
                        "w1-test@example.com 0912345678 標題 租約甲",
                        {"estate_name": STUDENT_ESTATE, "date_start": "20261101",
                         "date_end": "20271031", "rent": 12000,
                         "to_user_email": "w1-test@example.com", "to_user_phone": "0912345678",
                         "deposit_amount": 24000, "title": "租約甲"}),
    "manual_bill_create": ("幫我開帳單：合約 89481，名稱 管理費，金額 1000，期限 2026/11/30，說明 十一月",
                           {"contract_ref": "89481", "title": "管理費", "total": 1000,
                            "date_expire": "20261130", "sub_title": "十一月"}),
}

#: 欄位型別 ⇒ (不合值閘的值, 卡上若出現會長成的樣子)。文字／數字／日期／Email／電話／期別＝「不在
#: 使用者原話」；選項＝值域外；分類＝分類樹查無（安全審查 1-4）。
BAD = {
    "text": ("完全沒說過的字", ("完全沒說過的字",)),
    "int": (98765, ("98765", "98,765")),
    "number": (98765.5, ("98765.5", "98,765.5")),
    "date": ("20300105", ("2030/01/05", "20300105")),
    "email": ("nobody-said@example.org", ("nobody-said@example.org",)),
    "phone": ("0987000111", ("0987000111",)),
    "period": ("2030年3月", ("2030", )),
    "enum": ("Z9", ("Z9",)),
    "category": ("外星維修", ("外星維修",)),
    # 「選對紀錄」片（AGENT_PICK_RIGHT 預設 on）：延期繳費的「您說的計費期間」（客人講的起訖，程式解析）。
    "range": ("3/3到4/4", ("3/3到4/4", "03/03~04/04")),
}


def _v1_cases():
    cases = []
    for action, form in WF.FORMS.items():
        for f in form.fields:
            if f.source == WF.SOURCE_USER_WORDS:
                cases.append(pytest.param(action, f.key, f.kind, id=f"{action}-{f.key}-{f.kind}"))
    return cases


def test_v1_case_table_covers_every_form_action_and_every_user_words_kind():
    """V1 前提自證：參數化涵蓋 `FORMS` 每一支動作、`BAD` 涵蓋每一種使用者原話欄位型別（⛔ 以動作名分支）。"""
    cases = _v1_cases()
    assert {c.values[0] for c in cases} == set(WF.FORMS) == set(GOOD)
    kinds = {f.kind for form in WF.FORMS.values() for f in form.fields
             if f.source == WF.SOURCE_USER_WORDS}
    assert kinds <= set(BAD), kinds - set(BAD)
    assert {"text", "int", "date", "email", "phone", "period", "enum", "category"} <= kinds


@pytest.mark.parametrize("action,key,kind", _v1_cases())
async def test_v1_bad_value_never_reaches_card_and_program_payload_is_the_draft(api, action, key,
                                                                              kind):
    """V1 (a)(b)(c)：提議含一個不合值閘的值 ⇒ 該值不進草稿、不上卡；`registry.call` 收到的
    `confirm.request` 是程式依草稿發出的（payload＝`{action, **to_payload(草稿)}`、summary 常數）；
    出卡時卡上 payload 的草稿部分＝`to_payload(草稿)`；欄位不齊時追問句＝缺欄結果的 `missing_fields_ask_text`。"""
    text, good = GOOD[action]
    bad, shapes = BAD[kind]
    payload = {"action": action, **good, key: bad}
    w = _World()
    res, provider = await _turn_p(w, text, [_proposal(payload), _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    (args, result), = w.reg.confirm_calls()
    draft_fields = w.draft()["fields"]
    expected = {"action": action, **WF.to_payload(action, draft_fields)}
    # (c) registry 收到的是程式的呼叫（本案無照片、無物件記憶 ⇒ 沒有前處理寫入的鍵）
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert _sent_payload(args) == expected
    # 不合值閘的值 ⛔ 進草稿、⛔ 進送出的 payload、⛔ 上卡
    assert draft_fields.get(key) != str(bad) and expected.get(key) != bad
    for shape in shapes:
        assert shape not in res.answer, (shape, res.answer)
    if res.outcome["state"] == "confirm_pending":
        entry = w.pending()[res.trace.pending_id]                      # (a)
        assert entry[PENDING_DRAFT_PAYLOAD_KEY] == WF.to_payload(action, draft_fields)
        assert entry["payload"].get(key) != bad
    else:
        assert res.outcome["state"] == "clarifying", (res.outcome, res.answer)   # (b)
        assert res.answer == C.missing_fields_ask_text(result)
        assert result.data["missing_fields"] == WF.missing_labels(action, expected)
    assert len(provider.calls) == 1                     # 程式出口結束回合：模型只被叫了第一次


@pytest.mark.parametrize("action,key,kind", _v1_cases())
async def test_v1_flag_off_positive_control_model_args_are_executed(api, monkeypatch, action, key,
                                                                    kind):
    """V1 正對照（V9「開關 off 跑 V1 正對照」）：`AGENT_WRITE_PROPOSAL=off` ⇒ 同一份提議照舊以**模型
    參數**呼叫 `confirm.request`（summary＝模型給的「確認」、不合值閘的值原樣送進 registry）。"""
    monkeypatch.setenv(PROPOSAL_ENV, "off")
    text, good = GOOD[action]
    bad, _shapes = BAD[kind]
    payload = {"action": action, **good, key: bad}
    w = _World()
    res, _provider = await _turn_p(w, text, [_proposal(payload), _out(), _out()])
    assert WF.V_WRITE_PROPOSAL not in res.trace.violations
    args, _result = w.reg.confirm_calls()[0]
    assert args["summary"] == "確認"
    assert _sent_payload(args)[key] == bad


@pytest.mark.parametrize("action", sorted(GOOD))
async def test_v1_good_values_issue_the_program_card(api, action):
    """V1 正對照（同一組裝置不是「全部擋下」）：提議全為好值 ⇒ 程式依草稿出卡，卡上 payload 草稿部分
    ＝`to_payload(草稿)`，草稿保留。"""
    text, good = GOOD[action]
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal({"action": action, **good}), _out()])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert WF.V_PROGRAM_CONFIRM in res.trace.violations
    entry = w.pending()[res.trace.pending_id]
    assert entry[PENDING_DRAFT_PAYLOAD_KEY] == WF.to_payload(action, w.draft()["fields"])
    assert set(entry[PENDING_DRAFT_PAYLOAD_KEY]) == set(good)


@pytest.mark.usefixtures("_b_reply_off")
async def test_v1d_second_proposal_in_the_same_turn_gets_a_closed_result_and_no_token(api, monkeypatch):
    """V1 (d)：第一次提議轉成的程式呼叫是非終結結果（render 失敗 ⇒ 無缺欄清單的 `INVALID_INPUT`）⇒
    交回模型；同回合第二次提議 ⇒ 封閉工具結果 `HANDLED_BY_PROGRAM`、`registry.call` 只 1 次、token 表 0 列。
    B 片開關 off（改前行為）：on 時非問句回合在第一次非終結後即由程式狀態回話結束、不再交回模型（KD-3 已移除），
    見 `test_b_write_replies_program_req.py` V3 (b)。"""
    monkeypatch.setattr(C, "render", _render_fails)
    w = _World()
    payload = {"action": "repair_create", **REPAIR_FIELDS}
    res, provider = await _turn_p(w, REPAIR_TEXT, [_proposal(payload, "c1"),
                                                   _proposal(payload, "c2"), _out()])
    assert res.trace.violations.count(WF.V_WRITE_PROPOSAL) == 2
    assert WF.V_PROGRAM_NONTERMINAL in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert len(w.reg.confirm_calls()) == 1
    assert w.db.rows == []
    closed = [c for c in _tool_contents(provider) if "HANDLED_BY_PROGRAM" in c]
    assert len(closed) == 1
    assert STUDENT_ESTATE not in closed[0] and "冷氣不冷" not in closed[0]   # 常數、⛔ 含草稿值
    assert res.outcome["state"] != "confirm_pending"


@pytest.mark.parametrize("forged", ["wdprog", "docprog", "reserved"])
async def test_v1e_forged_program_or_reserved_id_still_takes_the_proposal_branch(api, monkeypatch,
                                                                                forged):
    """V1 (e)：模型送的 tool call id 為 `wdprog-<nonce[:8]>`、`docprog-<nonce[:8]>` 或本回合保留 id
    ⇒ 仍走提議分支（registry 收到的是程式的呼叫）、計入 `tool_calls`；保留 id 記
    `tool_call_id_collides_with_reserved`。"""
    nonce = "abcdef0123456789"
    monkeypatch.setattr(runtime_mod, "new_nonce", lambda: nonce)
    call_id = {"wdprog": f"wdprog-{nonce[:8]}", "docprog": f"docprog-{nonce[:8]}",
               "reserved": runtime_mod.OUTLINE_TOOL_CALL_ID}[forged]
    w = _World()
    res, _p = await _turn_p(w, REPAIR_TEXT,
                            [_proposal({"action": "repair_create", **REPAIR_FIELDS}, call_id), _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert any(r.id == call_id for r in res.trace.tool_calls)
    assert res.outcome["state"] == "confirm_pending", res.answer
    collided = "tool_call_id_collides_with_reserved" in res.trace.violations
    assert collided is (forged == "reserved")


@pytest.mark.parametrize("forged", ["wdprog", "docprog", "reserved"])
async def test_v1e_forged_id_closed_proposal_is_counted_against_the_budget(api, monkeypatch, forged):
    """V1 (e)：偽造 id 的提議走封閉結果時同樣計入預算——`max_tool_calls=1` 下同則第二個呼叫被預算擋下
    （⛔ 執行）；保留 id 在封閉分支同樣記撞名。"""
    nonce = "abcdef0123456789"
    monkeypatch.setattr(runtime_mod, "new_nonce", lambda: nonce)
    call_id = {"wdprog": f"wdprog-{nonce[:8]}", "docprog": f"docprog-{nonce[:8]}",
               "reserved": runtime_mod.OUTLINE_TOOL_CALL_ID}[forged]
    w = _World()
    msg = _multi(("confirm.request", _confirm_args({"action": "no_such_action"}), call_id),
                 ("confirm.request", _confirm_args({"action": "repair_create", **REPAIR_FIELDS}),
                  "c2"))
    res, _p = await _turn_p(w, REPAIR_TEXT, [msg, _out(), _out()], budget=Budget(max_tool_calls=1))
    assert res.trace.violations.count(WF.V_WRITE_PROPOSAL) == 1
    assert w.reg.confirm_calls() == []
    assert [r.id for r in res.trace.tool_calls] == [call_id]
    collided = "tool_call_id_collides_with_reserved" in res.trace.violations
    assert collided is (forged == "reserved")


@pytest.mark.parametrize("max_calls,expect", [(2, 2), (3, 3)])
async def test_v1f_n_proposals_in_one_message_are_each_counted(api, max_calls, expect):
    """V1 (f)：一則 message 帶 3 個 `confirm.request`（動作不在 FORMS ⇒ 封閉 `NO_MATCH`）⇒ 預算逐一計；
    `max_tool_calls=2` 時第三個被預算擋下；`=3` 是正對照（三個都跑）。"""
    w = _World()
    msg = _multi(*[("confirm.request", _confirm_args({"action": "no_such_action"}), f"c{i}")
                   for i in range(3)])
    res, provider = await _turn_p(w, "幫我處理一下", [msg, _out(), _out()],
                                  budget=Budget(max_tool_calls=max_calls))
    assert res.trace.violations.count(WF.V_WRITE_PROPOSAL) == expect
    assert len([r for r in res.trace.tool_calls if r.name == "confirm.request"]) == expect
    assert w.reg.confirm_calls() == []
    assert w.db.rows == []
    assert sum("NO_MATCH" in c for c in _tool_contents(provider)) == expect


@pytest.mark.parametrize("max_calls,expect", [(1, 1), (2, 2)])
async def test_v1f_program_converted_proposal_is_counted_too(api, monkeypatch, max_calls, expect):
    """V1 (f)＋實作約束 1-2：提議**轉成程式呼叫**的那一次照樣計入預算（⛔ 借用 `wd_program`）——
    非終結結果（render 失敗）後同則第二個提議在 `max_tool_calls=1` 下被擋；`=2` 為正對照。"""
    monkeypatch.setattr(C, "render", _render_fails)
    w = _World()
    payload = {"action": "repair_create", **REPAIR_FIELDS}
    msg = _multi(("confirm.request", _confirm_args(payload), "c1"),
                 ("confirm.request", _confirm_args(payload), "c2"))
    res, _p = await _turn_p(w, REPAIR_TEXT, [msg, _out(), _out()],
                            budget=Budget(max_tool_calls=max_calls))
    assert res.trace.violations.count(WF.V_WRITE_PROPOSAL) == expect
    assert len(w.reg.confirm_calls()) == 1


async def test_v1g_write_draft_none_gives_a_closed_result_and_no_registry_call(api, monkeypatch):
    """V1 (g)：開關 on、非排除回合、`acc.write_draft` 為 None ⇒ 封閉結果、⛔ 退回以模型參數執行
    （無 `registry.call`）、token 表 0 列。"""
    original = AgentRuntime._write_draft_begin

    def _begin_then_none(self, acc, *a, **kw):
        original(self, acc, *a, **kw)
        acc.write_draft = None

    monkeypatch.setattr(AgentRuntime, "_write_draft_begin", _begin_then_none)
    w = _World()
    res, provider = await _turn_p(w, REPAIR_TEXT,
                                  [_proposal({"action": "repair_create", **REPAIR_FIELDS}), _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert w.reg.confirm_calls() == []
    assert w.db.rows == []
    assert any("HANDLED_BY_PROGRAM" in c for c in _tool_contents(provider))


async def test_v1h_in_domain_enum_not_said_still_reaches_the_card(api):
    """V1 (h)（既有行為的正對照，非目標第四節）：選項欄位帶值域內、但原話沒說的值 ⇒ 照現行進卡。"""
    w = _World()
    res, _p = await _turn_p(w, REPAIR_TEXT, [_proposal(
        {"action": "repair_create", **REPAIR_FIELDS, "emergency_status": "2"}), _out()])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・急迫程度：緊急" in res.answer
    assert w.draft()["fields"]["emergency_status"] == "2"


async def test_v1_unknown_action_proposal_is_no_match_without_registry_call(api):
    """AP-1 (4)：提議的動作不在 `FORMS` ⇒ 封閉 `NO_MATCH`、不觸發、不建草稿。"""
    w = _World()
    res, provider = await _turn_p(w, "幫我處理一下", [_proposal({"action": "no_such_action"}), _out()])
    assert w.reg.confirm_calls() == [] and w.draft() is None
    assert any("NO_MATCH" in c for c in _tool_contents(provider))
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations


# ── 前處理照舊（照片、物件記憶）——原以模型自呼為載具的既有測試之程式路徑版本 ────────
async def test_aplus_server_photos_replace_model_photo_keys_on_the_program_call(api):
    """原 `test_server_photos_replace_model_photo_keys_and_show_on_card` 的 A+ 版：模型提議夾帶的照片鍵
    ⛔ 進草稿；程式依草稿發出的呼叫經照片前處理帶上伺服器端照片、卡上顯示、照片建議出卡即消耗；
    `draft_payload` 只含草稿鍵（照片鍵是前處理寫入的，不算）。"""
    w = _World()
    w.state = {"agent": {IMAGE_SUGGESTION_KEY: {"category_name": None, "photos": [_meta(1)]}}}
    forged = {"action": "repair_create", **REPAIR_FIELDS, "broken_photos": [_meta(9)],
              "image_ref": "x"}
    res, _p = await _turn_p(w, REPAIR_TEXT, [_proposal(forged), _out()])
    (args, _r), = w.reg.confirm_calls()
    sent = _sent_payload(args)
    assert sent["broken_photos"] == [_meta(1)] and "image_ref" not in sent
    assert {k: v for k, v in sent.items() if k != "broken_photos"} == {
        "action": "repair_create", **WF.to_payload("repair_create", w.draft()["fields"])}
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・附照片：1 張" in res.answer
    entry = w.pending()[res.trace.pending_id]
    assert entry["payload"]["broken_photos"] == [_meta(1)]
    assert entry[PENDING_DRAFT_PAYLOAD_KEY] == WF.to_payload("repair_create", w.draft()["fields"])
    assert IMAGE_SUGGESTION_KEY not in w.state["agent"]


async def test_aplus_estate_carry_fills_the_program_call(api):
    """原 `test_read_point_fills_estate_name_on_a_later_turn` 的 A+ 版：提議沒有物件、物件記憶有值 ⇒
    程式依草稿發出的呼叫經物件記憶前處理補上物件名稱並出卡；`draft_payload` 不含前處理寫入的鍵。"""
    w = _World()
    w.state = {"agent": {ESTATE_CARRY_KEY: {"name": STUDENT_ESTATE, "id": "67338"}}}
    res, _p = await _turn_p(w, "冷氣不冷", [_proposal(
        {"action": "repair_create", "description": "冷氣不冷"}), _out()])
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert _sent_payload(args)["estate_name"] == STUDENT_ESTATE
    assert "estate_carry_applied:estate_name" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer
    entry = w.pending()[res.trace.pending_id]
    assert entry[PENDING_DRAFT_PAYLOAD_KEY] == {"description": "冷氣不冷"}


async def test_aplus_unseen_estate_proposal_ends_with_the_not_found_sentence(api):
    """原 `test_repair_card_for_an_unseen_estate_is_the_fixed_sentence` 的 A+ 版：提議的物件在原話裡、
    但查無 ⇒ 程式呼叫得查無標記 ⇒ 程式固定句結束回合、無 token。

    F12（plan-name-lenient-f12-20261022 §4.4）：名稱寬鬆比對預設 on，名稱查無（寬鬆也落空）的固定句改為
    `name_match.NAME_NOT_FOUND_TEXT`；寬鬆模型每回合至多 1 次、不算主模型呼叫。"""
    w = _World()
    res, provider = await _turn_p(w, "不存在的物件甲 冷氣不冷", [_proposal(
        {"action": "repair_create", "estate_name": "不存在的物件甲", "description": "冷氣不冷"}),
        _out()])
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert res.answer == NM.NAME_NOT_FOUND_TEXT
    assert len(provider.lenient_calls) <= 1
    assert w.db.rows == [] and len(provider.calls) == 1


async def test_aplus_bill_candidates_proposal_ends_with_select_buttons(api, monkeypatch):
    """原 `test_multiple_candidates_become_an_ask_turn_with_select_buttons` 的 A+ 版：提議的期別對到多張
    帳單 ⇒ 程式呼叫得候選 ⇒ 程式點選句＋點選鍵結束回合、無 token、主模型只被叫一次。

    A-2a（DSP-103 Q1 含帳單）：開關 on 時帳單候選按鈕改 `pick:bill:<id>`（見
    test_a2a_write_candidates_req.py）；本題釘 off 驗 `select:` 現行行為逐字不變（A2-R12）。"""
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    w = _World()
    res, provider = await _turn_p(w, f"{KEELUNG_ESTATE} 7月那期 延後 3 天", [_proposal(
        {"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "period": "7月那期", "days": 3}),
        _out()])
    (args, result), = w.reg.confirm_calls()
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert (result.data or {}).get("candidates"), result
    assert res.answer.startswith(runtime_mod.CONFIRM_CANDIDATES_TEXT), res.answer
    assert res.quick_replies and all(r["value"].startswith("select:") for r in res.quick_replies)
    assert w.db.rows == [] and len(provider.calls) == 1


# ════════════════════════════════════════════════════════════════════
# V4（AP-R3、AP-R7）：卡片還在／綁定卡無效時的處置
# ════════════════════════════════════════════════════════════════════
async def test_v4_positive_control_restating_same_values_gets_card_still_valid(api):
    """V4 正對照（V3 的單元版）：全部成立 ⇒「卡片還在，請按確認。」＋同卡、同 pid、三顆鍵、無新 token；
    之後按送出 ⇒ 寫入 1 次。"""
    w = _World()
    r1, pid1 = await w.repair_card()
    card = r1.answer
    res = await _restate(w)
    # 填欄只填答覆修復輪 4（brief-fix5）：B 片生效、讀到值與卡相同 ⇒ 前導句 `CARD_READ_SAME_LEAD`（原 `CARD_STILL_VALID_TEXT`）。
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)
    # B 片 B5（業主裁 Q4，`AGENT_WRITE_REPLY_PROGRAM` 未設＝on）：前導句後列出本回合讀到的值（卡上顯示值）。
    read_line = WF.card_read_values_text([("物件", STUDENT_ESTATE), ("問題描述", "冷氣不冷")])
    assert res.answer == WF.CARD_READ_SAME_LEAD + "\n" + read_line + "\n" + card
    assert res.trace.llm_calls == 0                                # 主模型未被呼叫
    assert w.db.pids(w.session_id) == [pid1]
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert w.writes() == ["jgb2.action.repair_create"]


@pytest.mark.usefixtures("_b_reply_off")
async def test_v4_positive_control_restating_same_values_b_off_is_unchanged(api):
    """正對照（B 片開關 off＝改前行為）：同上情境 ⇒ 固定句＋換行＋整張卡（無讀到的值一行）。"""
    w = _World()
    r1, pid1 = await w.repair_card()
    card = r1.answer
    res = await _restate(w)
    _still_valid(res, pid1)
    assert res.answer == WF.CARD_STILL_VALID_TEXT + "\n" + card


async def test_v4_positive_control_on_the_proposal_path(api):
    """V4 正對照（AP-1 檢查點）：主模型提議同值 ⇒ 同樣回「卡片還在」、無新 token、registry 無新呼叫。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    n_before = len(w.reg.confirm_calls())
    res = await w.turn(REPAIR_TEXT, script=[_proposal({"action": "repair_create", **REPAIR_FIELDS}),
                                            _out()], program_first=False)
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)            # 修復輪 4：原 `CARD_STILL_VALID_TEXT`
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert len(w.reg.confirm_calls()) == n_before
    assert w.db.pids(w.session_id) == [pid1]


async def test_v4a_expired_token_burns_and_issues_a_new_card(api):
    """V4 (a)：token 已過期 ⇒ ⛔「卡片還在」；AP-3：視同燒成功、照常觸發出新卡；舊 pid 兌現失敗。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.advance(10_000)
    res = await _restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert "write_draft_bound_card_expired" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v4b_redeemed_token_without_receipt_is_the_s3_sentence(api):
    """V4 (b)：DB 已兌現（無收據）⇒ S3 固定句、⛔ 出新卡、待確認筆標作廢。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.row(pid1)["redeemed"] = True
    res = await _restate(w)
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert "write_draft_bound_card_redeemed" in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]
    assert w.pending()[pid1].get("invalidated") is True
    assert w.writes() == []


async def test_v4c_invalidated_entry_keeps_current_behaviour(api):
    """V4 (c)：已作廢 ⇒ ⛔「卡片還在」；照現行觸發出新卡（舊卡已作廢，不再比值）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.pending()[pid1]["invalidated"] = True
    res = await _restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert WF.V_CARD_STILL_VALID not in res.trace.violations
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1


@pytest.mark.parametrize("where", ["entry_card_sha", "db_summary_sha", "db_payload_sha"])
async def test_v4d_hash_mismatch_burns_and_issues_a_new_card(api, where):
    """V4 (d)：重排版雜湊與 `card_sha256` 不符、或與 DB `summary_sha256`（及 `payload_sha256`）不符 ⇒
    ⛔「卡片還在」；AP-3 (d)：先燒綁定卡（DB 列 redeemed）、照常觸發出新卡；舊 pid 兌現失敗。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    if where == "entry_card_sha":
        w.pending()[pid1]["card_sha256"] = "0" * 64
    elif where == "db_summary_sha":
        w.db.row(pid1)["summary_sha256"] = "0" * 64
    else:
        w.db.row(pid1)["payload_sha256"] = "0" * 64
    res = await _restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert "write_draft_bound_card_stale" in res.trace.violations
    assert w.db.redeemed(pid1) is True
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1
    assert w.pending()[pid1].get("invalidated") is True
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v4e_receipt_keeps_current_behaviour(api):
    """V4 (e)：已有收據 ⇒ ⛔「卡片還在」；照現行（新草稿、出新卡）；寫入仍只有原本那 1 次。"""
    w = _World()
    pid1 = await _submitted(w)
    res = await _restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert WF.V_CARD_STILL_VALID not in res.trace.violations
    assert res.trace.pending_id != pid1
    assert w.writes() == ["jgb2.action.repair_create"]


async def test_v4f_redeemed_and_expired_without_receipt_is_s3_and_writes_stay_one(api):
    """V4 (f)（安全審查 3-1，模擬 F9 收據遺失）：`redeemed=true` 且已過期、待確認筆沒有收據 ⇒ 已兌現
    優先 ⇒ S3 固定句、⛔ 出新卡、mock 寫入總數 1。"""
    w = _World()
    pid1 = await _submitted(w)
    w.pending()[pid1].pop("receipt")                               # 收據遺失
    w.state["agent"].pop(LAST_SUBMITTED_KEY, None)
    w.db.advance(10_000)
    assert w.db.redeemed(pid1) is True
    res = await _restate(w)
    assert res.answer == CONFIRMATION_REQUIRED_TEXT, res.answer
    assert "write_draft_bound_card_redeemed" in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]
    assert w.writes() == ["jgb2.action.repair_create"]


async def _overdue_bill_card(w: _World, monkeypatch, today: date):
    monkeypatch.setattr(_bills, "_today", lambda: today)
    res = await w.turn(f"{KEELUNG_ESTATE} 11月那期 延後 7 天", intents=[_intent(
        "bill_due_extend", estate_name=KEELUNG_ESTATE, period="11月那期", days="7")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    return res, res.trace.pending_id


def _bill_restate(w: _World):
    return w.turn(f"{KEELUNG_ESTATE} 11月那期 延後 7 天", script=[_out()], intents=[_intent(
        "bill_due_extend", estate_name=KEELUNG_ESTATE, period="11月那期", days="7")])


async def test_v4g_overdue_bill_extend_card_same_day_is_still_valid(api, monkeypatch):
    """V4 (g)（安全審查 2-1）：逾期帳單的延期卡（出卡時起算日＝今天）當天重述同值 ⇒ 回合不拋例外、
    回「卡片還在」。"""
    w = _World()
    r1, pid1 = await _overdue_bill_card(w, monkeypatch, date(2026, 11, 5))
    assert "・起算日：2026/11/05" in r1.answer                      # 前提：真的是逾期卡
    res = await _bill_restate(w)
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)            # 修復輪 4：原 `CARD_STILL_VALID_TEXT`
    assert w.db.pids(w.session_id) == [pid1]


async def test_v4h_overdue_bill_extend_card_after_midnight_follows_ap3d(api, monkeypatch):
    """V4 (h)：同 (g) 但時鐘跨過午夜 ⇒ 重排版不成立（render 例外被接住，⛔ 離開回合）⇒ AP-3 (d)：燒舊卡、
    出新卡（新起算日）；舊 pid 兌現失敗。"""
    w = _World()
    _r1, pid1 = await _overdue_bill_card(w, monkeypatch, date(2026, 11, 5))
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 11, 6))
    res = await _bill_restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert "write_draft_bound_card_stale" in res.trace.violations
    assert w.db.redeemed(pid1) is True
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1
    assert "・起算日：2026/11/06" in res.answer


async def test_v4i_less_than_60s_left_burns_and_issues_a_new_card(api):
    """V4 (i)：剩餘 < 60 秒（仍未過期）⇒ 判 `expired` ⇒ ⛔「卡片還在」；AP-3：燒掉（DB 列 redeemed）、出新卡。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.advance(w.db.row(pid1)["expires_at"] - w.db.now() - 30)
    res = await _restate(w)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert "write_draft_bound_card_expired" in res.trace.violations
    assert w.db.redeemed(pid1) is True
    assert res.trace.pending_id != pid1


async def test_v4i_card_date_before_today_is_not_still_valid(api, monkeypatch):
    """V4 (i)（安全審查 2-3）：卡上日期已早於今天（手動帳單繳費期限 2026/11/30，今天 2026/12/01）⇒
    ⛔「卡片還在」；AP-3 (d) 燒舊卡；新卡也過不了日期閘（非終結）⇒ #9b 固定句；舊 pid 兌現失敗、寫入 0。"""
    w = _World()
    _r1, pid1 = await _manual_bill_card(w)
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 12, 1))
    res = await w.turn("幫我開帳單：合約 89481，名稱 管理費，金額 1000，期限 2026/11/30",
                       script=[_out()], intents=[_intent(
                           "manual_bill_create", contract_ref="89481", title="管理費", total="1000",
                           date_expire="2026-11-30")])
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    assert "write_draft_bound_card_stale" in res.trace.violations
    assert w.db.redeemed(pid1) is True
    assert res.answer == WF.REISSUE_NOT_ISSUED_TEXT
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


@pytest.mark.parametrize("why", ["expired", "stale"])
async def test_v4j_burn_then_program_call_early_exit_is_the_9b_sentence(api, monkeypatch, why):
    """V4 (j)：(a)／(d) 燒卡後程式呼叫早退（render 失敗＝非終結）⇒ #9b 固定句、舊 pid 兌現失敗、寫入 0、
    無新可兌現卡。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    if why == "expired":
        w.db.advance(10_000)
    else:
        w.db.row(pid1)["summary_sha256"] = "0" * 64
    monkeypatch.setattr(C, "render", _render_fails)
    res = await _restate(w)
    assert res.answer == WF.REISSUE_NOT_ISSUED_TEXT, res.answer
    assert w.db.live_pids(w.session_id) == []
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


class _UndefinedColumn(Exception):
    sqlstate = "42703"


@pytest.mark.parametrize("err", [RuntimeError("connection lost"), _UndefinedColumn("pending_id")],
                         ids=["db_error", "42703"])
async def test_v4k_state_query_error_is_missing_and_never_still_valid(api, err):
    """V4 (k)：唯讀查詢遇 DB 例外或 42703 ⇒ 判 `missing`（fail-closed）⇒ ⛔「卡片還在」、S3 固定句、
    ⛔ 出新卡；待確認筆標作廢 ⇒ 之後按送出也不寫入。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.state_error = err
    res = await _restate(w)
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert "write_draft_bound_card_missing" in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]
    w.db.state_error = None
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v4k_pending_token_state_fail_closed_inputs():
    """V4 (k)／安全審查 3-2：`db_pool is None`、`pending_id` 不合 `_PENDING_ID_RE`、session 空、查無列 ⇒
    `missing`（⛔ 查 DB 的情形不送 SQL）；正對照：合法輸入且列存在 ⇒ `live`。"""
    db = FakeTokenDB()
    pid = "0123456789abcdef"
    db.rows.append({"token": "t", "session_id": "s1", "payload_sha256": "p", "summary_sha256": "s",
                    "expires_at": db.now() + 600, "redeemed": False, "pending_id": pid})
    assert (await C.pending_token_state(None, "s1", pid)).state == C.PENDING_STATE_MISSING
    assert (await C.pending_token_state(db, "s1", "not-a-pid")).state == C.PENDING_STATE_MISSING
    assert (await C.pending_token_state(db, "", pid)).state == C.PENDING_STATE_MISSING
    assert db.state_calls == []                                    # 前三種 ⛔ 送 SQL
    assert (await C.pending_token_state(db, "s1", "f" * 16)).state == C.PENDING_STATE_MISSING
    live = await C.pending_token_state(db, "s1", pid, card_sha256="s", payload_sha256="p")
    assert (live.state, live.summary_match, live.payload_match) == (C.PENDING_STATE_LIVE, True, True)
    wrong = await C.pending_token_state(db, "s1", pid, card_sha256="x", payload_sha256="p")
    assert wrong.summary_match is False


async def test_v4k_redeemed_wins_over_expired_in_the_state_query():
    """安全審查 3-1：`redeemed=true` 且已過期 ⇒ `redeemed`（已兌現優先於過期）；未兌現已過期 ⇒ `expired`
    且 `lapsed`；剩 30 秒 ⇒ `expired` 但未 `lapsed`。"""
    db = FakeTokenDB()
    base = {"token": "t", "session_id": "s1", "payload_sha256": "p", "summary_sha256": "s"}
    db.rows += [dict(base, pending_id="a" * 16, expires_at=db.now() - 5, redeemed=True),
                dict(base, pending_id="b" * 16, expires_at=db.now() - 5, redeemed=False),
                dict(base, pending_id="c" * 16, expires_at=db.now() + 30, redeemed=False)]
    a = await C.pending_token_state(db, "s1", "a" * 16)
    b = await C.pending_token_state(db, "s1", "b" * 16)
    c = await C.pending_token_state(db, "s1", "c" * 16)
    assert a.state == C.PENDING_STATE_REDEEMED
    assert (b.state, b.lapsed) == (C.PENDING_STATE_EXPIRED, True)
    assert (c.state, c.lapsed) == (C.PENDING_STATE_EXPIRED, False)


async def test_v4l_q3_draft_cleared_by_idle_then_partial_same_values(api):
    """V4 (l)（業主裁 Q3）：出卡後兩句無關話使草稿被清、卡仍有效；使用者只重述部分同值（問題描述）⇒
    「卡片還在」＋同卡、無新 token、無「還需要」；草稿只含本回合欄位（⛔ 從卡回填）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    for _ in range(WF.DRAFT_IDLE_LIMIT):
        await w.turn("今天天氣如何", script=[_out("好的，有需要再跟我說。")], intents=[_intent("none")])
    assert w.draft() is None and w.db.redeemed(pid1) is False      # 前提
    res = await w.turn("冷氣不冷", script=[_out()],
                       intents=[_intent("repair_create", description="冷氣不冷")])
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)            # 修復輪 4：原 `CARD_STILL_VALID_TEXT`
    assert "還需要" not in res.answer
    assert w.db.pids(w.session_id) == [pid1]
    assert w.draft()["fields"] == {"description": "冷氣不冷"}


async def test_v4l_q3_new_draft_with_a_different_value_triggers_without_backfill(api):
    """V4 (l) 對照：草稿已清後新建同動作草稿、值與卡不同 ⇒ 照現行觸發出新卡（A7 燒掉舊卡）；草稿只含本回合
    欄位（⛔ 從卡回填）——卡上的物件來自既有的物件記憶前處理（出卡寫點記下的物件），⛔ 來自草稿。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    for _ in range(WF.DRAFT_IDLE_LIMIT):
        await w.turn("今天天氣如何", script=[_out("好的，有需要再跟我說。")], intents=[_intent("none")])
    res = await w.turn(NEW_DESC, script=[_out()], intents=[_intent("repair_create", description=NEW_DESC)])
    assert WF.V_CARD_STILL_VALID not in res.trace.violations
    assert w.draft()["fields"] == {"description": NEW_DESC}
    assert "estate_carry_applied:estate_name" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1
    assert w.pending()[res.trace.pending_id][PENDING_DRAFT_PAYLOAD_KEY] == {"description": NEW_DESC}
    assert w.db.live_pids(w.session_id) == [res.trace.pending_id]


async def test_v4m_q2_user_category_dropped_gets_card_unchanged_text(api):
    """V4 (m)（業主裁 Q2）：卡後使用者給的分類對不到分類樹（意圖合併被值閘丟掉）、其餘值同卡 ⇒
    `CARD_UNCHANGED_TEXT`＋同卡、無新 token。"""
    w = _World()
    r1, pid1 = await w.repair_card()
    res = await w.turn(f"{REPAIR_TEXT} 分類是外星維修", script=[_out()], intents=[_intent(
        "repair_create", **REPAIR_FIELDS, category_name="外星維修")])
    _still_valid(res, pid1, lead=WF.CARD_UNCHANGED_TEXT)
    assert res.answer == WF.CARD_UNCHANGED_TEXT + "\n" + r1.answer
    assert "write_intent_category_invalid" in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]


async def test_v4m_q2_control_only_the_model_proposal_value_dropped(api):
    """V4 (m) 對照：只有**模型提議**的值被丟（使用者原話沒說分類）⇒ 仍回「卡片還在」。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    res = await w.turn(REPAIR_TEXT, script=[_proposal(
        {"action": "repair_create", **REPAIR_FIELDS, "category_name": "外星維修"}), _out()],
        program_first=False)
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)            # 修復輪 4：原 `CARD_STILL_VALID_TEXT`
    assert "write_intent_category_invalid" in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]


# ════════════════════════════════════════════════════════════════════
# V5（AP-R4）：正規化值比對
# ════════════════════════════════════════════════════════════════════
async def _period_bill_card(w: _World):
    res = await w.turn(f"{KEELUNG_ESTATE} 11月那期 延後 7 天", intents=[_intent(
        "bill_due_extend", estate_name=KEELUNG_ESTATE, period="11月那期", days="7")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    pid = res.trace.pending_id
    assert w.draft()["fields"]["period"] == "2026/11"              # 前提：草稿存正規化值
    assert w.pending()[pid][PENDING_DRAFT_PAYLOAD_KEY]["period"] == "2026/11"
    return res, pid


@pytest.mark.parametrize("said", ["11月那期", "2026年11月"])
async def test_v5_same_period_said_differently_is_the_same_value(api, said):
    """V5：延期卡由「11月那期」出卡；使用者再說「11月那期」或「2026年11月」⇒ 判相同 ⇒「卡片還在」、不重出卡。"""
    w = _World()
    _r1, pid1 = await _period_bill_card(w)
    res = await w.turn(f"{said} 延後 7 天", script=[_out()], intents=[_intent(
        "bill_due_extend", period=said, days="7")])
    _still_valid(res, pid1, lead=WF.CARD_READ_SAME_LEAD)            # 修復輪 4：原 `CARD_STILL_VALID_TEXT`
    assert w.db.pids(w.session_id) == [pid1]


async def test_v5_positive_control_changing_days_reissues(api):
    """V5 正對照：改天數 ⇒ 重出新卡、舊 pid 兌現失敗。"""
    w = _World()
    _r1, pid1 = await _period_bill_card(w)
    res = await w.turn("延 10 天", script=[_out()], intents=[_intent("bill_due_extend", days="10")])
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id != pid1
    assert "・延後天數：10 天" in res.answer
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


# ════════════════════════════════════════════════════════════════════
# V8 新增條目（安全審查第 5 節）
# ════════════════════════════════════════════════════════════════════
async def test_v8_1_ap1_path_9b_burned_card_then_early_exit(api, monkeypatch):
    """V8 (1)：綁定卡被 A2 燒掉（提議改了問題描述）、提議轉成的程式呼叫早退（render 失敗）⇒ #9b 固定句、
    舊 pid 兌現失敗、寫入 0。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    monkeypatch.setattr(C, "render", _render_fails)
    res = await w.turn(CORRECT_TEXT, script=[_proposal(
        {"action": "repair_create", "estate_name": STUDENT_ESTATE, "description": NEW_DESC}), _out()],
        program_first=False)
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert res.answer == WF.REISSUE_NOT_ISSUED_TEXT, res.answer
    assert w.db.redeemed(pid1) is True and w.db.live_pids(w.session_id) == []
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v8_2_9q_other_session_row_is_missing_and_untouched(api):
    """V8 (2) 9q 型：本 session 的列不在、另一 session 有相同 `pending_id` 的 live 列 ⇒ 本 session 判
    `missing`（S3 固定句）、該列不變。正對照：直接查另一 session 得 `live`。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    own = w.db.row(pid1)
    w.db.rows.remove(own)
    other = dict(own, session_id="another-session", token="other-token")
    w.db.rows.append(other)
    snapshot = dict(other)
    res = await _restate(w)
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert "write_draft_bound_card_missing" in res.trace.violations
    assert other == snapshot
    assert (await C.pending_token_state(w.db, "another-session", pid1)).state == C.PENDING_STATE_LIVE


async def test_v8_3_9aa_stale_save_after_ap3d_still_fails(api):
    """V8 (3) 9aa 型：AP-3 (d) 作廢（DB 摘要不符 ⇒ 燒舊卡出新卡）後，他回合以**舊狀態**存檔（舊 pid 沒有
    作廢標記）⇒ 舊 pid 仍兌現失敗、寫入 0。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    stale = copy.deepcopy(w.state)
    w.db.row(pid1)["summary_sha256"] = "0" * 64
    res = await _restate(w)
    assert res.trace.pending_id != pid1 and w.db.redeemed(pid1) is True
    assert stale["agent"][PENDING_CONFIRM_KEY][pid1].get("invalidated") is not True
    old = await w.turn(f"confirm_submit:{pid1}", state=stale)
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v8_4_9g_on_the_proposal_path(api):
    """V8 (4) 9g 型：送出後，主模型提議改值、意圖判定「修改剛送出的那一筆」⇒ `_write_draft_submitted_exit`
    固定句、無新卡、⛔ 建草稿（提議寫進的草稿撤回）、寫入 1 次。"""
    w = _World()
    pid1 = await _submitted(w)
    res = await w.turn(CORRECT_TEXT, script=[_proposal(
        {"action": "repair_create", "estate_name": STUDENT_ESTATE, "description": NEW_DESC}), _out()],
        intents=[_intent_mod("repair_create", True, description=NEW_DESC)], program_first=False)
    assert res.answer == WF.SUBMITTED_EDIT_TEXT, res.answer
    assert WF.V_SUBMITTED_EDIT_BLOCKED in res.trace.violations
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert w.db.pids(w.session_id) == [pid1]
    assert w.draft() is None
    assert w.writes() == ["jgb2.action.repair_create"]


@pytest.mark.parametrize("values", ["same", "changed"])
async def test_v8_5_9i_readonly_view_proposal_changes_nothing(api, values):
    """V8 (5) 9i 型：`readonly_view=True` 下主模型提議（同值＝AP-2／AP-3 檢查、改值＝AP-1）⇒ token 表與
    `agent_state`（`dialog` 以外）都不變。"""
    w = _World()
    await w.repair_card()
    desc = "冷氣不冷" if values == "same" else NEW_DESC
    state_before = copy.deepcopy(w.state)
    rows_before = copy.deepcopy(w.db.rows)
    await w.turn(f"{STUDENT_ESTATE} {desc}", script=[_proposal(
        {"action": "repair_create", "estate_name": STUDENT_ESTATE, "description": desc}), _out(),
        _out()], intents=_correct_intent(), program_first=False, readonly_view=True)
    assert w.db.rows == rows_before
    strip = lambda st: {k: v for k, v in st["agent"].items() if k != "dialog"}   # noqa: E731
    assert strip(w.state) == strip(state_before)


@pytest.mark.parametrize("path", ["model", "program_first", "after_output"])
async def test_v8_6_9l_proposal_off_two_cards_first_one_is_dead(api, monkeypatch, path):
    """V8 (6) 9l 型：`AGENT_WRITE_PROPOSAL=off` 時 9a 仍通過（任一路徑出第二張卡 ⇒ 第一張兌現失敗）。"""
    monkeypatch.setenv(PROPOSAL_ENV, "off")
    w = _World()
    p1, p2 = await _two_cards(w, path)
    assert w.db.live_pids(w.session_id) == [p2]
    old = await w.turn(f"confirm_submit:{p1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_v8_7_proposal_without_a_card_leaves_the_token_table_unchanged(api):
    """V8 (7)：提議沒發卡的回合（動作不在 FORMS ⇒ 封閉結果）token 表不變（含既有綁定卡那一列）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    rows_before = copy.deepcopy(w.db.rows)
    res = await w.turn("幫我處理一下", script=[_proposal({"action": "no_such_action"}), _out()],
                       program_first=False)
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert w.db.rows == rows_before


def test_aplus_switch_unset_empty_on_off_and_invalid(monkeypatch):
    """AP-0：`AGENT_WRITE_PROPOSAL` 未設／空字串＝on、`off`＝off、其他值啟動即失敗（附原因）。"""
    assert WF.write_proposal_enabled_from_env({}) is True
    assert WF.write_proposal_enabled_from_env({PROPOSAL_ENV: ""}) is True
    assert WF.write_proposal_enabled_from_env({PROPOSAL_ENV: "off"}) is False
    with pytest.raises(ValueError):
        WF.write_proposal_enabled_from_env({PROPOSAL_ENV: "maybe"})
    monkeypatch.setenv(PROPOSAL_ENV, "maybe")
    with pytest.raises(ValueError):
        AgentRuntime(_Provider([]), None, FakeVerifier([]), FakeAssembler(), Budget(), stage="M1",
                     clock=FakeClock())


@pytest.mark.parametrize("off", ["AGENT_WRITE_DRAFT", "AGENT_WRITE_LIFECYCLE", PROPOSAL_ENV])
async def test_aplus_active_only_when_all_three_switches_are_on(api, monkeypatch, off):
    """AP-0：三個開關任一 off ⇒ 提議分支不啟用（模型參數照現行執行，summary＝模型給的「確認」）。"""
    monkeypatch.setenv(off, "off")
    w = _World()
    res, _p = await _turn_p(w, REPAIR_TEXT,
                            [_proposal({"action": "repair_create", **REPAIR_FIELDS}), _out()])
    assert WF.V_WRITE_PROPOSAL not in res.trace.violations
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == "確認"


# ════════════════════════════════════════════════════════════════════
# V13 (A)（AP-R10，計畫 §9.2）：r3 AP-7——巢狀提議解一層、提議沒有值進草稿時由程式接住
# ════════════════════════════════════════════════════════════════════
ACTIONS = sorted(WF.FORMS)
#: 草稿「特殊值」與原話片段（V13 (f)：回覆 ⛔ 含任何草稿值或原話片段）。
SPECIAL = "ZQ特殊值ZQ"
SPECIAL_SAID = "ZQ原話片段ZQ"
NO_VALUE_MARKS = (WF.V_WRITE_PROPOSAL_NO_VALUE, WF.V_WRITE_PROPOSAL_NO_VALUE_CARD)


def _nested(action: str, inner, *, as_str: bool = False) -> dict:
    """巢狀提議 `{action, payload:{…}}`（內層 dict 或 JSON 字串）。"""
    return {"action": action, "payload": json.dumps(inner, ensure_ascii=False) if as_str else inner}


def _text_key(action: str) -> str:
    """該表單第一個 `user_words`、`text` 型欄位（取自表單宣告，⛔ 以動作名分支）。"""
    return next(f.key for f in WF.FORMS[action].fields
                if f.source == WF.SOURCE_USER_WORDS and f.kind == "text")


def _seed_draft(w: _World, action: str, fields: dict, *, asked=()) -> None:
    agent = w.state.setdefault("agent", {})
    agent[WRITE_DRAFT_KEY] = {"action": action, "fields": dict(fields), "idle_turns": 0,
                              "created_by_role": runtime_mod._write_draft_owner(w.ident),
                              "asked": list(asked)}


async def _card(w: _World, action: str):
    """以好值提議出一張程式卡（V1 正對照同一路徑；待確認筆帶 `draft_payload`）。"""
    text, good = GOOD[action]
    res, _p = await _turn_p(w, text, [_proposal({"action": action, **good}), _out()])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert PENDING_DRAFT_PAYLOAD_KEY in w.pending()[res.trace.pending_id]
    return res, res.trace.pending_id


def _no_value_text(w: _World, action: str) -> str:
    return WF.proposal_no_value_text(action, WF.to_payload(action, w.draft()["fields"]))


def _assert_no_value_text(res, provider, w: _World, action: str) -> None:
    """(f) 的出口形狀：`PROPOSAL_NO_VALUE_TEXT`、`clarifying`／expects text／草稿動作、無卡、模型只被叫提議那一次。"""
    assert res.answer == _no_value_text(w, action), res.answer
    assert res.outcome == {"state": "clarifying", "expects": "text", "action": action, "ref": None}
    assert res.trace.pending_id is None and not res.quick_replies
    assert WF.V_WRITE_PROPOSAL_NO_VALUE in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NO_VALUE_CARD not in res.trace.violations
    assert WF.V_CARD_STILL_VALID not in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED not in res.trace.violations
    assert len(provider.calls) == 1                     # ⛔ 模型寫回覆
    assert w.reg.confirm_calls() == [] or all(
        a["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY for a, _r in w.reg.confirm_calls())


def test_v13_case_table_has_a_text_field_for_every_action():
    """V13 前提自證：每支動作都有 `user_words` 文字欄位（(f)(h) 參數化依它取鍵）。"""
    assert {a: _text_key(a) for a in ACTIONS}


# ── (a)(b) 巢狀提議解一層 ─────────────────────────────────────────────
@pytest.mark.parametrize("as_str", [False, True], ids=["inner_dict", "inner_json_str"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13a_nested_proposal_is_unwrapped_and_the_program_issues_the_card(api, action, as_str):
    """V13 (a)：巢狀提議（內層 dict／JSON 字串）⇒ 內層值經值閘進草稿、程式出卡；卡上 payload＝
    `to_payload(草稿)`、記 `write_proposal_unwrapped`。對照：r2 只讀頂層鍵（0 鍵合併）。"""
    text, good = GOOD[action]
    w = _World()
    res, provider = await _turn_p(w, text, [_proposal(_nested(action, {"action": action, **good},
                                                              as_str=as_str)), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED not in res.trace.violations
    (args, _r), = w.reg.confirm_calls()
    draft_fields = w.draft()["fields"]
    assert set(draft_fields) == set(good)
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert _sent_payload(args) == {"action": action, **WF.to_payload(action, draft_fields)}
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert w.pending()[res.trace.pending_id][PENDING_DRAFT_PAYLOAD_KEY] == WF.to_payload(
        action, draft_fields)
    assert len(provider.calls) == 1


@pytest.mark.parametrize("as_str", [False, True], ids=["inner_dict", "inner_json_str"])
@pytest.mark.parametrize("action,key,kind", _v1_cases())
async def test_v13b_nested_bad_value_never_reaches_draft_or_card(api, action, key, kind, as_str):
    """V13 (b)：內層含不合值閘的值（同 V1 依欄位型別）⇒ 該值 ⛔ 進草稿、⛔ 進送出的 payload、⛔ 上卡；
    registry 收到的仍是程式依草稿發出的呼叫。"""
    text, good = GOOD[action]
    bad, shapes = BAD[kind]
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal(_nested(action, {"action": action, **good, key: bad},
                                                        as_str=as_str)), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations
    (args, result), = w.reg.confirm_calls()
    draft_fields = w.draft()["fields"]
    expected = {"action": action, **WF.to_payload(action, draft_fields)}
    assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    assert _sent_payload(args) == expected
    assert draft_fields.get(key) != str(bad) and expected.get(key) != bad
    for shape in shapes:
        assert shape not in res.answer, (shape, res.answer)
    if res.outcome["state"] == "confirm_pending":
        assert w.pending()[res.trace.pending_id]["payload"].get(key) != bad
    else:
        assert res.answer == C.missing_fields_ask_text(result)


# ── (c) 內層動作不合 ⇒ NO_MATCH，草稿與 created 都不變 ────────────────────
def _other_action(action: str) -> str:
    return next(a for a in ACTIONS if a != action)


def _spy_decide(monkeypatch) -> list:
    """記下本回合每一次 `_write_draft_decide` 進場時的 (created, merged)。"""
    seen: list = []
    original = AgentRuntime._write_draft_decide

    async def _spy(self, acc, *a, **kw):
        wd = acc.write_draft
        seen.append(None if wd is None else (wd.created, wd.merged))
        return await original(self, acc, *a, **kw)

    monkeypatch.setattr(AgentRuntime, "_write_draft_decide", _spy)
    return seen


def _spy_target(monkeypatch) -> list:
    calls: list = []
    original = AgentRuntime._write_draft_target

    def _spy(self, acc, action, **kw):
        calls.append(action)
        return original(self, acc, action, **kw)

    monkeypatch.setattr(AgentRuntime, "_write_draft_target", _spy)
    return calls


@pytest.mark.parametrize("prior", ["no_draft", "other_action_draft"])
@pytest.mark.parametrize("inner_action", ["other_visible", None, "", 123, ["x"]],
                         ids=["other_visible", "none", "empty", "int", "list"])
@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v13c_inner_action_mismatch_is_no_match_and_changes_nothing(api, monkeypatch, action,
                                                                         inner_action, prior, b_reply):
    """V13 (c)（安全審查 r3 F1）：內層 `action` 與外層不同（另一支看得到的合法動作、`None`、`""`、非字串）
    ⇒ 封閉 `NO_MATCH`；草稿前後完全相同、`created` 從未成立、`_write_draft_target` 0 次；整個回合（含模型輸出
    之後）無 `write_draft_program_confirm`、registry 無 `confirm.request`、token 表 0 列。內層帶的是好值
    （若被誤合併會進草稿）。

    B 片：`b_reply=on`（`AGENT_WRITE_REPLY_PROGRAM` 未設）⇒ 非問句回合提議未發即由程式狀態回話結束（B1）、
    不再交回模型 ⇒ 模型輸出之後的 `_write_draft_decide` 0 次；其餘不變量照驗。`off`＝改前行為（正對照）。"""
    if b_reply == "off":
        monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    text, good = GOOD[action]
    inner_act = _other_action(action) if inner_action == "other_visible" else inner_action
    w = _World()
    if prior == "other_action_draft":
        other = _other_action(action)
        _seed_draft(w, other, {_text_key(other): SPECIAL})
    draft_before = copy.deepcopy(w.draft())
    decides = _spy_decide(monkeypatch)
    targets = _spy_target(monkeypatch)
    res, provider = await _turn_p(w, text, [_proposal(_nested(action, {"action": inner_act, **good})),
                                            _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED not in res.trace.violations
    assert any('"NO_MATCH"' in c for c in _tool_contents(provider))
    assert targets == []
    if b_reply == "on":
        assert decides == [], decides                                 # 程式已結束回合、模型未再被叫
        assert WF.V_WRITE_REPLY_KD3_EXIT in res.trace.violations
        assert len(provider.calls) == 1
    else:
        assert decides and all(d is None or d[0] is False for d in decides), decides
    assert WF.V_PROGRAM_CONFIRM not in res.trace.violations
    assert w.reg.confirm_calls() == [] and w.db.rows == []
    after = w.draft()
    if draft_before is None:
        assert after is None
    else:
        assert {k: v for k, v in after.items() if k != "idle_turns"} == {
            k: v for k, v in draft_before.items() if k != "idle_turns"}
    for k in NO_VALUE_MARKS:
        assert k not in res.trace.violations


async def test_v13c_positive_control_same_inner_action_is_merged(api):
    """V13 (c) 正對照：內層 `action` 與外層相同 ⇒ 照 (a) 合併、出卡（同一組裝置不是「全部擋下」）。"""
    text, good = GOOD["repair_create"]
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal(_nested("repair_create",
                                                        {"action": "repair_create", **good})), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer


# ── (d) 只解一層 ────────────────────────────────────────────────────
@pytest.mark.parametrize("as_str", [False, True], ids=["dicts", "json_strs"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13d_two_level_nesting_is_unwrapped_only_once(api, action, as_str):
    """V13 (d)：兩層巢狀 `{action, payload:{payload:{action, …好值}}}` ⇒ 只解一層——第二層的值 ⛔ 進草稿、
    ⛔ 進送出的 payload。"""
    text, good = GOOD[action]
    level2 = {"action": action, **good}
    level1 = {"payload": json.dumps(level2, ensure_ascii=False) if as_str else level2}
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal(_nested(action, level1, as_str=as_str)), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations
    assert w.draft()["fields"] == {}
    for args, _r in w.reg.confirm_calls():
        assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
        assert _sent_payload(args) == {"action": action}
    assert res.outcome["state"] != "confirm_pending"


# ── (e) 頂層已有表單鍵 ⇒ 不解 ─────────────────────────────────────────
def _form_key_cases():
    return [pytest.param(a, k, id=f"{a}-{k}") for a in ACTIONS for k in WF.FORMS[a].keys]


@pytest.mark.parametrize("action,key", _form_key_cases())
async def test_v13e_top_level_form_key_means_no_unwrap(api, action, key):
    """V13 (e)：頂層已有任何 `form.keys` 鍵（含系統來源鍵）⇒ 不解內層——內層的好值 ⛔ 進草稿。"""
    text, good = GOOD[action]
    outer = {**_nested(action, {"action": action, **good}), key: good.get(key, "1")}
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal(outer), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED not in res.trace.violations
    assert set(w.draft()["fields"]) <= {key}


# ── (f)(g) 提議無值 ⇒ PROPOSAL_NO_VALUE_TEXT ──────────────────────────
def _no_value_proposal(variant: str, action: str) -> dict:
    if variant == "flat":
        return {"action": action}
    if variant == "nested":
        return _nested(action, {"action": action})
    return {"action": action, _text_key(action): "完全沒說過的字"}       # bad_only：值閘丟掉


@pytest.mark.parametrize("variant", ["flat", "nested", "bad_only"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13f_no_value_proposal_with_draft_and_no_card_is_the_fixed_sentence(api, action,
                                                                                   variant):
    """V13 (f)：提議無值、草稿在、無綁定卡 ⇒ `PROPOSAL_NO_VALUE_TEXT`、`clarifying`、無模型回覆呼叫、token 表
    不變；草稿帶特殊值、原話帶特殊片段 ⇒ 回覆 ⛔ 含任何草稿值或原話片段，只有表單標籤。"""
    w = _World()
    key = _text_key(action)
    _seed_draft(w, action, {key: SPECIAL})
    res, provider = await _turn_p(w, f"{SPECIAL_SAID} 幫我處理", [
        _proposal(_no_value_proposal(variant, action)), _out()])
    _assert_no_value_text(res, provider, w, action)
    assert WF.FORMS[action].field(key).label in res.answer
    assert "ZQ" not in res.answer and SPECIAL not in res.answer and SPECIAL_SAID not in res.answer
    assert res.answer.startswith("這句我沒有讀到要填寫或修改的內容，目前沒有更新。可以填寫或修改的有：")
    assert w.draft()["fields"] == {key: SPECIAL}                      # 草稿不變
    assert w.db.rows == [] and w.reg.confirm_calls() == []
    assert (WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations) is (variant == "nested")


def test_v13f_labels_rule_and_no_label_fallback():
    """V13 (f)：標籤規則同 `edit_ask_text`（草稿有值的 `user_words` 欄位；都沒有 ⇒ 全部 `user_words` 欄位；
    系統來源欄位 ⛔ 列）；無標籤 ⇒ 去掉中間那句的固定句（逐字）。"""
    assert WF.PROPOSAL_NO_VALUE_FALLBACK_TEXT == (
        "這句我沒有讀到要填寫或修改的內容，目前沒有更新。請直接說哪一項、內容是什麼，我再幫您整理成確認卡。")
    assert WF.proposal_no_value_text("no_such_action", {"x": SPECIAL}) == WF.PROPOSAL_NO_VALUE_FALLBACK_TEXT
    for action, form in WF.FORMS.items():
        # 「選對紀錄」片：只列上卡的欄位（`on_card`；客人講的比對值不上卡、⛔ 列）。
        user = [f for f in form.fields if f.source == WF.SOURCE_USER_WORDS and f.on_card]
        assert WF.proposal_no_value_text(action, {}) == WF.PROPOSAL_NO_VALUE_TEXT.format(
            labels="、".join(f.label for f in user))
        one = user[0]
        assert WF.proposal_no_value_text(action, {one.key: SPECIAL}) == WF.PROPOSAL_NO_VALUE_TEXT.format(
            labels=one.label)
        for f in form.fields:
            if f.source != WF.SOURCE_USER_WORDS:
                assert f.label not in WF.proposal_no_value_text(action, {})


def test_v13_fixed_sentences_are_verbatim():
    """V13：兩句固定句逐字＝業主裁示（計畫 §9.2 (2)、§9.6）。"""
    assert WF.PROPOSAL_NO_VALUE_CARD_TEXT == (
        "這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」或直接說要改哪一項、改成什麼。")
    assert WF.PROPOSAL_NO_VALUE_TEXT == (
        "這句我沒有讀到要填寫或修改的內容，目前沒有更新。可以填寫或修改的有：{labels}。"
        "請直接說哪一項、內容是什麼，我再幫您整理成確認卡。")


def _old_edit_ask_text(action, payload):
    """r2 的 `edit_ask_text`（抽共用函式前，逐字搬來的對照實作）。"""
    form = WF.FORMS.get(action) if isinstance(action, str) else None
    if form is None:
        return WF.EDIT_ASK_FALLBACK_TEXT
    values = payload if isinstance(payload, dict) else {}
    # 「選對紀錄」片：表單多了不上卡的比對值欄位（`on_card=False`），可修改清單只列上卡的欄位。
    user_fields = [f for f in form.fields if f.source == WF.SOURCE_USER_WORDS and f.on_card]
    labels = [f.label for f in user_fields if WF._given(values.get(f.key))]
    if not labels:
        labels = [f.label for f in user_fields]
    if not labels:
        return WF.EDIT_ASK_FALLBACK_TEXT
    return WF.EDIT_ASK_TEMPLATE.format(labels="、".join(labels))


def test_v13_edit_ask_text_unchanged_by_the_shared_label_helper():
    """抽出 `_user_word_labels` 後 `edit_ask_text` 行為不變（每支動作 × 空／好值／單欄／非 dict）。"""
    for action in [*ACTIONS, "no_such_action", None]:
        payloads = [{}, None, "x", {"estate_name": "  "}]
        if action in GOOD:
            payloads += [WF.to_payload(action, {k: str(v) for k, v in GOOD[action][1].items()}),
                         {_text_key(action): SPECIAL}]
        for payload in payloads:
            assert WF.edit_ask_text(action, payload) == _old_edit_ask_text(action, payload), (
                action, payload)


@pytest.mark.parametrize("action", ACTIONS)
async def test_v13g_bound_card_invalidated_by_edit_is_the_no_value_text(api, action):
    """V13 (g)：綁定卡已作廢（按過「修改」）、提議無值 ⇒ 同 (f)；token 表與待確認筆不變。"""
    w = _World()
    _r1, pid = await _card(w, action)
    edit = await w.turn(f"confirm_edit:{pid}")
    assert w.pending()[pid].get("invalidated") is True and w.draft() is not None, edit.answer
    rows_before = copy.deepcopy(w.db.rows)
    entry_before = copy.deepcopy(w.pending()[pid])
    n_calls = len(w.reg.confirm_calls())
    res, provider = await _turn_p(w, "問題描述改成：臥室冷氣滴水",
                                  [_proposal({"action": action}), _out()])
    _assert_no_value_text(res, provider, w, action)
    assert w.db.rows == rows_before and w.pending()[pid] == entry_before
    assert len(w.reg.confirm_calls()) == n_calls


# ── (h) 綁定卡有效、草稿＝卡 ⇒ 中性句＋同卡 ─────────────────────────────
def _assert_same_card_with_neutral_lead(res, provider, w: _World, pid: str, first_answer: str):
    lead = WF.PROPOSAL_NO_VALUE_CARD_TEXT
    assert res.answer.startswith(lead + "\n"), res.answer
    assert not res.answer.startswith(WF.CARD_UNCHANGED_TEXT)
    assert not res.answer.startswith(WF.CARD_STILL_VALID_TEXT)
    card = res.answer[len(lead) + 1:]
    assert hashlib.sha256(card.encode("utf-8")).hexdigest() == w.pending()[pid]["card_sha256"]
    assert card in first_answer
    assert res.outcome["state"] == "confirm_pending" and res.outcome["expects"] == "button"
    assert res.trace.pending_id == pid
    assert res.quick_replies == C.confirm_quick_replies(pid)
    assert len(res.quick_replies) == 3 and all(pid in r["value"] for r in res.quick_replies)
    assert WF.V_WRITE_PROPOSAL_NO_VALUE_CARD in res.trace.violations
    assert WF.V_CARD_STILL_VALID in res.trace.violations          # r3 F4：V2 計入程式重出同卡
    assert WF.V_WRITE_PROPOSAL_NO_VALUE not in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED not in res.trace.violations
    assert len(provider.calls) == 1


@pytest.mark.parametrize("said", ["再出一次確認卡", "物件不對，改成某某某"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13h_no_value_proposal_with_live_unchanged_card_is_neutral_lead_and_same_card(
        api, action, said):
    """V13 (h)：提議無值、綁定卡有效且 `to_payload(草稿)`＝卡 `draft_payload` ⇒ 回覆以
    `PROPOSAL_NO_VALUE_CARD_TEXT` 開頭＋同卡（雜湊＝`card_sha256`）、同 pid 三顆鍵、無新 token、同記
    `write_draft_card_still_valid`；使用者句子「再出一次確認卡」與「物件不對，改成 X」（意圖未抽出）各一案。"""
    w = _World()
    r1, pid = await _card(w, action)
    rows_before = copy.deepcopy(w.db.rows)
    entry_before = copy.deepcopy(w.pending()[pid])
    res, provider = await _turn_p(w, said, [_proposal({"action": action}), _out()])
    _assert_same_card_with_neutral_lead(res, provider, w, pid, r1.answer)
    assert w.db.rows == rows_before and w.db.pids(w.session_id) == [pid]
    assert w.pending()[pid] == entry_before


@pytest.mark.parametrize("action", ACTIONS)
async def test_v13h_user_value_dropped_still_gets_the_neutral_lead(api, action):
    """V13 (h)：`user_value_dropped` 為 True（意圖給的值被值閘丟掉、沒有值進草稿）時開頭句仍是
    `PROPOSAL_NO_VALUE_CARD_TEXT`（⛔ `CARD_UNCHANGED_TEXT`）。"""
    w = _World()
    r1, pid = await _card(w, action)
    res, provider = await _turn_p(w, "物件不對，改成某某某", [_proposal({"action": action}), _out()],
                                  intents=[_intent(action, **{_text_key(action): "完全沒說過的字"})])
    assert WF.V_NOT_IN_USER_WORDS in res.trace.violations          # 前提：使用者句子的值被丟
    _assert_same_card_with_neutral_lead(res, provider, w, pid, r1.answer)
    assert w.db.pids(w.session_id) == [pid]


@pytest.mark.parametrize("action", ACTIONS)
async def test_v13h_draft_differs_from_card_takes_the_no_value_text(api, action):
    """V13 (h)（安全審查 r3 F7）：草稿已改成新值而卡仍是舊值 ⇒ ⛔ (a)，走 (f)；token 表與待確認筆不變。"""
    w = _World()
    _r1, pid = await _card(w, action)
    w.draft()["fields"][_text_key(action)] = "改過的新值"
    rows_before = copy.deepcopy(w.db.rows)
    entry_before = copy.deepcopy(w.pending()[pid])
    res, provider = await _turn_p(w, "再出一次確認卡", [_proposal({"action": action}), _out()])
    _assert_no_value_text(res, provider, w, action)
    assert w.db.rows == rows_before and w.pending()[pid] == entry_before


# ── (i) 綁定卡無效 ⇒ (f)，且無副作用 ─────────────────────────────────
def _spy_side_effects(monkeypatch) -> dict:
    """記 `_write_draft_same_values` 呼叫次數與出口時的 `reissue_blocked`／`reissue_burned`／`card_still_valid`。"""
    seen: dict = {"same_values": 0, "flags": []}
    original_same = AgentRuntime._write_draft_same_values
    original_exit = AgentRuntime._write_proposal_no_value_exit

    async def _same(self, *a, **kw):
        seen["same_values"] += 1
        return await original_same(self, *a, **kw)

    def _exit(self, acc, *a, **kw):
        wd = acc.write_draft
        seen["flags"].append((wd.reissue_blocked, wd.reissue_burned, wd.card_still_valid))
        return original_exit(self, acc, *a, **kw)

    monkeypatch.setattr(AgentRuntime, "_write_draft_same_values", _same)
    monkeypatch.setattr(AgentRuntime, "_write_proposal_no_value_exit", _exit)
    return seen


def _make_card_invalid(w: _World, monkeypatch, pid: str, why: str) -> None:
    row = w.db.row(pid)
    if why == "expired":
        w.db.advance(10_000)
    elif why == "redeemed":
        row["redeemed"] = True
    elif why == "missing_row":
        w.db.rows.remove(row)
    elif why == "db_error":
        w.db.state_error = RuntimeError("connection lost")
    elif why == "db_summary_sha":
        row["summary_sha256"] = "0" * 64
    elif why == "db_payload_sha":
        row["payload_sha256"] = "0" * 64
    elif why == "entry_card_sha":
        w.pending()[pid]["card_sha256"] = "0" * 64
    elif why == "under_60s":
        w.db.advance(row["expires_at"] - w.db.now() - 30)
    elif why == "date_before_today":
        monkeypatch.setattr(runtime_mod, "fields_before_today", lambda *_a, **_kw: ["date"])
    elif why == "render_error":
        monkeypatch.setattr(runtime_mod._confirm_card, "render", _render_fails)
    else:
        raise AssertionError(why)


INVALID_REASONS = ["expired", "redeemed", "missing_row", "db_error", "db_summary_sha",
                   "db_payload_sha", "entry_card_sha", "under_60s", "date_before_today",
                   "render_error"]


async def _assert_invalid_card_is_no_value_without_side_effects(w, monkeypatch, action, pid):
    rows_before = copy.deepcopy(w.db.rows)
    entry_before = copy.deepcopy(w.pending()[pid])
    redeems_before = list(w.db.redeem_calls)
    seen = _spy_side_effects(monkeypatch)
    res, provider = await _turn_p(w, "再出一次確認卡", [_proposal({"action": action}), _out()])
    _assert_no_value_text(res, provider, w, action)
    assert w.pending()[pid] == entry_before                        # 含 ⛔ `invalidated`
    assert w.pending()[pid].get("invalidated") is not True
    assert w.db.rows == rows_before
    assert w.db.redeem_calls == redeems_before                     # `redeem_pending` 0 次
    assert seen["same_values"] == 0
    assert seen["flags"] == [(False, False, None)]


@pytest.mark.parametrize("why", INVALID_REASONS)
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13i_invalid_bound_card_takes_the_no_value_text_without_side_effects(
        api, monkeypatch, action, why):
    """V13 (i)：綁定卡 `expired`／`redeemed`／`missing`（查無列、DB 例外）／DB `summary_sha256` 或
    `payload_sha256` 不符／待確認筆 `card_sha256` 不符／live 但剩不到 60 秒／卡上日期早於今天／排版拋
    `ConfirmCardError` ⇒ 走 (f)，且無副作用：待確認筆未被改（含 `invalidated`）、`redeem_pending` 0 次、
    `_write_draft_same_values` 0 次、`reissue_blocked`／`reissue_burned` 皆 False、`card_still_valid` 未設。"""
    w = _World()
    _r1, pid = await _card(w, action)
    _make_card_invalid(w, monkeypatch, pid, why)
    await _assert_invalid_card_is_no_value_without_side_effects(w, monkeypatch, action, pid)


async def test_v13i_overdue_bill_extend_card_after_midnight(api, monkeypatch):
    """V13 (i)（真實情形，同 V4 (h)）：逾期帳單延期卡跨過午夜 ⇒ 重排版拋 `ConfirmCardError`（被接住）⇒ (f)、
    無副作用。"""
    w = _World()
    _r1, pid = await _overdue_bill_card(w, monkeypatch, date(2026, 11, 5))
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 11, 6))
    with pytest.raises(ConfirmCardError):                            # 前提：跨日真的排不出
        runtime_mod._confirm_card.render("bill_due_extend", w.pending()[pid]["payload"],
                                         today=date(2026, 11, 6))
    await _assert_invalid_card_is_no_value_without_side_effects(w, monkeypatch, "bill_due_extend", pid)


async def test_v13i_manual_bill_card_date_before_today(api, monkeypatch):
    """V13 (i)（真實情形，同 V4 (i)）：手動帳單繳費期限 2026/11/30、今天 2026/12/01 ⇒ (f)、無副作用。"""
    w = _World()
    _r1, pid = await _manual_bill_card(w)
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 12, 1))
    await _assert_invalid_card_is_no_value_without_side_effects(w, monkeypatch, "manual_bill_create",
                                                                pid)


# ── (j) 凍結回合、同回合第二次提議、write_draft 為 None ⇒ 封閉結果 ─────────────
def _assert_closed(res, provider, w: _World) -> None:
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert any('"HANDLED_BY_PROGRAM"' in c for c in _tool_contents(provider))
    for k in NO_VALUE_MARKS:
        assert k not in res.trace.violations
    assert len(provider.calls) >= 2                                  # 封閉結果之後交模型（AP-1 (4)）


@pytest.mark.parametrize("action", ACTIONS)
async def test_v13j_frozen_turn_no_value_proposal_is_closed(api, action):
    """V13 (j)：凍結回合（上回合追問、當句是問句）提議無值 ⇒ 照 AP-1 (4) 封閉結果（AP-R10 收窄：回答提問屬 AI）。"""
    w = _World()
    key = _text_key(action)
    _seed_draft(w, action, {key: SPECIAL}, asked=[key])
    res, provider = await _turn_p(w, "這一欄要填什麼？", [_proposal({"action": action}), _out()])
    assert WF.V_QUESTION_FROZEN in res.trace.violations               # 前提：真的凍結
    _assert_closed(res, provider, w)
    assert w.db.rows == []


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.usefixtures("_b_reply_off")
async def test_v13j_second_proposal_after_trigger_is_closed(api, monkeypatch, action):
    """V13 (j)：本回合程式已觸發（第一個提議轉成程式呼叫、非終結）後的第二次提議（無值）⇒ 封閉結果。
    B 片開關 off（改前行為；on 時非問句回合在第一次非終結後即由程式狀態回話結束，見
    `test_b_write_replies_program_req.py` V3）。"""
    monkeypatch.setattr(C, "render", _render_fails)
    text, good = GOOD[action]
    w = _World()
    res, provider = await _turn_p(w, text, [_proposal({"action": action, **good}, "c1"),
                                            _proposal({"action": action}, "c2"), _out()])
    assert res.trace.violations.count(WF.V_WRITE_PROPOSAL) == 2
    assert WF.V_PROGRAM_NONTERMINAL in res.trace.violations          # 前提：第一次已觸發且沒出卡
    assert len(w.reg.confirm_calls()) == 1
    _assert_closed(res, provider, w)
    assert w.db.rows == []


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.usefixtures("_b_reply_off")
async def test_v13j_write_draft_none_is_closed(api, monkeypatch, action):
    """V13 (j)：`write_draft` 為 None ⇒ 封閉結果（V1 (g) 的無值提議版）。B 片開關 off（改前行為；
    on 時提議未發即由程式狀態回話結束，見 `test_b_write_replies_program_req.py` V3）。"""
    original = AgentRuntime._write_draft_begin

    def _begin_then_none(self, acc, *a, **kw):
        original(self, acc, *a, **kw)
        acc.write_draft = None

    monkeypatch.setattr(AgentRuntime, "_write_draft_begin", _begin_then_none)
    w = _World()
    _seed_draft(w, action, {_text_key(action): SPECIAL})
    res, provider = await _turn_p(w, "再出一次確認卡", [_proposal({"action": action}), _out()])
    _assert_closed(res, provider, w)
    assert w.reg.confirm_calls() == [] and w.db.rows == []


# ── (k) 開關 off ⇒ 現行行為 ──────────────────────────────────────────
@pytest.mark.parametrize("shape", ["nested", "no_value"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13k_switch_off_keeps_model_args_execution(api, monkeypatch, action, shape):
    """V13 (k)（正對照）：`AGENT_WRITE_PROPOSAL=off` ⇒ 巢狀或無值提議照舊以**模型參數**呼叫 `confirm.request`
    （summary＝模型給的「確認」、payload＝模型原樣）；無 r3 標記。"""
    monkeypatch.setenv(PROPOSAL_ENV, "off")
    text, good = GOOD[action]
    w = _World()
    if shape == "nested":
        payload = _nested(action, {"action": action, **good})
    else:
        _seed_draft(w, action, {_text_key(action): SPECIAL})
        payload = {"action": action}
    res, _p = await _turn_p(w, text, [_proposal(payload), _out(), _out()])
    args, _r = w.reg.confirm_calls()[0]
    assert args["summary"] == "確認"
    assert _sent_payload(args) == payload
    for k in (WF.V_WRITE_PROPOSAL, WF.V_WRITE_PROPOSAL_UNWRAPPED, *NO_VALUE_MARKS):
        assert k not in res.trace.violations


# ── (l) 深層巢狀與超大字串 ⇒ 不拋例外、視同不解開 ──────────────────────────
DEEP = 200_000
HUGE_INNER = {
    "deep_array": "[" * DEEP,
    "deep_object": '{"a":' * DEEP,
    "huge_invalid": "x" * 1_000_000,
    "huge_array": json.dumps(["x"] * 200_000),
}


def test_v13l_precondition_deep_inner_strings_raise_recursion_error():
    """V13 (l) 前提自證：兩個深層字串真的會讓 `json.loads` 拋 `RecursionError`（不是 `ValueError`）；超大字串
    一個不是 JSON、一個解析成 list（都不是 dict）。"""
    for name in ("deep_array", "deep_object"):
        with pytest.raises(RecursionError):
            json.loads(HUGE_INNER[name])
    with pytest.raises(ValueError):
        json.loads(HUGE_INNER["huge_invalid"])
    assert isinstance(json.loads(HUGE_INNER["huge_array"]), list)


@pytest.mark.parametrize("inner", sorted(HUGE_INNER))
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13l_deep_or_huge_inner_string_never_raises_and_is_not_unwrapped(api, action, inner):
    """V13 (l)（安全審查 r3 F3）：內層為深層巢狀（觸發 `RecursionError`）或超大字串 ⇒ 回合不拋例外、視同
    不解開（無 `write_proposal_unwrapped`）；草稿在、無值 ⇒ 由 (f) 接住。"""
    w = _World()
    _seed_draft(w, action, {_text_key(action): SPECIAL})
    res, provider = await _turn_p(w, "再出一次確認卡", [
        _proposal({"action": action, "payload": HUGE_INNER[inner]}), _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED not in res.trace.violations
    _assert_no_value_text(res, provider, w, action)


# ── (m) 內層夾帶系統鍵、照片鍵、身分鍵、原話沒有的 bill_id ─────────────────────
FORGED_INNER = {
    "date_expire_before": "20300101", "date_expire_after": "20300202", "estate_id": "99999",
    "contract_id": "88888", "broken_photos": [{"forged": True}], "image_ref": "forged-ref",
    "role_id": "777777", "bill_id": 864209,       # 不與 GOOD 原話任何數字重疊（含電話子字串）
}


@pytest.mark.parametrize("as_str", [False, True], ids=["inner_dict", "inner_json_str"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13m_smuggled_inner_keys_never_reach_draft_or_card(api, action, as_str):
    """V13 (m)：內層夾帶系統來源鍵（`date_expire_before`、`date_expire_after`、`estate_id`、`contract_id`）、
    照片鍵、`role_id`、原話沒有的 `bill_id` ⇒ ⛔ 進草稿、⛔ 以夾帶值進送出的 payload、⛔ 上卡。"""
    text, good = GOOD[action]
    inner = {"action": action, **{k: v for k, v in good.items() if k != "bill_id"}, **FORGED_INNER}
    w = _World()
    res, _p = await _turn_p(w, text, [_proposal(_nested(action, inner, as_str=as_str)), _out()])
    assert WF.V_WRITE_PROPOSAL_UNWRAPPED in res.trace.violations
    assert not set(FORGED_INNER) & set(w.draft()["fields"])
    for args, _r in w.reg.confirm_calls():
        sent = _sent_payload(args)
        assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
        for k, v in FORGED_INNER.items():
            assert sent.get(k) != v, (k, sent.get(k))
    for shown in ("99999", "88888", "864209", "864,209", "777777", "2030", "forged"):
        assert shown not in res.answer, (shown, res.answer)


# ── (n) 影子回合、文件暫存、點選範圍 ⇒ 維持現行 ──────────────────────────
def _excluded_payload(shape: str, action: str) -> dict:
    text, good = GOOD[action]
    return _nested(action, {"action": action, **good}) if shape == "nested" else {"action": action}


@pytest.mark.parametrize("shape", ["nested", "no_value"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13n_readonly_view_proposal_changes_nothing(api, action, shape):
    """V13 (n)：影子回合（`readonly_view`）遇到巢狀或無值提議 ⇒ 不走提議分支；token 表與 `agent_state`
    （`dialog` 以外）都不變（同 V8 (5)）。"""
    w = _World()
    await _card(w, action)
    state_before = copy.deepcopy(w.state)
    rows_before = copy.deepcopy(w.db.rows)
    res, _p = await _turn_p(w, "再出一次確認卡", [_proposal(_excluded_payload(shape, action)), _out(),
                                                   _out()], readonly_view=True)
    for k in (WF.V_WRITE_PROPOSAL, WF.V_WRITE_PROPOSAL_UNWRAPPED, *NO_VALUE_MARKS):
        assert k not in res.trace.violations
    assert w.db.rows == rows_before
    strip = lambda st: {k: v for k, v in st["agent"].items() if k != "dialog"}   # noqa: E731
    assert strip(w.state) == strip(state_before)


def _with_carry(w: _World) -> None:
    w.state = {"agent": {}}
    AgentSession(w.state["agent"]).write_document_carry("estate_create", [("address", "某路 1 號")], None)
    assert runtime_mod._document_carry_of(w.state["agent"]) is not None          # 前提


def _with_select_scope(w: _World) -> None:
    w.state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "67652"}}}


@pytest.mark.parametrize("setup", ["document_carry", "select_scope"])
@pytest.mark.parametrize("shape", ["nested", "no_value"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v13n_carry_and_select_scope_turns_keep_current_behaviour(api, monkeypatch, action,
                                                                       shape, setup):
    """V13 (n)：文件暫存有效、點選範圍回合遇到巢狀或無值提議 ⇒ 不走提議分支（維持現行：模型參數照舊執行，
    文件暫存的既有前處理照舊補值）；結果與 `AGENT_WRITE_PROPOSAL=off` 同一回合完全相同（送進 registry 的參數、
    token 表、`agent_state`、回覆），token 表維持 0 列。"""
    prepare = _with_carry if setup == "document_carry" else _with_select_scope
    payload = _excluded_payload(shape, action)
    outcomes = {}
    for switch in ("on", "off"):
        if switch == "off":
            monkeypatch.setenv(PROPOSAL_ENV, "off")
        w = _World()
        prepare(w)
        res, _p = await _turn_p(w, "再出一次確認卡", [_proposal(payload), _out(), _out()])
        for k in (WF.V_WRITE_PROPOSAL, WF.V_WRITE_PROPOSAL_UNWRAPPED, *NO_VALUE_MARKS):
            assert k not in res.trace.violations
        (args, _r), = w.reg.confirm_calls()
        sent = _sent_payload(args)
        assert args["summary"] == "確認"                               # 模型參數照舊執行
        if setup == "document_carry":
            # 文件暫存的既有前處理會把暫存的已辨識欄位補進模型參數（現行行為、開關兩邊相同）
            assert all(sent.get(k) == v for k, v in payload.items() if k not in sent or k in ("action", "payload"))
            assert sent["action"] == action
        else:
            assert sent == payload
        assert w.db.rows == []
        outcomes[switch] = (copy.deepcopy(w.state), res.answer, res.outcome, sent)
    assert outcomes["on"] == outcomes["off"]


# ── (o) 靜態：解開邏輯只在 `_write_proposal_merge`，`_payload_of` 與 r2 相同 ─────────────
#: r2 基準（`~/jgb-archive/arch-step3-20261018/aplus/baseline-r2/rag-orchestrator/services/agent/runtime.py`）
#: 中 `_payload_of` 原始碼（`ast.get_source_segment`）的 sha256。
PAYLOAD_OF_R2_SHA256 = "7c56b78f53a6b93acb893e3a8a7402c2001109a57c3a4c1ef3f8ba9a94fa41b1"


def _runtime_functions() -> dict:
    with open(runtime_mod.__file__, encoding="utf-8") as fh:
        text = fh.read()
    out: dict = {}
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(ast.get_source_segment(text, node))
    return out


def test_v13o_payload_of_is_unchanged_from_r2():
    """V13 (o)：`_payload_of` 與 r2 相同（原始碼雜湊）；它仍只接 `TypeError`／`ValueError`、不解巢狀。"""
    (src,) = _runtime_functions()["_payload_of"]
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == PAYLOAD_OF_R2_SHA256


def test_v13o_unwrap_logic_lives_only_in_write_proposal_merge():
    """V13 (o)：解開邏輯（`V_WRITE_PROPOSAL_UNWRAPPED` 標記、`RecursionError` 接住）只在
    `_write_proposal_merge` 內；正對照：該函式本身兩者都命中。"""
    funcs = _runtime_functions()
    (merge,) = funcs["_write_proposal_merge"]
    assert "V_WRITE_PROPOSAL_UNWRAPPED" in merge and "RecursionError" in merge
    for name, sources in funcs.items():
        if name == "_write_proposal_merge":
            continue
        for src in sources:
            assert "V_WRITE_PROPOSAL_UNWRAPPED" not in src, name
            assert "RecursionError" not in src, name


def test_v13o_no_value_exit_never_burns_or_reuses_the_still_valid_lead():
    """V13 (o)／安全審查 r3 F2（靜態）：AP-7 (2) 的三支函式 ⛔ 呼叫 `_write_draft_same_values`、`redeem_pending`，
    ⛔ 寫 `invalidated`、`reissue_blocked`、`reissue_burned`、`card_still_valid`，⛔ 引用
    `CARD_UNCHANGED_TEXT`／`CARD_STILL_VALID_TEXT`。正對照：`_write_draft_same_values` 命中 `redeem_pending`。"""
    funcs = _runtime_functions()
    for name in ("_write_proposal_no_value", "_write_proposal_card_unchanged",
                 "_write_proposal_no_value_exit"):
        (src,) = funcs[name]
        body = src.split('"""', 2)[-1]                                 # 去掉 docstring
        for banned in ("_write_draft_same_values", "redeem_pending", '["invalidated"]',
                       "reissue_blocked =", "reissue_burned =", "card_still_valid =",
                       "CARD_UNCHANGED_TEXT", "CARD_STILL_VALID_TEXT"):
            assert banned not in body, (name, banned)
    (same,) = funcs["_write_draft_same_values"]
    assert "redeem_pending" in same
