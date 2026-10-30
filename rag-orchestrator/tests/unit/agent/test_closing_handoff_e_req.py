"""unit：E 片——收尾與「明確要真人」由程式決定（E7、E8、E9）。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-closing-handoff-e-20261026.md` §4.1；
凍結驗收 `acceptance-closing-handoff-e-20261026.md` 的 E-R1～E-R6、E-R10（E7～E9 為機制項）。

判斷只來自 AI 的理解標籤 `dialog_act`（本檔的假 provider 直接給標籤值）；⛔ 用關鍵字或詞表（E-R5，
`test_e7_new_code_has_no_chinese_keyword_matching` 掃新增程式）。
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import json
import re
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.budget import Budget
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.question_sensitivity import question_sensitive
from services.agent.runtime import ASK_TARGET_TEXT, AgentRuntime, _agent_output_response_format
from services.agent.tools.handoff import HANDOFF_REASONS, HANDOFF_SPEC
from services.agent.verifier import OutputVerifier
from services.presales_gate import MODEL_VISIBLE_HANDOFF_REASONS, HandoffReason

from tests.unit.agent.test_aplus_card_program_only_req import _seed_draft
from tests.unit.agent.test_runtime_req import (  # noqa: F401
    FakeAssembler, FakeClock, VerifierVerdict, _fake_message, _fake_response,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _RouteVerifier, _World, _env, api,
)
from tests.unit.agent.test_verifier_req import _RULES_PATH
from tests.unit.agent.test_write_draft_flow_req import STUDENT_ESTATE, _intent, _out, _Provider

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-closing-handoff-e")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py；E 標籤 `none`
    走填欄只填答覆 B 的組合由該檔測）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


ENV = WF.CLOSING_HANDOFF_ENV
RUNTIME_PATH = Path(runtime_mod.__file__)
WF_PATH = Path(WF.__file__)

#: 改前（E 片前的基準碼）送給模型的位元組摘要（`json.dumps(..., ensure_ascii=False)` 的 UTF-8 sha256）。
#: 取法：基準碼（`~/jgb-archive/arch-step3-20261018/e/baseline/`）在 `_World()`、
#: `_Provider([_out("好的")], [_intent("none")])`、訊息 `GOLDEN_MESSAGE` 下的第一次主模型呼叫。
GOLDEN_MESSAGE = "請問怎麼設定繳費日"
GOLDEN = {
    "response_format": ("0f19cd057c2f61d626b2c4ce18dd5003abd3acdf971d47acb5033c5166263119", 2900),
    "tools": ("2cc1c2ddf1d645204a9553b136d2b061793b51f0242d1ef2eb12cb5186ac9a37", 7504),   # 2026-10-29 列表查詢對齊真 JGB：統計工具 description 改了執行中狀態名（未收＝待繳費或待對帳不變）
    "handoff_spec": ("bf2bf0eda4e09ee6026bb7f4891df5255cf06d671df86d7a54853317875d1da9", 630),
}


def _digest(x) -> tuple:
    s = json.dumps(x, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest(), len(s)


# ════════════════════════════════════════════════════════════════════
# 假 provider：標籤呼叫（schema 名 DialogAct，回 `act`）；寫入意圖回應內的 dialog_act 程式不讀（r5 附錄）
# ════════════════════════════════════════════════════════════════════
def _act_response(act):
    content = json.dumps({"dialog_act": act}, ensure_ascii=False) if act is not None else "不是 JSON"
    return _fake_response(_fake_message(content=content), prompt_tokens=11, completion_tokens=3)


def _intent_with_act(act):
    """寫入意圖呼叫的回應（action=none），同一次呼叫帶標籤。"""
    return _intent(raw=json.dumps({"action": "none", "fields": [], "dialog_act": act}, ensure_ascii=False))


class _LabelProvider(_Provider):
    """`_Provider` ＋ `DialogAct` 獨立呼叫的腳本。`label_delay`＝標籤回應前先睡幾秒（真時間）；
    `hang_main`＝主模型呼叫永不回（只靠標籤搶先取消才收得了回合）；`label_only_delay`＝只有標籤呼叫多睡幾秒
    （寫入意圖呼叫照常先回）。`act` 可給清單（修正 9）：第 n 次標籤呼叫回第 n 個值（用完沿用最後一個）；
    `label_delays` 清單＝第 n 次標籤呼叫額外睡的秒數（確認呼叫逾時用）。"""

    def __init__(self, script, intents=None, *, act="none", label_delay=0.0, hang_main=False,
                 label_only_delay=0.0, label_delays=None):
        super().__init__(script, intents)
        self.label_delays = list(label_delays or [])
        self.act = act
        self.label_delay = label_delay
        self.label_only_delay = label_only_delay
        self.hang_main = hang_main
        self.label_calls: list = []

    async def create(self, **kwargs):
        rf = kwargs.get("response_format") or {}
        name = (rf.get("json_schema") or {}).get("name")
        if name == WF.DIALOG_ACT_SCHEMA_NAME:
            n = len(self.label_calls)
            self.label_calls.append(kwargs)
            extra = self.label_delays[n] if n < len(self.label_delays) else 0.0
            if self.label_delay or self.label_only_delay or extra:
                await asyncio.sleep(self.label_delay + self.label_only_delay + extra)
            if isinstance(self.act, list):
                return _act_response(self.act[min(n, len(self.act) - 1)])
            return _act_response(self.act)
        if name == WF.WRITE_INTENT_SCHEMA_NAME:
            if self.label_delay:
                await asyncio.sleep(self.label_delay)
            return await super().create(**kwargs)
        if self.hang_main:
            await asyncio.sleep(3600)
        await asyncio.sleep(0.01)    # 讓同回合並行建立的意圖／標籤 task 先跑（真模型呼叫本來就要時間）
        return await super().create(**kwargs)


def _runtime(w: _World, provider, *, verifier=None):
    verifier = verifier or _RouteVerifier([VerifierVerdict(ok=True)] * 6)
    return AgentRuntime(provider, w.reg, verifier, FakeAssembler(), Budget(), stage="M1",
                        clock=FakeClock(), db_pool=w.db)


async def _turn(w: _World, message, *, act="none", label_path="combined", script=None, intents=None,
                hang_main=False, label_delay=0.0, monkeypatch=None, verifier=None, label_only_delay=0.0,
                label_delays=None):
    """一個回合。`label_path`：`combined`＝看得到寫入動作（寫入意圖呼叫＋標籤呼叫並行）；
    `label_only`＝看不到任何寫入動作（只有標籤呼叫）。回 (res, provider, runtime)。"""
    if label_path == "label_only":
        assert monkeypatch is not None
        monkeypatch.setattr(AgentRuntime, "_write_draft_any_visible", lambda self, identity: False)
        provider = _LabelProvider(list(script if script is not None else [_out("主模型的回答")]),
                                  intents, act=act, hang_main=hang_main, label_delay=label_delay)
    else:
        if intents is None:
            intents = [_intent_with_act(act[0] if isinstance(act, list) else act)]
        provider = _LabelProvider(list(script if script is not None else [_out("主模型的回答")]),
                                  intents, act=act, hang_main=hang_main, label_delay=label_delay,
                                  label_only_delay=label_only_delay, label_delays=label_delays)
    rt = _runtime(w, provider, verifier=verifier)
    res = await rt.run_turn(w.ident, message, w.state)
    assert rt._write_intent_calls == {}
    assert rt._dialog_act_calls == {}
    return res, provider, rt


@pytest.fixture
def closing_handoff_off(monkeypatch):
    """其他功能的「線上送出內容與改前逐字相同」類測試用：釘住 E 片開關 off（E 片 on 的行為由本檔測）。"""
    monkeypatch.setenv(ENV, "off")


PATHS = ["combined", "label_only"]
ASK_HUMAN = "我要找真人客服"
WRITE_NO_DRAFT_WAIT = runtime_mod.WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S


# ════════════════════════════════════════════════════════════════════
# E-R4：值域隔離（E7 前兩項）
# ════════════════════════════════════════════════════════════════════
def test_e7_model_visible_domain_excludes_user_request():
    """主輸出 schema 的 `handoff_reason` enum 與 `handoff.request` 工具 enum 都不含 `user_request`；
    正對照：`HandoffReason` 本身含它，且舊 6 值都還在。"""
    assert HandoffReason.user_request.value == "user_request"                       # 正對照
    props = _agent_output_response_format()["json_schema"]["schema"]["properties"]
    branch = [b for b in props["handoff_reason"]["anyOf"] if b.get("type") == "string"][0]
    assert "user_request" not in branch["enum"]
    assert branch["enum"] == list(MODEL_VISIBLE_HANDOFF_REASONS)
    tool_enum = HANDOFF_SPEC["input_schema"]["properties"]["reason"]["enum"]
    assert "user_request" not in tool_enum and tool_enum == list(HANDOFF_REASONS)
    assert "no_grounding" in tool_enum and "no_grounding" in branch["enum"]         # 正對照


@pytest.mark.parametrize("switch", ["on", "off"])
async def test_e8_bytes_equal_pre_change_golden(api, monkeypatch, switch):
    """E8：主呼叫 `response_format`、工具定義、`HANDOFF_SPEC` 與改前逐位元組相同（sha256＋長度），
    開關 on／off 皆然（值域隔離與開關無關）。正對照：on 與 off 同一次實跑的 `response_format` 相同。"""
    monkeypatch.setenv(ENV, switch)
    monkeypatch.delenv("AGENT_WRITE_TOOLS_ENABLED", raising=False)   # 改前摘要是在未開寫入工具的環境取的
    w = _World()
    _res, provider, _rt = await _turn(w, GOLDEN_MESSAGE, script=[_out("好的")], intents=[_intent("none")])
    call = provider.calls[0]
    assert _digest(call["response_format"]) == GOLDEN["response_format"]
    assert _digest(call["tools"]) == GOLDEN["tools"]
    assert _digest(HANDOFF_SPEC) == GOLDEN["handoff_spec"]
    assert _digest(_agent_output_response_format()) == GOLDEN["response_format"]


@pytest.mark.parametrize("switch", ["off", "on"])
async def test_e8_off_makes_no_label_call_and_no_field(api, monkeypatch, switch):
    """寫入意圖呼叫不論開關都沒有 `dialog_act` 欄位與規則句（計畫 r5 附錄：標籤一律走獨立呼叫）；
    開關 off：不建只含標籤的呼叫（兩種路徑）；正對照：on 時兩種路徑各有一次標籤呼叫。"""
    monkeypatch.setenv(ENV, switch)
    w = _World()
    _r, prov, _ = await _turn(w, GOLDEN_MESSAGE, script=[_out("好的")])
    intent_rf = prov.intent_calls[0]["response_format"]["json_schema"]["schema"]
    assert WF.DIALOG_ACT_KEY not in intent_rf["properties"]
    sys_prompt = prov.intent_calls[0]["messages"][0]["content"]
    assert WF.DIALOG_ACT_RULE not in sys_prompt
    assert sys_prompt == WF.write_intent_system_prompt(enum_labels=True)     # 與改前同一個產生函式、同參數
    assert (len(prov.label_calls) == 1) is (switch == "on")                  # combined 路徑也另發標籤呼叫
    w2 = _World()
    _r, prov2, _ = await _turn(w2, GOLDEN_MESSAGE, label_path="label_only", monkeypatch=monkeypatch,
                               script=[_out("好的")])
    assert (len(prov2.label_calls) == 1) is (switch == "on")
    assert prov2.intent_calls == []


async def test_e8_label_comes_only_from_the_label_call(api, monkeypatch):
    """計畫 r5 附錄：程式只讀獨立標籤呼叫的 `dialog_act`。寫入意圖回應裡即使帶 `dialog_act=wants_human`，
    標籤呼叫回 `none` ⇒ 不轉人；正對照：標籤呼叫回 `wants_human` ⇒ 程式轉人。"""
    monkeypatch.delenv(ENV, raising=False)
    w = _World()
    res, prov, _rt = await _turn(w, ASK_HUMAN, act="none", intents=[_intent_with_act("wants_human")],
                                 script=[_out("主模型的回答")])
    assert len(prov.label_calls) == 1
    assert res.kind != "handoff" and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    w2 = _World()
    res2, _p2, _rt2 = await _turn(w2, ASK_HUMAN, act="wants_human", intents=[_intent_with_act("none")])
    assert res2.kind == "handoff" and WF.V_DIALOG_ACT_EXIT in res2.trace.violations       # 正對照


# ════════════════════════════════════════════════════════════════════
# E-R1：明確要真人 ⇒ 程式轉人
# ════════════════════════════════════════════════════════════════════
def _assert_program_handoff(res):
    assert res.kind == "handoff"
    assert res.outcome["state"] == "handoff"
    assert res.answer == WF.USER_REQUEST_HANDOFF_TEXT
    assert res.handoff["reason"] == "user_request" and res.handoff["message"] == WF.USER_REQUEST_HANDOFF_TEXT
    assert WF.V_DIALOG_ACT_EXIT in res.trace.violations


@pytest.mark.parametrize("path", PATHS)
async def test_e1_wants_human_is_a_program_handoff(api, monkeypatch, path):
    """E-R1：標籤 `wants_human` ⇒ `kind=handoff`、`outcome.state=handoff`、回覆為程式樣板；
    程式轉人經 `exit_gates.finalize` 後仍是轉人（結果即 finalize 的輸出）。"""
    monkeypatch.delenv(ENV, raising=False)
    w = _World()
    res, _p, _rt = await _turn(w, ASK_HUMAN, act="wants_human", label_path=path, monkeypatch=monkeypatch)
    _assert_program_handoff(res)


async def test_e1_program_handoff_survives_exit_gates_finalize(api, monkeypatch):
    """程式轉人以程式來源標記辨識（`acc._program_handoff`），經 `exit_gates.finalize` 後仍是 `kind=handoff`、
    reason `user_request`；正對照：同一個 `user_request` 若出自主模型自報（旗標沒設），不是轉人（見 E-R4 測試）。"""
    seen = {}
    real = runtime_mod.exit_gates.finalize

    def spy(acc, result, **kw):
        out = real(acc, result, **kw)
        if getattr(acc, "_program_handoff", False):
            seen["before"], seen["after"] = result.kind, out.kind
            seen["reason"] = out.handoff["reason"]
        return out

    monkeypatch.setattr(runtime_mod.exit_gates, "finalize", spy)
    w = _World()
    res, _p, _rt = await _turn(w, ASK_HUMAN, act="wants_human")
    assert seen == {"before": "handoff", "after": "handoff", "reason": "user_request"}
    _assert_program_handoff(res)


async def test_e1_wants_human_with_pending_card_still_hands_off_and_keeps_the_card(api, monkeypatch):
    """E-R1 情境：有確認卡未按時同樣直接轉；卡照留。"""
    w = _World()
    _r, pid = await w.repair_card()
    res, _p, _rt = await _turn(w, ASK_HUMAN, act="wants_human")
    _assert_program_handoff(res)
    assert w.pending()[pid].get("receipt") is None and w.pending()[pid].get("invalidated") is not True


async def test_e1_program_first_turn_waits_for_a_late_label(api):
    """E-R1：程式優先入口這一輪由程式回話（不叫主模型）時，標籤比寫入意圖晚回 ⇒ 迴圈前仍等標籤（決定點 (a)），
    `wants_human` 照樣程式轉人；⛔ 程式回話先結束回合把標籤取消（E1 候選情境 2 場的現象）。"""
    w = _World()
    _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE})
    res, _p, _rt = await _turn(w, "冷氣不冷，算了我要找真人", act="wants_human", label_only_delay=0.3,
                               intents=[_intent("repair_create", description="冷氣不冷")])
    _assert_program_handoff(res)
    assert WF.V_PROGRAM_CONFIRM in res.trace.violations
    assert WF.V_DIALOG_ACT_FALLBACK not in res.trace.violations


async def test_e1_wants_human_with_draft_in_progress_hands_off(api):
    """E-R1 情境：寫入草稿進行中（含追問中凍結：`asked` 非空且當句是問句）同樣直接轉。"""
    w = _World()
    _seed_draft(w, "estate_create", {"title": "測試新物件甲"}, asked=["city"])
    res, _p, _rt = await _turn(w, "可以幫我轉真人客服嗎？", act="wants_human")
    _assert_program_handoff(res)


# ════════════════════════════════════════════════════════════════════
# E-R2／E-R3：收尾與未決狀態
# ════════════════════════════════════════════════════════════════════
def _assert_program_closing(res):
    assert res.kind == "answer" and res.handoff is None
    assert res.outcome["state"] == "answered"
    assert res.answer == WF.CLOSING_TEXT
    assert WF.V_DIALOG_ACT_EXIT in res.trace.violations


@pytest.mark.parametrize("path", PATHS)
async def test_e2_resolved_without_pending_is_a_program_closing(api, monkeypatch, path):
    """E-R2：標籤 `resolved`、無未決狀態 ⇒ `CLOSING_TEXT`、`kind=answer`、`outcome.state=answered`；⛔ 轉人。"""
    w = _World()
    res, _p, _rt = await _turn(w, "好的，謝謝", act="resolved", label_path=path, monkeypatch=monkeypatch)
    _assert_program_closing(res)


async def test_e3_resolved_with_pending_card_is_not_closed_and_keeps_the_card(api):
    """E-R3：確認卡未按 ⇒ ⛔ 程式收尾，卡照留（仍可兌現）。"""
    w = _World()
    _r, pid = await w.repair_card()
    res, _p, _rt = await _turn(w, "好的，謝謝", act="resolved")
    assert res.answer != WF.CLOSING_TEXT and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    assert w.pending()[pid].get("receipt") is None and w.pending()[pid].get("invalidated") is not True


async def test_e3_resolved_with_draft_in_progress_is_not_closed_and_keeps_the_draft(api):
    """E-R3：寫入草稿進行中 ⇒ ⛔ 程式收尾，草稿仍在。"""
    w = _World()
    _seed_draft(w, "estate_create", {"title": "測試新物件甲"})
    res, _p, _rt = await _turn(w, "好的，謝謝", act="resolved")
    assert res.answer != WF.CLOSING_TEXT and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    assert w.draft() is not None and w.draft()["action"] == "estate_create"


async def test_e3_label_none_means_a_new_request_is_not_closed(api):
    """E-R3：同句帶新請求（AI 標的不是 `resolved`）⇒ 照現行，由主模型處理。"""
    w = _World()
    res, _p, _rt = await _turn(w, "謝謝，另外想問繳費日怎麼設", act="none", script=[_out("主模型處理新請求")])
    assert res.answer != WF.CLOSING_TEXT and "主模型處理新請求" in res.answer


# ════════════════════════════════════════════════════════════════════
# E-R6：敏感題維持現行
# ════════════════════════════════════════════════════════════════════
async def test_e9_sensitive_sentence_never_uses_the_program_exit(api):
    """E-R6：當句命中 `question_sensitive` ⇒ 不走程式轉人出口（敏感五類維持 DSP-009 固定句）。
    前提（正對照）：該句確實命中，且同一句換成非敏感句時走程式出口。"""
    rules = VerifierRules.load(_RULES_PATH)
    sensitive = next(m for m in ("你們的報價多少錢，我要找真人", "收費多少，請轉真人客服",
                                 "我要看價格，找真人客服") if question_sensitive(m, rules))
    assert not question_sensitive(ASK_HUMAN, rules)                                  # 正對照
    w = _World()
    sensitive_out = _out("", kind="handoff", handoff_reason="sensitive_no_grounding", fact_class="pricing")
    res, _p, _rt = await _turn(w, sensitive, act="wants_human", verifier=OutputVerifier(rules),
                               script=[sensitive_out] * 3)
    assert WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    assert res.answer != WF.USER_REQUEST_HANDOFF_TEXT
    assert res.kind == "handoff" and res.handoff["reason"] == "sensitive_no_grounding"   # 現行敏感路徑
    w2 = _World()
    res2, _p, _rt = await _turn(w2, ASK_HUMAN, act="wants_human", verifier=OutputVerifier(rules))
    _assert_program_handoff(res2)                                                    # 正對照


# ════════════════════════════════════════════════════════════════════
# E-R4：主模型自報不是轉人的觸發來源
# ════════════════════════════════════════════════════════════════════
def _real_verifier(mode: str) -> OutputVerifier:
    return OutputVerifier(VerifierRules.load(_RULES_PATH), mode=mode)


def _self_reported_user_request():
    return _out("", kind="handoff", handoff_reason="user_request", fact_class="other")


@pytest.mark.parametrize("mode", ["enforce", "observe_only"])
@pytest.mark.parametrize("bad_reason", ["user_request", "some_invisible_value"])
async def test_e7_switch_on_self_reported_invisible_reason_is_downgraded(api, monkeypatch, mode, bad_reason):
    """E-R4：開關 on，主模型輸出 `kind=handoff` 且 `handoff_reason` 不在模型可見值域（含 `user_request`）、
    零查詢 ⇒ 視同自報 `no_grounding`，走現行降級（`handoff_without_lookup`，答 `ASK_TARGET_TEXT`），
    Verifier 擋或觀察模式都一樣。⛔ 變成轉人。"""
    monkeypatch.delenv(ENV, raising=False)
    w = _World()
    out = _out("", kind="handoff", handoff_reason=bad_reason, fact_class="other")
    res, _p, _rt = await _turn(w, "隨便問一句", act="none", script=[out], verifier=_real_verifier(mode))
    assert res.kind != "handoff"
    assert WF.V_DIALOG_ACT_REASON_OUT_OF_DOMAIN in res.trace.violations
    assert "handoff_without_lookup" in res.trace.violations
    assert res.answer == ASK_TARGET_TEXT
    assert WF.V_DIALOG_ACT_EXIT not in res.trace.violations                          # 不是程式出口


@pytest.mark.parametrize("mode", ["enforce", "observe_only"])
async def test_e8_switch_off_self_reported_user_request_behaves_as_before(api, monkeypatch, mode):
    """E8：開關 off，主模型自報 `handoff_reason=user_request`：不加降級（與改前相同）。
    observe_only ⇒ 與改前相同地留成轉人（`user_request` 不在非敏感集合，降級閘不動它）；
    enforce ⇒ Verifier 以 `handoff_reason_invalid` 擋下（改前同）。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    res, prov, _rt = await _turn(w, "隨便問一句", script=[_self_reported_user_request()] * 4,
                                 intents=[_intent("none")], verifier=_real_verifier(mode))
    assert WF.V_DIALOG_ACT_REASON_OUT_OF_DOMAIN not in res.trace.violations
    assert prov.label_calls == [] and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    if mode == "observe_only":
        assert res.kind == "handoff" and res.handoff["reason"] == "user_request"
    else:
        # Verifier 擋下（值域外）⇒ 改寫輪用盡 ⇒ 預算耗盡轉人；總之不是 `user_request` 轉人
        assert res.handoff["reason"] == "budget_exhausted" and res.handoff["reason"] != "user_request"


