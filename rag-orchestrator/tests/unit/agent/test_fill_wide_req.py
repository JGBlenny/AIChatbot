"""unit：填欄擴及首句、卡後、多欄回合（計畫 `.kiro/specs/agentic-mcp-orchestration/plan-fill-wide-20261028.md` §4.1～4.4；
凍結清單 `acceptance-fill-wide-20261028.md` 的 FW11 (a)～(p)，皆為機制項）。

業主原話：「我建議另開一片處理首句、確認卡後、多欄回合的錯筆卡」（業主回「同意」）；核可時 Q1「當讀不到、照現行收值」、
Q3「算錯筆卡，本片要修」。

分工（DSP-091）：哪部分是資料由 AI 在寫入意圖呼叫標出（本檔的假 provider 直接給 `data_texts`）；收不收、要不要說沒套用
由程式決定（`_write_draft_turn_gate` 寬回合分支、`_fill_wide_*`）。⛔ 程式端用道謝詞表。

條目 ↔ 測試：測試名一律以 `test_fw11_<字母>_*` 開頭；3 個意圖呼叫建構點的測試名另含 `build_main`／`build_pick_rule`／
`build_target_picked`。測試句只用計畫 §4.5 已列的句子（與其補完的地址）。

資料走真 `JGBSystemAPI`＋`JGBMockTransport`＋真 `mcp_facade.build_registry`（`_World`）；全部離線，⛔ 打任何模型。
期望值由測試寫死（⛔ 引用被測物輸出當期望）。
"""
from __future__ import annotations

import ast
import asyncio
import copy
import dataclasses
import json
import logging
import textwrap
from pathlib import Path

import pytest

from services import usage_metering
from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.runtime import AgentRuntime, TurnAccumulator, _WriteDraftTurn

from tests.unit.agent.test_aplus_card_program_only_req import GOOD, _proposal
from tests.unit.agent.test_fill_data_text_req import (
    CC, CONTRACT, EST, FIX3_PARTIAL_NOTE_V1, FIX4_CASES, FIX6_NAME_NOTE_V1, MB, PRE_CHANGE_DIGESTS, RC4_MSG,
    RC4_PICK_NOTE_V1, RC4_SEGS, RC4_VALUES, REPAIR,
    _builder_kwargs, _digest, _direct, _draft, _fi, _field, _fields, _fix4_gate_equals_off, _hang, _listed_on, _NO,
    _p32_listed, _p32_turn, _picked_on, _schema, _seed_draft, _system, _v,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import STUDENT_ESTATE, _intent, _out, _Provider

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-fill-wide-20261028")]
FILL_ENV = WF.FILL_DATA_TEXT_ENV
WIDE_ENV = WF.FILL_DATA_TEXT_WIDE_ENV
RT = AgentRuntime
RUNTIME_PATH = Path(runtime_mod.__file__)
MB_TEXT, MB_GOOD = GOOD[MB]
CC_TEXT, CC_GOOD = GOOD[CC]


@pytest.fixture(autouse=True)
def _wide_on(monkeypatch):
    """本檔預設兩個開關都 on（未設＝on）；off 的測試自己 `setenv`。"""
    monkeypatch.delenv(FILL_ENV, raising=False)
    monkeypatch.delenv(WIDE_ENV, raising=False)


# ── 共用 ─────────────────────────────────────────────────────────────
def _fill_marks(res) -> list:
    return [m for m in _v(res) if str(m).startswith("fill_")]


async def _card(monkeypatch, action: str) -> _World:
    """兩個開關都 off 出一張卡（改前路徑；假意圖不帶資料段），之後回合回到本檔預設（on）。"""
    text, good = GOOD[action]
    monkeypatch.setenv(FILL_ENV, "off")
    w = _World()
    res = await w.turn(text, intents=[_intent(action, **{k: str(v) for k, v in good.items()})])
    assert res.outcome["state"] == "confirm_pending", res.answer
    monkeypatch.delenv(FILL_ENV, raising=False)
    return w


def _payload(w: _World, res) -> dict:
    return dict(w.pending()[res.trace.pending_id]["payload"])


def _bind_live_card(w: _World, action: str, pid: str = "pid-r1c", **extra) -> dict:
    """放一筆與草稿同動作、同建立者的待確認筆（`_write_draft_bound_card` 認得的綁定卡）；`extra` 可帶 `invalidated`／
    `receipt`。§4.1 (b) 卡後寬回合的條件之一是活的綁定卡（§11 r1c）。回該筆（測試可再改）。"""
    entry = {"action": action, "creator": runtime_mod._pending_creator(w.ident), "payload": {}, **extra}
    w.state.setdefault("agent", {}).setdefault(runtime_mod.PENDING_CONFIRM_KEY, {})[pid] = entry
    return entry


def _wdirect(w: _World, draft, message: str, *, asked=(), obj=None, consumed: bool = True, prior=(),
             card_live: bool = False):
    """建一個寫入回合的回合內狀態（同 `_write_draft_begin` 的欄位），依開關跑 `_fill_begin_intent_call`，再以 `obj`
    （意圖呼叫驗過的原始物件）跑寬回合讀資料段。回 `(runtime, acc, 建構點參數)`。
    `card_live`＝回合開始時草稿綁定的卡還活著（`bound_card_live`；§4.1 (b) 卡後寬回合的條件之一，§11 r1c）。"""
    rt = w.runtime(_Provider([]))
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-wide", start=0.0)
    acc.write_draft = _WriteDraftTurn(
        draft=draft, owner=runtime_mod._write_draft_owner(w.ident), user_texts=[*prior, message],
        asked=list(asked), had_draft=draft is not None, user_message=message, bound_card_live=card_live)
    kw = rt._fill_begin_intent_call(acc)
    if obj is not None:
        rt._fill_wide_read_data(acc.write_draft, obj)
    acc.write_draft.intent_consumed = consumed
    return rt, acc, kw


async def _late(obj: dict, delay: float = 0.2):
    """意圖呼叫晚到：`delay` 秒後才回（程式優先等待已縮短 ⇒ 主模型提議先到）。"""
    async def _step(_kwargs):
        await asyncio.sleep(delay)
        return _intent(raw=json.dumps(obj, ensure_ascii=False))
    return _step


def _short_program_first(monkeypatch, intent_wait: float = 2.0) -> None:
    """程式優先等待縮短（意圖一定趕不上）；意圖等待上限另設（`_await_write_intent` 與寬回合等意圖同一條）。"""
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_S", 0.05)
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S", 0.05)
    monkeypatch.setattr(runtime_mod, "WRITE_INTENT_WAIT_MAX_S", intent_wait)


def _obj(action: str, data=_NO, **fields) -> dict:
    obj: dict = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()]}
    if data is not _NO:
        obj[WF.DATA_TEXTS_KEY] = data
    return obj


# ════════════════════════════════════════════════════════════════════
# FW11 (a)：開關 off ⇒ 三種回合與現行逐字相同；開關值不合 ⇒ 啟動失敗
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("value,expected", [(None, True), ("", True), ("  ", True), ("on", True), ("off", False),
                                            (" off ", False)])
def test_fw11_a_switch_values(value, expected):
    env = {} if value is None else {WIDE_ENV: value}
    assert WF.fill_data_text_wide_enabled_from_env(env) is expected


@pytest.mark.parametrize("bad", ["true", "ON", "0", "1", "no", "disabled"])
def test_fw11_a_bad_switch_value_fails_startup(monkeypatch, bad):
    """FW11 (a)：開關值不合 ⇒ `AgentRuntime` 建構（啟動）即 `ValueError`（另一個開關 off 也一樣）。"""
    with pytest.raises(ValueError):
        WF.fill_data_text_wide_enabled_from_env({WIDE_ENV: bad})
    for fill in ("on", "off"):
        monkeypatch.setenv(FILL_ENV, fill)
        monkeypatch.setenv(WIDE_ENV, bad)
        with pytest.raises(ValueError):
            RT(_Provider([]), None, None, None, None, stage="M1")


def test_fw11_a_switch_attribute_has_no_default_off_getattr():
    """§4.4：讀開關一律走屬性本身，⛔ 預設 off 的 getattr；只在 `_fill_data_text_on` 也 on 時生效。"""
    src = RUNTIME_PATH.read_text(encoding="utf-8")
    assert "getattr(self, \"_fill_data_text_wide_on\"" not in src
    assert "getattr(self, '_fill_data_text_wide_on'" not in src
    assert src.count("self._fill_data_text_wide_on") >= 2          # 正對照：建構時設、判定點讀


