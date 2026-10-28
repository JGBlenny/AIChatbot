"""unit：B 片——寫入進行中的回話由程式產生、帶狀態句只在對得上狀態時送出。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-b-write-replies-program-20261020.md` §4.1 B1～B7；
凍結驗收清單同目錄 `acceptance-b-write-replies-program-20261020.md` 的**單元部分**：
V3、V4、V5、V8 (a)、V9（單元）、V11（單元與靜態）、V16。V1 的必過契約在
`test_dsp091_division_contract_req.py`（`test_c7`／`test_c8`／`test_c9`）。

每條皆含開關 off 正對照（`AGENT_WRITE_REPLY_PROGRAM`／`AGENT_STATE_CLAIM_GATE`＝off ⇒ 改前行為）。
裝置沿用 `test_step3_write_lifecycle_req.py` 的 `_World`（同一張 `FakeTokenDB`＋真 registry＋
`assistant_demo_vendor4.json` 離線 fixture）與 A+ 檔的提議小工具。判讀呼叫以 `FakeCompletions.judge_script`
注入（依 `response_format` 名稱 `state_claim_judge` 分流，⛔ 計入主模型 `calls`）。
"""
from __future__ import annotations

import ast
import asyncio
import copy
import json
import logging
import re
from pathlib import Path

import pytest

from services import usage_metering
from services.agent import exit_gates
from services.agent import runtime as runtime_mod
from services.agent import state_claim as SC
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_DRAFT_KEY
from services.agent.budget import Budget
from services.agent.output_schema import ASK_TARGETS
from services.agent.runtime import AgentRuntime
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools
from services.jgb import fixture_store

from tests.unit.agent.test_aplus_card_program_only_req import (  # noqa: F401 — helper 匯入
    ACTIONS, GOOD, _multi, _nested, _proposal, _render_fails, _seed_draft, _with_carry,
    _with_select_scope,
)
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeVerifier, VerifierVerdict, _fake_message, _fake_response,
    _fake_tool_call,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    REPAIR_TEXT, _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    STUDENT_ESTATE, _intent, _out, _Provider, _RulesVerifier,
)

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-b-write-replies-program")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


