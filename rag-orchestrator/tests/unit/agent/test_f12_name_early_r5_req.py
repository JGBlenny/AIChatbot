"""unit：F12 r5「(丙) 名稱先查」——寫入流程中名稱本回合講、其他欄位仍缺 ⇒ 當回合依名稱查。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-name-lenient-f12-20261022.md` §4.2 (丙)、§4.5、§4.8 S-18～S-21；
凍結規則與清單 `acceptance-name-lenient-f12-r5-20261022.md`（FR-4、FR-11、F1 r5 項）。

F1 r5 斷言 ↔ 本檔測試（逐條）：
  - 四動作 × 唯一／多筆／查無／API 錯誤（runtime，真 registry＋mock transport）
      唯一：回覆與 off-run 逐字、`agent_state`（＝`form_sessions.collected_data`）序列化逐位相同、`name_early:one`
                                              → `test_r5_unique_*`
      多筆：當回合候選 `ids`＝同名稱出卡時的多筆候選 → `test_r5_many_*`
      查無：(甲) 候選或 `NAME_NOT_FOUND_TEXT`   → `test_r5_none_*`
      API 錯誤：現行缺欄清單                    → `test_r5_api_error_*`
  - 選定後下一回合追問其餘欄位、出卡時依選定編號精確查 → `test_r5_pick_then_asks_the_rest_and_card_uses_exact_id`
  - 不觸發：前一回合講／按鈕・`pick:`・確認記號／已有程式選定／缺欄為空／建物件／延期有 `bill_id`／
    手開帳單有 `contract_ref` 又講物件 → `test_r5_not_*`
  - 第二接入點 B2 `_write_reply_state` 缺欄分支、`closed_action_missing_labels` 永遠不觸發 → `test_r5_b2_*`
  - 開關 off／A-2a 關、`use_mock=False` 不支援動作 ⇒ 0 次查詢 → `test_r5_switch_*`、`test_r5_real_jgb_*`
  - 身分負向 ⇒ 查詢與模型呼叫皆 0 次（修繕、延期也在缺欄檢查前擋）→ `test_r5_identity_negative_*`
  - 每回合兩支解析函式各 ≤1（同回合兩次 `confirm.request` 也不重查）、模型呼叫 ≤1 → `test_r5_resolvers_*`
  - 每支查詢帶 `role_id` 且 `viewer_user_id`＝本人（僅替身）→ 各 confirm 端測試＋`test_r5_property_*`
  - 性質測試涵蓋 (丙)                        → `test_r5_property_*`
  - log／trace 捕捉：`name_early:one|many|error` 各 ≥1；(甲)(乙) 有 `name_lenient:trigger:*` → `test_r5_log_*`
資料：真 `JGBSystemAPI`＋mock transport（`assistant_demo_vendor4.json`，viewer 12291）或依 (role, viewer)
回列的假 API；模型一律假。全部離線。
"""
from __future__ import annotations

import copy
import json
import logging
import random

import pytest

from services.agent import name_match as NM
from services.agent import write_candidates as WC
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_CANDIDATES_KEY, WRITE_DRAFT_KEY
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools

