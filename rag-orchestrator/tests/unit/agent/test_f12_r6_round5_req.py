"""unit：F12 r6 復原第 5 輪（計畫 `.kiro/specs/agentic-mcp-orchestration/plan-name-lenient-f12-20261022.md`
§11.15.3 修法 1～6；§11.15.4「F1 另加」）。

F1 另加 ↔ 本檔測試（逐條）：
  - 第 1 點 選定後不整句填入                     → `test_p1_*`
  - 第 2 點 `new_name` 專屬欄位                  → `test_p2_*`
  - 第 3 點 句中講出的編號採為改選               → `test_p3_*`
  - 第 4 點 名稱不算新動作的值                   → `test_p4_*`
  - 第 5 點 附候選段的意圖呼叫截斷重送一次       → `test_p5_*`
  - 第 6 點 同一次改選與改講新名稱（單次決定）   → `test_p6_*`
  - 標記常數                                     → `test_markers_*`
各點的正對照（暫改原始碼的哪一處 ⇒ 哪一支失敗 ⇒ 已還原）見收案報告；本檔另有 monkeypatch 型正對照
`test_*_control_*`。

選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md`）：已選定回合的 schema 換成 `target` 指令清單，
`rechoice`／`new_name`／`pick_id` 已刪；第 2、3、4、6 點在已選定回合的測試依新契約改寫（`name`／`pick` 指令、
名稱值一律丟棄），已撤回、未選定回合的測試與第 1、5 點不變。

資料：真 `JGBSystemAPI`＋mock transport（`assistant_demo_vendor4.json`，viewer 12291／role 20151）；模型一律假，
全部離線。期望值為 fixture 原始 JSON 人工查證（同 `test_f12_repick_r6_req.py` 檔頭）：
  - 「宏匯個人」查無 ⇒ 寬鬆：56907「瑞光宏匯C個人(空租)」、56906「瑞光宏匯B個人」、56905「瑞光宏匯A法人」；
  - 「瑞光好房1(個人租客)」兩筆同名（58207、55455）；
  - 「學生獨立套房可租補」唯一（67338，只有 12291 看得到）；
  - 「台北文山-離塵一房(國泰)」兩筆畫面除編號外全同（40303、26007）；
  - 合約「捷士堂一廳一房」（錯字）⇒ 寬鬆：85516「捷仕堂大一廳一房」。
"""
from __future__ import annotations

import asyncio
import json

import pytest

from services.agent import runtime as runtime_mod
from services.agent import write_candidates as WC
from services.agent import write_forms as WF

from tests.unit.agent.test_a2a_write_candidates_req import _intent_raw
from tests.unit.agent.test_f12_name_lenient_req import (  # noqa: F401 — autouse 匯入
    _f12_env, _ids_resp, _intent_rc6, _NO_RC, _pick_ids,
)
from tests.unit.agent.test_f12_repick_r6_req import (
    CC, KEEP, MODEL_SAID, RETRACT, RT, STUDENT_ID, SWITCH, _ask, _assert_cmd_absent,
    _assert_cmd_offered, _cands, _cmd, _card_id, _enum, _picked, _proposal, _rt, _schema, _sw, _t,
    _twin_indistinct, _twin_listed, _withdrawn_state,
)
from tests.unit.agent.test_runtime_req import _fake_message, _fake_response
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import STUDENT_ESTATE, _intent, _out

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


REPAIR = "repair_create"
BILL = "manual_bill_create"
JIA_IDS = ["56907", "56906", "56905"]
CONTRACT_TYPO = "捷士堂一廳一房"


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def _nn(action: str, rechoice=_NO_RC, pick_id=None, new_name=None, **fields):
    """已選定回合的假意圖回應：另帶 `new_name`（`None`＝不帶這個鍵；schema 順序 `new_name` 在 `rechoice` 之前）。"""
    obj: dict = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()]}
    if new_name is not None:
        obj["new_name"] = new_name
    if rechoice is not _NO_RC:
        obj["rechoice"] = rechoice
    if pick_id is not None:
        obj[WF.PICK_ID_KEY] = pick_id
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


def _truncated(content: str = '{"action": "contract_create", "fields": [], "rech'):
    """`finish_reason=length` 的假回應（內容是被截斷的半個 JSON）。"""
    resp = _fake_response(_fake_message(content=content), prompt_tokens=7, completion_tokens=3)
    resp.choices[0].finish_reason = "length"
    return resp


def _v(res) -> list:
    return res.trace.violations


async def _withdrawn(name: str = "jia"):
    w, src = await _picked(name)
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(src.action)])
    assert WC.is_withdrawn(_cands(w))
    return w, src


def _assert_conflict(w, src, res, before) -> None:
    """第 6 點決定 2：矛盾 ⇒ 視同 retract：已撤回、重列同一份 `ids`、名稱不套用、⛔ 解綁、⛔ 改選、⛔ 出卡。"""
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_CONFLICT in v, v
    assert WC.V_CANDIDATE_NAME_NEW not in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert WC.is_withdrawn(_cands(w)) and _withdrawn_state(w) == before
    assert _pick_ids(res) == src.ids and _ask(res), res.answer


def _assert_new_name(w, res, *, name=STUDENT_ESTATE, action=CC) -> None:
    """改講新名稱 ⇒ 名稱寫進候選集那一欄、解綁（候選集清掉）、依新名稱重查；草稿動作不變。"""
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_NEW in v, v
    assert WC.V_CANDIDATE_NAME_CONFLICT not in v, v
    assert _cands(w) is None
    assert w.draft()["action"] == action and w.draft()["fields"]["estate_name"] == name


