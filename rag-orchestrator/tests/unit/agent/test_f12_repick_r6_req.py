"""unit：F12 r6「選定後可改選」——候選集選定後、出卡前，客人改口由 AI 理解（`pick_id`）、程式決定改不改選。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-name-lenient-f12-20261022.md` §11.4；凍結規則與清單
`acceptance-name-lenient-f12-r6-20261024.md`（FR-12～FR-15、F1 r6 項）。業主裁定：r6-1 (a) 套用所有候選集、
r6-2 (a)、r6-3 (a) 加告知固定句、r6-6 (a) 不另寫 dialog 標記（F1 (l) 不適用）、r6-7 (a) `retract`。
§11.14（r6 復原第 4 輪）：已選定的回合 schema 另加必填封閉值 `rechoice`（`keep`／`switch`／`retract`，排在 `pick_id`
之前），`pick_id` enum 回到 `ids`＋`none`；撤回改由 `rechoice=retract` 觸發（取代 §11.4 第 7a 點的 `pick_id`＝`retract`）；
已選定回合 `pick_id` 只在 `rechoice=switch` 時採用。

F1 r6 斷言 ↔ 本檔測試（逐條）：
  - (a)  選定後出卡前仍附 `pick_id`（enum＝`ids`＋`none`；另附 `rechoice`）、出卡後不附；寬鬆改寫後
         `pick_offered`＝`ids`                       → `test_a_*`
  - (a2) 已撤回狀態四種來源、兩入口、名稱合併 V7-1、取列 V7-3、B2、重新選定、新名稱、取列為空；計數量尺自證
         （`test_a2_premise_*`、`test_a2_b2_premise_*`）    → `test_a2_*`
  - (b)  打字改選／不動／整句編號／候選集外編號（`pick_matches_name` 0 次）／被退回／判定順序 → `test_b_*`
  - (c)  寬鬆改選改寫正名與指紋、A-2a 不改寫、取名稱回 None → `test_c_*`
  - (d)  名稱合併（意圖與模型提議兩處）           → `test_d_*`
  - (e)  情境形狀 C03、C14、C10b、A→B→A           → `test_e_*`
  - (f)  開關矩陣（A-2a off 逐位相同、F12 off 且 A-2a on 照 r6——F12 off 時精確同名候選集選定後、出卡前的窗口
         是「欄位齊、選定那筆出不了卡」，用延期繳費）→ `test_f_*`（未選定時的既有測試全過見收案報告）
  - (g)  身分與綁定（換使用者、換動作、指紋改變）＋性質測試 → `test_g_*`
  - (h)  正對照：本檔 `test_*_control_*`（monkeypatch）；原始碼暫改見收案報告
  - (j)  r6-3 告知句（名稱取 API 列 title、dialog 不含名稱）＋B 片固定句測試 → `test_j_*`、
         `test_b_write_replies_program_req.test_v16b_program_texts_are_fixed_constants`
  - (k)  `withdrawn`／已改寫鍵形狀、原講法來源、保留編號、讀回竄改 → `test_k_*`
  - (m)  候選集內講法                              → `test_m_*`
  - (n)  只撤回 `rechoice=retract`                 → `test_n_*`
  - (i)  grep（收案報告）
  - §11.14 F1 另加：第 1 點句中講編號 → `test_s1_*`；第 2 點 `rechoice` → `test_rc_*`；第 3 點選定後誤換動作
         → `test_s3_*`（原始碼暫改正對照見收案報告）
資料：真 `JGBSystemAPI`＋mock transport（`assistant_demo_vendor4.json`，viewer 12291／role 20151）或依
(role, viewer) 回列的假 API；模型一律假。全部離線。期望值為 fixture 原始 JSON 人工查證：
  - 「宏匯個人」查無 ⇒ 寬鬆：56907「瑞光宏匯C個人(空租)」、56906「瑞光宏匯B個人」、56905「瑞光宏匯A法人」；
  - 「瑞光好房1(個人租客)」兩筆同名（58207、55455）；「瑞光好房個人租客」查無 ⇒ 寬鬆（55455、55454、55456），
    55455 改寫後的正名與 58207 相同；
  - 「基隆溫心一人宅」(乙) 缺名稱 ⇒ 寬鬆：67652「基隆溫馨一人宅套房」、67649「基隆獨立共生公寓雅房」；
  - 「海大質感獨立套房高級廚房可租補」兩筆同名（68007、67651）；8月那期只有 68007 有帳單 760889；
  - 「小南門那個分租套房」查無 ⇒ 寬鬆：45728「…分租套房B」、45729「…分租套房Ｃ」、49871「…分租套房D」。
"""
from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from services.agent import runtime as runtime_mod
from services.agent import write_candidates as WC
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_CANDIDATES_KEY
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools

from tests.unit.agent.test_a2a_write_candidates_req import _intent_raw, _SpyReg
from tests.unit.agent.test_f12_name_lenient_req import (  # noqa: F401 — autouse 匯入
    _CC_REST, _CC_REST_TEXT, _CC_TYPO, _FakeAPI, _IDENTS, _agent, _f12_env, _ids_resp, _intent_rc6, _NO_RC,
    _pick_ids, _snap, _universe,
)
from tests.unit.agent.test_runtime_req import _tool_call_response
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    OWNER, ROLE, STUDENT_ESTATE, _intent, _out, _pm, _Provider,
)

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-name-lenient-f12-20261022")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


@pytest.fixture
def closing_handoff_off(monkeypatch):
    """E 片：這類「送出內容與改前逐字相同」的測試釘住 `AGENT_CLOSING_HANDOFF=off`（E 片 on 的行為見 test_closing_handoff_e_req.py）。"""
    monkeypatch.setenv("AGENT_CLOSING_HANDOFF", "off")


RT = runtime_mod.AgentRuntime
CC = "contract_create"
DUE = "bill_due_extend"
STUDENT_ID = "67338"
MODEL_SAID = "模型自己寫的話。"


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
async def _t(w: _World, message, script=(), *, intents=None, lenient=None, program_first=True):
    """一回合：回 `(result, provider)`。`program_first=False` ⇒ 不走程式優先（模型提議先於意圖取用，
    用來測 `proposal_program` 入口在撤回那一回合的關口）。"""
    provider = _Provider(list(script), intents, lenient)
    rt = w.runtime(provider, program_first=program_first)
    res = await rt.run_turn(w.ident, message, w.state)
    assert rt._write_intent_calls == {}
    return res, provider


def _cands(w: _World):
    return _agent(w).get(WRITE_CANDIDATES_KEY)


def _enum(kw):
    props = kw["response_format"]["json_schema"]["schema"]["properties"]
    return props[WF.PICK_ID_KEY]["enum"] if WF.PICK_ID_KEY in props else None


def _schema(kw) -> dict:
    return kw["response_format"]["json_schema"]["schema"]


# 舊式假意圖的 `rechoice` 值（替身 `_adapt_intent_target` 依語意換成指令清單；計畫 plan-post-pick-commands §4.2）
SWITCH = "switch"
KEEP = "keep"
RETRACT = "retract"


def _sw(action: str, pid, **fields):
    """已選定回合 AI 判改選：`rechoice=switch`＋`pick_id`。"""
    return _intent_rc6(action, SWITCH, pid, **fields)


def _rt(action: str, **fields):
    """已選定回合 AI 判撤回：`rechoice=retract`、`pick_id=none`（規則句：不是 switch 時填 none）。"""
    return _intent_rc6(action, RETRACT, WF.PICK_ID_NONE, **fields)


def _cmd(action: str, *target, **fields):
    """選定後回合的假意圖：直接給指令清單（`target` 鍵一定在 ⇒ 替身 `_adapt_intent_target` 原樣送）。
    每個指令 `(op, value)`；`_cmd(CC, ("name", "甲"), ("pick", "56907"))`。"""
    obj = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()],
           WF.PICK_TARGET_KEY: [{"op": op, "value": value} for op, value in target]}
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


def _card_id(w: _World, res, key: str = "estate_id"):
    assert res.outcome["state"] == "confirm_pending", res.answer
    return str(w.pending()[res.trace.pending_id]["payload"][key])


def _proposal(action: str, **payload):
    return _tool_call_response("confirm.request", {"summary": "確認", "payload": json.dumps(
        {"action": action, **payload}, ensure_ascii=False)})


def _assert_via_proposal(res) -> None:
    """模型提議轉成程式依草稿發出的 `confirm.request`（`proposal_program`）：有提議標記、程式發出標記、⛔ 提議未發出
    標記。（已撤回時關口在經 registry 之前就重列，`confirm_source:` 來源標記只在經 registry 時才加，故不以它判。）"""
    v = res.trace.violations
    assert WF.V_WRITE_PROPOSAL in v and WF.V_PROGRAM_CONFIRM in v, v
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED not in v, v


def _ask(res) -> bool:
    return res.trace.pending_id is None and res.outcome["state"] == "clarifying"


@dataclass
class _Src:
    """一種候選集來源的一段對話：列候選、按鈕選定 `picked`；`other`＝同一份 `ids` 內另一筆。"""
    name: str
    action: str
    key: str
    ctype: str
    ids: list
    picked: str
    other: str
    spoken: str                      # 列候選前客人講過的名稱（假模型可能從上下文填回）
    rest: dict
    rest_text: str
    titles: dict = field(default_factory=dict)
    card_key: str = "estate_id"
    other_card: str = ""             # 出卡後 payload[card_key] 的期望值（改選到 other 時）
    picked_card: str = ""


_SOURCES = {
    "jia": dict(text="宏匯個人那間要簽約", intent=lambda: _intent(CC, estate_name="宏匯個人"),
                lenient=[_ids_resp(["56907", "56906", "56905"])],
                src=_Src("jia", CC, "estate_name", "estate", ["56907", "56906", "56905"], "56906", "56907",
                         "宏匯個人", _CC_REST, _CC_REST_TEXT,
                         {"56907": "瑞光宏匯C個人(空租)", "56906": "瑞光宏匯B個人", "56905": "瑞光宏匯A法人"},
                         other_card="56907", picked_card="56906")),
    "yi": dict(text=f"{_CC_TYPO}那間要新增合約", intent=lambda: _intent(CC),
               lenient=[_ids_resp(["67652", "67649"])],
               src=_Src("yi", CC, "estate_name", "estate", ["67652", "67649", "24211", "22481", "22482"],
                        "67652", "67649",
                        _CC_TYPO, _CC_REST, _CC_REST_TEXT,
                        {"67652": "基隆溫馨一人宅套房", "67649": "基隆獨立共生公寓雅房"},
                        other_card="67649", picked_card="67652")),
    "exact": dict(text="瑞光好房1(個人租客) 這間要簽新租約",
                  intent=lambda: _intent(CC, estate_name="瑞光好房1(個人租客)"), lenient=None,
                  src=_Src("exact", CC, "estate_name", "estate", ["58207", "55455"], "58207", "55455",
                           "瑞光好房1(個人租客)", _CC_REST, _CC_REST_TEXT,
                           {"58207": "瑞光好房1(個人租客)", "55455": "瑞光好房1(個人租客)"},
                           other_card="55455", picked_card="58207")),
    "pick_right": dict(text="海大質感獨立套房高級廚房可租補 8月那期 要延期",
                       intent=lambda: _intent(DUE, estate_name="海大質感獨立套房高級廚房可租補", period="8月那期"),
                       lenient=None,
                       src=_Src("pick_right", DUE, "estate_name", "estate", ["68007", "67651"], "67651", "68007",
                                "海大質感獨立套房高級廚房可租補", {"days": "3"}, "延後 3 天",
                                {"68007": "海大質感獨立套房高級廚房可租補", "67651": "海大質感獨立套房高級廚房可租補"},
                                card_key="bill_id", other_card="760889")),
}
ALL_SOURCES = list(_SOURCES)


async def _listed(name: str, w=None):
    """列候選（未選定）⇒ `(w, src, res)`。"""
    spec = _SOURCES[name]
    w = w or _World()
    res, _p = await _t(w, spec["text"], intents=[spec["intent"]()], lenient=spec["lenient"])
    src = spec["src"]
    assert _pick_ids(res) == src.ids, res.answer                     # 前提自證：fixture 對到期望的候選
    assert _cands(w)["picked"] is None and res.trace.pending_id is None
    return w, src, res


async def _picked(name: str, w=None, pick=None):
    """列候選後按鈕選定 ⇒ 追問其餘欄位（⛔ 出卡）⇒ `(w, src)`。"""
    w, src, _res = await _listed(name, w)
    pick = pick or src.picked
    res, _p = await _t(w, f"pick:{src.ctype}:{pick}")
    assert WC.V_CANDIDATE_PICK_BUTTON in res.trace.violations, res.trace.violations
    assert _ask(res), res.answer
    assert _cands(w)["picked"] == pick
    return w, src


def _fill_intent(src: _Src, **extra):
    return _intent(src.action, **src.rest, **extra)


def _withdrawn_state(w: _World) -> tuple:
    c = _cands(w)
    return (list(c["ids"]), c["name_fp"], c.get(WC.LENIENT_KEY), c.get(WC.REWRITTEN_KEY),
            c.get(WC.ORIGIN_KEY), w.draft()["fields"].get("estate_name"))


class _BillsCount:
    """`api.get_bills` 計數（選對紀錄 `scope_pick` 帳單解析 0 次的證據）。"""

    def __init__(self, api, monkeypatch):
        self.n = 0
        inner = api.get_bills

        async def spy(*a, **k):
            self.n += 1
            return await inner(*a, **k)

        monkeypatch.setattr(api, "get_bills", spy)