AGENT_DIR = Path(runtime_mod.__file__).resolve().parent
MODEL_SAID = "ZQ模型自己寫的回話ZQ"
REPAIR_FIELDS = {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷"}
STATE_PREFIX = WF.TRACE_WRITE_REPLY_STATE_PREFIX
SOURCE_PROGRAM = f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{WF.WRITE_REPLY_SOURCE_PROGRAM}"
SOURCE_PLUS = f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{WF.WRITE_REPLY_SOURCE_MODEL_PLUS_STATUS}"


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
async def _bt(w: _World, message, script, *, intents=None, judge=None, budget=None,
              program_first: bool = False, readonly_view: bool = False, state=None,
              document=None):
    """一回合：回 `(result, provider)`；`judge`＝判讀呼叫腳本（None ⇒ 一律回空 claims）。"""
    provider = _Provider(list(script), intents)
    if judge is not None:
        provider.main.judge_script = list(judge)
    verifier = (_RulesVerifier if program_first else FakeVerifier)([VerifierVerdict(ok=True)] * 6)
    rt = AgentRuntime(provider, w.reg, verifier, FakeAssembler(), budget or Budget(), stage="M1",
                      clock=FakeClock(), db_pool=w.db, readonly_view=readonly_view)
    kwargs = {} if document is None else {"document": document}
    res = await rt.run_turn(w.ident, message, w.state if state is None else state, **kwargs)
    return res, provider


def _b_off(monkeypatch, *, gate: bool = True) -> None:
    """B 片開關 off（改前行為）：回話開關；`gate=True` 時判讀閘一併 off。"""
    monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    if gate:
        monkeypatch.setenv(SC.STATE_CLAIM_GATE_ENV, "off")


def _branch(res):
    marks = [v[len(STATE_PREFIX):] for v in res.trace.violations if v.startswith(STATE_PREFIX)]
    assert len(marks) == 1, res.trace.violations
    return marks[0]


def _expected_text(branch: str, w: _World) -> str:
    """文字分支（無卡）的期望回覆：逐字等於常數或樣板 `.format()`（V16 (b)）。"""
    if branch == WF.WRITE_REPLY_STATE_NOT_ISSUED:
        return WF.WRITE_NOT_ISSUED_TEXT
    if branch == WF.WRITE_REPLY_STATE_NO_PENDING:
        return WF.NO_PENDING_WRITE_TEXT
    if branch == WF.WRITE_REPLY_STATE_MISSING:
        d = w.draft()
        labels = WF.missing_labels(d["action"], WF.to_payload(d["action"], d["fields"]))
        return C.MISSING_FIELDS_ASK_TEMPLATE.format(labels=C.MISSING_FIELDS_SEP.join(labels))
    raise AssertionError(branch)


def _expected_outcome_state(branch: str) -> str:
    return {WF.WRITE_REPLY_STATE_NOT_ISSUED: "failed", WF.WRITE_REPLY_STATE_NO_PENDING: "answered",
            WF.WRITE_REPLY_STATE_MISSING: "clarifying"}.get(branch, "confirm_pending")


def _assert_program_text_reply(res, provider, w: _World, *, rows_before: int, main_calls: int = 1):
    """V3：程式狀態回話（文字分支）——主模型只被叫 `main_calls` 次、回覆＝分支對應常數、`outcome` 一致、
    token 表列數不變、⛔ 被 T1 改成 `ASK_TARGET_TEXT`、模型文字 ⛔ 出現。"""
    branch = _branch(res)
    assert len(provider.calls) == main_calls, len(provider.calls)
    assert res.answer == _expected_text(branch, w), res.answer
    assert res.outcome["state"] == _expected_outcome_state(branch), res.outcome
    assert res.trace.pending_id is None and res.quick_replies == []
    assert len(w.db.rows) == rows_before
    assert res.answer != exit_gates.ASK_TARGET_TEXT
    assert MODEL_SAID not in res.answer
    assert SOURCE_PROGRAM in res.trace.violations
    return branch


# ════════════════════════════════════════════════════════════════════
# V3（B-R2、B-R3）(a) 提議未發的每種原因 × 每支動作
# ════════════════════════════════════════════════════════════════════
def _other(action: str) -> str:
    return next(a for a in ACTIONS if a != action)


@pytest.mark.parametrize("b_reply", ["on", "off"])
@pytest.mark.parametrize("reason", ["nested_no_match", "second_after_trigger", "deadline"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v3a_unissued_proposal_ends_with_the_program_state_reply(api, monkeypatch, action,
                                                                      reason, b_reply):
    """V3 (a)：提議未發（巢狀內層動作不合 `NO_MATCH`／本回合已觸發後的第二次提議／期限不足）⇒
    主模型 ⛔ 被叫第二次、回覆＝B-R2 狀態回話（逐字常數）、`outcome` 一致、token 表列數不變。
    正對照（off）：照舊交回模型（主模型被叫第二次、模型文字送出）。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    text, good = GOOD[action]
    w = _World()
    budget = None
    if reason == "nested_no_match":
        script = [_proposal(_nested(action, {"action": _other(action), **good})), _out(MODEL_SAID)]
    elif reason == "second_after_trigger":
        monkeypatch.setattr(C, "render", _render_fails)
        script = [_multi(("confirm.request", {"summary": "確認", "payload": json.dumps(
                              {"action": action, **good}, ensure_ascii=False)}, "c1"),
                         ("confirm.request", {"summary": "確認", "payload": json.dumps(
                              {"action": action}, ensure_ascii=False)}, "c2")),
                  _out(MODEL_SAID)]
    else:
        budget = Budget(deadline_s=5.9)
        script = [_proposal({"action": action, **good}), _out(MODEL_SAID)]
    rows_before = len(w.db.rows)
    res, provider = await _bt(w, text, script, budget=budget)
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations          # 前提：真的走到提議未發
    if b_reply == "on":
        branch = _assert_program_text_reply(res, provider, w, rows_before=rows_before)
        assert WF.V_WRITE_REPLY_KD3_EXIT in res.trace.violations
        if reason == "nested_no_match":
            assert branch == WF.WRITE_REPLY_STATE_NO_PENDING
        else:
            assert branch == WF.WRITE_REPLY_STATE_NOT_ISSUED           # 草稿完整、無卡
    else:
        assert len(provider.calls) == 2 and MODEL_SAID in res.answer
        assert not any(v.startswith(STATE_PREFIX) for v in res.trace.violations)


# ════════════════════════════════════════════════════════════════════
# V3 (b) 提議轉成的程式呼叫非終結 × 每支動作
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("b_reply", ["on", "off"])
@pytest.mark.parametrize("why", ["render_error", "insert_error"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_v3b_nonterminal_program_call_ends_with_the_program_state_reply(api, monkeypatch,
                                                                             action, why, b_reply):
    """V3 (b)：程式呼叫非終結（排版例外 ⇒ 無缺欄清單 `INVALID_INPUT`；INSERT 例外）⇒ 同 (a) 的回話契約。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    text, good = GOOD[action]
    w = _World()
    if why == "render_error":
        monkeypatch.setattr(C, "render", _render_fails)
    else:
        w.db.insert_error = RuntimeError("boom")
    rows_before = len(w.db.rows)
    res, provider = await _bt(w, text, [_proposal({"action": action, **good}), _out(MODEL_SAID)])
    assert WF.V_PROGRAM_NONTERMINAL in res.trace.violations                # 前提：非終結
    assert len(w.reg.confirm_calls()) == 1
    if b_reply == "on":
        branch = _assert_program_text_reply(res, provider, w, rows_before=rows_before)
        assert branch == WF.WRITE_REPLY_STATE_NOT_ISSUED
    else:
        assert len(provider.calls) == 2 and MODEL_SAID in res.answer


@pytest.mark.parametrize("b_reply", ["on", "off"])
@pytest.mark.parametrize("case", ["no_match_period", "date_before_today"])
async def test_v3b_no_match_and_date_before_today_end_with_the_program_state_reply(api, monkeypatch,
                                                                                   case, b_reply):
    """V3 (b)：無查無標記的 `NO_MATCH`（期別對不到）、`DATE_BEFORE_TODAY`（到期日已過）各一案。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    if case == "no_match_period":
        action = "bill_due_extend"
        text, good = GOOD[action]
        good = {k: v for k, v in good.items() if k != "bill_id"}
        good["period"] = "1999年1月那期"
        text = text.replace("11月那期", "1999年1月那期").replace(" 帳單 709744", "")
    else:
        action = "manual_bill_create"
        text, good = GOOD[action]
        good = {**good, "date_expire": "20201130"}
        text = text.replace("2026/11/30", "2020/11/30")
    w = _World()
    rows_before = len(w.db.rows)
    res, provider = await _bt(w, text, [_proposal({"action": action, **good}), _out(MODEL_SAID)])
    (_args, result), = w.reg.confirm_calls()
    assert not result.ok
    assert WF.V_PROGRAM_NONTERMINAL in res.trace.violations
    if b_reply == "on":
        _assert_program_text_reply(res, provider, w, rows_before=rows_before)
    else:
        assert len(provider.calls) == 2 and MODEL_SAID in res.answer


# ════════════════════════════════════════════════════════════════════
# V3 狀態分支各一案（一般出口、非問句回合、模型 `answer`）
# ════════════════════════════════════════════════════════════════════
LATER = "我先去看一下"


def _assert_same_card(res, provider, w: _World, pid: str, card: str, lead: str, *, rows_before):
    assert len(provider.calls) == 1
    assert res.answer == f"{lead}\n{card}", res.answer
    assert res.outcome["state"] == "confirm_pending"
    assert res.trace.pending_id == pid
    assert res.quick_replies == C.confirm_quick_replies(pid)
    assert w.db.rows == rows_before and w.db.pids(w.session_id) == [pid]
    assert MODEL_SAID not in res.answer
    assert SOURCE_PROGRAM in res.trace.violations


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v3_state_card_still_valid_reissues_the_same_card(api, monkeypatch, b_reply):
    """V3 狀態 (1)：綁定卡 live 且草稿＝卡 ⇒ 前導句＋整張卡、同 pid、無新 token。填欄只填答覆修復輪 3：本回合沒讀到
    任何值（意圖 `none`）⇒ 前導句是 `CARD_NO_CHANGE_TEXT`（原為 `CARD_STILL_VALID_TEXT`）；分支名不變。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    r1, pid = await w.repair_card()
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        assert _branch(res) == WF.WRITE_REPLY_STATE_CARD_STILL_VALID
        _assert_same_card(res, provider, w, pid, r1.answer, WF.CARD_NO_CHANGE_TEXT,
                          rows_before=rows_before)
        assert WF.V_CARD_NO_VALUE_READ in res.trace.violations
    else:
        assert MODEL_SAID in res.answer and res.trace.pending_id is None


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v3_state_user_value_dropped_gets_card_unchanged_text(api, monkeypatch, b_reply):
    """V3 狀態：同 (1) 但使用者值被值閘丟掉（意圖給的值不在原話）⇒ `CARD_UNCHANGED_TEXT`＋同卡。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    r1, pid = await w.repair_card()
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)],
                              intents=[_intent("repair_create", description="完全沒說過的字")])
    assert WF.V_NOT_IN_USER_WORDS in res.trace.violations          # 前提：值被丟
    if b_reply == "on":
        assert _branch(res) == WF.WRITE_REPLY_STATE_CARD_UNCHANGED
        _assert_same_card(res, provider, w, pid, r1.answer, WF.CARD_UNCHANGED_TEXT,
                          rows_before=rows_before)
    else:
        assert MODEL_SAID in res.answer and res.trace.pending_id is None


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v3_state_card_differs_reissues_the_same_card_with_differs_text(api, monkeypatch,
                                                                             b_reply):
    """V3 狀態 (2)：綁定卡 live、草稿≠卡 ⇒ `CARD_DIFFERS_TEXT`＋整張卡（舊卡，同 pid）、無新 token。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    r1, pid = await w.repair_card()
    w.draft()["fields"]["description"] = "改過的新值"
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        assert _branch(res) == WF.WRITE_REPLY_STATE_CARD_DIFFERS
        _assert_same_card(res, provider, w, pid, r1.answer, WF.CARD_DIFFERS_TEXT,
                          rows_before=rows_before)
        assert "改過的新值" not in res.answer
    else:
        assert MODEL_SAID in res.answer and res.trace.pending_id is None


@pytest.mark.parametrize("b_reply", ["on", "off"])
@pytest.mark.parametrize("why", ["expired", "summary_sha_mismatch", "payload_sha_mismatch"])
async def test_v3_state_dead_card_is_never_reissued(api, monkeypatch, why, b_reply):
    """V3 狀態：卡已過期或雜湊不符 ⇒ ⛔ 重出（草稿完整 ⇒ `WRITE_NOT_ISSUED_TEXT`）、token 表不變。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    _r1, pid = await w.repair_card()
    if why == "expired":
        w.db.advance(10_000)
    elif why == "summary_sha_mismatch":
        w.db.row(pid)["summary_sha256"] = "0" * 64
    else:
        w.db.row(pid)["payload_sha256"] = "0" * 64
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        assert _assert_program_text_reply(res, provider, w, rows_before=len(rows_before)) == \
            WF.WRITE_REPLY_STATE_NOT_ISSUED
        assert w.db.rows == rows_before
    else:
        assert MODEL_SAID in res.answer


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v3_state_missing_label_outside_vocab_is_not_issued(api, monkeypatch, b_reply):
    """V3 狀態：缺欄標籤不在詞彙 ⇒ `WRITE_NOT_ISSUED_TEXT`（⛔ 套追問樣板）。正對照：標籤在詞彙 ⇒ 追問樣板。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE})
    ok, _p = await _bt(w, "我等一下再補", [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        assert _branch(ok) == WF.WRITE_REPLY_STATE_MISSING                  # 正對照
        assert ok.answer == C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="問題描述")
    w2 = _World()
    _seed_draft(w2, "repair_create", {"estate_name": STUDENT_ESTATE})
    monkeypatch.setattr(WF, "missing_labels", lambda *_a, **_kw: ["ZQ不在詞彙ZQ"])
    res, provider = await _bt(w2, "我等一下再補", [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        assert _assert_program_text_reply(res, provider, w2, rows_before=0) == \
            WF.WRITE_REPLY_STATE_NOT_ISSUED
        assert "ZQ不在詞彙ZQ" not in res.answer
    else:
        assert MODEL_SAID in res.answer


# ════════════════════════════════════════════════════════════════════
# V4（B-R2、B-R4 (a)、B-R13）
# ════════════════════════════════════════════════════════════════════
QUESTION = "這樣可以嗎？"
OUT_OF_DOMAIN = "zq_not_a_target"


async def _missing_world():
    w = _World()
    _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE})
    return w


def _assert_missing_ask(res, *, prefix=None):
    ask = C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="問題描述")
    expected = ask if prefix is None else f"{prefix}\n\n{ask}"
    assert res.answer == expected, res.answer
    assert res.outcome["state"] == "clarifying"
    assert res.ask_target != "confirm_intent"


@pytest.mark.parametrize("b_reply", ["on", "off"])
@pytest.mark.parametrize("setup", ["missing", "card"])
@pytest.mark.parametrize("kind", ["ask", "recommend"])
async def test_v4_non_question_turn_ask_and_recommend_become_program_reply(api, monkeypatch, kind,
                                                                          setup, b_reply):
    """V4：非問句回合、模型 `kind=ask`／`recommend` ⇒ 缺欄追問（草稿缺欄）或重出同卡（綁定卡有效）；
    模型文字 ⛔ 出現。正對照（off）：模型文字照送。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    if setup == "missing":
        w = await _missing_world()
        card = pid = None
    else:
        w = _World()
        r1, pid = await w.repair_card()
        card = r1.answer
    target = "description" if kind == "ask" else None
    res, _p = await _bt(w, LATER, [_out(MODEL_SAID + "？", kind=kind, ask_target=target)],
                        intents=[_intent("none")])
    if b_reply == "off":
        assert MODEL_SAID in res.answer
        return
    assert MODEL_SAID not in res.answer and SOURCE_PROGRAM in res.trace.violations
    if setup == "missing":
        _assert_missing_ask(res)
    else:
        # 填欄只填答覆修復輪 3：本回合沒讀到值 ⇒ 前導句 `CARD_NO_CHANGE_TEXT`（原 `CARD_STILL_VALID_TEXT`）
        assert res.answer == f"{WF.CARD_NO_CHANGE_TEXT}\n{card}" and res.trace.pending_id == pid


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v4_1_non_question_answer_becomes_program_reply(api, monkeypatch, b_reply):
    """V4 (1)：非問句回合（「我先去看一下」）、模型 `answer`「好的」⇒ 換成程式狀態回話。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = await _missing_world()
    res, _p = await _bt(w, LATER, [_out("好的" + MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "on":
        _assert_missing_ask(res)
        assert MODEL_SAID not in res.answer and SOURCE_PROGRAM in res.trace.violations
    else:
        assert MODEL_SAID in res.answer


@pytest.mark.parametrize("target", list(ASK_TARGETS) + [None, OUT_OF_DOMAIN])
async def test_v4_2_question_turn_ask_any_target_becomes_program_reply(api, target):
    """V4 (2)：問句回合、模型 `kind=ask`，`ASK_TARGETS` 全部值＋`None`＋值域外 ⇒ 全部換成程式狀態回話、
    `write_reply_source=program`。"""
    assert len(ASK_TARGETS) == 19                                         # 前提：值域來源
    w = await _missing_world()
    res, _p = await _bt(w, QUESTION, [_out(MODEL_SAID + "？", kind="ask", ask_target=target)],
                        intents=[_intent("none")])
    assert MODEL_SAID not in res.answer
    assert SOURCE_PROGRAM in res.trace.violations and SOURCE_PLUS not in res.trace.violations
    _assert_missing_ask(res)


@pytest.mark.parametrize("target", ["confirm_intent", None])
async def test_v4_2_off_question_turn_ask_is_sent_as_before(api, monkeypatch, target):
    """V4 (2) 正對照（off）：同形狀模型文字照送（`None` 會被 T1 改成 `ASK_TARGET_TEXT`，照舊）。"""
    _b_off(monkeypatch)
    w = await _missing_world()
    res, _p = await _bt(w, QUESTION, [_out(MODEL_SAID + "？", kind="ask", ask_target=target)],
                        intents=[_intent("none")])
    assert not any(v.startswith(WF.TRACE_WRITE_REPLY_SOURCE_PREFIX) for v in res.trace.violations)
    assert MODEL_SAID in res.answer or res.answer == exit_gates.ASK_TARGET_TEXT


def _model_inputs(provider) -> str:
    return json.dumps([c.get("messages") for c in provider.calls], ensure_ascii=False, default=str)


async def _next_turn_ok_is_not_carried_or_redeemed(w: _World, pid: str) -> None:
    """下一回合使用者說「好」⇒ ⛔ 注入 `AFFIRMATIVE_CARRY_TEXT`、⛔ 兌現（寫入 0、卡仍未兌現）。"""
    res, provider = await _bt(w, "好", [_out("好的")], intents=[_intent("none")])
    assert runtime_mod.AFFIRMATIVE_CARRY_TEXT not in _model_inputs(provider)
    assert w.writes() == [] and w.db.redeemed(pid) is False
    assert res.outcome["state"] != "confirmed"


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v4_3_question_turn_unissued_proposal_confirm_intent_never_carries(api, monkeypatch,
                                                                                b_reply):
    """V4 (3)：問句回合、本回合提議未轉成程式呼叫、綁定卡 live、模型 `ask`／`confirm_intent` ⇒ 程式狀態回話，
    送出的 `ask_target` ≠ `confirm_intent`；下一回合「好」⇒ ⛔ 帶肯定、⛔ 兌現。
    正對照（off）：送出 `confirm_intent`、下一回合「好」帶肯定注入（改前行為）。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    r1, pid = await w.repair_card()
    text, good = GOOD["repair_create"]
    res, provider = await _bt(w, QUESTION, [
        _proposal(_nested("repair_create", {"action": _other("repair_create"), **good})),
        _out("請確認以上內容" + MODEL_SAID, kind="ask", ask_target="confirm_intent")])
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations          # 前提
    assert [r.status for r in res.trace.tool_calls if r.name == "confirm.request"] == ["error"]
    if b_reply == "on":
        assert len(provider.calls) == 2                                    # 問句回合照現行交回模型
        assert MODEL_SAID not in res.answer and SOURCE_PROGRAM in res.trace.violations
        # 填欄只填答覆修復輪 3：本回合沒讀到值 ⇒ 前導句 `CARD_NO_CHANGE_TEXT`（原 `CARD_STILL_VALID_TEXT`）
        assert res.answer == f"{WF.CARD_NO_CHANGE_TEXT}\n{r1.answer}" and res.trace.pending_id == pid
        assert res.ask_target != "confirm_intent"
        await _next_turn_ok_is_not_carried_or_redeemed(w, pid)
    else:
        assert MODEL_SAID in res.answer and res.ask_target == "confirm_intent"
        nxt, p2 = await _bt(w, "好", [_out("好的")], intents=[_intent("none")])
        assert runtime_mod.AFFIRMATIVE_CARRY_TEXT in _model_inputs(p2)
        del nxt


@pytest.mark.parametrize("target", [None, "choice"])
async def test_v4_4_question_turn_recommend_becomes_program_reply(api, target):
    """V4 (4)：問句回合、模型 `recommend`（`ask_target` 為 `None`／`choice`）⇒ 程式狀態回話、`program`。"""
    w = await _missing_world()
    res, _p = await _bt(w, QUESTION, [_out(MODEL_SAID, kind="recommend", ask_target=target)],
                        intents=[_intent("none")])
    assert MODEL_SAID not in res.answer and SOURCE_PROGRAM in res.trace.violations
    _assert_missing_ask(res)


KNOWLEDGE_ANSWER = "修繕單送出後會由管理員安排處理。"


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v4_5_question_turn_answer_is_model_text_plus_card(api, monkeypatch, b_reply):
    """V4 (5)（Q1 乙′）：問句回合、模型 `answer`、不含帶狀態句、綁定卡有效 ⇒ 模型文字逐字在前、空行、
    程式前導句＋整張卡（逐字＝卡 formatter 輸出、雜湊＝`summary_sha256`）；同 pid 三顆鍵、無新 token；
    `ask_target` 為 `None`、`model_plus_status`；下一回合「好」⇒ ⛔ 帶肯定、⛔ 兌現。正對照（off）：只有模型文字。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    r1, pid = await w.repair_card()
    card = r1.answer
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, "送出後多久會處理？", [_out(KNOWLEDGE_ANSWER)],
                              intents=[_intent("none")])
    if b_reply == "off":
        assert res.answer == KNOWLEDGE_ANSWER and res.trace.pending_id is None
        return
    assert len(provider.calls) == 1
    # 填欄只填答覆修復輪 3：本回合沒讀到值 ⇒ 前導句 `CARD_NO_CHANGE_TEXT`（原 `CARD_STILL_VALID_TEXT`）
    assert res.answer == f"{KNOWLEDGE_ANSWER}\n\n{WF.CARD_NO_CHANGE_TEXT}\n{card}", res.answer
    assert res.answer.endswith(card)
    assert C.sha256_hex(card) == w.db.row(pid)["summary_sha256"]
    assert res.quick_replies == C.confirm_quick_replies(pid) and res.trace.pending_id == pid
    assert w.db.rows == rows_before
    assert res.ask_target is None
    assert SOURCE_PLUS in res.trace.violations and SOURCE_PROGRAM not in res.trace.violations
    assert SC.V_STATE_CLAIM_CHECK in res.trace.violations                # 模型文字先過判讀閘
    await _next_turn_ok_is_not_carried_or_redeemed(w, pid)


async def test_v4_5_question_turn_answer_with_missing_fields_appends_the_ask(api):
    """V4 (5)：同上、草稿缺欄 ⇒ 模型文字＋空行＋缺欄追問樣板；`ask_target` 為 `None`。"""
    w = await _missing_world()
    res, _p = await _bt(w, "送出後多久會處理？", [_out(KNOWLEDGE_ANSWER)], intents=[_intent("none")])
    _assert_missing_ask(res, prefix=KNOWLEDGE_ANSWER)
    assert res.ask_target is None and SOURCE_PLUS in res.trace.violations


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v4_non_write_context_ask_is_sent_as_is(api, monkeypatch, b_reply):
    """V4 正對照：非寫入情境回合（無草稿、無卡、無提議）的 `kind=ask` ⇒ 照送；on 與 off 回覆相同。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    w = _World()
    res, _p = await _bt(w, "我想問一下", [_out("請問您想問哪一項功能？", kind="ask", ask_target="choice")],
                        intents=[_intent("none")])
    assert res.answer == "請問您想問哪一項功能？"
    assert not any(v.startswith(STATE_PREFIX) for v in res.trace.violations)


# ════════════════════════════════════════════════════════════════════
# V5（B-R5）帶狀態句判讀閘
# ════════════════════════════════════════════════════════════════════
def _claims(*cats) -> str:
    return json.dumps({"claims": list(cats)})


UNBACKED = SC.TRACE_STATE_CLAIM_UNBACKED_PREFIX


def _unbacked(res) -> list:
    return [v[len(UNBACKED):] for v in res.trace.violations if v.startswith(UNBACKED)]


async def _submitted_world() -> tuple:
    """出卡後按送出 ⇒ session 有成功收據（前回合「已完成」事件）。"""
    w = _World()
    _r1, pid = await w.repair_card()
    ok = await w.turn(f"confirm_submit:{pid}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    return w, pid


async def _cancelled_world() -> tuple:
    w = _World()
    _r1, pid = await w.repair_card()
    cancel = next(r["value"] for r in C.confirm_quick_replies(pid) if r["value"].startswith("confirm_cancel"))
    res = await w.turn(cancel)
    assert w.pending()[pid]["receipt"].get("cancelled") is True, res.answer
    return w, pid


THANKS = "謝謝，先這樣"


@pytest.mark.parametrize("gate", ["on", "off"])
@pytest.mark.parametrize("cat", [SC.CLAIM_COMPLETED, SC.CLAIM_CANCELLED, SC.CLAIM_AWAITING,
                                 SC.CLAIM_HANDED_OFF])
async def test_v5a_claim_without_event_is_replaced(api, monkeypatch, cat, gate):
    """V5 (a) 無事件：知識回合（無草稿、無卡、無收據）模型 `answer` 被判出 `cat` ⇒ 模型文字 ⛔ 送出、換成程式句
    （「已轉人」⇒ `HANDOFF_OFFER_TEXT`，其餘 ⇒ `NO_PENDING_WRITE_TEXT`）、記 `state_claim_unbacked:<cat>`、
    ⛔ 進 dialog。正對照（閘 off）：判讀 ⛔ 呼叫、模型文字照送。"""
    if gate == "off":
        monkeypatch.setenv(SC.STATE_CLAIM_GATE_ENV, "off")
    w = _World()
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(cat)])
    if gate == "off":
        assert provider.main.judge_calls == [] and res.answer == MODEL_SAID
        return
    assert len(provider.main.judge_calls) == 1
    expected = WF.HANDOFF_OFFER_TEXT if cat == SC.CLAIM_HANDED_OFF else WF.NO_PENDING_WRITE_TEXT
    assert res.answer == expected
    assert _unbacked(res) == [cat]
    assert MODEL_SAID not in json.dumps(w.state, ensure_ascii=False)


@pytest.mark.parametrize("cat", [SC.CLAIM_COMPLETED, SC.CLAIM_CANCELLED])
async def test_v5a_i_claim_with_previous_turn_event_is_sent(api, cat):
    """V5 (a)／(i) 有事件：前回合已有收據（「已完成」）／已取消（「已取消」）⇒ 照送、⛔ 記未對到。"""
    w, _pid = await (_submitted_world() if cat == SC.CLAIM_COMPLETED else _cancelled_world())
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(cat)])
    assert len(provider.main.judge_calls) == 1
    assert res.answer == MODEL_SAID and _unbacked(res) == []


async def test_v5a_i_awaiting_with_live_card_is_sent(api):
    """V5 (a)／(i) 有事件：前回合程式出的卡仍 live ⇒「等待確認」照送（問句回合乙′：照送後接程式狀態行）。"""
    w = _World()
    r1, pid = await w.repair_card()
    res, provider = await _bt(w, "要按哪裡？", [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_AWAITING)])
    assert len(provider.main.judge_calls) == 1 and _unbacked(res) == []
    # 填欄只填答覆修復輪 3：本回合沒讀到值 ⇒ 前導句 `CARD_NO_CHANGE_TEXT`（原 `CARD_STILL_VALID_TEXT`）
    assert res.answer == f"{MODEL_SAID}\n\n{WF.CARD_NO_CHANGE_TEXT}\n{r1.answer}"
    assert res.trace.pending_id == pid


async def test_v5i_awaiting_with_live_select_scope_card_is_sent(api):
    """V5 (i)：點選範圍回合出的卡（模型自呼路徑，KD-1）仍 live ⇒ 下一回合「等待確認」照送。"""
    from tests.unit.agent.test_write_draft_flow_req import KEELUNG_ESTATE, _call, _confirm_args
    w = _World()
    _with_select_scope(w)
    payload = {"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "bill_id": 709744, "days": 7}
    card, _p = await _bt(w, "延後 7 天", [_call("confirm.request", _confirm_args(payload)), _out()],
                         intents=[_intent("none")])
    assert card.outcome["state"] == "confirm_pending", card.answer
    pid = card.trace.pending_id
    res, provider = await _bt(w, "要按哪裡？", [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_AWAITING)])
    assert len(provider.main.judge_calls) == 1 and _unbacked(res) == []
    assert res.answer.startswith(MODEL_SAID)
    assert w.db.live_pids(w.session_id) == [pid]


async def test_v5i_awaiting_with_live_document_card_is_sent(api):
    """V5 (i)：文件回合出的卡仍 live ⇒ 下一回合「等待確認」照送。"""
    from tests.unit.agent.test_assistant_documents_photos_req import _confirm_call, _receipt_doc
    w = _World()
    card, _p = await _bt(w, "這張收據開到合約 89481，項目水電費，期限 20261130",
                         [_confirm_call({"action": "manual_bill_create", "contract_ref": "89481",
                                         "title": "水電費", "total": 588, "date_expire": "20261130"}),
                          _out()],
                         document=_receipt_doc(), intents=[_intent("none")])
    assert card.outcome["state"] == "confirm_pending", card.answer
    res, provider = await _bt(w, "要按哪裡？", [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_AWAITING)])
    assert len(provider.main.judge_calls) == 1 and _unbacked(res) == []
    assert res.answer.startswith(MODEL_SAID)


def _setup_turn_type(w: _World, kind: str) -> dict:
    """V5 (b)：回合種類（回 `_bt` 額外參數）。"""
    if kind == "write_context":
        _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE})
        return {"message": "送出後多久會處理？"}
    if kind == "select_scope":
        _with_select_scope(w)
        return {"message": THANKS}
    if kind == "document_carry":
        _with_carry(w)
        return {"message": THANKS}
    if kind == "document":
        from tests.unit.agent.test_assistant_documents_photos_req import _receipt_doc
        return {"message": "這是什麼收據", "document": _receipt_doc()}
    assert kind == "knowledge"
    return {"message": THANKS}


TURN_TYPES = ["write_context", "select_scope", "document", "document_carry", "knowledge"]


@pytest.mark.parametrize("kind", TURN_TYPES)
async def test_v5b_every_turn_type_replaces_an_unbacked_claim(api, kind):
    """V5 (b)：寫入情境、點選範圍、文件、文件暫存、知識回合，模型文字被判「已完成」且無事件 ⇒ 都換句、
    模型文字 ⛔ 送出；寫入情境回合換成 B2 狀態回話，其餘換 `NO_PENDING_WRITE_TEXT`。"""
    w = _World()
    extra = _setup_turn_type(w, kind)
    message = extra.pop("message")
    res, provider = await _bt(w, message, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_COMPLETED)], **extra)
    assert len(provider.main.judge_calls) == 1, res.trace.violations
    assert MODEL_SAID not in res.answer and _unbacked(res) == [SC.CLAIM_COMPLETED]
    if kind == "write_context":
        _assert_missing_ask(res)
    else:
        assert res.answer == WF.NO_PENDING_WRITE_TEXT


@pytest.mark.parametrize("out_kind", ["answer", "ask", "recommend"])
async def test_v5c_answer_ask_recommend_are_all_judged(api, out_kind):
    """V5 (c)：知識回合 `answer`／`ask`／`recommend` 各一案 ⇒ 都經判讀；未對到 ⇒ 換句。"""
    w = _World()
    target = "choice" if out_kind == "ask" else None
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID, kind=out_kind, ask_target=target)],
                              intents=[_intent("none")], judge=[_claims(SC.CLAIM_COMPLETED)])
    assert len(provider.main.judge_calls) == 1
    assert res.answer == WF.NO_PENDING_WRITE_TEXT


async def test_v5c_handoff_is_never_judged(api):
    """V5 (c) 正對照：`kind=handoff` ⇒ ⛔ 呼叫判讀（DSP-021 固定句照舊）。"""
    w = _World()
    res, provider = await _bt(w, "我要找真人", [_out("", kind="handoff", handoff_reason="tool_unavailable",
                                                fact_class="other")],
                              intents=[_intent("none")], judge=[_claims(SC.CLAIM_HANDED_OFF)])
    assert res.kind == "handoff"
    assert provider.main.judge_calls == [] and SC.V_STATE_CLAIM_CHECK not in res.trace.violations


@pytest.mark.parametrize("gate", ["on", "off"])
async def test_v5d_structural_confirm_intent_is_replaced_without_judging(api, monkeypatch, gate):
    """V5 (d)：`kind=ask`、`ask_target=confirm_intent`、本回合未呼叫 `confirm.request`（現行 `prose_confirm_suspect`
    三條件）⇒ ⛔ 呼叫判讀、直接換句、記「等待確認」未對到。正對照（閘 off）：只記旗標、模型文字照送。"""
    if gate == "off":
        monkeypatch.setenv(SC.STATE_CLAIM_GATE_ENV, "off")
    w = _World()
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID + "？", kind="ask", ask_target="confirm_intent")],
                              intents=[_intent("none")])
    assert "prose_confirm_suspect" in res.trace.violations
    assert provider.main.judge_calls == []
    if gate == "on":
        assert res.answer == WF.NO_PENDING_WRITE_TEXT and _unbacked(res) == [SC.CLAIM_AWAITING]
        assert res.ask_target != "confirm_intent"
    else:
        assert MODEL_SAID in res.answer


async def _sleep_long(_kwargs):
    await asyncio.sleep(5)
    return _claims()


def _raise(_kwargs):
    raise RuntimeError("ZQ判讀例外ZQ")


FAILURES = {
    "timeout": _sleep_long,
    "not_json": "ZQ不是JSON",
    "out_of_domain": _claims("ZQ值域外"),
    "exception": _raise,
}


@pytest.mark.parametrize("failure", sorted(FAILURES))
@pytest.mark.parametrize("kind", TURN_TYPES)
async def test_v5e_judge_failure_fail_closed_on_card_capable_turns(api, monkeypatch, kind, failure,
                                                                  caplog):
    """V5 (e)：判讀逾時、非 JSON、值域外、例外 ⇒ 可出卡的回合（寫入情境、點選範圍、文件、文件暫存）換句
    （fail-closed）；知識回合照送；兩者皆記 `state_claim_check_failed`。log 只記例外類別名（⛔ 原文）。"""
    monkeypatch.setattr(SC, "STATE_CLAIM_TIMEOUT_S", 0.05)
    caplog.set_level(logging.DEBUG)
    w = _World()
    extra = _setup_turn_type(w, kind)
    message = extra.pop("message")
    res, provider = await _bt(w, message, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[FAILURES[failure]], **extra)
    assert len(provider.main.judge_calls) == 1
    assert SC.V_STATE_CLAIM_CHECK_FAILED in res.trace.violations
    if kind == "knowledge":
        assert res.answer == MODEL_SAID
    else:
        assert MODEL_SAID not in res.answer
        if kind == "write_context":
            _assert_missing_ask(res)
        else:
            assert res.answer == WF.NO_PENDING_WRITE_TEXT
    assert "ZQ判讀例外ZQ" not in caplog.text and "ZQ不是JSON" not in caplog.text


async def test_v5e_timeout_is_capped_by_the_turn_deadline(api, monkeypatch):
    """V5 (e)：逾時取 `STATE_CLAIM_TIMEOUT_S` 與回合剩餘時間較早者——剩餘 ≤0 ⇒ ⛔ 呼叫、直接判讀失敗。"""
    seen = {}
    real = SC.judge_state_claims

    async def _spy(create, **kw):
        seen.update(kw)
        return await real(create, **kw)

    monkeypatch.setattr(SC, "judge_state_claims", _spy)
    w = _World()
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                              budget=Budget(deadline_s=2.0))
    assert seen["timeout_s"] == 2.0                                       # min(4, 剩餘 2)
    assert len(provider.main.judge_calls) == 1 and res.answer == MODEL_SAID


@pytest.mark.parametrize("reply", [KNOWLEDGE_ANSWER, "好的，有需要再跟我說。", "這張帳單已繳清。"])
async def test_v5f_k_reply_without_claim_is_sent_verbatim(api, reply):
    """V5 (f)／(k)：不含帶狀態句（含轉述紀錄狀態「這張帳單已繳清」）、判讀回空 claims ⇒ 照送、逐字相等。"""
    w = _World()
    res, provider = await _bt(w, THANKS, [_out(reply)], intents=[_intent("none")], judge=[_claims()])
    assert len(provider.main.judge_calls) == 1
    assert res.answer == reply and _unbacked(res) == []
    assert SC.V_STATE_CLAIM_CHECK_FAILED not in res.trace.violations


SENTINEL_IN = "ZQ判讀輸入哨兵ZQ"
SENTINEL_OUT = "ZQ判讀輸出哨兵ZQ"


async def test_v5g_judge_input_metering_and_no_raw_text_anywhere(api, monkeypatch, caplog):
    """V5 (g)：判讀輸入只有模型回覆文字、包在 nonce 資料段內（⛔ 資料段、草稿值、卡文字）；輸出上限＝200；
    同意圖呼叫的模型與推理設定；token 經 `usage_metering.add_llm_usage` 計量；trace、agent_state（含 dialog）、
    log 不含判讀輸入輸出原文；被擋的模型文字不在 dialog。"""
    metered: list = []
    monkeypatch.setattr(usage_metering, "add_llm_usage", lambda model, usage: metered.append((model, usage)))
    caplog.set_level(logging.DEBUG)
    w = _World()
    r1, _pid = await w.repair_card()
    card = r1.answer
    metered.clear()
    reply = f"已幫你送出了{SENTINEL_IN}"
    judge_out = _fake_response(_fake_message(
        content=f"<reasoning>{SENTINEL_OUT}</reasoning>{_claims(SC.CLAIM_COMPLETED)}"),
        prompt_tokens=11, completion_tokens=3)
    res, provider = await _bt(w, "要按哪裡？", [_out(reply)], intents=[_intent("none")],
                              judge=[judge_out])
    (kw,), = [provider.main.judge_calls]
    assert kw["max_completion_tokens"] == SC.STATE_CLAIM_MAX_COMPLETION_TOKENS == 200
    assert kw["response_format"]["json_schema"]["name"] == SC.STATE_CLAIM_SCHEMA_NAME
    msgs = kw["messages"]
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[0]["content"] == SC.STATE_CLAIM_SYSTEM_PROMPT
    m = re.match(r"<<data:([^:]+):" + SC.STATE_CLAIM_DATA_LABEL + ">>", msgs[1]["content"])
    assert m, msgs[1]["content"]
    from services.agent.prompt_assembler import wrap_tool_data
    assert msgs[1]["content"] == wrap_tool_data(SC.STATE_CLAIM_DATA_LABEL, reply, m.group(1))
    assert m.group(1) != res.trace.trace_id
    for leaked in (STUDENT_ESTATE, "冷氣不冷", card, "<<data:" + m.group(1) + ":kb"):
        assert leaked not in msgs[1]["content"]
    intent_kw = provider.intent_calls[0]
    assert kw["model"] == intent_kw["model"]
    assert kw.get("extra_body") == intent_kw.get("extra_body")
    # 計量：判讀那一次以模型名＋usage 記一筆（意圖呼叫另有一筆）。
    assert (kw["model"], {"prompt_tokens": 11, "completion_tokens": 3}) in metered
    # 擋下：模型文字 ⛔ 送出、⛔ 進 dialog；原文 ⛔ 進 trace／state／log。
    assert SENTINEL_IN not in res.answer and _unbacked(res) == [SC.CLAIM_COMPLETED]
    trace_dump = repr(res.trace)
    state_dump = json.dumps(w.state, ensure_ascii=False, default=str)
    for s in (SENTINEL_IN, SENTINEL_OUT):
        assert s not in trace_dump and s not in state_dump and s not in caplog.text


def test_v5h_single_assembly_point_and_gate_before_it():
    """V5 (h) 靜態：`normalize_terminal_punctuation(` 於 `runtime.py` 恰 1 處；判讀閘呼叫在它之前（同函式）。"""
    src = (AGENT_DIR / "runtime.py").read_text(encoding="utf-8")
    assert src.count("normalize_terminal_punctuation(") == 1
    gate_call = src.find("await self._state_claim_gate(")
    assert gate_call != -1                                                  # 正對照：閘呼叫存在
    assert gate_call < src.find("normalize_terminal_punctuation(")
    tree = ast.parse(src)
    hosts = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name != "normalize_terminal_punctuation"
             and "normalize_terminal_punctuation(" in ast.get_source_segment(src, n)
             and not any(isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and "normalize_terminal_punctuation(" in ast.get_source_segment(src, c)
                         for c in ast.walk(n) if c is not n)]
    assert len(hosts) == 1                                                  # 最內層的組裝函式
    body = ast.get_source_segment(src, hosts[0])
    assert "self._state_claim_gate(" in body
    assert body.index("self._state_claim_gate(") < body.index("normalize_terminal_punctuation(")


async def test_v5j_replacement_texts_stay_true_after_receipt_and_handoff(api):
    """V5 (j)：session 有前回合收據／前回合轉人時，換回句 `NO_PENDING_WRITE_TEXT`、`HANDOFF_OFFER_TEXT`
    仍逐字等於常數（句子只說本回合或不宣稱狀態）。"""
    w, _pid = await _submitted_world()
    res, _p = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                        judge=[_claims(SC.CLAIM_AWAITING)])
    assert res.answer == WF.NO_PENDING_WRITE_TEXT
    res2, _p = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                         judge=[_claims(SC.CLAIM_HANDED_OFF)])
    assert res2.answer == WF.HANDOFF_OFFER_TEXT
    ho, _p = await _bt(w, "我要找真人", [_out("", kind="handoff", handoff_reason="tool_unavailable",
                                              fact_class="other")], intents=[_intent("none")])
    assert ho.kind == "handoff"
    res3, _p = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                         judge=[_claims(SC.CLAIM_HANDED_OFF)])
    assert res3.answer == WF.HANDOFF_OFFER_TEXT
    res4, _p = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                         judge=[_claims(SC.CLAIM_AWAITING)])
    assert res4.answer == WF.NO_PENDING_WRITE_TEXT
    for r in (res, res2, res3, res4):
        assert MODEL_SAID not in r.answer


# ════════════════════════════════════════════════════════════════════
# V8 (a)（B-R7）候選清單出口：給人看的版本
# ════════════════════════════════════════════════════════════════════
SENTINEL_QUERY = "ZQ哨兵查詢字串ZQ"


async def test_v8a_candidates_reply_has_no_model_hints_no_query_and_summary_dialog(api, monkeypatch):
    """V8 (a)：候選清單出口的回覆 ⛔ 含 `jgb2` 給模型的兩句提示（以常數比對；另注入哨兵到給模型版本）、
    ⛔ 含模型 payload 的查詢字串（哨兵）；`dialog_answer` 為程式摘要。正對照：給模型的 `text_for_model`
    仍含兩句提示與查詢字串。"""
    from services.agent.tools.registry import ToolResult
    from tests.unit.agent.test_confirm_candidates_buttons_req import _rows
    from tests.unit.agent.test_runtime_req import FakeProvider, FakeRegistry, _identity
    monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")          # 載具：模型自呼路徑直接拿到候選結果
    hint_sentinel = "ZQ給模型提示哨兵ZQ"
    monkeypatch.setattr(jgb2_tools, "CANDIDATES_MODEL_HINT_FOOTER",
                        jgb2_tools.CANDIDATES_MODEL_HINT_FOOTER + hint_sentinel)
    rows = _rows(2)
    for_model = jgb2_tools._candidates_text("bills", SENTINEL_QUERY, rows)
    # 正對照：給模型的版本含兩句提示、注入的哨兵、查詢字串
    assert jgb2_tools.CANDIDATES_MODEL_HINT_HEADER in for_model
    assert jgb2_tools.CANDIDATES_MODEL_HINT_FOOTER in for_model and hint_sentinel in for_model
    assert SENTINEL_QUERY in for_model
    payload = {"action": "bill_due_extend", "estate_name": SENTINEL_QUERY, "period": "九月", "days": 3}
    result = ToolResult(ok=True, data={"facts": "", "candidates": rows, "action": "bill_due_extend",
                                       "payload": payload}, text_for_model=for_model)
    state = {"agent": {}}
    provider = FakeProvider([_fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "延後", "payload": json.dumps(payload, ensure_ascii=False)},
        "c1")])), _out("不該走到這")])
    rt = AgentRuntime(provider, FakeRegistry(call_results=[result]),
                      FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(), Budget(),
                      stage="M1", clock=FakeClock())
    res = await rt.run_turn(_identity(), f"{SENTINEL_QUERY}九月的房租晚三天繳", state)
    assert "confirm_request_candidates" in res.trace.violations          # 前提：走到候選清單出口
    assert res.answer.startswith(runtime_mod.CONFIRM_CANDIDATES_TEXT)
    for leaked in (jgb2_tools.CANDIDATES_MODEL_HINT_HEADER, jgb2_tools.CANDIDATES_MODEL_HINT_FOOTER,
                   hint_sentinel, SENTINEL_QUERY):
        assert leaked not in res.answer
    assert res.answer == runtime_mod.CONFIRM_CANDIDATES_TEXT + "\n" + \
        jgb2_tools.candidates_text_for_user("bills", rows)
    assert "756240" in res.answer and "756241" in res.answer             # 列值照列
    dialog = state["agent"]["dialog"]
    assert dialog[-1] == {"role": "assistant",
                          "content": runtime_mod.CONFIRM_CANDIDATES_DIALOG_SUMMARY.format(n=2)}


async def test_v8a_real_registry_candidates_text_for_model_keeps_hints(api, monkeypatch):
    """V8 (a)：真 registry（`bill_due_extend` 物件有多筆帳單 ⇒ 候選）——回覆 ⛔ 含兩句提示；同一次工具結果的
    `text_for_model` 含兩句提示（正對照）；dialog 只寫程式摘要。

    A-2a（DSP-103 Q1 含帳單）：開關 on 時提議轉成的程式呼叫改出 A-2a 帳單候選清單（`pick:bill:`）；本題釘 off
    驗 B 的帳單候選出口逐字不變（A2-R12）。"""
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    from tests.unit.agent.test_write_draft_flow_req import KEELUNG_ESTATE, _call, _confirm_args
    w = _World()
    payload = {"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "days": 7}
    res, _p = await _bt(w, f"{KEELUNG_ESTATE} 帳單延後 7 天",
                        [_call("confirm.request", _confirm_args(payload)), _out(MODEL_SAID)],
                        intents=[_intent("none")])
    assert "confirm_request_candidates" in res.trace.violations, res.answer
    (_args, result), = w.reg.confirm_calls()
    assert jgb2_tools.CANDIDATES_MODEL_HINT_HEADER in result.text_for_model
    assert jgb2_tools.CANDIDATES_MODEL_HINT_FOOTER in result.text_for_model
    assert jgb2_tools.CANDIDATES_MODEL_HINT_HEADER not in res.answer
    assert jgb2_tools.CANDIDATES_MODEL_HINT_FOOTER not in res.answer
    n = len(res.quick_replies)
    assert n >= 2
    assert w.state["agent"]["dialog"][-1]["content"] == \
        runtime_mod.CONFIRM_CANDIDATES_DIALOG_SUMMARY.format(n=n)


# ════════════════════════════════════════════════════════════════════
# V9（B-R9）W-R3 形狀：卡物件「豪宅」、使用者「物件不對，是就是豪宅啦」
# ════════════════════════════════════════════════════════════════════
MANSION = "豪宅"
MANSION_ID = 990067338


def _add_mansion_estate() -> None:
    """fixture 加一筆標題恰為「豪宅」的物件（複製 67338、新 id、同可見性）。`api` fixture 已把 `_DATA`
    換成本測試自己的副本（`load_from`），測試結束由 monkeypatch 復原。"""
    data = fixture_store._DATA
    base = next(e for e in data["estates"] if e["id"] == 67338)
    row = copy.deepcopy(base)
    row.update(id=MANSION_ID, title=MANSION)
    data["estates"].append(row)
    data["estate_visibility"][str(MANSION_ID)] = list(data["estate_visibility"]["67338"])


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_v9_restating_mansion_lists_what_was_read(api, monkeypatch, b_reply):
    """V9：卡物件「豪宅」；使用者「物件不對，是就是豪宅啦」、意圖抽成「豪宅」⇒ 回覆含「卡片還在」句、列出
    「物件「豪宅」」、同卡同 pid、無新 token。正對照（off）：只有「卡片還在」句＋卡（不列讀到的值）。
    填欄只填答覆修復輪 4（brief-fix5）：on 的前導句由 `CARD_STILL_VALID_TEXT` 改為 `CARD_READ_SAME_LEAD`；off 照舊。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    # A-2a（§4.1「`repair_create` 物件多筆：出卡前先判」）：實測 mock 物件名稱查詢（`_viewer_estate_rows`
    # 「豪宅」）回 3 筆（68700、39931、35214），不含本題加的 990067338 ⇒ 開關 on 時出卡前判不出唯一、改出
    # 候選清單。本題驗 B 的重述句，與候選無關 ⇒ 釘 off（A2-R12）。
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    _add_mansion_estate()
    w = _World()
    r1, pid = await w.repair_card(f"{MANSION} 冷氣不冷", estate_name=MANSION)
    assert f"物件：{MANSION}" in r1.answer or MANSION in r1.answer             # 前提：卡上物件是「豪宅」
    rows_before = copy.deepcopy(w.db.rows)
    res = await w.turn("物件不對，是就是豪宅啦", script=[_out(MODEL_SAID)],
                       intents=[_intent("repair_create", estate_name=MANSION)])
    assert res.trace.pending_id == pid and res.quick_replies == C.confirm_quick_replies(pid)
    assert w.db.rows == rows_before and w.db.pids(w.session_id) == [pid]
    if b_reply == "on":
        line = WF.card_read_values_text([("物件", MANSION)])
        assert res.answer == f"{WF.CARD_READ_SAME_LEAD}\n{line}\n{r1.answer}", res.answer
        assert WF.CARD_STILL_VALID_TEXT not in res.answer
        assert "物件「豪宅」" in res.answer
    else:
        assert res.answer == f"{WF.CARD_STILL_VALID_TEXT}\n{r1.answer}"


# ════════════════════════════════════════════════════════════════════
# V11（B-R13）出卡與兌現不變量
# ════════════════════════════════════════════════════════════════════
async def test_v11_1_reissued_same_card_redeems_exactly_once(api):
    """V11 (1)：B 的新出口重出同卡 ⇒ 無新 token；舊 pid 可兌現 1 次（第二次不再寫入）。"""
    w = _World()
    r1, pid = await w.repair_card()
    res, _p = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    assert _branch(res) == WF.WRITE_REPLY_STATE_CARD_STILL_VALID and res.trace.pending_id == pid
    assert w.db.pids(w.session_id) == [pid]
    ok = await w.turn(f"confirm_submit:{pid}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    again = await w.turn(f"confirm_submit:{pid}")
    assert w.writes() == ["jgb2.action.repair_create"]
    assert w.db.redeemed(pid) is True
    del again, r1


async def test_v11_2_frozen_turn_never_issues_a_card(api):
    """V11 (2)：草稿完整、無有效卡、凍結回合（程式追問後的問句）⇒ 程式狀態回話與判讀閘換句都 ⛔ 出卡、
    token 表不變、回 `WRITE_NOT_ISSUED_TEXT`。"""
    for out, judge in ((_out(MODEL_SAID + "？", kind="ask", ask_target="description"), None),
                       (_out(MODEL_SAID), [_claims(SC.CLAIM_AWAITING)])):
        w = _World()
        _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷"},
                    asked=["description"])
        res, provider = await _bt(w, "冷氣不冷嗎？", [out], intents=[_intent("none")], judge=judge)
        assert res.answer == WF.WRITE_NOT_ISSUED_TEXT, res.answer
        assert w.db.rows == [] and w.reg.confirm_calls() == [] and res.quick_replies == []
        assert WF.V_PROGRAM_CONFIRM not in res.trace.violations


async def test_v11_2_deadline_short_never_issues_a_card(api):
    """V11 (2)：期限不足（提議路徑與判讀閘換句）⇒ ⛔ 出卡、回 `WRITE_NOT_ISSUED_TEXT`、token 表 0 列。"""
    text, good = GOOD["repair_create"]
    w = _World()
    res, _p = await _bt(w, text, [_proposal({"action": "repair_create", **good}), _out(MODEL_SAID)],
                        budget=Budget(deadline_s=5.9))
    assert res.answer == WF.WRITE_NOT_ISSUED_TEXT and w.db.rows == [] and w.reg.confirm_calls() == []
    w2 = _World()
    _seed_draft(w2, "repair_create", dict(REPAIR_FIELDS))
    res2, _p = await _bt(w2, "這樣就好了嗎？", [_out(MODEL_SAID)], intents=[_intent("none")],
                         judge=[_claims(SC.CLAIM_AWAITING)], budget=Budget(deadline_s=5.9))
    assert res2.answer == WF.WRITE_NOT_ISSUED_TEXT and w2.db.rows == [] and w2.reg.confirm_calls() == []


async def test_v11_2_reissue_gate_held_never_issues_a_card(api):
    """V11 (2)：重出擋關（綁定卡已有收據、草稿仍在 ⇒ `write_draft_reissue_skipped_has_receipt`）⇒ ⛔ 出卡、
    回 `WRITE_NOT_ISSUED_TEXT`、token 表不變。"""
    from tests.unit.agent.test_step3_write_lifecycle_req import CORRECT_TEXT, _correct_intent
    w = _World()
    _r1, pid = await w.repair_card()
    draft = copy.deepcopy(w.draft())
    await w.turn(f"confirm_submit:{pid}")
    w.state["agent"][WRITE_DRAFT_KEY] = draft
    rows_before = copy.deepcopy(w.db.rows)
    res, _p = await _bt(w, CORRECT_TEXT, [_out(MODEL_SAID)], intents=_correct_intent())
    assert "write_draft_reissue_skipped_has_receipt" in res.trace.violations
    assert res.answer == WF.WRITE_NOT_ISSUED_TEXT, res.answer
    assert w.db.rows == rows_before and w.db.pids(w.session_id) == [pid]


async def test_v11_2_submitted_edit_and_sensitive_handoff_keep_their_existing_exits(api):
    """V11 (2)：已送出修改（#9g）與 `allow_trigger=False`（敏感轉人）這兩道擋關在 B 之前由既有出口結束回合
    （`SUBMITTED_EDIT_TEXT`／轉人固定句）——B 的出口與判讀閘 ⛔ 介入（無 `write_reply_state:` 標記、⛔ 判讀）、
    ⛔ 出卡、token 表不變。"""
    from tests.unit.agent.test_step3_write_lifecycle_req import CORRECT_TEXT, NEW_DESC, _intent_mod
    w = _World()
    _r1, pid = await w.repair_card()
    await w.turn(f"confirm_submit:{pid}")
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, CORRECT_TEXT, [_out(MODEL_SAID)],
                              intents=[_intent_mod("repair_create", True, description=NEW_DESC)])
    assert res.answer == WF.SUBMITTED_EDIT_TEXT
    assert w.db.rows == rows_before and provider.main.judge_calls == []
    assert not any(v.startswith(STATE_PREFIX) for v in res.trace.violations)
    w2 = _World()
    _seed_draft(w2, "repair_create", dict(REPAIR_FIELDS))
    res2, p2 = await _bt(w2, "修繕費用怎麼算", [
        _out("", kind="handoff", fact_class="pricing", handoff_reason="sensitive_no_grounding")],
        intents=[_intent("repair_create", **REPAIR_FIELDS)])
    assert res2.kind == "handoff" and w2.db.rows == [] and w2.reg.confirm_calls() == []
    assert p2.main.judge_calls == []
    assert not any(v.startswith(STATE_PREFIX) for v in res2.trace.violations)


#: 本片新增的出口與狀態判定函式（V11 靜態、V16 (a)）。
B_REPLY_FUNCS = (
    "_write_reply_state", "_write_reply_state_exit", "_write_reply_program_exit",
    "_write_reply_kd3_exit", "_state_claim_replace_exit", "_write_reply_model_plus_status",
    "_write_reply_read_values_line", "_session_live_card", "_live_entry", "_state_claim_events",
    "_write_context_turn", "_write_draft_survives_turn",
)


def _funcs(path: Path) -> dict:
    src = path.read_text(encoding="utf-8")
    out: dict = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(ast.get_source_segment(src, node))
    return out


def test_v11_static_new_exits_never_create_tokens():
    """V11 靜態：本片新出口 ⛔ 呼叫 `_begin_pending_confirm`、⛔ 以任何方式呼叫 `confirm.request`
    （`CONFIRM_TOOL_NAME`、`registry.call`、`"confirm.request"`）。正對照：`_maybe_confirm_turn` 一類既有出卡
    路徑命中 `_begin_pending_confirm`。"""
    funcs = _funcs(AGENT_DIR / "runtime.py")
    assert any("_begin_pending_confirm(" in s for srcs in funcs.values() for s in srcs)   # 正對照
    for name in B_REPLY_FUNCS:
        (src,) = funcs[name]
        for banned in ("_begin_pending_confirm", "CONFIRM_TOOL_NAME", "registry.call", "confirm.request",
                       "redeem_pending("):
            assert banned not in src, (name, banned)


def test_v11_4_token_insert_lives_only_in_tools_confirm():
    """V11 (4) 靜態：`INSERT INTO agent_confirmation_tokens` 只在 `tools/confirm.py`；正對照同檔
    `UPDATE agent_confirmation_tokens` 命中。"""
    services = AGENT_DIR.parent
    insert = re.compile(r"INSERT\s+INTO\s+agent_confirmation_tokens")
    update = re.compile(r"UPDATE\s+agent_confirmation_tokens")
    hits = sorted(str(p.relative_to(services)) for p in services.rglob("*.py")
                  if insert.search(p.read_text(encoding="utf-8")))
    assert hits == ["agent/tools/confirm.py"], hits
    assert update.search((AGENT_DIR / "tools" / "confirm.py").read_text(encoding="utf-8"))


async def test_v11_3_readonly_view_gate_writes_nothing(api):
    """V11 (3)：影子回合下判讀閘（含換句）⛔ 寫 `agent_state`（`dialog` 除外，既有行為同 #9i）、⛔ 寫 token 表。"""
    w = _World()
    await w.repair_card()
    state_before = copy.deepcopy(w.state)
    rows_before = copy.deepcopy(w.db.rows)
    res, provider = await _bt(w, THANKS, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_COMPLETED)], readonly_view=True)
    assert len(provider.main.judge_calls) == 1 and res.answer == WF.NO_PENDING_WRITE_TEXT   # 前提：閘有跑
    assert w.db.rows == rows_before
    strip = lambda st: {k: v for k, v in st["agent"].items() if k != "dialog"}   # noqa: E731
    assert strip(w.state) == strip(state_before)