def test_fw11_a_compose_declares_both_switches():
    """§4.4（security-reviewer F1）：`docker-compose.prod.yml` 的 `rag-orchestrator.environment` 宣告兩個開關（空＝on）。"""
    text = (Path(__file__).resolve().parents[4] / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "AGENT_WRITE_DRAFT: ${AGENT_WRITE_DRAFT:-}" in text                       # 正對照
    assert "AGENT_FILL_DATA_TEXT: ${AGENT_FILL_DATA_TEXT:-}" in text
    assert "AGENT_FILL_DATA_TEXT_WIDE: ${AGENT_FILL_DATA_TEXT_WIDE:-}" in text


_OFF_COMBOS = [("on", "off"), ("off", "on"), ("off", "off")]


async def _run_turn(w: _World, message: str, intents, script=()):
    provider = _Provider(list(script), intents)
    res = await w.runtime(provider).run_turn(w.ident, message, w.state)
    (kw,) = provider.intent_calls
    return res, kw


def _off_shape(kw) -> None:
    assert WF.DATA_TEXTS_RULE not in _system(kw)
    assert WF.DATA_TEXTS_KEY not in _schema(kw)["properties"]
    assert _system(kw) in {WF.write_intent_system_prompt(enum_labels=b) for b in (True, False)}
    assert kw["response_format"] in [WF.write_intent_response_format(enum_labels=b) for b in (True, False)]


@pytest.mark.parametrize("fill,wide", _OFF_COMBOS)
async def test_fw11_a_build_main_off_three_turn_kinds_equal_pre_change(api, monkeypatch, fill, wide):
    """FW11 (a) 建構點一般：任一開關 off ⇒ 首句、卡後、多欄三種回合送出的系統句與 schema＝改前建構函式輸出（不帶本片
    參數）、沒有任何 `fill_` 標記，值照現行值閘併入（含「3q」）。"""
    async def _first():
        return _World()

    async def _after_card():
        return await _card(monkeypatch, MB)

    async def _multi():
        w0 = _World()
        _seed_draft(w0, MB, {"contract_ref": CONTRACT}, asked=["title", "total"])
        return w0

    cases = [
        (_first, "幫我開一張帳單，水電費 3q", lambda: [_fi(MB, data=["幫我開一張帳單，水電費"], title="水電費 3q")],
         lambda w: _fields(w).get("title") == "水電費 3q"),
        (_after_card, "金額改一下 2000 3q", lambda: [_fi(MB, data=["金額改一下"], total="2000")],
         lambda w: _fields(w).get("total") == "2000"),
        (_multi, "水電費 3q", lambda: [_fi(MB, data=["水電費"], title="水電費 3q")],
         lambda w: _fields(w).get("title") == "水電費 3q"),
    ]
    for make, msg, intents, check in cases:
        w = await make()
        monkeypatch.setenv(FILL_ENV, fill)
        monkeypatch.setenv(WIDE_ENV, wide)
        res, kw = await _run_turn(w, msg, intents(), script=[_out("主模型的回答")])
        _off_shape(kw)
        assert not _fill_marks(res), (msg, _v(res))
        assert check(w), (msg, _fields(w), res.answer)
        assert not res.answer.startswith(WF.CARD_UNCHANGED_TEXT), res.answer


@pytest.mark.parametrize("fill,wide", _OFF_COMBOS)
async def test_fw11_a_build_pick_rule_and_target_picked_off_equal_pre_change(api, monkeypatch, fill, wide):
    """FW11 (a) 建構點候選段 `pick_rule`／`target_picked`：任一開關 off ⇒ 系統句不含資料段規則、schema 不含 `data_texts`。"""
    for make, key in ((_listed_on, WF.PICK_ID_KEY), (_picked_on, WF.PICK_TARGET_KEY)):
        w, src = await make(monkeypatch)
        w.draft()["asked"] = []
        monkeypatch.setenv(FILL_ENV, fill)
        monkeypatch.setenv(WIDE_ENV, wide)
        res, kw = await _run_turn(w, "租金 12000", [_fi(src.action, data=["租金 12000"], target=[], rent="12000")],
                                  script=[_out("好的")])
        assert key in _schema(kw)["properties"]                         # 前提：走的是該建構點
        assert WF.DATA_TEXTS_RULE not in _system(kw) and WF.DATA_TEXTS_KEY not in _schema(kw)["properties"]
        assert not _fill_marks(res), _v(res)


@pytest.mark.parametrize("asked,draft_fields", [((), None), ((), {"contract_ref": CONTRACT, "title": "管理費",
                                                                 "total": "1000"}),
                                                (("title", "total"), {"contract_ref": CONTRACT})],
                         ids=["first", "after_card", "multi"])
async def test_fw11_a_wide_off_gate_equals_current_value_gate(api, monkeypatch, asked, draft_fields):
    """FW11 (a) 值閘：`AGENT_FILL_DATA_TEXT_WIDE=off` ⇒ 三種回合 `_fill_begin_intent_call` 回 `{}`、不設 `fill_wide`，
    本回合閘門原話＝現行值閘（同一回傳、同一組 violation），即使資料段不含該值。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    w = _World()
    draft = _draft(w, MB, draft_fields) if draft_fields is not None else None
    rt, acc, kw = _wdirect(w, draft, "水電費 3q", asked=asked, obj=_obj(MB, data=["金額改成"]),
                           card_live=draft is not None and not asked)
    assert kw == {} and acc.write_draft.fill_wide is False and acc.write_draft.fill_wide_data is None
    if draft is None:
        acc.write_draft.draft = _draft(w, MB, {"contract_ref": CONTRACT})
    await _fix4_gate_equals_off(w, rt, acc, FIX4_CASES)


@pytest.mark.parametrize("fill,wide", _OFF_COMBOS)
async def test_fw11_a_status_text_after_card_equals_pre_change(api, monkeypatch, fill, wide):
    """FW11 (a) 狀態句：卡後同值重述（「金額 1,000 謝謝」）、卡後新值不在資料段——任一開關 off ⇒ 前導句照改前
    （同值：`CARD_READ_SAME_LEAD`；新值：照併、⛔「這次的修改沒有套用…」）。"""
    w = await _card(monkeypatch, MB)
    monkeypatch.setenv(FILL_ENV, fill)
    monkeypatch.setenv(WIDE_ENV, wide)
    res, _kw = await _run_turn(w, "金額 1,000 謝謝", [_fi(MB, data=["金額 1,000"], total="1,000")],
                               script=[_out("主模型的回答")])
    assert res.answer.startswith(WF.CARD_READ_SAME_LEAD), res.answer
    w2 = await _card(monkeypatch, MB)
    monkeypatch.setenv(FILL_ENV, fill)
    monkeypatch.setenv(WIDE_ENV, wide)
    res2, _kw2 = await _run_turn(w2, "金額改一下 2000 3q", [_fi(MB, data=["金額改一下"], total="2000")],
                                 script=[_out("主模型的回答")])
    assert WF.CARD_UNCHANGED_TEXT not in res2.answer and res2.outcome["state"] == "confirm_pending", res2.answer
    assert str(_payload(w2, res2).get("total")) == "2000"


# ════════════════════════════════════════════════════════════════════
# 3 個建構點（§4.2）：寬回合帶 `data_text=True`、⛔ `asked_labels`
# ════════════════════════════════════════════════════════════════════
async def test_fw11_build_main_first_after_card_multi_carry_data_rule_without_answer_text(api, monkeypatch):
    """建構點 `_start_write_intent_call`（一般）：首句、卡後、多欄三種回合 ⇒ 系統句＝`write_intent_system_prompt(…,
    data_text=True)`（接 `WRITE_INTENT_PARTIAL_NOTE`、`DATA_TEXTS_RULE`＋`DATA_TEXTS_NAME_NOTE`），schema 根層必填
    `data_texts`、⛔ `answer_text`（不帶追問欄位標籤）。"""
    async def _first():
        return _World()

    async def _after_card():
        return await _card(monkeypatch, MB)

    async def _multi():
        w0 = _World()
        _seed_draft(w0, MB, {"contract_ref": CONTRACT}, asked=["title", "total"])
        return w0

    for make, msg in ((_first, "幫我開一張帳單，水電費 3q"), (_after_card, "金額改成 2000 3q"), (_multi, "水電費 3q")):
        w = await make()
        _res, kw = await _run_turn(w, msg, [_fi(MB, data=[])], script=[_out("主模型的回答")])
        assert _system(kw) in {WF.write_intent_system_prompt(enum_labels=b, data_text=True) for b in (True, False)}
        assert _system(kw).endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + R1_W2_NOTE_V1 + R1_W3_NOTE_V1)
        assert kw["response_format"] in [WF.write_intent_response_format(enum_labels=b, data_text=True)
                                         for b in (True, False)]
        assert _schema(kw)["required"][-1] == WF.DATA_TEXTS_KEY
        assert WF.ANSWER_TEXT_KEY not in _schema(kw)["properties"]


async def test_fw11_build_pick_rule_after_card_carries_data_and_pick_note(api, monkeypatch):
    """建構點候選段 `pick_rule=True`（未選定、`asked` 空＝卡後種類）：系統句接 `DATA_TEXTS_RULE`＋名稱說明＋候選清單說明；
    schema 必填 `data_texts`、⛔ `answer_text`；值不在資料段 ⇒ 拒收（證明讀了資料段）。"""
    w, src = await _listed_on(monkeypatch)
    w.draft()["asked"] = []
    res, kw = await _run_turn(w, "租金 12000", [_fi(src.action, data=["租金"], rent="12000")], script=[_out("好的")])
    assert WF.PICK_ID_KEY in _schema(kw)["properties"]                       # 前提：走的是 pick_rule 這一支
    assert WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 in _system(kw)
    assert WF.DATA_TEXTS_KEY in _schema(kw)["required"] and WF.ANSWER_TEXT_KEY not in _schema(kw)["properties"]
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert "rent" not in _fields(w)


async def test_fw11_build_target_picked_after_card_carries_data_rule(api, monkeypatch):
    """建構點候選段 `target_picked`（已選定、`asked` 空＝卡後種類）：系統句接 `DATA_TEXTS_RULE`、schema（指令版）必填
    `data_texts`、⛔ `answer_text`；資料段有效 ⇒ 照併。"""
    w, src = await _picked_on(monkeypatch)
    w.draft()["asked"] = []
    _bind_live_card(w, src.action)                   # 已選定不算等選的候選清單 ⇒ 卡後要有活的綁定卡（§4.1 (b)）
    res, kw = await _run_turn(w, "租金 12000", [_fi(src.action, data=["租金 12000"], target=[], rent="12000")],
                              script=[_out("好的")])
    assert WF.PICK_TARGET_KEY in _schema(kw)["properties"]                   # 前提：走的是 target_picked 這一支
    assert WF.pick_target_rule(src.picked) in _system(kw) and WF.DATA_TEXTS_RULE in _system(kw)
    assert WF.DATA_TEXTS_KEY in _schema(kw)["required"] and WF.ANSWER_TEXT_KEY not in _schema(kw)["properties"]
    assert WF.V_FILL_VALUE_OUTSIDE_DATA not in _v(res), _v(res)
    assert str(_fields(w).get("rent")) == "12000", (_fields(w), res.answer)


# ════════════════════════════════════════════════════════════════════
# FW11 (b)：單欄追問回合與現行逐字相同
# ════════════════════════════════════════════════════════════════════
async def test_fw11_b_single_field_followup_turn_unchanged_by_wide_switch(api, monkeypatch):
    """FW11 (b)：單欄追問回合（`len(asked) == 1`）不是寬回合——`AGENT_FILL_DATA_TEXT_WIDE` on／off 送出的系統句、schema、
    回話、草稿、標記逐字相同，且仍是上一片的形狀（追問欄位標籤、`answer_text`、只填答覆段）。上一片
    `test_fill_data_text_req.py` 全過另見完成條件 1。"""
    out = {}
    for wide in ("off", "on"):
        monkeypatch.setenv(WIDE_ENV, wide)
        w = _World()
        _seed_draft(w, REPAIR, {"estate_name": STUDENT_ESTATE}, asked=["description"])
        res, kw = await _run_turn(w, "冷氣不冷 3q", [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
        out[wide] = (_system(kw), json.dumps(kw["response_format"], ensure_ascii=False), res.answer, _fields(w),
                     list(_v(res)))
    assert out["on"] == out["off"]
    assert out["on"][0].endswith("\n" + WF.answer_text_rule(("問題描述",)))
    assert WF.V_FILL_ANSWER_SEGMENT in out["on"][4]
    assert WF.V_FILL_WIDE_DATA_UNKNOWN not in out["on"][4]


def test_fw11_b_single_field_direct_state_is_not_wide(api):
    """FW11 (b)／§4.1 互斥：單欄追問回合 ⇒ `fill_active`、⛔ `fill_wide`；寬回合 ⇒ `fill_wide`、⛔ `fill_active`。"""
    w = _World()
    _rt, acc, kw = _wdirect(w, _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE}), "冷氣不冷", asked=["description"])
    assert kw == {"data_text": True, "asked_labels": ("問題描述",)}
    assert acc.write_draft.fill_active is True and acc.write_draft.fill_wide is False
    for asked, draft, kind in (((), None, runtime_mod.FILL_WIDE_FIRST),
                               ((), _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE}), runtime_mod.FILL_WIDE_CARD),
                               (("estate_name", "description"), _draft(w, REPAIR, {}), runtime_mod.FILL_WIDE_MULTI)):
        _rt2, acc2, kw2 = _wdirect(w, draft, "冷氣不冷", asked=asked, card_live=kind == runtime_mod.FILL_WIDE_CARD)
        assert kw2 == {"data_text": True}, (asked, kw2)
        assert acc2.write_draft.fill_wide is True and acc2.write_draft.fill_active is False
        assert acc2.write_draft.fill_wide_kind == kind


def test_fw11_b_frozen_and_pick_button_turns_are_not_wide(api):
    """§4.1：凍結回合、`pick:` 按鈕回合照現行（⛔ 寬回合）。"""
    w = _World()
    rt = w.runtime(_Provider([]))
    for attr in ("frozen", "pick_button"):
        acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-x", start=0.0)
        acc.write_draft = _WriteDraftTurn(draft=_draft(w, MB, {}), owner="o", user_texts=["x"], asked=["title", "total"],
                                          had_draft=True, user_message="x")
        setattr(acc.write_draft, attr, True)
        assert rt._fill_begin_intent_call(acc) == {}
        assert acc.write_draft.fill_wide is False


# ════════════════════════════════════════════════════════════════════
# FW11 (c)～(h)：三種回合的值閘
# ════════════════════════════════════════════════════════════════════
async def test_fw11_c_first_sentence_name_with_thanks_rejected_other_fields_filled(api):
    """FW11 (c)：首句「我要新增一個物件叫和平小屋 3q，在台北市…」、資料段兩段（不含「3q」）、AI 把名稱回成「和平小屋 3q」
    ⇒ 名稱不含「3q」（被拒收、由程式追問），縣市、區域、地址照填。"""
    msg = "我要新增一個物件叫和平小屋 3q，在台北市大安區復興南路100號"
    w = _World()
    res = await w.turn(msg, intents=[_fi(EST, data=["我要新增一個物件叫和平小屋", "在台北市大安區復興南路100號"],
                                         title="和平小屋 3q", city="台北市", district="大安區",
                                         address="復興南路100號")])
    f = _fields(w)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert not any("3q" in str(v) for v in f.values()), f
    assert "title" not in f, f
    assert (f.get("city"), f.get("district"), f.get("address")) == ("台北市", "大安區", "復興南路100號"), f
    assert res.outcome["state"] == "clarifying" and _field(EST, "title").label in res.answer, res.answer
    assert "3q" not in res.answer


@pytest.mark.parametrize("data", [["17000"], ["租金改成17000"]])
async def test_fw11_d_after_card_rent_correction_with_thanks_applied(api, monkeypatch, data):
    """FW11 (d)：卡後「租金改成17000感謝您」、資料段 `["17000"]` 或 `["租金改成17000"]` ⇒ rent 改成 17000、卡重出。"""
    w = await _card(monkeypatch, CC)
    res = await w.turn("租金改成17000感謝您", intents=[_fi(CC, data=data, rent="17000")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("rent")) == "17000", _payload(w, res)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA not in _v(res) and WF.V_FILL_WIDE_DATA_UNKNOWN not in _v(res), _v(res)


async def test_fw11_e_after_card_empty_data_treated_unknown_rent_applied(api, monkeypatch):
    """FW11 (e)：卡後同句、資料段 `[]`、`fields` 有 rent ⇒ 當未知、照現行收值：rent 改成 17000、記 `fill_wide_data_unknown`。"""
    w = await _card(monkeypatch, CC)
    res = await w.turn("租金改成17000感謝您", intents=[_fi(CC, data=[], rent="17000")])
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in _v(res), _v(res)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA not in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("rent")) == "17000"


async def test_fw11_f_after_card_empty_data_empty_fields_proposal_merged(api, monkeypatch):
    """FW11 (f)：卡後「繳費期限改到 2026/12/20，辛苦你了」、資料段 `[]`、`fields` 空、主模型提議 `date_expire` ⇒ 當未知、
    照現行併（期限改成 2026/12/20、卡重出、記 `fill_wide_data_unknown`）。意圖晚到（提議先到 ⇒ 等意圖讀到 `[]`）。"""
    w = await _card(monkeypatch, MB)
    _short_program_first(monkeypatch)
    res = await w.turn("繳費期限改到 2026/12/20，辛苦你了",
                       intents=[await _late(_obj(MB, data=[]))],
                       script=[_proposal({"action": MB, **MB_GOOD, "date_expire": "2026-12-20"}), _out("主模型的回答")])
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in _v(res), _v(res)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA not in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("date_expire")).replace("-", "") == "20261220", _payload(w, res)


async def test_fw11_g_multi_field_answer_no_value_contains_thanks(api):
    """FW11 (g)：多欄追問「台北市大安區復興南路100號 住宅 3q」⇒ 縣市、區域、地址照填；AI 從「3q」衍生的樓層「3」不在資料段
    ⇒ 拒收；沒有任何值含「3q」。"""
    w = _World()
    _seed_draft(w, EST, {"title": "和平小屋"}, asked=["city", "district", "address"])
    res = await w.turn("台北市大安區復興南路100號 住宅 3q",
                       intents=[_fi(EST, data=["台北市大安區復興南路100號", "住宅"], city="台北市", district="大安區",
                                    address="復興南路100號", floor="3")])
    f = _fields(w) if w.draft() is not None else {}
    if res.trace.pending_id is not None:
        f = _payload(w, res)
    assert (f.get("city"), f.get("district"), f.get("address")) == ("台北市", "大安區", "復興南路100號"), f
    assert "floor" not in f, f
    assert not any("3q" in str(v) or str(v) == "3" for v in f.values()), f
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert WF.V_FILL_FILLED_FIELD_KEPT not in _v(res) and WF.V_FILL_REASK not in _v(res), _v(res)


async def test_fw11_h_two_values_one_outside_only_that_one_rejected(api, monkeypatch):
    """FW11 (h)：一句兩值（金額在資料段內、帳單項目不在）⇒ 只拒收帳單項目：金額改成 2000、帳單項目仍是「管理費」。"""
    w = await _card(monkeypatch, MB)
    res = await w.turn("金額改成 2000，帳單項目改水電費 3q",
                       intents=[_fi(MB, data=["金額改成 2000"], total="2000", title="水電費 3q")])
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending", res.answer
    p = _payload(w, res)
    assert str(p.get("total")) == "2000" and p.get("title") == "管理費", p


# ════════════════════════════════════════════════════════════════════
# FW11 (i)、(o)：主模型提議比意圖先到 ⇒ 等意圖一次再驗
# ════════════════════════════════════════════════════════════════════
REPAIR_MSG = f"{STUDENT_ESTATE} 浴室的燈不亮3q"
REPAIR_PROPOSAL = {"action": REPAIR, "estate_name": STUDENT_ESTATE, "description": "浴室的燈不亮3q"}


async def test_fw11_i_proposal_first_waits_intent_and_rejects_thanks(api, monkeypatch):
    """FW11 (i) 前半：意圖逾時（程式優先等不到）、主模型提議 description 含「3q」、意圖之後完成且資料段不含「3q」⇒
    提議值被拒收（`fill_value_outside_data`）；之後意圖照常由 `_write_draft_decide` 合併（description＝「浴室的燈不亮」）。"""
    _short_program_first(monkeypatch)
    w = _World()
    res = await w.turn(REPAIR_MSG, intents=[await _late(_obj(REPAIR, data=[STUDENT_ESTATE, "浴室的燈不亮"],
                                                             estate_name=STUDENT_ESTATE, description="浴室的燈不亮"))],
                       script=[_proposal(REPAIR_PROPOSAL), _out("主模型的回答")])
    v = _v(res)
    assert WF.V_PROGRAM_FIRST_WAIT_TIMEOUT in v and WF.V_WRITE_PROPOSAL in v, v       # 前提：提議先到
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in v and WF.V_FILL_WIDE_DATA_UNKNOWN not in v, v
    f = _payload(w, res) if res.trace.pending_id is not None else _fields(w)
    assert f.get("description") == "浴室的燈不亮", (f, res.answer)
    assert "3q" not in res.answer


async def test_fw11_i_intent_never_completes_proposal_merged_as_current(api, monkeypatch):
    """FW11 (i) 後半：意圖到上限仍未完成 ⇒ 資料段未知、提議照現行併（description 含「3q」）、記 `fill_wide_data_unknown`。"""
    _short_program_first(monkeypatch, intent_wait=0.05)
    w = _World()
    res = await w.turn(REPAIR_MSG, intents=[_hang], script=[_proposal(REPAIR_PROPOSAL), _out("主模型的回答")])
    v = _v(res)
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in v and WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
    f = _payload(w, res) if res.trace.pending_id is not None else _fields(w)
    assert f.get("description") == "浴室的燈不亮3q", (f, res.answer)


async def test_fw11_o_proposal_first_marks_once_and_intent_merged_by_decide(api, monkeypatch):
    """FW11 (o)：提議先到、等意圖——`write_intent_call` 等收尾標記每回合各只一次、⛔ `write_intent_call_failed`；意圖照常由
    `_write_draft_decide` 合併（意圖多帶的急迫程度「緊急」提議裡沒有，仍進了卡）。"""
    _short_program_first(monkeypatch)
    w = _World()
    calls = []
    real = AgentRuntime._await_write_intent

    async def _spy(self, acc):
        calls.append(acc.write_draft.intent_consumed)
        return await real(self, acc)
    monkeypatch.setattr(AgentRuntime, "_await_write_intent", _spy)
    res = await w.turn(REPAIR_MSG, intents=[await _late(_obj(REPAIR, data=[STUDENT_ESTATE, "浴室的燈不亮"],
                                                             estate_name=STUDENT_ESTATE, description="浴室的燈不亮",
                                                             emergency_status="緊急"))],
                       script=[_proposal(REPAIR_PROPOSAL), _out("主模型的回答")])
    v = _v(res)
    assert calls == [True], calls                                    # 只由 `_write_draft_decide` 取用一次
    for mark in (WF.V_CALL, WF.V_PROGRAM_FIRST_WAIT_TIMEOUT, WF.V_FILL_VALUE_OUTSIDE_DATA):
        assert v.count(mark) == 1, (mark, v)
    for mark in (WF.V_CALL_FAILED, WF.V_UNPARSED, WF.V_AMBIGUOUS, WF.V_OUT_OF_DOMAIN):
        assert mark not in v, (mark, v)
    f = _payload(w, res) if res.trace.pending_id is not None else _fields(w)
    assert f.get("description") == "浴室的燈不亮" and str(f.get("emergency_status")) == "2", (f, res.answer)


async def test_fw11_o_failed_intent_marks_once_and_data_unknown(api, monkeypatch):
    """FW11 (o)：意圖 task 例外 ⇒ 資料段未知（提議照現行併、記 `fill_wide_data_unknown`），`write_intent_call_failed` 只一次。"""
    _short_program_first(monkeypatch)
    w = _World()

    async def _late_boom(_kwargs):
        await asyncio.sleep(0.2)
        raise RuntimeError("bedrock 500")
    res = await w.turn(REPAIR_MSG, intents=[_late_boom], script=[_proposal(REPAIR_PROPOSAL), _out("主模型的回答")])
    v = _v(res)
    assert v.count(WF.V_CALL_FAILED) == 1, v
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in v and WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
    f = _payload(w, res) if res.trace.pending_id is not None else _fields(w)
    assert f.get("description") == "浴室的燈不亮3q", f


class _Call:
    """直接測 `_fill_wide_await_data` 用的意圖呼叫替身（只有 `_WriteIntentCall` 被讀的屬性）。"""

    def __init__(self, task):
        self.task = task
        self.settled = False
        self.label_only = False


def _wide_acc(w: _World, rt, message: str, *, start: float = 0.0):
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-wait", start=start)
    acc.write_draft = _WriteDraftTurn(draft=None, owner="o", user_texts=[message], user_message=message)
    assert rt._fill_begin_intent_call(acc) == {"data_text": True}
    return acc


async def test_fw11_o_deadline_exhausted_wait_cap_zero_no_exception(api):
    """FW11 (o)：剩餘期限已不足 ⇒ 等待上限為 0（`max(0.0, …)`）、不丟例外、資料段未知；⛔ 記任何標記、⛔ 設
    `intent_consumed`；每回合只等一次（第二次呼叫不再等，即使 task 已完成也不讀）。"""
    w = _World()
    rt = w.runtime(_Provider([]))
    msg = "金額改成 2000 3q"
    acc = _wide_acc(w, rt, msg, start=rt._clock() - rt.budget.deadline_s - 100.0)
    task = asyncio.create_task(asyncio.sleep(0.3, result=_intent(raw=json.dumps(_obj(MB, data=["金額改成 2000"])))))
    acc.write_intent_call = _Call(task)
    t0 = asyncio.get_running_loop().time()
    await rt._fill_wide_await_data(acc)
    assert asyncio.get_running_loop().time() - t0 < 0.2
    assert acc.write_draft.fill_wide_data is None and acc.write_draft.fill_wide_waited is True
    assert acc.violations == [] and acc.write_draft.intent_consumed is False
    await task
    await rt._fill_wide_await_data(acc)                              # 鎖住：⛔ 重等、⛔ 重讀
    assert acc.write_draft.fill_wide_data is None and acc.violations == []


@pytest.mark.parametrize("kind", ["exception", "retry_failed", "cancelled", "ok"])
async def test_fw11_o_peek_failed_or_retry_failed_means_unknown(api, kind):
    """FW11 (o)：意圖 task 例外、重送失敗（`_RetriedIntentResponse.failed`）、被取消 ⇒ 資料段未知；正對照 ok ⇒ 讀到。
    皆 ⛔ 記標記、⛔ 寫意圖相關欄位。"""
    w = _World()
    rt = w.runtime(_Provider([]))
    msg = "金額改成 2000 3q"
    acc = _wide_acc(w, rt, msg)
    good = _intent(raw=json.dumps(_obj(MB, data=["金額改成 2000"]), ensure_ascii=False))

    async def _make():
        if kind == "exception":
            raise RuntimeError("bedrock 500")
        if kind == "retry_failed":
            return runtime_mod._RetriedIntentResponse(good, good, failed=True)
        if kind == "cancelled":
            await asyncio.sleep(30)
        return good
    task = asyncio.create_task(_make())
    if kind == "cancelled":
        await asyncio.sleep(0)
        task.cancel()
    await asyncio.sleep(0.01)
    acc.write_intent_call = _Call(task)
    await rt._fill_wide_await_data(acc)
    wd = acc.write_draft
    assert wd.fill_wide_data == (["金額改成 2000"] if kind == "ok" else None), wd.fill_wide_data
    assert acc.violations == [] and wd.intent_consumed is False
    assert (wd.intent_parsed, wd.modifies_submitted, wd.intent_pick_id, wd.intent_target, wd.record_rechoice) == (
        False, False, None, None, None)


# ════════════════════════════════════════════════════════════════════
# FW11 (j)：意圖例外、無法解析、ambiguous、值域外、鍵缺、null、型別不對 ⇒ 照現行併
# ════════════════════════════════════════════════════════════════════
_J_PARSED = {
    "key_missing": _obj(MB, total="2000"),
    "null": _obj(MB, data=None, total="2000"),
    "wrong_type": _obj(MB, data="金額改成", total="2000"),
    "number_items": _obj(MB, data=[2000], total="2000"),
    "cuts_digits": _obj(MB, data=["金額改成 200"], total="2000"),
}


@pytest.mark.parametrize("kind", sorted(_J_PARSED))
async def test_fw11_j_bad_data_key_merges_as_current(api, monkeypatch, kind):
    """FW11 (j) 鍵缺、`null`、型別不對（非陣列、項目非字串）、段切斷數字 ⇒ 資料段未知、照現行併（金額 2000、卡重出）。"""
    w = await _card(monkeypatch, MB)
    res = await w.turn("金額改成 2000 3q", intents=[_intent(raw=json.dumps(_J_PARSED[kind], ensure_ascii=False))])
    v = _v(res)
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in v and WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("total")) == "2000"


_J_FAILED = {
    "exception": None,
    "unparsed": "這不是 JSON",
    "ambiguous": (json.dumps(_obj(MB, data=["金額改成"], total="2000"), ensure_ascii=False) + " "
                  + json.dumps(_obj(REPAIR, data=["金額改成"]), ensure_ascii=False)),
    "out_of_domain": json.dumps({"action": MB, "fields": [{"key": "total", "value": "2000"},
                                                          {"key": "no_such_key", "value": "x"}],
                                 WF.DATA_TEXTS_KEY: ["金額改成"]}, ensure_ascii=False),
}


@pytest.mark.parametrize("kind", sorted(_J_FAILED))
async def test_fw11_j_intent_failed_proposal_merges_as_current(api, monkeypatch, kind):
    """FW11 (j) 意圖例外、無法解析、ambiguous、值域外 ⇒ 資料段未知（就算回應裡有不含 2000 的資料段也不用）：主模型提議的
    新金額照現行併（2000、卡重出）、記 `fill_wide_data_unknown`、⛔ `fill_value_outside_data`。"""
    w = await _card(monkeypatch, MB)

    def _bad(_kwargs):
        if _J_FAILED[kind] is None:
            raise RuntimeError("bedrock 500")
        return _J_FAILED[kind]
    res = await w.turn("金額改成 2000 3q", intents=[_bad],
                       script=[_proposal({"action": MB, **MB_GOOD, "total": 2000}), _out("主模型的回答")])
    v = _v(res)
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in v and WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("total")) == "2000"


# ════════════════════════════════════════════════════════════════════
# FW11 (k)、(p)：卡後回話
# ════════════════════════════════════════════════════════════════════
async def test_fw11_k_after_card_rejected_correction_does_not_say_press_confirm(api, monkeypatch):
    """FW11 (k)：卡後更正被 (iii) 拒收（新金額不在資料段）、綁定卡仍有效 ⇒ 回話是 `CARD_UNCHANGED_TEXT`，⛔「卡片還在，請按
    確認。」、⛔ `CARD_READ_SAME_LEAD`；卡上金額不變。"""
    w = await _card(monkeypatch, MB)
    res = await w.turn("金額改一下 2000 3q", intents=[_fi(MB, data=["金額改一下"], total="2000")],
                       script=[_out("主模型的回答")])
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert res.answer.startswith(WF.CARD_UNCHANGED_TEXT), res.answer
    assert WF.CARD_STILL_VALID_TEXT not in res.answer and not res.answer.startswith(WF.CARD_READ_SAME_LEAD)
    assert _fields(w).get("total") == "1000", _fields(w)


async def test_fw11_k_after_card_unknown_data_new_value_not_flagged(api, monkeypatch):
    """FW11 (k) 對照（§4.3 第 8 點「資料段未知不設」）：資料段未知 ⇒ 新值照現行併、卡重出、⛔「這次的修改沒有套用…」。"""
    w = await _card(monkeypatch, MB)
    res = await w.turn("金額改成 2000 3q", intents=[_fi(MB, total="2000")])
    assert WF.V_FILL_WIDE_DATA_UNKNOWN in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending" and WF.CARD_UNCHANGED_TEXT not in res.answer, res.answer
    assert str(_payload(w, res).get("total")) == "2000"


async def test_fw11_p_partial_apply_reissued_card_names_rejected_label_without_value(api, monkeypatch):
    """FW11 (p)：卡後「租金改成17000、押金改 20000 ty」、資料段只含租金段 ⇒ 租金改、卡重出；回話含點名「押金」的程式固定句、
    ⛔ 含押金的新值；押金仍是原值。"""
    w = await _card(monkeypatch, CC)
    res = await w.turn("租金改成17000、押金改 20000 ty",
                       intents=[_fi(CC, data=["租金改成17000"], rent="17000", deposit_amount="20000")])
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending", res.answer
    p = _payload(w, res)
    assert str(p.get("rent")) == "17000" and str(p.get("deposit_amount")) == "24000", p
    label = _field(CC, "deposit_amount").label
    assert label == "押金"
    notice = WF.fill_wide_not_applied_text([label])
    assert notice is not None and "押金" in notice and "20000" not in notice and "20,000" not in notice
    first_line = res.answer.split("\n", 1)[0]
    assert first_line == notice, res.answer
    assert "20000" not in res.answer and "20,000" not in res.answer, res.answer
    dialog = (w.state.get("agent") or {}).get("dialog") or []
    assert notice not in json.dumps(dialog, ensure_ascii=False)               # 卡外前導句 ⛔ 進歷史（DSP-038）


async def test_fw11_p_partial_apply_card_differs_branch_appends_notice(api, monkeypatch):
    """FW11 (p) `CARD_DIFFERS_TEXT` 分支（security-reviewer F3）：綁定卡 live、草稿≠卡、本回合沒重出卡、寬回合卡後有欄位被拒收
    ⇒ 前導句＝`CARD_DIFFERS_TEXT`＋換行＋點名標籤的固定句；沒有拒收 ⇒ 與改前逐字相同。"""
    w = _World()
    rt = w.runtime(_Provider([]))
    entry = {"action": MB, runtime_mod.PENDING_DRAFT_PAYLOAD_KEY: {"title": "管理費"}}

    async def _unchanged(*_a, **_k):
        return None

    async def _live(*_a, **_k):
        return "pid-1", entry, "live"
    monkeypatch.setattr(rt, "_write_proposal_card_unchanged", _unchanged)
    monkeypatch.setattr(rt, "_session_live_card", _live)
    monkeypatch.setattr(rt, "_write_draft_bound_card_text", lambda *_a, **_k: "CARD")
    monkeypatch.setattr(runtime_mod, "_pending_draft_payload", lambda e: e[runtime_mod.PENDING_DRAFT_PAYLOAD_KEY])
    for rejected, expect in ((False, WF.CARD_DIFFERS_TEXT),
                             (True, WF.CARD_DIFFERS_TEXT + "\n" + WF.fill_wide_not_applied_text(["金額"]))):
        _rt, acc, _kw = _wdirect(w, _draft(w, MB, {"contract_ref": CONTRACT, "title": "水電費", "total": "1000"}),
                                 "x", asked=(), card_live=True)
        if rejected:
            acc.write_draft.fill_wide_rejected[(MB, "total")] = _field(MB, "total").label
        state = await rt._write_reply_state(acc, w.ident, {})
        assert state["branch"] == WF.WRITE_REPLY_STATE_CARD_DIFFERS and state["lead"] == expect, state


def test_fw11_p_notice_template_is_label_only():
    """§4.3 第 8 點：固定句只帶表單標籤（依序、去重）；空、非字串 ⇒ `None`。"""
    assert WF.fill_wide_not_applied_text([]) is None
    assert WF.fill_wide_not_applied_text(["押金", 3]) is None
    assert WF.fill_wide_not_applied_text(["押金", "租金", "押金"]) == WF.FILL_WIDE_NOT_APPLIED_TEMPLATE.format(
        labels="押金、租金")


# ════════════════════════════════════════════════════════════════════
# FW11 (l)：候選綁定欄只過 (i)
# ════════════════════════════════════════════════════════════════════
async def test_fw11_l_bound_candidate_field_only_passes_i(api, monkeypatch):
    """FW11 (l)：未選定、仍綁定的候選集那一欄（物件），意圖帶前句才講過的名稱（不在本句資料段、在客人原話）⇒ 例外放行
    （`fill_bound_field_exempt`），日期租金照併；同句別欄不受影響。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO
    w = _World()
    await _p32_listed(w)
    assert len(w.draft()["asked"]) != 1, w.draft()["asked"]                  # 前提：寬回合（非單欄追問）
    res = await _p32_turn(w, RC4_MSG, RC4_SEGS, estate_name=_CC_TYPO, **RC4_VALUES)
    v = _v(res)
    assert WF.V_FILL_BOUND_FIELD_EXEMPT in v, v
    assert _fields(w).get("estate_name") == _CC_TYPO and str(_fields(w).get("rent")) == "12000", _fields(w)


async def test_fw11_l_bound_field_value_not_in_user_words_still_blocked_by_i(api):
    """FW11 (l) 對照：綁定欄的值不在任何客人原話 ⇒ 照舊被 (i) 擋、⛔ 例外。"""
    w = _World()
    await _p32_listed(w)
    res = await _p32_turn(w, RC4_MSG, RC4_SEGS, estate_name="海景豪宅", **RC4_VALUES)
    assert WF.V_FILL_BOUND_FIELD_EXEMPT not in _v(res), _v(res)
    assert _fields(w).get("estate_name") != "海景豪宅", _fields(w)


# ════════════════════════════════════════════════════════════════════
# FW11 (m)：資料段只活在本回合
# ════════════════════════════════════════════════════════════════════
async def test_fw11_m_data_strings_do_not_leave_the_turn(api, monkeypatch, caplog):
    """FW11 (m)：資料段字串不出現在 `agent_state`（對話紀錄本來就存的原句除外）、草稿、trace、決策快照、日誌（caplog）與
    violation 字串；回合內欄位名不落地；`repr` 回合狀態也不帶寬回合欄位。"""
    captured: list = []
    real = usage_metering.set_agent_decision
    monkeypatch.setattr(usage_metering, "set_agent_decision", lambda d: (captured.append(copy.deepcopy(d)), real(d)))
    seen_wd: list = []
    real_verdict = AgentRuntime._fill_wide_verdict

    def _spy(self, acc, *a, **k):
        seen_wd.append(acc.write_draft)
        return real_verdict(self, acc, *a, **k)
    monkeypatch.setattr(AgentRuntime, "_fill_wide_verdict", _spy)
    caplog.set_level(logging.DEBUG)
    seg = "租金改成17000"
    w = await _card(monkeypatch, CC)
    res = await w.turn("租金改成17000、押金改 20000 ty",
                       intents=[_fi(CC, data=[seg], rent="17000", deposit_amount="20000")])
    assert res.outcome["state"] == "confirm_pending" and seen_wd, res.answer
    state = copy.deepcopy(w.state)
    state.get("agent", {}).pop("dialog", None)
    blobs = {
        "agent_state": json.dumps(state, ensure_ascii=False, default=str),
        "trace": json.dumps(dataclasses.asdict(res.trace), ensure_ascii=False, default=str),
        "decision_snapshot": json.dumps(captured, ensure_ascii=False, default=str),
        "log": caplog.text,
        "violations": json.dumps(_v(res), ensure_ascii=False),
    }
    assert captured, "沒有落地任何 decision_snapshot——這條斷言就什麼都沒證明"
    for where, blob in blobs.items():
        assert seg not in blob, where
        for key in (WF.DATA_TEXTS_KEY, "fill_wide_data", "fill_wide_rejected", "fill_wide_kind", "fill_wide_waited"):
            assert f'"{key}"' not in blob and f"'{key}'" not in blob, (where, key)
    assert "17000" in blobs["agent_state"]                           # 正對照：掃描的是有內容的狀態
    wd = seen_wd[-1]
    assert wd.fill_wide_data == [seg]                                # 正對照：回合內確實讀到資料段
    text = repr(wd)
    assert "fill_wide" not in text and repr([seg]) not in text, text
    fill_marks = {m for m in _v(res) if str(m).startswith("fill_")}
    assert fill_marks <= {WF.V_FILL_WIDE_DATA_UNKNOWN, WF.V_FILL_VALUE_OUTSIDE_DATA, WF.V_FILL_BOUND_FIELD_EXEMPT,
                          WF.V_FILL_SEGMENT_NOT_IN_MESSAGE}, fill_marks


def test_fw11_m_new_constants_are_fixed_strings_and_fields_hidden_from_repr():
    """§4.3 第 10 點：新標記固定字串（⛔ 帶值、⛔ 格式化）；新回合內欄位 `repr=False`。"""
    value = WF.V_FILL_WIDE_DATA_UNKNOWN
    assert value == "fill_wide_data_unknown" and value.isascii() and "{" not in value
    for line in RUNTIME_PATH.read_text(encoding="utf-8").splitlines():
        if "V_FILL_" in line and ("f\"" in line or ".format(" in line):
            raise AssertionError(line)
    hidden = {f.name for f in dataclasses.fields(_WriteDraftTurn) if not f.repr}
    assert {"fill_wide", "fill_wide_kind", "fill_wide_data", "fill_wide_waited", "fill_wide_rejected"} <= hidden


def test_fw11_m_wait_path_catches_exceptions_without_logging_text():
    """§4.3 第 10 點：新判讀路徑接住例外且 ⛔ 記 `str(exc)`（不呼叫 logger、不格式化例外）。"""
    fn = _fn(_tree(), "_fill_wide_await_data")
    src = _code(fn)
    handlers = [h for h in ast.walk(fn) if isinstance(h, ast.ExceptHandler)]
    broad = [h for h in handlers if isinstance(h.type, ast.Name) and h.type.id == "Exception"]
    assert len(broad) == 1 and broad[0].name is None, ast.unparse(fn)      # ⛔ `except Exception as exc`
    assert "logger" not in src and "str(" not in src and "repr(" not in src, src


# ════════════════════════════════════════════════════════════════════
# FW11 (n)：回合中草稿換成另一動作
# ════════════════════════════════════════════════════════════════════
async def test_fw11_n_draft_switched_mid_turn_still_wide_no_b4_b5(api):
    """FW11 (n)：多欄追問帳單中、客人改講報修（意圖換動作 ⇒ 新草稿）⇒ 寬回合做法照樣套在新草稿：description 含「3q」不在
    資料段 ⇒ 拒收、物件照收；⛔ 單欄追問的 B4（答覆段）、B5（不覆寫已填欄）、B6（重問）標記。"""
    w = _World()
    _seed_draft(w, MB, {"contract_ref": CONTRACT}, asked=["title", "total"])
    msg = f"另外幫我報修 {STUDENT_ESTATE} 冷氣不冷3q"
    res = await w.turn(msg, intents=[_fi(REPAIR, data=[f"另外幫我報修 {STUDENT_ESTATE} 冷氣不冷"],
                                         estate_name=STUDENT_ESTATE, description="冷氣不冷3q")],
                       script=[_out("主模型的回答")])
    v = _v(res)
    d = w.draft()
    assert d is not None and d["action"] == REPAIR, (d, res.answer)
    assert _fields(w).get("estate_name") == STUDENT_ESTATE and "description" not in _fields(w), _fields(w)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in v, v
    for mark in (WF.V_FILL_ANSWER_SEGMENT, WF.V_FILL_FILLED_FIELD_KEPT, WF.V_FILL_REASK, WF.V_FILL_DATA_TEXT_UNKNOWN):
        assert mark not in v, (mark, v)


# ════════════════════════════════════════════════════════════════════
# 結構（§4.1、§4.3 第 4 點實作約束、DSP-091）
# ════════════════════════════════════════════════════════════════════
def _tree():
    return ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))