# ════════════════════════════════════════════════════════════════════
# 第 1 點：選定後不整句填入
# ════════════════════════════════════════════════════════════════════
async def _repair_picked(w=None):
    """修繕：「宏匯個人那間要報修」⇒ 寬鬆候選 ⇒ 按鈕選定 56906 ⇒ 程式追問問題描述（恰一個欄位）。"""
    w = w or _World()
    res, _p = await _t(w, "宏匯個人那間要報修", intents=[_intent(REPAIR, estate_name="宏匯個人")],
                       lenient=[_ids_resp(JIA_IDS)])
    assert _pick_ids(res) == JIA_IDS, res.answer
    res2, _p = await _t(w, "pick:estate:56906")
    assert _ask(res2) and _cands(w)["picked"] == "56906", res2.answer
    assert w.draft()["asked"] == ["description"], w.draft()                 # 前提：整句填入的條件成立
    return w


async def test_p1_picked_ask_description_ai_extracts_nothing_never_fills(api):
    """第 1 點：選定後、追問問題描述，客人講的不是描述（「欸等一下」）、AI 沒抽到 ⇒ 問題描述 ⛔ 被整句填入、⛔ 出卡；
    程式照現行再追問。"""
    w = await _repair_picked()
    res, p = await _t(w, "欸等一下", [_out(MODEL_SAID)] * 2, intents=[_nn(REPAIR, KEEP, WF.PICK_ID_NONE, "")])
    assert len(p.intent_calls) == 1
    assert "description" not in w.draft()["fields"], w.draft()
    assert res.trace.pending_id is None and res.outcome["state"] == "clarifying", res.answer
    assert _cands(w)["picked"] == "56906"


async def test_p1_picked_ask_description_ai_extracts_fills_the_ai_value(api):
    """第 1 點：AI 抽到描述 ⇒ 填 AI 值（⛔ 整句）、出卡，卡上是選定那筆。"""
    w = await _repair_picked()
    res, _p = await _t(w, "冷氣不冷啦，你先記一下", [_out(MODEL_SAID)] * 2,
                       intents=[_nn(REPAIR, KEEP, WF.PICK_ID_NONE, "", description="冷氣不冷")])
    assert _card_id(w, res) == "56906"
    assert w.pending()[res.trace.pending_id]["payload"]["description"] == "冷氣不冷"


async def test_p1_withdrawn_repick_turn_never_fills(api):
    """第 1 點（Q15-1「已撤回」）：選定 ⇒ 撤回 ⇒ 下一回合打字重新選定（AI 回 `pick_id`），追問欄位是問題描述、
    AI 沒抽到描述 ⇒ 那一回合 ⛔ 整句填入（「56907 那間」⛔ 變成問題描述）、⛔ 出卡。
    ⚠️ 撤回那一回合程式重列候選、草稿 `asked` 清成空（實跑所見）；「已撤回＋追問欄位恰為問題描述」的狀態由撤回後
    把草稿 `asked` 補回 `["description"]` 組成（同 `test_b_refused_amount_mismatch_repick_withdraws` 的組法）——驗程式
    規則本身：沒有本點時，這個狀態下整句填入條件成立。"""
    w = await _repair_picked()
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(REPAIR)])
    assert WC.is_withdrawn(_cands(w))
    w.draft()["asked"] = ["description"]                                   # 前提：整句填入的條件成立
    res, _p = await _t(w, "56907 那間", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(REPAIR, pick_id="56907")])
    assert WC.V_CANDIDATE_REPICK_TYPED in _v(res), _v(res)
    assert _cands(w)["picked"] == "56907"
    assert "description" not in w.draft()["fields"], w.draft()
    assert res.trace.pending_id is None, res.answer


async def _bill_picked():
    """手開帳單：合約名稱錯字＋金額＋期限 ⇒ 合約寬鬆候選 ⇒ 按鈕選定 85516 ⇒ 只剩帳單項目要問。"""
    w = _World()
    res, _p = await _t(w, f"合約 {CONTRACT_TYPO} 要開一張帳單，金額 1000，期限 2026/11/30",
                       intents=[_intent(BILL, contract_ref=CONTRACT_TYPO, total="1000", date_expire="2026/11/30")],
                       lenient=[_ids_resp(["85516"])])
    assert _pick_ids(res)[0] == "85516", res.answer
    res2, _p = await _t(w, "pick:contract:85516")
    assert _ask(res2), res2.answer
    assert w.draft()["asked"] == ["title"], w.draft()                      # 前提：整句填入的條件成立
    return w


async def test_p1_picked_ask_bill_title_ai_extracts_nothing_never_fills(api):
    """第 1 點（Q15-2「所有文字欄」）：選定後只追問帳單項目，客人改口（「等等，不是這個合約」）、AI 沒抽到 ⇒
    帳單項目 ⛔ 被整句填入、⛔ 出卡。"""
    w = await _bill_picked()
    res, _p = await _t(w, "等等，不是這個合約", [_out(MODEL_SAID)] * 2,
                       intents=[_nn(BILL, KEEP, WF.PICK_ID_NONE, "")])
    assert "title" not in w.draft()["fields"], w.draft()
    assert res.trace.pending_id is None, res.answer