async def test_v11_5_card_turns_skip_the_gate(api):
    """V11 (5)：確認卡回合（程式出卡、A+ 卡片還在、B2 重出同卡）⛔ 經判讀閘；卡文字逐字＝formatter 輸出
    （雜湊＝`summary_sha256`）。"""
    w = _World()
    provider_judge = []
    r1, pid = await w.repair_card()
    assert C.sha256_hex(r1.answer) == w.db.row(pid)["summary_sha256"]
    assert SC.V_STATE_CLAIM_CHECK not in r1.trace.violations
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")],
                              judge=[_claims(SC.CLAIM_COMPLETED)])
    provider_judge.extend(provider.main.judge_calls)
    assert res.answer.endswith(r1.answer) and res.trace.pending_id == pid
    restate, p2 = await _bt(w, REPAIR_TEXT, [_out(MODEL_SAID)], program_first=True,
                            intents=[_intent("repair_create", **REPAIR_FIELDS)])
    provider_judge.extend(p2.main.judge_calls)
    assert restate.trace.pending_id == pid and restate.answer.endswith(r1.answer)
    assert provider_judge == []
    for r in (res, restate):
        assert SC.V_STATE_CLAIM_CHECK not in r.trace.violations


# ════════════════════════════════════════════════════════════════════
# V16（B-R8）程式回話不經 LLM、逐字常數
# ════════════════════════════════════════════════════════════════════
LLM_CALL_MARKERS = ("_next_model_message", "chat.completions", "provider.")


