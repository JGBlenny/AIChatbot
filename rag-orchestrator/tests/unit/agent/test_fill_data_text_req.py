"""unit：填欄只填答覆（計畫 `.kiro/specs/agentic-mcp-orchestration/plan-fill-answer-only-20261027.md` §4.1；
凍結清單 `acceptance-fill-answer-only-20261027.md` 的 FA8、FA9 (a)～(t)，皆為機制項）。

業主原話：「只填答覆部分，衍生值算錯卡」「例：「水電費 3q」只能填「水電費」。卡上出現道謝字，或出現從道謝衍生的
別欄值（金額 3、面積 3），都算錯筆卡。」

分工（DSP-091）：哪部分是資料、哪部分回答追問欄位由 AI 在寫入意圖呼叫標出（本檔的假 provider 直接給
`data_texts`／`answer_text`）；填不填、併不併、要不要重問由程式決定（`_write_draft_turn_gate` 等）。

條目 ↔ 測試：測試名一律以條目代號開頭（`test_fa8_*`、`test_fa9_<字母>_*`）；值閘呼叫點 ①～⑥ 與 3 個意圖呼叫
建構點的測試名另含 `site1`～`site6`、`build_main`／`build_pick_rule`／`build_target_picked`。

資料走真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`）＋真 `mcp_facade.build_registry`；
全部離線，⛔ 打任何模型。期望值由測試寫死（⛔ 引用被測物輸出當期望）；FA8 (2) 的 `PRE_CHANGE_DIGESTS` 是改前
`write_forms.py`（md5 `be060b80580e44936a14ccb5a8bf4a73`）在測試容器內算出的摘要（取法見該常數註解）。
"""
from __future__ import annotations

import ast
import asyncio
import copy
import dataclasses
import hashlib
import json
import logging
import textwrap
from pathlib import Path

import pytest

from services import usage_metering
from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.output_schema import WriteIntent
from services.agent.runtime import AgentRuntime, TurnAccumulator, _fill_locate, _WriteDraftTurn

from tests.unit.agent.test_aplus_card_program_only_req import GOOD, _proposal
from tests.unit.agent.test_aplus_card_program_only_req import _seed_draft as _seed_draft_raw
from tests.unit.agent.test_runtime_req import FakeAssembler, FakeClock, VerifierVerdict  # noqa: F401
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    STUDENT_ESTATE, _intent, _out, _pm, _Provider, _Reg, _unique_estate_hit,
)

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-fill-answer-only-20261027")]

ENV = WF.FILL_DATA_TEXT_ENV
#: 下一片（plan-fill-wide-20261028）的開關：本檔斷言「首句、卡後、多欄回合＝off」的測試把它設 off（＝FW11 (a) 改前逐字）。
WIDE_ENV = WF.FILL_DATA_TEXT_WIDE_ENV
RT = AgentRuntime
RUNTIME_PATH = Path(runtime_mod.__file__)
MB = "manual_bill_create"
REPAIR = "repair_create"
EST = "estate_create"
CONTRACT = "89481"                  # GOOD[manual_bill_create] 用的合約（fixture 內存在）
_NO = object()


@pytest.fixture(autouse=True)
def _fill_on(monkeypatch):
    """本檔預設開關 on（未設＝on）；off 的測試自己 `setenv`。"""
    monkeypatch.delenv(ENV, raising=False)


def _fi(action: str = "none", data=_NO, answer=_NO, *, target=_NO, extra=None, **fields):
    """寫入意圖的假回應：`data`→`data_texts`、`answer`→`answer_text`；`_NO`＝不帶該鍵（鍵缺）。"""
    obj: dict = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()]}
    if data is not _NO:
        obj[WF.DATA_TEXTS_KEY] = data
    if answer is not _NO:
        obj[WF.ANSWER_TEXT_KEY] = answer
    if target is not _NO:
        obj[WF.PICK_TARGET_KEY] = target
    if extra:
        obj.update(extra)
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


def _v(res) -> list:
    return res.trace.violations


def _fields(w: _World) -> dict:
    return dict((w.draft() or {}).get("fields") or {})


def _seed_draft(w: _World, action: str, fields: dict, *, asked=()) -> None:
    """草稿欄值一律存字串（形狀檢查 `write_draft_shape_invalid` 會丟掉非字串值的草稿）。"""
    _seed_draft_raw(w, action, {k: str(v) for k, v in fields.items()}, asked=asked)


def _schema(kw) -> dict:
    return kw["response_format"]["json_schema"]["schema"]


def _system(kw) -> str:
    return kw["messages"][0]["content"]


def _assert_reasked(res, label: str) -> None:
    """B6：程式依草稿回缺欄追問（⛔ 出卡、⛔ 整句填入）。"""
    assert res.outcome["state"] == "clarifying", res.answer
    assert res.trace.pending_id is None
    assert label in res.answer, res.answer
    assert WF.V_ANSWER_FILLED not in _v(res), _v(res)


def _seed_repair_asking_description(w: _World) -> None:
    _seed_draft(w, REPAIR, {"estate_name": STUDENT_ESTATE}, asked=["description"])


def _seed_bill_asking_title(w: _World, **extra) -> None:
    _seed_draft(w, MB, {"contract_ref": CONTRACT, **extra}, asked=["title"])


def _patch_intent_timeout(monkeypatch) -> list:
    """意圖呼叫逾時（程式優先等待與意圖等待上限都縮短；意圖 task 永不回）。回記錄 task 的清單。"""
    monkeypatch.setattr(runtime_mod, "WRITE_INTENT_WAIT_MAX_S", 0.05)
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_S", 0.05)
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S", 0.05)
    return []


async def _hang(_kwargs):
    await asyncio.sleep(30)


def _boom(_kwargs):
    raise RuntimeError("bedrock 500")


# ── 直接呼叫（單一 helper／呼叫點）用的回合內狀態 ─────────────────────────
def _draft(w: _World, action: str, fields: dict) -> dict:
    return {"action": action, "fields": {k: str(v) for k, v in fields.items()}, "idle_turns": 0,
            "created_by_role": runtime_mod._write_draft_owner(w.ident), "asked": []}


def _direct(w: _World, draft, message: str, *, asked=(), obj=None, consumed: bool = True, prior=()):
    """建一個寫入回合的回合內狀態（同 `_write_draft_begin` 的欄位），依開關跑 `_fill_begin_intent_call`，
    再以 `obj`（意圖呼叫驗過的原始物件）跑 B1。回 `(runtime, acc, 建構點參數)`。"""
    rt = RT(_Provider([]), w.reg, None, None, None, stage="M1")
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-fill", start=0.0)
    acc.write_draft = _WriteDraftTurn(
        draft=draft, owner=runtime_mod._write_draft_owner(w.ident), user_texts=[*prior, message],
        asked=list(asked), had_draft=draft is not None, user_message=message)
    kw = rt._fill_begin_intent_call(acc)
    if obj is not None:
        rt._fill_read_data(acc.write_draft, obj)
    acc.write_draft.intent_consumed = consumed
    return rt, acc, kw


def _field(action: str, key: str):
    return WF.FORMS[action].field(key)


# ════════════════════════════════════════════════════════════════════
# FA8：沒送意圖呼叫的回合與開關 off 逐字不變
# ════════════════════════════════════════════════════════════════════
#: 改前 `write_forms.py`（md5 be060b80…，`~/jgb-archive/arch-step3-20261018/fill/baseline/code-before`）在測試容器
#: 內以 `json.dumps(x, ensure_ascii=False)` 的 UTF-8 sha256 算出（[系統句, response_format]）。取法：暫置改前檔、
#: `importlib` 載入、對同一組參數同時算改前／現行／`data_text=False` 三者並斷言相等，輸出存
#: `~/jgb-archive/arch-step3-20261018/fill/prefill-golden-check.txt`（暫置檔已刪）。
#: 鍵＝`enum_labels|參數`；`pick`＝系統句 `pick_rule=True`＋schema `pick_ids=("101","102")`。
PRE_CHANGE_DIGESTS = {
    "True|{}": ["4359e27e1cee50b0c43c2a14f00b02845a4485baf4747e7fe26e69346851d446",
                "eae9caef0ba739a2227084839474e5677856dffbe0c0187263b6fd8c99cfb1a2"],
    "True|{\"pick\": true}": ["9dcc416c59391f74d24397d86e5a576a0a6d4d32916ed1e22f27fcba72045e28",
                              "50d767bacb5e16fcfd2a1e879b483d0e709bca95271838bd1ea545c0b56988c2"],
    "True|{\"target_picked\": \"56906\"}": ["15bfda519695653301029ac427d9b2ab3fa4bf528c6ce2c02c9c26672590154a",
                                            "6e8443e133235b3c3e1c2cc1ead1ca3fb1d27a744d4cac86ec49f51345fa8d3d"],
    "True|{\"dialog_act\": true}": ["8113fe2e258750cf6df5e38173121abe29667072f6a173f763e391e84dc51d82",
                                    "2b8b6fb8ef865a2afd7a4601333a68fa09c52738bd11677346a79adbac3258c3"],
    "True|{\"rechoice_type\": \"bill\"}": ["0389b780f292c7e92ba37e87229647f51ae1b61a3a30a88a1ba8575a2bea0b62",
                                           "723e5152b7e6c337f0eb7e3b99bc9507c34ff218d969f249b0bd4f94c622ad57"],
    "True|{\"rechoice_type\": \"contract\"}": ["74905c34d5021f482a13233df2000c51749438a1659b98d2cffe4b39f0e84ccd",
                                               "332e1e8358df504575ed9a83721192ea9236782cf4bf943114b4df1218109379"],
    "True|{\"rechoice_type\": \"estate\"}": ["73598e0cbe30ddd20f9e34e89bddfbf2d9572377941dd925eb7bb1a708766707",
                                             "81ad75bdb5dde8161f45346cc38dcefcb8ca2626e10854953882c6810c00be4e"],
    "False|{}": ["441415fe11a503281da53fda50ce456d8e5b7c060f30d30db976b12689e58b0a",
                 "7dec74319c049f8db9dd42e7280c957ab1e7d12ca57acb0075f57671ac3855f1"],
    "False|{\"pick\": true}": ["d0179c3be6db1c93cf44558ce9a3abc6573e8d99f15815f4d2d75cc06da0b22d",
                               "ef493efce85274575f2b52e772743b327dcd270f7177cba03a26c1ed2b572fb2"],
    "False|{\"target_picked\": \"56906\"}": ["a9abe48fabee9384e56f16f5abb735fce9644ac7222cb67c0cb476fb7f949fda",
                                             "a46177e73a89676f47adf61cadd0094a5d9875665e4010455fe1cddc40451271"],
    "False|{\"dialog_act\": true}": ["6a91405d5538f606c15c43b3abfe4b9767cb1437c66971013a32abc3a2274283",
                                     "3eccd0050bd8b01ce2975a6f0b6889bc6858a1ffb9c0817c2bb3322339f831a7"],
    "False|{\"rechoice_type\": \"bill\"}": ["b2d12db5785b3bd0837602df6e8ca35bce07ee6c1a3cd1c19522790da9c4122d",
                                            "e0955ba5f90e813df4d8334a18c30e93906bd8e0b6713f98bfef33cd791faea0"],
    "False|{\"rechoice_type\": \"contract\"}": ["afefae78ed8180e241f81a2464c3447ef37020205ef4abd3a35d0fa1b037e179",
                                                "9c32622ca4cc7e2d52621300dd07cb03d705fa1bee3a1cae5ca37389fbea8b2f"],
    "False|{\"rechoice_type\": \"estate\"}": ["ff12fcab4578f362e717c896285ebe31237643c8c225e13a336911f8867055be",
                                              "7ca5b6ded82085ba8ad808a5fd9548b82d9979dce1adba6dcdc35869e0f0e184"],
}


def _digest(x) -> str:
    return hashlib.sha256(json.dumps(x, ensure_ascii=False).encode("utf-8")).hexdigest()


def _builder_kwargs(variant: dict) -> tuple:
    sp = {k: v for k, v in variant.items() if k != "pick"}
    rf = dict(sp)
    if variant.get("pick"):
        sp["pick_rule"] = True
        rf["pick_ids"] = ("101", "102")
    return sp, rf


@pytest.mark.parametrize("label", sorted(PRE_CHANGE_DIGESTS))
def test_fa8_2_off_builders_equal_pre_change_golden(label):
    """FA8 (2)：三個建構點共用的 `write_intent_system_prompt`／`write_intent_response_format`，`data_text=False`（off）
    與不帶本片參數時，和改前 `write_forms.py` 的輸出逐位相同（摘要比對；矩陣涵蓋 enum_labels、`pick_rule`／
    `pick_ids`、`target_picked`、`rechoice_type`、`dialog_act`）。"""
    enum_labels, variant = label.split("|", 1)
    sp, rf = _builder_kwargs(json.loads(variant))
    el = enum_labels == "True"
    for extra in ({}, {"data_text": False}, {"data_text": False, "asked_labels": ("帳單項目",)}):
        assert _digest(WF.write_intent_system_prompt(enum_labels=el, **sp, **extra)) == PRE_CHANGE_DIGESTS[label][0]
        assert _digest(WF.write_intent_response_format(enum_labels=el, **rf, **extra)) == PRE_CHANGE_DIGESTS[label][1]


def test_fa8_2_on_builders_only_append_the_rule_and_keys():
    """FA8 (2) 正對照（on 形狀）：on ⇒ 系統句＝off 系統句＋`WRITE_INTENT_PARTIAL_NOTE`（緊接 off 末尾的
    `WRITE_INTENT_NONE_RULE`，修復輪 2 追加 brief-fix3）＋「\\n＋規則」；schema＝off schema＋必填 `data_texts`（字串陣列），
    追問回合再加必填 `answer_text`（字串）、規則句帶追問欄位標籤（⛔ 使用者原話）。"""
    off_sp = WF.write_intent_system_prompt(enum_labels=True)
    off_schema = WF.write_intent_call_schema(enum_labels=True)
    on_sp = WF.write_intent_system_prompt(enum_labels=True, data_text=True)
    assert off_sp.endswith("\n" + WF.WRITE_INTENT_NONE_RULE)
    assert on_sp == off_sp + FIX3_PARTIAL_NOTE_V1 + "\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE
    on_schema = WF.write_intent_call_schema(enum_labels=True, data_text=True)
    assert on_schema["properties"][WF.DATA_TEXTS_KEY] == {
        "type": "array", "items": {"type": "string"}, "description": WF.DATA_TEXTS_RULE}
    assert on_schema["required"] == off_schema["required"] + [WF.DATA_TEXTS_KEY]
    trimmed = copy.deepcopy(on_schema)
    trimmed["properties"].pop(WF.DATA_TEXTS_KEY)
    trimmed["required"].remove(WF.DATA_TEXTS_KEY)
    assert trimmed == off_schema
    ask_sp = WF.write_intent_system_prompt(enum_labels=True, data_text=True, asked_labels=("帳單項目",))
    rule = WF.answer_text_rule(("帳單項目",))
    assert "帳單項目" in rule and ask_sp == on_sp + "\n" + rule
    ask_schema = WF.write_intent_call_schema(enum_labels=True, data_text=True, asked_labels=("帳單項目",))
    assert ask_schema["properties"][WF.ANSWER_TEXT_KEY] == {"type": "string", "description": rule}
    assert ask_schema["required"][-2:] == [WF.DATA_TEXTS_KEY, WF.ANSWER_TEXT_KEY]
    assert ask_schema["additionalProperties"] is False


@pytest.mark.parametrize("value,expected", [
    (None, True), ("", True), ("on", True), (" on ", True), ("off", False), ("off ", False),
])
def test_fa8_3_switch_values(value, expected):
    env = {} if value is None else {ENV: value}
    assert WF.fill_data_text_enabled_from_env(env) is expected


@pytest.mark.parametrize("bad", ["true", "ON", "0", "1", "no", "disabled"])
def test_fa8_3_bad_switch_value_fails_startup(monkeypatch, bad):
    """FA8 (3)：開關值不合 ⇒ `AgentRuntime` 建構（啟動）即 `ValueError`。"""
    with pytest.raises(ValueError):
        WF.fill_data_text_enabled_from_env({ENV: bad})
    monkeypatch.setenv(ENV, bad)
    with pytest.raises(ValueError):
        RT(_Provider([]), None, None, None, None, stage="M1")


def test_fa8_3_switch_attribute_has_no_default_off_getattr():
    """FA8 (3)／§4.1「開關」：讀開關一律走屬性本身，⛔ `getattr(self, "_fill_data_text_on", False)` 這種預設 off 的讀法。"""
    src = RUNTIME_PATH.read_text(encoding="utf-8")
    assert "getattr(self, \"_fill_data_text_on\"" not in src
    assert "getattr(self, '_fill_data_text_on'" not in src
    assert src.count("self._fill_data_text_on") >= 2          # 正對照：建構時設、建構點讀


async def test_fa8_2_off_followup_turn_sends_pre_change_shape_and_fills_whole_sentence(api, monkeypatch):
    """FA8 (2)：開關 off 的追問回合——送出的系統句與 schema 不含本片任何規則與鍵，且與不帶本片參數的建構函式逐位相同；
    整句填入照改前（整句「冷氣不冷 3q」填入）；沒有任何 `fill_` 標記。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    _seed_repair_asking_description(w)
    provider = _Provider([], [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
    rt = w.runtime(provider)
    res = await rt.run_turn(w.ident, "冷氣不冷 3q", w.state)
    (kw,) = provider.intent_calls
    assert WF.DATA_TEXTS_RULE not in _system(kw)
    assert WF.DATA_TEXTS_KEY not in _schema(kw)["properties"]
    assert WF.ANSWER_TEXT_KEY not in _schema(kw)["properties"]
    assert _system(kw) in {WF.write_intent_system_prompt(enum_labels=b) for b in (True, False)}
    assert kw["response_format"] in [WF.write_intent_response_format(enum_labels=b) for b in (True, False)]
    assert WF.V_ANSWER_FILLED in _v(res)
    assert _fields(w).get("description") == "冷氣不冷 3q" or "冷氣不冷 3q" in res.answer
    assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)


async def test_fa8_2_off_gate_sites_equal_pre_change_value_gate(api, monkeypatch):
    """FA8 (2)：off ⇒ 本回合閘門原話（①～⑥ 共用）＝改前值閘（同一輸入、同一回傳、同一組 violation），連資料段外的值也照併。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    rt, acc, kw = _direct(w, draft, "水電費 3q", asked=["title"],
                          obj={"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["水電費"]})
    assert kw == {} and acc.write_draft.fill_active is False
    for key, raw in (("total", "3"), ("title", "水電費 3q"), ("total", "abc"), ("date_expire", "2020/01/01")):
        f = _field(MB, key)
        expect_v: list = []
        expect = await rt._write_draft_gate_value(f, raw, w.ident, acc.write_draft.user_texts, expect_v,
                                                  from_intent=True)
        before = list(acc.violations)
        got, dropped = await rt._write_draft_turn_gate(acc, w.ident, f, raw, from_intent=True)
        assert got == expect and acc.violations[len(before):] == expect_v, (key, raw)
        assert dropped is (expect is None and bool(expect_v))


async def test_fa8_1_pick_button_turn_sends_no_intent_call_and_matches_off(api, monkeypatch):
    """FA8 (1)：`pick:` 按鈕回合不送寫入意圖呼叫 ⇒ 本片完全不生效：on 與 off 同一回合的回話、草稿、標記相同。"""
    from tests.unit.agent.test_f12_repick_r6_req import _listed

    results = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, "off")                      # 列候選那一回合（假意圖不帶資料段）照改前
        w, src, _res = await _listed("exact")
        monkeypatch.setenv(ENV, value)
        provider = _Provider([], None)
        rt = w.runtime(provider)
        res = await rt.run_turn(w.ident, f"pick:{src.ctype}:{src.picked}", w.state)
        assert provider.intent_calls == []
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        results.append((res.answer, res.outcome, _fields(w), [m for m in _v(res)]))
    assert results[0] == results[1]


def test_fa8_1_fill_state_is_only_set_where_the_intent_call_is_built():
    """FA8 (1)：本片的回合內狀態只在建意圖呼叫那一處開啟（`_fill_begin_intent_call` 只被 `_start_write_intent_call`
    呼叫）⇒ 文件回合、`pick:` 回合（不送意圖呼叫）`fill_active` 恆為 `False`，`_write_draft_turn_gate` 即改前值閘。"""
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    callers = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "_fill_begin_intent_call"):
                    callers.append(node.name)
    assert callers == ["_start_write_intent_call"], callers
    setters = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Attribute) and t.attr == "fill_active" for t in n.targets)]
    assert len(setters) == 1, "fill_active 只能在 _fill_begin_intent_call 設"