def _fn(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def _code(fn) -> str:
    """函式本體原始碼（去掉 docstring；docstring 會描述 ⛔ 做的事，不算程式）。"""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return "\n".join(ast.unparse(s) for s in body)


def test_fw11_struct_wide_state_only_set_where_the_intent_call_is_built():
    """§4.1：`fill_wide` 只在 `_fill_wide_begin` 設、`_fill_wide_begin` 只被 `_fill_begin_intent_call` 呼叫（後者只被
    `_start_write_intent_call` 呼叫，上一片已驗）⇒ 文件、`pick:` 回合不會是寬回合。"""
    tree = _tree()
    callers = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               for s in ast.walk(n) if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute)
               and s.func.attr == "_fill_wide_begin"]
    assert callers == ["_fill_begin_intent_call"], callers
    setters = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Attribute) and t.attr in ("fill_wide", "fill_wide_kind") for t in n.targets)]
    assert len(setters) == 2 and all(any(s is x for x in ast.walk(_fn(tree, "_fill_wide_begin"))) for s in setters)


def test_fw11_struct_wait_has_no_side_effects_and_own_flag():
    """§4.3 第 4 點：等意圖那一支 ⛔ 記 violation、⛔ 寫意圖相關欄位、⛔ 設 `intent_consumed`、⛔ 讀 `_write_intent_calls`、
    ⛔ 碰 `fill_proposal_first`；上限式含 `max(0.0, min(WRITE_INTENT_WAIT_MAX_S, …))`；判讀與 `_await_write_intent` 共用
    `_peek_write_intent`；只在 `_write_proposal_merge` 逐值迴圈之前呼叫。"""
    tree = _tree()
    src = _code(_fn(tree, "_fill_wide_await_data"))
    for banned in ("violations", "intent_consumed =", "modifies_submitted", "intent_pick_id", "intent_parsed",
                   "intent_target", "record_rechoice", "_write_intent_calls", "fill_proposal_first", "_fill_mark"):
        assert banned not in src, banned
    assert "max(0.0, min(WRITE_INTENT_WAIT_MAX_S, remaining - WRITE_DRAFT_PROGRAM_MIN_REMAINING_S))" in src
    assert "acc.write_intent_call" in src and "_peek_write_intent(call)" in src
    assert "_peek_write_intent(call)" in ast.unparse(_fn(tree, "_await_write_intent"))
    peek = _code(_fn(tree, "_peek_write_intent"))
    assert "violations" not in peek and "write_draft" not in peek
    callers = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               for s in ast.walk(n) if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute)
               and s.func.attr == "_fill_wide_await_data"]
    assert callers == ["_write_proposal_merge"], callers
    merge = _fn(tree, "_write_proposal_merge")
    loop = next(s for s in merge.body if isinstance(s, ast.For))
    wait = next(s for s in merge.body if isinstance(s, ast.Expr) and "_fill_wide_await_data" in ast.unparse(s))
    assert merge.body.index(wait) < merge.body.index(loop)