def test_e8_verifier_domain_is_model_visible_subset():
    """Verifier 值域檢查用模型可見子集：`user_request` ⇒ `handoff_reason_invalid`；正對照：`no_grounding` 通過。"""
    v = _real_verifier("enforce")
    for reason, ok in (("user_request", False), ("no_grounding", True)):
        out = AgentOutput(kind="handoff", fact_class="feature", handoff_reason=reason, sentences=[])
        verdict = v.verify(out, {}, "問怎麼操作", None, resolved={}, resolve_errors={})
        assert verdict.ok is ok, (reason, verdict)
        if not ok:
            assert verdict.schema_cause == "handoff_reason_invalid"


# ════════════════════════════════════════════════════════════════════
# 時點：標籤搶先取消主模型（決定點 b）、不落入 budget_exhausted
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("path", PATHS)
async def test_e7_label_first_cancels_the_main_call_without_budget_exhausted(api, monkeypatch, path):
    """標籤先完成（`wants_human`）而主模型永不回 ⇒ 取消主模型、記 `dialog_act_late`、程式轉人；
    取消有自己的例外，⛔ 落入 `budget_exhausted`（W2 期限）。"""
    w = _World()
    res, _p, _rt = await asyncio.wait_for(
        _turn(w, ASK_HUMAN, act="wants_human", label_path=path, monkeypatch=monkeypatch, hang_main=True),
        timeout=20)
    _assert_program_handoff(res)
    if path == "label_only":    # 看不到寫入動作：沒有程式優先入口的等待，標籤與主模型真的在迴圈內競速
        assert WF.V_DIALOG_ACT_LATE in res.trace.violations
    assert res.trace.llm_calls == 0 or WF.V_DIALOG_ACT_LATE in res.trace.violations
    assert "budget_exhausted" not in " ".join(map(str, res.trace.violations))
    assert res.trace.handoff_reason == "user_request"