async def test_fa8_1_inactive_turn_gate_equals_value_gate(api):
    """FA8 (1)：沒送意圖呼叫的回合（`fill_active=False`，例：文件回合）——即使開關 on，閘門原話＝現行值閘。"""
    w = _World()
    rt = RT(_Provider([]), w.reg, None, None, None, stage="M1")
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-doc", start=0.0)
    acc.write_draft = _WriteDraftTurn(draft=_draft(w, MB, {"contract_ref": CONTRACT}),
                                      owner=runtime_mod._write_draft_owner(w.ident),
                                      user_texts=["水電費 3q"], user_message="水電費 3q")
    assert rt._fill_data_text_on is True and acc.write_draft.fill_active is False
    for key, raw in (("total", "3"), ("title", "水電費 3q")):
        got, _dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, key), raw)
        expect = await rt._write_draft_gate_value(_field(MB, key), raw, w.ident, ["水電費 3q"], [])
        assert got == expect and got is not None
    assert not [m for m in acc.violations if str(m).startswith("fill_")]


# ════════════════════════════════════════════════════════════════════
# 3 個意圖呼叫建構點（§4.1 A.3）＋ FA9 (k)
# ════════════════════════════════════════════════════════════════════
async def test_build_main_followup_turn_carries_rule_labels_and_required_keys(api, monkeypatch):
    """建構點 `_start_write_intent_call`（一般）：單欄追問回合 ⇒ 系統句末尾接資料段規則＋追問欄位標籤規則；schema 根層
    必填 `data_texts`、`answer_text`。修復輪 3（縮小到追問回合）：非追問寫入回合（第一句）⇒ 與開關 off 相同（不帶本片
    任何規則與鍵）。下一片起第一句由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 本條設它 off（FW11 (a)）。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    w = _World()
    _seed_repair_asking_description(w)
    provider = _Provider([], [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
    await w.runtime(provider).run_turn(w.ident, "冷氣不冷 3q", w.state)
    (kw,) = provider.intent_calls
    rule = WF.answer_text_rule(("問題描述",))
    assert _system(kw).endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE + "\n" + rule)
    assert _schema(kw)["required"][-2:] == [WF.DATA_TEXTS_KEY, WF.ANSWER_TEXT_KEY]

    w2 = _World()
    provider2 = _Provider([_out("好的")], [_fi("none", data=[])])
    await w2.runtime(provider2).run_turn(w2.ident, "能幫我新增一張修繕單嗎", w2.state)
    (kw2,) = provider2.intent_calls
    assert WF.DATA_TEXTS_RULE not in _system(kw2)
    assert _system(kw2) in {WF.write_intent_system_prompt(enum_labels=b) for b in (True, False)}
    assert kw2["response_format"] in [WF.write_intent_response_format(enum_labels=b) for b in (True, False)]
    assert WF.DATA_TEXTS_KEY not in _schema(kw2)["properties"]
    assert WF.ANSWER_TEXT_KEY not in _schema(kw2)["properties"]


@pytest.mark.parametrize("bad", ["missing", "null", "string", "number_items", "answer_missing", "answer_null",
                                 "answer_number"])
async def test_fa9_k_build_main_bad_keys_mean_data_unknown(api, bad):
    """FA9 (k) 建構點一般：鍵缺、null、型別不對（`data_texts` 非字串陣列、`answer_text` 非字串）⇒ 資料段未知：
    意圖值不併、追問欄不填、程式重問。"""
    data, answer = {
        "missing": (_NO, "冷氣不冷"), "null": (None, "冷氣不冷"), "string": ("冷氣不冷", "冷氣不冷"),
        "number_items": ([1], "冷氣不冷"), "answer_missing": (["冷氣不冷"], _NO),
        "answer_null": (["冷氣不冷"], None), "answer_number": (["冷氣不冷"], 3),
    }[bad]
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=[_fi(REPAIR, data=data, answer=answer, description="冷氣不冷")])
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert "description" not in _fields(w)
    _assert_reasked(res, "問題描述")


async def _listed_on(monkeypatch, name: str = "exact"):
    from tests.unit.agent.test_f12_repick_r6_req import _listed
    monkeypatch.setenv(ENV, "off")
    w, src, _res = await _listed(name)
    monkeypatch.delenv(ENV, raising=False)
    return w, src


async def _picked_on(monkeypatch, name: str = "exact"):
    from tests.unit.agent.test_f12_repick_r6_req import _picked
    monkeypatch.setenv(ENV, "off")
    w, src = await _picked(name)
    monkeypatch.delenv(ENV, raising=False)
    return w, src


@pytest.mark.parametrize("data", [_NO, None, "租金 12000"])
async def test_fa9_k_build_pick_rule_bad_keys_mean_data_unknown(api, monkeypatch, data):
    """FA9 (k) 建構點候選段 `pick_rule=True`（未選定）：系統句與 schema 同樣接資料段規則與必填鍵；鍵缺、null、型別不對
    ⇒ 資料段未知、意圖值（租金）不併。正對照：資料段有效 ⇒ 租金照併。修復輪 3：本片只在單欄追問回合生效 ⇒ 列候選後把
    草稿追問改成單欄（租金），候選段回合才走本片。"""
    w, src = await _listed_on(monkeypatch)
    w.draft()["asked"] = ["rent"]
    provider = _Provider([_out("好的")], [_fi(src.action, data=data, answer="12000", rent="12000")])
    res = await w.runtime(provider).run_turn(w.ident, "租金 12000", w.state)
    (kw,) = provider.intent_calls
    assert WF.PICK_ID_KEY in _schema(kw)["properties"]                       # 前提：走的是 pick_rule 這一支
    assert WF.PICK_ID_RULE in _system(kw) and WF.DATA_TEXTS_RULE in _system(kw)
    assert WF.DATA_TEXTS_KEY in _schema(kw)["required"]
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert "rent" not in _fields(w)

    w2, src2 = await _listed_on(monkeypatch)
    w2.draft()["asked"] = ["rent"]
    res2 = await w2.runtime(_Provider([_out("好的")], [_fi(src2.action, data=["租金 12000"], answer="12000",
                                                           rent="12000")])
                            ).run_turn(w2.ident, "租金 12000", w2.state)
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in _v(res2)
    assert str(_fields(w2).get("rent")) == "12000", (_fields(w2), res2.answer)


@pytest.mark.parametrize("data", [_NO, None, ["租金", 12000]])
async def test_fa9_k_build_target_picked_bad_keys_mean_data_unknown(api, monkeypatch, data):
    """FA9 (k) 建構點候選段 `target_picked`（已選定）：系統句與 schema 接資料段規則與必填鍵（指令版 schema）；鍵缺、
    null、型別不對 ⇒ 資料段未知、意圖值不併。正對照：資料段有效 ⇒ 照併。修復輪 3：選定後把草稿追問改成單欄（租金），
    該回合才走本片。"""
    w, src = await _picked_on(monkeypatch)
    w.draft()["asked"] = ["rent"]
    provider = _Provider([_out("好的")], [_fi(src.action, data=data, answer="12000", target=[], rent="12000")])
    res = await w.runtime(provider).run_turn(w.ident, "租金 12000", w.state)
    (kw,) = provider.intent_calls
    assert WF.PICK_TARGET_KEY in _schema(kw)["properties"]                   # 前提：走的是 target_picked 這一支
    assert WF.pick_target_rule(src.picked) in _system(kw) and WF.DATA_TEXTS_RULE in _system(kw)
    assert WF.DATA_TEXTS_KEY in _schema(kw)["required"]
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert "rent" not in _fields(w)

    w2, src2 = await _picked_on(monkeypatch)
    w2.draft()["asked"] = ["rent"]
    res2 = await w2.runtime(_Provider([_out("好的")], [
        _fi(src2.action, data=["租金 12000"], answer="12000", target=[], rent="12000")])
    ).run_turn(w2.ident, "租金 12000", w2.state)
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in _v(res2), _v(res2)
    assert str(_fields(w2).get("rent")) == "12000", (_fields(w2), res2.answer)


# ════════════════════════════════════════════════════════════════════
# B1 驗資料段（FA9 (h)、(m)、(t)）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("message,segment,ok", [
    ("1500 3q", "1500", True),                       # (m) 空白算邊界
    ("租金 15000", "租金 1500", False),               # (h) 切斷數字
    ("租金 15000", "1500", False),
    ("期限 2026/11/15", "期限 2026/11/1", False),     # (h) 日期切斷
    ("期限 2026/11/15", "2026/11/15", True),
    ("水電費 3q", "水電費 3", False),                  # 切斷 ASCII 英數「3q」
    ("水電費3q", "水電費", True),                      # 中文與英數相鄰不算切斷
    ("和平小屋abc", "和平小屋ab", False),
    ("水電費，1500", "水電費，1500", True),
    ("水電費　3q", "水 電 費", True),                  # 去空白後比（U+3000 也是空白）
    ("水電費 3q", "冷氣", False),
    ("1500 跟 15000", "1500", True),                  # 出現多次：任一處成立即可
    ("15000 跟 1500", "1500", True),
    ("水電費", "   ", False),                         # 空段（由呼叫端略過，不算成立）
])
def test_fa9_h_m_locate_boundaries(message, segment, ok):
    """B1：子字串（去空白）＋原句起訖不切斷數字／ASCII 英數。"""
    span = _fill_locate(message, segment)
    assert (span is not None) is ok, (message, segment, span)
    if span is not None:
        assert "".join(message[span[0]:span[1]].split()) == "".join(segment.split())


async def test_fa9_h_cut_number_segment_means_unknown_and_value_not_merged(api):
    """FA9 (h)：原話「租金 15000」、資料段「租金 1500」⇒ 資料段未知、1500（與 15000）都不進草稿；程式追問。
    修復輪 3：本片只在單欄追問回合生效 ⇒ 改成追問租金的回合（原為第一句建物件）。"""
    w = _World()
    _seed_draft(w, EST, {"title": "測試新物件乙"}, asked=["rent"])
    # 意圖值用原話裡的 15000（過得了現行值閘 (i)），才驗得到資料段切斷 ⇒ 未知（1500 本身已被 (i) 擋）。
    res = await w.turn("租金 15000", intents=[_fi(EST, data=["租金 1500"], answer="1500", rent="15000")])
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert w.draft() is not None and w.draft()["action"] == EST
    assert "rent" not in _fields(w) and _fields(w).get("title") == "測試新物件乙"
    assert res.outcome["state"] == "clarifying" and res.trace.pending_id is None


async def test_fa9_h_cut_date_segment_means_unknown(api):
    """FA9 (h)：日期「2026/11/15」切成「2026/11/1」⇒ 資料段未知、期限不進草稿。"""
    w = _World()
    _seed_draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費", "total": 1000}, asked=["date_expire"])
    res = await w.turn("期限 2026/11/15", intents=[_fi(MB, data=["期限 2026/11/1"], answer="2026/11/1",
                                                     date_expire="2026/11/15")])
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert "date_expire" not in _fields(w)


async def test_fa9_t_empty_segments_skipped_and_value_across_segments_rejected(api):
    """FA9 (t)：空字串段、全空白段略過（不算不成立）；值橫跨兩段 ⇒ 拒收（逐段比，⛔ 串接）。修復輪 3：改在追問帳單項目
    的單欄追問回合（本片只在這種回合生效）。"""
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    msg = "水電 費用 3q"
    rt, acc, _kw = _direct(w, draft, msg, asked=["title"],
                           obj={"action": "none", "fields": [], WF.ANSWER_TEXT_KEY: "",
                                WF.DATA_TEXTS_KEY: ["", "   ", "水電", "費用"]})
    assert acc.write_draft.fill_data == ["水電", "費用"]
    value, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "title"), "水電 費用")
    assert value is None and dropped is False
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in acc.violations
    value2, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "title"), "水電")
    assert value2 == "水電"


async def test_fa9_t_two_asked_fields_do_not_use_answer_text(api):
    """FA9 (t)：同時追問兩欄 ⇒ 不用 `answer_text` 填（整句填入只在恰好追問一欄時）。修復輪 3：多欄追問回合本片不生效
    （＝off）⇒ 也沒有任何 `fill_` 標記。"""
    w = _World()
    _seed_draft(w, MB, {"contract_ref": CONTRACT, "total": 1000}, asked=["title", "sub_title"])
    res = await w.turn("水電費 3q", script=[_out("好的")], intents=[_fi(MB, data=["水電費"], answer="水電費")])
    assert WF.V_ANSWER_FILLED not in _v(res) and WF.V_FILL_ANSWER_SEGMENT not in _v(res)
    assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
    assert "title" not in _fields(w) and "sub_title" not in _fields(w)


# ════════════════════════════════════════════════════════════════════
# B4 只填答覆（FA9 (c)、(m)）
# ════════════════════════════════════════════════════════════════════
async def test_fa9_c_answer_segment_only_other_field_via_intent(api):
    """FA9 (c)：「水電費，1500」＋意圖沒回追問欄 ⇒ 追問欄（帳單項目）＝答覆段「水電費」、不含「1500」；
    1500 只經意圖值進 `total`。"""
    w = _World()
    _seed_bill_asking_title(w)
    res = await w.turn("水電費，1500", intents=[_fi(MB, data=["水電費，1500"], answer="水電費", total="1500")])
    assert WF.V_FILL_ANSWER_SEGMENT in _v(res), _v(res)
    f = _fields(w)
    assert f.get("title") == "水電費" or "帳單項目：水電費" in res.answer
    assert "1500" not in str(f.get("title"))
    assert f.get("total") == "1500" or "1,500" in res.answer or "1500" in res.answer


async def test_fa9_m_number_next_to_thanks_fills_the_number(api):
    """FA9 (m)：追問金額、「1500 3q」、資料段「1500」⇒ 成立、金額填 1500。"""
    w = _World()
    _seed_draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費"}, asked=["total"])
    res = await w.turn("1500 3q", intents=[_fi(MB, data=["1500"], answer="1500", total="1500")])
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in _v(res) and WF.V_FILL_VALUE_OUTSIDE_DATA not in _v(res)
    assert _fields(w).get("total") == "1500"


async def test_fa9_m_answer_with_ideographic_space_fills_original_chars(api):
    """FA9 (m)：模型回的答覆段含 U+3000（原句沒有）⇒ 卡上是原句原字「水電費」（⛔ 模型字串）。"""
    w = _World()
    _seed_bill_asking_title(w, total=1000)
    res = await w.turn("水電費 3q", intents=[_fi(MB, data=["水電費"], answer="水電　費")])
    assert WF.V_FILL_ANSWER_SEGMENT in _v(res), _v(res)
    title = _fields(w).get("title")
    if title is None:                                   # 草稿已出卡：看卡上
        assert "帳單項目：水電費" in res.answer and "　" not in res.answer
    else:
        assert title == "水電費"


async def test_fa9_m_answer_longer_than_max_len_is_rejected(api):
    """FA9 (m)：答覆段超過 `value_max_len` ⇒ 拒收（⛔ 截斷）、追問欄不填、程式重問。"""
    f = _field(REPAIR, "description")
    long_text = "冷" * (WF.value_max_len(f) + 5)
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn(f"{long_text} 3q", intents=[_fi(REPAIR, data=[long_text], answer=long_text)])
    assert "description" not in _fields(w)
    _assert_reasked(res, "問題描述")


async def test_fa9_m_thanks_after_text_answer_fills_only_the_answer(api):
    """FA9 (m)／業主例：追問帳單項目「水電費 3q」⇒ 只填「水電費」；金額不出現從「3q」衍生的 3。"""
    w = _World()
    _seed_bill_asking_title(w, total=1000)
    res = await w.turn("水電費 3q", intents=[_fi(MB, data=["水電費"], answer="水電費", title="水電費 3q",
                                                total="3")])
    f = _fields(w)
    assert f.get("total") == "1000", f
    assert f.get("title") == "水電費" or "帳單項目：水電費" in res.answer
    assert "3q" not in str(f.get("title")) and "3q" not in res.answer


# ════════════════════════════════════════════════════════════════════
# B2 資料段未知 ＋ B6 重問（FA9 (a)、(b)、(j)、(p)）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("case", ["timeout", "unparsed", "not_in_message"])
async def test_fa9_a_failures_do_not_fill_whole_sentence_and_program_reasks(api, monkeypatch, case):
    """FA9 (a)：意圖呼叫逾時、解析失敗、資料段不在原話裡 ⇒ 追問欄不填、⛔ 整句填入，程式重問（B6）。"""
    script: list = []
    if case == "timeout":
        _patch_intent_timeout(monkeypatch)
        intents = [_hang]
        script = [_out("主模型的回答")]
    elif case == "unparsed":
        intents = ["不是 JSON"]
    else:
        intents = [_fi(REPAIR, data=["冷氣壞了"], answer="冷氣壞了", description="冷氣不冷 3q")]
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", script=script, intents=intents)
    assert "description" not in _fields(w)
    assert WF.V_FILL_REASK in _v(res), _v(res)
    _assert_reasked(res, "問題描述")


async def test_fa9_b_unknown_data_and_model_proposal_total_3_keeps_filled_total(api, monkeypatch):
    """FA9 (b)：資料段未知（意圖逾時、提議比意圖先到）＋模型自呼提議 `total=3`（「水電費 3q」）⇒ 已填 `total` 不變，
    帳單項目也不收「水電費 3q」。"""
    _patch_intent_timeout(monkeypatch)
    w = _World()
    _seed_bill_asking_title(w, total=1500)
    res = await w.turn("水電費 3q", intents=[_hang], script=[
        _proposal({"action": MB, "contract_ref": CONTRACT, "title": "水電費 3q", "total": 3}),
        _out("主模型的回答")])
    f = _fields(w)
    assert f.get("total") == "1500", f
    assert "3q" not in str(f.get("title"))
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert res.trace.pending_id is None or "3q" not in res.answer


def _j_intents(case: str):
    return {
        "exception": [_boom],
        "unparsed": ["不是 JSON"],
        "ambiguous": ['{"action":"repair_create","fields":[]}{"action":"contract_create","fields":[]}'],
        "out_of_domain": [_fi("fly_to_moon", data=["冷氣不冷"], answer="冷氣不冷")],
        "out_of_domain_key": [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷", bill_id="1")],
        "none_invalid_keys": [_fi("none", data="冷氣不冷", answer=None)],
    }[case]


@pytest.mark.parametrize("case", ["exception", "unparsed", "ambiguous", "out_of_domain", "out_of_domain_key",
                                  "none_invalid_keys"])
async def test_fa9_j_followup_intent_failures_reask_without_merging(api, case):
    """FA9 (j)：追問回合意圖例外、無法解析、ambiguous、值域外、`action=none` 而兩鍵無效 ⇒ 不整句填入、不併新值、程式重問。"""
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=_j_intents(case))
    assert "description" not in _fields(w), (_fields(w), _v(res), res.answer)
    assert WF.V_FILL_REASK in _v(res), _v(res)
    _assert_reasked(res, "問題描述")


async def test_fa9_j_followup_timeout_reasks(api, monkeypatch):
    """FA9 (j)：追問回合意圖逾時 ⇒ 同上（主模型照叫，回合結尾由程式重問）。"""
    _patch_intent_timeout(monkeypatch)
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=[_hang], script=[_out("主模型的回答")])
    assert "description" not in _fields(w)
    _assert_reasked(res, "問題描述")


async def test_fa9_j_followup_proposal_of_another_action_without_intent_reasks(api, monkeypatch):
    """FA9 (j)：主模型提議帶另一動作、意圖未確認（逾時）⇒ 資料段未知：提議值不併、追問欄不填、⛔ 出卡。"""
    _patch_intent_timeout(monkeypatch)
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=[_hang], script=[
        _proposal({"action": MB, "contract_ref": CONTRACT, "title": "冷氣不冷 3q", "total": 3}),
        _out("主模型的回答")])
    assert WF.V_ANSWER_FILLED not in _v(res)
    assert res.trace.pending_id is None, res.answer
    assert (w.draft() or {}).get("fields", {}).get("total") is None
    assert "description" not in _fields(w) or w.draft()["action"] != REPAIR


async def test_fa9_j_none_with_valid_keys_uses_the_data(api):
    """FA9 (j) 正對照：`action=none` 而兩鍵有效 ⇒ 照資料段處理（追問欄填答覆段「冷氣不冷」）。"""
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=[_fi("none", data=["冷氣不冷"], answer="冷氣不冷")])
    assert WF.V_FILL_ANSWER_SEGMENT in _v(res), _v(res)
    assert _fields(w).get("description") == "冷氣不冷" or "問題描述：冷氣不冷" in res.answer
    assert "3q" not in res.answer


@pytest.mark.parametrize("data", [None, _NO])
async def test_fa9_p_first_sentence_without_data_still_creates_draft_and_asks(api, monkeypatch, data):
    """FA9 (p)：第一句（非追問）意圖動作有效、資料段為 `None`（null 或鍵缺）⇒ 草稿照建、程式追問缺欄。
    修復輪 3（業主 10-27「縮小到追問回合」）：第一句本片不生效 ⇒ 與 off 相同（意圖值照現行值閘併入，
    「水電費 3q」、金額 3 照收——業主接受的代價），沒有任何 `fill_` 標記。下一片起由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    seen = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        res = await w.turn("幫我開一張帳單，水電費 3q", intents=[_fi(MB, data=data, title="水電費 3q", total="3")])
        assert w.draft() is not None and w.draft()["action"] == MB
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        assert res.outcome["state"] == "clarifying" and res.trace.pending_id is None
        seen.append((res.answer, _fields(w), list(_v(res))))
    assert seen[0] == seen[1]
    assert seen[1][1] == {"title": "水電費 3q", "total": "3"}, seen[1][1]