async def test_p1_unpicked_whole_sentence_fill_unchanged(api):
    """第 1 點「未選定時整句填入照舊」：沒有候選集（名稱唯一）、追問問題描述、AI 沒抽到 ⇒ 整句填入、出卡。"""
    w = _World()
    res, _p = await _t(w, f"{STUDENT_ESTATE} 要報修", [_out(MODEL_SAID)] * 2,
                       intents=[_intent(REPAIR, estate_name=STUDENT_ESTATE)])
    assert _cands(w) is None and w.draft()["asked"] == ["description"], (res.answer, w.draft())
    res2, _p = await _t(w, "冷氣不冷", [_out(MODEL_SAID)] * 2, intents=[_intent(REPAIR)])
    assert res2.outcome["state"] == "confirm_pending", res2.answer
    payload = w.pending()[res2.trace.pending_id]["payload"]
    assert payload["description"] == "冷氣不冷" and payload["estate_name"] == STUDENT_ESTATE, payload


async def test_p1_control_post_pick_start_off_fills_the_sentence(api, monkeypatch):
    """正對照（monkeypatch 版）：回合開始的快照恆為 `False`（＝拿掉「選定後不跑整句填入」）⇒ 第一支那一句被整句填成
    問題描述、出卡。"""
    w = await _repair_picked()
    orig = RT._write_draft_begin

    def _begin(self, acc, *a, **k):
        out = orig(self, acc, *a, **k)
        if acc.write_draft is not None:
            acc.write_draft.post_pick_start = False
        return out

    monkeypatch.setattr(RT, "_write_draft_begin", _begin)
    res, _p = await _t(w, "欸等一下", [_out(MODEL_SAID)] * 2, intents=[_nn(REPAIR, KEEP, WF.PICK_ID_NONE, "")])
    assert _card_id(w, res) == "56906"
    assert w.pending()[res.trace.pending_id]["payload"]["description"] == "欸等一下"