from tests.unit.agent.test_f12_name_lenient_req import (  # noqa: F401 — autouse 匯入
    CONTRACT_TYPO, KEELUNG_ID, KEELUNG_TITLE, KEELUNG_TYPO, NOWHERE, STUDENT_ID, TYPO_STUDENT,
    _CC_REST, _CC_REST_TEXT, _Create, _FakeAPI, _IDENTS, _MB_REST, _MB_REST_TEXT, _agent,
    _f12_env, _ids_resp, _mutate, _out_model, _pick_ids, _pm_missing, _state_dump, _t, _tenant,
    _transport_calls, _universe,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import ASK_TEXT, OWNER, ROLE, _intent, _pm, _pool

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-name-lenient-f12-20261022")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


TWIN = "台北文山-離塵一房(國泰)"               # 12291 看得到兩筆同名物件（40303、26007）
TWIN_IDS = ["40303", "26007"]
KEELUNG_HOUSE = "基隆好房"                      # 12291 看得到六份同名合約
NOWHERE_CONTRACT = "火星合約"

# shape: 動作、名稱欄、候選型別、本句模板、四種名稱、(甲) 錯字與目標、出卡時（欄位齊）的其餘欄位與講法
_SHAPES = {
    "repair": dict(
        action="repair_create", field="estate_name", ctype="estate", say=lambda n: f"{n} 要報修",
        one="學生獨立套房", many=TWIN, none=NOWHERE, typo=TYPO_STUDENT, typo_id=STUDENT_ID,
        rest=dict(description="冷氣不冷"), rest_text="冷氣不冷"),
    "contract_create": dict(
        action="contract_create", field="estate_name", ctype="estate",
        say=lambda n: f"{n}那間要新增合約",
        one="基隆溫馨一人宅", many=TWIN, none=NOWHERE, typo=KEELUNG_TYPO, typo_id=KEELUNG_ID,
        rest=_CC_REST, rest_text=_CC_REST_TEXT),
    "manual_bill_contract": dict(
        action="manual_bill_create", field="contract_ref", ctype="contract",
        say=lambda n: f"合約 {n} 要開一張帳單",
        one="捷仕堂大一廳", many=KEELUNG_HOUSE, none=NOWHERE_CONTRACT, typo=CONTRACT_TYPO,
        typo_id="85516", rest=_MB_REST, rest_text=_MB_REST_TEXT),
    "manual_bill_estate": dict(
        action="manual_bill_create", field="estate_name", ctype="estate",
        say=lambda n: f"物件 {n} 要開一張帳單",
        one="學生獨立套房", many=TWIN, none=NOWHERE, typo=KEELUNG_TYPO, typo_id=KEELUNG_ID,
        rest=_MB_REST, rest_text=_MB_REST_TEXT),
    "due_extend": dict(
        action="bill_due_extend", field="estate_name", ctype="estate",
        say=lambda n: f"{n} 要延期繳費",
        one="基隆溫馨一人宅", many=TWIN, none=NOWHERE, typo=KEELUNG_TYPO, typo_id=KEELUNG_ID,
        rest=dict(period="7月那期", days="3"), rest_text="7月那期 延後 3 天"),
}
#: 手開帳單以物件：物件唯一但有 3 份有效合約（計畫 (丙)：無／多份有效合約 ⇒ 現行缺欄）。
_MB_ESTATE_ONE_MULTI_CONTRACTS = "基隆溫馨一人宅"


def _name_turn(shape: str, name: str):
    s = _SHAPES[shape]
    return s["say"](name), _intent(s["action"], **{s["field"]: name})


async def _run(api, shape: str, name: str, *, lenient=None, w=None):
    """名稱本回合講、其他欄位缺的一回合 ⇒ `(res, provider, w, 本回合 JGB 出向)`。"""
    text, intent = _name_turn(shape, name)
    w = w or _World()
    before = len(api._mock_transport.calls)
    res, provider = await _t(w, text, intents=[intent], lenient=lenient)
    return res, provider, w, _transport_calls(api)[before:]


def _early_marks(res) -> list:
    return [v for v in res.trace.violations if str(v).startswith(C.V_NAME_EARLY_PREFIX)]


def _user_view(res) -> tuple:
    """使用者看得到的結果＋trace（去掉 (丙) 型別標記）。"""
    return (res.answer, res.outcome, res.quick_replies, res.ask_target, res.trace.pending_id,
            [v for v in res.trace.violations if not str(v).startswith(C.V_NAME_EARLY_PREFIX)])


def _assert_viewer(calls) -> None:
    assert calls
    for _m, _path, params in calls:
        assert (params or {}).get("role_id") == ROLE and (params or {}).get("viewer_user_id") == OWNER, \
            params


def _lookup_calls(calls) -> list:
    return [c for c in calls if c[1].endswith("/estates") or "contracts" in c[1]]


async def _card_time_many_ids(api, monkeypatch, shape: str) -> list:
    """同名稱在**出卡時**（欄位齊、r5 之前的路徑：`AGENT_NAME_LENIENT=off`）列出的多筆候選編號。"""
    s = _SHAPES[shape]
    with monkeypatch.context() as mp:
        mp.setenv(NM.NAME_LENIENT_ENV, "off")
        w = _World()
        prefix = "合約 " if s["ctype"] == "contract" else ""
        res, _p = await _t(w, f"{prefix}{s['many']} {s['rest_text']}",
                           intents=[_intent(s["action"], **{s["field"]: s["many"]}, **s["rest"])])
    ids = _pick_ids(res)
    assert len(ids) >= 2, res.answer                              # 前提自證：出卡時確實是多筆候選
    return ids


# ════════════════════════════════════════════════════════════════════
# runtime：四動作 × 唯一／多筆／查無／API 錯誤
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_r5_unique_is_identical_to_off_run_and_never_lands(api, monkeypatch, shape):
    """FR-11 唯一／S-19：回覆與 off-run 逐字相同；`agent_state`（含 `estate_carry`、`write_candidates`、
    `write_draft`；即寫進 `form_sessions.collected_data` 的內容）序列化逐位相同（比值）；trace 有
    `name_early:one`；差別只有那一次帶 role＋viewer 的名稱查詢。"""
    name = _SHAPES[shape]["one"]
    on, p_on, w_on, calls_on = await _run(api, shape, name)
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, p_off, w_off, calls_off = await _run(api, shape, name)
    assert _early_marks(on) == [C.V_NAME_EARLY_ONE], on.trace.violations
    assert _early_marks(off) == []
    assert _user_view(on) == _user_view(off)
    assert on.answer.startswith("要完成這筆建立"), on.answer
    assert _state_dump(w_on) == _state_dump(w_off)
    assert w_on.draft()["fields"][_SHAPES[shape]["field"]] == name   # 草稿名稱欄仍是使用者講的值
    assert WRITE_CANDIDATES_KEY not in _agent(w_on)
    assert p_on.lenient_calls == [] and len(p_on.calls) == 0
    assert calls_off == []
    assert len(calls_on) == 1
    _assert_viewer(calls_on)


async def test_r5_unique_manual_bill_estate_with_many_valid_contracts_is_identical(api, monkeypatch):
    """手開帳單講物件、物件唯一但有效合約 3 份 ⇒ 現行缺欄（逐字、逐位同 off-run）；不另查有效合約。"""
    name = _MB_ESTATE_ONE_MULTI_CONTRACTS
    on, _p, w_on, calls_on = await _run(api, "manual_bill_estate", name)
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, _p, w_off, _c = await _run(api, "manual_bill_estate", name)
    assert _early_marks(on) == [C.V_NAME_EARLY_ONE]
    assert _user_view(on) == _user_view(off) and _state_dump(w_on) == _state_dump(w_off)
    assert len(calls_on) == 1 and calls_on[0][1].endswith("/estates"), calls_on


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_r5_many_lists_the_card_time_candidates_on_the_name_turn(api, monkeypatch, shape):
    """FR-11 多筆：講名稱那一回合就列 A-2a 候選（⛔ 出卡、⛔ 草稿寫編號），`ids`＝同名稱出卡時的多筆候選集合。"""
    s = _SHAPES[shape]
    expected = await _card_time_many_ids(api, monkeypatch, shape)
    res, provider, w, calls = await _run(api, shape, s["many"])
    assert _early_marks(res) == [C.V_NAME_EARLY_MANY], res.trace.violations
    shown = _pick_ids(res)
    assert shown == expected, (shown, expected)
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["ids"] == shown and cands["type"] == s["ctype"] and cands["field"] == s["field"]
    assert not WC.is_lenient(cands)
    assert res.trace.pending_id is None and w.writes() == [] and res.outcome["state"] == "clarifying"
    fields = w.draft()["fields"]
    assert fields[s["field"]] == s["many"] and "estate_id" not in fields and "contract_id" not in fields
    assert provider.lenient_calls == [] and len(provider.calls) == 0
    _assert_viewer(calls)
    names = [c[1] for c in calls]
    if shape == "due_extend":                                        # 名稱查詢 1 次＋annotate 有效合約 1 次（另計）
        assert len(calls) == 2 and names[0].endswith("/estates") and "contracts" in names[1], calls
    else:
        assert len(calls) == 1, calls


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_r5_none_goes_to_jia_candidates_or_not_found(api, shape):
    """FR-11 查無 ⇒ (甲)：寬鬆有候選 ⇒ (甲) 前言＋候選；寬鬆落空 ⇒ `NAME_NOT_FOUND_TEXT`（同 (甲) 出口）。"""
    s = _SHAPES[shape]
    res, provider, w, calls = await _run(api, shape, s["typo"], lenient=[_ids_resp([s["typo_id"]])])
    assert _early_marks(res) == [C.V_NAME_EARLY_NONE], res.trace.violations
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in res.trace.violations
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT + "\n"), res.answer
    assert _pick_ids(res)[0] == s["typo_id"]
    assert WC.is_lenient(_agent(w)[WRITE_CANDIDATES_KEY])
    assert len(provider.lenient_calls) == 1 and len(provider.calls) == 0
    _assert_viewer(calls)
    res2, provider2, w2, calls2 = await _run(api, shape, s["none"], lenient=[_ids_resp(["none"])])
    assert _early_marks(res2) == [C.V_NAME_EARLY_NONE]
    assert res2.answer == NM.NAME_NOT_FOUND_TEXT, res2.answer
    assert NM.V_NAME_LENIENT_NOT_FOUND_EXIT in res2.trace.violations
    assert s["field"] not in w2.draft()["fields"]
    assert len(provider2.lenient_calls) <= 1 and len(provider2.calls) == 0
    _assert_viewer(calls2)