async def test_e7_label_first_closing_cancels_the_main_call(api):
    """同上，標籤 `resolved`、無未決 ⇒ 取消主模型、程式收尾。"""
    w = _World()
    res, _p, _rt = await asyncio.wait_for(_turn(w, "謝謝你", act="resolved", hang_main=True), timeout=20)
    _assert_program_closing(res)
    assert "budget_exhausted" not in " ".join(map(str, res.trace.violations))


@pytest.mark.parametrize("case", ["no_draft_slow_label", "frozen_slow_label"])
async def test_e7_in_loop_race_label_cancels_main_on_no_draft_and_frozen_turns(api, case):
    """決定點 (b)：程式優先入口沒等到標籤（無草稿回合等 1 秒；追問中凍結的回合不等）⇒ 標籤在主模型迴圈內搶先完成
    ⇒ 取消主模型、記 `dialog_act_late`、程式轉人；⛔ `budget_exhausted`。"""
    w = _World()
    if case == "frozen_slow_label":
        _seed_draft(w, "estate_create", {"title": "測試新物件甲"}, asked=["city"])
        message, delay = "可以幫我轉真人客服嗎？", 0.3
    else:
        message, delay = ASK_HUMAN, WRITE_NO_DRAFT_WAIT + 0.4
    res, _p, _rt = await asyncio.wait_for(
        _turn(w, message, act="wants_human", hang_main=True, label_delay=delay), timeout=25)
    _assert_program_handoff(res)
    assert WF.V_DIALOG_ACT_LATE in res.trace.violations
    assert "budget_exhausted" not in " ".join(map(str, res.trace.violations))