def test_v16a_program_reply_functions_never_call_an_llm():
    """V16 (a) 靜態：組 B2 狀態回話、狀態行、換回句的函式內 ⛔ `_next_model_message`、`chat.completions`、
    `provider.`；正對照：判讀閘函式 `_state_claim_gate` 命中其判讀呼叫（`chat.completions`）。"""
    funcs = _funcs(AGENT_DIR / "runtime.py")
    (gate,) = funcs["_state_claim_gate"]
    assert "chat.completions" in gate and "judge_state_claims" in gate               # 正對照
    for name in B_REPLY_FUNCS:
        (src,) = funcs[name]
        for marker in LLM_CALL_MARKERS:
            assert marker not in src, (name, marker)
    helpers = (
        (AGENT_DIR / "write_forms.py", "card_read_values_text"),
        (AGENT_DIR / "tools" / "confirm.py", "missing_labels_ask_text"),
        (AGENT_DIR / "tools" / "jgb2.py", "candidates_text_for_user"),
        (AGENT_DIR / "confirm_card.py", "card_display_rows"),
    )
    for path, name in helpers:
        (src,) = _funcs(path)[name]
        for marker in LLM_CALL_MARKERS:
            assert marker not in src, (name, marker)


def test_v16b_program_texts_are_fixed_constants():
    """V16 (b)：每個 B2 分支與換回句的回覆來源是常數或樣板（Q2 不潤飾）；各分支回覆逐字相等由 V3／V4／V5
    的單元斷言驗（`==` 常數或 `.format()`）。這裡驗常數本身非空、彼此不同、⛔ 含格式欄位以外的變數。
    F12 r6-3 (a)：固定句清單加「已改成：{title}（編號 {id}）。」（名稱只取系統列，見 r6 測試檔 (j)）。"""
    texts = [WF.CARD_STILL_VALID_TEXT, WF.CARD_UNCHANGED_TEXT, WF.CARD_DIFFERS_TEXT,
             WF.WRITE_NOT_ISSUED_TEXT, WF.NO_PENDING_WRITE_TEXT, WF.HANDOFF_OFFER_TEXT,
             WF.CARD_NO_CHANGE_TEXT]
    assert all(isinstance(t, str) and t and "{" not in t for t in texts)
    assert len(set(texts)) == len(texts)
    assert set(re.findall(r"{(\w+)}", C.MISSING_FIELDS_ASK_TEMPLATE)) == {"labels"}
    assert set(re.findall(r"{(\w+)}", WF.CARD_READ_VALUES_TEMPLATE)) == {"pairs"}
    # F12 r6-3 (a)（計畫 §11.6、§11.8 R6-S2）：改選回合未出卡的告知句——樣板欄位只含 `{title}`、`{id}`；
    # 寫進 dialog 的程式摘要是常數、⛔ 含任何格式欄位（不含名稱）。
    from services.agent import write_candidates as WC
    assert re.findall(r"{(\w+)}", WC.CANDIDATE_REPICK_TEXT) == ["title", "id"]
    assert set(re.findall(r"{[^}]*}", WC.CANDIDATE_REPICK_TEXT)) == {"{title}", "{id}"}
    assert WC.CANDIDATE_REPICK_DIALOG_SUMMARY and "{" not in WC.CANDIDATE_REPICK_DIALOG_SUMMARY
    assert WC.CANDIDATE_REPICK_TEXT not in texts and WC.CANDIDATE_REPICK_DIALOG_SUMMARY not in texts