def _fail_lookups(monkeypatch, api, ctype: str) -> list:
    hits: list = []

    async def _boom(*_a, **kw):
        hits.append(kw)
        return {"success": False, "error": {"code": 500}}

    monkeypatch.setattr(api, "get_contracts" if ctype == "contract" else "get_estate_status", _boom)
    return hits


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_r5_api_error_keeps_the_current_missing_list(api, monkeypatch, shape):
    """FR-11 沒查成（上游 500）⇒ 現行缺欄清單（⛔ 當查無、⛔ 寬鬆）；回覆與 `agent_state` 同 off-run。"""
    s = _SHAPES[shape]
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, _p, w_off, _c = await _run(api, shape, s["many"])
    monkeypatch.delenv(NM.NAME_LENIENT_ENV)
    hits = _fail_lookups(monkeypatch, api, s["ctype"])
    on, provider, w_on, _c = await _run(api, shape, s["many"], lenient=[_ids_resp(["none"])])
    assert hits and all(h.get("role_id") == ROLE and h.get("viewer_user_id") == OWNER for h in hits)
    assert len(hits) == 1
    assert _early_marks(on) == [C.V_NAME_EARLY_ERROR], on.trace.violations
    assert _user_view(on) == _user_view(off) and _state_dump(w_on) == _state_dump(w_off)
    assert on.answer.startswith("要完成這筆建立") and NM.NAME_NOT_FOUND_TEXT not in on.answer
    assert provider.lenient_calls == []
    assert not [v for v in on.trace.violations if str(v).startswith("name_lenient:")]


# ════════════════════════════════════════════════════════════════════
# 選定後：下一回合追問其餘欄位、出卡時依選定編號精確查
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("shape, pick", [("repair", "26007"), ("contract_create", "26007")])
async def test_r5_pick_then_asks_the_rest_and_card_uses_exact_id(api, monkeypatch, shape, pick):
    s = _SHAPES[shape]
    res, _p, w, _calls = await _run(api, shape, s["many"])
    assert _pick_ids(res) == TWIN_IDS
    by_id: list = []
    orig = C._estate_by_id

    async def _spy(api_, role_id, user_id, estate_id):
        by_id.append((role_id, user_id, str(estate_id)))
        return await orig(api_, role_id, user_id, estate_id)

    monkeypatch.setattr(C, "_estate_by_id", _spy)
    res2, provider2 = await _t(w, f"pick:estate:{pick}")
    assert _early_marks(res2) == [], res2.trace.violations          # 按鈕回合、已有程式選定 ⇒ 不觸發
    assert res2.outcome["state"] == "clarifying", res2.answer
    rest = WF.missing_labels(s["action"], WF.to_payload(s["action"], w.draft()["fields"]))
    assert rest and res2.answer == ASK_TEXT.format(labels="、".join(rest)), res2.answer
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0
    res3, provider3 = await _t(w, s["rest_text"], intents=[_intent(s["action"], **s["rest"])])
    assert res3.outcome["state"] == "confirm_pending", res3.answer
    assert _early_marks(res3) == []
    payload = w.pending()[res3.trace.pending_id]["payload"]
    assert str(payload["estate_id"]) == pick
    assert (ROLE, OWNER, pick) in by_id, by_id                      # 出卡時依選定編號精確查（帶 viewer）
    assert w.writes() == []


# ════════════════════════════════════════════════════════════════════
# 不觸發（runtime）
# ════════════════════════════════════════════════════════════════════
async def test_r5_not_when_the_name_was_said_in_a_previous_turn(api, monkeypatch):
    """名稱前一回合講（存在草稿）、本回合只補部分欄位 ⇒ (丙) 不觸發、0 次名稱查詢；正對照：本回合再講名稱 ⇒ 觸發。"""
    for say_again in (False, True):
        w = _World()
        with monkeypatch.context() as mp:
            mp.setenv(NM.NAME_LENIENT_ENV, "off")
            await _t(w, f"{TWIN}那間要新增合約", intents=[_intent("contract_create", estate_name=TWIN)])
        assert w.draft()["fields"]["estate_name"] == TWIN
        text = "2026-11-01 到 2027-10-31"
        if say_again:
            text = f"{TWIN} {text}"
        before = len(api._mock_transport.calls)
        res, provider = await _t(w, text, intents=[_intent(
            "contract_create", estate_name=TWIN, date_start="2026-11-01", date_end="2027-10-31")])
        calls = _transport_calls(api)[before:]
        if say_again:
            assert _early_marks(res) == [C.V_NAME_EARLY_MANY] and _pick_ids(res) == TWIN_IDS
        else:
            assert _early_marks(res) == [], res.trace.violations
            assert _lookup_calls(calls) == [], calls
            assert res.answer.startswith("要完成這筆建立"), res.answer
            assert provider.lenient_calls == []


async def test_r5_not_when_missing_list_is_empty_lookup_count_unchanged(api, monkeypatch):
    """缺欄為空 ⇒ 走現行出卡路徑（(丙) 不觸發）；名稱查找次數、回覆、`agent_state` 與 off-run 相同。"""
    out = {}
    for mode in ("on", "off"):
        if mode == "off":
            monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
        for shape in ("repair", "manual_bill_contract"):
            s = _SHAPES[shape]
            w = _World()
            before = len(api._mock_transport.calls)
            prefix = "合約 " if s["ctype"] == "contract" else ""
            name = "學生獨立套房可租補" if shape == "repair" else "捷仕堂大一廳一房"
            res, _p = await _t(w, f"{prefix}{name} {s['rest_text']}",
                               intents=[_intent(s["action"], **{s["field"]: name}, **s["rest"])])
            calls = _transport_calls(api)[before:]
            assert _early_marks(res) == []
            out[(mode, shape)] = (res.answer.replace(str(res.trace.pending_id), "<pid>"),
                                  res.outcome["state"], len(_lookup_calls(calls)))
    for shape in ("repair", "manual_bill_contract"):
        assert out[("on", shape)] == out[("off", shape)], (out[("on", shape)], out[("off", shape)])
        assert out[("on", shape)][1] == "confirm_pending"