# ════════════════════════════════════════════════════════════════════
# (a) 選定後出卡前仍附 `pick_id`
# ════════════════════════════════════════════════════════════════════
def _assert_cmd_offered(kw, ids: list, picked: str) -> None:
    """選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.2）：已選定回合 ⇒ schema 沒有 `pick_id`、
    `rechoice`、`new_name`（`_enum` 為 `None`）；根層必填 `target`（排在最後，說明＝帶現選定編號的規則句）；
    系統句＝`write_intent_system_prompt(enum_labels=…)`（不帶 `pick_rule`）＋「\\n」＋規則句（含「編號 {picked}」）。
    （與對照探針 `abl` 變體 `build()` 的逐位比對見 `test_post_pick_commands_req.py` F1 (a)。）"""
    assert _enum(kw) is None
    schema = _schema(kw)
    keys = list(schema["properties"])
    assert keys[-1] == WF.PICK_TARGET_KEY and schema["required"][-1] == WF.PICK_TARGET_KEY, (keys, schema["required"])
    assert not {WF.PICK_ID_KEY, "rechoice", "new_name"} & set(keys), keys
    rule = WF.pick_target_rule(picked)
    assert rule is not None and f"編號 {picked}" in rule
    assert schema["properties"][WF.PICK_TARGET_KEY]["description"] == rule
    system = kw["messages"][0]["content"]
    assert system in {WF.write_intent_system_prompt(enum_labels=b) + "\n" + rule
                      for b in (False, True)}, system


def _assert_cmd_absent(kw, ids: list) -> None:
    """未選定、已撤回 ⇒ enum＝`ids`＋`none`、⛔ `target`／`rechoice`／`new_name`，系統句＝未選定時的系統句（⛔ 規則句）。"""
    assert _enum(kw) == ids + [WF.PICK_ID_NONE]
    schema = _schema(kw)
    for key in (WF.PICK_TARGET_KEY, "rechoice", "new_name"):
        assert key not in schema["properties"] and key not in schema["required"], key
    system = kw["messages"][0]["content"]
    assert system in {WF.write_intent_system_prompt(enum_labels=b, pick_rule=True) for b in (False, True)}
    assert "rechoice" not in system and "target" not in system


@pytest.mark.parametrize("name", ALL_SOURCES)
@pytest.mark.usefixtures("closing_handoff_off")
async def test_a_pick_id_still_offered_after_pick_and_not_after_the_card(api, name):
    """(a)＋選定後回合改指令式（計畫 plan-post-pick-commands §4.2）：選定後、出卡前的打字回合，意圖呼叫仍附候選段；
    schema 改附 `target`（無 `pick_id`），系統句最末接帶現選定編號的規則句；出卡（候選集清掉）後的回合不附 `pick_id`。"""
    w, src = await _picked(name)
    res, provider = await _t(w, "嗯我想一下", [_out(MODEL_SAID)], intents=[_intent("none")])
    (kw,) = provider.intent_calls
    _assert_cmd_offered(kw, src.ids, src.picked)
    assert _cands(w)["picked"] == src.picked                          # 選定不動
    if name == "pick_right":
        return                                                        # 67651 該期無帳單 ⇒ 不出卡
    res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert _card_id(w, res2, src.card_key) == src.picked_card
    assert _cands(w) is None
    _res3, provider3 = await _t(w, "好的謝謝", [_out(MODEL_SAID)], intents=[_intent("none")])
    assert all(_enum(k) is None for k in provider3.intent_calls)