# ════════════════════════════════════════════════════════════════════
# 第 2 點：`new_name`
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("state", ["unpicked", "withdrawn"])
@pytest.mark.usefixtures("closing_handoff_off")
async def test_p2_schema_no_new_name_when_unpicked_or_withdrawn(api, state):
    """第 2 點：未選定、已撤回的回合 ⛔ `new_name`（schema 與系統句照第 4 輪：無 `rechoice`、無規則句）。
    （已選定回合的 schema 見 `test_post_pick_commands_req.py` F1 (a)。）"""
    if state == "withdrawn":
        w, src = await _withdrawn("jia")
    else:
        w = _World()
        await _t(w, "宏匯個人那間要簽約", intents=[_intent(CC, estate_name="宏匯個人")],
                 lenient=[_ids_resp(JIA_IDS)])
    _res, p = await _t(w, "好", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    (kw,) = p.intent_calls
    _assert_cmd_absent(kw, JIA_IDS)
    schema = _schema(kw)
    assert "new_name" not in schema["properties"] and "new_name" not in schema["required"]
    assert "new_name" not in kw["messages"][0]["content"]


@pytest.mark.parametrize("rc", [KEEP, RETRACT, _NO_RC], ids=["keep", "retract", "missing"])
async def test_p2_new_name_qualified_unbinds_and_requeries(api, rc):
    """第 2 點（改寫為 `name` 指令）：已選定、AI 回 `name` 指令＝候選集外且出自本句的名稱 ⇒ 名稱寫進候選集那一欄、
    解綁、依新名稱重查（唯一 ⇒ 卡是 67338）、記 `write_candidate_name_new`。（替身把舊式 `new_name` 換成 `name` 指令；
    `rc` 三格在新契約下結果相同。）"""
    w, src = await _picked("exact")
    res, p = await _t(w, f"啊講錯了，是{STUDENT_ESTATE}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                      intents=[_nn(CC, rc, WF.PICK_ID_NONE, STUDENT_ESTATE, **src.rest)])
    assert len(p.intent_calls) == 1
    assert WC.V_CANDIDATE_NAME_NEW in _v(res), _v(res)
    assert _card_id(w, res) == STUDENT_ID


async def test_p2_name_command_not_said_this_turn_is_invalid_and_withdraws(api):
    """第 2 點（改寫）：`name` 指令的名稱不出自本句（模型從上下文填回）⇒ 無效 ⇒ 撤回並重列同一份 `ids`
    （`write_candidate_cmd_invalid`）；⛔ 依該名稱重查。（舊契約「忽略、卡是原選定」已不存在：無效指令一律撤回。）"""
    w, src = await _picked("exact")
    before = _withdrawn_state(w)
    res, p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", STUDENT_ESTATE), **src.rest)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_NEW not in v and WC.V_CANDIDATE_CMD_INVALID in v, v
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids and p.lenient_calls == [], res.answer


@pytest.mark.parametrize("value, effect", [("宏匯個人", "keep"), ("瑞光宏匯C個人", "repick")],
                         ids=["origin", "title_part"])
async def test_p2_name_command_in_set_value_never_requeries(api, value, effect):
    """第 2 點（改寫）：`name` 指令的名稱是候選集內講法 ⇒ ⛔ 依該名稱重查（⛔ `write_candidate_name_new`）：
    原講法 ⇒ 維持（卡是原選定 56906）；系統正名的一部分、唯一對到清單內另一筆（56907）且本句講了 ⇒ 改選那一筆
    （修復輪 1，計畫 §8.2 點 1；卡是 56907）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"就{value}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", value), **src.rest)])
    assert WC.V_CANDIDATE_NAME_NEW not in _v(res), _v(res)
    if effect == "keep":
        assert _card_id(w, res) == src.picked
    else:
        assert _card_id(w, res) == "56907" != src.picked, res.answer


@pytest.mark.parametrize("value", ["", "   ", 5], ids=["empty", "blank", "int"])
async def test_p2_name_command_bad_value_is_invalid_and_withdraws(api, value):
    """第 2 點（改寫）：`name` 指令的值空字串、只有空白、非字串 ⇒ 無效 ⇒ 撤回並重列（`write_candidate_cmd_invalid`）。"""
    w, src = await _picked("exact")
    res, _p = await _t(w, f"{STUDENT_ESTATE} {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", value), **src.rest)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_NEW not in v and WC.V_CANDIDATE_CMD_INVALID in v, v
    assert WC.is_withdrawn(_cands(w)), res.answer


async def test_p2_target_key_absent_is_invalid_and_withdraws(api):
    """第 2 點（改寫）：回覆沒帶 `target` 鍵 ⇒ 無效 ⇒ 撤回並重列（`__raw__` 讓替身原樣送、不補 `target`）。"""
    w, src = await _picked("exact")
    obj = {"action": CC, "fields": [{"key": k, "value": v} for k, v in src.rest.items()], "__raw__": 1}
    res, _p = await _t(w, f"{STUDENT_ESTATE} {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_intent(raw=json.dumps(obj, ensure_ascii=False))])
    v = _v(res)
    assert WC.V_CANDIDATE_CMD_INVALID in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert WC.is_withdrawn(_cands(w)), res.answer


# ════════════════════════════════════════════════════════════════════
# 第 3 點：句中講出的編號採為改選
# ════════════════════════════════════════════════════════════════════
async def test_p3_pick_command_with_said_id_repicks(api):
    """第 3 點（改寫為 `pick` 指令）：已選定 56906，AI 回 `pick` 指令＝56907（在本回合附的候選編號內）⇒ 改選 56907
    （`write_candidate_repick:typed`）；補欄位 ⇒ 卡是 56907。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "是 56907 那間才對", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "56907"))])
    assert WC.V_CANDIDATE_REPICK_TYPED in _v(res), _v(res)
    assert WC.V_CANDIDATE_RETRACT_TYPED not in _v(res)
    assert _cands(w)["picked"] == "56907"
    res2, _p = await _t(w, src.rest_text, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == "56907"


async def test_p3_empty_command_list_never_repicks(api):
    """第 3 點（改寫）：AI 回空指令清單（維持）、句中沒講編號 ⇒ ⛔ 改選（選定不動）。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, "是另一間才對", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC)])
    assert WC.V_CANDIDATE_REPICK_TYPED not in _v(res), _v(res)
    assert _cands(w)["picked"] == "56906"


# ════════════════════════════════════════════════════════════════════
# 第 4 點：名稱不算新動作的值
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rc", [KEEP, RETRACT, _NO_RC], ids=["keep", "retract", "missing"])
async def test_p4_picked_other_action_only_new_name_keeps_action_and_requeries(api, rc):
    """第 4 點（改寫）：已選定（建合約），AI 判成修繕、名稱只放在 `name` 指令（候選集外、本句講的）⇒ ⛔ 換動作、記
    `write_candidate_action_kept`、解綁依該名稱重查、記 `write_candidate_name_new`（名稱欄值故意帶「那間」：
    名稱欄值一律丟棄、只用 `name` 指令的值）。"""
    w, src = await _picked("jia")
    text = f"啊講錯了，是{STUDENT_ESTATE}那間"
    intent = _nn(REPAIR, rc, WF.PICK_ID_NONE, STUDENT_ESTATE, estate_name=f"{STUDENT_ESTATE}那間")
    res, p = await _t(w, text, [_out(MODEL_SAID)] * 3, intents=[intent])
    assert len(p.intent_calls) == 1
    assert WC.V_CANDIDATE_ACTION_KEPT in _v(res), _v(res)
    _assert_new_name(w, res)


async def test_p4_picked_other_action_only_name_field_is_dropped(api):
    """第 4 點（改寫）：已選定＋另一動作＋只有名稱欄值（候選集外、本句講的）、沒有 `name` 指令 ⇒ ⛔ 換動作
    （`write_candidate_action_kept`）、名稱丟棄（`write_candidate_name_kept`）、⛔ 解綁重查、選定不動。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"啊講錯了，是{STUDENT_ESTATE}那間", [_out(MODEL_SAID)] * 3,
                       intents=[_cmd(REPAIR, estate_name=STUDENT_ESTATE)])
    v = _v(res)
    assert WC.V_CANDIDATE_ACTION_KEPT in v and WC.V_CANDIDATE_NAME_KEPT in v, v
    assert WC.V_CANDIDATE_NAME_NEW not in v
    assert w.draft()["action"] == CC and _cands(w)["picked"] == src.picked