# ════════════════════════════════════════════════════════════════════
# 第二接入點：B2 `_write_reply_state` 缺欄分支（程式先行沒發 `confirm.request` 的回合）
# ════════════════════════════════════════════════════════════════════
def _seed_draft(w: _World, action: str, fields: dict) -> None:
    from services.agent import runtime as runtime_mod
    w.state = {"agent": {WRITE_DRAFT_KEY: {
        "action": action, "fields": dict(fields), "idle_turns": 0,
        "created_by_role": runtime_mod._write_draft_owner(w.ident), "asked": []}}}


async def _b2(api, shape: str, name: str, *, lenient=None, fields_extra=None):
    s = _SHAPES[shape]
    w = _World()
    _seed_draft(w, s["action"], {s["field"]: name, **(fields_extra or {})})
    before = len(api._mock_transport.calls)
    res, provider = await _t(w, f"{name} 那筆我晚點再補", [_out_model()], intents=[_intent("none")],
                             lenient=lenient)
    return res, provider, w, _transport_calls(api)[before:]


def _b2_branch(res, branch: str) -> bool:
    return f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{branch}" in res.trace.violations


@pytest.mark.parametrize("shape", ["repair", "manual_bill_contract", "due_extend"])
async def test_r5_b2_many_lists_the_same_candidates(api, monkeypatch, shape):
    s = _SHAPES[shape]
    expected = await _card_time_many_ids(api, monkeypatch, shape)
    res, provider, w, calls = await _b2(api, shape, s["many"])
    assert WF.V_PROGRAM_CONFIRM not in res.trace.violations          # 前提：本回合沒發程式 confirm.request
    assert _b2_branch(res, WF.WRITE_REPLY_STATE_CANDIDATES), res.trace.violations
    assert _early_marks(res) == [C.V_NAME_EARLY_MANY]
    assert _pick_ids(res) == expected
    assert _agent(w)[WRITE_CANDIDATES_KEY]["ids"] == expected
    assert provider.lenient_calls == [] and res.trace.pending_id is None
    _assert_viewer(calls)


@pytest.mark.parametrize("shape", ["repair", "manual_bill_contract"])
async def test_r5_b2_none_goes_to_jia_not_found(api, shape):
    s = _SHAPES[shape]
    res, provider, w, calls = await _b2(api, shape, s["none"], lenient=[_ids_resp(["none"])])
    assert WF.V_PROGRAM_CONFIRM not in res.trace.violations
    assert _b2_branch(res, WF.WRITE_REPLY_STATE_NAME_NOT_FOUND), res.trace.violations
    assert _early_marks(res) == [C.V_NAME_EARLY_NONE]
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in res.trace.violations
    assert res.answer.endswith(NM.NAME_NOT_FOUND_TEXT) and s["none"] not in res.answer
    assert s["field"] not in w.draft()["fields"] and s["field"] in w.draft()["asked"]
    _assert_viewer(calls)


@pytest.mark.parametrize("shape", ["repair", "manual_bill_contract"])
async def test_r5_b2_unique_and_error_are_identical_to_off_run(api, monkeypatch, shape):
    s = _SHAPES[shape]
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, _p, w_off, calls_off = await _b2(api, shape, s["one"])
    off_err, _p, w_off_err, _c = await _b2(api, shape, s["many"])
    monkeypatch.delenv(NM.NAME_LENIENT_ENV)
    on, _p, w_on, calls_on = await _b2(api, shape, s["one"])
    assert _b2_branch(on, WF.WRITE_REPLY_STATE_MISSING), on.trace.violations
    assert _early_marks(on) == [C.V_NAME_EARLY_ONE]
    assert _user_view(on) == _user_view(off) and _state_dump(w_on) == _state_dump(w_off)
    assert len(_lookup_calls(calls_on)) == len(_lookup_calls(calls_off)) + 1
    hits = _fail_lookups(monkeypatch, api, s["ctype"])
    err, _p, w_err, _c = await _b2(api, shape, s["many"])
    assert len(hits) == 1 and _early_marks(err) == [C.V_NAME_EARLY_ERROR]
    assert _user_view(err) == _user_view(off_err) and _state_dump(w_err) == _state_dump(w_off_err)


async def test_r5_b2_closed_action_missing_labels_never_triggers(api, monkeypatch):
    """`closed_action_missing_labels`（欄位齊的出卡前解析補出的缺欄，如物件無有效合約）⛔ 觸發 (丙)：
    B2 手開帳單講物件（有效合約 0 份）欄位齊 ⇒ 無 `name_early:*`；confirm 端直呼也從不進 `name_early_lookup`。"""
    seen: list = []
    orig = C.name_early_lookup

    async def _spy(*a, **k):
        seen.append(a[1] if len(a) > 1 else k.get("action"))
        return await orig(*a, **k)

    from services.agent import runtime as runtime_mod
    monkeypatch.setattr(C, "name_early_lookup", _spy)
    monkeypatch.setattr(runtime_mod, "name_early_lookup", _spy)
    res, _p, _w, _c = await _b2(api, "manual_bill_estate", "學生獨立套房可租補",
                                fields_extra={"title": "管理費", "total": "1000",
                                              "date_expire": "2026-11-30"})
    assert _early_marks(res) == [] and seen == [], (res.trace.violations, seen)
    assert not _b2_branch(res, WF.WRITE_REPLY_STATE_CANDIDATES)
    for action, payload in [
        ("manual_bill_create", {"estate_name": "學生獨立套房可租補", "title": "管理費", "total": 1000,
                                "date_expire": "2026-11-30"}),
        ("manual_bill_create", {"contract_ref": KEELUNG_HOUSE, "title": "管理費", "total": 1000,
                                "date_expire": "2026-11-30"}),
        ("contract_create", {"estate_name": TWIN}),
        ("manual_bill_create", {"estate_name": TWIN}),
    ]:
        await C.closed_action_missing_labels(_pm(), action, dict(payload))
    assert seen == []
    # 正對照：同一支 spy 在 (丙) 觸發的回合會被呼叫（spy 沒壞）
    res2, _p, _w, _c = await _run(api, "repair", TWIN)
    assert seen and _early_marks(res2) == [C.V_NAME_EARLY_MANY]