async def test_e7_label_first_with_pending_state_does_not_cancel_main(api):
    """正對照：同樣標籤先完成，但 `resolved` 有未決卡 ⇒ ⛔ 取消主模型；主模型照回。"""
    w = _World()
    _r, _pid = await w.repair_card()
    res, prov, _rt = await _turn(w, "謝謝你", act="resolved", script=[_out("主模型照回")])
    assert WF.V_DIALOG_ACT_LATE not in res.trace.violations and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    assert len(prov.calls) == 1 and res.answer != WF.CLOSING_TEXT      # 主模型照常被呼叫；卡仍在（B 片程式回話）


async def test_e7_label_late_main_output_is_used_and_marked_fallback(api):
    """決定點 (c)：主模型先回、標籤逾 1 秒仍未完成 ⇒ 用主模型輸出、記 `dialog_act_fallback`（後備）。"""
    w = _World()
    res, _p, _rt = await asyncio.wait_for(
        _turn(w, ASK_HUMAN, act="wants_human", label_delay=30.0, script=[_out("主模型的回答")]), timeout=25)
    assert WF.V_DIALOG_ACT_FALLBACK in res.trace.violations
    assert WF.V_DIALOG_ACT_EXIT not in res.trace.violations and "主模型的回答" in res.answer


@pytest.mark.parametrize("path", PATHS)
async def test_e7_unparsable_or_missing_label_falls_back_to_the_main_output(api, monkeypatch, path):
    """標籤解析不出／值域外 ⇒ 沒有標籤：照現行（主模型輸出）；⛔ 程式出口。"""
    w = _World()
    res, _p, _rt = await _turn(w, ASK_HUMAN, act=None, label_path=path, monkeypatch=monkeypatch,
                               intents=[_intent_with_act("not_a_real_value")] if path == "combined" else None)
    assert WF.V_DIALOG_ACT_EXIT not in res.trace.violations and "主模型的回答" in res.answer