@pytest.mark.parametrize("with_proposal", [False, True])
async def test_fa9_p_first_sentence_whole_intent_none_timeout(api, monkeypatch, with_proposal):
    """FA9 (p)（主會話 10-27 補）：第一句整個意圖回 `None`（逾時）⇒ ①～⑥ 不併新值、⛔ 整句填入、⛔ 出卡。
    主模型另自呼提議帶值（③）時同樣不併。草稿建不建照現行程式（實測後寫死）：沒有提議 ⇒ 不建草稿、回主模型的回答；
    有提議 ⇒ 由提議建帳單草稿。修復輪 3（業主 10-27「縮小到追問回合」）：第一句本片不生效 ⇒ 與 off 相同：有提議時
    提議值照現行值閘併入（「水電費 3q」、金額 3——業主接受的代價），程式追問其餘缺欄（合約、繳費期限）；
    沒有任何 `fill_` 標記。下一片起由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    _patch_intent_timeout(monkeypatch)
    seen = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        msg = "幫我開一張帳單，水電費 3q"
        script = [_out("主模型的回答")]
        if with_proposal:
            script = [_proposal({"action": MB, "contract_ref": CONTRACT, "title": "水電費 3q", "total": 3}),
                      *script]
        res = await w.turn(msg, intents=[_hang], script=script)
        d = w.draft()
        if with_proposal:
            assert d is not None and d["action"] == MB, d
            assert _fields(w) == {"title": "水電費 3q", "total": "3"}, d
            assert res.outcome["state"] == "clarifying"
            for label in ("合約", "繳費期限"):
                assert label in res.answer, res.answer
        else:
            assert d is None, d
            assert res.answer == "主模型的回答", res.answer
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        assert WF.V_ANSWER_FILLED not in _v(res)
        assert res.trace.pending_id is None, res.answer
        seen.append((res.answer, _fields(w), list(_v(res))))
    assert seen[0] == seen[1]


# ════════════════════════════════════════════════════════════════════
# B3 兩道都要過（FA9 (d)、(f)、(l)、(o)、(q)）
# ════════════════════════════════════════════════════════════════════
async def test_fa9_d_earlier_turn_number_does_not_leak_into_this_turn(api):
    """FA9 (d)：先前回合含「3」（「3 月份」）＋本回合「水電費 3q」⇒ `3` 不進任何欄（(i) 過得了前文，(iii) 擋下）。"""
    w = _World()
    _seed_bill_asking_title(w)
    w.state["agent"]["dialog"] = [{"role": "user", "content": "3 月份的帳單"},
                                  {"role": "assistant", "content": "好的。"}]
    res = await w.turn("水電費 3q", intents=[_fi(MB, data=["水電費"], answer="水電費", total="3", sub_title="3")])
    f = _fields(w)
    assert f.get("total") is None and f.get("sub_title") is None, f
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res)
    assert f.get("title") == "水電費" or "帳單項目：水電費" in res.answer


async def test_fa9_f_restated_same_value_kept_and_not_counted_as_dropped(api):
    """FA9 (f)：本回合重述與草稿現值相同的值（「1,200」對現值 1200）⇒ 草稿不變、不記值被丟——資料段未知、資料段外
    都一樣（同值例外）。"""
    w = _World()
    for obj in ({"action": "none", "fields": []},                                # 資料段未知
                {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: []},         # 空陣列
                {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["水電費"]}):  # 資料段外
        draft = _draft(w, MB, {"contract_ref": CONTRACT, "total": 1200})
        rt, acc, _kw = _direct(w, draft, "水電費 1,200", asked=["title"], obj=obj)
        value, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "1,200",
                                                         from_intent=True)
        assert value == "1200" and dropped is False
        assert acc.write_draft.user_value_dropped is False
        assert WF.V_FILL_VALUE_OUTSIDE_DATA not in acc.violations
        assert acc.write_draft.fill_not_applied is False


async def test_fa9_l_same_value_side_effects_equal_pre_change(api, monkeypatch):
    """FA9 (l)：(ii) 同值重述的 `provided`／`touched`／`merged` 與改前（off）同值重併相同。"""
    obj = {"action": MB, "fields": [{"key": "total", "value": "1,200"}], WF.DATA_TEXTS_KEY: []}
    out = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        draft = _draft(w, MB, {"contract_ref": CONTRACT, "total": 1200})
        rt, acc, _kw = _direct(w, draft, "水電費 1,200", asked=["title"], obj=obj)
        provided = await rt._write_draft_merge_intent(acc, w.ident, {}, WriteIntent.model_validate(obj))
        wd = acc.write_draft
        out.append((provided, set(wd.touched), wd.merged, wd.user_value_dropped, dict(wd.draft["fields"])))
    assert out[0] == out[1]
    assert out[1][0] == {"total"} and out[1][4]["total"] == "1200"


async def test_fa9_o_first_sentence_two_segments_name_without_thanks(api):
    """FA9 (o)：「叫和平小屋 3q，在台北市大安區」、資料段兩段 ⇒ 物件名稱不含「3q」，其餘欄（縣市、區）照填。
    正對照：模型回「和平小屋」⇒ 填「和平小屋」。修復輪 3（業主 10-27「縮小到追問回合」）：原為第一句建物件；第一句
    本片不生效 ⇒ 改成追問物件名稱（單欄）的回合。"""
    msg = "叫和平小屋 3q，在台北市大安區"
    data = ["叫和平小屋", "在台北市大安區"]
    w = _World()
    _seed_draft(w, EST, {}, asked=["title"])
    res = await w.turn(msg, intents=[_fi(EST, data=data, answer="和平小屋", title="和平小屋 3q", city="台北市",
                                         district="大安區")])
    f = _fields(w)
    assert "3q" not in str(f.get("title")) and "3q" not in res.answer, (f, res.answer)
    assert f.get("city") == "台北市" and f.get("district") == "大安區", f
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res)

    w2 = _World()
    _seed_draft(w2, EST, {}, asked=["title"])
    await w2.turn(msg, intents=[_fi(EST, data=data, answer="和平小屋", title="和平小屋", city="台北市",
                                    district="大安區")])
    assert _fields(w2).get("title") == "和平小屋"


@pytest.mark.parametrize("message", ["謝謝", "OK 3q"])
async def test_fa9_q_empty_data_merges_nothing_including_enum_and_category(api, message):
    """FA9 (q)：資料段空陣列 ⇒ 不併任何新值，enum／category 也不併（`repair_create` 追問中、意圖帶 `emergency_status`
    與分類標籤 ⇒ 兩欄不變；業主 10-27 裁 C1 (a)）；追問欄不填、程式重問。"""
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn(message, intents=[_fi(REPAIR, data=[], answer="", emergency_status="1",
                                             category_name="家電維修", description=message)])
    f = _fields(w)
    assert "emergency_status" not in f and "category_name" not in f and "description" not in f, f
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in _v(res)
    _assert_reasked(res, "問題描述")


async def test_fa9_q_empty_data_on_name_question(api):
    """FA9 (q)：追問物件名稱欄時回「OK 3q」、資料段空陣列 ⇒ 名稱不併（「3q」不成為物件名稱）。"""
    w = _World()
    _seed_draft(w, EST, {"city": "台北市"}, asked=["title"])
    res = await w.turn("OK 3q", intents=[_fi(EST, data=[], answer="", title="3q")])
    assert "title" not in _fields(w)
    assert "3q" not in res.answer


# ════════════════════════════════════════════════════════════════════
# B5 追問回合已填欄不覆寫（FA9 (g)、(s)）
# ════════════════════════════════════════════════════════════════════
async def test_b5_followup_turn_does_not_overwrite_filled_non_asked_field(api):
    """B5：追問回合（問帳單項目）已填的金額，意圖帶新金額（在資料段內）⇒ 不覆寫、記 `fill_filled_field_kept`。
    非追問寫入回合（卡後補充、第一句）照現行覆寫（由 FA9 (r) 的正對照與 (o) 涵蓋）。"""
    w = _World()
    _seed_bill_asking_title(w, total=1000)
    res = await w.turn("水電費 2000", intents=[_fi(MB, data=["水電費 2000"], answer="水電費", total="2000")])
    assert _fields(w).get("total") == "1000" or "1,000" in res.answer
    assert WF.V_FILL_FILLED_FIELD_KEPT in _v(res)


async def test_fa9_g_candidate_bound_field_follows_name_rule_not_b5(api):
    """FA9 (g)：追問回合裡，候選集綁定那一欄（物件名稱）經 ③／④ 改講新名稱 ⇒ ⛔ 套 B5，照 F12 名稱規則（同 ⑤ 的處理：
    值在資料段內 ⇒ 過閘）；非綁定的已填欄同一回合才套 B5。"""
    w = _World()
    msg = f"改成 {STUDENT_ESTATE}"
    for site, from_intent in (("site3", False), ("site4", False), ("site5", True)):
        draft = _draft(w, REPAIR, {"estate_name": "舊物件名", "category_name": "家電維修"})
        rt, acc, _kw = _direct(w, draft, msg, asked=["description"],
                               obj={"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [msg],
                                    WF.ANSWER_TEXT_KEY: ""})
        acc.write_draft.candidates = {"field": "estate_name", "creator": "other"}
        value, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(REPAIR, "estate_name"),
                                                    STUDENT_ESTATE, from_intent=from_intent)
        assert value == STUDENT_ESTATE, site
        assert WF.V_FILL_FILLED_FIELD_KEPT not in acc.violations, site
    # 對照：同一回合、同樣已填但不是綁定欄 ⇒ B5 不覆寫
    acc.write_draft.candidates = None
    value, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(REPAIR, "estate_name"), STUDENT_ESTATE)
    assert value is None and WF.V_FILL_FILLED_FIELD_KEPT in acc.violations


async def test_fa9_s_replaced_draft_gets_no_b4_no_b5(api):
    """FA9 (s)：追問回合裡草稿被換成另一份（主模型提議另一動作 ③、缺欄寫點換草稿）⇒ 新草稿 B4 不填、B5 不套。"""
    w = _World()
    start = _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE})
    msg = "水電費 2000"
    rt, acc, _kw = _direct(w, start, msg, asked=["description"],
                           obj={"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [msg], WF.ANSWER_TEXT_KEY: msg})
    wd = acc.write_draft
    assert rt._fill_followup_now(wd) is True                                    # 前提：回合開始那份
    wd.draft = _draft(w, MB, {"contract_ref": CONTRACT, "total": 1000})         # 換草稿（③／缺欄寫點）
    assert rt._fill_followup_now(wd) is False
    value, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(MB, "total"), "2000", from_intent=True)
    assert value == "2000" and WF.V_FILL_FILLED_FIELD_KEPT not in acc.violations    # B5 不套
    wd.asked = ["title"]
    await rt._write_draft_fill_answer(acc, {}, msg, set())
    assert "title" not in wd.draft["fields"] and WF.V_ANSWER_FILLED not in acc.violations   # B4 不填


async def test_fa9_s_proposal_of_another_action_replaces_draft_full_turn(api, monkeypatch):
    """FA9 (s) 回合層：追問修繕問題描述時，主模型提議帳單（意圖已取用、資料段已知）⇒ 新草稿依非追問寫入回合處理：
    答覆段不填進新草稿、B5 不套（新草稿的值照資料段閘門合併）。"""
    async def _no_program_first(self, *a, **k):
        return None
    monkeypatch.setattr(AgentRuntime, "_write_draft_program_first", _no_program_first)
    w = _World()
    _seed_repair_asking_description(w)
    msg = "另外幫我開帳單，水電費 2000"
    res = await w.turn(msg, intents=[_fi("none", data=[msg], answer="")], script=[
        _proposal({"action": MB, "contract_ref": CONTRACT, "title": "水電費", "total": 2000}),
        _out("主模型的回答")])
    assert WF.V_FILL_FILLED_FIELD_KEPT not in _v(res), _v(res)
    assert WF.V_ANSWER_FILLED not in _v(res)
    d = w.draft() or {}
    if d.get("action") == MB:                       # 換成新草稿 ⇒ 答覆段（整句）沒有進新草稿任何欄
        assert msg not in d["fields"].values(), d
        assert not [k for k in d["fields"] if k not in ("contract_ref", "title", "total")], d
    else:                                            # 沒換成（提議比意圖先到 ⇒ 資料段未知）⇒ 追問欄也不填
        assert "description" not in d.get("fields", {}), d


# ════════════════════════════════════════════════════════════════════
# FA9 (i)：追問中改辦另一動作
# ════════════════════════════════════════════════════════════════════
async def test_fa9_i_switching_action_uses_data_as_non_followup(api):
    """FA9 (i)：追問帳單項目中改辦報修、意圖確認該動作 ⇒ 新草稿依非追問寫入回合處理（資料段照用、⛔ 答覆段填入）。"""
    w = _World()
    _seed_bill_asking_title(w, total=1000)
    msg = f"{STUDENT_ESTATE} 冷氣不冷 要報修"
    res = await w.turn(msg, intents=[_fi(REPAIR, data=[f"{STUDENT_ESTATE} 冷氣不冷"], answer="冷氣不冷",
                                         estate_name=STUDENT_ESTATE, description="冷氣不冷")])
    assert w.draft()["action"] == REPAIR
    assert WF.V_FILL_ANSWER_SEGMENT not in _v(res) and WF.V_FILL_FILLED_FIELD_KEPT not in _v(res)
    f = _fields(w)
    assert (f.get("estate_name"), f.get("description")) == (STUDENT_ESTATE, "冷氣不冷"), (f, res.answer)


# ════════════════════════════════════════════════════════════════════
# FA9 (e)：名稱路徑
# ════════════════════════════════════════════════════════════════════
async def test_fa9_e_name_question_thanks_not_in_name_via_intent(api):
    """FA9 (e)：追問物件名稱、「叫 學生獨立套房可租補 3q」⇒ 名稱欄不含「3q」（意圖回帶 3q 的名稱 ⇒ 資料段外拒收）。"""
    w = _World()
    _seed_draft(w, REPAIR, {"description": "冷氣不冷"}, asked=["estate_name"])
    msg = f"叫 {STUDENT_ESTATE} 3q"
    res = await w.turn(msg, intents=[_fi(REPAIR, data=[f"叫 {STUDENT_ESTATE}"], answer=STUDENT_ESTATE,
                                         estate_name=f"{STUDENT_ESTATE} 3q")])
    assert "3q" not in str(_fields(w).get("estate_name")) and "3q" not in res.answer


async def test_fa9_e_catch_name_writes_the_system_title(api):
    """FA9 (e)：單筆命中補名稱路徑（`_write_draft_catch_name`）：前置查詢恰好命中一列 ⇒ 名稱欄＝列上的系統正名
    （不含「3q」）。"""
    w = _World()
    msg = f"叫 {STUDENT_ESTATE} 3q"
    w.reg = _Reg(w.db, estates_override={msg: _unique_estate_hit(), f"{STUDENT_ESTATE} 3q": _unique_estate_hit(),
                                         STUDENT_ESTATE: _unique_estate_hit()})
    _seed_draft(w, REPAIR, {"description": "冷氣不冷"}, asked=["estate_name"])
    res = await w.turn(msg, intents=[_fi(REPAIR, data=[f"叫 {STUDENT_ESTATE}"], answer=STUDENT_ESTATE,
                                         estate_name=STUDENT_ESTATE)])
    name = _fields(w).get("estate_name")
    assert name in (None, STUDENT_ESTATE) and "3q" not in res.answer, (name, res.answer)


@pytest.mark.parametrize("raw,ok", [("和平小屋 3q", False), ("和平小屋", True)])
async def test_fa9_e_site5_apply_name_respects_data(api, raw, ok):
    """FA9 (e)／⑤ `_write_candidates_apply_name`（本回合改講新名稱）：名稱值在資料段內才寫進候選集那一欄。
    修復輪 3：本片只在單欄追問回合生效 ⇒ 改在追問問題描述的回合（草稿不含問題描述）。"""
    w = _World()
    msg = "改叫 和平小屋 3q"
    draft = _draft(w, REPAIR, {"estate_name": "舊物件名"})
    rt, acc, _kw = _direct(w, draft, msg, asked=["description"],
                           obj={"action": "none", "fields": [], WF.ANSWER_TEXT_KEY: "",
                                WF.DATA_TEXTS_KEY: ["改叫 和平小屋"]})
    acc.write_draft.candidates = {"field": "estate_name", "creator": "other"}
    state: dict = {}
    out = await rt._write_candidates_apply_name(acc, w.ident, state, _field(REPAIR, "estate_name"), "intent", raw)
    assert out is ok
    assert acc.write_draft.draft["fields"]["estate_name"] == ("和平小屋" if ok else "舊物件名")
    assert acc.write_draft.user_value_dropped is False


# ════════════════════════════════════════════════════════════════════
# 值閘呼叫點 ①～⑥（每點至少一條；④⑥ 直接呼叫）
# ════════════════════════════════════════════════════════════════════
def _calls_in(fn_name: str) -> set:
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == fn_name:
            return {sub.func.attr for sub in ast.walk(node)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)}
    raise AssertionError(f"{fn_name} 不存在")


SITES = ["_write_draft_merge_intent", "_write_draft_merge_model_confirm", "_write_proposal_merge",
         "_write_candidates_deferred_names", "_write_candidates_apply_name", "_write_candidates_replay_names"]


@pytest.mark.parametrize("fn", SITES, ids=["site1", "site2", "site3", "site4", "site5", "site6"])
def test_sites_1_to_6_all_use_the_turn_gate(fn):
    """§4.1 B「一個 helper、⛔ 各點各寫」：六個值閘呼叫點都呼叫 `_write_draft_turn_gate`，⛔ 直接呼叫改前值閘。"""
    calls = _calls_in(fn)
    assert "_write_draft_turn_gate" in calls and "_write_draft_gate_value" not in calls, (fn, calls)


def test_sites_value_gate_called_only_by_the_turn_gate():
    """正對照：`_write_draft_gate_value(` 只剩定義與 helper 內的呼叫（G6 原本是定義 1＋呼叫 6）。"""
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    owners = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute)
                   and s.func.attr == "_write_draft_gate_value" for s in ast.walk(node)):
                owners.append(node.name)
    assert sorted(set(owners)) == ["_write_draft_turn_gate"], owners


async def test_site1_merge_intent_rejects_value_outside_data(api):
    """①：意圖值不在資料段 ⇒ 不併（例：「水電費 3q」的 total=3）；在資料段 ⇒ 併。修復輪 3：本片只在單欄追問回合生效
    ⇒ 在追問帳單項目的回合測（以下 ②③ 同）。"""
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    obj = {"action": MB, "fields": [{"key": "total", "value": "3"}, {"key": "title", "value": "水電費"}],
           WF.DATA_TEXTS_KEY: ["水電費"], WF.ANSWER_TEXT_KEY: "水電費"}
    rt, acc, _kw = _direct(w, draft, "水電費 3q", asked=["title"], obj=obj)
    provided = await rt._write_draft_merge_intent(acc, w.ident, {}, WriteIntent.model_validate(obj))
    assert provided == {"title"}
    assert acc.write_draft.draft["fields"] == {"contract_ref": CONTRACT, "title": "水電費"}
    assert acc.write_draft.user_value_dropped is False                           # B2／B3 ⛔ 計入值被丟


async def test_site2_model_confirm_args_respect_data(api):
    """②：模型自呼 `confirm.request` 的參數（供之後回合用）同樣套 B2、B3：資料段外的 total=3 不併。"""
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    rt, acc, _kw = _direct(w, draft, "水電費 3q", asked=["title"],
                           obj={"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["水電費"],
                                WF.ANSWER_TEXT_KEY: "水電費"})
    args = {"summary": "確認", "payload": json.dumps({"action": MB, "contract_ref": CONTRACT, "title": "水電費",
                                                      "total": 3}, ensure_ascii=False)}
    await rt._write_draft_merge_model_confirm(acc, w.ident, {}, args)
    assert acc.write_draft.draft["fields"].get("total") is None
    assert acc.write_draft.draft["fields"].get("title") == "水電費"
    # 資料段未知 ⇒ 一律不併
    rt2, acc2, _ = _direct(w, _draft(w, MB, {"contract_ref": CONTRACT}), "水電費 3q", asked=["title"],
                           obj={"action": "none"})
    await rt2._write_draft_merge_model_confirm(acc2, w.ident, {}, args)
    assert "title" not in acc2.write_draft.draft["fields"] and "total" not in acc2.write_draft.draft["fields"]
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in acc2.violations


async def test_site3_proposal_before_intent_means_unknown(api):
    """③：提議在意圖結果取用前到（`intent_consumed=False`）⇒ 本回合資料段未知（之後讀到的資料段也不用）。"""
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    rt, acc, _kw = _direct(w, draft, "水電費 3q", asked=["title"], consumed=False)
    args = {"summary": "確認", "payload": json.dumps({"action": MB, "title": "水電費", "total": 3},
                                                      ensure_ascii=False)}
    await rt._write_proposal_merge(acc, w.ident, {}, args)
    wd = acc.write_draft
    assert wd.fill_proposal_first is True
    assert "title" not in wd.draft["fields"] and "total" not in wd.draft["fields"]
    rt._fill_read_data(wd, {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["水電費"]})
    assert wd.fill_data is None and rt._fill_data_unknown(wd)


async def test_site3_proposal_after_intent_respects_data(api):
    """③ 正對照：意圖已取用、資料段已知 ⇒ 提議值逐一過資料段（title 併、total=3 不併）。"""
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    rt, acc, _kw = _direct(w, draft, "水電費 3q", asked=["title"],
                           obj={"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["水電費"],
                                WF.ANSWER_TEXT_KEY: "水電費"})
    args = {"summary": "確認", "payload": json.dumps({"action": MB, "title": "水電費", "total": 3},
                                                      ensure_ascii=False)}
    await rt._write_proposal_merge(acc, w.ident, {}, args)
    assert acc.write_draft.draft["fields"].get("title") == "水電費"
    assert acc.write_draft.draft["fields"].get("total") is None


@pytest.mark.parametrize("obj,ok", [
    ({"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["和平小屋 冷氣不冷"], WF.ANSWER_TEXT_KEY: "和平小屋"}, True),
    ({"action": "none", "fields": []}, False),
    ({"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [], WF.ANSWER_TEXT_KEY: ""}, False),
])
async def test_site4_deferred_names_respect_data(api, obj, ok):
    """④ `_write_candidates_deferred_names`（③暫存的名稱值）：資料段內才併；未知、空陣列 ⇒ 不併。修復輪 3：本片只在
    單欄追問回合生效 ⇒ 在追問物件名稱的回合測（⑥ 同）。"""
    w = _World()
    draft = _draft(w, REPAIR, {"description": "冷氣不冷"})
    rt, acc, _kw = _direct(w, draft, "和平小屋 冷氣不冷 3q", asked=["estate_name"], obj=obj)
    acc.write_draft.deferred_names = [("estate_name", "和平小屋")]
    await rt._write_candidates_deferred_names(acc, w.ident, {})
    assert (acc.write_draft.draft["fields"].get("estate_name") == "和平小屋") is ok


@pytest.mark.parametrize("raw,current,obj,ok", [
    ("和平小屋", "和平小屋", {"action": "none", "fields": []}, True),                     # 同值例外（未知也照併）
    ("和平小屋", "舊名", {"action": "none", "fields": []}, False),                        # 未知 ⇒ 不併
    ("和平小屋", "舊名", {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: ["和平小屋"],
                         WF.ANSWER_TEXT_KEY: "和平小屋"}, True),
])
async def test_site6_replay_names_respect_data(api, monkeypatch, raw, current, obj, ok):
    """⑥ `_write_candidates_replay_names`（本回合收集的名稱值，規則判 `same`）：同值照併；資料段未知且值不同 ⇒ 不併。"""
    monkeypatch.setattr(AgentRuntime, "_write_candidates_name_rule", lambda self, *a, **k: "same")
    w = _World()
    draft = _draft(w, REPAIR, {"estate_name": current, "description": "冷氣不冷"})
    rt, acc, _kw = _direct(w, draft, "和平小屋 3q", asked=["estate_name"], obj=obj)
    acc.write_draft.collected_names = [("intent", raw)]
    await rt._write_candidates_replay_names(acc, w.ident, {}, _field(REPAIR, "estate_name"))
    assert (acc.write_draft.draft["fields"]["estate_name"] == raw) is ok
    assert ("estate_name" in acc.write_draft.touched) is ok


# ════════════════════════════════════════════════════════════════════
# FA9 (r)＋計畫 §10 待查 3：卡仍有效時的狀態句
# ════════════════════════════════════════════════════════════════════
MB_TEXT, MB_GOOD = GOOD[MB]


async def _bill_card(monkeypatch) -> _World:
    """開關 off 出一張帳單卡（改前路徑；假意圖不帶資料段），之後回合開關 on。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    res = await w.turn(MB_TEXT, intents=[_intent(MB, **{k: str(v) for k, v in MB_GOOD.items()})])
    assert res.outcome["state"] == "confirm_pending", res.answer
    monkeypatch.delenv(ENV, raising=False)
    return w