# ════════════════════════════════════════════════════════════════════
# 開關、真 JGB
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("env", [(NM.NAME_LENIENT_ENV, "off"), (WF.WRITE_CANDIDATES_ENV, "off")])
@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_r5_switch_off_or_a2a_off_never_queries(api, monkeypatch, env, shape):
    monkeypatch.setenv(*env)
    res, provider, _w, calls = await _run(api, shape, _SHAPES[shape]["many"])
    assert _early_marks(res) == [] and _lookup_calls(calls) == [], calls
    assert provider.lenient_calls == [] and res.answer.startswith("要完成這筆建立")


# ════════════════════════════════════════════════════════════════════
# confirm 端（假 API，依 (role, viewer) 回列）
# ════════════════════════════════════════════════════════════════════
_KEY = ("20151", "12291")
_EST = {
    _KEY: [{"id": 101, "title": "甲棟套房A"}, {"id": 102, "title": "甲棟套房B"},
           {"id": 103, "title": "乙棟雅房"}],
    ("20151", "990002"): [{"id": 201, "title": "甲棟套房C"}, {"id": 202, "title": "丙棟頂樓"}],
}
_CON = {
    _KEY: [{"id": 301, "title": "甲棟合約", "estate_id": 101, "is_history": False},
           {"id": 302, "title": "甲棟合約", "estate_id": 102, "is_history": False},
           {"id": 303, "title": "乙棟合約", "estate_id": 103, "is_history": False}],
    ("20151", "990002"): [{"id": 401, "title": "丙棟合約", "estate_id": 202, "is_history": False}],
}
# action: (payload, 本句)；名稱「甲棟」⇒ 多筆
_CONFIRM_CASES = {
    "repair_create": ({"estate_name": "甲棟"}, "甲棟 要報修"),
    "contract_create": ({"estate_name": "甲棟"}, "甲棟那間要新增合約"),
    "manual_bill_create": ({"contract_ref": "甲棟合約"}, "合約 甲棟合約 要開帳單"),
    "bill_due_extend": ({"estate_name": "甲棟"}, "甲棟 要延期"),
}


def _ctx5(create=None, *, user_message="", typed=True, program_selected=lambda: False, marks=None):
    create = create or _Create(_ids_resp(["none"]))
    return C.NameLenientTurnCtx(
        create_factory=lambda: create, model="fake-model", reasoning_effort=None,
        user_message=user_message, touched=(), remaining_s=lambda: 20.0,
        marks=[] if marks is None else marks, user_texts=lambda: [user_message], typed=typed,
        reask_key=None, program_selected=program_selected)


def _labels(action: str, payload: dict) -> list:
    return WF.missing_labels(action, {"action": action, **payload})


def _fake(monkeypatch, *, use_mock=None) -> _FakeAPI:
    fake = _FakeAPI(copy.deepcopy(_EST), copy.deepcopy(_CON))
    if use_mock is not None:
        fake.use_mock = use_mock
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    return fake


def _assert_fake_viewer(fake: _FakeAPI, role=ROLE, user=OWNER) -> None:
    assert fake.calls
    for _what, params in fake.calls:
        assert params["role_id"] == role and params["viewer_user_id"] == user, params


@pytest.mark.parametrize("action", list(_CONFIRM_CASES))
async def test_r5_confirm_many_positive_control(monkeypatch, action):
    """正對照（下面所有「0 次」的前提）：完整業者身分、條件全成立 ⇒ 真的查、回候選形狀、帶 role＋viewer。"""
    fake = _fake(monkeypatch)
    payload, sentence = _CONFIRM_CASES[action]
    ctx = _ctx5(user_message=sentence)
    res = await C.name_early_lookup(_pm(), action, dict(payload), labels=_labels(action, payload),
                                    name_lenient=ctx)
    assert res is not None and C.is_candidate_shape(res), res
    ids = sorted(str(r["id"]) for r in res.data["candidates"])
    assert ids == (["301", "302"] if action == "manual_bill_create" else ["101", "102"])
    assert ctx.marks == [C.V_NAME_EARLY_MANY]
    _assert_fake_viewer(fake)


@pytest.mark.parametrize("who", ["no_role", "no_user", "empty_user", "tenant"])
@pytest.mark.parametrize("action", list(_CONFIRM_CASES))
async def test_r5_identity_negative_never_queries_or_calls_the_model(monkeypatch, who, action):
    """S-2：缺 role、缺 user、非 property_manager ⇒ 查詢與模型呼叫皆 0 次——`name_early_lookup` 本身，
    以及實際入口（修繕、延期：`confirm_request` 回缺欄之前；封閉三動作：`_prepare_closed_action`）。"""
    fake = _fake(monkeypatch)
    payload, sentence = _CONFIRM_CASES[action]
    ident = {"no_role": lambda: _pm_missing(role=None), "no_user": lambda: _pm_missing(user=None),
             "empty_user": lambda: _pm_missing(user="  "), "tenant": _tenant}[who]()
    create = _Create(_ids_resp(["101"]))
    ctx = _ctx5(create, user_message=sentence)
    res = await C.name_early_lookup(ident, action, dict(payload), labels=_labels(action, payload),
                                    name_lenient=ctx)
    assert res is None and fake.calls == [] and create.calls == [] and ctx.marks == []
    assert ctx.early_resolver_calls == {} and ctx.model_calls == 0
    if action in ("repair_create", "bill_due_extend"):
        await C.confirm_request(
            ident, {"summary": "s", "payload": json.dumps({"action": action, **payload},
                                                          ensure_ascii=False)},
            db_pool=_pool(), name_lenient=ctx)
    else:
        await C._prepare_closed_action(ident, action, dict(payload), candidates=True,
                                       pick_right=True, name_lenient=ctx)
    assert fake.calls == [] and create.calls == [] and ctx.early_resolver_calls == {}
    assert not [m for m in ctx.marks if m.startswith(C.V_NAME_EARLY_PREFIX)]


@pytest.mark.parametrize("env", [(NM.NAME_LENIENT_ENV, "off"), (WF.WRITE_CANDIDATES_ENV, "off"),
                                 (WF.WRITE_PROPOSAL_ENV, "off")])