# ════════════════════════════════════════════════════════════════════
# E-R13：追問欄位中的道謝／要真人不當欄位答覆
# ════════════════════════════════════════════════════════════════════
THANKS_MID_FIELD = "好喔謝謝"


def _seed_asking_description(w: _World) -> None:
    """修繕草稿只缺「問題描述」，且上一回合程式已追問該欄（`asked`）。"""
    _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE}, asked=["description"])


def _description(w: _World):
    return (w.draft() or {}).get("fields", {}).get("description")


async def test_e13_control_without_label_the_thanks_is_filled_into_the_field(api):
    """正對照（證明情境鋪得出現行問題）：標籤 `none` ⇒ 道謝被當欄位答覆填入（改前現象 `write_draft_answer_filled`）。"""
    w = _World()
    _seed_asking_description(w)
    res, _p, _rt = await _turn(w, THANKS_MID_FIELD, act="none")
    assert "write_draft_answer_filled" in res.trace.violations
    assert WF.V_DIALOG_ACT_FILL_SKIPPED not in res.trace.violations
    assert _description(w) == THANKS_MID_FIELD or THANKS_MID_FIELD in res.answer


async def test_e13_resolved_label_is_not_filled_draft_kept_and_reasks(api):
    """E-R13：追問欄位中，當句標籤 `resolved` ⇒ 不填入欄位、草稿原樣保留、不收尾（E-R3）、不出卡，回現行缺欄追問。"""
    w = _World()
    _seed_asking_description(w)
    res, _p, _rt = await _turn(w, THANKS_MID_FIELD, act="resolved")
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    assert "write_draft_answer_filled" not in res.trace.violations
    assert _description(w) is None and w.draft() is not None and w.draft()["action"] == "repair_create"
    assert w.draft()["fields"].get("estate_name") == STUDENT_ESTATE
    assert res.answer != WF.CLOSING_TEXT and WF.V_DIALOG_ACT_EXIT not in res.trace.violations
    assert THANKS_MID_FIELD not in res.answer and w.pending() == {}
    assert res.outcome["state"] != "confirm_pending"