async def test_fa9_r_card_turn_timeout_proposal_new_amount_says_not_applied(api, monkeypatch):
    """FA9 (r)：卡後回合、意圖逾時、提議帶新金額＋舊值。修復輪 3（業主 10-27「縮小到追問回合」）：卡後打字回合本片
    不生效 ⇒ 與 off 相同：提議的新金額照現行值閘併入（2000），沒有任何 `fill_` 標記，⛔「這次的修改沒有套用…」。
    下一片起卡後回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    _patch_intent_timeout(monkeypatch)
    seen = []
    for value in ("off", "on"):
        w = await _bill_card(monkeypatch)
        monkeypatch.setenv(ENV, value)
        res = await w.turn("金額改成 2000", intents=[_hang], script=[
            _proposal({"action": MB, **MB_GOOD, "total": 2000}), _out("主模型的回答")])
        assert _fields(w).get("total") == "2000", (res.answer, _v(res))
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        assert WF.CARD_UNCHANGED_TEXT not in res.answer, res.answer
        seen.append((res.answer, res.outcome["state"], _fields(w), list(_v(res))))
    assert seen[0] == seen[1]


async def test_fa9_r_card_turn_outside_data_rejection_says_not_applied(api, monkeypatch):
    """FA9 (r)「(iii) 拒收時同」：卡後回合、意圖帶新金額但不在模型標的資料段內。修復輪 3：卡後打字回合本片不生效
    ⇒ 與 off 相同：資料段不送也不用、新金額照現行值閘併入（2000）、沒有任何 `fill_` 標記。下一片起卡後回合由
    `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off（on 的行為見 `test_fill_wide_req.py` FW11 (k)）。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    seen = []
    for value in ("off", "on"):
        w = await _bill_card(monkeypatch)
        monkeypatch.setenv(ENV, value)
        res = await w.turn("金額改一下 2000 3q", intents=[_fi(MB, data=["金額改一下"], total="2000")],
                           script=[_out("主模型的回答")])
        assert _fields(w).get("total") == "2000", (res.answer, _v(res))
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        assert WF.CARD_UNCHANGED_TEXT not in res.answer, res.answer
        seen.append((res.answer, res.outcome["state"], _fields(w), list(_v(res))))
    assert seen[0] == seen[1]


async def test_fa9_r_control_card_turn_in_data_reissues_new_amount(api, monkeypatch):
    """FA9 (r) 正對照：卡後補充、新金額在資料段內 ⇒ 照現行（非追問寫入回合）覆寫並重出卡。"""
    w = await _bill_card(monkeypatch)
    res = await w.turn("金額改成 2000 3q", intents=[_fi(MB, data=["金額改成 2000"], total="2000")])
    assert _fields(w).get("total") == "2000", (res.answer, _v(res))
    assert res.outcome["state"] == "confirm_pending"


def _status_head(answer: str) -> str:
    for lead in (WF.CARD_UNCHANGED_TEXT, WF.CARD_STILL_VALID_TEXT, WF.CARD_READ_SAME_LEAD):
        if answer.startswith(lead):
            return lead
    return answer[:20]


@pytest.mark.parametrize("message,raw_total,head", [
    ("金額 abc", "abc", WF.CARD_UNCHANGED_TEXT),          # 改前：值閘拒收、記值被丟 ⇒ 沒套用
    # 修復輪 4（brief-fix5）：同值重述 ⇒ 前導句 `CARD_READ_SAME_LEAD`（原 `CARD_STILL_VALID_TEXT`；on／off 皆同）
    ("金額 1,000 謝謝", "1,000", WF.CARD_READ_SAME_LEAD),
])
async def test_pending3_status_text_same_as_pre_change_when_data_is_valid(api, monkeypatch, message, raw_total,
                                                                          head):
    """計畫 §10 r3 待查 3：B2「⛔ 計入 `user_value_dropped`」不改變卡仍有效回合的狀態句——資料段有效時，同一回合
    on 與改前（off）的狀態句開頭相同（值閘拒收 ⇒ 都是「沒有套用」；同值重述 ⇒ 都是「卡片還在」）。"""
    heads = []
    for value in ("off", "on"):
        w = await _bill_card(monkeypatch)
        monkeypatch.setenv(ENV, value)
        data = [message.replace(" 謝謝", "")]
        res = await w.turn(message, intents=[_fi(MB, data=data, total=raw_total)], script=[_out("主模型的回答")])
        heads.append(_status_head(res.answer))
        assert _fields(w).get("total") == "1000"
    assert heads == [head, head], heads


async def test_pending3_unknown_data_with_only_same_values_same_as_pre_change(api, monkeypatch):
    """計畫 §10 r3 待查 3（主會話 10-27 裁：B2 旗標＝「至少一個與草稿現值不同的新值沒套用」）：卡後回合資料段未知、
    值全是同值重述 ⇒ 不設旗標，on 與改前（off）前導句相同。修復輪 4（brief-fix5）：該句由「卡片還在，請按確認。」
    改為 `CARD_READ_SAME_LEAD`（on／off 皆同）。"""
    heads = []
    for value in ("off", "on"):
        w = await _bill_card(monkeypatch)
        monkeypatch.setenv(ENV, value)
        res = await w.turn("金額 1,000", intents=[_fi(MB, total="1,000")], script=[_out("主模型的回答")])
        heads.append(_status_head(res.answer))
        assert _fields(w).get("total") == "1000"
        if value == "on":
            assert WF.V_FILL_DATA_TEXT_UNKNOWN not in _v(res), _v(res)     # 同值由 (ii) 照併，不走 B2
    assert heads == [WF.CARD_READ_SAME_LEAD, WF.CARD_READ_SAME_LEAD], heads


async def test_pending3_unknown_data_same_and_new_values_mixed_says_not_applied(api, monkeypatch):
    """待查 3：卡後回合（意圖不帶資料段）、同值（金額 1,000）與新值（帳單項目 水電費）混在一起。修復輪 3（業主 10-27
    「縮小到追問回合」）：卡後打字回合本片不生效 ⇒ 與 off 相同：新值照現行值閘併入（帳單項目改成水電費）、金額不變、
    沒有任何 `fill_` 標記，⛔「這次的修改沒有套用…」。下一片起卡後回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    seen = []
    for value in ("off", "on"):
        w = await _bill_card(monkeypatch)
        monkeypatch.setenv(ENV, value)
        res = await w.turn("金額 1,000 帳單項目 水電費", intents=[_fi(MB, total="1,000", title="水電費")],
                           script=[_out("主模型的回答")])
        assert _fields(w).get("total") == "1000" and _fields(w).get("title") == "水電費", _fields(w)
        assert not [m for m in _v(res) if str(m).startswith("fill_")], _v(res)
        assert _status_head(res.answer) != WF.CARD_UNCHANGED_TEXT, res.answer
        seen.append((res.answer, res.outcome["state"], _fields(w), list(_v(res))))
    assert seen[0] == seen[1]


# ════════════════════════════════════════════════════════════════════
# FA9 (n)／B7：資料段只活在本回合
# ════════════════════════════════════════════════════════════════════
async def test_fa9_n_data_and_answer_strings_do_not_leave_the_turn(api, monkeypatch, caplog):
    """FA9 (n)：資料段與答覆段字串不出現在 `agent_state`（對話紀錄本來就存的原句除外）、草稿、trace、決策快照、日誌與
    violation 字串；回合內欄位名與兩個鍵名也不落地。"""
    captured: list = []
    real = usage_metering.set_agent_decision
    monkeypatch.setattr(usage_metering, "set_agent_decision", lambda d: (captured.append(copy.deepcopy(d)), real(d)))
    caplog.set_level(logging.DEBUG)
    seg = "冷氣不冷，順便看濾網"
    answer = "冷氣不冷，順便看"
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn(f"{seg} 3q", intents=[_fi(REPAIR, data=[seg], answer=answer)])
    assert WF.V_FILL_ANSWER_SEGMENT in _v(res)
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
        for key in (WF.DATA_TEXTS_KEY, WF.ANSWER_TEXT_KEY, "fill_data", "fill_answer", "fill_start_fields",
                    "fill_asked_labels"):
            assert f'"{key}"' not in blob and f"'{key}'" not in blob, (where, key)
    # 正對照：答覆段原字照規格進了草稿（證明掃描的是有內容的狀態）
    assert answer in blobs["agent_state"]
    fill_marks = {m for m in _v(res) if str(m).startswith("fill_")}
    assert fill_marks <= {WF.V_FILL_DATA_TEXT_UNKNOWN, WF.V_FILL_VALUE_OUTSIDE_DATA, WF.V_FILL_FILLED_FIELD_KEPT,
                          WF.V_FILL_ANSWER_SEGMENT, WF.V_FILL_REASK}, fill_marks


def test_fa9_n_new_violation_constants_are_fixed_strings():
    """B7：新 violation 一律固定字串（⛔ 帶值、⛔ 格式化）。"""
    for name in ("V_FILL_DATA_TEXT_UNKNOWN", "V_FILL_VALUE_OUTSIDE_DATA", "V_FILL_FILLED_FIELD_KEPT",
                 "V_FILL_ANSWER_SEGMENT", "V_FILL_REASK"):
        value = getattr(WF, name)
        assert isinstance(value, str) and value.isascii() and "{" not in value and ":" not in value
    src = RUNTIME_PATH.read_text(encoding="utf-8")
    assert "V_FILL_" in src
    for line in src.splitlines():
        if "V_FILL_" in line and ("f\"" in line or ".format(" in line):
            raise AssertionError(line)


# ════════════════════════════════════════════════════════════════════
# E 片標籤 `none` 也改走 B（§4.1 末段）；DSP-091：⛔ 詞表
# ════════════════════════════════════════════════════════════════════
async def test_e_label_none_goes_through_b_not_whole_sentence(api):
    """E 片標籤 `none`（主模型替身的 DialogAct 呼叫一律回 none）⇒ 不再整句填，改走 B：只填答覆段。"""
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷 3q", intents=[_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
    assert "dialog_act_field_label:none" in _v(res), _v(res)                    # 前提：E 片標籤確實是 none
    assert WF.V_FILL_ANSWER_SEGMENT in _v(res)
    assert _fields(w).get("description") == "冷氣不冷" or "問題描述：冷氣不冷" in res.answer
    assert "3q" not in res.answer


def _new_functions() -> list:
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    names = {"_fill_begin_intent_call", "_fill_read_data", "_write_draft_turn_gate", "_fill_reask_if_missing",
             "_fill_followup_now", "_fill_data_unknown", "_fill_value_not_applied", "_fill_locate", "_fill_cuts",
             "_fill_intent_in_domain"}
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]


def test_dsp091_new_code_has_no_chinese_keyword_matching():
    """DSP-091／AR5：本片新程式 ⛔ 以道謝或寒暄的詞表判斷——新函式內沒有任何含中文的字串常數（docstring 除外）。"""
    fns = _new_functions()
    assert len(fns) == 10, [f.name for f in fns]
    for fn in fns:
        body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                               and isinstance(getattr(fn.body[0], "value", None), ast.Constant)) else fn.body
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert not any("一" <= ch <= "鿿" for ch in node.value), (fn.name, node.value)
                    assert node.value.lower() not in {"3q", "thx", "thanks", "ok", "謝謝"}, (fn.name, node.value)


# ════════════════════════════════════════════════════════════════════
# 修復輪 1（`~/jgb-archive/arch-step3-20261018/fill/brief-fix1.md`）
# RC2：資料段裡完全不在最新一句的段（AI 把前面回合的話抄進來）⇒ 略過該段，不讓整回合「資料段未知」。
# 重現：改後量測 E14 post_fill「冷氣不冷」「清潔費」（`fill/x5/E14/records.jsonl`）；主會話探針 probe4 6 次中 3 次回
# `data_texts: ["學生獨立套房可租補", "冷氣不冷"]`。
# ════════════════════════════════════════════════════════════════════
PRIOR_ESTATE_DIALOG = [{"role": "user", "content": "能幫我新增一張修繕單嗎"},
                       {"role": "assistant", "content": "要完成這筆建立，還需要：物件、問題描述。"},
                       {"role": "user", "content": STUDENT_ESTATE},
                       {"role": "assistant", "content": "要完成這筆建立，還需要：問題描述。"}]


async def test_rc2_a_prior_turn_estate_in_data_is_skipped_and_answer_filled(api):
    """RC2 (a)：追問「問題描述」、前一句講過物件、這句只回「冷氣不冷」、AI 回 `data_texts=[物件名, 冷氣不冷]` ⇒
    物件名那段略過（記 `fill_segment_not_in_message`）、`fill_data == ["冷氣不冷"]`、答覆段填入、不重問。"""
    w = _World()
    draft = _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE})
    obj = {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [STUDENT_ESTATE, "冷氣不冷"],
           WF.ANSWER_TEXT_KEY: "冷氣不冷"}
    rt, acc, _kw = _direct(w, draft, "冷氣不冷", asked=["description"], obj=None, prior=(STUDENT_ESTATE,))
    rt._fill_read_data(acc.write_draft, obj, acc.violations)
    assert acc.write_draft.fill_data == ["冷氣不冷"]
    assert acc.write_draft.fill_answer == "冷氣不冷"
    assert not rt._fill_data_unknown(acc.write_draft)
    assert acc.violations.count(WF.V_FILL_SEGMENT_NOT_IN_MESSAGE) == 1

    # 回合層：同一情境實跑 ⇒ 問題描述＝「冷氣不冷」、⛔ 資料段未知、⛔ 重問
    w2 = _World()
    _seed_repair_asking_description(w2)
    w2.state["agent"]["dialog"] = copy.deepcopy(PRIOR_ESTATE_DIALOG)
    res = await w2.turn("冷氣不冷", intents=[_fi(REPAIR, data=[STUDENT_ESTATE, "冷氣不冷"], answer="冷氣不冷",
                                                 estate_name=STUDENT_ESTATE, description="冷氣不冷")])
    v = _v(res)
    assert WF.V_FILL_SEGMENT_NOT_IN_MESSAGE in v, v
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in v and WF.V_FILL_REASK not in v, v
    assert _fields(w2).get("description") == "冷氣不冷" or "問題描述：冷氣不冷" in res.answer, (res.answer, v)
    assert _fields(w2).get("estate_name") == STUDENT_ESTATE or STUDENT_ESTATE in res.answer


async def test_rc2_a_control_without_prior_segment_same_result(api):
    """RC2 (a) 正對照：AI 只回「冷氣不冷」一段 ⇒ 同樣填入，且 ⛔ 記 `fill_segment_not_in_message`（標記只在有段被略過時記）。"""
    w = _World()
    _seed_repair_asking_description(w)
    w.state["agent"]["dialog"] = copy.deepcopy(PRIOR_ESTATE_DIALOG)
    res = await w.turn("冷氣不冷", intents=[_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷", description="冷氣不冷")])
    assert WF.V_FILL_SEGMENT_NOT_IN_MESSAGE not in _v(res)
    assert _fields(w).get("description") == "冷氣不冷" or "問題描述：冷氣不冷" in res.answer


async def test_rc2_b_prior_turn_new_value_still_blocked(api):
    """RC2 (b)：前句講過金額（「金額 1200 元」），本句只回帳單項目「清潔費」，AI 把前句也列進資料段、意圖帶 total=1200
    ⇒ 前句那段略過；1200 不在留下的資料段 ⇒ (iii) 照舊拒收（`fill_value_outside_data`）、金額不進草稿；帳單項目照填。"""
    w = _World()
    _seed_bill_asking_title(w)
    w.state["agent"]["dialog"] = [{"role": "user", "content": "金額 1200 元"},
                                  {"role": "assistant", "content": "要完成這筆建立，還需要：帳單項目。"}]
    res = await w.turn("清潔費", intents=[_fi(MB, data=["金額 1200 元", "清潔費"], answer="清潔費",
                                              total="1200", title="清潔費")])
    v = _v(res)
    assert WF.V_FILL_SEGMENT_NOT_IN_MESSAGE in v and WF.V_FILL_VALUE_OUTSIDE_DATA in v, v
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in v, v
    f = _fields(w)
    assert f.get("total") is None, f
    assert f.get("title") == "清潔費" or "帳單項目：清潔費" in res.answer, (f, res.answer)


@pytest.mark.parametrize("data", [["租金 1500"], [STUDENT_ESTATE, "租金 1500"]])
async def test_rc2_c_segment_in_message_but_cutting_number_still_unknown(api, data):
    """RC2 (c)：段出現在最新一句、但起訖切斷數字（「15000」切成「1500」）⇒ 仍整回合未知（另有被略過的段也一樣）。
    修復輪 3：本片只在單欄追問回合生效 ⇒ 在追問租金的回合測。"""
    w = _World()
    draft = _draft(w, EST, {"title": "測試新物件乙"})
    rt, acc, _kw = _direct(w, draft, "租金 15000", asked=["rent"], prior=(STUDENT_ESTATE,))
    rt._fill_read_data(acc.write_draft, {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: data}, acc.violations)
    assert acc.write_draft.fill_data is None and rt._fill_data_unknown(acc.write_draft)
    value, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(EST, "rent"), "15000", from_intent=True)
    assert value is None and WF.V_FILL_DATA_TEXT_UNKNOWN in acc.violations


async def test_rc2_d_all_segments_skipped_means_empty_data_and_nothing_merged(api):
    """RC2 (d)：全部段都不在最新一句 ⇒ `fill_data == []`（B3 空陣列）：不併任何新值，含 enum（`emergency_status`）與
    text；記 `fill_segment_not_in_message`、`fill_value_outside_data`，⛔ 記資料段未知。"""
    w = _World()
    draft = _draft(w, REPAIR, {"estate_name": STUDENT_ESTATE})
    obj = {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [STUDENT_ESTATE, "冷氣壞了"], WF.ANSWER_TEXT_KEY: ""}
    rt, acc, _kw = _direct(w, draft, "好喔謝謝", asked=["description"], prior=(STUDENT_ESTATE, "冷氣壞了"))
    rt._fill_read_data(acc.write_draft, obj, acc.violations)
    assert acc.write_draft.fill_data == [] and acc.write_draft.fill_answer == ""
    for key, raw in (("emergency_status", "緊急"), ("description", "冷氣壞了")):
        value, dropped = await rt._write_draft_turn_gate(acc, w.ident, _field(REPAIR, key), raw, from_intent=True)
        assert value is None and dropped is False, key
    assert WF.V_FILL_SEGMENT_NOT_IN_MESSAGE in acc.violations
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in acc.violations
    assert WF.V_FILL_DATA_TEXT_UNKNOWN not in acc.violations

    # 回合層：意圖帶 enum 與 text 值 ⇒ 都不進草稿、追問欄不填、程式重問
    w2 = _World()
    _seed_repair_asking_description(w2)
    w2.state["agent"]["dialog"] = copy.deepcopy(PRIOR_ESTATE_DIALOG)
    res = await w2.turn("好喔謝謝", intents=[_fi(REPAIR, data=[STUDENT_ESTATE], answer="", emergency_status="緊急",
                                                  description="冷氣壞了")])
    f = _fields(w2)
    assert "emergency_status" not in f and "description" not in f, f
    assert WF.V_FILL_SEGMENT_NOT_IN_MESSAGE in _v(res)
    _assert_reasked(res, "問題描述")


async def test_rc2_e_answer_only_in_skipped_segment_means_unknown(api):
    """RC2 (e)：`answer_text` 只落在被略過的段（前句的物件名）⇒ 資料段未知（答覆段須落在留下來的資料段內）。"""
    w = _World()
    draft = _draft(w, REPAIR, {"description": "冷氣不冷"})
    obj = {"action": "none", "fields": [], WF.DATA_TEXTS_KEY: [STUDENT_ESTATE, "冷氣不冷"],
           WF.ANSWER_TEXT_KEY: STUDENT_ESTATE}
    rt, acc, _kw = _direct(w, draft, "冷氣不冷", asked=["estate_name"], prior=(STUDENT_ESTATE,))
    rt._fill_read_data(acc.write_draft, obj, acc.violations)
    assert acc.write_draft.fill_data is None and rt._fill_data_unknown(acc.write_draft)
    value, _d = await rt._write_draft_turn_gate(acc, w.ident, _field(REPAIR, "estate_name"), STUDENT_ESTATE,
                                                from_intent=True)
    assert value is None and WF.V_FILL_DATA_TEXT_UNKNOWN in acc.violations


def test_rc2_new_violation_is_a_fixed_string_and_exported():
    """B7：新 violation 固定字串（⛔ 帶值）、列在 `write_forms.__all__`。"""
    value = WF.V_FILL_SEGMENT_NOT_IN_MESSAGE
    assert value == "fill_segment_not_in_message"
    assert value.isascii() and "{" not in value and ":" not in value
    assert "V_FILL_SEGMENT_NOT_IN_MESSAGE" in WF.__all__


# ════════════════════════════════════════════════════════════════════
# 修復輪 1 RC3：B6 重問與 E 片程式出口（收尾／轉人）的先後。
# 對碼（`_run_model_loop`）：`_write_draft_program_first`（含 B6 `_fill_reask_if_missing`）先算出程式訊息，但**執行**
# 在 `while` 迴圈內；其間 `_dialog_act_pre_loop` 已先依標籤走 `_dialog_act_exit`，出口成立即結束回合。
# 送出成功（receipt）一律清草稿 ⇒ 完成後的道謝回合沒有草稿、不是追問回合，B6 不生效。
# ════════════════════════════════════════════════════════════════════
def _e_helpers():
    from tests.unit.agent import test_closing_handoff_e_req as E
    return E


async def _submitted_repair(monkeypatch) -> _World:
    """開關 off 出一張修繕卡並送出（寫 receipt）；之後回合由呼叫端設開關。"""
    monkeypatch.setenv(ENV, "off")
    w = _World()
    _res, pid = await w.repair_card()
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "confirmed", res.answer
    assert w.draft() is None                                   # 前提：送出成功即清草稿
    return w


@pytest.mark.parametrize("message", ["謝謝你，問題解決了", "ok了 解決了"])
async def test_rc3_thanks_after_completed_write_closes_same_on_and_off(api, monkeypatch, message):
    """RC3：寫入完成後道謝、E 片標籤 `resolved` ⇒ 程式收尾樣板、⛔ 重問；本片 on 與 off 結果相同。"""
    E = _e_helpers()
    out = []
    for value in ("off", "on"):
        w = await _submitted_repair(monkeypatch)
        monkeypatch.setenv(ENV, value)
        res, _p, _rt = await E._turn(w, message, act="resolved", intents=[_fi("none", data=[], answer="")])
        E._assert_program_closing(res)
        assert WF.V_FILL_REASK not in _v(res), _v(res)
        out.append((res.kind, res.answer, res.outcome["state"]))
    assert out[0] == out[1] and out[1][1] == WF.CLOSING_TEXT


async def test_rc3_wants_human_during_followup_hands_off_same_on_and_off(api, monkeypatch):
    """RC3：回合開始有 `asked` 非空草稿（追問問題描述）、E 片標籤 `wants_human` ⇒ 程式轉人（E-R1），B6 的重問 ⛔ 搶在
    前面；本片 on 與 off 結果相同。"""
    E = _e_helpers()
    out = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        _seed_repair_asking_description(w)
        res, _p, _rt = await E._turn(w, E.ASK_HUMAN, act="wants_human", intents=[_fi("none", data=[], answer="")])
        E._assert_program_handoff(res)
        assert WF.V_ANSWER_FILLED not in _v(res) and res.trace.pending_id is None
        assert "description" not in _fields(w)
        if value == "on":
            # 前提（證明情境鋪得出先後問題）：B6 本回合確實已設重問（程式訊息已算出），仍由 E 片出口結束回合。
            assert WF.V_FILL_REASK in _v(res), _v(res)
        out.append((res.kind, res.answer, res.outcome["state"], res.handoff["reason"]))
    assert out[0] == out[1]


async def test_rc3_thanks_mid_field_still_reasks_like_e14(api, monkeypatch):
    """RC3：填欄中道謝（追問問題描述、標籤 `resolved`、確認也 `resolved`）⇒ 照 E14 既有行為：`dialog_act_fill_skipped`、
    不填、不收尾（E-R3：草稿進行中）、依草稿重問缺欄；本片 on 與 off 回話相同。"""
    E = _e_helpers()
    out = []
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        _seed_repair_asking_description(w)
        res, _p, _rt = await E._turn(w, E.THANKS_MID_FIELD, act="resolved",
                                     intents=[_fi("none", data=[], answer="")])
        v = _v(res)
        assert WF.V_DIALOG_ACT_FILL_SKIPPED in v, v
        assert res.answer != WF.CLOSING_TEXT and WF.V_DIALOG_ACT_EXIT not in v
        assert "description" not in _fields(w) and w.draft()["fields"].get("estate_name") == STUDENT_ESTATE
        _assert_reasked(res, "問題描述")
        out.append((res.answer, res.outcome["state"]))
    assert out[0] == out[1]


# ════════════════════════════════════════════════════════════════════
# 修復輪 1 追加（RC1，業主 2026-10-27 裁示計畫 §6 第 8 點）：規則句點名常見網路／口語道謝
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix1b 指定的逐字段落（測試端獨立寫一份，⛔ 引用 `WF.DATA_TEXTS_RULE` 自證）。
RC1_THANKS_HINT = ("（道謝、客套也包括網路縮寫與口語，例如「3q」「thx」「麻煩囉」；它們常緊貼在資料前後、中間沒有標點，"
                   "仍要從那裡斷開、不算資料。）只抄最新這一句裡的字；前面回合講過的資料不要再列。")


async def test_rc1_thanks_hint_in_system_and_data_texts_description_on_only(api, monkeypatch):
    """RC1：`DATA_TEXTS_RULE` 末尾接上逐字段落 ⇒ on 的寫入回合送出的系統句與 `data_texts` 欄位 description 都含這段；
    off ⇒ 系統句與整份 schema 都不含（建構函式層與實際送出層各驗一次）。這些詞只在規則句，程式不拿來判斷（DSP-091）。"""
    assert WF.DATA_TEXTS_RULE.endswith(RC1_THANKS_HINT)
    for el in (True, False):
        on_sp = WF.write_intent_system_prompt(enum_labels=el, data_text=True)
        on_desc = WF.write_intent_call_schema(enum_labels=el, data_text=True)["properties"][WF.DATA_TEXTS_KEY]["description"]
        assert RC1_THANKS_HINT in on_sp and RC1_THANKS_HINT in on_desc
        assert RC1_THANKS_HINT not in WF.write_intent_system_prompt(enum_labels=el)
        assert RC1_THANKS_HINT not in json.dumps(WF.write_intent_call_schema(enum_labels=el), ensure_ascii=False)
    sent = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        _seed_repair_asking_description(w)
        provider = _Provider([], [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
        await w.runtime(provider).run_turn(w.ident, "冷氣不冷 3q", w.state)
        (kw,) = provider.intent_calls
        sent[value] = (_system(kw), _schema(kw))
    on_sys, on_schema = sent["on"]
    assert RC1_THANKS_HINT in on_sys
    assert RC1_THANKS_HINT in on_schema["properties"][WF.DATA_TEXTS_KEY]["description"]
    off_sys, off_schema = sent["off"]
    assert RC1_THANKS_HINT not in off_sys and WF.DATA_TEXTS_KEY not in off_schema["properties"]
    assert RC1_THANKS_HINT not in json.dumps(off_schema, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# 修復輪 1 追加 2（RC4，brief-fix1c）：合約鋪陳第 3 句日期、租金、Email 全沒進草稿
# ════════════════════════════════════════════════════════════════════
CC = "contract_create"
RC4_MSG = "2026年11月1日到2027年10月31日，月租12000元，承租人信箱 e-test-0@example.com"
RC4_SEGS = ["2026年11月1日到2027年10月31日", "月租12000元", "承租人信箱 e-test-0@example.com"]
RC4_VALUES = dict(date_start="2026-11-01", date_end="2027-10-31", rent="12000", to_user_email="e-test-0@example.com")
RC4_ESTATE = "基隆溫馨一人宅套房"          # fixture 內唯一命中（`name_early:one`），同 e/drive_e.py contract(1)


async def _rc4_after_name(w: _World) -> None:
    """鋪陳前兩句（同 `e/drive_e.py` 的 `contract(i)`）：第 1 句程式追問全部欄位；第 2 句講物件名稱（唯一命中）⇒ 程式
    追問其餘欄位（`asked` 多欄）。第 2 句的意圖帶有效答覆段（追問多欄時 `answer_text` 不用來填）。"""
    await w.turn("幫我建立一份新合約", intents=[_fi(CC, data=[])])
    await w.turn(f"物件是{RC4_ESTATE}", intents=[_fi(CC, data=[RC4_ESTATE], answer=RC4_ESTATE,
                                                   estate_name=RC4_ESTATE)])
    asked = w.draft()["asked"]
    assert len(asked) > 1 and "date_start" in asked, asked                 # 前提：第 3 句是追問多欄的回合


@pytest.mark.parametrize("answer", [RC4_MSG, _NO], ids=["answer_whole_sentence", "answer_key_missing"])
async def test_rc4_a_multi_asked_answer_text_invalid_keeps_data_segments(api, monkeypatch, answer):
    """RC4 形狀 A（直接呼叫 `_fill_read_data`）：追問 4 欄、`answer_text`＝整句（橫跨 3 段資料段）或鍵缺。
    修復輪 3（業主 10-27「縮小到追問回合」）：多欄追問回合本片不生效 ⇒ 建構點不帶本片參數（`{}`）、`fill_active` 為
    `False`、不讀資料段（`fill_data`／`fill_answer` 皆 `None`）＝off；本條原驗的「多欄時答覆段無效仍保留資料段」那條路徑
    在本範圍下不會走到。下一片起多欄回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    w = _World()
    draft = _draft(w, CC, {"estate_name": RC4_ESTATE})
    obj = {"action": CC, "fields": [], WF.DATA_TEXTS_KEY: RC4_SEGS}
    if answer is not _NO:
        obj[WF.ANSWER_TEXT_KEY] = answer
    _rt, acc, kw = _direct(w, draft, RC4_MSG, asked=["date_start", "date_end", "rent", "to_user_email"], obj=obj)
    assert kw == {} and acc.write_draft.fill_active is False
    assert acc.write_draft.fill_data is None
    assert acc.write_draft.fill_answer is None


async def test_rc4_a_multi_asked_whole_sentence_answer_merges_dates_rent_email_same_as_off(api, monkeypatch):
    """RC4 形狀 A（整回合，重現 `e/drive_e.py` contract(1)）：名稱收下、程式追問其餘欄 ⇒ 第 3 句 AI 的 `answer_text` 回整句
    ⇒ 日期、租金、Email 照併（⛔ `fill_data_text_unknown`），草稿欄位與開關 off 相同。"""
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _rc4_after_name(w)
        res = await w.turn(RC4_MSG, intents=[_fi(CC, data=RC4_SEGS, answer=RC4_MSG, **RC4_VALUES)])
        assert WF.V_FILL_DATA_TEXT_UNKNOWN not in _v(res), _v(res)
        f = _fields(w) if w.draft() is not None else dict(w.pending()[res.trace.pending_id]["payload"])
        out[value] = {k: str(f.get(k)) for k in ("estate_name", *RC4_VALUES)}
        assert out[value]["date_start"] == "2026-11-01" and out[value]["rent"] == "12000", (value, f, res.answer)
    assert out["on"] == out["off"]


@pytest.mark.parametrize("answer", ["冷氣不冷，很吵", _NO], ids=["answer_across_segments", "answer_key_missing"])
async def test_rc4_a_control_single_asked_answer_invalid_still_unknown(api, answer):
    """RC4 形狀 A 對照：恰好追問一欄（問題描述）、`answer_text` 橫跨兩段資料段或鍵缺 ⇒ 仍整回合未知（fail-closed 不變）、
    不填、程式重問。"""
    w = _World()
    _seed_repair_asking_description(w)
    res = await w.turn("冷氣不冷，很吵", intents=[_fi(REPAIR, data=["冷氣不冷", "很吵"], answer=answer)])
    assert WF.V_FILL_DATA_TEXT_UNKNOWN in _v(res), _v(res)
    assert "description" not in _fields(w)
    _assert_reasked(res, "問題描述")


async def _rc4_listed_lenient(w: _World) -> None:
    """形狀 B 的前兩句：第 2 句名稱查無 ⇒ 寬鬆列候選（未選定），同 `e/drive_e.py` contract(0)／(2) 的「程式列候選、客人沒選」。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO, _ids_resp
    await w.turn("幫我建立一份新合約", intents=[_fi(CC, data=[])])
    provider = _Provider([], [_fi(CC, data=[_CC_TYPO], answer=_CC_TYPO, estate_name=_CC_TYPO)],
                         [_ids_resp(["67652", "67649"])])
    res = await w.runtime(provider).run_turn(w.ident, f"物件是{_CC_TYPO}", w.state)
    cands = (w.state.get("agent") or {}).get("write_candidates")
    assert res.quick_replies and cands and cands["picked"] is None, (res.answer, cands)   # 前提：列候選、未選定


async def _rc4_b_turn3(w: _World, data):
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO, _ids_resp
    provider = _Provider([], [_fi(CC, data=data, answer=RC4_MSG, estate_name=_CC_TYPO, **RC4_VALUES)],
                         [_ids_resp(["67652", "67649"])])
    return await w.runtime(provider).run_turn(w.ident, RC4_MSG, w.state)


async def test_rc4_b_unpicked_candidates_valid_segments_merge_same_as_off_name_unchanged(api, monkeypatch):
    """RC4 形狀 B 重放：候選集未選定、客人沒選、直接講日期租金 Email；意圖 `estate_name`＝前句名稱（草稿現值，(ii) 同值）＋
    日期／月租／Email，`data_texts` 只含本句 3 段 ⇒ on 與 off 草稿欄位相同（含名稱欄：同值、⛔ 經 (iii) 放行新名稱），
    沒有 `fill_value_outside_data`、沒有 `write_candidate_reask`。⇒ 程式路徑（`_write_draft_merge_intent` →
    `_write_draft_turn_gate` → `_write_candidates_typed`）在資料段有效時不掉值。"""
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _rc4_listed_lenient(w)
        res = await _rc4_b_turn3(w, RC4_SEGS)
        v = _v(res)
        assert WF.V_FILL_VALUE_OUTSIDE_DATA not in v and WF.V_FILL_DATA_TEXT_UNKNOWN not in v, v
        out[value] = _fields(w)
        assert all(str(out[value].get(k)) == RC4_VALUES[k] for k in RC4_VALUES), (value, out[value], res.answer)
    assert out["on"] == out["off"]


async def test_rc4_b_empty_data_texts_reproduces_live_signature_nothing_merged(api, monkeypatch):
    """RC4 形狀 B 掉值那一步：同一重放，AI 的 `data_texts` 回空陣列。改前（修復輪 1）on 重現線上 contract(0) 的標記組合
    （`fill_value_outside_data`＋`write_candidate_reask`，日期等全沒併）。修復輪 3（業主 10-27「縮小到追問回合」）：這一句
    是多欄追問回合、本片不生效 ⇒ on 與 off 相同：日期、租金、Email 照併，沒有任何 `fill_` 標記（線上掉值簽名不再出現）。
    下一片起多欄回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _rc4_listed_lenient(w)
        res = await _rc4_b_turn3(w, [])
        v = _v(res)
        assert not [m for m in v if str(m).startswith("fill_")], v
        assert str(_fields(w).get("rent")) == "12000", (value, _fields(w))
        out[value] = (_fields(w), res.answer, list(v))
    assert out["on"] == out["off"]


def _wc_reask() -> str:
    from services.agent import write_candidates as WC
    return WC.V_CANDIDATE_REASK


# ════════════════════════════════════════════════════════════════════
# 修復輪 1 追加 3（RC4 形狀 B，brief-fix1d）：未選定候選回合系統句在 DATA_TEXTS_RULE 後緊接候選清單說明
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix1d 指定的 v1 逐字（測試端獨立寫一份，⛔ 引用 `WF.DATA_TEXTS_PICK_NOTE` 自證）。
RC4_PICK_NOTE_V1 = ("（候選清單那一段是系統給的紀錄、不是使用者的話，不列；使用者最新一句裡講的欄位值，例如日期、金額、Email，"
                    "即使同時有候選清單也照樣列。）")


def test_rc4_pick_note_only_on_with_pick_rule_builder_level():
    """RC4 形狀 B（建構函式層）：`data_text=True` 且 `pick_rule=True` ⇒ 系統句含這段、緊接 `DATA_TEXTS_RULE` 之後；
    on 無 pick_rule、on＋`target_picked`、off＋pick_rule ⇒ 都不含；任何組合的 schema（含 `data_texts` description）都不含。"""
    assert WF.DATA_TEXTS_PICK_NOTE == RC4_PICK_NOTE_V1 and "DATA_TEXTS_PICK_NOTE" in WF.__all__
    for el in (True, False):
        on_pick = WF.write_intent_system_prompt(enum_labels=el, pick_rule=True, data_text=True)
        assert WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 in on_pick
        assert on_pick.endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE)
        asked = WF.write_intent_system_prompt(enum_labels=el, pick_rule=True, data_text=True,
                                              asked_labels=("租金",))
        assert asked.endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE + "\n"
                              + WF.answer_text_rule(("租金",)))
        for kw in ({"data_text": True}, {"data_text": True, "target_picked": "56906"},
                   {"pick_rule": True}, {"pick_rule": True, "data_text": False}):
            assert RC4_PICK_NOTE_V1 not in WF.write_intent_system_prompt(enum_labels=el, **kw), kw
        for rf in ({"data_text": True, "pick_ids": ("101", "102")}, {"data_text": True},
                   {"pick_ids": ("101", "102")}):
            assert RC4_PICK_NOTE_V1 not in json.dumps(
                WF.write_intent_response_format(enum_labels=el, **rf), ensure_ascii=False), rf


async def test_rc4_pick_note_sent_on_unpicked_candidate_turn_not_on_plain_followup(api, monkeypatch):
    """RC4 形狀 B（實際送出層）：未選定候選回合（寬鬆列候選、客人沒選、直接講租金）送出的系統句含這段且緊接
    `DATA_TEXTS_RULE`；schema 的 `data_texts` description 仍是 `DATA_TEXTS_RULE`。非候選的追問回合送出的系統句不含。
    開關 off 的同一候選回合也不含。修復輪 3（業主 10-27「縮小到追問回合」）：本片只在單欄追問回合生效 ⇒ 候選回合改成
    單欄追問（租金）才送這段；列候選後原狀（`asked` 空）與多欄追問（日期租金 Email）的候選回合 on 都與 off 相同
    （不含本片任何規則）。下一片起卡後、多欄回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO, _ids_resp
    monkeypatch.setenv(WIDE_ENV, "off")
    sent = {}
    for value in ("on", "off"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _rc4_listed_lenient(w)
        w.draft()["asked"] = ["rent"]
        provider = _Provider([], [_fi(CC, data=["月租12000元"], answer="12000", estate_name=_CC_TYPO,
                                      rent="12000")],
                             [_ids_resp(["67652", "67649"])])
        await w.runtime(provider).run_turn(w.ident, "月租12000元", w.state)
        (kw,) = provider.intent_calls
        assert WF.PICK_ID_KEY in _schema(kw)["properties"]                  # 前提：走的是 pick_rule 這一支
        sent[value] = kw
    on_sys = _system(sent["on"])
    assert WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 in on_sys
    assert _schema(sent["on"])["properties"][WF.DATA_TEXTS_KEY]["description"] == WF.DATA_TEXTS_RULE
    assert RC4_PICK_NOTE_V1 not in _system(sent["off"])
    for asked in (None, ["date_start", "date_end", "rent", "to_user_email"]):  # 原狀（asked 空）／多欄 ⇒ on＝off
        multi = {}
        for value in ("on", "off"):
            monkeypatch.setenv(ENV, value)
            w3 = _World()
            await _rc4_listed_lenient(w3)
            if asked is None:
                assert w3.draft()["asked"] == []                            # 前提：列候選後 asked 空
            else:
                w3.draft()["asked"] = list(asked)
            provider3 = _Provider([], [_fi(CC, data=RC4_SEGS, answer="", estate_name=_CC_TYPO, **RC4_VALUES)],
                                  [_ids_resp(["67652", "67649"])])
            await w3.runtime(provider3).run_turn(w3.ident, RC4_MSG, w3.state)
            (kw3,) = provider3.intent_calls
            assert WF.PICK_ID_KEY in _schema(kw3)["properties"]             # 前提：走的是 pick_rule 這一支
            multi[value] = (_system(kw3), kw3["response_format"])
        assert multi["on"] == multi["off"], asked
        assert RC4_PICK_NOTE_V1 not in multi["on"][0] and WF.DATA_TEXTS_RULE not in multi["on"][0]
    monkeypatch.delenv(ENV, raising=False)
    w2 = _World()
    _seed_repair_asking_description(w2)
    provider2 = _Provider([], [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
    await w2.runtime(provider2).run_turn(w2.ident, "冷氣不冷 3q", w2.state)
    (kw2,) = provider2.intent_calls
    assert WF.PICK_ID_KEY not in _schema(kw2)["properties"]                 # 前提：非候選回合
    assert WF.DATA_TEXTS_RULE in _system(kw2) and RC4_PICK_NOTE_V1 not in _system(kw2)


# ════════════════════════════════════════════════════════════════════
# 修復輪 2（P3-2，brief-fix2）：候選集綁定那一欄的前句名稱只過 (i)
# ════════════════════════════════════════════════════════════════════
async def _p32_listed(w: _World) -> None:
    """P3-2 前提：客人講物件（AI 沒抽出名稱）⇒ 程式依「名稱缺」寬鬆列 1 筆候選、未選定，草稿 `estate_name` 仍空
    （同 `x4-after2` FA1a-con-05 的 `name_lenient:trigger:missing`＋`write_candidates_shown:estate:1`）。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO, _ids_resp
    provider = _Provider([], [_fi(CC, data=[])], [_ids_resp(["67652"])])
    res = await w.runtime(provider).run_turn(w.ident, f"{_CC_TYPO}那間要新增合約", w.state)
    cands = (w.state.get("agent") or {}).get("write_candidates")
    assert "write_candidates_shown:estate:1" in _v(res) and "name_lenient:trigger:missing" in _v(res), _v(res)
    assert cands and cands["picked"] is None and cands["field"] == "estate_name", cands
    assert "estate_name" not in _fields(w)


async def _p32_turn(w: _World, message: str, data, **fields):
    from tests.unit.agent.test_f12_name_lenient_req import _ids_resp
    provider = _Provider([], [_fi(CC, data=data, answer="", **fields)], [_ids_resp(["67652"])])
    return await w.runtime(provider).run_turn(w.ident, message, w.state)


async def test_p32_a_unpicked_lenient_one_prior_name_and_dates_merge_same_as_off(api, monkeypatch):
    """P3-2 (a)：1 筆寬鬆候選未選定、第 3 句只有日期租金 Email、意圖帶前句名稱（不在本句資料段）⇒ 名稱經例外只過 (i)、
    記 `fill_bound_field_exempt`，日期等照併；之後名稱解析、候選照現行規則（本 fixture：錯字名稱再走寬鬆列候選）。
    on 與 off 的草稿、回話、按鈕相同。修復輪 3：本片只在單欄追問回合生效 ⇒ 列候選後把草稿追問改成單欄（租金）。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _p32_listed(w)
        w.draft()["asked"] = ["rent"]
        res = await _p32_turn(w, RC4_MSG, RC4_SEGS, estate_name=_CC_TYPO, **RC4_VALUES)
        v = _v(res)
        assert WF.V_FILL_VALUE_OUTSIDE_DATA not in v, v
        assert (WF.V_FILL_BOUND_FIELD_EXEMPT in v) is (value == "on"), v
        assert _fields(w).get("estate_name") == _CC_TYPO and str(_fields(w).get("rent")) == "12000", _fields(w)
        out[value] = (_fields(w), res.answer, res.quick_replies, res.trace.pending_id is None)
    assert out["on"] == out["off"]


async def test_p32_b_control_not_bound_field_prior_value_still_blocked(api, monkeypatch):
    """P3-2 (b) 對照：
    - 沒有候選集（名稱欄不是綁定欄）、意圖帶前句才講過的名稱 ⇒ 照舊 (iii) 拒收（`fill_value_outside_data`、⛔ 例外）；
    - 有候選集（綁定 `estate_name`），但意圖帶前句才講過的**別欄**新值（租金）⇒ 照舊 (iii) 拒收，綁定欄照例外放行。
    修復輪 3：本片只在單欄追問回合生效 ⇒ 兩段都改成單欄追問（租金／開始日）。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO
    w = _World()
    _seed_draft(w, CC, {}, asked=["rent"])
    w.state["agent"]["dialog"] = [{"role": "user", "content": f"物件是{_CC_TYPO}"},
                                  {"role": "assistant", "content": "要完成這筆建立，還需要：物件。"}]
    res = await w.turn(RC4_MSG, intents=[_fi(CC, data=RC4_SEGS, answer="", estate_name=_CC_TYPO, **RC4_VALUES)])
    v = _v(res)
    assert (w.state.get("agent") or {}).get("write_candidates") is None           # 前提：沒有候選集
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in v and WF.V_FILL_BOUND_FIELD_EXEMPT not in v, v
    assert "estate_name" not in _fields(w) and str(_fields(w).get("rent")) == "12000", _fields(w)

    w2 = _World()
    await _p32_listed(w2)
    w2.draft()["asked"] = ["date_start"]
    w2.state["agent"]["dialog"].append({"role": "user", "content": "月租9000元"})
    msg = "2026年11月1日到2027年10月31日"
    res2 = await _p32_turn(w2, msg, [msg], estate_name=_CC_TYPO, date_start="2026-11-01", date_end="2027-10-31",
                           rent="9000")
    v2 = _v(res2)
    assert WF.V_FILL_VALUE_OUTSIDE_DATA in v2 and WF.V_FILL_BOUND_FIELD_EXEMPT in v2, v2
    f2 = _fields(w2)
    assert "rent" not in f2 and f2.get("estate_name") == _CC_TYPO and f2.get("date_start") == "2026-11-01", f2


async def test_p32_c_control_bound_field_value_not_in_user_words_still_blocked_by_i(api):
    """P3-2 (c) 對照：綁定欄的值不在任何客人原話（AI 編的「海景豪宅」）⇒ 照舊被 (i) 擋、⛔ 例外、不進草稿。
    修復輪 3：本片只在單欄追問回合生效 ⇒ 列候選後把草稿追問改成單欄（租金），本條才走本片。"""
    w = _World()
    await _p32_listed(w)
    w.draft()["asked"] = ["rent"]
    res = await _p32_turn(w, RC4_MSG, RC4_SEGS, estate_name="海景豪宅", **RC4_VALUES)
    v = _v(res)
    assert WF.V_FILL_BOUND_FIELD_EXEMPT not in v, v
    assert _fields(w).get("estate_name") != "海景豪宅", _fields(w)
    assert str(_fields(w).get("rent")) == "12000", _fields(w)


async def test_p32_d_bound_field_value_with_thanks_passes_i_and_is_admitted_like_off(api, monkeypatch):
    """P3-2 (d)（已知放寬，回報主會話裁是否收窄成「值須等於前句客人原話中的一段」）：本句「基隆溫心一人宅 3q」、資料段
    「基隆溫心一人宅」、意圖名稱「基隆溫心一人宅 3q」⇒ 名稱值在客人原話裡、過 (i) ⇒ 綁定欄例外放行（記
    `fill_bound_field_exempt`），草稿名稱＝「基隆溫心一人宅 3q」，與開關 off 相同（本 fixture 之後走寬鬆列候選、⛔ 出卡）。
    ⇒ 綁定欄不再擋本句的道謝字；名稱只進名稱解析，⛔ 由例外直接選定。修復輪 3：本片只在單欄追問回合生效 ⇒ 列候選後
    把草稿追問改成單欄（租金）。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        await _p32_listed(w)
        w.draft()["asked"] = ["rent"]
        res = await _p32_turn(w, f"{_CC_TYPO} 3q", [_CC_TYPO], estate_name=f"{_CC_TYPO} 3q")
        v = _v(res)
        assert (WF.V_FILL_BOUND_FIELD_EXEMPT in v) is (value == "on"), v
        assert _fields(w).get("estate_name") == f"{_CC_TYPO} 3q", _fields(w)
        assert res.trace.pending_id is None and res.quick_replies, res.answer
        out[value] = (_fields(w), res.answer, res.quick_replies)
    assert out["on"] == out["off"]


async def test_p32_cmd_path_bound_field_not_exempt_when_picked_at_turn_start(api, monkeypatch):
    """P3-2 cmd 路徑不受影響：回合開始已選定（`cmd_scope_start`）⇒ `_fill_bound_field_exempt` 回 `False`（名稱值照舊由
    `_write_candidates_name_rule`／指令路徑處理）；候選集已選定（`picked` 有值）同樣 `False`；未選定、仍綁定 ⇒ `True`。"""
    w = _World()
    await _p32_listed(w)
    cands = copy.deepcopy((w.state.get("agent") or {}).get("write_candidates"))
    rt, acc, _kw = _direct(w, copy.deepcopy(w.draft()), RC4_MSG)
    wd = acc.write_draft
    f = _field(CC, "estate_name")
    wd.candidates = cands
    assert rt._fill_bound_field_exempt(w.ident, wd, f) is True
    assert rt._fill_bound_field_exempt(w.ident, wd, _field(CC, "rent")) is False
    wd.cmd_scope_start = True
    assert rt._fill_bound_field_exempt(w.ident, wd, f) is False
    wd.cmd_scope_start = False
    wd.candidates = dict(cands, picked="67652")
    assert rt._fill_bound_field_exempt(w.ident, wd, f) is False
    wd.candidates = dict(cands, name_fp="0" * 32)                          # 解綁（名稱指紋不符）
    assert rt._fill_bound_field_exempt(w.ident, wd, f) is False


# ════════════════════════════════════════════════════════════════════
# 修復輪 2 追加（brief-fix3）：on 系統句在 WRITE_INTENT_NONE_RULE 後緊接「只補一部分也照填 action」說明
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix3 指定的 v1 逐字（測試端獨立寫一份，⛔ 引用 `WF.WRITE_INTENT_PARTIAL_NOTE` 自證）。
FIX3_PARTIAL_NOTE_V1 = ("（正在回答進行中的建立所需的資料時，即使這句只補了一部分、還沒補齊，也照進行中的動作填 action，"
                        "並把這句講到的欄位列進 fields。）")


def test_fix3_partial_note_only_on_and_right_after_none_rule_builder_level():
    """brief-fix3（建構函式層）：`data_text=True`（一般、`asked_labels`、`pick_rule`、`target_picked` 各一）⇒ 系統句恰含
    一次這段、且緊接 `WRITE_INTENT_NONE_RULE`；off（不帶本片參數、`data_text=False`，含各組合）⇒ 不含；任何組合的
    schema 都不含（只給 AI 讀的系統句說明）。"""
    assert WF.WRITE_INTENT_PARTIAL_NOTE == FIX3_PARTIAL_NOTE_V1 and "WRITE_INTENT_PARTIAL_NOTE" in WF.__all__
    on_variants = ({}, {"asked_labels": ("租金", "承租人 Email")}, {"pick_rule": True},
                   {"target_picked": "56906"})
    for el in (True, False):
        for kw in on_variants:
            sp = WF.write_intent_system_prompt(enum_labels=el, data_text=True, **kw)
            assert sp.count(FIX3_PARTIAL_NOTE_V1) == 1, kw
            assert WF.WRITE_INTENT_NONE_RULE + FIX3_PARTIAL_NOTE_V1 in sp, kw
            assert sp.count(WF.WRITE_INTENT_NONE_RULE) == 1, kw
            # 其餘既有段落位置不動：去掉這段 ⇒ 與「off 系統句＋原本 on 才接的段落」相同（off 部分逐字不變）
            off_sp = WF.write_intent_system_prompt(enum_labels=el, **kw)
            assert sp.replace(FIX3_PARTIAL_NOTE_V1, "", 1).startswith(off_sp), kw
        for kw in ({}, {"data_text": False}, {"data_text": False, "asked_labels": ("租金",)},
                   {"pick_rule": True}, {"target_picked": "56906"}, {"dialog_act": True},
                   {"rechoice_type": "contract"}):
            assert FIX3_PARTIAL_NOTE_V1 not in WF.write_intent_system_prompt(enum_labels=el, **kw), kw
        for rf in ({"data_text": True}, {"data_text": True, "asked_labels": ("租金",)},
                   {"data_text": True, "pick_ids": ("101", "102")}, {"data_text": True, "target_picked": "56906"},
                   {}):
            assert FIX3_PARTIAL_NOTE_V1 not in json.dumps(
                WF.write_intent_response_format(enum_labels=el, **rf), ensure_ascii=False), rf


async def test_fix3_partial_note_sent_on_followup_and_unpicked_candidate_turns(api, monkeypatch):
    """brief-fix3（實際送出層）：開關 on 的一般追問回合（修繕單追問問題描述）與未選定候選回合（寬鬆列候選、客人沒選、
    直接講日期租金 Email）送出的系統句都含這段且緊接 `WRITE_INTENT_NONE_RULE`；schema 不含。開關 off 的同兩回合都不含。
    修復輪 3（業主 10-27「縮小到追問回合」）：本片只在單欄追問回合生效 ⇒ 候選回合改成單欄追問（租金）。"""
    from tests.unit.agent.test_f12_name_lenient_req import _CC_TYPO, _ids_resp
    for value in ("on", "off"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        _seed_repair_asking_description(w)
        provider = _Provider([], [_fi(REPAIR, data=["冷氣不冷"], answer="冷氣不冷")])
        await w.runtime(provider).run_turn(w.ident, "冷氣不冷 3q", w.state)
        (kw,) = provider.intent_calls
        assert WF.PICK_ID_KEY not in _schema(kw)["properties"]              # 前提：非候選的追問回合
        assert (WF.answer_text_rule(("問題描述",)) in _system(kw)) is (value == "on")   # 前提：追問回合
        w2 = _World()
        await _rc4_listed_lenient(w2)
        w2.draft()["asked"] = ["rent"]
        provider2 = _Provider([], [_fi(CC, data=RC4_SEGS, answer="12000", estate_name=_CC_TYPO, **RC4_VALUES)],
                              [_ids_resp(["67652", "67649"])])
        await w2.runtime(provider2).run_turn(w2.ident, RC4_MSG, w2.state)
        (kw2,) = provider2.intent_calls
        assert WF.PICK_ID_KEY in _schema(kw2)["properties"]                 # 前提：走的是 pick_rule 這一支
        for sent in (kw, kw2):
            sys_text = _system(sent)
            if value == "on":
                assert sys_text.count(FIX3_PARTIAL_NOTE_V1) == 1
                assert WF.WRITE_INTENT_NONE_RULE + FIX3_PARTIAL_NOTE_V1 in sys_text
            else:
                assert FIX3_PARTIAL_NOTE_V1 not in sys_text and WF.WRITE_INTENT_NONE_RULE in sys_text
            assert FIX3_PARTIAL_NOTE_V1 not in json.dumps(sent["response_format"], ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# 修復輪 3（brief-fix4；業主 2026-10-27 計畫 §6 第 10 點「縮小到追問回合」＋卡後更正沒套用卻說卡片還在）
# 改動 1：本片只在「單欄追問回合」生效；第一句、卡出後打字、多欄追問 ⇒ 與開關 off 逐位相同。
# 改動 2：卡仍有效、本回合沒讀到任何值 ⇒ `CARD_NO_CHANGE_TEXT`（⛔「卡片還在，請按確認。」）。
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix4 指定的逐字（測試端獨立寫一份，⛔ 引用 `WF.CARD_NO_CHANGE_TEXT` 自證）。
FIX4_NO_CHANGE_V1 = "卡片內容沒有變更；要送出請按確認，要改請按「我要修改」。"
FIX4_NO_VALUE_MARK_V1 = "write_reply_card_no_value_read"


async def test_fix4_a_single_field_followup_turn_still_uses_data_segments(api):
    """(a)：單欄追問回合（追問帳單項目、回合開始有草稿、未凍結）⇒ 仍生效：建構點帶 `data_text` 與追問欄標籤、
    `fill_active`；實際送出的系統句接資料段規則＋答覆段規則；「水電費 3q」只填「水電費」、金額不被「3q」衍生的 3 覆寫。"""
    w = _World()
    _rt, acc, kw = _direct(w, _draft(w, MB, {"contract_ref": CONTRACT, "total": 1000}), "水電費 3q", asked=["title"])
    assert kw == {"data_text": True, "asked_labels": ("帳單項目",)}, kw
    assert acc.write_draft.fill_active is True and acc.write_draft.fill_followup is True

    w2 = _World()
    _seed_bill_asking_title(w2, total=1000)
    provider = _Provider([], [_fi(MB, data=["水電費"], answer="水電費", title="水電費 3q", total="3")])
    res = await w2.runtime(provider).run_turn(w2.ident, "水電費 3q", w2.state)
    (kw2,) = provider.intent_calls
    assert _system(kw2).endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE + "\n"
                                 + WF.answer_text_rule(("帳單項目",)))
    assert _schema(kw2)["required"][-2:] == [WF.DATA_TEXTS_KEY, WF.ANSWER_TEXT_KEY]
    f = _fields(w2)
    assert f.get("total") == "1000", f
    assert f.get("title") == "水電費" or "帳單項目：水電費" in res.answer, (f, res.answer)
    assert "3q" not in res.answer


async def _fix4_on_off(monkeypatch, make_world, message: str, intents, script=()) -> dict:
    """同一回合 off、on 各跑一次（每次新世界）；回送出的系統句、response_format、回話、草稿欄位、標記。"""
    out = {}
    for value in ("off", "on"):
        monkeypatch.setenv(ENV, value)
        w = await make_world()
        monkeypatch.setenv(ENV, value)                       # `_bill_card` 會自己切開關，這裡再設一次
        provider = _Provider(list(script), intents())
        res = await w.runtime(provider).run_turn(w.ident, message, w.state)
        (kw,) = provider.intent_calls
        out[value] = {"system": _system(kw), "rf": kw["response_format"], "answer": res.answer,
                      "state": res.outcome["state"], "pending": res.trace.pending_id is not None,
                      "fields": _fields(w), "v": list(_v(res))}
    return out


def _fix4_assert_equals_off(out: dict) -> None:
    on, off = out["on"], out["off"]
    assert on["system"].encode("utf-8") == off["system"].encode("utf-8")          # 逐位相同
    assert _digest(on["rf"]) == _digest(off["rf"])
    assert WF.DATA_TEXTS_RULE not in on["system"] and WF.DATA_TEXTS_KEY not in on["rf"]["json_schema"]["schema"][
        "properties"]
    assert on == off
    assert not [m for m in on["v"] if str(m).startswith("fill_")], on["v"]


async def _fix4_gate_equals_off(w: _World, rt, acc, cases) -> None:
    """直接層：`fill_active=False` ⇒ 閘門原話（①～⑥ 共用）＝現行值閘（同一回傳、同一組 violation）。"""
    assert acc.write_draft.fill_active is False
    for key, raw in cases:
        f = _field(MB, key)
        expect_v: list = []
        expect = await rt._write_draft_gate_value(f, raw, w.ident, acc.write_draft.user_texts, expect_v,
                                                  from_intent=True)
        before = len(acc.violations)
        got, dropped = await rt._write_draft_turn_gate(acc, w.ident, f, raw, from_intent=True)
        assert got == expect and acc.violations[before:] == expect_v, (key, raw)
        assert dropped is (expect is None and bool(expect_v))


FIX4_CASES = (("total", "3"), ("title", "水電費 3q"), ("total", "2000"), ("title", "水電費"))


async def test_fix4_b_first_sentence_equals_off(api, monkeypatch):
    """(b) 第一句（回合開始沒有草稿）：送出的系統句與 schema、值閘、草稿結果皆＝off；`fill_active` 為 `False`。
    下一片起第一句由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    msg = "幫我開一張帳單，水電費 3q"
    w = _World()
    rt, acc, kw = _direct(w, None, msg, obj={"action": MB, "fields": [], WF.DATA_TEXTS_KEY: ["幫我開一張帳單，水電費"]})
    assert kw == {} and acc.write_draft.fill_data is None
    acc.write_draft.draft = _draft(w, MB, {"contract_ref": CONTRACT})          # 回合中建出的草稿
    await _fix4_gate_equals_off(w, rt, acc, FIX4_CASES)

    async def _fresh():
        return _World()
    out = await _fix4_on_off(monkeypatch, _fresh, msg, lambda: [
        _fi(MB, data=["幫我開一張帳單，水電費"], title="水電費 3q", total="3")])
    _fix4_assert_equals_off(out)
    assert out["on"]["fields"] == {"title": "水電費 3q", "total": "3"}, out["on"]["fields"]


async def test_fix4_b_typing_after_card_equals_off(api, monkeypatch):
    """(b) 卡出後打字（回合開始草稿已出卡、`asked` 空）：送出的系統句與 schema、值閘、草稿結果皆＝off；
    `fill_active` 為 `False`。下一片起卡後回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    msg = "金額改成 2000 3q"
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費", "total": 1000})
    rt, acc, kw = _direct(w, draft, msg, asked=[], obj={"action": MB, "fields": [], WF.DATA_TEXTS_KEY: ["金額改成"]})
    assert kw == {} and acc.write_draft.fill_data is None
    await _fix4_gate_equals_off(w, rt, acc, FIX4_CASES)

    async def _card():
        return await _bill_card(monkeypatch)
    out = await _fix4_on_off(monkeypatch, _card, msg, lambda: [_fi(MB, data=["金額改成"], total="2000")],
                             script=[_out("主模型的回答")])
    _fix4_assert_equals_off(out)
    assert out["on"]["fields"].get("total") == "2000", out["on"]


async def test_fix4_b_multi_field_followup_equals_off(api, monkeypatch):
    """(b) 多欄追問（`asked` ≥2）：送出的系統句與 schema、值閘、草稿結果皆＝off；`fill_active` 為 `False`。
    下一片起多欄回合由 `AGENT_FILL_DATA_TEXT_WIDE` 管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    msg = "水電費 3q"
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT})
    rt, acc, kw = _direct(w, draft, msg, asked=["title", "total"],
                          obj={"action": MB, "fields": [], WF.DATA_TEXTS_KEY: ["水電費"], WF.ANSWER_TEXT_KEY: "水電費"})
    assert kw == {} and acc.write_draft.fill_data is None and acc.write_draft.fill_answer is None
    await _fix4_gate_equals_off(w, rt, acc, FIX4_CASES)

    async def _multi():
        w0 = _World()
        _seed_draft(w0, MB, {"contract_ref": CONTRACT}, asked=["title", "total"])
        return w0
    out = await _fix4_on_off(monkeypatch, _multi, msg, lambda: [
        _fi(MB, data=["水電費"], answer="水電費", title="水電費", total="3")], script=[_out("好的")])
    _fix4_assert_equals_off(out)


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix4_d_card_turn_no_value_read_says_no_change(api, monkeypatch, fill):
    """(d)：卡後回合、意圖沒抽出任何欄位（客人打字要更正、但沒讀到值）⇒ 回話開頭是 `CARD_NO_CHANGE_TEXT`、記
    `write_reply_card_no_value_read`、⛔「卡片還在，請按確認。」；卡與金額不變。本片開關 on／off 皆同。"""
    w = await _bill_card(monkeypatch)
    monkeypatch.setenv(ENV, fill)
    res = await w.turn("金額改1250 3Q", intents=[_fi("none")], script=[_out("主模型的回答")])
    assert res.answer.startswith(FIX4_NO_CHANGE_V1 + "\n"), res.answer
    assert WF.CARD_STILL_VALID_TEXT not in res.answer and WF.CARD_UNCHANGED_TEXT not in res.answer
    assert FIX4_NO_VALUE_MARK_V1 in _v(res), _v(res)
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id is not None
    assert _fields(w).get("total") == "1000" and "1,250" not in res.answer


async def test_fix4_d_b_off_keeps_old_text(api, monkeypatch):
    """(d) 對照：B 片回話開關 off（`_write_reply_active()` 為 `False`）⇒ 舊路徑不變：不出新句、不記新標記。"""
    from tests.unit.agent.test_b_write_replies_program_req import _b_off
    w = await _bill_card(monkeypatch)
    _b_off(monkeypatch)
    res = await w.turn("金額改1250 3Q", intents=[_fi("none")], script=[_out("主模型的回答")])
    assert FIX4_NO_CHANGE_V1 not in res.answer, res.answer
    assert FIX4_NO_VALUE_MARK_V1 not in _v(res), _v(res)


@pytest.mark.parametrize("b_reply", ["on", "off"])
def test_fix4_d_still_valid_exit_direct(api, monkeypatch, b_reply):
    """(d) 直接呼叫 `_write_draft_card_still_valid_exit`（A+ 出口）：沒讀到任何值（`touched` 空）⇒ B 片生效時前導句＝
    `CARD_NO_CHANGE_TEXT`＋記標記；B 片 off ⇒ 仍是 `CARD_STILL_VALID_TEXT`（舊路徑不變）。"""
    if b_reply == "off":
        from tests.unit.agent.test_b_write_replies_program_req import _b_off
        _b_off(monkeypatch)
    w = _World()
    draft = _draft(w, MB, {"contract_ref": CONTRACT, "title": "管理費", "total": 1000})
    rt, acc, _kw = _direct(w, draft, "好")
    acc.write_draft.card_still_valid = {"pid": "p-fix4", "card": "（卡）", "action": MB}
    res = rt._write_draft_card_still_valid_exit(acc, {}, "好")
    if b_reply == "on" and rt._write_reply_active():
        assert res.answer == f"{FIX4_NO_CHANGE_V1}\n（卡）", res.answer
        assert FIX4_NO_VALUE_MARK_V1 in acc.violations
    else:
        assert b_reply == "off", "前提：B 片開關預設 on 時 `_write_reply_active()` 為 True"
        assert res.answer == f"{WF.CARD_STILL_VALID_TEXT}\n（卡）", res.answer
        assert FIX4_NO_VALUE_MARK_V1 not in acc.violations


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix4_e_same_value_read_uses_read_same_lead_and_read_line(api, monkeypatch, fill):
    """(e)：卡後回合讀到值且與卡相同（金額 1,000）⇒ 「這次讀到的是：…」那一行；不記新標記。
    修復輪 4（brief-fix5）：前導句由 `CARD_STILL_VALID_TEXT` 改為 `CARD_READ_SAME_LEAD`。"""
    w = await _bill_card(monkeypatch)
    monkeypatch.setenv(ENV, fill)
    res = await w.turn("金額 1,000", intents=[_fi(MB, total="1,000")], script=[_out("主模型的回答")])
    lines = res.answer.split("\n")
    assert lines[0] == WF.CARD_READ_SAME_LEAD and WF.CARD_STILL_VALID_TEXT not in res.answer, res.answer
    assert lines[1].startswith("這次讀到的是：") and "金額" in lines[1], res.answer
    assert FIX4_NO_VALUE_MARK_V1 not in _v(res) and FIX4_NO_CHANGE_V1 not in res.answer
    assert _fields(w).get("total") == "1000"


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix4_f_value_dropped_keeps_unchanged_text(api, monkeypatch, fill):
    """(f)：卡後回合值被值閘丟掉（金額 abc）⇒ 照舊 `CARD_UNCHANGED_TEXT`；不記新標記。"""
    w = await _bill_card(monkeypatch)
    monkeypatch.setenv(ENV, fill)
    res = await w.turn("金額 abc", intents=[_fi(MB, total="abc")], script=[_out("主模型的回答")])
    assert res.answer.startswith(WF.CARD_UNCHANGED_TEXT), res.answer
    assert FIX4_NO_VALUE_MARK_V1 not in _v(res) and FIX4_NO_CHANGE_V1 not in res.answer
    assert _fields(w).get("total") == "1000"


def test_fix4_new_constant_and_violation_are_fixed_strings_and_exported():
    """改動 2：新常數逐字＝派工單指定句、列在 `__all__`；新 violation 固定字串（⛔ 帶值）、列在 `__all__`；
    與既有兩句不同。"""
    assert WF.CARD_NO_CHANGE_TEXT == FIX4_NO_CHANGE_V1 and "CARD_NO_CHANGE_TEXT" in WF.__all__
    assert WF.V_CARD_NO_VALUE_READ == FIX4_NO_VALUE_MARK_V1 and "V_CARD_NO_VALUE_READ" in WF.__all__
    assert FIX4_NO_VALUE_MARK_V1.isascii() and "{" not in FIX4_NO_VALUE_MARK_V1 and ":" not in FIX4_NO_VALUE_MARK_V1
    assert "{" not in FIX4_NO_CHANGE_V1
    assert len({WF.CARD_NO_CHANGE_TEXT, WF.CARD_STILL_VALID_TEXT, WF.CARD_UNCHANGED_TEXT}) == 3


# ════════════════════════════════════════════════════════════════════
# 修復輪 4（brief-fix5；業主 2026-10-27 計畫 §6 第 10 點）：卡後回合讀到的值都與卡相同 ⇒ 前導句一律中性
# `CARD_READ_SAME_LEAD`（⛔「卡片還在，請按確認。」）——程式分不出「客人真的沒要改」與「AI 漏讀要改的欄」
# （第 4 輪 X4 `FA1c-rep-06`：「問題描述再加一句…」只讀到物件、描述提議被值閘丟）。B 片關的舊路徑照舊。
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix5 指定的逐字（測試端獨立寫一份，⛔ 引用 `WF.CARD_READ_SAME_LEAD` 自證）。
FIX5_READ_SAME_LEAD_V1 = "卡片內容沒有變更；要送出請按確認。"
FIX5_STATE_MARK = f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{WF.WRITE_REPLY_STATE_CARD_STILL_VALID}"


def _fix5_assert_read_same(answer: str, label: str) -> None:
    lines = answer.split("\n")
    assert lines[0] == FIX5_READ_SAME_LEAD_V1, answer
    assert lines[1].startswith("這次讀到的是：") and label in lines[1], answer
    assert WF.CARD_STILL_VALID_TEXT not in answer and WF.CARD_NO_CHANGE_TEXT not in answer, answer
    assert WF.CARD_UNCHANGED_TEXT not in answer, answer


def test_fix5_new_constant_is_fixed_string_and_exported():
    """新常數逐字＝派工單指定句、列在 `__all__`、⛔ 帶值；與既有四句皆不同、既有值未改。"""
    assert WF.CARD_READ_SAME_LEAD == FIX5_READ_SAME_LEAD_V1 and "CARD_READ_SAME_LEAD" in WF.__all__
    assert "{" not in FIX5_READ_SAME_LEAD_V1
    assert WF.CARD_STILL_VALID_TEXT == "卡片還在，請按確認。"
    assert WF.CARD_NO_CHANGE_TEXT == FIX4_NO_CHANGE_V1
    assert len({WF.CARD_READ_SAME_LEAD, WF.CARD_NO_CHANGE_TEXT, WF.CARD_STILL_VALID_TEXT,
                WF.CARD_UNCHANGED_TEXT, WF.CARD_READ_VALUES_TEMPLATE}) == 5


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix5_still_valid_exit_intent_same_value_uses_read_same_lead(api, monkeypatch, fill):
    """`_write_draft_card_still_valid_exit`（程式優先、意圖讀到金額 1,000＝卡；實測此回合由 A+ 出口結束、無
    `_write_reply_state` 分支標記）⇒ 開頭 `CARD_READ_SAME_LEAD`、第二行「這次讀到的是：…金額…」、⛔
    `CARD_STILL_VALID_TEXT`；`V_CARD_STILL_VALID` 照記、不記沒讀到值標記；卡與金額不變。本片開關 on／off 皆同。"""
    w = await _bill_card(monkeypatch)
    monkeypatch.setenv(ENV, fill)
    res = await w.turn("金額 1,000", intents=[_fi(MB, total="1,000")], script=[_out("主模型的回答")])
    _fix5_assert_read_same(res.answer, "金額")
    assert FIX5_STATE_MARK not in _v(res) and WF.V_CARD_STILL_VALID in _v(res), _v(res)
    assert FIX4_NO_VALUE_MARK_V1 not in _v(res)
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id is not None
    assert _fields(w).get("total") == "1000"


async def _fix5_reply_state_direct(monkeypatch, card: str) -> tuple:
    """直接呼叫 `_write_reply_state`：草稿＝卡（`_write_proposal_card_unchanged` 以替身回同一張卡）、`touched`＝{total}、
    值沒被丟 ⇒ 走 unchanged 分支的「讀到值」那一支。回 `(runtime, acc, state)`。"""
    w = _World()
    rt, acc, _kw = _direct(w, _draft(w, MB, {"contract_ref": CONTRACT, "total": 1000}), "金額 1,000")
    acc.write_draft.touched = {"total"}
    assert acc.write_draft.user_value_dropped is False and not rt._fill_value_not_applied(acc.write_draft)

    async def _unchanged(_identity, _agent_state, action, _values):
        return ("p-fix5", card, action)
    monkeypatch.setattr(rt, "_write_proposal_card_unchanged", _unchanged)
    state = await rt._write_reply_state(acc, w.ident, {})
    return rt, acc, state


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix5_reply_state_unchanged_direct_read_same_lead(api, monkeypatch, fill):
    """`_write_reply_state` unchanged 分支（B 片生效）：讀到值且與卡相同 ⇒ `lead`＝`CARD_READ_SAME_LEAD`＋換行＋讀到行；
    分支名照舊 `card_still_valid`；不記沒讀到值標記。本片開關 on／off 皆同。"""
    monkeypatch.setenv(ENV, fill)
    card = "即將建立帳單，請確認：\n・金額：1,000"
    rt, acc, state = await _fix5_reply_state_direct(monkeypatch, card)
    assert rt._write_reply_active()                                   # 前提：B 片預設生效
    assert state["branch"] == WF.WRITE_REPLY_STATE_CARD_STILL_VALID and state["pid"] == "p-fix5"
    read_line = WF.card_read_values_text([("金額", "1,000")])
    assert state["lead"] == f"{FIX5_READ_SAME_LEAD_V1}\n{read_line}", state["lead"]
    _fix5_assert_read_same(f"{state['lead']}\n{state['card']}", "金額")
    assert FIX4_NO_VALUE_MARK_V1 not in acc.violations


async def test_fix5_b_off_reply_state_unchanged_direct_keeps_old_text(api, monkeypatch):
    """`_write_reply_state` unchanged 分支、B 片關（`_write_reply_active()` 為 `False`）⇒ 照舊
    `CARD_STILL_VALID_TEXT`＋讀到行（改前即如此）、⛔ `CARD_READ_SAME_LEAD`。"""
    from tests.unit.agent.test_b_write_replies_program_req import _b_off
    _b_off(monkeypatch)
    card = "即將建立帳單，請確認：\n・金額：1,000"
    rt, _acc, state = await _fix5_reply_state_direct(monkeypatch, card)
    assert not rt._write_reply_active()                               # 前提
    read_line = WF.card_read_values_text([("金額", "1,000")])
    assert state["lead"] == f"{WF.CARD_STILL_VALID_TEXT}\n{read_line}", state["lead"]
    assert FIX5_READ_SAME_LEAD_V1 not in state["lead"]


@pytest.mark.parametrize("fill", ["on", "off"])
async def test_fix5_still_valid_exit_same_value_uses_read_same_lead(api, monkeypatch, fill):
    """`_write_draft_card_still_valid_exit`（AP-1 提議檢查點：主模型提議與卡同值）⇒ 開頭 `CARD_READ_SAME_LEAD`、
    第二行「這次讀到的是：…」、⛔ `CARD_STILL_VALID_TEXT`；此出口不經 `_write_reply_state`（無其分支標記）。
    本片開關 on／off 皆同。"""
    w = await _bill_card(monkeypatch)
    monkeypatch.setenv(ENV, fill)
    pid1 = next(iter(w.pending()))
    res = await w.turn("金額 1,000", program_first=False, script=[
        _proposal({"action": MB, **MB_GOOD}), _out("主模型的回答")])
    _fix5_assert_read_same(res.answer, "")
    assert FIX5_STATE_MARK not in _v(res) and WF.V_WRITE_PROPOSAL in _v(res), _v(res)
    assert FIX4_NO_VALUE_MARK_V1 not in _v(res)
    assert res.outcome["state"] == "confirm_pending" and res.trace.pending_id == pid1


@pytest.mark.parametrize("fill", ["on", "off"])
def test_fix5_still_valid_exit_direct_read_same_lead(api, monkeypatch, fill):
    """直接呼叫 `_write_draft_card_still_valid_exit`：`touched`＝{total}、卡上「・金額：1,000」⇒
    `CARD_READ_SAME_LEAD`＋讀到行＋卡；不記沒讀到值標記。本片開關 on／off 皆同。"""
    monkeypatch.setenv(ENV, fill)
    w = _World()
    card = "即將建立帳單，請確認：\n・金額：1,000"
    rt, acc, _kw = _direct(w, _draft(w, MB, {"contract_ref": CONTRACT, "total": 1000}), "金額 1,000")
    assert rt._write_reply_active()                                   # 前提：B 片預設生效
    acc.write_draft.card_still_valid = {"pid": "p-fix5", "card": card, "action": MB}
    acc.write_draft.touched = {"total"}
    res = rt._write_draft_card_still_valid_exit(acc, {}, "金額 1,000")
    read_line = WF.card_read_values_text([("金額", "1,000")])
    assert res.answer == f"{FIX5_READ_SAME_LEAD_V1}\n{read_line}\n{card}", res.answer
    _fix5_assert_read_same(res.answer, "金額")
    assert FIX4_NO_VALUE_MARK_V1 not in acc.violations


def test_fix5_b_off_still_valid_exit_direct_keeps_old_text(api, monkeypatch):
    """B 片關（`_write_reply_active()` 為 `False`）⇒ 舊路徑照舊：`CARD_STILL_VALID_TEXT`＋卡（不列讀到的值）。"""
    from tests.unit.agent.test_b_write_replies_program_req import _b_off
    _b_off(monkeypatch)
    w = _World()
    card = "即將建立帳單，請確認：\n・金額：1,000"
    rt, acc, _kw = _direct(w, _draft(w, MB, {"contract_ref": CONTRACT, "total": 1000}), "金額 1,000")
    assert not rt._write_reply_active()                               # 前提
    acc.write_draft.card_still_valid = {"pid": "p-fix5", "card": card, "action": MB}
    acc.write_draft.touched = {"total"}
    res = rt._write_draft_card_still_valid_exit(acc, {}, "金額 1,000")
    assert res.answer == f"{WF.CARD_STILL_VALID_TEXT}\n{card}", res.answer
    assert FIX5_READ_SAME_LEAD_V1 not in res.answer


async def test_fix5_b_off_turn_keeps_still_valid_text(api, monkeypatch):
    """B 片關、卡後同值重述（整回合）⇒ 回話照舊以 `CARD_STILL_VALID_TEXT` 開頭、⛔ `CARD_READ_SAME_LEAD`。"""
    from tests.unit.agent.test_b_write_replies_program_req import _b_off
    w = await _bill_card(monkeypatch)
    _b_off(monkeypatch)
    res = await w.turn("金額 1,000", intents=[_fi(MB, total="1,000")], script=[_out("主模型的回答")])
    assert res.answer.startswith(WF.CARD_STILL_VALID_TEXT + "\n"), res.answer
    assert FIX5_READ_SAME_LEAD_V1 not in res.answer


# ════════════════════════════════════════════════════════════════════
# 修復輪 5（brief-fix6；計畫 §6 第 11 點「補一句說明再收」）：`DATA_TEXTS_RULE` 後緊接名稱說明
# 重現：第 5 輪 X4 `FA3-est-04`「復興100號3q」、`FA3-est-05`「3Q 晴空小舍」單欄追問名稱回合錯筆卡（探針 17：AI 把 3Q
# 標進資料段與答覆段 3/8～7/8）；探針 18 把系統句的 `DATA_TEXTS_RULE` 換成 `DATA_TEXTS_RULE`＋本段 ⇒ 3/8→0/8、6/8→1/8。
# 本段只給 AI 讀；程式端 ⛔ 拿這段文字或詞判斷（DSP-091）。
# ════════════════════════════════════════════════════════════════════
#: 派工單 brief-fix6 指定的逐字（測試端獨立寫一份，⛔ 引用 `WF.DATA_TEXTS_NAME_NOTE` 自證）。
FIX6_NAME_NOTE_V1 = "（名稱也一樣：客人回名稱時，緊貼在名稱前後的道謝縮寫是道謝、不是名稱的一部分，名稱只抄道謝以外的字。）"


def test_fix6_name_note_is_fixed_string_and_exported():
    """新常數逐字＝派工單指定句、列在 `__all__`、⛔ 帶值；既有規則句逐字未改（`DATA_TEXTS_RULE` 仍以 RC1 段結尾、
    `DATA_TEXTS_PICK_NOTE`／`WRITE_INTENT_PARTIAL_NOTE` 仍＝各自 v1、三者皆不含本段）。"""
    assert WF.DATA_TEXTS_NAME_NOTE == FIX6_NAME_NOTE_V1 and "DATA_TEXTS_NAME_NOTE" in WF.__all__
    assert "{" not in FIX6_NAME_NOTE_V1
    assert WF.DATA_TEXTS_RULE.endswith(RC1_THANKS_HINT)
    assert WF.DATA_TEXTS_PICK_NOTE == RC4_PICK_NOTE_V1
    assert WF.WRITE_INTENT_PARTIAL_NOTE == FIX3_PARTIAL_NOTE_V1
    for const in (WF.DATA_TEXTS_RULE, WF.DATA_TEXTS_PICK_NOTE, WF.WRITE_INTENT_PARTIAL_NOTE,
                  WF.WRITE_INTENT_NONE_RULE, WF.PICK_ID_RULE):
        assert FIX6_NAME_NOTE_V1 not in const


def test_fix6_name_note_on_right_after_data_texts_rule_builder_level():
    """建構函式層：`data_text=True`（無追問、帶 `asked_labels`、`pick_rule`、`target_picked`、`pick_rule`＋`asked_labels`）
    ⇒ 系統句恰含一次本段、緊接 `DATA_TEXTS_RULE`；`pick_rule` ⇒ 順序為 `DATA_TEXTS_RULE`→本段→`DATA_TEXTS_PICK_NOTE`；
    off（不帶或 `data_text=False`，含 pick／target_picked／rechoice／dialog_act）⇒ 不含；任何組合的 schema（含 `data_texts`
    description）都不含，on 的 description 仍＝`DATA_TEXTS_RULE`。"""
    for el in (True, False):
        for kw in ({}, {"asked_labels": ("物件名稱",)}, {"pick_rule": True}, {"target_picked": "56906"},
                   {"pick_rule": True, "asked_labels": ("租金",)}):
            sp = WF.write_intent_system_prompt(enum_labels=el, data_text=True, **kw)
            assert sp.count(FIX6_NAME_NOTE_V1) == 1, kw
            assert "\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 in sp, kw
            if kw.get("pick_rule"):
                assert WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + RC4_PICK_NOTE_V1 in sp, kw
            else:
                assert RC4_PICK_NOTE_V1 not in sp, kw
            if kw.get("asked_labels"):
                assert sp.endswith(FIX6_NAME_NOTE_V1 + (RC4_PICK_NOTE_V1 if kw.get("pick_rule") else "") + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE + "\n"
                                   + WF.answer_text_rule(kw["asked_labels"])), kw
        for kw in ({}, {"data_text": False}, {"data_text": False, "asked_labels": ("物件名稱",)},
                   {"pick_rule": True}, {"target_picked": "56906"}, {"rechoice_type": "estate"},
                   {"dialog_act": True}):
            assert FIX6_NAME_NOTE_V1 not in WF.write_intent_system_prompt(enum_labels=el, **kw), kw
        for rf in ({"data_text": True}, {"data_text": True, "asked_labels": ("物件名稱",)},
                   {"data_text": True, "pick_ids": ("101", "102")}, {}, {"pick_ids": ("101", "102")}):
            assert FIX6_NAME_NOTE_V1 not in json.dumps(
                WF.write_intent_response_format(enum_labels=el, **rf), ensure_ascii=False), rf
        assert WF.write_intent_call_schema(enum_labels=el, data_text=True)["properties"][WF.DATA_TEXTS_KEY][
            "description"] == WF.DATA_TEXTS_RULE


async def test_fix6_name_note_sent_on_single_field_name_followup_turn(api, monkeypatch):
    """實際送出層（重現 `FA3-est-05` 形狀）：單欄追問物件名稱、客人回「大安溫馨套房3Q」⇒ on 送出的系統句含本段、緊接
    `DATA_TEXTS_RULE`、其後接名稱欄的答覆段規則；schema 不含本段。off 的同一回合 ⇒ 系統句不含本段、＝off 建構函式輸出。
    非追問回合（第一句）on ⇒ 不含（修復輪 3：本片只在單欄追問回合生效）。下一片起第一句由 `AGENT_FILL_DATA_TEXT_WIDE`
    管 ⇒ 設 off。"""
    monkeypatch.setenv(WIDE_ENV, "off")
    label = _field(EST, "title").label
    sent = {}
    for value in ("on", "off"):
        monkeypatch.setenv(ENV, value)
        w = _World()
        _seed_draft(w, EST, {"city": "台北市"}, asked=["title"])
        provider = _Provider([], [_fi(EST, data=["大安溫馨套房"], answer="大安溫馨套房", title="大安溫馨套房")])
        await w.runtime(provider).run_turn(w.ident, "大安溫馨套房3Q", w.state)
        (kw,) = provider.intent_calls
        sent[value] = kw
    on_sys = _system(sent["on"])
    assert on_sys.count(FIX6_NAME_NOTE_V1) == 1
    assert on_sys.endswith("\n" + WF.DATA_TEXTS_RULE + FIX6_NAME_NOTE_V1 + WF.FIELD_NOT_IN_FORM_NOTE + WF.ANOTHER_RECORD_NOTE + "\n" + WF.answer_text_rule((label,)))
    assert FIX6_NAME_NOTE_V1 not in json.dumps(sent["on"]["response_format"], ensure_ascii=False)
    off_sys = _system(sent["off"])
    assert FIX6_NAME_NOTE_V1 not in off_sys
    assert off_sys in {WF.write_intent_system_prompt(enum_labels=b) for b in (True, False)}
    monkeypatch.delenv(ENV, raising=False)
    w2 = _World()
    provider2 = _Provider([_out("好的")], [_fi("none", data=[])])
    await w2.runtime(provider2).run_turn(w2.ident, "我要新增一個物件", w2.state)
    (kw2,) = provider2.intent_calls
    assert FIX6_NAME_NOTE_V1 not in _system(kw2)


def test_fix6_program_does_not_judge_by_name_note():
    """DSP-091：本段只給 AI 讀——`runtime.py` 不引用這個常數、不含這段文字；`write_forms.py` 裡除定義與 `__all__` 外，
    只有 `write_intent_system_prompt` 用到它。"""
    rt_src = RUNTIME_PATH.read_text(encoding="utf-8")
    assert "DATA_TEXTS_NAME_NOTE" not in rt_src and "名稱也一樣" not in rt_src
    assert "DATA_TEXTS_RULE" in rt_src or "write_intent_system_prompt" in rt_src      # 正對照：讀的確實是 runtime 原始碼
    wf_tree = ast.parse(Path(WF.__file__).read_text(encoding="utf-8"))
    users = [fn.name for fn in ast.walk(wf_tree) if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
             and any(isinstance(n, ast.Name) and n.id == "DATA_TEXTS_NAME_NOTE" for n in ast.walk(fn))]
    assert users == ["write_intent_system_prompt"], users