@pytest.mark.parametrize("action", list(_CONFIRM_CASES))
async def test_r5_switch_off_confirm_never_queries(monkeypatch, env, action):
    monkeypatch.setenv(*env)
    fake = _fake(monkeypatch)
    payload, sentence = _CONFIRM_CASES[action]
    ctx = _ctx5(user_message=sentence)
    assert await C.name_early_lookup(_pm(), action, dict(payload), labels=_labels(action, payload),
                                     name_lenient=ctx) is None
    assert fake.calls == [] and ctx.early_resolver_calls == {}


@pytest.mark.parametrize("action", ["contract_create", "manual_bill_create"])
async def test_r5_real_jgb_not_supported_actions_never_query(monkeypatch, action):
    """`use_mock=False`（真 JGB）且動作在 `WRITE_NOT_SUPPORTED_ACTIONS` ⇒ 0 次查詢；正對照：修繕照查。"""
    fake = _fake(monkeypatch, use_mock=False)
    payload, sentence = _CONFIRM_CASES[action]
    ctx = _ctx5(user_message=sentence)
    assert await C.name_early_lookup(_pm(), action, dict(payload), labels=_labels(action, payload),
                                     name_lenient=ctx) is None
    assert fake.calls == []
    payload, sentence = _CONFIRM_CASES["repair_create"]
    ctx2 = _ctx5(user_message=sentence)
    assert await C.name_early_lookup(_pm(), "repair_create", dict(payload),
                                     labels=_labels("repair_create", payload), name_lenient=ctx2)
    assert fake.calls


async def test_r5_not_triggers_at_confirm_level(monkeypatch):
    """不觸發（confirm 端，皆 0 次查詢、0 次模型）：非打字回合（按鈕／`pick:`／確認記號）、非 runtime 脈絡、
    已有程式選定（`program_pick`、脈絡判定、判斷不了）、缺欄為空、建物件、延期已有 `bill_id`、
    手開帳單有 `contract_ref` 又講物件名稱（S-18）、名稱純數字、名稱非本回合講、延期在選對紀錄關時。"""
    fake = _fake(monkeypatch)
    repair, sentence = _CONFIRM_CASES["repair_create"]
    labels = _labels("repair_create", repair)

    def _boom():
        raise RuntimeError("probe broke")

    plain = NM.NameLenientTurn(
        create_factory=lambda: _Create(), model="m", reasoning_effort=None, user_message=sentence,
        touched=(), remaining_s=lambda: 20.0, marks=[])
    pick = {"action": "repair_create", "field": "estate_name", "type": "estate", "id": "101"}
    cases = [
        ("typed_false", "repair_create", repair, labels, _ctx5(user_message=sentence, typed=False), None),
        ("plain_ctx", "repair_create", repair, labels, plain, None),
        ("program_pick", "repair_create", repair, labels, _ctx5(user_message=sentence), pick),
        ("program_selected", "repair_create", repair, labels,
         _ctx5(user_message=sentence, program_selected=lambda: True), None),
        ("program_selected_none", "repair_create", repair, labels,
         _ctx5(user_message=sentence, program_selected=None), None),
        ("program_selected_raises", "repair_create", repair, labels,
         _ctx5(user_message=sentence, program_selected=_boom), None),
        ("empty_labels", "repair_create", repair, [], _ctx5(user_message=sentence), None),
        ("estate_create", "estate_create", {"title": "甲棟", "estate_name": "甲棟"}, ["地址"],
         _ctx5(user_message="甲棟 新增物件"), None),
        ("extend_has_bill", "bill_due_extend", {"estate_name": "甲棟", "bill_id": "9001"}, ["延後天數"],
         _ctx5(user_message="甲棟 9001 要延期"), None),
        ("mb_contract_ref_and_estate_said", "manual_bill_create",
         {"contract_ref": "乙棟合約", "estate_name": "甲棟"}, ["帳單項目"],
         _ctx5(user_message="物件 甲棟 要開帳單"), None),
        ("digit_name", "repair_create", {"estate_name": "101"}, labels,
         _ctx5(user_message="101 要報修"), None),
        ("not_said_this_turn", "repair_create", repair, labels,
         _ctx5(user_message="問題是冷氣不冷"), None),
    ]
    for tag, action, payload, labs, ctx, ppick in cases:
        before = dict(payload)
        res = await C.name_early_lookup(_pm(), action, payload, labels=labs, name_lenient=ctx,
                                        program_pick=ppick)
        assert res is None, tag
        assert fake.calls == [], (tag, fake.calls)
        assert payload == before, tag
        assert getattr(ctx, "early_resolver_calls", {}) == {}, tag
    monkeypatch.setenv(WF.PICK_RIGHT_ENV, "off")
    ext, ext_sentence = _CONFIRM_CASES["bill_due_extend"]
    assert await C.name_early_lookup(_pm(), "bill_due_extend", dict(ext),
                                     labels=_labels("bill_due_extend", ext),
                                     name_lenient=_ctx5(user_message=ext_sentence)) is None
    assert fake.calls == []
    # 正對照：同一份 fake、同一組 repair 輸入在條件全成立時會查
    monkeypatch.delenv(WF.PICK_RIGHT_ENV)
    assert await C.name_early_lookup(_pm(), "repair_create", dict(repair), labels=labels,
                                     name_lenient=_ctx5(user_message=sentence)) is not None
    assert fake.calls


async def test_r5_unique_returns_none_and_never_writes_the_payload(monkeypatch):
    """唯一 ⇒ `None`（呼叫端照現行缺欄）；⛔ 改呼叫端 payload（⛔ 寫編號、⛔ 寫系統正名）；候選 payload 是副本。"""
    fake = _fake(monkeypatch)
    for action, payload, sentence in [
        ("repair_create", {"estate_name": "乙棟", "estate_id": "999"}, "乙棟 要報修"),
        ("manual_bill_create", {"contract_ref": "乙棟合約"}, "合約 乙棟合約 要開帳單"),
        ("manual_bill_create", {"estate_name": "乙棟"}, "物件 乙棟 要開帳單"),
        ("bill_due_extend", {"estate_name": "乙棟"}, "乙棟 要延期"),
    ]:
        before = copy.deepcopy(payload)
        ctx = _ctx5(user_message=sentence)
        res = await C.name_early_lookup(_pm(), action, payload, labels=_labels(action, payload),
                                        name_lenient=ctx)
        assert res is None and payload == before, (action, payload)
        assert ctx.marks == [C.V_NAME_EARLY_ONE]
    _assert_fake_viewer(fake)
    payload = {"estate_name": "甲棟", "estate_id": "999"}
    before = copy.deepcopy(payload)
    res = await C.name_early_lookup(_pm(), "repair_create", payload,
                                    labels=_labels("repair_create", payload),
                                    name_lenient=_ctx5(user_message="甲棟 要報修"))
    assert C.is_candidate_shape(res) and payload == before
    assert "estate_id" not in res.data["payload"]