def test_fw11_struct_value_gate_only_in_turn_gate():
    """§4.3：值閘全在 `_write_draft_turn_gate`（`_write_draft_gate_value(` 只在它裡面被呼叫；寬回合分支也在它裡面）。"""
    tree = _tree()
    owners = sorted({n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     for s in ast.walk(n) if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute)
                     and s.func.attr == "_write_draft_gate_value"})
    assert owners == ["_write_draft_turn_gate"], owners
    gate = ast.unparse(_fn(tree, "_write_draft_turn_gate"))
    assert "if wd.fill_wide:" in gate and gate.index("if wd.fill_wide:") < gate.index("if not wd.fill_active:")


_WIDE_FUNCS = {"_fill_wide_begin", "_fill_wide_read_data", "_fill_wide_await_data", "_fill_wide_not_applied_labels",
               "_fill_wide_notice", "_fill_wide_slot", "_fill_wide_precheck", "_fill_wide_verdict", "_fill_data_spans",
               "_peek_write_intent", "_write_draft_turn_gate", "_fill_value_not_applied"}


def _has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)


def test_fw11_dsp091_new_code_has_no_chinese_keyword_matching():
    """DSP-091（FW-R8）：本片新程式 ⛔ 以道謝或寒暄的詞表判斷——新函式內沒有任何含中文的字串常數（docstring 除外）。"""
    tree = _tree()
    fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in _WIDE_FUNCS]
    assert {f.name for f in fns} == _WIDE_FUNCS
    for fn in fns:
        doc = ast.get_docstring(fn, clean=False)
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value != doc:
                assert not _has_cjk(node.value), (fn.name, node.value)
    wf_src = textwrap.dedent(Path(WF.__file__).read_text(encoding="utf-8"))
    fn = _fn(ast.parse(wf_src), "fill_wide_not_applied_text")
    assert "3q" not in ast.unparse(fn) and "謝" not in ast.unparse(fn)