async def test_p4_picked_other_action_name_field_with_pick_command_repicks(api):
    """第 4 點（改寫）：已選定＋另一動作＋名稱欄值（候選集外）＋`pick` 指令 56907 ⇒ ⛔ 換動作、名稱丟棄、
    `pick` 驗過 ⇒ 改選 56907（⛔ 矛盾重列：名稱欄值不是 `name` 指令）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"56907 那間，不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 3,
                       intents=[_cmd(REPAIR, ("pick", "56907"), estate_name=STUDENT_ESTATE)])
    v = _v(res)
    assert WC.V_CANDIDATE_ACTION_KEPT in v and WC.V_CANDIDATE_NAME_KEPT in v, v
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_CANDIDATE_NAME_CONFLICT not in v, v
    assert w.draft()["action"] == CC and _cands(w)["picked"] == "56907"


async def test_p4_withdrawn_other_action_only_new_name_keeps_action_and_requeries(api):
    """第 4 點：已撤回＋另一動作＋只有候選集外、本句講的名稱 ⇒ ⛔ 換動作、解綁依該名稱重查。"""
    w, _src = await _withdrawn("jia")
    res, _p = await _t(w, f"是{STUDENT_ESTATE}那間", [_out(MODEL_SAID)] * 3,
                       intents=[_intent_raw(REPAIR, pick_id=WF.PICK_ID_NONE, estate_name=STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_ACTION_KEPT in _v(res), _v(res)
    _assert_new_name(w, res)


@pytest.mark.parametrize("state", ["picked", "withdrawn"])
async def test_p4_other_action_only_in_set_name_drops_it(api, state):
    """第 4 點：另一動作＋只有候選集內講法（原講法「宏匯個人」）⇒ ⛔ 換動作、名稱丟棄（`write_candidate_name_kept`）、
    選定（或已撤回）不動、⛔ 解綁。"""
    if state == "picked":
        w, src = await _picked("jia")
        intent = _nn(REPAIR, KEEP, WF.PICK_ID_NONE, "", estate_name="宏匯個人")
    else:
        w, src = await _withdrawn("jia")
        intent = _intent_raw(REPAIR, pick_id=WF.PICK_ID_NONE, estate_name="宏匯個人")
    before = _withdrawn_state(w)
    picked_before = _cands(w)["picked"]
    res, _p = await _t(w, "宏匯個人那間", [_out(MODEL_SAID)] * 3, intents=[intent])
    v = _v(res)
    assert WC.V_CANDIDATE_ACTION_KEPT in v and WC.V_CANDIDATE_NAME_KEPT in v, v
    assert WC.V_CANDIDATE_NAME_NEW not in v
    assert w.draft()["action"] == CC and _withdrawn_state(w) == before
    assert _cands(w)["picked"] == picked_before


async def test_p4_other_action_with_non_name_value_switches(api):
    """第 4 點「另一動作＋非名稱欄值 ⇒ 照換」：名稱＋問題描述 ⇒ 換成修繕草稿、⛔ `write_candidate_action_kept`。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"改報修 {STUDENT_ESTATE} 冷氣不冷", [_out(MODEL_SAID)] * 3,
                       intents=[_nn(REPAIR, KEEP, WF.PICK_ID_NONE, "", estate_name=STUDENT_ESTATE,
                                    description="冷氣不冷")])
    assert WC.V_CANDIDATE_ACTION_KEPT not in _v(res), _v(res)
    assert w.draft()["action"] == REPAIR and w.draft()["fields"].get("description") == "冷氣不冷"


async def test_p4_no_candidate_set_only_name_switches_as_current(api):
    """第 4 點「無候選集時照現行」：草稿（建合約、名稱唯一 ⇒ 沒有候選集），AI 回修繕只帶名稱 ⇒ 照現行換成修繕草稿。"""
    w = _World()
    await _t(w, f"{STUDENT_ESTATE} 這間要簽新租約", [_out(MODEL_SAID)] * 2,
             intents=[_intent(CC, estate_name=STUDENT_ESTATE)])
    assert _cands(w) is None and w.draft()["action"] == CC
    res, _p = await _t(w, f"{STUDENT_ESTATE} 要報修", [_out(MODEL_SAID)] * 3,
                       intents=[_intent(REPAIR, estate_name=STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_ACTION_KEPT not in _v(res), _v(res)
    assert w.draft()["action"] == REPAIR


async def test_p4_control_name_counted_as_value_switches_the_draft(api, monkeypatch):
    """正對照（monkeypatch 版）：「有值」判定把名稱欄也算進去 ⇒ 第一支那一句換成修繕草稿（⛔ `action_kept`）。"""
    def _with_names(intent):
        return any(isinstance(getattr(i, "value", None), str) and i.value.strip()
                   for i in getattr(intent, "fields", None) or [])

    monkeypatch.setattr(runtime_mod, "_intent_has_value", _with_names)
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"啊講錯了，是{STUDENT_ESTATE}那間", [_out(MODEL_SAID)] * 3,
                       intents=[_nn(REPAIR, KEEP, WF.PICK_ID_NONE, "", estate_name=STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_ACTION_KEPT not in _v(res)
    assert w.draft()["action"] == REPAIR


# ════════════════════════════════════════════════════════════════════
# 第 5 點：附候選段的意圖呼叫截斷時重送一次
# ════════════════════════════════════════════════════════════════════
def _same_input(a: dict, b: dict) -> bool:
    return json.dumps(a, ensure_ascii=False, sort_keys=True, default=str) == json.dumps(
        b, ensure_ascii=False, sort_keys=True, default=str)


@pytest.mark.parametrize("first", ["length", "unparsed"])
async def test_p5_first_call_truncated_or_unparsed_retries_once_and_uses_the_retry(api, first):
    """第 5 點：附候選段（已選定）的意圖呼叫第一次 `finish_reason=length`（或內容解析不出）⇒ 同一份輸入重送一次、
    用重送的結果（改選 56907）；記 `write_candidate_intent_retry`。"""
    w, _src = await _picked("jia")
    bad = _truncated() if first == "length" else _intent(raw="抱歉我不確定")
    res, p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[bad, _sw(CC, "56907")])
    assert len(p.intent_calls) == 2
    assert _same_input(p.intent_calls[0], p.intent_calls[1])
    assert WC.V_CANDIDATE_INTENT_RETRY in _v(res), _v(res)
    assert WF.V_UNPARSED not in _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in _v(res) and _cands(w)["picked"] == "56907"


async def test_p5_retry_counts_both_calls_tokens(api):
    """第 5 點（計量照實）：同一回合有重送 vs 沒重送，trace token 恰差第一次（截斷）那次的 usage（7／3）。"""
    w1, _src = await _picked("jia")
    once, p1 = await _t(w1, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_sw(CC, "56907")])
    w2, _src = await _picked("jia")
    twice, p2 = await _t(w2, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_truncated(), _sw(CC, "56907")])
    assert (len(p1.intent_calls), len(p2.intent_calls)) == (1, 2)
    assert twice.trace.prompt_tokens - once.trace.prompt_tokens == 7
    assert twice.trace.completion_tokens - once.trace.completion_tokens == 3


async def test_p5_both_calls_truncated_is_none(api):
    """第 5 點：兩次都截斷 ⇒ 照現行（`None`＋`write_intent_unparsed`）：選定不動、⛔ 第三次呼叫。"""
    w, _src = await _picked("jia")
    res, p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_truncated(), _truncated()])
    assert len(p.intent_calls) == 2
    assert WF.V_UNPARSED in _v(res) and WC.V_CANDIDATE_INTENT_RETRY in _v(res), _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED not in _v(res)
    assert _cands(w)["picked"] == "56906"