@pytest.mark.parametrize("name", ALL_SOURCES)
@pytest.mark.usefixtures("closing_handoff_off")
async def test_rc_unpicked_and_withdrawn_prompt_and_schema_identical_to_unpicked(api, name):
    """未選定、已撤回 ⇒ 意圖呼叫的系統句與 `response_format` 與未選定時**逐字相同**（⛔ `target`、⛔ 規則句、
    enum＝`ids`＋`none`；Q1 (a)：已撤回回合照第 5 輪）。四種來源各一；同一句、同一份 `ids`。"""
    w0, src, _r = await _listed(name)
    _res, provider = await _t(w0, "嗯我想一下", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    (unpicked,) = provider.intent_calls
    _assert_cmd_absent(unpicked, src.ids)
    w, src = await _picked(name)
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(src.action)])
    assert WC.is_withdrawn(_cands(w))
    _res, provider = await _t(w, "嗯我想一下", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    (withdrawn,) = provider.intent_calls
    _assert_cmd_absent(withdrawn, src.ids)
    assert withdrawn["messages"][0] == unpicked["messages"][0]
    assert json.dumps(withdrawn["response_format"], ensure_ascii=False, sort_keys=False) == \
        json.dumps(unpicked["response_format"], ensure_ascii=False, sort_keys=False)


async def test_rc_control_offering_rechoice_when_withdrawn_breaks_identity(api, monkeypatch):
    """正對照（「已撤回與未選定時 schema 與系統句逐字同未選定」）：組 schema／系統句時一律帶候選集原選定編號
    （已撤回也帶）⇒ 上一支的逐字相同失敗（已撤回那回合出現 `target`）。"""
    orig_fmt = WF.write_intent_response_format
    orig_sys = WF.write_intent_system_prompt

    def fmt(**kw):
        if kw.get("pick_ids") is not None and kw.get("target_picked") is None:
            kw["pick_ids"], kw["target_picked"] = None, "58207"
        return orig_fmt(**kw)

    def sysp(**kw):
        if kw.get("pick_rule") and kw.get("target_picked") is None:
            kw["pick_rule"], kw["target_picked"] = False, "58207"
        return orig_sys(**kw)

    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    monkeypatch.setattr(WF, "write_intent_response_format", fmt)
    monkeypatch.setattr(WF, "write_intent_system_prompt", sysp)
    _res, provider = await _t(w, "嗯我想一下", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    (kw,) = provider.intent_calls
    assert WF.PICK_TARGET_KEY in _schema(kw)["properties"]
    with pytest.raises(AssertionError):
        _assert_cmd_absent(kw, src.ids)


_RG_TYPO = "瑞光好房個人租客"
#: AI 挑滿 `NAME_LENIENT_CAP`（5）筆 ⇒ 補齊步驟加不進同正名的 58207（候選集外、本人可見、與 55455 同正名）。
_RG_IDS = ["55455", "55454", "55456", "56907", "56906"]


async def _rg_lenient_picked():
    """寬鬆候選（AI 挑滿 5 筆、不含 58207）按鈕選 55455 ⇒ 草稿改寫成「瑞光好房1(個人租客)」（與 58207 同正名）。"""
    w = _World()
    res, _p = await _t(w, f"{_RG_TYPO}那間要簽約", intents=[_intent(CC, estate_name=_RG_TYPO)],
                       lenient=[_ids_resp(_RG_IDS)])
    assert _pick_ids(res) == _RG_IDS, res.answer
    res2, _p = await _t(w, "pick:estate:55455")
    assert WC.V_NAME_LENIENT_REWRITE in res2.trace.violations
    assert w.draft()["fields"]["estate_name"] == "瑞光好房1(個人租客)"
    c = _cands(w)
    assert c["picked"] == "55455" and WC.is_lenient(c) and WC.is_rewritten(c)
    return w


def _seed_full_draft(w: _World) -> None:
    """已選定、草稿其餘欄位已齊、還沒出卡（例：上一回合出卡沒成）——出卡前解析此時會真的依名稱查
    （⛔ 因缺欄回 `None`），依名稱重查與依 `ids` 取列的差別才看得到。"""
    w.draft()["fields"].update(_CC_REST)


@pytest.mark.parametrize("full", [False, True], ids=["partial", "full"])
@pytest.mark.usefixtures("closing_handoff_off")
async def test_a_lenient_rewritten_offers_every_id_not_just_the_same_title(api, full):
    """(a)：寬鬆候選選定並改寫名稱後、仍選定 ⇒ `pick_offered`（enum）＝候選集 `ids`（本人可見者）；⛔ 依改寫後的
    名稱重查（那只剩同正名者：55455，另帶一筆候選集外的 58207）。其餘欄位未齊、已齊兩種草稿各一。"""
    w = await _rg_lenient_picked()
    if full:
        _seed_full_draft(w)
    _res, provider = await _t(w, "這兩間差在哪裡？", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    (kw,) = provider.intent_calls
    _assert_cmd_offered(kw, _RG_IDS, "55455")
    data = kw["messages"][-2]["content"]                      # 資料段＝候選集 `ids` 內的列（已選定回合沒有 enum）
    assert all(i in data for i in _RG_IDS) and "58207" not in data, data


async def test_a_control_requery_by_rewritten_name_offers_only_the_same_title(api, monkeypatch):
    """正對照（(a)「改回依名稱重查 ⇒ 失敗」）：取列改成忽略已改寫鍵（依草稿名稱走出卡前解析）⇒ 已齊草稿那支的
    enum 只剩同正名且在 `ids` 內的 55455。"""
    orig = RT._write_candidates_fetch_rows

    async def by_name(self, acc, identity, cands, payload):
        return await orig(self, acc, identity,
                          {k: v for k, v in cands.items() if k != WC.REWRITTEN_KEY}, payload)

    w = await _rg_lenient_picked()
    _seed_full_draft(w)
    monkeypatch.setattr(RT, "_write_candidates_fetch_rows", by_name)
    _res, provider = await _t(w, "這兩間差在哪裡？", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    (kw,) = provider.intent_calls
    data = kw["messages"][-2]["content"]                      # 已選定回合沒有 enum ⇒ 看資料段只剩同正名且在 `ids` 內的 55455
    assert "55455" in data and "55454" not in data and "58207" not in data, data


# ════════════════════════════════════════════════════════════════════
# (a2) 已撤回狀態
# ════════════════════════════════════════════════════════════════════
async def _retract(w: _World, src: _Src, *, program_first=True, script=()):
    before = _withdrawn_state(w)
    confirms = len(w.reg.confirm_calls())
    res, provider = await _t(w, "剛剛選錯了", list(script) + [_out(MODEL_SAID)] * 2,
                             intents=[_rt(src.action)], program_first=program_first)
    c = _cands(w)
    assert c["picked"] is None and c[WC.WITHDRAWN_KEY] is True, c
    assert _withdrawn_state(w) == before                              # ids／指紋／寬鬆鍵／原講法／草稿名稱逐位相同
    loaded, invalid = WC.load_write_candidates(c)
    assert loaded == c and invalid is False
    assert RT._write_candidates_bound(c, w.ident, w.draft())          # 仍綁定
    assert WC.V_CANDIDATE_RETRACT_TYPED in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATES_SHAPE_INVALID not in res.trace.violations
    assert _pick_ids(res) == src.ids and _ask(res), res.answer        # 重列同一份 ids、不出卡
    assert len(w.reg.confirm_calls()) == confirms                     # `confirm.request` 經 registry 0 次
    return res, provider, before


@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_a2_retract_then_fill_relists_the_same_ids_wd_program(api, monkeypatch, name):
    """(a2) 四種來源 × `wd_program` 入口：已選定 ⇒ `retract` ⇒ 已撤回（`picked` 清、`withdrawn`、其餘逐位相同、
    讀回合法、仍綁定）、重列同一份 `ids`；下一回合只補齊欄位 ⇒ 仍重列同一份 `ids`、不出卡、`confirm.request`
    經 registry 0 次、選對紀錄帳單解析 0 次。"""
    bills = _BillsCount(api, monkeypatch)
    w, src = await _picked(name)
    bills.n = 0
    _res, _p, before = await _retract(w, src)
    confirms = len(w.reg.confirm_calls())
    res, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert WC.V_CANDIDATE_RELIST_WITHDRAWN in res.trace.violations, res.trace.violations
    assert _pick_ids(res) == src.ids and _ask(res), res.answer
    assert len(w.reg.confirm_calls()) == confirms
    assert _withdrawn_state(w) == before and WC.is_withdrawn(_cands(w))
    assert all(w.draft()["fields"].get(k) == v for k, v in src.rest.items())   # 補的欄位照收
    assert bills.n == 0
    assert w.writes() == []


@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_a2_retract_and_fill_through_proposal_program(api, monkeypatch, name):
    """(a2) 四種來源 × `proposal_program` 入口：撤回那回合（模型提議先於意圖取用）與下一回合（模型提議補欄位）
    都經同一個關口 ⇒ 重列同一份 `ids`、不出卡、`confirm.request` 經 registry 0 次、帳單解析 0 次。"""
    bills = _BillsCount(api, monkeypatch)
    w, src = await _picked(name)
    bills.n = 0
    res, _p, before = await _retract(
        w, src, program_first=False, script=[_proposal(src.action, **src.rest)])
    _assert_via_proposal(res)
    assert WC.V_CANDIDATE_RELIST_WITHDRAWN in res.trace.violations
    confirms = len(w.reg.confirm_calls())
    res2, _p = await _t(w, f"{src.rest_text}，可以幫我處理嗎？", [_proposal(src.action, **src.rest)],
                        intents=[_intent("none")])
    _assert_via_proposal(res2)
    assert WC.V_CANDIDATE_RELIST_WITHDRAWN in res2.trace.violations
    assert _pick_ids(res2) == src.ids and _ask(res2), res2.answer
    assert len(w.reg.confirm_calls()) == confirms and bills.n == 0
    assert _withdrawn_state(w) == before
    assert w.writes() == []


async def test_a2_premise_bill_counter_sees_scope_pick_resolution(api, monkeypatch):
    """前提自證（上兩支「帳單解析 0 次」不是量尺壞了）：選對紀錄選定 68007 後補天數 ⇒ 依選定物件解析帳單 ⇒
    計數 ≥1、卡是 760889；`confirm.request` 經 registry 的計數同樣看得到這次出卡。"""
    bills = _BillsCount(api, monkeypatch)
    w, src = await _picked("pick_right", pick="68007")
    bills.n = 0
    confirms = len(w.reg.confirm_calls())
    res, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert _card_id(w, res, "bill_id") == "760889"
    assert bills.n >= 1 and len(w.reg.confirm_calls()) > confirms


async def test_a2_picked_exact_proposal_program_carries_program_pick(api):
    """(a2) V7-2：A-2a 精確同名選定後走模型提議那一回合 ⇒ 提議轉成的程式呼叫帶 `program_pick` ⇒ 卡是選定那筆
    （⛔ 依同名重列蓋掉選定）。"""
    w, src = await _picked("exact")
    w.reg = _SpyReg(w.db)
    res, _p = await _t(w, src.rest_text, [_proposal(CC, **src.rest)], intents=[_intent("none")])
    assert "confirm_source:program_proposal" in res.trace.violations, res.trace.violations
    assert _card_id(w, res) == src.picked
    picks = [p for n, _s, p in w.reg.picks if n == "confirm.request"]
    assert picks and picks[-1] is not None and picks[-1]["id"] == src.picked


@pytest.mark.parametrize("name", ALL_SOURCES)
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_a2_withdrawn_fill_with_old_name_drops_it(api, name, where):
    """(a2) V7-1：已撤回後下一回合只補欄位，假模型在意圖或模型提議填回前幾回合客人講過的講法（撤回那句講了
    已撤回那筆的正名，會唯一對到它；或列候選前的原講法）⇒ 名稱值丟棄、`write_candidate_name_kept`、重列
    同一份 `ids`、不出卡。"""
    w, src = await _picked(name)
    retract_text = f"不是{src.titles[src.picked]}這間，剛剛選錯了"
    await _t(w, retract_text, [_out(MODEL_SAID)] * 2, intents=[_rt(src.action)])
    before = _withdrawn_state(w)
    pad = [_out(MODEL_SAID)] * 2
    for said in (src.spoken, src.titles[src.picked]):
        if where == "intent":
            res, _p = await _t(w, src.rest_text, pad, intents=[_fill_intent(src, **{src.key: said})])
        else:
            res, _p = await _t(w, src.rest_text, [_proposal(src.action, **{src.key: said}, **src.rest)] + pad,
                               intents=[_intent("none")], program_first=False)
            _assert_via_proposal(res)
        assert _pick_ids(res) == src.ids and _ask(res), (said, res.answer)   # 端點斷言在前（正對照看它）
        assert _withdrawn_state(w) == before
        assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations, (said, res.trace.violations)
        assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert w.writes() == []


async def test_a2_control_withdrawn_current_merge_unbinds(api, monkeypatch):
    """正對照（V7-1「已撤回時改走現行合併 ⇒ 失敗」）：已撤回時名稱合併規則回 `None`（照現行合併）⇒ 原講法併進草稿、
    解綁、候選集被清（⛔ 重列同一份 `ids`）。"""
    orig = RT._write_candidates_name_rule

    def current_when_withdrawn(self, acc, identity, f, raw, *, defer):
        cands = acc.write_draft.candidates
        if WC.is_withdrawn(cands):
            return None
        return orig(self, acc, identity, f, raw, defer=defer)

    w, src = await _picked("jia")
    await _t(w, "剛剛選錯了", intents=[_rt(CC)])
    monkeypatch.setattr(RT, "_write_candidates_name_rule", current_when_withdrawn)
    res, _p = await _t(w, src.rest_text, intents=[_fill_intent(src, estate_name=src.spoken)],
                       lenient=[_ids_resp(["56905"])])
    assert WC.V_CANDIDATE_NAME_KEPT not in res.trace.violations
    assert w.draft()["fields"]["estate_name"] == src.spoken
    assert _cands(w) is None or not WC.is_withdrawn(_cands(w))


async def test_a2_repick_after_withdrawn_issues_the_new_one(api):
    """(a2)：已撤回後 `pick_id` ∈ `ids` ⇒ 重新選定（拿掉 `withdrawn`），補欄位 ⇒ 卡是新那筆。四種來源中以
    選對紀錄（延期繳費、帳單依選定物件解析）與寬鬆各一。"""
    for name in ("pick_right", "jia"):
        w, src = await _picked(name)
        await _t(w, "剛剛選錯了", intents=[_rt(src.action)])
        res, _p = await _t(w, f"要 {src.other} 那間", intents=[_intent_raw(src.action, pick_id=src.other)])
        assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations
        c = _cands(w)
        assert c["picked"] == src.other and WC.WITHDRAWN_KEY not in c
        res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
        assert _card_id(w, res2, src.card_key) == src.other_card, res2.answer


async def test_a2_withdrawn_then_new_name_unbinds_and_requeries(api):
    """(a2)：已撤回後講候選集外的新名稱（本回合原話）⇒ 解綁、候選集清掉、依新名稱重查（唯一 ⇒ 卡是新那筆）。"""
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", intents=[_rt(CC)])
    res, _p = await _t(w, f"改成 {STUDENT_ESTATE} {src.rest_text}",
                       intents=[_fill_intent(src, estate_name=STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations, res.trace.violations
    assert _card_id(w, res) == STUDENT_ID


async def test_a2_withdrawn_rows_empty_clears_and_asks_the_name(api, monkeypatch):
    """(a2)：已撤回後依 `ids` 取列也為空（全都看不到了）⇒ 候選集與草稿名稱欄清掉、追問名稱、不出卡。"""
    w, src = await _picked("jia")
    await _t(w, "剛剛選錯了", intents=[_rt(CC)])

    async def _none(*_a, **_k):
        return []

    monkeypatch.setattr(runtime_mod, "name_lenient_rows_for_ids", _none)
    confirms = len(w.reg.confirm_calls())
    res, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert _cands(w) is None
    assert "estate_name" not in w.draft()["fields"]
    assert _ask(res) and _pick_ids(res) == [], res.answer
    assert "物件" in res.answer and len(w.reg.confirm_calls()) == confirms


async def test_a2_v7_3_exact_listed_early_withdrawn_still_relists(api):
    """(a2) V7-3：(丙) 來源（建合約其他欄位仍缺時列出的精確同名候選），選定、撤回後下一回合仍缺欄 ⇒ 重列同一份
    `ids`、名稱欄與 `name_fp` 不變、⛔ 追問名稱。"""
    w, src = await _picked("exact")
    r0, _p = await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2,
                      intents=[_rt(CC)])
    assert WC.V_CANDIDATE_RETRACT_TYPED in r0.trace.violations and _pick_ids(r0) == src.ids, r0.answer
    before = _withdrawn_state(w)
    res, _p = await _t(w, "租金 12000", [_out(MODEL_SAID)] * 2, intents=[_intent(CC, rent="12000")])
    assert _pick_ids(res) == src.ids and _ask(res), res.answer
    assert _withdrawn_state(w) == before
    assert not res.answer.startswith("要完成這筆建立")


async def test_a2_control_v7_3_rows_only_from_write_name_candidates(api, monkeypatch):
    """正對照（V7-3「取列只用 `write_name_candidates` ⇒ 失敗」）：拿掉依 `ids` 取列的後備 ⇒ 其他欄位仍缺時取不到列，
    候選集與名稱欄被清、改追問名稱（⛔ 重列同一份 `ids`）。"""
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", intents=[_rt(CC)])

    async def _none(*_a, **_k):
        return []

    monkeypatch.setattr(runtime_mod, "name_lenient_rows_for_ids", _none)
    res, _p = await _t(w, "租金 12000", intents=[_intent(CC, rent="12000")])
    assert _pick_ids(res) != src.ids
    assert _cands(w) is None


_B2_RESOLVERS = ("name_early_lookup", "missing_name_lenient", "closed_action_missing_labels",
                 "write_name_candidates")


def _spy_b2_resolvers(monkeypatch) -> list:
    """B2 名稱解析呼叫的計數：只記從 `_write_reply_state` 內發出的呼叫（`pick_id` 資料段取列也會呼叫
    `write_name_candidates`，那不是 B2 的名稱解析）。"""
    import sys
    hits: list = []
    for fn in _B2_RESOLVERS:
        orig = getattr(runtime_mod, fn)

        def _spy(*a, _fn=fn, _orig=orig, **k):
            frame = sys._getframe(1)
            while frame is not None:
                if frame.f_code.co_name == "_write_reply_state":
                    hits.append(_fn)
                    break
                frame = frame.f_back
            return _orig(*a, **k)

        monkeypatch.setattr(runtime_mod, fn, _spy)
    return hits


@pytest.mark.parametrize("full", [False, True], ids=["missing", "complete"])
async def test_a2_b2_withdrawn_never_resolves_the_name(api, monkeypatch, full):
    """(a2)：B2 `_write_reply_state` 在已撤回時 ⇒ 名稱解析 0 次（`name_early_lookup`、`missing_name_lenient`、
    `closed_action_missing_labels`、`write_name_candidates`），重列同一份 `ids`。草稿缺欄（缺欄分支、(丙)）與已齊
    （出卡前解析分支）兩種各一；量尺自證見 `test_a2_b2_premise_spy_sees_resolution_when_unpicked`。"""
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    if full:
        _seed_full_draft(w)
    hits = _spy_b2_resolvers(monkeypatch)
    res, _p = await _t(w, "這兩間差在哪裡？", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    assert hits == []
    assert f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{WF.WRITE_REPLY_STATE_CANDIDATES}" in res.trace.violations, \
        res.trace.violations
    assert WC.V_CANDIDATE_RELIST_WITHDRAWN in res.trace.violations
    assert _pick_ids(res) == src.ids and res.trace.pending_id is None


async def test_a2_b2_premise_spy_sees_resolution_when_unpicked(api, monkeypatch):
    """前提自證（上一支的 0 次不是量尺壞了）：沒有候選集、草稿名稱齊而其他欄位缺時，同一種問句回合 B2 會走名稱
    解析 ⇒ 計數 ≥1。"""
    w = _World()
    await _t(w, f"{STUDENT_ESTATE} 這間要簽新租約", [_out(MODEL_SAID)] * 2,
             intents=[_intent(CC, estate_name=STUDENT_ESTATE)])
    assert _cands(w) is None
    hits = _spy_b2_resolvers(monkeypatch)
    await _t(w, "這間租金多少？", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    assert hits, hits


# ════════════════════════════════════════════════════════════════════
# (b) 打字改選
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_b_typed_repick_in_set(api, name):
    """(b)＋§11.14 第 2 點：`rechoice=switch` 且 `pick_id` ∈ 候選集、≠ 選定 ⇒ 改選、trace
    `write_candidate_repick:typed`（四種來源）。"""
    w, src = await _picked(name)
    res, _p = await _t(w, "按錯了，要另一間", intents=[_sw(src.action, src.other)])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations
    assert _cands(w)["picked"] == src.other and _ask(res), res.answer


@pytest.mark.parametrize("pid", ["same", WF.PICK_ID_NONE, "missing", 56907, ["56907"]])
async def test_b_typed_non_repick_values_keep_the_pick(api, pid):
    """(b)：`pick_id`＝選定、`none`、缺漏、型別錯 ⇒ 選定不動、⛔ 改選標記。選定後回合改指令式：舊式假意圖（`switch`
    ＋`pick_id`）由替身換成指令——選定那筆 ⇒ `[pick 選定]`（維持）；`none`、缺漏、非字串 ⇒ `[]`（維持）。
    無效值（候選集外編號、空字串、帶空白）⇒ 撤回重列，見 `test_b_typed_invalid_pick_values_withdraw`。"""
    w, src = await _picked("jia")
    value = {"same": src.picked, "missing": None}.get(pid, pid) if isinstance(pid, str) else pid
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)], intents=[_intent_rc6(CC, SWITCH, value)])
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.V_CANDIDATE_CMD_INVALID not in res.trace.violations, res.trace.violations
    assert _cands(w)["picked"] == src.picked


@pytest.mark.parametrize("pid", ["67338", "", "56907 "])
async def test_b_typed_invalid_pick_values_withdraw(api, pid):
    """(b)（選定後回合改指令式，計畫 §4.3 第 3 點）：`pick` 的編號是候選集外編號、空字串、帶空白 ⇒ 指令無效 ⇒ 撤回並
    重列同一份 `ids`（記 `write_candidate_cmd_invalid`、`write_candidate_retract:typed`）；⛔ 改選、⛔ 留著舊選定。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_intent_rc6(CC, SWITCH, pid)])
    v = res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED not in v and WC.V_CANDIDATE_CMD_INVALID in v, v
    assert WC.V_CANDIDATE_RETRACT_TYPED in v, v
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids and res.trace.pending_id is None, res.answer


async def test_b_whole_sentence_in_set_id_repicks(api):
    """(b)：整句只打候選集內另一個編號（AI 回 `none`）⇒ 改選。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, src.other, intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations
    assert _cands(w)["picked"] == src.other


async def test_b_out_of_set_id_after_pick_never_calls_pick_matches_name(api, monkeypatch):
    """(b) R6-S1：已選定後整句打候選集外編號 58207（fixture 有一筆與改寫後草稿名稱同名、本人可見的紀錄）⇒
    `pick_matches_name` 呼叫 0 次；程式從不把候選集外編號送進改選（`write_candidates.repick`）。選定後回合改指令式：
    AI 的 `pick 58207` 不在 `ids` ⇒ 指令無效 ⇒ 撤回重列。
    同一句在未選定時會走 `pick_matches_name` 並成立（前提自證，見下支）。"""
    w = await _rg_lenient_picked()
    calls: list = []
    repicks: list = []
    orig_pm = runtime_mod.pick_matches_name
    orig_rp = WC.repick

    async def _pm_spy(*a, **k):
        calls.append(k.get("pick_id"))
        return await orig_pm(*a, **k)

    def _rp_spy(cands, pick_id):
        repicks.append(pick_id)
        return orig_rp(cands, pick_id)

    monkeypatch.setattr(runtime_mod, "pick_matches_name", _pm_spy)
    monkeypatch.setattr(WC, "repick", _rp_spy)
    res, _p = await _t(w, "58207", [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "58207")])
    assert calls == [] and repicks == []
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.V_CANDIDATE_PICK_TYPED not in res.trace.violations
    # 選定後回合改指令式：`pick` 58207 不在本回合編號 ∩ `ids` ⇒ 指令無效 ⇒ 撤回重列（⛔ 出舊選定 55455 的卡）。
    assert WC.V_CANDIDATE_CMD_INVALID in res.trace.violations, res.trace.violations
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == _RG_IDS, res.answer
    res2, _p = await _t(w, _CC_REST_TEXT, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **_CC_REST)])
    assert res2.trace.pending_id is None and _pick_ids(res2) == _RG_IDS, res2.answer


async def test_b_premise_out_of_set_id_unpicked_does_use_pick_matches_name(api, monkeypatch):
    """前提自證：同一份寬鬆候選集**未選定**時整句打 58207 ⇒ `pick_matches_name` 被呼叫（上一支的 0 不是工具壞了）。"""
    w = _World()
    await _t(w, f"{_RG_TYPO}那間要簽約", intents=[_intent(CC, estate_name=_RG_TYPO)],
             lenient=[_ids_resp(_RG_IDS)])
    calls: list = []
    orig = runtime_mod.pick_matches_name

    async def _spy(*a, **k):
        calls.append(k.get("pick_id"))
        return await orig(*a, **k)

    monkeypatch.setattr(runtime_mod, "pick_matches_name", _spy)
    await _t(w, "58207", [_out(MODEL_SAID)], intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    assert calls == ["58207"]


async def _twin_listed(monkeypatch):
    """兩筆畫面除編號外全同（40303、26007）的選對紀錄候選，未選定。"""
    async def _same(api_, role_id, user_id, rows_):
        return [dict(r, **{WC.HAS_VALID_CONTRACT_KEY: None}) for r in rows_]

    monkeypatch.setattr(C, "_annotate_valid_contract", _same)
    twin = "台北文山-離塵一房(國泰)"
    w = _World()
    res, _p = await _t(w, f"{twin}那間要新增合約", intents=[_intent(CC, estate_name=twin)])
    assert _pick_ids(res) == ["40303", "26007"] and WC.PR_INDISTINCT_TEXT in res.answer.split("\n")
    assert _cands(w)["picked"] is None
    return w


async def _twin_indistinct(monkeypatch):
    w = await _twin_listed(monkeypatch)
    res2, _p = await _t(w, "pick:estate:26007")
    assert _ask(res2) and _cands(w)["picked"] == "26007"
    return w


async def test_b_refused_indistinct_repick_withdraws_never_the_old_card(api, monkeypatch):
    """(b) §11.8 N-2：改選目標分不出（畫面除編號外全同）⇒ 與未選定時同一套重問（`pick_right:indistinct`、
    `write_candidate_reask`），且 `picked` 已清（已撤回）；下一回合補欄位 ⇒ 重列、⛔ 出舊選定 26007 的卡。"""
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "是有合約那間才對", intents=[_sw(CC, "40303")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_REASK in res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == ["40303", "26007"] and _ask(res)
    res2, _p = await _t(w, _CC_REST_TEXT, intents=[_intent(CC, **_CC_REST)])
    assert res2.trace.pending_id is None and _pick_ids(res2) == ["40303", "26007"], res2.answer


@pytest.mark.usefixtures("closing_handoff_off")
async def test_b_refused_amount_mismatch_repick_withdraws(api):
    """(b)：改選目標與先前講的金額不符（選對紀錄 `_pick_right_typed_mismatch`）⇒ 不收、重問、`picked` 清掉
    （⛔ 留著舊選定、⛔ 出卡）。帳單候選集「已選定、還沒出卡」的狀態（按鈕選定帳單照常即出卡；只有該次出卡
    沒成時才留在這個狀態）由前一回合的列候選結果補上選定 709740 組成——驗程式規則本身。"""
    w = _World()
    keelung = "基隆溫馨一人宅套房"
    await _t(w, f"{keelung} 7月那期 5000元 延後 3 天",
             intents=[_intent(DUE, estate_name=keelung, period="7月那期", days="3", said_amount="5000")])
    c = dict(_cands(w), picked="709740")
    assert WC.load_write_candidates(c)[0] == c
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, p = await _t(w, "改 24800 那張", [_out(MODEL_SAID)], intents=[_sw(DUE, "709739")])
    (kw,) = p.intent_calls
    _assert_cmd_offered(kw, ["709740", "709739"], "709740")
    assert WC.V_PICK_RIGHT_AMOUNT_MISMATCH in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.is_withdrawn(_cands(w)) and res.trace.pending_id is None
    assert _pick_ids(res) == ["709740", "709739"], res.answer


@pytest.mark.parametrize("state", ["picked", "withdrawn"])
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_b_order_repick_wins_over_a_new_name_in_the_same_sentence(api, where, state):
    """(b) 判定順序（N-1）：同一句含改口（`pick_id`＝另一筆）與候選集外、本回合講的名稱值 ⇒ 改選生效、名稱值丟棄
    （候選集未被名稱合併解綁）；補欄位 ⇒ 卡是改選那筆。§11.14：已選定時 AI 回 `rechoice=switch`。
    F12 r6 復原第 5 輪（計畫 §11.15.3 第 6 點；F1 第 6 點「已撤回——`pick_id` X 驗過＋名稱欄候選集外本回合講的 ⇒
    矛盾、重列」）改寫已撤回那一半：已撤回時名稱欄的候選集外、本回合講的值算「改講新名稱」，與同一次驗過的 X 矛盾 ⇒
    視同 retract：重列同一份 `ids`、名稱丟棄、⛔ 解綁、⛔ 改選、⛔ 出卡，記 `write_candidate_name_conflict`。已選定那一半
    不變（AI 回 `switch`，名稱欄值依 §11.14 第 2 點不算改講新名稱）。"""
    w, src = await _picked("jia")
    if state == "withdrawn":
        await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
        assert WC.is_withdrawn(_cands(w))
    before = _withdrawn_state(w)
    text = f"改成 56907，內湖宏匯 {src.rest_text}"
    if where == "intent":
        res, _p = await _t(w, text, intents=[_sw(CC, "56907", estate_name="內湖宏匯", **src.rest)])
    else:
        res, _p = await _t(w, text, [_proposal(CC, estate_name="內湖宏匯", **src.rest)],
                           intents=[_sw(CC, "56907")], program_first=False)
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    if state == "withdrawn":
        assert WC.V_CANDIDATE_NAME_CONFLICT in res.trace.violations, res.trace.violations
        assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
        assert WC.is_withdrawn(_cands(w)) and _withdrawn_state(w) == before
        assert _pick_ids(res) == src.ids and res.trace.pending_id is None, res.answer
        return
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations
    assert WC.V_CANDIDATE_NAME_CONFLICT not in res.trace.violations
    assert _card_id(w, res) == "56907"


async def test_b_control_name_merge_first_unbinds_the_repick(api, monkeypatch):
    """正對照（N-1）：拿掉「先算改選目標」⇒ 已撤回狀態下名稱合併判新名稱、解綁 ⇒ 改選失效、⛔ 出 56907 的卡。
    第 5 輪（§11.15.3 第 6 點）：已撤回且意圖解析成功的回合改由 `_write_candidates_post_pick_names` 單次決定，改選目標
    由 `_write_candidates_typed_target` 算出——暫改處隨之改成它（舊處 `_write_candidates_repick_target` 只剩意圖解析
    失敗的現行路徑在用）；拿掉目標 ⇒ 不再判矛盾、名稱解綁（上一支已撤回那半失敗）。"""
    w, src = await _picked("jia")
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    monkeypatch.setattr(RT, "_write_candidates_typed_target", staticmethod(lambda *a, **k: None))
    res, _p = await _t(w, f"改成 56907，內湖宏匯 {src.rest_text}",
                       intents=[_sw(CC, "56907", estate_name="內湖宏匯", **src.rest)],
                       lenient=[_ids_resp(["56905"])])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations
    assert res.trace.pending_id is None or _card_id(w, res) != "56907"


# ════════════════════════════════════════════════════════════════════
# (c) 寬鬆改選改寫正名
# ════════════════════════════════════════════════════════════════════
async def test_c_lenient_repick_rewrites_the_title_and_fingerprint(api):
    """(c)：寬鬆候選改選 ⇒ 草稿名稱改寫成新那筆的系統正名、`name_fp` 同步；原講法不動。"""
    w, src = await _picked("jia")
    origin = _cands(w)[WC.ORIGIN_KEY]
    assert w.draft()["fields"]["estate_name"] == src.titles["56906"]
    res, _p = await _t(w, "按錯了", intents=[_sw(CC, "56907")])
    assert WC.V_NAME_LENIENT_REWRITE in res.trace.violations
    c = _cands(w)
    assert w.draft()["fields"]["estate_name"] == src.titles["56907"]
    assert c["name_fp"] == WC.name_fp(src.titles["56907"]) and c[WC.ORIGIN_KEY] == origin
    assert WC.is_lenient(c) and WC.is_rewritten(c)


async def test_c_exact_repick_never_rewrites(api):
    """(c)：A-2a 精確同名改選 ⇒ 名稱與指紋不動（本來相同）、⛔ 改寫標記。"""
    w, src = await _picked("exact")
    before = (w.draft()["fields"]["estate_name"], _cands(w)["name_fp"])
    res, _p = await _t(w, "按錯了", intents=[_sw(CC, src.other)])
    assert WC.V_NAME_LENIENT_REWRITE not in res.trace.violations
    assert (w.draft()["fields"]["estate_name"], _cands(w)["name_fp"]) == before
    assert set(_cands(w)) == WC.CANDIDATE_SET_KEYS


async def test_c_repick_title_lookup_none_never_issues_the_old_card(api, monkeypatch):
    """(c)：改選時取名稱查詢回 `None` ⇒ 不改寫；補欄位 ⇒ 卡是新那筆或查無固定句，⛔ 卡是舊那筆。"""
    w, src = await _picked("jia")

    async def _none(*_a, **_k):
        return None

    monkeypatch.setattr(runtime_mod, "name_lenient_picked_title", _none)
    res, _p = await _t(w, "按錯了", intents=[_sw(CC, "56907")])
    assert WC.V_NAME_LENIENT_REWRITE not in res.trace.violations
    res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert res2.trace.pending_id is None or _card_id(w, res2) == "56907", res2.answer
    assert res2.trace.pending_id is None or _card_id(w, res2) != src.picked


# ════════════════════════════════════════════════════════════════════
# (d) 名稱合併（意圖與模型提議兩處）
# ════════════════════════════════════════════════════════════════════
async def _fill_with_name(w, src, name, *, where, said_in_text, rc=_NO_RC, pid=None, cmd=None):
    """補欄位那句帶名稱值（意圖或模型提議）。`rc`＝舊式假模型的 `rechoice`（`_NO_RC`＝不帶；替身換成指令清單）；
    `cmd`＝直接給指令清單（`[(op, value), …]`，優先於 `rc`）。選定後回合改指令式（計畫 plan-post-pick-commands §4.3）：
    名稱值一律丟棄，只有驗過的 `name` 指令才會改名稱。"""
    text = f"{name} {src.rest_text}" if said_in_text else src.rest_text

    def mk(**f):
        if cmd is not None:
            return _cmd(src.action, *cmd, **f)
        return _intent_rc6(src.action, rc, pid, **f)

    if where == "intent":
        return await _t(w, text, intents=[mk(**{src.key: name}, **src.rest)],
                        lenient=[_ids_resp(["none"])])
    return await _t(w, text,
                    [_proposal(src.action, **{src.key: name}, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                    intents=[mk()], lenient=[_ids_resp(["none"])],
                    program_first=False)


def _assert_kept_by_rc(w, src, res, rc) -> None:
    """名稱值被判候選集內／重講而丟棄後：`keep` ⇒ 卡是原選定；`retract` ⇒ 已撤回、重列同一份 `ids`、不出卡。"""
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    if rc == RETRACT:
        assert WC.V_CANDIDATE_RETRACT_TYPED in res.trace.violations
        assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids and _ask(res), res.answer
    else:
        assert _pick_ids(res) == [] and _card_id(w, res) == src.picked


@pytest.mark.parametrize("rc", [KEEP, RETRACT])
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_d_name_not_said_this_turn_is_dropped(api, where, rc):
    """(d)：名稱值不在本回合原話（模型從上下文填回）⇒ 丟棄、`write_candidate_name_kept`。`keep` ⇒ 不重列、卡是選定
    那筆；`retract`（§11.14：只有它會往下分類）⇒ 仍丟棄（⛔ 依舊講法重查）、已撤回重列。"""
    w, src = await _picked("exact")
    res, _p = await _fill_with_name(w, src, STUDENT_ESTATE, where=where, said_in_text=False, rc=rc)
    _assert_kept_by_rc(w, src, res, rc)


@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_d_name_said_this_turn_unbinds_and_requeries(api, where):
    """(d)＋選定後回合改指令式：AI 回 `name` 指令、名稱候選集外且在本回合原話 ⇒ 解綁、依新名稱重查（唯一 ⇒ 卡是新那筆）、
    `write_candidate_name_new`。（沒有 `name` 指令、同一句名稱只在欄位／提議裡 ⇒ 丟棄，見
    `test_rc_keep_drops_the_candidate_name`。）"""
    w, src = await _picked("exact")
    res, _p = await _fill_with_name(w, src, STUDENT_ESTATE, where=where, said_in_text=True,
                                    cmd=[("name", STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations, res.trace.violations
    assert _card_id(w, res) == STUDENT_ID


@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_d_pick_id_equal_to_picked_drops_the_name(api, where):
    """(d)：`rechoice=switch` 而 `pick_id`＝選定 ⇒ 沒有改選目標、名稱值丟棄（指的就是選定那筆）⇒ 卡是選定那筆。"""
    w, src = await _picked("exact")
    res, _p = await _fill_with_name(w, src, STUDENT_ESTATE, where=where, said_in_text=True, rc=SWITCH,
                                    pid=src.picked)
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert _card_id(w, res) == src.picked


# ════════════════════════════════════════════════════════════════════
# (e) 情境形狀
# ════════════════════════════════════════════════════════════════════
async def test_e_c03_lenient_button_pick_then_repick_by_id_then_fill(api):
    """(e) C03：寬鬆、按鈕選定後以編號改口（AI 回 `pick_id`）、補欄位 ⇒ 卡是 56907。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "按錯了 要改成 56907", [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "56907")])
    res2, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **_CC_REST)])
    assert _card_id(w, res2) == "56907"                                # 端點斷言在前（正對照看它）
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations


async def test_e_c14_exact_button_pick_then_repick(api):
    """(e) C14：A-2a 精確同名、按鈕選定後改口講編號 ⇒ 卡是改口那筆 55455（r6-1 (a)）。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, "剛剛選錯 我要55455", intents=[_sw(CC, "55455")])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations
    res2, _p = await _t(w, src.rest_text, intents=[_intent(CC, **_CC_REST)])
    assert _card_id(w, res2) == "55455"


_XNM = "小南門那個分租套房"


async def test_e_c10b_typed_pick_then_fill_never_relists(api):
    """(e) C10b：打字選定（非按鈕）後補欄位，意圖把列候選前的模糊講法再吐一次 ⇒ 不重列、卡是打字選的 45728。"""
    w = _World()
    res, _p = await _t(w, f"{_XNM} 有人要租 幫我弄合約", intents=[_intent(CC, estate_name=_XNM)],
                       lenient=[_ids_resp(["45728", "45729", "49871"])])
    assert "45728" in _pick_ids(res), res.answer
    res1, _p = await _t(w, "B那間", intents=[_intent_raw(CC, pick_id="45728")])
    assert WC.V_CANDIDATE_PICK_TYPED in res1.trace.violations, res1.trace.violations
    res2, p2 = await _t(w, _CC_REST_TEXT, intents=[_intent(CC, estate_name=_XNM, **_CC_REST)])
    assert _pick_ids(res2) == [] and p2.lenient_calls == []
    assert WC.V_CANDIDATE_NAME_KEPT in res2.trace.violations
    assert _card_id(w, res2) == "45728"


async def test_e_a_b_a_issues_a(api):
    """(e) A→B→A：按鈕選 56907、改口 56906、再改回 56907（整句只打編號）⇒ 卡是 56907。"""
    w, src = await _picked("jia", pick="56907")
    await _t(w, "不對 是 B 那間", intents=[_sw(CC, "56906")])
    assert _cands(w)["picked"] == "56906"
    res, _p = await _t(w, "56907", intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations
    res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert _card_id(w, res2) == "56907"


# ════════════════════════════════════════════════════════════════════
# (f) 開關矩陣
# ════════════════════════════════════════════════════════════════════
_R6_HOOKS = {
    "_write_candidates_post_pick": lambda *a, **k: None,
    "_write_candidates_name_rule": lambda *a, **k: None,
    "_write_candidates_repick_target": lambda *a, **k: None,
    "_write_candidates_repick_notice": lambda *a, **k: None,
    "_write_candidates_proposal_pick": lambda *a, **k: None,
}


async def _c14_conversation(api) -> list:
    w = _World()
    out = []
    for text, intents in [
        ("瑞光好房1(個人租客) 這間要簽新租約", [_intent(CC, estate_name="瑞光好房1(個人租客)")]),
        ("pick:estate:58207", None),
        ("剛剛選錯 我要55455", [_sw(CC, "55455")]),
        ("剛剛選錯了", [_rt(CC)]),
        (_CC_REST_TEXT, [_intent(CC, **_CC_REST)]),
    ]:
        res, _p = await _t(w, text, [_out(MODEL_SAID)] * 3, intents=intents)
        out.append(_snap(res))
    out.append(json.dumps(w.state, ensure_ascii=False, sort_keys=True, default=str))
    return out


async def test_f_a2a_off_is_identical_with_r6_hooks_neutralised(api, monkeypatch):
    """(f)：A-2a off ⇒ 沒有候選集；同一段 C14 對話（含改口、撤回）與「r6 新增的判斷全換成不生效值」逐位相同
    （回覆、按鈕、trace、`agent_state` 序列化），且無任何 r6 標記。"""
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    on = await _c14_conversation(api)
    for attr, fn in _R6_HOOKS.items():
        monkeypatch.setattr(RT, attr, fn)
    off = await _c14_conversation(api)
    assert on == off
    dumped = json.dumps(on, ensure_ascii=False)
    for mark in (WC.V_CANDIDATE_REPICK_TYPED, WC.V_CANDIDATE_RETRACT_TYPED, WC.V_CANDIDATE_RELIST_WITHDRAWN,
                 WC.V_CANDIDATE_NAME_KEPT, WC.V_CANDIDATE_NAME_NEW):
        assert mark not in dumped


@pytest.mark.usefixtures("closing_handoff_off")
async def test_f_lenient_off_a2a_on_exact_repick_follows_r6(api, monkeypatch):
    """(f) r6-1 (a)：F12 off 且 A-2a on ⇒ 精確同名候選集選定後打字改選照 r6（C14 形狀：按鈕選定、改口講編號、
    卡是改口那筆）。F12 off 時 (丙)「其他欄位仍缺時列精確同名候選」不生效（下面前提自證：同一句只追問欄位、
    ⛔ 列候選）⇒ 精確同名候選集選定後、出卡前的窗口是「欄位齊全、選定那筆出不了卡」：延期繳費講齊物件名稱、
    期別、天數，兩筆同名物件（68007、67651）先列物件；按鈕選 67651（該期無帳單 ⇒ 這次沒產生確認卡、候選集仍
    選定 67651）⇒ 改口講 68007 ⇒ 卡是 68007 的 8月帳單 760889。"""
    from services.agent import name_match as NM
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    w0 = _World()
    res0, _p = await _t(w0, _SOURCES["exact"]["text"], intents=[_SOURCES["exact"]["intent"]()])
    assert _pick_ids(res0) == [] and _cands(w0) is None, res0.answer        # 前提自證：(丙) 不生效
    w = _World()
    name = "海大質感獨立套房高級廚房可租補"
    r1, _p = await _t(w, f"{name} 8月那期 延後 3 天 要延期",
                      intents=[_intent(DUE, estate_name=name, period="8月那期", days="3")])
    assert _pick_ids(r1) == ["68007", "67651"] and WC.V_PICK_RIGHT_ESTATE_FIRST in r1.trace.violations
    assert WC.LENIENT_KEY not in _cands(w)
    r2, _p = await _t(w, "pick:estate:67651")
    assert r2.trace.pending_id is None and _cands(w)["picked"] == "67651", r2.answer
    res, provider = await _t(w, "剛剛選錯 我要68007", intents=[_sw(DUE, "68007")])
    (kw,) = provider.intent_calls
    _assert_cmd_offered(kw, ["68007", "67651"], "67651")
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations
    assert _card_id(w, res, "bill_id") == "760889"


# ════════════════════════════════════════════════════════════════════
# (g) 身分與綁定
# ════════════════════════════════════════════════════════════════════
def _tamper_creator(c):
    c["creator"] = {"user_id": "990002", "role_id": c["creator"]["role_id"]}


def _tamper_action(c):
    c["action"] = "repair_create"


def _tamper_fp(c):
    c["name_fp"] = WC.name_fp("別的名稱")


@pytest.mark.parametrize("tamper", [_tamper_creator, _tamper_action, _tamper_fp],
                         ids=["user", "action", "name_fp"])
async def test_g_repick_only_when_bound(api, tamper):
    """(g)：候選集不再綁定本草稿（換使用者、換動作、名稱指紋改變）⇒ 不改選（候選集作廢；AI 回的 `pick_id`
    不被收、⛔ `write_candidate_repick:typed`）。"""
    w, src = await _picked("exact")
    c = dict(_cands(w))
    tamper(c)
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, _p = await _t(w, "按錯了 要 55455", [_out(MODEL_SAID)] * 2,
                       intents=[_sw(CC, "55455")])
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.V_CANDIDATE_PICK_TYPED not in res.trace.violations
    after = _cands(w)
    assert after is None or after.get("picked") != "55455"


async def test_g_control_bound_ignoring_creator_repicks_for_another_user(api, monkeypatch):
    """正對照（(h)「`_write_candidates_bound` 忽略建立者 ⇒ (g) 換使用者那支失敗」）。"""
    orig = RT._write_candidates_bound

    def no_creator(cands, identity, draft):
        if isinstance(cands, dict) and isinstance(cands.get("creator"), dict):
            cands = dict(cands, creator={"user_id": identity.user_id, "role_id": identity.role_id})
        return orig(cands, identity, draft)

    monkeypatch.setattr(RT, "_write_candidates_bound", staticmethod(no_creator))
    w, src = await _picked("exact")
    c = dict(_cands(w))
    _tamper_creator(c)
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, _p = await _t(w, "按錯了 要 55455", [_out(MODEL_SAID)] * 2,
                       intents=[_sw(CC, "55455")])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations


PROPERTY_CASES = 240


async def test_g_property_model_returns_another_identity_id_never_repicks(monkeypatch):
    """(g) 性質測試（240 組）：假 API 依 (role, viewer) 回列；候選集（寬鬆已改寫／A-2a 精確同名兩種形狀）已選定、
    綁定本身分；假模型在已選定回合回他人編號、本人候選集外編號、保留字、型別錯或候選集內另一筆。選定後回合改指令式
    （計畫 plan-post-pick-commands §4.3）：同一組（候選集、`pick` 編號）逐一配上四種指令讀法（`pick`／`nth`／`clear`／
    空陣列），由 `_write_candidates_cmd_turn` 執行。斷言：
    (1) 附上的編號（`pick_offered`）⊆ 本身分可見 ∩ `ids`；(2) 改選只在 `pick` 的編號 ∈ `pick_offered` ∩ `ids` 且 ≠ 選定、
    或 `nth` 對到畫面清單內另一筆時成立（`clear` ⇒ 已撤回；空陣列 ⇒ 不動；其餘無效 ⇒ 已撤回）；
    (3) 他人編號從不成為選定；(4) 每支出向帶 role_id 且 viewer_user_id＝本人。量尺自證：改選、拒收兩種結果都出現。"""
    repicked = refused_other = kept_by_rc = retracted = 0
    for seed in range(PROPERTY_CASES):
        rng = random.Random(seed)
        estates, contracts = _universe(seed)
        key = rng.choice(_IDENTS)
        role, user = key
        own = estates[key]
        title = rng.choice(own)["title"]
        nid = 900000 + seed * 10
        twins = [{"id": nid + i, "title": title, "address": f"地址{seed}-{i}"} for i in range(rng.randint(1, 3))]
        estates[key] = own + twins
        others = []
        for k in _IDENTS:
            if k != key:
                extra = {"id": nid + 7 + _IDENTS.index(k), "title": title, "address": "地址"}
                estates[k] = estates[k] + [extra]
                others += [str(r["id"]) for r in estates[k]]
        fake = _FakeAPI(estates, contracts)
        monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
        ident = _pm(user=user, role=role)
        same = [str(r["id"]) for r in estates[key] if r["title"] == title]
        lenient = rng.random() < 0.5
        if lenient:
            pool = [str(r["id"]) for r in estates[key]]
            ids = rng.sample(pool, min(len(pool), rng.randint(2, 5)))
        else:
            ids = same if len(same) >= 2 else same + [str(nid + 5)]
        if len(ids) < 2:
            continue
        picked = ids[0]
        cands = {"action": "repair_create", "field": "estate_name", "type": "estate", "ids": ids,
                 "has_more": False, "name_fp": WC.name_fp(title),
                 "creator": {"user_id": user, "role_id": role}, "picked": picked}
        if lenient:
            cands.update({WC.LENIENT_KEY: True, WC.REWRITTEN_KEY: True, WC.ORIGIN_KEY: "",
                          WC.ORIGIN_FP_KEY: WC.name_fp("")})
        loaded, invalid = WC.load_write_candidates(cands)
        assert loaded is not None and not invalid, (seed, cands)
        draft = {"action": "repair_create", "fields": {"estate_name": title}, "idle_turns": 0,
                 "created_by_role": runtime_mod._write_draft_owner(ident), "asked": []}
        mode = rng.choice(["other", "other", "own_out", "in_set", "in_set", "picked", "none", "retract", "bad"])
        own_out = [str(r["id"]) for r in estates[key] if str(r["id"]) not in ids]
        pid = {"other": rng.choice(others) if others else "1",
               "own_out": rng.choice(own_out) if own_out else "1",
               "in_set": rng.choice(ids[1:]), "picked": picked, "none": WF.PICK_ID_NONE,
               "retract": "retract", "bad": rng.choice([123, None, ["1"], ""])}[mode]
        n = rng.randint(1, len(ids) + 1)
        # 同一組（候選集、`pick` 編號）逐一配上四種指令讀法：`pick`／`nth`／`clear`／空陣列。
        for kind in ("pick", "nth", "clear", "empty"):
            rt = RT(_Provider([]), None, None, None, None, stage="M1")
            acc = runtime_mod.TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t", start=0.0)
            acc.write_draft = runtime_mod._WriteDraftTurn(draft=copy.deepcopy(draft),
                                                          owner=draft["created_by_role"],
                                                          user_texts=["幫我處理"])
            acc.write_draft.candidates = loaded
            agent_state = {WRITE_CANDIDATES_KEY: loaded}
            fake.calls.clear()
            out = await rt._write_candidates_intent_kwargs(
                acc, ident, (loaded, {"estate_name": title, "description": "冷氣不冷"}),
                {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]},
                enum_labels=False)
            visible = {str(r["id"]) for r in estates[key]}
            offered = set(acc.write_draft.pick_offered)
            assert offered <= visible & set(ids), (seed, offered)
            for _what, params in fake.calls:
                assert params["role_id"] == role and params["viewer_user_id"] == user, (seed, params)
            assert acc.write_draft.cmd_offered is (out is not None), seed
            tag = (seed, mode, pid, kind, n, lenient, out is not None)
            if out is None:
                continue                                      # 附不出候選段 ⇒ 不走指令路徑（見 `test_post_pick_commands_req`）
            item = {"pick": {"op": "pick", "value": pid}, "nth": {"op": "nth", "value": str(n)},
                    "clear": {"op": "clear", "value": ""}}.get(kind)
            wd = acc.write_draft
            wd.cmd_scope_start = True
            wd.intent_target = [item] if item is not None else []
            await rt._write_candidates_cmd_turn(
                acc, ident, agent_state, "幫我處理", SimpleNamespace(action="repair_create", fields=[]),
                blocked=False, fields_before=dict(draft["fields"]))
            now = (wd.candidates or {}).get("picked")
            assert now is None or now in ids, tag
            assert now not in others or now in ids, tag      # (3) 他人編號從不成為選定
            if kind == "empty":
                assert now == picked and not WC.is_withdrawn(wd.candidates), tag
                continue
            if kind == "clear":
                assert now is None and WC.V_CANDIDATE_RETRACT_TYPED in acc.violations, tag
                retracted += 1
                continue
            if kind == "pick":
                target = pid if isinstance(pid, str) and pid in offered and pid in ids else None
            else:
                shown = ids[:rt._write_candidates_shown_limit(rt._pick_right_active())]
                target = shown[n - 1] if n <= len(shown) and all(x in offered for x in shown) else None
            if target is None:                            # 無效指令 ⇒ 撤回重列（⛔ 改選）
                assert now is None and WC.V_CANDIDATE_CMD_INVALID in acc.violations, tag
                assert WC.V_CANDIDATE_REPICK_TYPED not in acc.violations, tag
                if mode == "other" and kind == "pick":
                    refused_other += 1
            elif target == picked:
                assert now == picked and WC.V_CANDIDATE_REPICK_TYPED not in acc.violations, tag
                kept_by_rc += 1
            elif now is None:                             # 分不出（畫面除編號外全同）⇒ 被退回、已撤回，屬 (b) 正當拒收
                assert WC.V_PICK_RIGHT_INDISTINCT in acc.violations or WC.V_PICK_RIGHT_AMOUNT_MISMATCH in acc.violations, \
                    (tag, acc.violations)
            else:
                assert now == target, tag
                repicked += 1
    print(f"F12_R6_PROPERTY cases={PROPERTY_CASES} repicked={repicked} refused_other={refused_other} "
          f"kept_by_cmd={kept_by_rc} retracted={retracted}")
    assert repicked >= 15 and refused_other >= 40, (repicked, refused_other)
    assert kept_by_rc >= 15 and retracted >= 40, (kept_by_rc, retracted)


# ════════════════════════════════════════════════════════════════════
# (j) r6-3 告知句
# ════════════════════════════════════════════════════════════════════
_RG_SHORT = "瑞光好房1"


async def _rg_short_picked():
    """講法「瑞光好房1」（與系統正名「瑞光好房1(個人租客)」不同）對到兩筆同名 ⇒ 按鈕選 58207。"""
    w = _World()
    res, _p = await _t(w, f"{_RG_SHORT} 這間要簽新租約", intents=[_intent(CC, estate_name=_RG_SHORT)])
    assert _pick_ids(res) == ["58207", "55455"], res.answer
    res2, _p = await _t(w, "pick:estate:58207")
    assert _ask(res2) and w.draft()["fields"]["estate_name"] == _RG_SHORT
    return w


async def test_j_repick_notice_uses_the_api_row_title_and_dialog_has_no_name(api):
    """(j)：打字改選成立、還沒出卡 ⇒ 回覆開頭是固定句「已改成：{title}（編號 {id}）。」，title＝本身分 API 該列
    title（客人講法刻意不同）；該回合寫進 dialog 的是不含名稱的程式摘要。"""
    w = await _rg_short_picked()
    res, _p = await _t(w, "剛剛選錯 我要55455", intents=[_sw(CC, "55455")])
    notice = WC.CANDIDATE_REPICK_TEXT.format(title="瑞光好房1(個人租客)", id="55455")
    assert res.answer.startswith(notice + "\n"), res.answer
    assert res.answer.split("\n", 1)[1].startswith("要完成這筆建立"), res.answer
    last = _agent(w)["dialog"][-1]
    assert last["role"] == "assistant"
    assert last["content"].startswith(WC.CANDIDATE_REPICK_DIALOG_SUMMARY + "\n")
    assert "瑞光好房" not in last["content"] and "55455" not in last["content"]


async def test_j_no_notice_without_a_typed_repick(api):
    """(j)：沒有改選的追問回合 ⇒ 與改動前逐字相同（不加告知句）。"""
    w = await _rg_short_picked()
    res, _p = await _t(w, "租金 12000", intents=[_intent(CC, rent="12000")])
    assert res.answer.startswith("要完成這筆建立"), res.answer
    assert "已改成" not in res.answer


async def test_j_control_notice_from_draft_value_differs(api, monkeypatch):
    """正對照（(j)「改用草稿值 ⇒ 失敗」）：告知句名稱改取草稿值 ⇒ 出現客人講法「瑞光好房1」、與 API title 不同。"""

    def from_draft(self, acc):
        wd = acc.write_draft
        if not isinstance(wd.repick_id, str):
            return None
        return WC.CANDIDATE_REPICK_TEXT.format(title=wd.draft["fields"]["estate_name"], id=wd.repick_id)

    monkeypatch.setattr(RT, "_write_candidates_repick_notice", from_draft)
    w = await _rg_short_picked()
    res, _p = await _t(w, "剛剛選錯 我要55455", intents=[_sw(CC, "55455")])
    assert res.answer.startswith("已改成：瑞光好房1（編號 55455）。"), res.answer


# ════════════════════════════════════════════════════════════════════
# (k) 形狀
# ════════════════════════════════════════════════════════════════════
def _base_set(**over) -> dict:
    value = {"action": CC, "field": "estate_name", "type": "estate", "ids": ["101", "102"],
             "has_more": False, "name_fp": WC.name_fp("甲"), "creator": {"user_id": OWNER, "role_id": ROLE},
             "picked": "101", WC.LENIENT_KEY: True, WC.REWRITTEN_KEY: True, WC.ORIGIN_KEY: "甲乙",
             WC.ORIGIN_FP_KEY: WC.name_fp("甲乙")}
    value.update(over)
    return {k: v for k, v in value.items() if v is not _DROP}


_DROP = object()


def test_k_valid_shapes():
    assert WC.load_write_candidates(_base_set())[1] is False
    assert WC.load_write_candidates(_base_set(picked=None, withdrawn=True))[1] is False
    plain = _base_set(**{WC.LENIENT_KEY: _DROP, WC.REWRITTEN_KEY: _DROP, WC.ORIGIN_KEY: _DROP,
                         WC.ORIGIN_FP_KEY: _DROP})
    assert WC.load_write_candidates(plain)[1] is False
    assert WC.load_write_candidates(dict(plain, picked=None, withdrawn=True))[1] is False


_TAMPERED = {
    "withdrawn_with_picked": dict(withdrawn=True),
    "withdrawn_not_true": dict(picked=None, withdrawn=1),
    "withdrawn_string": dict(picked=None, withdrawn="true"),
    "withdrawn_false": dict(picked=None, withdrawn=False),
    "rewritten_unpicked_not_withdrawn": dict(picked=None),
    "rewritten_not_bool": {WC.REWRITTEN_KEY: "yes"},
    "rewritten_without_lenient": {WC.LENIENT_KEY: _DROP},
    "origin_fp_not_str": {WC.ORIGIN_FP_KEY: 123},
    "origin_overlong": {WC.ORIGIN_KEY: "甲" * 500, WC.ORIGIN_FP_KEY: WC.name_fp("甲" * 500)},
    "origin_fp_mismatch": {WC.ORIGIN_FP_KEY: WC.name_fp("別的")},
    "origin_without_fp": {WC.ORIGIN_FP_KEY: _DROP},
    "reserved_id_none": dict(ids=["101", WF.PICK_ID_NONE]),
    "reserved_id_pick": dict(ids=["101", "pick"]),
    "reserved_id_nth": dict(ids=["101", "nth"]),
    "reserved_id_name": dict(ids=["101", "name"]),
    "reserved_id_clear": dict(ids=["101", "clear"]),
    "picked_not_in_ids": dict(picked="999"),
    "bill_with_lenient": dict(action=DUE, type="bill"),
}


@pytest.mark.parametrize("case", list(_TAMPERED))
def test_k_tampered_shapes_are_invalid(case):
    assert WC.load_write_candidates(_base_set(**_TAMPERED[case])) == (None, True)


def test_k_reserved_ids_are_rejected_when_building():
    """(k) R6-S7：組候選集時編號為 `none` 或指令 `op` 值域內字串（`pick`／`nth`／`name`／`clear`）⇒ 拒收（組不出合法形狀
    ⇒ `None`）。選定後回合改指令式（計畫 plan-post-pick-commands §4.2、§4.3）：`RESERVED_IDS`＝`PICK_ID_NONE` ∪
    `PICK_TARGET_OP_DOMAIN`（縱深防禦，⛔ 與指令 `op` 值撞名）；`retract` 不再是保留字。"""
    assert WC.RESERVED_IDS == frozenset({WF.PICK_ID_NONE}) | frozenset(WF.PICK_TARGET_OP_DOMAIN)
    assert WF.PICK_TARGET_OP_DOMAIN == ("pick", "nth", "name", "clear")
    for reserved in (WF.PICK_ID_NONE, *WF.PICK_TARGET_OP_DOMAIN):
        assert WC.new_candidate_set(action=CC, field="estate_name", cand_type="estate", ids=["101", reserved],
                                    has_more=False, field_value="甲",
                                    creator={"user_id": OWNER, "role_id": ROLE}) is None
    assert WC.new_candidate_set(action=CC, field="estate_name", cand_type="estate", ids=["101", "102"],
                                has_more=False, field_value="甲",
                                creator={"user_id": OWNER, "role_id": ROLE}) is not None


_RUNTIME_TAMPER = {
    "origin_fp_not_str": {WC.ORIGIN_FP_KEY: 1},
    "origin_overlong": {WC.ORIGIN_KEY: "甲" * 500, WC.ORIGIN_FP_KEY: WC.name_fp("甲" * 500)},
    "origin_fp_mismatch": {WC.ORIGIN_FP_KEY: WC.name_fp("別的")},
    "reserved_id": {"ids": ["56907", "pick", "56905"]},
    "picked_not_in_ids": {"picked": "12345"},
    "rewritten_not_bool": {WC.REWRITTEN_KEY: 1},
    "rewritten_without_lenient": {WC.LENIENT_KEY: _DROP},
    "unpicked_rewritten_not_withdrawn": {"picked": None},
    "withdrawn_with_picked": {WC.WITHDRAWN_KEY: True},
}


@pytest.mark.parametrize("case", list(_RUNTIME_TAMPER))
async def test_k_runtime_tampered_state_clears_and_never_issues_a_program_pick_card(api, case):
    """(k)：讀回竄改狀態 ⇒ `write_candidates_shape_invalid`、候選集被清、⛔ 出 `program_pick` 卡。"""
    w, src = await _picked("jia")
    c = dict(_cands(w))
    for k, v in _RUNTIME_TAMPER[case].items():
        if v is _DROP:
            c.pop(k, None)
        else:
            c[k] = v
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    w.reg = _SpyReg(w.db)
    res, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_fill_intent(src)])
    assert WC.V_CANDIDATES_SHAPE_INVALID in res.trace.violations, res.trace.violations
    assert all(p is None for n, _s, p in w.reg.picks if n == "confirm.request")
    after = _cands(w)
    assert after is None or after.get("picked") is None


async def test_k_origin_is_the_listing_draft_value_never_the_r4_sentence(api):
    """(k)：列候選後選定，`agent_state` 序列化的原講法＝列候選時草稿名稱值的正規化結果（`_name_said_key`），
    ⛔ R4 整句（假模型整句與名稱值刻意不同）；正對照：該整句確實出現在送寬鬆模型的 messages 裡。(乙) ⇒ 空字串。"""
    w = _World()
    sentence = "宏匯個人那間要簽約"
    res, provider = await _t(w, sentence, intents=[_intent(CC, estate_name="宏匯個人")],
                             lenient=[_ids_resp(["56907", "56906", "56905"])])
    (kw,) = provider.lenient_calls
    assert kw["messages"][2]["content"] == sentence                  # 正對照：整句在送模型的訊息裡
    await _t(w, "pick:estate:56906")
    c = _cands(w)
    assert c[WC.ORIGIN_KEY] == runtime_mod._name_said_key("宏匯個人")
    assert c[WC.ORIGIN_KEY] != runtime_mod._name_said_key(sentence)
    assert c[WC.ORIGIN_FP_KEY] == WC.name_fp(c[WC.ORIGIN_KEY])
    dumped = json.dumps(c, ensure_ascii=False)
    assert "那間要簽約" not in dumped
    w2, _src = await _picked("yi")
    assert _cands(w2)[WC.ORIGIN_KEY] == ""


# ════════════════════════════════════════════════════════════════════
# (m) 候選集內講法
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rc", [KEEP, RETRACT])
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_m_lenient_fill_restating_the_vague_phrase_keeps_the_pick(api, where, rc):
    """(m)：寬鬆選定後補欄位那句含原模糊講法（本回合講）⇒ `write_candidate_name_kept`、⛔ 依講法重查。`keep` ⇒ 卡是
    原選定；`retract`（§11.14：只有它會往下分類）⇒ 候選集內講法照樣丟棄、已撤回重列。"""
    w, src = await _picked("jia")
    res, p = await _fill_with_name(w, src, "宏匯個人", where=where, said_in_text=True, rc=rc)
    assert p.lenient_calls == []
    _assert_kept_by_rc(w, src, res, rc)


@pytest.mark.parametrize("rc", [KEEP, RETRACT])
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_m_exact_fill_restating_the_title_keeps_the_pick(api, where, rc):
    """(m)：A-2a 精確同名選定後補欄位重述正名 ⇒ `write_candidate_name_kept`；`keep` ⇒ 卡是原選定，`retract` ⇒
    已撤回重列。"""
    w, src = await _picked("exact")
    res, _p = await _fill_with_name(w, src, src.spoken, where=where, said_in_text=True, rc=rc)
    _assert_kept_by_rc(w, src, res, rc)


@pytest.mark.parametrize("rc", [KEEP, RETRACT])
async def test_m_part_of_another_candidate_title_is_in_set(api, rc):
    """(m)：講法被包含於候選集另一筆的系統正名（取自本回合帶身分取得的列）⇒ 候選集內講法、丟棄；`keep` ⇒ 卡是原
    選定，`retract` ⇒ 已撤回重列。"""
    w, src = await _picked("jia")
    res, _p = await _fill_with_name(w, src, "宏匯C個人", where="intent", said_in_text=True, rc=rc)
    _assert_kept_by_rc(w, src, res, rc)


async def test_m_control_titles_from_draft_value_requeries(api, monkeypatch):
    """正對照（(m)「正名改用草稿值 ⇒ 失敗」）：比對用的正名改成草稿現值 ⇒「宏匯C個人」不被包含於任一列正名 ⇒ `name`
    指令判新名稱重查（正常 ⇒ 對到另一筆全名 ⇒ 撤回重列，見 `test_m_name_command_of_another_candidate_withdraws`）。
    選定後回合改指令式：候選集內講法的判定在 `_write_candidates_name_hits`（名稱合併與 `name` 指令共用一支），暫改處隨之。"""
    orig = RT._write_candidates_name_hits

    def draft_titles(self, wd, cands, raw):
        saved = wd.offered_rows
        wd.offered_rows = {"x": {"id": "x", "title": wd.draft["fields"].get("estate_name")}}
        try:
            return orig(self, wd, cands, raw)
        finally:
            wd.offered_rows = saved

    monkeypatch.setattr(RT, "_write_candidates_name_hits", draft_titles)
    w, src = await _picked("jia")
    res, _p = await _fill_with_name(w, src, "宏匯C個人", where="intent", said_in_text=True,
                                    cmd=[("name", "宏匯C個人")])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations


async def test_m_name_command_of_another_candidate_repicks(api):
    """(m)＋計畫 §4.3 第 3 點、修復輪 1 §8.2 點 1：`name` 指令的名稱被包含於候選集另一筆（非現選定）的系統正名
    （「宏匯C個人」）、只對到那一筆、且本句講了 ⇒ 改選那一筆（卡是 56907；⛔ 出舊選定的卡、⛔ 依新名稱重查、
    ⛔ 寬鬆模型）。"""
    w, src = await _picked("jia")
    res, p = await _fill_with_name(w, src, "宏匯C個人", where="intent", said_in_text=True,
                                   cmd=[("name", "宏匯C個人")])
    assert p.lenient_calls == []
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert _card_id(w, res) == "56907" != src.picked, res.answer


async def test_m_rows_unavailable_only_origin_applies(api, monkeypatch):
    """(m)：本回合取列失敗 ⇒ 不附候選段（⛔ `target`、⛔ `pick_id`；假模型照回指令也不讀）⇒ 沒設 `cmd_offered`，名稱值一律
    丟棄（計畫 §4.3 第 7 點）：原講法與候選集外、本句講的名稱都不解綁、選定不動。"""
    async def _none(*_a, **_k):
        return []

    w, src = await _picked("jia")
    monkeypatch.setattr(runtime_mod, "name_lenient_rows_for_ids", _none)
    res, p = await _fill_with_name(w, src, "宏匯個人", where="intent", said_in_text=True,
                                   cmd=[("name", "宏匯個人")])
    assert all(_enum(k) is None and WF.PICK_TARGET_KEY not in _schema(k)["properties"]
               for k in p.intent_calls)
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations and _card_id(w, res) == src.picked
    w, src = await _picked("jia")
    res, _p = await _fill_with_name(w, src, "宏匯C個人", where="intent", said_in_text=True,
                                    cmd=[("name", "宏匯C個人")])
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations and _card_id(w, res) == src.picked


async def test_m_out_of_set_name_containing_the_origin_requeries(api):
    """(m)：`name` 指令的名稱**包含**原講法（「宏匯個人二館」）⇒ 不算候選集內講法 ⇒ 依新名稱重查。"""
    w, src = await _picked("jia")
    res, p = await _fill_with_name(w, src, "宏匯個人二館", where="intent", said_in_text=True,
                                   cmd=[("name", "宏匯個人二館")])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations, res.trace.violations
    (kw,) = p.lenient_calls                                           # 依新名稱重查（假寬鬆模型回 none ⇒ 查無出口）
    assert "宏匯個人二館" in kw["messages"][2]["content"]
    assert res.trace.pending_id is None


async def test_m_control_counting_containment_of_origin_keeps_it(api, monkeypatch):
    """正對照（(m)「把『包含原講法』算進候選集內講法 ⇒ 該支失敗」）。暫改處＝`_write_candidates_name_hits`（原講法命中
    多算「包含原講法」）；暫改內容不變。"""
    orig = RT._write_candidates_name_hits

    def contains_too(self, wd, cands, raw):
        origin_hit, matched = orig(self, wd, cands, raw)
        origin = (cands or {}).get(WC.ORIGIN_KEY) or ""
        if not origin_hit and origin and origin in runtime_mod._name_said_key(raw):
            return True, matched
        return origin_hit, matched

    monkeypatch.setattr(RT, "_write_candidates_name_hits", contains_too)
    w, src = await _picked("jia")
    res, p = await _fill_with_name(w, src, "宏匯個人二館", where="intent", said_in_text=True,
                                   cmd=[("name", "宏匯個人二館")])
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert p.lenient_calls == [] and _card_id(w, res) == src.picked    # ⛔ 依新名稱重查（上一支失敗）；選定不動出卡


async def test_m_control_without_in_set_exclusion_restated_origin_requeries(api, monkeypatch):
    """正對照（(m)「拿掉候選集內講法排除 ⇒ 原講法那支失敗」）：原講法比對拿掉 ⇒ `name` 指令重述「宏匯個人」被判新名稱。"""
    monkeypatch.setattr(RT, "_write_candidates_origin", staticmethod(lambda cands, draft: ""))
    w, src = await _picked("jia")
    res, _p = await _fill_with_name(w, src, "宏匯個人", where="intent", said_in_text=True,
                                    cmd=[("name", "宏匯個人")])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations


# ════════════════════════════════════════════════════════════════════
# (n) 只撤回
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_n_retract_withdraws_and_relists(api, name):
    """(n)＋§11.14 第 2 點：已選定且 `rechoice=retract` ⇒ `picked` 清掉、已撤回、重列同一份 `ids`、
    `write_candidate_retract:typed`。"""
    w, src = await _picked(name)
    await _retract(w, src)


async def test_n_retract_while_withdrawn_is_none(api):
    """(n)：已撤回期間不附 `rechoice`（假模型照回 `retract`）⇒ 不讀（不再記撤回標記、仍已撤回）。"""
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", intents=[_rt(CC)])
    res, _p = await _t(w, "還是不對", intents=[_rt(CC)])
    assert WC.V_CANDIDATE_RETRACT_TYPED not in res.trace.violations
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids


async def test_n_retract_while_unpicked_is_none(api):
    """(n)：未選定時不附 `rechoice`（假模型照回 `retract`）⇒ 與回 `none` 逐字相同；⛔ 撤回標記。"""
    w, src, _r = await _listed("exact")
    res, _p = await _t(w, "都不是", intents=[_rt(CC)])
    w2, _src, _r2 = await _listed("exact")
    res2, _p = await _t(w2, "都不是", intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_RETRACT_TYPED not in res.trace.violations
    assert _snap(res) == _snap(res2)
    assert _cands(w) == _cands(w2) and WC.WITHDRAWN_KEY not in _cands(w)


async def test_n_old_pick_id_retract_value_is_not_a_retract(api):
    """§11.14 第 2 點（取代第 7a 點）：已選定回合 AI 回舊形狀 `pick_id`＝`retract`（enum 已無此值）、沒帶 `rechoice`
    ⇒ 不撤回、選定不動（`retract` 只經 `rechoice` 觸發）。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id="retract")])
    assert WC.V_CANDIDATE_RETRACT_TYPED not in res.trace.violations
    assert _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


async def test_n_control_ignoring_retract_keeps_the_pick(api, monkeypatch):
    """正對照（(n)「忽略 `retract` ⇒ 失敗」）：撤回處置換成不動 ⇒ 選定留著、⛔ 已撤回。"""
    monkeypatch.setattr(RT, "_write_candidates_withdraw", staticmethod(lambda *a, **k: None))
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)], intents=[_rt(CC)])
    assert _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


# ════════════════════════════════════════════════════════════════════
# §11.14 第 1 點：客人句中講出的編號不算 AI 猜測（選對紀錄「分不出」）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text", ["是 26007 那間", "要編號２６００７的", "26007"])
async def test_s1_prepick_said_id_in_sentence_is_picked_on_an_indistinct_pair(api, monkeypatch, text):
    """第 1 點（未選定，PR-2／PR-7）：兩筆畫面除編號外全同；客人句中講出 26007（含全形數字，NFKC 後同）、AI 回
    `pick_id`＝26007 ⇒ 選定成立（⛔ `pick_right:indistinct` 退回）。整句只打編號且 AI 回同一編號那格同樣成立（修前
    `pick_id` 分支先選中、被「分不出」退回）。"""
    w = await _twin_listed(monkeypatch)
    res, _p = await _t(w, text, [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id="26007")])
    assert WC.V_PICK_RIGHT_INDISTINCT not in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_PICK_TYPED in res.trace.violations, res.trace.violations
    assert _cands(w)["picked"] == "26007"


async def test_s1_postpick_said_id_in_sentence_repicks_on_an_indistinct_pair(api, monkeypatch):
    """第 1 點（已選定，§11.4 第 2 點同一條）：選定 26007 後「改成 40303 那間」、AI 回 `switch`＋40303 ⇒ 改選成立、
    ⛔ 退回；補欄位 ⇒ 卡是 40303。"""
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "改成 40303 那間", [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "40303")])
    assert WC.V_PICK_RIGHT_INDISTINCT not in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations
    assert _cands(w)["picked"] == "40303"
    res2, _p = await _t(w, _CC_REST_TEXT, intents=[_intent(CC, **_CC_REST)])
    assert _card_id(w, res2) == "40303"


@pytest.mark.parametrize("text", ["40303 還是 26007", "26007，對，就 26007", "26007 那間，40303 不要"])
async def test_s1_two_set_ids_or_repeated_id_still_refused(api, monkeypatch, text):
    """第 1 點「恰有一段」：句中有兩個候選集編號、或同一編號講兩次 ⇒ 不免除（保守：依出現次數計），未選定時照舊
    `pick_right:indistinct` 退回重列；已選定時改選目標被退回 ⇒ 已撤回。"""
    w = await _twin_listed(monkeypatch)
    res, _p = await _t(w, text, [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id="26007")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res.trace.violations, res.trace.violations
    assert _cands(w)["picked"] is None and res.trace.pending_id is None
    w2 = await _twin_indistinct(monkeypatch)
    res2, _p = await _t(w2, text, [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "40303")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res2.trace.violations, res2.trace.violations
    assert WC.is_withdrawn(_cands(w2)) and res2.trace.pending_id is None


async def test_s1_digit_run_without_a_matching_pick_id_selects_nothing(api, monkeypatch):
    """第 1 點「數字段只作佐證」：句中有候選集編號但 AI 沒回該編號 ⇒ ⛔ 單憑句中數字選定或改選：
    未選定＋`none` ⇒ 不選定（重列）；未選定＋AI 回另一筆 40303 ⇒ 該段≠`pick_id` ⇒ 照舊退回；已選定 26007＋
    「是 40303 那間」＋`keep`／`none` ⇒ 不改選。"""
    w = await _twin_listed(monkeypatch)
    res, _p = await _t(w, "是 26007 那間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    assert _cands(w)["picked"] is None and WC.V_CANDIDATE_PICK_TYPED not in res.trace.violations
    res, _p = await _t(w, "是 26007 那間", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id="40303")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res.trace.violations and _cands(w)["picked"] is None
    w2 = await _twin_indistinct(monkeypatch)
    res2, _p = await _t(w2, "是 40303 那間", [_out(MODEL_SAID)] * 2,
                        intents=[_intent_rc6(CC, KEEP, WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_REPICK_TYPED not in res2.trace.violations
    assert _cands(w2)["picked"] == "26007"


async def test_s1_said_id_still_checks_the_amount(api):
    """第 1 點「金額期間不符照舊套用」：改選目標編號講在句中（709739）且 AI 回 `switch`＋709739，但與先前講的金額
    不符 ⇒ 照舊退回、已撤回（同 `test_b_refused_amount_mismatch_repick_withdraws` 的帳單候選集）。"""
    w = _World()
    keelung = "基隆溫馨一人宅套房"
    await _t(w, f"{keelung} 7月那期 5000元 延後 3 天",
             intents=[_intent(DUE, estate_name=keelung, period="7月那期", days="3", said_amount="5000")])
    c = dict(_cands(w), picked="709740")
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, _p = await _t(w, "改 709739 那張", [_out(MODEL_SAID)], intents=[_sw(DUE, "709739")])
    assert WC.V_PICK_RIGHT_AMOUNT_MISMATCH in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations
    assert WC.is_withdrawn(_cands(w)) and res.trace.pending_id is None


async def test_s1_control_without_the_said_id_exemption_refuses(api, monkeypatch):
    """正對照（第 1 點「拿掉 ⇒ 退回」）：`_said_id_is_pick_id` 一律回 `False` ⇒ 句中講出的編號照舊被「分不出」退回
    （上兩支 `test_s1_prepick_*`／`test_s1_postpick_*` 失敗）。"""
    monkeypatch.setattr(runtime_mod, "_said_id_is_pick_id", lambda *a, **k: False)
    w = await _twin_listed(monkeypatch)
    res, _p = await _t(w, "是 26007 那間", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id="26007")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res.trace.violations and _cands(w)["picked"] is None
    w2 = await _twin_indistinct(monkeypatch)
    res2, _p = await _t(w2, "改成 40303 那間", [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "40303")])
    assert WC.V_PICK_RIGHT_INDISTINCT in res2.trace.violations and WC.is_withdrawn(_cands(w2))


def test_s1_said_id_helper_counts_maximal_ascii_runs():
    """第 1 點的數字段定義（純函式）：NFKC 後以非數字為界的最長連續數字；只算整段 ASCII 且屬於 `ids` 的段，依出現
    次數計；恰一段且等於 `pick_id` 才成立。較長數字裡含編號（「1260071」）不算。"""
    f = runtime_mod._said_id_is_pick_id
    ids = ["40303", "26007"]
    assert f("是 26007 那間", ids, "26007") is True
    assert f("２６００７", ids, "26007") is True
    assert f("26007 和 26007", ids, "26007") is False
    assert f("40303 還是 26007", ids, "26007") is False
    assert f("是 26007 那間", ids, "40303") is False
    assert f("1260071", ids, "26007") is False
    assert f("電話 0912345678 要 26007", ids, "26007") is True
    assert f("沒有編號", ids, "26007") is False
    assert f(None, ids, "26007") is False and f("26007", ids, None) is False


# ════════════════════════════════════════════════════════════════════
# §11.14 第 2 點：已選定回合先回 `rechoice`
# ════════════════════════════════════════════════════════════════════
_BAD_RC = [KEEP, _NO_RC, "Switch", "SWITCH", 1, "", None]


@pytest.mark.parametrize("legacy", [{"rechoice": "switch"}, {"rechoice": "keep"}, {}], ids=["switch", "keep", "none"])
@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_rc_legacy_keys_are_never_read_on_selected_turns(api, name, legacy):
    """選定後回合改指令式（計畫 §4.2、§4.3「讀不讀 `target`」）：舊鍵 `pick_id`、`rechoice`、`new_name` 即使假模型照回也不讀——
    `target` 為空陣列 ⇒ 維持，選定不動、⛔ `write_candidate_repick:typed`（四種來源）。"""
    w, src = await _picked(name)
    obj = {"action": src.action, "fields": [], WF.PICK_TARGET_KEY: [], WF.PICK_ID_KEY: src.other,
           "new_name": STUDENT_ESTATE, **legacy}
    res, _p = await _t(w, "按錯了，要另一間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent(raw=json.dumps(obj, ensure_ascii=False))])
    assert WC.V_CANDIDATE_REPICK_TYPED not in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_RETRACT_TYPED not in res.trace.violations
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


async def test_rc_control_reading_legacy_pick_id_as_switch_repicks(api, monkeypatch):
    """正對照（「舊鍵不讀」）：`intent_pick_target` 改成把舊鍵 `pick_id` 讀成 `pick` 指令 ⇒ 上一支改選（失敗）。"""
    monkeypatch.setattr(WF, "intent_pick_target", lambda obj: [{"op": "pick", "value": obj.get(WF.PICK_ID_KEY)}])
    w, src = await _picked("jia")
    obj = {"action": CC, "fields": [], WF.PICK_TARGET_KEY: [], WF.PICK_ID_KEY: src.other}
    res, _p = await _t(w, "按錯了，要另一間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent(raw=json.dumps(obj, ensure_ascii=False))])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations and _cands(w)["picked"] == src.other


@pytest.mark.parametrize("rc", [KEEP, _NO_RC, "bogus"], ids=["keep", "missing", "bogus"])
@pytest.mark.parametrize("where", ["intent", "proposal"])
async def test_rc_keep_drops_the_candidate_name(api, where, rc):
    """第 2 點：已選定、`rechoice` 為 `keep`、缺漏或值不合 ⇒ 本回合候選集那一欄的名稱值一律丟棄（記
    `write_candidate_name_kept`）——即使那是候選集外、本回合原話講的新名稱；卡是原選定（⛔ 依新名稱重查）。
    意圖與模型提議兩處各一。（同一句 `retract` ⇒ 解綁重查，見 `test_d_name_said_this_turn_unbinds_and_requeries`。）"""
    w, src = await _picked("exact")
    res, p = await _fill_with_name(w, src, STUDENT_ESTATE, where=where, said_in_text=True, rc=rc)
    assert WC.V_CANDIDATE_NAME_KEPT in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_NAME_NEW not in res.trace.violations
    assert p.lenient_calls == []
    assert _card_id(w, res) == src.picked


@pytest.mark.parametrize("rc", [KEEP, RETRACT, _NO_RC], ids=["keep", "retract", "missing"])
async def test_rc_whole_sentence_id_repicks_regardless_of_rechoice(api, rc):
    """第 2 點「整句只打 `ids` 內另一編號 ⇒ 改選（不看 `rechoice`）」：選定 58207 後整句只打 55455、AI 回 `keep`、
    `retract` 或沒帶 ⇒ 改選成 55455（⛔ 撤回）；補欄位 ⇒ 卡是 55455。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, "55455", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_rc6(CC, rc, WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_REPICK_TYPED in res.trace.violations, res.trace.violations
    assert WC.V_CANDIDATE_RETRACT_TYPED not in res.trace.violations
    assert _cands(w)["picked"] == "55455"
    res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    assert _card_id(w, res2) == "55455"


@pytest.mark.parametrize("name", ALL_SOURCES)
async def test_rc_retract_with_a_new_name_said_unbinds_and_requeries(api, name):
    """選定後回合改指令式（S11 形狀）：已選定後「不是這間，改成 {學生宅}」、AI 回 `name` 指令（新名稱放 `target`、⛔ 欄位）
    ⇒ `write_candidate_name_new`、解綁重查、⛔ 卡是舊選定。"""
    w, src = await _picked(name)
    text = f"不是這間，改成 {STUDENT_ESTATE}"
    res, _p = await _t(w, text, [_out(MODEL_SAID)] * 3,
                       intents=[_cmd(src.action, ("name", STUDENT_ESTATE))], lenient=[_ids_resp(["none"])])
    assert WC.V_CANDIDATE_NAME_NEW in res.trace.violations, res.trace.violations
    c = _cands(w)
    assert c is None or c.get("picked") != src.picked
    assert res.trace.pending_id is None or str(
        w.pending()[res.trace.pending_id]["payload"][src.card_key]) not in (src.picked, src.picked_card)


# ════════════════════════════════════════════════════════════════════
# §11.14 第 3 點：選定後誤換動作的防護
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rc", [RETRACT, KEEP], ids=["retract", "keep"])
@pytest.mark.parametrize("empty", ["no_fields", "blank_value"])
async def test_s3_other_action_without_values_keeps_the_draft(api, rc, empty):
    """第 3 點（S19 形狀）：已選定、仍綁定；客人說「剛剛選錯了」、AI 判成另一支寫入動作（repair_create）卻沒有任何
    非空欄位值（沒欄位、或值只有空白）⇒ 草稿不換（動作、欄位逐位相同）、`write_candidate_action_kept`；候選集照
    `rechoice` 處置（`retract` ⇒ 已撤回並重列同一份 `ids`；`keep` ⇒ 選定不動）。"""
    w, src = await _picked("exact")
    before = json.dumps(w.draft()["fields"], ensure_ascii=False, sort_keys=True)
    fields = {} if empty == "no_fields" else {"description": "  "}
    res, _p = await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 3,
                       intents=[_intent_rc6("repair_create", rc, WF.PICK_ID_NONE, **fields)])
    assert WC.V_CANDIDATE_ACTION_KEPT in res.trace.violations, res.trace.violations
    draft = w.draft()
    assert draft["action"] == CC
    assert json.dumps(draft["fields"], ensure_ascii=False, sort_keys=True) == before
    if rc == RETRACT:
        assert WC.V_CANDIDATE_RETRACT_TYPED in res.trace.violations
        assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids and _ask(res), res.answer
    else:
        assert _cands(w)["picked"] == src.picked
    res2, _p = await _t(w, src.rest_text, intents=[_fill_intent(src)])
    if rc == KEEP:
        assert _card_id(w, res2) == src.picked
    else:
        assert res2.trace.pending_id is None and _pick_ids(res2) == src.ids


async def test_s3_withdrawn_other_action_without_values_keeps_the_draft(api):
    """第 3 點「已選定或已撤回」：已撤回後「幫我報修」、AI 回 repair_create 沒有值 ⇒ 草稿不換、
    `write_candidate_action_kept`、仍已撤回並重列。"""
    w, src = await _picked("exact")
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    assert WC.is_withdrawn(_cands(w))
    res, _p = await _t(w, "幫我報修", [_out(MODEL_SAID)] * 3, intents=[_intent("repair_create")])
    assert WC.V_CANDIDATE_ACTION_KEPT in res.trace.violations, res.trace.violations
    assert w.draft()["action"] == CC and WC.is_withdrawn(_cands(w))
    assert _pick_ids(res) == src.ids, res.answer


async def test_s3_other_action_with_values_switches(api):
    """第 3 點「帶了值 ⇒ 照現行換動作」：已選定後客人講「改報修 冷氣不冷」、AI 回 repair_create 帶描述 ⇒ 換成修繕
    草稿、⛔ `write_candidate_action_kept`。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, "改報修 冷氣不冷", [_out(MODEL_SAID)] * 3,
                       intents=[_intent_rc6("repair_create", KEEP, WF.PICK_ID_NONE, description="冷氣不冷")])
    assert WC.V_CANDIDATE_ACTION_KEPT not in res.trace.violations, res.trace.violations
    assert w.draft()["action"] == "repair_create"
    assert w.draft()["fields"].get("description") == "冷氣不冷"


async def test_s3_no_candidate_set_keeps_current_behaviour(api):
    """第 3 點「無候選集時照現行」：草稿（建合約、名稱唯一 ⇒ 沒有候選集）回合，AI 回 repair_create 沒有值 ⇒ 照現行換成
    修繕草稿、⛔ `write_candidate_action_kept`。"""
    w = _World()
    await _t(w, f"{STUDENT_ESTATE} 這間要簽新租約", [_out(MODEL_SAID)] * 2,
             intents=[_intent(CC, estate_name=STUDENT_ESTATE)])
    assert _cands(w) is None and w.draft()["action"] == CC
    res, _p = await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 3, intents=[_intent("repair_create")])
    assert WC.V_CANDIDATE_ACTION_KEPT not in res.trace.violations, res.trace.violations
    assert w.draft()["action"] == "repair_create"


async def test_s3_control_without_the_guard_switches_the_draft(api, monkeypatch):
    """正對照（第 3 點「拿掉防護 ⇒ 失敗」）：`_intent_has_value` 一律回 `True`（防護永不成立）⇒ 同一句換成修繕草稿、
    候選集解綁（`test_s3_other_action_without_values_keeps_the_draft` 失敗）。"""
    monkeypatch.setattr(runtime_mod, "_intent_has_value", lambda intent: True)
    w, src = await _picked("exact")
    res, _p = await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 3,
                       intents=[_intent_rc6("repair_create", RETRACT, WF.PICK_ID_NONE)])
    assert WC.V_CANDIDATE_ACTION_KEPT not in res.trace.violations
    assert w.draft() is None or w.draft()["action"] != CC


def test_s3_marker_constant():
    assert WC.V_CANDIDATE_ACTION_KEPT == "write_candidate_action_kept"
    assert "V_CANDIDATE_ACTION_KEPT" in WC.__all__