def test_state_claim_prompt_excludes_pick_record_and_supply_data_from_awaiting():
    """原話 8（V12 停點）：「請使用者從查到的紀錄選一筆／補資料／核對名稱條件」⛔ 屬等待確認；
    等待確認只限要按確認／送出或等使用者確認已整理好的待辦事（真陽性範圍不變）。"""
    p = SC.STATE_CLAIM_SYSTEM_PROMPT
    line = next(l for l in p.splitlines() if l.startswith(f"- {SC.CLAIM_AWAITING}："))
    assert "按確認或送出後才辦" in line and "內容已整理好、只等使用者點頭" in line
    assert "要選哪一筆紀錄" in line and "提供或補充什麼資料" in line and "名稱編號或條件對不對" in line
    assert "不屬於這一類" in line


# ════════════════════════════════════════════════════════════════════
# B2 (3)（原話 9／B-R4）：封閉三動作欄位齊、但名稱解析不唯一 ⇒ 與出卡路徑同一份缺欄清單
# ════════════════════════════════════════════════════════════════════
MANUAL_BILL = "manual_bill_create"
#: fixture `assistant_demo_vendor4.json`：990101「合成展示合約 甲」、990102「合成展示合約 乙」。
MANY_CONTRACT_REF = "合成展示合約"          # 關鍵字對到兩份、無完全相符 ⇒ `many`
ONE_CONTRACT_REF = "合成展示合約 甲"        # 完全相符一份 ⇒ `one`