# ════════════════════════════════════════════════════════════════════
# 修復輪 1（計畫 §11；業主 2026-10-28「三項都修，照排程重跑」）
# R1-W1：寬回合、前一句講過的值（不在最新一句）⇒ 照 (i) 收、記 `fill_wide_carry_over`；最新一句裡的非資料值照舊被 (iii) 擋
# R1-W2／R1-W3：`data_text=True` 系統句接兩句共用說明；`data_text=False` 逐字不變
# 測試句由本檔自寫（⛔ X3～X5 輸入原句）。
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-r1 的 v1 逐字（測試端獨立寫一份，⛔ 引用 `WF.FIELD_NOT_IN_FORM_NOTE`／`WF.ANOTHER_RECORD_NOTE` 自證）。
R1_W2_NOTE_V1 = ("（使用者講到的欄位如果不在這個動作列出的鍵裡，那個值就不列進 fields，⛔ 改填到別的鍵，意思相近的鍵也一樣；"
                 "例如這個動作沒有「聯絡時段」這一欄，使用者說「聯絡時段寫平日晚上」，就不要把「平日晚上」填進任何一個鍵。）")
R1_W3_NOTE_V1 = ("（使用者要另外再建一筆（另一份、另一間、再開一張），是新的請求，⛔ 拿它來改進行中這一筆的欄位；"
                 "例如進行中這一筆是本月的帳單，使用者說「下個月的也先開一張」，就不要把這一筆的欄位改成下個月的。）")