async def test_p5_retry_truncated_even_if_parsable_is_none(api):
    """第 5 點（保守讀法，spec question c）：重送那次 `finish_reason=length` 但內容可解析 ⇒ 仍當失敗（`None`）。"""
    w, _src = await _picked("jia")
    second = _sw(CC, "56907")
    second.choices[0].finish_reason = "length"
    res, p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_truncated(), second])
    assert len(p.intent_calls) == 2 and WF.V_UNPARSED in _v(res), _v(res)
    assert _cands(w)["picked"] == "56906"


async def test_p5_without_candidate_section_sends_once(api):
    """第 5 點：未附候選段（沒有候選集）的呼叫 ⇒ 只送一次（截斷但內容可解析 ⇒ 照現行採用）、⛔ 重送標記。"""
    w = _World()
    resp = _intent(CC, estate_name=STUDENT_ESTATE)
    resp.choices[0].finish_reason = "length"
    res, p = await _t(w, f"{STUDENT_ESTATE} 這間要簽新租約", [_out(MODEL_SAID)] * 2, intents=[resp])
    assert len(p.intent_calls) == 1
    assert WC.V_CANDIDATE_INTENT_RETRY not in _v(res), _v(res)
    assert w.draft()["action"] == CC and w.draft()["fields"]["estate_name"] == STUDENT_ESTATE


async def test_p5_without_candidate_section_unparsed_sends_once(api):
    """第 5 點：未附候選段、解析不出 ⇒ 只送一次、照現行 `write_intent_unparsed`。"""
    w = _World()
    trunc = _truncated('{"action": "contract_create", "fie')
    res, p = await _t(w, f"{STUDENT_ESTATE} 這間要簽新租約", [_out(MODEL_SAID)] * 2, intents=[trunc])
    assert len(p.intent_calls) == 1 and WF.V_UNPARSED in _v(res), _v(res)
    assert WC.V_CANDIDATE_INTENT_RETRY not in _v(res)


async def test_p5_retry_past_the_wait_limit_times_out_as_current(api, monkeypatch):
    """第 5 點：重送算在同一個等待上限內；超過 ⇒ 照現行逾時（`write_intent_call_failed`、組 trace 時取消），選定不動。"""
    w, _src = await _picked("jia")
    monkeypatch.setattr(runtime_mod, "WRITE_INTENT_WAIT_MAX_S", 0.05)
    tasks: list = []

    async def _slow(kwargs):
        tasks.append(asyncio.current_task())
        await asyncio.sleep(30)

    res, p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_truncated(), _slow])
    assert len(p.intent_calls) == 2
    v = _v(res)
    assert WF.V_CALL_FAILED in v and WF.V_CALL_CANCELLED in v and WC.V_CANDIDATE_INTENT_RETRY in v, v
    assert _cands(w)["picked"] == "56906"
    await asyncio.sleep(0)
    assert tasks and all(t.done() for t in tasks)


def test_p5_needs_retry_helper():
    """第 5 點判準：截斷或解析不出 ⇒ 重送；可解析、多物件（ambiguous）⇒ ⛔ 重送。"""
    f = runtime_mod._write_intent_needs_retry
    assert f(_truncated()) is True
    assert f(_intent(raw="不是 JSON")) is True
    assert f(object()) is True
    assert f(_intent(CC)) is False
    assert f(_intent(raw='{"action":"repair_create","fields":[]}{"action":"contract_create","fields":[]}')) is False