def _manual_bill_fields(ref: str) -> dict:
    return {"contract_ref": ref, "title": "管理費", "total": "1000", "date_expire": "2026-11-30"}


def _spy_prepare(monkeypatch) -> list:
    """包住真的 `_prepare_closed_action`、記下每次呼叫的動作（行為不變）。"""
    calls: list = []
    real = C._prepare_closed_action

    async def _spy(identity, action, payload, **kw):
        # A-2a：`confirm_request`／`write_name_candidates` 另帶具名參數 `program_pick`／`candidates`，照轉。
        calls.append(action)
        return await real(identity, action, payload, **kw)

    monkeypatch.setattr(C, "_prepare_closed_action", _spy)
    return calls


async def _assert_contract_resolves(w: _World, ref: str, expected: str) -> None:
    """前提：替身 API 上這個合約指稱的解析結果（`many`／`one`）。"""
    role_id, user_id = C._identity_pair(w.ident)
    status, _row = await C._resolve_unique_contract(jgb2_tools._get_api(), role_id, user_id, ref)
    assert status == expected, (ref, status)


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_b2_3_closed_action_ambiguous_contract_asks_for_contract(api, monkeypatch, b_reply):
    """(a)：手動帳單草稿欄位齊（`WF.missing_labels` 為空）、`contract_ref` 是對到多筆的名稱 ⇒ 非問句回合回覆＝
    `MISSING_FIELDS_ASK_TEMPLATE` 套「合約」（出卡路徑同一支 `_prepare_closed_action` 的缺欄清單）、
    trace 有 `write_reply_state:missing_fields`、token 表列數不變、主模型只被叫一次、草稿不被改動。
    正對照（off）：模型文字照送。"""
    if b_reply == "off":
        _b_off(monkeypatch)
    # A-2a（A2-R8）：開關 on 時名稱多筆改回候選清單（test_a2a_write_candidates_req.py 的 V2）；本題釘 off
    # 驗 B 的缺欄追問逐字不變（A2-R12）。
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    w = _World()
    await _assert_contract_resolves(w, MANY_CONTRACT_REF, "many")
    fields = _manual_bill_fields(MANY_CONTRACT_REF)
    assert WF.missing_labels(MANUAL_BILL, WF.to_payload(MANUAL_BILL, fields)) == []   # 前提：表單判不缺
    _seed_draft(w, MANUAL_BILL, fields)
    calls = _spy_prepare(monkeypatch)
    rows_before = len(w.db.rows)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    if b_reply == "off":
        assert MODEL_SAID in res.answer
        return
    assert _branch(res) == WF.WRITE_REPLY_STATE_MISSING
    assert "write_reply_state:missing_fields" in res.trace.violations
    assert res.answer == C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="合約"), res.answer
    assert res.outcome["state"] == "clarifying"
    assert res.trace.pending_id is None and res.quick_replies == []
    assert len(w.db.rows) == rows_before
    assert len(provider.calls) == 1
    assert calls == [MANUAL_BILL]                                    # 正對照：真的走出卡路徑同一支
    assert w.draft()["fields"] == fields                             # ⛔ 改動草稿
    assert SOURCE_PROGRAM in res.trace.violations and MODEL_SAID not in res.answer