R1_PRIOR = "金額是 2000"
R1_MSG = "帳單項目是水電費 3q"
R1_SEGS = ["帳單項目是水電費"]


def test_r1_w1_carry_over_mark_is_fixed_string_and_exported():
    """R1-W1：新標記固定字串（⛔ 帶值、⛔ 格式化），列在 `write_forms` 匯出清單（比照 `V_FILL_WIDE_DATA_UNKNOWN`）。"""
    value = WF.V_FILL_WIDE_CARRY_OVER
    assert value == "fill_wide_carry_over" and value.isascii() and "{" not in value
    assert "V_FILL_WIDE_CARRY_OVER" in WF.__all__ and "V_FILL_WIDE_DATA_UNKNOWN" in WF.__all__     # 正對照


@pytest.mark.parametrize("asked,draft_fields", [((), None), ((), {"contract_ref": CONTRACT, "title": "管理費"}),
                                                (("title", "total"), {"contract_ref": CONTRACT})],
                         ids=["first", "after_card", "multi"])
async def test_r1_w1_direct_prior_value_carried_latest_non_data_still_rejected(api, asked, draft_fields):
    """R1-W1（三種寬回合，直接打 `_write_draft_turn_gate`）：前一句「金額是 2000」、最新一句「帳單項目是水電費 3q」、資料段
    只有「帳單項目是水電費」、草稿金額欄空 ⇒ 金額 2000（只在前一句）照 (i) 收、記 `fill_wide_carry_over`、⛔ `fill_value_outside_data`；
    帳單項目「水電費 3q」（在最新一句、不在資料段）照舊拒收、記 `fill_value_outside_data`。"""
    w = _World()
    draft = _draft(w, MB, draft_fields) if draft_fields is not None else None
    rt, acc, kw = _wdirect(w, draft, R1_MSG, asked=asked, obj=_obj(MB, data=R1_SEGS), prior=(R1_PRIOR,),
                           card_live=draft is not None and not asked)
    assert kw == {"data_text": True} and acc.write_draft.fill_wide_data == R1_SEGS        # 前提：寬回合、資料段讀到
    got, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "2000", from_intent=True)
    assert (got, dropped) == ("2000", False)
    assert WF.V_FILL_WIDE_CARRY_OVER in acc.violations and WF.V_FILL_VALUE_OUTSIDE_DATA not in acc.violations, \
        acc.violations
    got2, dropped2 = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "title"), "水電費 3q", from_intent=True)
    assert (got2, dropped2) == (None, False)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in acc.violations, acc.violations
    got3, _d3 = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "title"), "水電費", from_intent=True)
    assert got3 == "水電費"                                                               # 正對照：資料段內照收
    assert all("2000" not in str(m) and "水電費" not in str(m) for m in acc.violations), acc.violations


async def test_r1_w1_direct_value_in_no_user_words_still_blocked_by_i(api):
    """R1-W1 對照：值不在任何客人原話 ⇒ 照舊被 (i) 擋（⛔ `fill_wide_carry_over`）——放行的只有 (i) 已過的值。"""
    w = _World()
    rt, acc, _kw = _wdirect(w, _draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費", "total": "1000"}), R1_MSG,
                            obj=_obj(MB, data=R1_SEGS), prior=(R1_PRIOR,), card_live=True)
    got, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "3500", from_intent=True)
    assert (got, dropped) == (None, True)
    assert WF.V_FILL_WIDE_CARRY_OVER not in acc.violations and WF.V_NOT_IN_USER_WORDS in acc.violations


async def test_r1_w1_direct_non_string_user_message_equals_i(api):
    """R1-W1：`user_message` 非字串 ⇒ 當空字串（空欄、最新一句比不到 ⇒ 照 (i) 收），結果＝改前（只過 (i)）。"""
    w = _World()
    rt, acc, _kw = _wdirect(w, _draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費"}), R1_MSG,
                            obj=_obj(MB, data=R1_SEGS), prior=(R1_PRIOR,), card_live=True)
    acc.write_draft.user_message = None
    got, _dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "2000", from_intent=True)
    assert got == "2000" and WF.V_FILL_WIDE_CARRY_OVER in acc.violations