async def test_e13_resolved_keeps_the_asked_field_so_the_next_answer_is_filled(api):
    """E-R13「草稿保留並重問缺的欄位」：道謝回合不填，追問中的欄位（`asked`）也保留 ⇒ 下一句答覆照現行整句填入
    （E14 帳單組 2 場：道謝回合取走 `asked` 後沒放回，下一句只能靠意圖抽值，抽不到草稿就閒置清掉）。"""
    w = _World()
    _seed_asking_description(w)
    res, _p, _rt = await _turn(w, THANKS_MID_FIELD, act="resolved")
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    assert w.draft()["asked"] == ["description"]
    res2, _p2, _rt2 = await _turn(w, "冷氣不冷", act="none", intents=[_intent("none")])
    assert "write_draft_answer_filled" in res2.trace.violations
    assert _description(w) == "冷氣不冷" or res2.outcome["state"] == "confirm_pending"


@pytest.mark.parametrize("program_first", ["on", "unavailable"])
async def test_e13_resolved_model_proposal_with_the_thanks_is_not_merged(api, monkeypatch, program_first):
    """E-R13：道謝回合主模型自呼 `confirm.request`、把道謝那句提議成欄位值 ⇒ ⛔ 合併、⛔ 出卡；
    程式回缺欄追問、草稿與追問中的欄位保留（`e/after6/E14` 帳單組「3Q」被提議成帳單項目而出卡）。
    `on`：程式優先入口依草稿重發（`fill_reask`），主模型不被叫；`unavailable`：程式優先入口不成立（例：意圖等待
    逾時）、主模型照跑 ⇒ 提議走 r3 AP-7 (2) 由程式回缺欄追問（`write_proposal_no_value`）。
    正對照：同一提議在標籤 `none` 時照現行合併出卡。"""
    from tests.unit.agent.test_aplus_card_program_only_req import _proposal

    def proposal():
        return [_proposal({"action": "repair_create", "estate_name": STUDENT_ESTATE,
                           "description": THANKS_MID_FIELD}), _out("主模型的回答")]

    if program_first == "unavailable":
        async def _no_program_first(self, *a, **k):
            return None
        monkeypatch.setattr(AgentRuntime, "_write_draft_program_first", _no_program_first)
    w = _World()
    _seed_asking_description(w)
    res, prov, _rt = await _turn(w, THANKS_MID_FIELD, act="resolved", script=proposal())
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    if program_first == "unavailable":
        assert WF.V_WRITE_PROPOSAL_NO_VALUE in res.trace.violations
    else:
        assert prov.calls == []
    assert _description(w) is None and w.draft()["asked"] == ["description"]
    assert res.outcome["state"] == "clarifying" and w.pending() == {}
    assert THANKS_MID_FIELD not in res.answer

    w2 = _World()                                                                    # 正對照
    _seed_asking_description(w2)
    res2, _p2, _rt2 = await _turn(w2, THANKS_MID_FIELD, act="none", script=proposal())
    assert res2.outcome["state"] == "confirm_pending" and THANKS_MID_FIELD in res2.answer