async def test_r5_resolvers_at_most_once_per_turn_even_with_two_confirm_requests(monkeypatch):
    """S-21：同一回合 `_resolve_estate_rows`、`_resolve_contract_rows` 各 ≤1 次——同回合呼兩次
    `confirm.request`（修繕、延期）或兩次 `_prepare_closed_action`（手開帳單）⇒ 第二次沿用第一次結果、不重查；
    同回合換一個名稱 ⇒ 不查（照現行）。有效合約與 annotate 查詢另計（延期多筆：annotate 1 次）。模型呼叫 ≤1。"""
    counts = {}
    for action in ("repair_create", "bill_due_extend", "manual_bill_create"):
        fake = _fake(monkeypatch)
        payload, sentence = _CONFIRM_CASES[action]
        create = _Create(_ids_resp(["none"]))
        ctx = _ctx5(create, user_message=f"{sentence} 乙棟")
        results = []
        for _ in range(2):
            if action == "manual_bill_create":
                res, _e, _s = await C._prepare_closed_action(
                    _pm(), action, dict(payload), candidates=True, pick_right=True, name_lenient=ctx)
            else:
                res = await C.confirm_request(
                    _pm(), {"summary": "s", "payload": json.dumps({"action": action, **payload},
                                                                  ensure_ascii=False)},
                    db_pool=_pool(), name_lenient=ctx)
            results.append(res)
        assert C.is_candidate_shape(results[0]) and results[0].data == results[1].data, action
        resolver = "contract" if action == "manual_bill_create" else "estate"
        assert ctx.early_resolver_calls == {resolver: 1}, (action, ctx.early_resolver_calls)
        # 同回合換名稱 ⇒ 不查
        other = dict(payload)
        other["contract_ref" if action == "manual_bill_create" else "estate_name"] = (
            "乙棟合約" if action == "manual_bill_create" else "乙棟")
        n_before = len(fake.calls)
        assert await C.name_early_lookup(_pm(), action, other, labels=_labels(action, other),
                                         name_lenient=ctx) is None
        assert len(fake.calls) == n_before and ctx.early_resolver_calls == {resolver: 1}
        name_calls = [c for c in fake.calls
                      if (c[0] == "estates") or (c[0] == "contracts" and c[1].get("keyword"))]
        annotate = [c for c in fake.calls if c[0] == "contracts" and not c[1].get("keyword")]
        assert len(name_calls) == 1, (action, fake.calls)
        assert len(annotate) == (1 if action == "bill_due_extend" else 0), (action, fake.calls)
        assert ctx.marks.count(C.V_NAME_EARLY_MANY) == 1
        assert len(create.calls) <= 1 and ctx.model_calls <= 1
        _assert_fake_viewer(fake)
        counts[action] = (len(name_calls), len(annotate))
    print(f"F12R5_RESOLVER_COUNTS {counts}")


async def test_r5_none_shares_run_once_with_jia_and_yi(monkeypatch):
    """(丙) 查無 ⇒ (甲) 與 (甲)(乙) 共用 `run_once`：同回合 (丙) 查無跑過寬鬆後，(乙) 不再跑；模型 ≤1。"""
    fake = _fake(monkeypatch)
    create = _Create(_ids_resp(["103"]))
    ctx = _ctx5(create, user_message="乙棟雅屋 要報修")
    res = await C.name_early_lookup(_pm(), "repair_create", {"estate_name": "乙棟雅屋"},
                                    labels=["問題描述"], name_lenient=ctx)
    assert res is not None and res.data.get(C.NAME_LENIENT_KEY) is True
    assert ctx.marks[:2] == [C.V_NAME_EARLY_NONE, C.V_NAME_LENIENT_TRIGGER_NOTFOUND], ctx.marks
    again = await C.missing_name_lenient(_pm(), "contract_create", {},
                                         labels=_labels("contract_create", {}), name_lenient=ctx)
    assert again is None and ctx.calls == 1 and len(create.calls) == 1
    _assert_fake_viewer(fake)


# ════════════════════════════════════════════════════════════════════
# 性質測試（≥200 組，涵蓋 (丙)）
# ════════════════════════════════════════════════════════════════════
R5_PROPERTY_CASES = 240
_R5_PATHS = {
    "repair": ("repair_create", "estate_name", "estate"),
    "contract_create": ("contract_create", "estate_name", "estate"),
    "bill_contract": ("manual_bill_create", "contract_ref", "contract"),
    "bill_estate": ("manual_bill_create", "estate_name", "estate"),
    "due_extend": ("bill_due_extend", "estate_name", "estate"),
}


class _FailingAPI(_FakeAPI):
    async def get_estate_status(self, *a, **kw):
        await super().get_estate_status(*a, **kw)
        return {"success": False, "error": {"code": 500}}

    async def get_contracts(self, *a, **kw):
        await super().get_contracts(*a, **kw)
        return {"success": False, "error": {"code": 500}}