async def test_r1_w1_single_field_followup_prior_value_unchanged(api, monkeypatch):
    """R1-W1：單欄追問回合（`len(asked) == 1`，上一片 RC2）不變——前一句講過的問題描述「冷氣不冷」不在本句資料段 ⇒ 照舊
    拒收（`fill_value_outside_data`）、⛔ `fill_wide_carry_over`；寬回合開關 on／off 結果相同。"""
    out = {}
    for wide in ("off", "on"):
        monkeypatch.setenv(WIDE_ENV, wide)
        w = _World()
        obj = _obj(REPAIR, data=["浴室漏水"])
        obj[WF.ANSWER_TEXT_KEY] = "浴室漏水"
        rt, acc, kw = _direct(w, _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE}), "浴室漏水", asked=["description"],
                              obj=obj, prior=("冷氣不冷",))
        assert acc.write_draft.fill_active is True and acc.write_draft.fill_wide is False, kw   # 前提：單欄追問
        got = await rt._write_draft_turn_gate(acc, w.ident, _field(REPAIR, "description"), "冷氣不冷", from_intent=True)
        out[wide] = (got, list(acc.violations))
    assert out["on"] == out["off"]
    assert out["on"][0] == (None, False)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in out["on"][1] and WF.V_FILL_WIDE_CARRY_OVER not in out["on"][1]


def _dialog_users(w: _World) -> list:
    return [m.get("content") for m in ((w.state.get("agent") or {}).get("dialog") or []) if m.get("role") == "user"]


async def _card_without(monkeypatch, action: str, key: str, said: str) -> _World:
    """同 `_card`，但出卡那句不講 `key`（`said` 是 GOOD 原句裡講那欄的片段）⇒ 卡上該欄空。"""
    text, good = GOOD[action]
    assert said in text
    monkeypatch.setenv(FILL_ENV, "off")
    w = _World()
    res = await w.turn(text.replace(said, ""), intents=[_intent(action, **{k: str(v) for k, v in good.items()
                                                                          if k != key})])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert key not in _fields(w), _fields(w)
    monkeypatch.delenv(FILL_ENV, raising=False)
    return w


async def test_r1_w1_after_card_prior_turn_value_applied(api, monkeypatch, caplog):
    """R1-W1 卡後：卡上押金欄空，前一句「押金要收 20000」（意圖沒抽到、卡沒變），這一句「押金就照上一句」AI 才補上押金 20000
    （不在這一句）⇒ 收下、卡重出、押金 20000、記 `fill_wide_carry_over`、⛔ `fill_value_outside_data`、⛔「這次的修改沒有套用」。
    標記與資料段 ⛔ 帶值（沿用 FW11 (m)：trace、violation、日誌不含資料段與值）。"""
    caplog.set_level(logging.DEBUG)
    w = await _card_without(monkeypatch, CC, "deposit_amount", "押金 24000 ")
    await w.turn("押金要收 20000", intents=[_fi("none", data=[])], script=[_out("好的")])
    assert "押金要收 20000" in _dialog_users(w), _dialog_users(w)                    # 前提：前一句在客人原話裡
    assert (w.draft() or {}).get("asked") in ([], None), w.draft()                     # 前提：仍是卡後（寬回合 (b)）
    assert "deposit_amount" not in _fields(w), _fields(w)                              # 前提：該欄仍空
    res = await w.turn("押金就照上一句改", intents=[_fi(CC, data=["押金就照上一句改"], deposit_amount="20000")])
    v = _v(res)
    assert WF.V_FILL_WIDE_CARRY_OVER in v and WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert str(_payload(w, res).get("deposit_amount")) == "20000", _payload(w, res)
    assert WF.CARD_UNCHANGED_TEXT not in res.answer, res.answer
    blobs = {"trace": json.dumps(dataclasses.asdict(res.trace), ensure_ascii=False, default=str),
             "violations": json.dumps(v, ensure_ascii=False), "log": caplog.text}
    for where, blob in blobs.items():
        assert "押金就照上一句改" not in blob, where
        assert f'"{WF.DATA_TEXTS_KEY}"' not in blob and "fill_wide_data" not in blob, where
    assert all("20000" not in str(m) for m in v), v


async def test_r1_w1b_after_card_filled_field_rewritten_prior_value_rejected(api, monkeypatch):
    """R1-W1b（修復輪 1 追加，X4 FA1c-rep-06 型）：卡後、物件欄已填「學生獨立套房可租補」，這一句沒講物件，AI 把前句的物件名稱
    改寫成截短版重新提議 ⇒ 過得了 (i)（是前句原話的子字串）卻不在最新一句；該欄已有值 ⇒ ⛔ carry-over、照 (iii) 拒收
    （`fill_value_outside_data`）、草稿與卡上物件名稱不變、回話照第 8 點（`CARD_UNCHANGED_TEXT`）。"""
    w = await _card(monkeypatch, CC)
    before = _fields(w).get("estate_name")
    assert before == STUDENT_ESTATE, _fields(w)                                        # 前提：該欄已填
    short = STUDENT_ESTATE[:-1]
    assert short in GOOD[CC][0]                                                        # 前提：截短版在前句原話裡
    res = await w.turn("租金那邊再確認一下", intents=[_fi(CC, data=["租金那邊再確認一下"], estate_name=short)],
                       script=[_out("主模型的回答")])
    v = _v(res)
    assert WF.V_FILL_WIDE_CARRY_OVER not in v and WF.V_FILL_VALUE_OUTSIDE_DATA in v, v
    assert _fields(w).get("estate_name") == before, _fields(w)
    assert res.answer.startswith(WF.CARD_UNCHANGED_TEXT), res.answer


@pytest.mark.parametrize("filled", [True, False], ids=["filled", "empty"])
async def test_r1_w1b_direct_filled_field_prior_value_not_carried(api, filled):
    """R1-W1b（直接打閘門，卡後）：前句才有的金額 2000——草稿金額欄已有 1000 ⇒ ⛔ carry-over、照 (iii) 拒收、記拒收紀錄；
    金額欄空 ⇒ 照收、記 `fill_wide_carry_over`（R1-W1 對照）。"""
    w = _World()
    fields = {"contract_ref": CONTRACT, "title": "管理費", **({"total": "1000"} if filled else {})}
    rt, acc, _kw = _wdirect(w, _draft(w, MB, fields), R1_MSG, obj=_obj(MB, data=R1_SEGS), prior=(R1_PRIOR,),
                            card_live=True)
    got, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "2000", from_intent=True)
    if filled:
        assert (got, dropped) == (None, False)
        assert WF.V_FILL_VALUE_OUTSIDE_DATA in acc.violations and WF.V_FILL_WIDE_CARRY_OVER not in acc.violations
        assert acc.write_draft.fill_wide_rejected == {(MB, "total"): _field(MB, "total").label}
        assert acc.write_draft.draft["fields"]["total"] == "1000"
    else:
        assert (got, dropped) == ("2000", False)
        assert WF.V_FILL_WIDE_CARRY_OVER in acc.violations and WF.V_FILL_VALUE_OUTSIDE_DATA not in acc.violations


async def test_r1_w1_multi_field_prior_value_applied_thanks_still_rejected(api):
    """R1-W1 多欄：追問帳單項目與金額中，前一句「金額是 2000」（意圖沒抽到），這一句「帳單項目是水電費 3q」AI 補上金額 2000、
    帳單項目回成「水電費 3q」⇒ 金額照收（`fill_wide_carry_over`）；「水電費 3q」在最新一句、不在資料段 ⇒ 照舊拒收
    （`fill_value_outside_data`）；沒有任何值含「3q」。"""
    w = _World()
    _seed_draft(w, MB, {"contract_ref": CONTRACT}, asked=["title", "total"])
    await w.turn(R1_PRIOR, intents=[_fi(MB, data=[R1_PRIOR])], script=[_out("好的")])
    assert R1_PRIOR in _dialog_users(w), _dialog_users(w)
    assert "total" not in _fields(w), _fields(w)                                      # 前提：前一句的金額沒套上
    w.draft()["asked"] = ["title", "total"]                                            # 程式仍在追問兩欄（寬回合 (c)）
    res = await w.turn(R1_MSG, intents=[_fi(MB, data=R1_SEGS, title="水電費 3q", total="2000")],
                       script=[_out("主模型的回答")])
    v = _v(res)
    assert WF.V_FILL_WIDE_CARRY_OVER in v and WF.V_FILL_VALUE_OUTSIDE_DATA in v, v
    f = _payload(w, res) if res.trace.pending_id is not None else _fields(w)
    assert str(f.get("total")) == "2000" and "title" not in f, (f, res.answer)
    assert not any("3q" in str(x) for x in f.values()), f


_R1_PROMPT_VARIANTS = [{}, {"pick_rule": True}, {"asked_labels": ("帳單項目",)},
                       {"pick_rule": True, "asked_labels": ("租金",)}, {"target_picked": "56906"},
                       {"dialog_act": True}, {"rechoice_type": "bill"}]


def test_r1_w2_w3_constants_verbatim_and_examples_not_eval_inputs():
    """R1-W2／R1-W3：兩句＝v1 逐字、固定字串、已匯出；例句不是評估輸入原句或其近似、⛔ 道謝縮寫當例。"""
    assert WF.FIELD_NOT_IN_FORM_NOTE == R1_W2_NOTE_V1 and WF.ANOTHER_RECORD_NOTE == R1_W3_NOTE_V1
    for name in ("FIELD_NOT_IN_FORM_NOTE", "ANOTHER_RECORD_NOTE"):
        assert name in WF.__all__
    for note in (R1_W2_NOTE_V1, R1_W3_NOTE_V1):
        assert "{" not in note
        for banned in ("退租清潔", "說明幫我加", "饒河", "一起建", "3q", "3Q", "thx", "ty", "tks", "感謝", "謝謝", "感恩"):
            assert banned not in note, (banned, note)


@pytest.mark.parametrize("enum_labels", [True, False])
@pytest.mark.parametrize("variant", _R1_PROMPT_VARIANTS, ids=lambda v: json.dumps(v, ensure_ascii=False))
def test_r1_w2_w3_data_text_on_prompt_carries_each_note_once(enum_labels, variant):
    """R1-W2／R1-W3：`data_text=True` 系統句各含新句恰一次，位置＝`DATA_TEXTS_RULE`＋名稱說明（候選回合＋候選說明）之後、
    追問欄規則句之前；schema 不含新句（description 照舊只有 `DATA_TEXTS_RULE`）。"""
    sp = WF.write_intent_system_prompt(enum_labels=enum_labels, data_text=True, **variant)
    assert sp.count(R1_W2_NOTE_V1) == 1 and sp.count(R1_W3_NOTE_V1) == 1, variant
    head = "\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + (RC4_PICK_NOTE_V1 if variant.get("pick_rule") else "")
    tail = R1_W2_NOTE_V1 + R1_W3_NOTE_V1
    labels = variant.get("asked_labels")
    assert sp.endswith(head + tail + ("\n" + WF.answer_text_rule(labels) if labels else "")), variant
    pick_ids = {"pick_ids": ("101", "102")} if variant.get("pick_rule") else {}
    rf_kw = {k: v for k, v in variant.items() if k != "pick_rule"}
    rf = json.dumps(WF.write_intent_response_format(enum_labels=enum_labels, data_text=True, **rf_kw, **pick_ids),
                    ensure_ascii=False)
    assert R1_W2_NOTE_V1 not in rf and R1_W3_NOTE_V1 not in rf
    if not variant:                                                     # 改前 on 形狀＋兩句（逐字）
        off = WF.write_intent_system_prompt(enum_labels=enum_labels)
        assert sp == off + FIX3_PARTIAL_NOTE_V1 + head + tail