async def test_e13_resolved_intent_value_from_the_thanks_is_not_merged_and_program_reasks(api):
    """E-R13：道謝回合寫入意圖呼叫把道謝那句抽成欄位值 ⇒ ⛔ 合併、⛔ 出卡；程式依草稿回缺欄追問（⛔ 交主模型），
    草稿與追問中的欄位保留（verifier X7：建物件「OK 3q」的「3q」被抽成物件名稱而出卡，`e/x7-verifier/x7/fill1`）。
    正對照：同一意圖在標籤 `none` 時照現行合併出卡。"""
    def intents():
        return [_intent("repair_create", estate_name=STUDENT_ESTATE, description=THANKS_MID_FIELD)]

    w = _World()
    _seed_asking_description(w)
    res, prov, _rt = await _turn(w, THANKS_MID_FIELD, act="resolved", intents=intents())
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    assert _description(w) is None and w.draft()["asked"] == ["description"]
    assert res.outcome["state"] == "clarifying" and w.pending() == {}
    assert "問題描述" in res.answer and THANKS_MID_FIELD not in res.answer
    assert prov.calls == []                                                          # 程式回話，主模型沒被叫
    assert res.answer != WF.CLOSING_TEXT and res.kind != "handoff"

    w2 = _World()                                                                    # 正對照
    _seed_asking_description(w2)
    res2, _p2, _rt2 = await _turn(w2, THANKS_MID_FIELD, act="none", intents=intents())
    assert res2.outcome["state"] == "confirm_pending" and THANKS_MID_FIELD in res2.answer


async def test_e13_wants_human_label_is_not_filled_and_hands_off(api):
    """E-R13＋E-R1：追問欄位中，當句標籤 `wants_human` ⇒ 程式轉人；欄位不填、草稿保留。"""
    w = _World()
    _seed_asking_description(w)
    res, _p, _rt = await _turn(w, "不用填了，我要找真人", act="wants_human")
    _assert_program_handoff(res)
    assert _description(w) is None and w.draft() is not None


async def test_e13_unfinished_label_reasks_the_field(api):
    """修正 9（業主 2026-10-26「逾時就重問缺欄」）：追問欄位中標籤未完成 ⇒ ⛔ 整句填入，程式重問缺欄、草稿與追問中
    的欄位保留（照現行整句填入時「ok thx」「我想找真人客」被填進欄位出卡，`e/fix8/recheck`、`e/after8/E1`）。"""
    w = _World()
    _seed_asking_description(w)
    res, _p, _rt = await asyncio.wait_for(
        _turn(w, THANKS_MID_FIELD, act="resolved", label_delay=30.0), timeout=25)
    assert WF.V_DIALOG_ACT_FIELD_UNSETTLED_REASK in res.trace.violations
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    assert "write_draft_answer_filled" not in res.trace.violations
    assert _description(w) is None and w.draft()["asked"] == ["description"]
    assert res.outcome["state"] == "clarifying" and w.pending() == {}
    assert "問題描述" in res.answer and res.kind != "handoff"


async def test_e13_resolved_needs_a_second_label_to_skip(api):
    """修正 9（業主 2026-10-26「再問一次標籤確認」）：追問欄位中第一次標籤 `resolved` ⇒ 另發一次同輸入的確認呼叫；
    確認為 `none` ⇒ 是欄位答覆，照現行填入（線上把真答覆「E14測試物件」「清潔費」誤標道謝而跳過，`e/fix8/recheck`）。
    正對照：確認也 `resolved` ⇒ 跳過、重問。"""
    w = _World()
    _seed_asking_description(w)
    res, prov, _rt = await _turn(w, "冷氣不冷", act=["resolved", "none"], intents=[_intent("none")])
    assert len(prov.label_calls) == 2
    assert prov.label_calls[1]["messages"] == prov.label_calls[0]["messages"]        # 同一份輸入
    assert f"{WF.V_DIALOG_ACT_FIELD_CONFIRM_PREFIX}none" in res.trace.violations
    assert WF.V_DIALOG_ACT_CONFIRM_CALL in res.trace.violations
    assert WF.V_DIALOG_ACT_FILL_SKIPPED not in res.trace.violations
    assert "write_draft_answer_filled" in res.trace.violations
    assert _description(w) == "冷氣不冷" or res.outcome["state"] == "confirm_pending"

    w2 = _World()                                                                    # 正對照
    _seed_asking_description(w2)
    res2, prov2, _rt2 = await _turn(w2, THANKS_MID_FIELD, act=["resolved", "resolved"])
    assert len(prov2.label_calls) == 2
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res2.trace.violations
    assert _description(w2) is None and res2.outcome["state"] == "clarifying"


async def test_e13_unfinished_confirm_label_reasks(api):
    """修正 9：確認呼叫在 `DIALOG_ACT_FIELD_CONFIRM_WAIT_S` 內沒回 ⇒ 照「逾時就重問缺欄」：跳過、重問，確認呼叫取消並計量。"""
    w = _World()
    _seed_asking_description(w)
    res, prov, _rt = await asyncio.wait_for(
        _turn(w, THANKS_MID_FIELD, act=["resolved", "none"], label_delays=[0.0, 30.0]), timeout=25)
    assert len(prov.label_calls) == 2
    assert f"{WF.V_DIALOG_ACT_FIELD_CONFIRM_PREFIX}None" in res.trace.violations
    assert WF.V_DIALOG_ACT_CONFIRM_CALL_CANCELLED in res.trace.violations
    assert WF.V_DIALOG_ACT_FILL_SKIPPED in res.trace.violations
    assert _description(w) is None and res.outcome["state"] == "clarifying"