async def test_r5_property_name_early_only_when_said_typed_missing_and_in_identity(monkeypatch):
    """F1 性質測試 (丙)：隨機 240 組（身分 × 五條路徑 × 名稱講法 × 本回合講否 × 打字否 × 缺欄空否 × 上游失敗 ×
    假模型）。斷言：(1) 有任何查詢 ⇔ 本回合講、打字、缺欄非空、名稱非純數字、身分完整；
    (2) 兩支解析函式各 ≤1、模型 ≤1；(3) 從不改呼叫端 payload；(4) 唯一／錯誤 ⇒ `None`、多筆 ⇒ 候選 ⊆ 本身分列、
    查無 ⇒ (甲) 結果或 `None`；(5) 每支出向帶 role 且 viewer＝本人。"""
    dist = {"one": 0, "many": 0, "none": 0, "error": 0, "skip": 0}
    for seed in range(R5_PROPERTY_CASES):
        rng = random.Random(10_000 + seed)
        estates, contracts = _universe(seed)
        key = rng.choice(_IDENTS)
        role, user = key
        path = rng.choice(list(_R5_PATHS))
        action, field, ctype = _R5_PATHS[path]
        own = (contracts if ctype == "contract" else estates)[key]
        kind = rng.choice(["exact", "substring", "typo", "common", "common", "common", "garbage", "digit"])
        if kind == "exact":
            name = rng.choice(own)["title"]
        elif kind == "substring":
            t = rng.choice(own)["title"]
            name = t[: max(2, len(t) // 2)]
        elif kind == "typo":
            name = _mutate(rng, rng.choice(own)["title"])
        elif kind == "common":
            name = rng.choice(["台北", "基隆", "套房", "合成展示合約", "雅房"])
        elif kind == "garbage":
            name = rng.choice(["火星基地", "隨便講講", "ＸＹＺ大樓"])
        else:
            name = str(rng.randint(1, 10 ** 6))
        said = rng.random() < 0.75
        typed = rng.random() < 0.85
        has_missing = rng.random() < 0.85
        good_ident = rng.random() < 0.9
        failing = rng.random() < 0.1
        fake = (_FailingAPI if failing else _FakeAPI)(estates, contracts)
        monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
        ident = _pm(user=user, role=role) if good_ident else rng.choice(
            [_tenant(), _pm_missing(role=None), _pm_missing(user=None)])
        payload = {field: name}
        if path == "repair":
            payload["description"] = "漏水"
        labels = _labels(action, payload) if has_missing else []
        if has_missing and not labels:
            labels = ["其他"]
        sentence = f"{name} 幫我處理" if said else "其他欄位我補一下"
        own_ids = {str(r["id"]) for r in own}
        create = _Create(fn=lambda kw, _r=rng: _ids_resp(
            _r.sample(sorted(own_ids), min(2, len(own_ids))) if _r.random() < 0.5 else ["none"]))
        ctx = _ctx5(create, user_message=sentence, typed=typed)
        before = copy.deepcopy(payload)
        res = await C.name_early_lookup(ident, action, payload, labels=labels, name_lenient=ctx)
        tag = (seed, path, name, said, typed, has_missing, good_ident, failing)
        expect = said and typed and has_missing and good_ident and not name.strip().isdigit()
        # (1)
        assert bool(ctx.early_resolver_calls) is expect, tag
        assert payload == before, tag                                        # (3)
        if not expect:
            assert fake.calls == [] and create.calls == [] and res is None, tag
            dist["skip"] += 1
            continue
        # (2)
        assert all(v == 1 for v in ctx.early_resolver_calls.values()), tag
        assert len(ctx.early_resolver_calls) == 1 and len(create.calls) <= 1, tag
        # (5)
        for _what, params in fake.calls:
            assert params["role_id"] == role and params["viewer_user_id"] == user, (tag, params)
        status = [m for m in ctx.marks if m.startswith(C.V_NAME_EARLY_PREFIX)]
        assert len(status) == 1, (tag, ctx.marks)
        st = status[0][len(C.V_NAME_EARLY_PREFIX):]
        dist[st] += 1
        # (4)
        if st in ("one", "error"):
            assert res is None and create.calls == [], tag
            if st == "error":
                assert failing, tag
        elif st == "many":
            assert C.is_candidate_shape(res), tag
            cands = {str(r["id"]) for r in res.data["candidates"]}
            assert len(cands) >= 2 and cands <= own_ids, tag
            assert res.data["field"] == field and res.data[C.CANDIDATE_TYPE_KEY] == ctype, tag
            assert create.calls == [], tag
        else:
            if res is not None and C.is_name_not_found(res) is None:
                cands = {str(r["id"]) for r in res.data["candidates"]}
                assert cands <= own_ids and res.data.get(C.NAME_LENIENT_KEY) is True, tag
    print(f"F12R5_PROPERTY cases={R5_PROPERTY_CASES} dist={dist}")
    assert dist["one"] >= 15 and dist["many"] >= 15 and dist["none"] >= 15, dist
    assert dist["error"] >= 5 and dist["skip"] >= 40, dist


# ════════════════════════════════════════════════════════════════════
# log／trace 捕捉（S-20）
# ════════════════════════════════════════════════════════════════════
async def test_r5_log_and_trace_carry_name_early_marks_and_lenient_triggers(api, monkeypatch, caplog):
    """(丙) 案例的捕捉內必須搜得到 `name_early:one`、`name_early:many`、`name_early:error`（各 ≥1）；
    (甲)(乙) 案例必須搜得到 `name_lenient:trigger:*`；搜不到 ⇒ 捕捉壞了。log／trace 不含名稱與本句。"""
    caplog.set_level(logging.DEBUG)
    one, *_ = await _run(api, "repair", _SHAPES["repair"]["one"])
    many, *_ = await _run(api, "repair", TWIN)
    jia, *_ = await _run(api, "repair", TYPO_STUDENT, lenient=[_ids_resp([STUDENT_ID])])
    w_yi = _World()
    yi, _p = await _t(w_yi, f"{KEELUNG_TYPO}那間要新增合約", intents=[_intent("contract_create")],
                      lenient=[_ids_resp([KEELUNG_ID])])
    with monkeypatch.context() as mp:
        _fail_lookups(mp, api, "estate")
        err, *_ = await _run(api, "repair", TWIN)
    logs = "\n".join(r.getMessage() for r in caplog.records)
    for res, mark in ((one, C.V_NAME_EARLY_ONE), (many, C.V_NAME_EARLY_MANY),
                      (err, C.V_NAME_EARLY_ERROR)):
        assert mark in res.trace.violations, (mark, res.trace.violations)
        assert f"[agent] {mark}" in logs, mark
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in jia.trace.violations
    assert C.V_NAME_LENIENT_TRIGGER_MISSING in yi.trace.violations
    assert f"[agent] {C.V_NAME_LENIENT_TRIGGER_NOTFOUND}" in logs
    assert f"[agent] {C.V_NAME_LENIENT_TRIGGER_MISSING}" in logs
    early_logs = [r.getMessage() for r in caplog.records if C.V_NAME_EARLY_PREFIX in r.getMessage()]
    trace_dump = json.dumps([list(r.trace.violations) for r in (one, many, err)], ensure_ascii=False)
    for secret in (TWIN, _SHAPES["repair"]["one"], "要報修", *TWIN_IDS):
        assert secret not in trace_dump, secret
        for line in early_logs:
            assert secret not in line, (secret, line)