@pytest.mark.parametrize("label", sorted(PRE_CHANGE_DIGESTS))
def test_r1_w2_w3_data_text_off_prompt_equals_pre_change(label):
    """R1-W2／R1-W3：`data_text=False`（或不帶）⇒ 系統句與 schema＝改前逐字（上一片凍結的改前摘要），不含新句。"""
    enum_labels, variant = label.split("|", 1)
    sp, rf = _builder_kwargs(json.loads(variant))
    el = enum_labels == "True"
    for extra in ({}, {"data_text": False}, {"data_text": False, "asked_labels": ("帳單項目",)}):
        text = WF.write_intent_system_prompt(enum_labels=el, **sp, **extra)
        assert _digest(text) == PRE_CHANGE_DIGESTS[label][0]
        assert R1_W2_NOTE_V1 not in text and R1_W3_NOTE_V1 not in text
        assert _digest(WF.write_intent_response_format(enum_labels=el, **rf, **extra)) == PRE_CHANGE_DIGESTS[label][1]


def test_r1_w2_w3_main_model_prompt_untouched():
    """R1-W2／R1-W3：主模型（AgentOutput）提示詞 ⛔ 動——兩句只在 `write_forms.py` 內被引用。"""
    agent_dir = Path(WF.__file__).resolve().parent
    hits = sorted(p.name for p in agent_dir.rglob("*.py")
                  for name in ("FIELD_NOT_IN_FORM_NOTE", "ANOTHER_RECORD_NOTE")
                  if name in p.read_text(encoding="utf-8"))
    assert hits == ["write_forms.py", "write_forms.py"], hits


# ════════════════════════════════════════════════════════════════════
# 修復輪 1 追加 r1c（計畫 §11 追加 r1c、§4.1 (b)；業主 2026-10-28「收窄卡後定義，定向重跑 (Recommended)」）
# 卡後寬回合要「回合開始時草稿綁定的卡還活著」（`_write_draft_bound_card` 找得到、無 `receipt`、`invalidated` 非 `True`）；
# 插問知識題（凍結）後 `asked` 已清空、還沒出過卡 ⇒ ⛔ 寬回合，系統句、schema、值閘照現行。
# ════════════════════════════════════════════════════════════════════
R1C_QUESTION = "修繕費用是誰要付？"


def _r1c_begin(w: _World, message: str):
    """以真的 `_write_draft_begin` 建回合內狀態（`bound_card_live` 由它判），再跑 `_fill_begin_intent_call`。
    回 `(acc, 建構點參數)`。"""
    rt = w.runtime(_Provider([]))
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-r1c", start=0.0)
    rt._write_draft_begin(acc, w.ident, w.state.setdefault("agent", {}), message)
    wd = acc.write_draft
    assert wd is not None and wd.had_draft and wd.asked == [] and not wd.frozen    # 前提：草稿在、asked 空、非凍結
    return acc, rt._fill_begin_intent_call(acc)


@pytest.mark.parametrize("card,live", [
    (None, False),
    ({}, True),
    ({"invalidated": True}, False),
    ({"receipt": {"status": "ok"}}, False),
    ({"action": MB}, False),
], ids=["no_card", "live", "invalidated", "receipt", "other_action"])
def test_r1c_after_card_kind_requires_live_bound_card(api, card, live):
    """r1c（§4.1 (b)）：草稿在、`asked` 空——沒有綁定卡、綁定卡已作廢、已有 `receipt`、只有別的動作的卡 ⇒ `bound_card_live`
    為 `False`、`_fill_begin_intent_call` 回 `{}`、⛔ 設 `fill_wide`／`fill_wide_kind`（也不是單欄追問回合）；有活的綁定卡 ⇒
    照舊卡後寬回合（`{"data_text": True}`、`FILL_WIDE_CARD`）。"""
    w = _World()
    _seed_draft(w, REPAIR, {"estate_name": STUDENT_ESTATE})
    if card is not None:
        extra = dict(card)
        _bind_live_card(w, extra.pop("action", REPAIR), **extra)
    acc, kw = _r1c_begin(w, "冷氣不冷")
    wd = acc.write_draft
    assert wd.bound_card_live is live and wd.pick_list_open is False                # 本組沒有候選集
    if live:
        assert kw == {"data_text": True}, kw
        assert wd.fill_wide is True and wd.fill_wide_kind == runtime_mod.FILL_WIDE_CARD
    else:
        assert kw == {}, kw
        assert wd.fill_wide is False and wd.fill_wide_kind is None and wd.fill_active is False


async def test_r1c_real_card_live_then_invalidated_or_receipt_is_not_after_card(api, monkeypatch):
    """r1c 正對照（§4.1 (b)）：真的出過卡（`_card`）⇒ 綁定卡活著、卡後寬回合；同一張卡標 `invalidated` 或帶 `receipt` ⇒
    ⛔ 寬回合（`{}`）。"""
    w = await _card(monkeypatch, MB)
    acc, kw = _r1c_begin(w, "金額改成 2000")
    assert acc.write_draft.bound_card_live is True and kw == {"data_text": True}, kw
    assert acc.write_draft.fill_wide_kind == runtime_mod.FILL_WIDE_CARD
    for mark in ({"invalidated": True}, {"receipt": {"status": "ok"}}):
        w2 = await _card(monkeypatch, MB)
        entries = [e for e in w2.pending().values() if e.get("action") == MB]
        assert len(entries) == 1, w2.pending()                                       # 前提：只有那一張卡
        entries[0].update(mark)
        acc2, kw2 = _r1c_begin(w2, "金額改成 2000")
        assert acc2.write_draft.bound_card_live is False and kw2 == {}, (mark, kw2)
        assert acc2.write_draft.fill_wide is False and acc2.write_draft.fill_wide_kind is None


async def test_r1c_question_then_estate_answer_without_card_equals_current(api, monkeypatch):
    """r1c 觸發場景（§11 追加 r1c，E2a T 組型）：報修追問物件中插問知識題（T2 凍結 ⇒ `asked` 清空、還沒出過卡），下一句只講
    物件「學生獨立套房可租補」（T3）⇒ ⛔ 卡後寬回合：寬回合開關 on／off 送出的意圖呼叫系統句、schema、回話、草稿、標記逐字
    相同，皆不帶資料段規則與 `data_texts`、⛔ 任何 `fill_` 標記。"""
    out = {}
    for wide in ("off", "on"):
        monkeypatch.setenv(WIDE_ENV, wide)
        w = _World()
        _seed_draft(w, REPAIR, {}, asked=["estate_name"])
        t2 = await w.turn(R1C_QUESTION, script=[_out("依合約約定。")])
        assert WF.V_QUESTION_FROZEN in _v(t2), _v(t2)                                  # 前提：T2 凍結
        assert w.draft() is not None and w.draft()["asked"] == [] and not w.pending()  # 前提：草稿在、asked 空、沒出過卡
        res, kw = await _run_turn(w, STUDENT_ESTATE, [_intent(REPAIR, estate_name=STUDENT_ESTATE)],
                                  script=[_out("主模型的回答")])
        assert WF.DATA_TEXTS_RULE not in _system(kw) and WF.DATA_TEXTS_KEY not in _schema(kw)["properties"]
        assert not _fill_marks(res), _v(res)
        out[wide] = (_system(kw), json.dumps(kw["response_format"], ensure_ascii=False), res.answer, _fields(w),
                     list(_v(res)))
    assert out["on"] == out["off"]


async def test_r1c_unpicked_candidate_list_without_card_is_after_card_wide(api):
    """r1c（§4.1 (b) 候選回合）：列出候選、未選定、沒出過卡、`asked` 空 ⇒ `pick_list_open`、卡後寬回合（`{"data_text": True}`、
    `FILL_WIDE_CARD`）；同一份草稿把候選集拿掉（插問後型：沒卡也沒候選）⇒ `{}`。"""
    w = _World()
    await _p32_listed(w)
    w.draft()["asked"] = []
    assert not w.pending()                                                            # 前提：沒出過卡
    acc, kw = _r1c_begin(w, RC4_MSG)
    wd = acc.write_draft
    assert wd.candidates is not None and wd.candidates["picked"] is None              # 前提：候選集讀回、未選定
    assert wd.bound_card_live is False and wd.pick_list_open is True
    assert kw == {"data_text": True}, kw
    assert wd.fill_wide is True and wd.fill_wide_kind == runtime_mod.FILL_WIDE_CARD
    w.state["agent"].pop("write_candidates")
    acc2, kw2 = _r1c_begin(w, RC4_MSG)
    assert acc2.write_draft.candidates is None and acc2.write_draft.pick_list_open is False
    assert kw2 == {} and acc2.write_draft.fill_wide is False and acc2.write_draft.fill_wide_kind is None


async def test_r1c_picked_candidate_without_card_is_not_after_card(api, monkeypatch):
    """r1c（§4.1 (b)）：候選已選定（不再等使用者選）、沒出過卡、`asked` 空 ⇒ ⛔ 卡後寬回合（`{}`）；補上活的綁定卡 ⇒
    卡後寬回合。"""
    w, src = await _picked_on(monkeypatch)
    w.draft()["asked"] = []
    assert not w.pending()                                                            # 前提：沒出過卡
    acc, kw = _r1c_begin(w, "租金 12000")
    assert acc.write_draft.candidates["picked"] == src.picked and acc.write_draft.pick_list_open is False
    assert kw == {} and acc.write_draft.fill_wide is False
    _bind_live_card(w, src.action)
    acc2, kw2 = _r1c_begin(w, "租金 12000")
    assert acc2.write_draft.bound_card_live is True and kw2 == {"data_text": True}, kw2
    assert acc2.write_draft.fill_wide_kind == runtime_mod.FILL_WIDE_CARD