async def test_e13_switch_off_behaves_as_before(api, monkeypatch):
    """開關 off ⇒ 同改前：沒有標籤，道謝被填入；沒有新標記。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    _seed_asking_description(w)
    res, prov, _rt = await _turn(w, THANKS_MID_FIELD, intents=[_intent("none")])
    assert "write_draft_answer_filled" in res.trace.violations
    assert WF.V_DIALOG_ACT_FILL_SKIPPED not in res.trace.violations and prov.label_calls == []


# ════════════════════════════════════════════════════════════════════
# 標籤輸入契約
# ════════════════════════════════════════════════════════════════════
def test_e7_label_domain_and_parser():
    assert WF.DIALOG_ACT_DOMAIN == (WF.DIALOG_ACT_WANTS_HUMAN, WF.DIALOG_ACT_RESOLVED, WF.DIALOG_ACT_NONE)
    assert WF.parse_dialog_act_content('{"dialog_act": "wants_human"}') == "wants_human"
    assert WF.parse_dialog_act_content('{"dialog_act": "resolved"}') == "resolved"
    assert WF.parse_dialog_act_content('{"dialog_act": "none"}') == "none"
    for bad in ("", "不是 JSON", '{"dialog_act": "x"}', '{"other": 1}', None):
        assert WF.parse_dialog_act_content(bad) is None, bad
    assert WF.parse_dialog_act_content(
        '{"dialog_act": "none"}{"dialog_act": "resolved"}') is None                  # 互相衝突 ⇒ 未提供
    schema = WF.dialog_act_only_schema()
    assert schema["properties"][WF.DIALOG_ACT_KEY]["enum"] == list(WF.DIALOG_ACT_DOMAIN)


async def test_e7_no_label_call_for_document_turns_and_label_call_shape(api, monkeypatch):
    """獨立標籤呼叫：同模型、`max_completion_tokens` 800、輸入含當句；schema 名 `DialogAct`。"""
    w = _World()
    _r, prov, rt = await _turn(w, "謝謝", label_path="label_only", monkeypatch=monkeypatch, act="none")
    (call,) = prov.label_calls
    assert call["model"] == rt._model and call["max_completion_tokens"] == WF.WRITE_INTENT_MAX_COMPLETION_TOKENS == 800
    assert call["messages"][-1] == {"role": "user", "content": "謝謝"}
    assert call["response_format"]["json_schema"]["name"] == "DialogAct"
    # 修正 6：系統句先看這句要做的事，再接標籤規則（寫入意圖呼叫的系統句不帶這段，r5）。
    sys_prompt = call["messages"][0]["content"]
    assert sys_prompt == WF.dialog_act_only_system_prompt()
    assert sys_prompt.index(WF.DIALOG_ACT_TASK_FIRST) < sys_prompt.index(WF.DIALOG_ACT_RULE)
    assert WF.DIALOG_ACT_TASK_FIRST not in WF.write_intent_system_prompt(enum_labels=True, dialog_act=False)


# ════════════════════════════════════════════════════════════════════
# E-R5：新增程式無中文關鍵字比對
# ════════════════════════════════════════════════════════════════════
_CJK = re.compile(r"[一-鿿]")
_NEW_RUNTIME_FUNCS = (
    "_closing_active", "_start_dialog_act_call", "_dialog_act_label", "_closing_pending_state",
    "_dialog_act_decision", "_dialog_act_exit", "_pre_loop_program_exit_pending", "_dialog_act_pre_loop",
    "_dialog_act_after_output",
)
_NEW_WF_FUNCS = ("closing_handoff_enabled_from_env", "dialog_act_only_system_prompt", "dialog_act_only_schema",
                 "dialog_act_only_response_format", "parse_dialog_act_content")


def _functions(path: Path, names) -> list:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert sorted(n.name for n in found) == sorted(names), "掃描對象缺漏（函式改名了？）"
    return found


def _keyword_matches(fn) -> list:
    """函式本體（不含 docstring）裡以中文字面量做比對的位置：`in`／`==`／`startswith` 等方法、`re.*`。"""
    hits = []
    doc = fn.body[0].value if (fn.body and isinstance(fn.body[0], ast.Expr)
                               and isinstance(fn.body[0].value, ast.Constant)) else None

    def has_cjk_const(node):
        return any(isinstance(n, ast.Constant) and isinstance(n.value, str) and n is not doc
                   and _CJK.search(n.value) for n in ast.walk(node))

    for n in ast.walk(fn):
        if isinstance(n, ast.Compare) and has_cjk_const(n):
            hits.append(ast.unparse(n))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in {"startswith", "endswith", "find", "index", "count", "match", "search",
                               "fullmatch", "findall", "sub", "split", "replace"} and has_cjk_const(n):
                hits.append(ast.unparse(n))
            elif isinstance(n.func.value, ast.Name) and n.func.value.id == "re":
                hits.append(ast.unparse(n))
    return hits


def test_e7_new_code_has_no_chinese_keyword_matching():
    """E-R5：本片新增函式沒有任何中文字面量比對／正則（判斷只來自 AI 標籤）。
    正對照：掃描法對一個故意用 `"謝謝" in msg` 的函式要抓到。"""
    probe = ast.parse(textwrap.dedent('''
        def bad(msg):
            """說明"""
            return "謝謝" in msg
    ''')).body[0]
    assert _keyword_matches(probe), "正對照：掃描法壞了"
    clean = ast.parse("def ok(msg):\n    return msg == 'wants_human'\n").body[0]
    assert not _keyword_matches(clean)
    for path, names in ((RUNTIME_PATH, _NEW_RUNTIME_FUNCS), (WF_PATH, _NEW_WF_FUNCS)):
        for fn in _functions(path, names):
            assert _keyword_matches(fn) == [], (fn.name, _keyword_matches(fn))
    # 規則句與樣板是給模型／使用者的文字，不是比對：只確認沒有被用在 `in` 比對（上面已掃函式本體）。
    assert inspect.getsource(runtime_mod.AgentRuntime._dialog_act_decision).count("WF.DIALOG_ACT_") >= 2