async def test_b2_3_closed_action_unique_contract_stays_not_issued(api, monkeypatch):
    """(b) 正對照：同草稿但名稱解析到唯一一筆（`_prepare_closed_action` 回 `None`）且無有效卡 ⇒
    維持 `WRITE_NOT_ISSUED_TEXT`。"""
    # A-2a：開關 on 時 B2 (3) 先以 `write_name_candidates` 多呼叫一次 `_prepare_closed_action`；本題驗 B 的
    # 呼叫次數（恰 1 次）⇒ 釘 off（A2-R12）。
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    w = _World()
    await _assert_contract_resolves(w, ONE_CONTRACT_REF, "one")
    fields = _manual_bill_fields(ONE_CONTRACT_REF)
    _seed_draft(w, MANUAL_BILL, fields)
    calls = _spy_prepare(monkeypatch)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    assert _assert_program_text_reply(res, provider, w, rows_before=0) == \
        WF.WRITE_REPLY_STATE_NOT_ISSUED
    assert res.answer == WF.WRITE_NOT_ISSUED_TEXT
    assert calls == [MANUAL_BILL]
    assert w.draft()["fields"] == fields


async def test_b2_3_non_closed_action_does_not_call_prepare_closed_action(api, monkeypatch):
    """(c)：非封閉動作（`bill_due_extend` 欄位齊、無卡）⇒ 維持 `WRITE_NOT_ISSUED_TEXT`，且 ⛔ 呼叫
    `_prepare_closed_action`（正對照見 (a)／(b)：同一支 spy 有記到封閉動作的呼叫）。"""
    w = _World()
    fields = {"bill_id": "709744", "days": "7"}
    assert WF.missing_labels("bill_due_extend",
                             WF.to_payload("bill_due_extend", fields)) == []     # 前提：欄位齊
    _seed_draft(w, "bill_due_extend", fields)
    calls = _spy_prepare(monkeypatch)
    res, provider = await _bt(w, LATER, [_out(MODEL_SAID)], intents=[_intent("none")])
    assert _assert_program_text_reply(res, provider, w, rows_before=0) == \
        WF.WRITE_REPLY_STATE_NOT_ISSUED
    assert res.answer == WF.WRITE_NOT_ISSUED_TEXT
    assert calls == []