def test_p5_retried_response_sums_usage():
    first, second = _truncated(), _intent(CC, pt=11, ct=4)
    r = runtime_mod._RetriedIntentResponse(first, second, failed=False)
    assert r.choices is second.choices and r.failed is False
    assert (r.usage.prompt_tokens, r.usage.completion_tokens) == (7 + 11, 3 + 4)
    r2 = runtime_mod._RetriedIntentResponse(first, None, failed=True)
    assert r2.choices is first.choices and r2.failed is True
    assert (r2.usage.prompt_tokens, r2.usage.completion_tokens) == (7, 3)


# ════════════════════════════════════════════════════════════════════
# 第 6 點：同一次改選與改講新名稱（單次決定）
# ════════════════════════════════════════════════════════════════════
async def test_p6_picked_pick_then_name_last_wins_name(api):
    """第 6 點（改寫為最後一項生效）：已選定，指令清單＝`pick` 56907 再 `name`（候選集外、本句講的）⇒ 最後一項生效：
    改講新名稱、解綁重查（⛔ 改選 56907、⛔ 矛盾重列）；只送一次意圖呼叫。"""
    w, _src = await _picked("jia")
    res, p = await _t(w, f"改成 56907，不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("pick", "56907"), ("name", STUDENT_ESTATE))])
    assert len(p.intent_calls) == 1
    assert WC.V_CANDIDATE_REPICK_TYPED not in _v(res)
    _assert_new_name(w, res)


async def test_p6_picked_name_then_pick_last_wins_pick(api):
    """第 6 點（改寫）：指令清單＝`name` 再 `pick` 56907 ⇒ 最後一項生效：改選 56907、⛔ 依名稱重查、⛔ 矛盾重列。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"不是{STUDENT_ESTATE}，是 56907 那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", STUDENT_ESTATE), ("pick", "56907"))])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert WC.V_CANDIDATE_NAME_CONFLICT not in v and _cands(w)["picked"] == "56907"


async def test_p6_picked_sentence_with_id_and_name_command_is_a_new_name(api):
    """第 6 點（改寫；計畫例句「22492 那間，不對，是幸福五館」的同形狀）：句中有編號，但不是整句只打編號 ⇒ 不走
    整句編號優先；AI 回 `name` 指令 ⇒ 改講新名稱、解綁重查。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"56907 那間，不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", STUDENT_ESTATE))])
    _assert_new_name(w, res)


async def test_p6_picked_clear_with_name_field_never_requeries(api):
    """第 6 點（改寫）：`clear` 指令＋名稱欄值（候選集外、本句講的）、沒有 `name` 指令 ⇒ 名稱丟棄
    （`write_candidate_name_kept`）、⛔ 解綁重查；`clear` ⇒ 撤回並重列。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"不是這間，改成{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("clear", ""), estate_name=STUDENT_ESTATE)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == src.ids, res.answer


async def test_p6_picked_name_command_with_refused_pick_before_it_requeries(api, monkeypatch):
    """第 6 點（改寫）：指令清單＝`pick` 40303（會被選對紀錄退回）再 `name` ⇒ 最後一項是 `name`，`pick` 不生效、
    不退回 ⇒ 改講新名稱、解綁重查（⛔ `write_pick_right_indistinct`）。"""
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, f"是有合約那間才對，喔不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "40303"), ("name", STUDENT_ESTATE))])
    assert WC.V_PICK_RIGHT_INDISTINCT not in _v(res), _v(res)
    _assert_new_name(w, res)


async def test_p6_picked_switch_refused_without_new_name_relists(api, monkeypatch):
    """第 6 點（已選定）：`switch` 40303 被退回、無新名稱 ⇒ 重列（已撤回）、⛔ 改選、⛔ 解綁。"""
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "是有合約那間才對", [_out(MODEL_SAID)] * 2, intents=[_nn(CC, SWITCH, "40303", "")])
    v = _v(res)
    assert WC.V_PICK_RIGHT_INDISTINCT in v and WC.V_CANDIDATE_REASK in v, v
    assert WC.V_CANDIDATE_REPICK_TYPED not in v and WC.V_CANDIDATE_NAME_NEW not in v
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == ["40303", "26007"] and _ask(res)


async def test_p6_picked_switch_with_other_action_value_switches_action(api):
    """第 6 點決定 1（已選定）：`switch` 驗過 56907＋另一動作帶非名稱值 ⇒ 照 §11.14 第 3 點換動作（現行）。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, "56907 那間改報修，冷氣不冷", [_out(MODEL_SAID)] * 3,
                       intents=[_nn(REPAIR, SWITCH, "56907", "", description="冷氣不冷")])
    assert WC.V_CANDIDATE_ACTION_KEPT not in _v(res), _v(res)
    assert WC.V_CANDIDATE_NAME_CONFLICT not in _v(res)
    assert w.draft()["action"] == REPAIR