@pytest.mark.parametrize("ref, expected", [(MANY_CONTRACT_REF, ["合約"]), (ONE_CONTRACT_REF, [])])
async def test_b2_3_closed_action_missing_labels_does_not_mutate_payload(api, ref, expected):
    """(d)：`closed_action_missing_labels` ⛔ 改動傳入的 payload（呼叫前後 dict 相等）；`many` ⇒ `["合約"]`、
    `one` ⇒ `[]`。正對照：直接把同一份 payload 交給 `_prepare_closed_action` 會被就地改寫（`one` 時寫入
    `contract_id`），證明「相等」不是因為本來就不會改。"""
    w = _World()
    payload = WF.to_payload(MANUAL_BILL, _manual_bill_fields(ref))
    before = copy.deepcopy(payload)
    assert await C.closed_action_missing_labels(w.ident, MANUAL_BILL, payload) == expected
    assert payload == before
    if ref == ONE_CONTRACT_REF:
        exposed = copy.deepcopy(payload)
        early, _e, _s = await C._prepare_closed_action(w.ident, MANUAL_BILL, exposed)
        assert early is None and exposed != before and "contract_id" in exposed   # 正對照


async def test_b2_3_closed_action_missing_labels_fail_soft_and_guards(api, monkeypatch, caplog):
    """`closed_action_missing_labels` 的邊界：非封閉動作 ⇒ `[]`（⛔ 呼叫 `_prepare_closed_action`）；接真 JGB
    且屬尚未開放的動作 ⇒ `[]`（⛔ 往下查，同出卡路徑先以「尚未開放」收尾）；例外 ⇒ `[]`、log 不含值。"""
    w = _World()
    payload = WF.to_payload(MANUAL_BILL, _manual_bill_fields(MANY_CONTRACT_REF))
    calls = _spy_prepare(monkeypatch)
    assert await C.closed_action_missing_labels(w.ident, MANUAL_BILL, payload) == ["合約"]   # 正對照
    assert calls == [MANUAL_BILL]
    assert await C.closed_action_missing_labels(w.ident, "bill_due_extend", {"days": 7}) == []
    assert calls == [MANUAL_BILL]
    monkeypatch.setattr(api, "use_mock", False)
    assert await C.closed_action_missing_labels(w.ident, MANUAL_BILL, payload) == []
    assert calls == [MANUAL_BILL]
    monkeypatch.setattr(api, "use_mock", True)

    async def _boom(*_a, **_kw):
        raise RuntimeError("ZQ例外值ZQ")

    monkeypatch.setattr(C, "_prepare_closed_action", _boom)
    with caplog.at_level(logging.INFO):
        assert await C.closed_action_missing_labels(w.ident, MANUAL_BILL, payload) == []
    assert "ZQ例外值ZQ" not in caplog.text and MANY_CONTRACT_REF not in caplog.text
    assert "RuntimeError" in caplog.text                                       # 正對照：真的記了那一行