async def test_p6_withdrawn_pick_with_out_of_set_name_conflicts(api):
    """第 6 點（已撤回）：`pick_id` 56907 驗過＋名稱欄候選集外、本句講的 ⇒ 矛盾、重列。"""
    w, src = await _withdrawn("jia")
    before = _withdrawn_state(w)
    res, p = await _t(w, f"56907，不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                      intents=[_intent_raw(CC, pick_id="56907", estate_name=STUDENT_ESTATE)])
    assert len(p.intent_calls) == 1
    _assert_conflict(w, src, res, before)


async def test_p6_withdrawn_pick_refused_with_out_of_set_name_requeries(api, monkeypatch):
    """第 6 點（已撤回）：`pick_id` 40303 被退回（分不出）＋名稱欄候選集外、本句講的 ⇒ 改講新名稱、解綁重查。"""
    w = await _twin_indistinct(monkeypatch)
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    assert WC.is_withdrawn(_cands(w))
    res, _p = await _t(w, f"有合約那間，喔不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id="40303", estate_name=STUDENT_ESTATE)])
    assert WC.V_PICK_RIGHT_INDISTINCT in _v(res), _v(res)
    _assert_new_name(w, res)


async def test_p6_withdrawn_pick_with_in_set_name_repicks(api):
    """第 6 點（已撤回）：`pick_id` 56907 驗過＋名稱欄是候選集內講法（原講法）⇒ 改選 56907、名稱丟棄（現行）。"""
    w, src = await _withdrawn("jia")
    res, _p = await _t(w, "56907 宏匯個人那間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id="56907", estate_name="宏匯個人")])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_CANDIDATE_NAME_KEPT in v, v
    assert WC.V_CANDIDATE_NAME_CONFLICT not in v and WC.V_CANDIDATE_NAME_NEW not in v
    assert _cands(w)["picked"] == "56907"
    res2, _p = await _t(w, src.rest_text, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == "56907"


async def test_p6_deferred_proposal_name_dropped_on_conflict(api):
    """第 6 點（已撤回）：主模型提議（早於意圖取用、暫存的 `deferred_names`）帶候選集外名稱＋同一次矛盾
    （`pick_id` 56907 驗過＋暫存的名稱本身）⇒ 暫存名稱丟棄、⛔ 解綁、⛔ 出卡。（已選定回合見下一支。）"""
    w, src = await _withdrawn("jia")
    intent = _intent_raw(CC, pick_id="56907")
    before = _withdrawn_state(w)
    res, p = await _t(w, f"改成 56907，不對，是{STUDENT_ESTATE} {src.rest_text}",
                      [_proposal(CC, estate_name=STUDENT_ESTATE, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                      intents=[intent], program_first=False)
    assert len(p.intent_calls) == 1
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_CONFLICT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert WC.is_withdrawn(_cands(w)) and _withdrawn_state(w) == before
    assert w.draft()["fields"]["estate_name"] == src.titles["56906"]
    assert res.trace.pending_id is None and _pick_ids(res) == src.ids, res.answer


async def test_p6_picked_deferred_proposal_name_dropped_and_pick_applies(api):
    """第 6 點（已選定，改寫）：主模型提議帶候選集外名稱、意圖回 `pick` 56907 ⇒ 暫存名稱一律丟棄
    （`write_candidate_name_kept`）、⛔ 解綁重查；`pick` 驗過 ⇒ 改選 56907。"""
    w, src = await _picked("jia")
    res, p = await _t(w, f"改成 56907，不對，是{STUDENT_ESTATE} {src.rest_text}",
                      [_proposal(CC, estate_name=STUDENT_ESTATE, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                      intents=[_cmd(CC, ("pick", "56907"))], program_first=False)
    assert len(p.intent_calls) == 1
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_REPICK_TYPED in v, v
    assert WC.V_CANDIDATE_NAME_NEW not in v and WC.V_CANDIDATE_NAME_CONFLICT not in v, v
    assert _card_id(w, res) == "56907"                                   # 提議的其餘欄位已齊 ⇒ 依改選的那筆出卡


async def test_p6_control_refused_target_counts_as_x_conflicts(api, monkeypatch):
    """正對照（monkeypatch 版，(i) 名稱去向改用退回前的目標）：退回判定恆回 `None`（X 一律算驗過）⇒
    「已撤回 X 被退回＋候選集外名稱」那支改判矛盾（⛔ 改講新名稱）。"""
    w = await _twin_indistinct(monkeypatch)
    await _t(w, "剛剛選錯了", [_out(MODEL_SAID)] * 2, intents=[_rt(CC)])
    monkeypatch.setattr(RT, "_write_candidates_refusal", lambda *a, **k: None)
    res, _p = await _t(w, f"有合約那間，喔不對，是{STUDENT_ESTATE}", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id="40303", estate_name=STUDENT_ESTATE)])
    assert WC.V_CANDIDATE_NAME_NEW not in _v(res), _v(res)


# ════════════════════════════════════════════════════════════════════
# 標記常數
# ════════════════════════════════════════════════════════════════════
def test_markers_constants():
    assert WC.V_CANDIDATE_NAME_CONFLICT == "write_candidate_name_conflict"
    assert WC.V_CANDIDATE_INTENT_RETRY == "write_candidate_intent_retry"
    assert {"V_CANDIDATE_NAME_CONFLICT", "V_CANDIDATE_INTENT_RETRY"} <= set(WC.__all__)
    # 選定後回合改指令式：`new_name`／`rechoice` 相關符號已刪，換成 `target` 指令符號。
    assert WF.PICK_TARGET_KEY == "target"
    assert {"PICK_TARGET_KEY", "PICK_TARGET_RULE_TEMPLATE", "intent_pick_target"} <= set(WF.__all__)
    assert not hasattr(WF, "PICK_NEW_NAME_KEY") and not hasattr(WF, "intent_new_name")
    assert WF.intent_pick_target({WF.PICK_TARGET_KEY: [{"op": "pick", "value": "1"}]}) == [
        {"op": "pick", "value": "1"}]
