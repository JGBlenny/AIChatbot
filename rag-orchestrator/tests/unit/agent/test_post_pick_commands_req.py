"""unit：選定後回合改指令式（計畫 `.kiro/specs/agentic-mcp-orchestration/plan-post-pick-commands-20261024.md` §4.2、§4.3；
凍結清單 `acceptance-post-pick-commands-20261024.md` 項目 F1，採 Q1 (a) 版：已撤回回合照第 5 輪原樣）。

F1 子項 ↔ 本檔測試（逐條；正對照＝`test_*_control_*`〔monkeypatch 型〕與收案報告列的「暫改原始碼哪一處 ⇒ 哪一支失敗 ⇒ 已還原」）：
  - (a)  系統句與 schema 逐位比對             → `test_a_*`
  - (b)  各指令效果                           → `test_b_*`
  - (c)  最後一個生效                         → `test_c_*`
  - (d)  整句編號優先與反例                   → `test_d_*`
  - (e)  選對紀錄                             → `test_e_*`
  - (f)  換動作                               → `test_f_*`
  - (g)  名稱鍵丟棄、不整句填入               → `test_g_*`
  - (h)  綁定                                 → `test_h_*`
  - (i)  意圖解析失敗                         → `test_i_*`
  - (j)  trace 只記封閉碼                     → `test_j_*`
  - (k)  刪除檢查、保留清單、spy              → `test_k_*`
  - (l)  第 5 輪第 1、5 點測試照過            → `test_f12_r6_round5_req.py::test_p1_*`、`::test_p5_*`（本檔不重複）
  - (m)  已撤回回合與改前相同                 → `test_m_*`
  - (n1)～(n4) 名稱值一律規則                 → `test_n*_*`
  - (o)  `{picked}` 形狀與保留值              → `test_o_*`
  - (p)  重列出口有一列看不到                 → `test_p_*`

(a) 的比對來源：**fixture 複本，不是 import**——`fixtures/post_pick_cmd_abl_expected.json` 是對照探針
`probe2/probe_abl.py` 的 `build()` 在三個現選定編號（56906、709740、a_B-7）下的輸出複本（探針檔頂層有 `asyncio.run`
與外部 import，無法在單元測試環境載入）；`fixtures/post_pick_cmd_pre_impl_expected.json` 是改動前（pre-impl 備份）
`write_forms.py` 對未選定／無候選集／卡後更正三種輸入的輸出複本。

資料：同 `test_f12_repick_r6_req.py`（真 `JGBSystemAPI`＋mock transport；模型一律假；全部離線）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.agent import runtime as runtime_mod
from services.agent import write_candidates as WC
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_CANDIDATES_KEY

from tests.unit.agent.test_a2a_write_candidates_req import _intent_raw
from tests.unit.agent.test_f12_name_lenient_req import (  # noqa: F401 — autouse 匯入
    _CC_REST, _CC_REST_TEXT, _f12_env, _ids_resp, _pick_ids,
)
from tests.unit.agent.test_f12_r6_round5_req import (
    JIA_IDS, REPAIR, _assert_new_name, _v, _withdrawn,
)
from tests.unit.agent.test_f12_repick_r6_req import (
    CC, DUE, MODEL_SAID, RT, _ask, _assert_cmd_absent, _assert_cmd_offered, _cands, _card_id, _cmd,
    _fill_with_name, _listed, _picked, _proposal, _schema, _seed_full_draft, _t, _tamper_action,
    _tamper_creator, _tamper_fp, _twin_indistinct, _twin_listed, _withdrawn_state,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import STUDENT_ESTATE, _intent, _out

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-post-pick-commands-20261024")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


@pytest.fixture
def closing_handoff_off(monkeypatch):
    """E 片：這類「送出內容與改前逐字相同」的測試釘住 `AGENT_CLOSING_HANDOFF=off`（E 片 on 的行為見 test_closing_handoff_e_req.py）。"""
    monkeypatch.setenv("AGENT_CLOSING_HANDOFF", "off")


FIXTURES = Path(__file__).parent / "fixtures"
ABL = json.loads((FIXTURES / "post_pick_cmd_abl_expected.json").read_text(encoding="utf-8"))
PRE_IMPL = json.loads((FIXTURES / "post_pick_cmd_pre_impl_expected.json").read_text(encoding="utf-8"))
SERVICES = Path(runtime_mod.__file__).resolve().parents[1]           # rag-orchestrator/services

#: 「幸福五館」＝候選集外的名稱（本檔的 `name` 指令例子；`STUDENT_ESTATE` 是 fixture 內唯一、只有 viewer 看得到的物件）。
OUT_NAME = STUDENT_ESTATE


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def _raw_target(action: str, target, *, with_key: bool = True, **fields):
    """自帶（可能壞掉的）`target` 值的假意圖：`__raw__` 讓替身 `_adapt_intent_target` 原樣送、不補 `target`。"""
    obj: dict = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()], "__raw__": 1}
    if with_key:
        obj["target"] = target
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


def _assert_withdrawn_relist(w, src, res, *, invalid: bool | None = None) -> None:
    """撤回並重列同一份 `ids`：已撤回、`write_candidate_retract:typed`、⛔ 改選、⛔ 出卡。"""
    v = _v(res)
    assert WC.V_CANDIDATE_RETRACT_TYPED in v, v
    assert WC.V_CANDIDATE_REPICK_TYPED not in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    if invalid is not None:
        assert (WC.V_CANDIDATE_CMD_INVALID in v) is invalid, v
    assert WC.is_withdrawn(_cands(w)), _cands(w)
    assert _pick_ids(res) == src.ids and res.trace.pending_id is None, res.answer


def _assert_kept(w, src, res) -> None:
    """維持：選定不動、⛔ 改選、⛔ 撤回、⛔ 無效。"""
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED not in v and WC.V_CANDIDATE_RETRACT_TYPED not in v, v
    assert WC.V_CANDIDATE_CMD_INVALID not in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    c = _cands(w)
    assert c is not None and c["picked"] == src.picked and not WC.is_withdrawn(c), c


def _assert_repicked(w, res, target: str) -> None:
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_CANDIDATE_CMD_INVALID not in v, v
    assert _cands(w)["picked"] == target


# ════════════════════════════════════════════════════════════════════
# (a) 系統句與 schema 逐位比對
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("picked", ["56906", "709740", "a_B-7"])
def test_a_selected_turn_equals_probe_abl_build(picked):
    """(a)：已選定回合的系統句＋規則句與 schema 和對照探針 `abl` 變體 `build()`（fixture 複本，⛔ import）逐位相同
    （同輸入：現選定編號；探針的 `build()` 帶 `modifies_submitted`，對應 `enum_labels=True`，即常駐設定）。"""
    fx = ABL[picked]
    assert WF.write_intent_system_prompt(enum_labels=True, target_picked=picked) == fx["system"]
    assert WF.write_intent_response_format(enum_labels=True, target_picked=picked) == fx["response_format"]


@pytest.mark.usefixtures("closing_handoff_off")
async def test_a_selected_turn_call_equals_probe_abl_build(api):
    """(a)：經真實執行路徑送出的已選定回合呼叫（假模型收到的 kwargs）與探針 `abl` 複本逐位相同（現選定 56906）；
    資料段在使用者這句之前（使用者這句仍是最後一則）。"""
    w, src = await _picked("jia")
    _res, p = await _t(w, "嗯", [_out(MODEL_SAID)], intents=[_cmd(CC)])
    (kw,) = p.intent_calls
    _assert_cmd_offered(kw, src.ids, src.picked)
    fx = ABL[src.picked]
    assert kw["messages"][0]["content"] == fx["system"]
    assert kw["response_format"] == fx["response_format"]
    assert kw["messages"][-1]["content"] == "嗯" and kw["messages"][-2]["role"] == "user"


@pytest.mark.parametrize("case", PRE_IMPL["cases"], ids=lambda c: f"{c['label']}-labels{c['enum_labels']}")
def test_a_unselected_variants_equal_pre_impl(case):
    """(a)：未選定（列候選）、無候選集、卡後更正三種輸入的系統句與 schema 與改前逐位相同（fixture 複本）。"""
    rt = case["rechoice_type"]
    assert WF.write_intent_system_prompt(enum_labels=case["enum_labels"], pick_rule=case["pick_rule"],
                                         rechoice_type=rt) == case["system"]
    assert WF.write_intent_response_format(enum_labels=case["enum_labels"], pick_ids=case["pick_ids"],
                                           rechoice_type=rt) == case["response_format"]


@pytest.mark.usefixtures("closing_handoff_off")
async def test_a_unpicked_and_no_candidates_calls_equal_pre_impl(api):
    """(a)：經真實路徑——第一句（無候選集）與列候選後未選定的打字回合，送出的系統句與 schema 與改前複本逐位相同。"""
    w = _World()
    src_text = "宏匯個人那間要簽約"
    _res, p = await _t(w, src_text, intents=[_intent(CC, estate_name="宏匯個人")], lenient=[_ids_resp(JIA_IDS)])
    (kw0,) = p.intent_calls
    none_cases = [c for c in PRE_IMPL["cases"] if c["label"] == "no_candidates"]
    assert any(kw0["messages"][0]["content"] == c["system"] and kw0["response_format"] == c["response_format"]
               for c in none_cases)
    _res, p = await _t(w, "好", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    (kw1,) = p.intent_calls
    ids_cases = [c for c in PRE_IMPL["cases"] if c["label"] == "unpicked_ids"]
    assert any(kw1["messages"][0]["content"] == c["system"] and kw1["response_format"] == c["response_format"]
               for c in ids_cases)


async def test_a_control_rule_sentence_byte_difference_is_detected(monkeypatch):
    """正對照（monkeypatch 版）：規則句模板改一個字 ⇒ 與探針複本的逐位比對不再相同（量尺看得見差一字）。"""
    monkeypatch.setattr(WF, "PICK_TARGET_RULE_TEMPLATE", WF.PICK_TARGET_RULE_TEMPLATE.replace("nth", "nht", 1))
    assert WF.write_intent_system_prompt(enum_labels=False, target_picked="56906") != ABL["56906"]["system"]
    assert WF.write_intent_response_format(enum_labels=False, target_picked="56906") != ABL["56906"]["response_format"]


# ════════════════════════════════════════════════════════════════════
# (b) 各指令效果（候選集 jia：ids＝56907、56906、56905；現選定 56906）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("cmd, effect", [
    ([("pick", "56907")], "repick:56907"),
    ([("pick", "56905")], "repick:56905"),
    ([("pick", "56906")], "keep"),                              # 現選定 ⇒ 維持
    ([("pick", "12345")], "invalid"),                           # 他人／候選集外編號
    ([("pick", "")], "invalid"),
    ([("pick", "56907 ")], "invalid"),
    ([("nth", "1")], "repick:56907"),
    ([("nth", "2")], "keep"),                                   # 第 2 個＝現選定
    ([("nth", "3")], "repick:56905"),
    ([("nth", "0")], "invalid"),
    ([("nth", "4")], "invalid"),                                # 超過畫面列數
    ([("nth", "二")], "invalid"),
    ([("nth", "abc")], "invalid"),
    ([("nth", "1_0")], "invalid"),
    ([("nth", "+2")], "invalid"),
    ([("nth", " 2 ")], "invalid"),
    ([("nth", "２")], "keep"),                                  # 全形「２」NFKC 後＝2（spec question：計畫 §4.3 第 3 點）
    ([("name", "瑞光宏匯B個人")], "keep"),                      # 現選定的正名
    ([("name", "宏匯個人")], "keep"),                           # 原講法
    ([("name", "瑞光宏匯")], "keep"),                           # 同時對到現選定與另兩列 ⇒ 維持
    ([("name", "瑞光宏匯C個人(空租)")], "repick:56907"),        # 只對到另一列的全名且本句講 ⇒ 改選那列（修復輪 1 R1-1）
    ([("clear", "")], "withdraw"),
    ([], "keep"),
])
async def test_b_command_effects(api, cmd, effect):
    """(b)：每種指令值的效果（程式驗證、⛔ 猜）。`name` 的例子句都含該名稱（出自本句）。"""
    w, src = await _picked("jia")
    text = "嗯 " + " ".join(v for op, v in cmd if op == "name")
    res, p = await _t(w, text.strip(), [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, *cmd)])
    assert p.lenient_calls == []
    if effect == "keep":
        _assert_kept(w, src, res)
    elif effect.startswith("repick:"):
        _assert_repicked(w, res, effect.split(":")[1])
    elif effect == "withdraw":
        _assert_withdrawn_relist(w, src, res, invalid=False)
    else:
        _assert_withdrawn_relist(w, src, res, invalid=True)


async def test_b_name_only_matching_another_row_said_repicks_never_the_old_card(api):
    """(b) 修復輪 1 R1-1：`name` 只對到非現選定的一列（講清單內另一筆全名）且名稱是本句講的 ⇒ 改選那列
    （`write_candidate_repick:typed`），補欄位的下一句出的卡是 56907、⛔ 出舊選定 56906 的卡。"""
    w, src = await _picked("jia")
    res, p = await _t(w, "是瑞光宏匯C個人(空租)那間", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", "瑞光宏匯C個人(空租)"))])
    _assert_repicked(w, res, "56907")
    assert WC.V_CANDIDATE_RETRACT_TYPED not in _v(res) and p.lenient_calls == []
    res2, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == src.other_card == "56907"


async def test_b_name_only_matching_another_row_not_said_withdraws(api):
    """(b)：只對到另一列但名稱不是本句講的（AI 依描述猜出的正名）⇒ 撤回重列（⛔ 改選、⛔ 出舊選定的卡）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯，那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", "瑞光宏匯C個人(空租)"))])
    _assert_withdrawn_relist(w, src, res, invalid=False)
    res2, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **src.rest)])
    assert res2.trace.pending_id is None and _pick_ids(res2) == src.ids, res2.answer


async def test_b_name_matching_two_other_rows_withdraws_even_if_said(api, monkeypatch):
    """(b)：對到兩列以上（皆非現選定）⇒ 撤回重列，即使名稱是本句講的（⛔ 由程式挑一筆）。"""
    monkeypatch.setattr(RT, "_write_candidates_name_hits",
                        lambda self, wd, cands, raw: (False, ["56907", "56905"]))
    w, src = await _picked("jia")
    res, _p = await _t(w, "是瑞光某某那間", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("name", "瑞光某某"))])
    _assert_withdrawn_relist(w, src, res, invalid=False)


async def test_b_name_current_plus_another_keeps_even_if_said(api):
    """(b)：同時對到現選定與另一列（本句講的「瑞光宏匯」對到三列）⇒ 維持，先於唯一命中判。"""
    w, src = await _picked("jia")
    res, p = await _t(w, "是瑞光宏匯那間", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("name", "瑞光宏匯"))])
    _assert_kept(w, src, res)
    assert p.lenient_calls == []


async def test_b_name_unique_other_row_amount_mismatch_withdraws(api, monkeypatch):
    """(b)：只對到一列（非現選定）、名稱是本句講的，但金額期間不符（選對紀錄）⇒ 撤回重列（`via="name"` 只免除分不出）。"""
    w = _World()
    keelung = "基隆溫馨一人宅套房"
    await _t(w, f"{keelung} 7月那期 5000元 延後 3 天",
             intents=[_intent(DUE, estate_name=keelung, period="7月那期", days="3", said_amount="5000")])
    c = dict(_cands(w), picked="709740")
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    monkeypatch.setattr(RT, "_write_candidates_name_hits",
                        lambda self, wd, cands, raw: (False, ["709739"]))
    res, _p = await _t(w, "改 24800 那張，是某某那張", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(DUE, ("name", "某某那張"))])
    v = _v(res)
    assert WC.V_PICK_RIGHT_AMOUNT_MISMATCH in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert WC.is_withdrawn(_cands(w)) and res.trace.pending_id is None


async def test_b_name_unique_match_skips_the_indistinct_refusal(api, monkeypatch):
    """(b) `via="name"`：程式依客人原字的名稱唯一對到（不是 AI 依描述猜）⇒ 分不出判定不套，改選成立。
    （畫面除編號外全同的列，標題必同名而對到兩列，故以假「分不出」集合直接驗退回函式的分支。）"""
    monkeypatch.setattr(WC, "pr_indistinct_ids", lambda cand_type, rows: {"56907", "56906", "56905"})
    w, src = await _picked("jia")
    res, _p = await _t(w, "是瑞光宏匯C個人(空租)那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", "瑞光宏匯C個人(空租)"))])
    v = _v(res)
    assert WC.V_PICK_RIGHT_INDISTINCT not in v and WC.V_CANDIDATE_REPICK_TYPED in v, v
    assert _cands(w)["picked"] == "56907"
    # 同一狀態下 `pick` 指令（客人句中沒講出編號）仍被「分不出」退回——假集合確實會擋，上一支的通過不是空轉。
    w2, _src = await _picked("jia")
    res2, _p = await _t(w2, "是 C 個人那間", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "56907"))])
    assert WC.V_PICK_RIGHT_INDISTINCT in _v(res2) and WC.V_CANDIDATE_REPICK_TYPED not in _v(res2)


async def test_b_name_not_in_set_and_said_this_turn_requeries(api):
    """(b)：`name` 都對不到清單且本句講 ⇒ 解綁、依新名稱重查（唯一 ⇒ 卡是 67338）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"不是，是{OUT_NAME}那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", OUT_NAME), **src.rest)])
    _assert_new_name(w, res)


async def test_b_name_not_said_this_turn_is_invalid(api):
    """(b)：`name` 都對不到清單但不是本句講的（從上下文填回）⇒ 無效 ⇒ 撤回重列。"""
    w, src = await _picked("jia")
    res, p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("name", OUT_NAME))])
    _assert_withdrawn_relist(w, src, res, invalid=True)
    assert p.lenient_calls == []


@pytest.mark.parametrize("target", ["字串", {"op": "pick", "value": "56907"}, None],
                         ids=["string", "object", "null"])
async def test_b_target_not_a_list_withdraws(api, target):
    """(b)：`target` 為字串、物件、null ⇒ 無效 ⇒ 撤回重列。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_raw_target(CC, target)])
    _assert_withdrawn_relist(w, src, res, invalid=True)


async def test_b_target_key_missing_withdraws(api):
    """(b)：`target` 缺鍵 ⇒ 無效 ⇒ 撤回重列。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_raw_target(CC, None, with_key=False)])
    _assert_withdrawn_relist(w, src, res, invalid=True)


@pytest.mark.parametrize("item", ["pick", ["pick"], {"op": "pick"}, {"op": 5, "value": "x"},
                                  {"op": "pick", "value": 56907}, {"op": "guess", "value": "56907"}],
                         ids=["str", "list", "no_value", "op_int", "value_int", "op_unknown"])
async def test_b_malformed_item_is_invalid(api, item):
    """(b)：指令項非物件、缺 `value`、`op` 非字串或值域外、`value` 非字串 ⇒ 無效 ⇒ 撤回重列。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_raw_target(CC, [item])])
    _assert_withdrawn_relist(w, src, res, invalid=True)


async def test_b_control_unique_name_withdrawn_instead_of_repick_fails(api, monkeypatch):
    """正對照（monkeypatch 版）：改回「`name` 只對到另一列 ⇒ 撤回重列」（修復輪 1 之前的行為）⇒ (b)「只對到一列且本句講
    ⇒ 改選」那支失敗（撤回重列、沒改選）。"""
    orig = RT._write_candidates_cmd_effect

    def back_to_withdraw(self, wd, cands, user_message, item):
        out = orig(self, wd, cands, user_message, item)
        return ("withdraw",) if out[0] == "target" and out[2] == WF.PICK_TARGET_OP_NAME else out

    monkeypatch.setattr(RT, "_write_candidates_cmd_effect", back_to_withdraw)
    w, src = await _picked("jia")
    res, _p = await _t(w, "是瑞光宏匯C個人(空租)那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", "瑞光宏匯C個人(空租)"))])
    assert WC.V_CANDIDATE_REPICK_TYPED not in _v(res) and WC.is_withdrawn(_cands(w))
    with pytest.raises(AssertionError):
        _assert_repicked(w, res, "56907")


# ════════════════════════════════════════════════════════════════════
# (c) 最後一個生效
# ════════════════════════════════════════════════════════════════════
async def test_c_pick_then_name_requeries_the_name(api):
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"56907，不對，是{OUT_NAME}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "56907"), ("name", OUT_NAME))])
    assert WC.V_CANDIDATE_REPICK_TYPED not in _v(res)
    _assert_new_name(w, res)


async def test_c_name_then_pick_issues_the_picked_one(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, f"不是{OUT_NAME}，是 56907", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", OUT_NAME), ("pick", "56907"))])
    _assert_repicked(w, res, "56907")
    assert WC.V_CANDIDATE_NAME_NEW not in _v(res)
    res2, _p = await _t(w, src.rest_text, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == "56907"


async def test_c_pick_then_clear_withdraws(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, "選 56907，算了不對", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "56907"), ("clear", ""))])
    _assert_withdrawn_relist(w, src, res, invalid=False)


async def test_c_clear_then_pick_picks(api):
    w, _src = await _picked("jia")
    res, _p = await _t(w, "不對，是 56907", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("clear", ""), ("pick", "56907"))])
    _assert_repicked(w, res, "56907")


async def test_c_pick_then_name_only_matching_b_issues_the_card_of_b(api):
    """(c) 修復輪 1：〔pick A, name N〕，N 只對到 B（≠ A、≠現選定）且本句講 ⇒ 最後一個指令生效 ⇒ 改選 B、卡是 B。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "56905，不對，是瑞光宏匯C個人(空租)那間", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "56905"), ("name", "瑞光宏匯C個人(空租)"))])
    _assert_repicked(w, res, "56907")
    res2, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == "56907"


async def test_c_pick_other_then_pick_current_keeps(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, "56907 不對還是原本的", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "56907"), ("pick", src.picked))])
    _assert_kept(w, src, res)


async def test_c_last_item_invalid_withdraws_even_if_earlier_valid(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, "56907 再 99999", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("pick", "56907"), ("pick", "99999"))])
    _assert_withdrawn_relist(w, src, res, invalid=True)


# ════════════════════════════════════════════════════════════════════
# (d) 整句編號優先與反例
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("cmd", [[], [("clear", "")], [("pick", "56905")], [("name", OUT_NAME)]],
                         ids=["empty", "clear", "other_pick", "name"])
async def test_d_whole_sentence_id_wins_over_any_command(api, cmd):
    """(d)：整句只打 `ids` 內編號 56907、草稿值沒變 ⇒ 依該編號改選，不論 AI 回什麼指令。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, *cmd)])
    _assert_repicked(w, res, "56907")


async def test_d_counterexample_number_extracted_as_a_field_never_repicks(api):
    """(d) 反例：意圖把該數字抽成金額等欄位（草稿值有變）⇒ 不走整句編號、不改選（維持）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, rent="56907")])
    _assert_kept(w, src, res)
    assert w.draft()["fields"].get("rent") == "56907"


# ════════════════════════════════════════════════════════════════════
# (e) 選對紀錄（twin：40303、26007 畫面除編號外全同；現選定 26007）
# ════════════════════════════════════════════════════════════════════
async def test_e_pick_indistinct_not_said_withdraws(api, monkeypatch):
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "是有合約那間才對", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "40303"))])
    v = _v(res)
    assert WC.V_PICK_RIGHT_INDISTINCT in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert WC.is_withdrawn(_cands(w)) and _pick_ids(res) == ["40303", "26007"] and _ask(res)


async def test_e_pick_indistinct_said_repicks(api, monkeypatch):
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "我要 40303 那間才對", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "40303"))])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_PICK_RIGHT_INDISTINCT not in v, v
    assert _cands(w)["picked"] == "40303"


async def test_e_nth_indistinct_with_ordinal_repicks(api, monkeypatch):
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "第一個", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("nth", "1"))])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_PICK_RIGHT_INDISTINCT not in v, v
    assert _cands(w)["picked"] == "40303"


async def test_e_nth_indistinct_without_ordinal_withdraws(api, monkeypatch):
    """原話沒有序數（「大的那間」）⇒ AI 把依描述猜的包成序數 ⇒ 同 `pick` 退回、撤回重列。"""
    w = await _twin_indistinct(monkeypatch)
    res, _p = await _t(w, "大的那間", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("nth", "1"))])
    v = _v(res)
    assert WC.V_PICK_RIGHT_INDISTINCT in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert WC.is_withdrawn(_cands(w))


@pytest.mark.parametrize("text", ["最後一個", "第 1 個", "第一筆"])
async def test_e_ordinal_forms_are_recognised(api, monkeypatch, text):
    """序數佐證的幾種講法（「第」接阿拉伯／國字數字、「最後」）。"""
    w = await _twin_indistinct(monkeypatch)
    nth = "2" if "最後" in text else "1"
    res, _p = await _t(w, text, [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("nth", nth))])
    v = _v(res)
    if nth == "2":                                           # 第 2 個＝現選定 26007 ⇒ 維持
        assert WC.V_CANDIDATE_REPICK_TYPED not in v and _cands(w)["picked"] == "26007"
    else:
        assert WC.V_CANDIDATE_REPICK_TYPED in v and _cands(w)["picked"] == "40303", v


@pytest.mark.parametrize("op, value", [("pick", "709739"), ("nth", "2")])
async def test_e_amount_mismatch_withdraws_for_both_ops(api, op, value):
    """金額期間不符一律套：`pick`、`nth` 兩者皆撤回重列（即使句中講出編號／序數）。"""
    from tests.unit.agent.test_step3_write_lifecycle_req import _World as W   # noqa: F401
    w = _World()
    keelung = "基隆溫馨一人宅套房"
    await _t(w, f"{keelung} 7月那期 5000元 延後 3 天",
             intents=[_intent(DUE, estate_name=keelung, period="7月那期", days="3", said_amount="5000")])
    c = dict(_cands(w), picked="709740")
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    ids = c["ids"]
    text = "改 24800 那張，709739 第二個"
    res, _p = await _t(w, text, [_out(MODEL_SAID)] * 2, intents=[_cmd(DUE, (op, value if op == "pick" else str(ids.index("709739") + 1)))])
    v = _v(res)
    assert WC.V_PICK_RIGHT_AMOUNT_MISMATCH in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert WC.is_withdrawn(_cands(w)) and res.trace.pending_id is None


# ════════════════════════════════════════════════════════════════════
# (f) 換動作
# ════════════════════════════════════════════════════════════════════
async def test_f_other_action_with_non_name_value_switches_and_skips_target(api):
    """(f)：另一動作帶非名稱值 ⇒ 換動作、不讀 `target`、trace `write_candidate_cmd_skipped`；新動作草稿的 `estate_name`
    ＝意圖 `fields` 的名稱（照現行值閘）；同時回了 `target` 〔pick 另一筆〕⇒ 不改選、不影響新草稿。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, f"改報修 {OUT_NAME} 冷氣不冷", [_out(MODEL_SAID)] * 3,
                       intents=[_cmd(REPAIR, ("pick", "56907"), estate_name=OUT_NAME, description="冷氣不冷")])
    v = _v(res)
    assert WC.V_CANDIDATE_CMD_SKIPPED in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v), v
    assert w.draft()["action"] == REPAIR
    assert w.draft()["fields"]["estate_name"] == OUT_NAME and w.draft()["fields"]["description"] == "冷氣不冷"


async def test_f_control_name_always_drop_rule_on_switch_loses_the_new_draft_name(api, monkeypatch):
    """正對照（monkeypatch 版）：換動作回合也套名稱值一律規則（不看綁定）⇒ 新草稿的 `estate_name` 被丟（⛔ 照現行值閘）。"""
    orig = RT._write_candidates_name_rule

    def always_drop(self, acc, identity, f, raw, *, defer):
        if getattr(f, "key", None) == "estate_name" and isinstance(raw, str) and raw.strip():
            return "drop"
        return orig(self, acc, identity, f, raw, defer=defer)

    monkeypatch.setattr(RT, "_write_candidates_name_rule", always_drop)
    w, _src = await _picked("jia")
    await _t(w, f"改報修 {OUT_NAME} 冷氣不冷", [_out(MODEL_SAID)] * 3,
             intents=[_cmd(REPAIR, estate_name=OUT_NAME, description="冷氣不冷")])
    assert w.draft()["action"] == REPAIR and "estate_name" not in w.draft()["fields"]


async def test_f_merge_rejected_keeps_old_draft_bound_and_pick(api):
    """(f)：另一動作帶非名稱值但合併被拒（表外鍵：修繕單沒有 `rent`）⇒ 草稿留在舊動作、仍綁定、選定不變；`target` 不讀
    （`write_candidate_cmd_skipped`）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯 租金 5000", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(REPAIR, ("pick", "56907"), rent="5000")])
    v = _v(res)
    assert WF.V_OUT_OF_DOMAIN in v and WC.V_CANDIDATE_CMD_SKIPPED in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert w.draft()["action"] == CC and _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


async def test_f_merge_rejected_with_deferred_out_of_set_name_stays_bound(api):
    """(f) 另一支：換動作且合併被拒，主模型提議候選集外、本句講的名稱 ⇒ 候選集仍綁定、選定不變、記
    `write_candidate_name_kept`、⛔ 依新名稱重查。"""
    w, src = await _picked("jia")
    res, p = await _t(w, f"{OUT_NAME} 冷氣不冷",
                      [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                      intents=[_cmd(REPAIR, rent="5000")], program_first=False)
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _cands(w) is not None and _cands(w)["picked"] == src.picked and w.draft()["action"] == CC
    assert p.lenient_calls == []


async def test_f_merge_rejected_action_not_visible_stays_bound_and_unchanged(api, monkeypatch):
    """(f)：換動作但身分看不到該寫入動作（`_write_draft_specs` 不含 `jgb2.action.<REPAIR>`）⇒ 合併被拒、記
    `write_intent_action_not_visible`；草稿留在舊動作、候選集仍綁定、選定不變；主模型提議的候選集外名稱不重查。"""
    cls = RT
    orig = cls._write_draft_specs

    def no_repair(self, identity):
        specs = orig(self, identity)
        return None if specs is None else [s for s in specs if s.get("name") != f"jgb2.action.{REPAIR}"]

    monkeypatch.setattr(cls, "_write_draft_specs", no_repair)
    w, src = await _picked("jia")
    res, p = await _t(w, f"{OUT_NAME} 報修 冷氣不冷",
                      [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                      intents=[_cmd(REPAIR, estate_name=OUT_NAME, description="冷氣不冷")], program_first=False)
    v = _v(res)
    assert "write_intent_action_not_visible" in v, v
    assert w.draft()["action"] == CC and WC.V_CANDIDATE_NAME_NEW not in v
    assert _cands(w) is not None and _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))
    assert p.lenient_calls == []


async def test_f_control_name_rule_ignoring_binding_rebinds_on_rejected_merge(api, monkeypatch):
    """正對照（monkeypatch 版）：名稱值一律規則改成不套（回 `None`，照現行合併）⇒ 上一支的提議名稱被併入、解綁重查。"""
    monkeypatch.setattr(RT, "_write_candidates_name_rule", lambda *a, **k: None)
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 冷氣不冷",
                       [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                       intents=[_cmd(REPAIR, rent="5000")], program_first=False)
    assert WC.V_CANDIDATE_NAME_KEPT not in _v(res) and (_cands(w) is None or _cands(w)["picked"] != src.picked)


async def test_f_switch_succeeds_deferred_proposal_name_not_written_into_old_draft(api):
    """(f)：換動作成功時，意圖取用前的暫存提議名稱 ⇒ 不寫進舊草稿、不解綁（舊動作草稿留著、候選集仍綁定）。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 報修 冷氣不冷",
                       [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                       intents=[_cmd(REPAIR, estate_name=OUT_NAME, description="冷氣不冷")], program_first=False)
    assert w.draft()["action"] == REPAIR
    assert w.draft()["fields"].get("estate_name") == OUT_NAME
    assert WC.V_CANDIDATE_NAME_NEW not in _v(res)


@pytest.mark.parametrize("fields", [{"estate_name": OUT_NAME}, {}], ids=["name_only", "no_value"])
async def test_f_other_action_without_value_does_not_switch_and_executes_command(api, fields):
    """(f)：另一動作只帶名稱或不帶值 ⇒ 不換、指令照執行、`fields` 名稱丟棄。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"改成 56907 {OUT_NAME}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(REPAIR, ("pick", "56907"), **fields)])
    v = _v(res)
    assert WC.V_CANDIDATE_ACTION_KEPT in v and WC.V_CANDIDATE_CMD_SKIPPED not in v, v
    assert w.draft()["action"] == CC and WC.V_CANDIDATE_NAME_NEW not in v
    _assert_repicked(w, res, "56907")
    if fields:
        assert WC.V_CANDIDATE_NAME_KEPT in v


# ════════════════════════════════════════════════════════════════════
# (g) 名稱鍵、暫存提議名稱丟棄；選定後不整句填入
# ════════════════════════════════════════════════════════════════════
async def test_g_fields_name_key_is_dropped_even_when_said(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, estate_name=OUT_NAME, **src.rest)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _card_id(w, res) == src.picked


async def test_g_deferred_proposal_name_is_dropped(api):
    w, src = await _picked("jia")
    res, _p = await _fill_with_name(w, src, OUT_NAME, where="proposal", said_in_text=True, cmd=[])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _card_id(w, res) == src.picked


async def test_g_no_whole_sentence_fill_after_pick(api):
    """選定後、追問問題描述，客人講的不是描述、AI 沒抽到 ⇒ ⛔ 整句填入（完整案例見第 5 輪第 1 點測試）。"""
    w = _World()
    res, _p = await _t(w, "宏匯個人那間要報修", intents=[_intent(REPAIR, estate_name="宏匯個人")],
                       lenient=[_ids_resp(JIA_IDS)])
    await _t(w, "pick:estate:56906")
    assert w.draft()["asked"] == ["description"]
    res, _p = await _t(w, "欸等一下", [_out(MODEL_SAID)] * 2, intents=[_cmd(REPAIR)])
    assert "description" not in w.draft()["fields"] and res.trace.pending_id is None


# ════════════════════════════════════════════════════════════════════
# (h) 綁定
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("tamper", [_tamper_creator, _tamper_action, _tamper_fp], ids=["user", "action", "name_fp"])
async def test_h_unbound_candidate_set_never_repicks_or_reads_target(api, tamper):
    """(h)：候選集不再綁定本草稿（換使用者、換動作、名稱指紋改變）⇒ 不改選、不讀 `target`。"""
    w, _src = await _picked("jia")
    c = dict(_cands(w))
    tamper(c)
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, _p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "56907"))])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED not in v and not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v), v
    after = _cands(w)
    assert after is None or after.get("picked") != "56907"


# ════════════════════════════════════════════════════════════════════
# (i) 意圖解析失敗
# ════════════════════════════════════════════════════════════════════
async def test_i_parse_failure_whole_sentence_id_still_repicks(api):
    """(i)：意圖解析失敗（含重送後仍失敗）⇒ 與改前同一路徑：整句只打 `ids` 內另一編號仍可改選；不讀 `target`。"""
    w, _src = await _picked("jia")
    res, p = await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_intent(raw="不是 JSON"), _intent(raw="不是 JSON")])
    assert len(p.intent_calls) == 2
    v = _v(res)
    assert WF.V_UNPARSED in v and WC.V_CANDIDATE_REPICK_TYPED in v, v
    assert not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v) and WC.V_CANDIDATE_CMD_INVALID not in v
    assert _cands(w)["picked"] == "56907"


async def test_i_parse_failure_other_sentence_changes_nothing(api):
    w, src = await _picked("jia")
    res, _p = await _t(w, "嗯好", [_out(MODEL_SAID)] * 2, intents=[_intent(raw="不是 JSON"), _intent(raw="不是 JSON")])
    _assert_kept(w, src, res)
    assert not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in _v(res))


# ════════════════════════════════════════════════════════════════════
# (j) trace 只記封閉碼
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("item", [{"op": "幸福五館", "value": "x"}, {"op": "56907", "value": "x"},
                                  {"op": 5, "value": "x"}], ids=["name_as_op", "id_as_op", "non_string_op"])
async def test_j_trace_records_invalid_code_never_the_value(api, item):
    w, _src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_raw_target(CC, [item])])
    v = _v(res)
    assert f"{WC.V_CANDIDATE_CMDS_PREFIX}invalid" in v and f"{WC.V_CANDIDATE_CMD_LAST_PREFIX}invalid" in v, v
    blob = json.dumps(v, ensure_ascii=False)
    assert "幸福五館" not in blob and "56907" not in blob


async def test_j_trace_codes_in_order_and_capped_at_eight(api):
    w, src = await _picked("jia")
    cmd = [("pick", "56907"), ("nth", "1"), ("name", "甲"), ("clear", "")] * 3
    res, _p = await _t(w, "甲", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, *cmd)])
    v = _v(res)
    assert f"{WC.V_CANDIDATE_CMDS_PREFIX}pick,nth,name,clear,pick,nth,name,clear" in v, v
    assert f"{WC.V_CANDIDATE_CMD_LAST_PREFIX}clear" in v


async def test_j_trace_empty_list_is_none(api):
    w, _src = await _picked("jia")
    res, _p = await _t(w, "嗯", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC)])
    v = _v(res)
    assert f"{WC.V_CANDIDATE_CMDS_PREFIX}" in v and f"{WC.V_CANDIDATE_CMD_LAST_PREFIX}none" in v, v


def test_j_marker_constants():
    assert WC.V_CANDIDATE_CMDS_PREFIX == "write_candidate_cmds:"
    assert WC.V_CANDIDATE_CMD_LAST_PREFIX == "write_candidate_cmd_last:"
    assert WC.V_CANDIDATE_CMD_INVALID == "write_candidate_cmd_invalid"
    assert WC.V_CANDIDATE_CMD_SKIPPED == "write_candidate_cmd_skipped"


# ════════════════════════════════════════════════════════════════════
# (k) 刪除檢查、保留清單、spy
# ════════════════════════════════════════════════════════════════════
_DELETE_SET = (r"PICK_NEW_NAME|PICK_RECHOICE|pick_rechoice_rule|intent_new_name|intent_pick_rechoice|"
               r"_write_candidates_new_name|pick_rechoice_offered|intent_rechoice")
_DELETE_SYMBOLS = ["PICK_NEW_NAME", "PICK_RECHOICE", "pick_rechoice_rule", "intent_new_name",
                   "intent_pick_rechoice", "_write_candidates_new_name", "pick_rechoice_offered", "intent_rechoice"]
_KEEP_SYMBOLS = [
    "_write_candidates_post_pick_names", "_write_candidates_typed_post_pick", "_write_candidates_typed_target",
    "_write_candidates_name_is_new", "_write_candidates_typed", "collected_names", "name_collect", "name_conflict",
    "V_CANDIDATE_NAME_CONFLICT", "repick_target", "_write_candidates_repick_target",
    "_write_candidates_deferred_names", "_write_candidates_replay_names", "_write_candidates_apply_name",
    "_write_candidates_withdraw", "_write_candidates_in_set", "_said_id_is_pick_id", "_write_candidates_name_rule",
    "_write_candidates_refusal",
]


def _count(pattern: str) -> int:
    rx = re.compile(pattern)
    return sum(len(rx.findall(p.read_text(encoding="utf-8"))) for p in sorted(SERVICES.rglob("*.py")))


def test_k_delete_set_has_zero_hits_in_services():
    """(k)(a) 版：`grep -rn "<刪除清單>" rag-orchestrator/services/` 0 筆。"""
    assert _count(_DELETE_SET) == 0


@pytest.mark.parametrize("symbol", _DELETE_SYMBOLS)
def test_k_delete_set_pattern_control_each_symbol_hits_when_present(symbol):
    """正對照：刪除檢查的樣式對每個符號都抓得到（在含該符號的文字上命中 ≥1）——樣式沒壞，0 筆才有意義。"""
    assert re.search(_DELETE_SET, f"x = {symbol}_demo(1)") is not None


@pytest.mark.parametrize("symbol", _KEEP_SYMBOLS)
def test_k_keep_list_symbols_exist(symbol):
    """(k)：計畫 §4.3「刪除與保留」保留清單的每個符號各 ≥1 筆。"""
    assert _count(re.escape(symbol)) >= 1, symbol


def _spy_post_pick(monkeypatch) -> dict:
    calls = {"names": 0, "typed_post_pick": 0}
    orig_names = RT._write_candidates_post_pick_names
    orig_typed = RT._write_candidates_typed_post_pick

    async def names(self, *a, **k):
        calls["names"] += 1
        return await orig_names(self, *a, **k)

    def typed(self, *a, **k):
        calls["typed_post_pick"] += 1
        return orig_typed(self, *a, **k)

    monkeypatch.setattr(RT, "_write_candidates_post_pick_names", names)
    monkeypatch.setattr(RT, "_write_candidates_typed_post_pick", typed)
    return calls


@pytest.mark.parametrize("cmd", [[("pick", "56907")], [("name", OUT_NAME)], [("clear", "")], [], [("nth", "9")]],
                         ids=["pick", "name", "clear", "empty", "invalid"])
async def test_k_cmd_turn_never_calls_old_post_pick_functions(api, monkeypatch, cmd):
    """(k) spy：選定後回合、設了 `cmd_offered`、意圖解析成功、沒換動作 ⇒ 兩個舊函式各 0 次。"""
    calls = _spy_post_pick(monkeypatch)
    w, _src = await _picked("jia")
    calls.update(names=0, typed_post_pick=0)
    await _t(w, f"嗯 {OUT_NAME}", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, *cmd)])
    assert calls == {"names": 0, "typed_post_pick": 0}, calls


async def test_k_control_withdrawn_turn_calls_each_at_least_once(api, monkeypatch):
    """正對照：已撤回回合（打字重新選定）⇒ 兩個函式各 ≥1 次（spy 看得見）。"""
    w, _src = await _withdrawn("jia")
    calls = _spy_post_pick(monkeypatch)
    await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id="56907")])
    assert calls["names"] >= 1 and calls["typed_post_pick"] >= 1, calls


async def test_k_control_parse_failure_goes_through_typed_post_pick(api, monkeypatch):
    """正對照：選定後回合意圖解析失敗、整句只打 `ids` 內另一編號 ⇒ 經 `_write_candidates_typed_post_pick` 改選（與 (i) 同）。"""
    w, _src = await _picked("jia")
    calls = _spy_post_pick(monkeypatch)
    await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_intent(raw="不是 JSON"), _intent(raw="不是 JSON")])
    assert calls["typed_post_pick"] >= 1, calls
    assert _cands(w)["picked"] == "56907"


# ════════════════════════════════════════════════════════════════════
# (m) 已撤回回合與改前相同（Q1 (a)）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.usefixtures("closing_handoff_off")
async def test_m_withdrawn_turn_schema_and_prompt_equal_pre_impl(api):
    w, src = await _withdrawn("jia")
    _res, p = await _t(w, "好", [_out(MODEL_SAID)] * 2, intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE)])
    (kw,) = p.intent_calls
    _assert_cmd_absent(kw, src.ids)
    ids_cases = [c for c in PRE_IMPL["cases"] if c["label"] == "unpicked_ids"]
    assert any(kw["messages"][0]["content"] == c["system"] and kw["response_format"] == c["response_format"]
               for c in ids_cases)


async def test_m_withdrawn_turn_ignores_target_and_uses_pick_id(api):
    """已撤回回合：假模型即使回了 `target` 也不讀（舊路徑只看 `pick_id`）。"""
    w, _src = await _withdrawn("jia")
    obj = {"action": CC, "fields": [], "pick_id": "56907",
           WF.PICK_TARGET_KEY: [{"op": "clear", "value": ""}]}
    res, _p = await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_intent(raw=json.dumps(obj))])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v), v
    assert _cands(w)["picked"] == "56907"


async def test_m_withdrawn_out_of_set_said_name_rebinds_and_requeries(api):
    """已撤回回合講候選集外、本句講的名稱 ⇒ 解綁、依新名稱重查（第 5 輪行為不變）。"""
    w, _src = await _withdrawn("jia")
    res, _p = await _t(w, f"是{OUT_NAME}那間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE, estate_name=OUT_NAME)])
    _assert_new_name(w, res)


async def test_m_control_name_rule_scope_back_to_post_pick_start_fails(api, monkeypatch):
    """正對照（monkeypatch 版）：名稱值一律規則的範圍改回 `post_pick_start`（含已撤回回合）⇒ 上一支已撤回改講新名稱
    被丟棄、失敗。"""
    orig = RT._write_draft_begin

    def widened(self, acc, *a, **k):
        out = orig(self, acc, *a, **k)
        if acc.write_draft is not None and acc.write_draft.post_pick_start:
            acc.write_draft.cmd_scope_start = True
        return out

    monkeypatch.setattr(RT, "_write_draft_begin", widened)
    w, _src = await _withdrawn("jia")
    res, _p = await _t(w, f"是{OUT_NAME}那間", [_out(MODEL_SAID)] * 2,
                       intents=[_intent_raw(CC, pick_id=WF.PICK_ID_NONE, estate_name=OUT_NAME)])
    assert WC.V_CANDIDATE_NAME_NEW not in _v(res)


# ════════════════════════════════════════════════════════════════════
# (n1)～(n4) 名稱值一律規則
# ════════════════════════════════════════════════════════════════════
async def test_n1_proposal_after_intent_consumed_drops_the_name(api):
    """(n1)：意圖取用後同回合主模型提議候選集外、本句講的名稱 ⇒ 丟棄、不解綁。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 好",
                       [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                       intents=[_cmd(CC)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _cands(w) is None or _cands(w)["picked"] == src.picked


async def test_n2_parse_failure_proposal_name_is_dropped(api):
    """(n2)：意圖解析失敗、主模型提議同上 ⇒ 丟棄、不解綁。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 好",
                       [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                       intents=[_intent(raw="不是 JSON"), _intent(raw="不是 JSON")])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _cands(w) is None or _cands(w)["picked"] == src.picked


async def test_n2_control_without_the_rule_rebinds(api, monkeypatch):
    """正對照（monkeypatch 版）：拿掉名稱值一律規則（只留第 5 輪判法）⇒ (n2) 的提議名稱解綁重查、該支失敗。"""
    orig = RT._write_candidates_name_rule

    def without_cmd_scope(self, acc, identity, f, raw, *, defer):
        wd = acc.write_draft
        saved, wd.cmd_scope_start = wd.cmd_scope_start, False
        try:
            return orig(self, acc, identity, f, raw, defer=defer)
        finally:
            wd.cmd_scope_start = saved

    monkeypatch.setattr(RT, "_write_candidates_name_rule", without_cmd_scope)
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 好",
                       [_proposal(CC, estate_name=OUT_NAME, **src.rest), _out(MODEL_SAID), _out(MODEL_SAID)],
                       intents=[_intent(raw="不是 JSON"), _intent(raw="不是 JSON")])
    assert WC.V_CANDIDATE_NAME_NEW in _v(res)


async def test_n3_no_candidate_section_never_reads_target(api, monkeypatch):
    """(n3)：候選段附不出（不設 `cmd_offered`）、假模型仍回 `target` ⇒ 不讀、名稱丟棄。"""
    async def _none(self, *a, **k):
        return None

    w, src = await _picked("jia")
    monkeypatch.setattr(RT, "_write_candidates_fetch_rows", _none)
    res, p = await _t(w, f"{OUT_NAME} 好", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", OUT_NAME), estate_name=OUT_NAME)])
    v = _v(res)
    assert all(WF.PICK_TARGET_KEY not in _schema(k)["properties"] for k in p.intent_calls)
    assert not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v) and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert WC.V_CANDIDATE_NAME_KEPT in v
    assert _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


@pytest.fixture
def _rows_unavailable(monkeypatch):
    async def _none(self, *a, **k):
        return None

    monkeypatch.setattr(RT, "_write_candidates_fetch_rows", _none)


async def test_n4_1_other_action_only_name_keeps_bound(api, _rows_unavailable):
    """(n4)(1)：候選段附不出、另一動作只帶名稱、名稱在候選集外且本句講的 ⇒ 仍綁定、選定不變、草稿動作不變、記
    `write_candidate_name_kept`、不記 `write_candidate_name_new`。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 報修", [_out(MODEL_SAID)] * 3, intents=[_cmd(REPAIR, estate_name=OUT_NAME)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert w.draft()["action"] == CC and _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


async def test_n4_1_control_without_cmd_scope_start_in_post_pick_names_rebinds(api, _rows_unavailable, monkeypatch):
    """正對照（monkeypatch 版）：放回第 5 輪被擋名稱的 `ok` 判定（拿掉 `cmd_scope_start` 不收名稱）⇒ 解綁重查、(n4)(1) 失敗。"""
    orig = RT._write_candidates_post_pick_names

    async def old_scope(self, acc, *a, **k):
        wd = acc.write_draft
        saved, wd.cmd_scope_start = wd.cmd_scope_start, False
        try:
            return await orig(self, acc, *a, **k)
        finally:
            wd.cmd_scope_start = saved

    monkeypatch.setattr(RT, "_write_candidates_post_pick_names", old_scope)
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 報修", [_out(MODEL_SAID)] * 3, intents=[_cmd(REPAIR, estate_name=OUT_NAME)])
    assert WC.V_CANDIDATE_NAME_NEW in _v(res)


async def test_n4_2_intent_fields_name_dropped(api, _rows_unavailable):
    """(n4)(2)：同狀態、意圖 `fields` 帶候選集外、本句講的名稱 ⇒ 同 (1)。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"{OUT_NAME} 好", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, estate_name=OUT_NAME)])
    v = _v(res)
    assert WC.V_CANDIDATE_NAME_KEPT in v and WC.V_CANDIDATE_NAME_NEW not in v, v
    assert _cands(w)["picked"] == src.picked and not WC.is_withdrawn(_cands(w))


async def test_n4_3_whole_sentence_id_repicks(api, _rows_unavailable):
    """(n4)(3)：同狀態、整句只打 `ids` 內另一個編號 ⇒ 改選該筆（`write_candidate_repick:typed`）。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, "56907", [_out(MODEL_SAID)] * 2, intents=[_intent("none")])
    assert WC.V_CANDIDATE_REPICK_TYPED in _v(res), _v(res)
    assert _cands(w)["picked"] == "56907"


async def test_n4_4_whole_sentence_id_plus_other_action_name_repicks_without_conflict(api, _rows_unavailable):
    """(n4)(4)：同狀態、整句編號＋另一動作帶候選集外名稱 ⇒ 改選、名稱丟棄、不記 `write_candidate_name_conflict`。"""
    w, _src = await _picked("jia")
    res, _p = await _t(w, "56907", [_out(MODEL_SAID)] * 3, intents=[_cmd(REPAIR, estate_name=OUT_NAME)])
    v = _v(res)
    assert WC.V_CANDIDATE_REPICK_TYPED in v and WC.V_CANDIDATE_NAME_CONFLICT not in v, v
    assert WC.V_CANDIDATE_NAME_NEW not in v and _cands(w)["picked"] == "56907"


# ════════════════════════════════════════════════════════════════════
# (o) `{picked}` 形狀與保留值
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("bad", [WF.PICK_ID_NONE, *WF.PICK_TARGET_OP_DOMAIN, "", "a b", "x" * 33, "中文", None, 5])
def test_o_rule_sentence_refuses_bad_or_reserved_picked(bad):
    assert WF.pick_target_rule(bad) is None
    assert WF.write_intent_call_schema(target_picked=bad) == WF.write_intent_call_schema()


@pytest.mark.parametrize("good", ["56906", "a_B-7", "x" * 32])
def test_o_rule_sentence_accepts_good_picked(good):
    rule = WF.pick_target_rule(good)
    assert rule is not None and f"編號 {good}" in rule


async def test_o_bad_picked_shape_attaches_no_candidate_section(api, monkeypatch):
    """(o)：`{picked}` 形狀不合 ⇒ 不附候選段、schema 無 `target`／`pick_id`、不讀 `target`（fail-closed）。"""
    monkeypatch.setattr(WF, "pick_target_rule", lambda picked: None)
    w, src = await _picked("jia")
    res, p = await _t(w, "改成 56907", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "56907"))])
    (kw,) = p.intent_calls
    props = _schema(kw)["properties"]
    assert WF.PICK_TARGET_KEY not in props and WF.PICK_ID_KEY not in props
    assert all("標示為資料" not in str(m.get("content")) for m in kw["messages"][1:-1])
    v = _v(res)
    assert not any(x.startswith(WC.V_CANDIDATE_CMDS_PREFIX) for x in v) and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    assert _cands(w)["picked"] == src.picked


def test_o_reserved_ids_definition():
    assert WC.RESERVED_IDS == frozenset({WF.PICK_ID_NONE}) | frozenset(WF.PICK_TARGET_OP_DOMAIN)
    assert WF.PICK_TARGET_OP_DOMAIN == ("pick", "nth", "name", "clear")


@pytest.mark.parametrize("reserved", [WF.PICK_ID_NONE, *WF.PICK_TARGET_OP_DOMAIN])
def test_o_candidate_set_with_reserved_id_is_refused_on_load(reserved):
    """(o)：讀回的候選集 `ids` 含保留值 ⇒ `load_write_candidates` 拒收；`RESERVED_IDS`＝`PICK_ID_NONE` ∪ `PICK_TARGET_OP_DOMAIN`。"""
    from tests.unit.agent.test_f12_repick_r6_req import _base_set
    good = _base_set()
    assert WC.load_write_candidates(good)[0] == good
    bad = _base_set(ids=[*good["ids"][:-1], reserved])
    assert WC.load_write_candidates(bad)[0] is None


def test_o_control_reserved_ids_without_pick_accepts_pick(monkeypatch):
    """正對照（monkeypatch 版）：從 `RESERVED_IDS` 拿掉 `pick` ⇒ 含 `pick` 的候選集被接受（上一支的 `pick` 那格失敗）。"""
    monkeypatch.setattr(WC, "RESERVED_IDS", frozenset(WC.RESERVED_IDS) - {"pick"})
    from tests.unit.agent.test_f12_repick_r6_req import _base_set
    good = _base_set()
    bad = _base_set(ids=[*good["ids"][:-1], "pick"])
    assert WC.load_write_candidates(bad)[0] is not None


# ════════════════════════════════════════════════════════════════════
# (p) 重列出口：有一列本回合看不到
# ════════════════════════════════════════════════════════════════════
async def _picked_with_unseen_row(monkeypatch):
    """已選定 56906；本回合取列少一筆（56905 看不到）：附上的編號＝56907、56906。"""
    w, src = await _picked("jia")
    orig = RT._write_candidates_fetch_rows

    async def minus_one(self, *a, **k):
        rows = await orig(self, *a, **k)
        return [r for r in rows if str(r.get("id")) != "56905"] if rows else rows

    monkeypatch.setattr(RT, "_write_candidates_fetch_rows", minus_one)
    return w, src


async def test_p_nth_with_unseen_row_is_invalid_and_relist_equals_clear_relist(api, monkeypatch):
    """(p)：有一列本回合看不到時，`nth` ⇒ 無效（畫面清單有列取不到）⇒ 撤回重列；重列畫面文字與按鈕與 `clear` 撤回
    重列（同一個出口、同一狀態）逐位相同；只列本回合看得到的列（依 `ids` 順序）。"""
    w1, src = await _picked_with_unseen_row(monkeypatch)
    res1, _p = await _t(w1, "第一個", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("nth", "1"))])
    v = _v(res1)
    assert WC.V_CANDIDATE_CMD_INVALID in v and WC.V_CANDIDATE_REPICK_TYPED not in v, v
    w2, _src = await _picked_with_unseen_row(monkeypatch)
    res2, _p = await _t(w2, "第一個", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("clear", ""))])
    assert _pick_ids(res1) == ["56907", "56906"] == _pick_ids(res2)
    assert res1.answer == res2.answer and res1.quick_replies == res2.quick_replies


async def test_p_pick_of_the_unseen_row_is_invalid(api, monkeypatch):
    """`pick` 看不到的那一列（不在本回合附上的編號內）⇒ 無效。"""
    w, src = await _picked_with_unseen_row(monkeypatch)
    res, _p = await _t(w, "改成 56905", [_out(MODEL_SAID)] * 2, intents=[_cmd(CC, ("pick", "56905"))])
    _assert_withdrawn_relist_visible = _v(res)
    assert WC.V_CANDIDATE_CMD_INVALID in _assert_withdrawn_relist_visible
    assert WC.is_withdrawn(_cands(w))


# ════════════════════════════════════════════════════════════════════
# (q) 解綁前查找（修復輪 1 R1-2；計畫 §8.2 第 2 點；C-10）
#   jia（型別 estate）：ids＝56907、56906、56905，現選定 56906；`Q_NAME`＝清單內都對不到（不是任一列正名的子字串、
#   不是原講法「宏匯個人」的子字串）、精確查找 `none` 的名稱 ⇒ 寬鬆比對（假模型回 `_ids_resp`）。
# ════════════════════════════════════════════════════════════════════
Q_NAME = "瑞光宏匯個人"
#: 清單外的另一個物件名稱（錯字、只講一半）：精確查找 `none`、寬鬆比對落在 67652／67649，不含 jia 的現選定 56906。
Q_OTHER = "基隆溫心一人宅"
MB = "manual_bill_create"


def _precheck_marks(res) -> list:
    return [m for m in _v(res) if m.startswith("write_candidate_name_precheck")]


def _spy_lookups(monkeypatch, *, estate=None, contract=None):
    """精確查找替身：`estate`／`contract`＝`{名稱: (status, 列們)}`（只攔這些名稱，其餘走原函式）；回每次呼叫的紀錄
    `[(種類, 名稱)]`。同時攔 `name_precheck_ids` 的呼叫次數（`calls["precheck"]`）。"""
    from services.agent.tools import confirm as C
    calls: dict = {"lookups": [], "precheck": 0}
    orig_e, orig_c, orig_p = C._resolve_estate_rows, C._resolve_contract_rows, runtime_mod.name_precheck_ids

    async def fake_estate(api_, role_id, user_id, ref):
        calls["lookups"].append(("estate", ref.strip()))
        if estate and ref.strip() in estate:
            status, rows = estate[ref.strip()]
            return status, (rows[0] if status == "one" else None), list(rows)
        return await orig_e(api_, role_id, user_id, ref)

    async def fake_contract(api_, role_id, user_id, ref):
        calls["lookups"].append(("contract", ref.strip()))
        if contract and ref.strip() in contract:
            status, rows = contract[ref.strip()]
            return status, (rows[0] if status == "one" else None), list(rows), False
        return await orig_c(api_, role_id, user_id, ref)

    async def spy_precheck(*a, **k):
        calls["precheck"] += 1
        return await orig_p(*a, **k)

    monkeypatch.setattr(C, "_resolve_estate_rows", fake_estate)
    monkeypatch.setattr(C, "_resolve_contract_rows", fake_contract)
    monkeypatch.setattr(runtime_mod, "name_precheck_ids", spy_precheck)
    return calls


def test_q_marker_constants():
    assert WC.V_CANDIDATE_NAME_PRECHECK_KEEP == "write_candidate_name_precheck:keep"
    assert WC.V_CANDIDATE_NAME_PRECHECK_MISS == "write_candidate_name_precheck:miss"


async def test_q1_estate_lenient_hit_containing_picked_keeps_pick_and_restores_name(api):
    """(q1) 型別 estate、名稱清單內都對不到且本句講、精確查找 `none`、寬鬆回含現選定的多列 ⇒ 選定不變、候選集不變、名稱欄＝
    改前值、本回合非名稱欄照合併、記 `precheck:keep`、不記 `name_new`、不重列；本回合寬鬆模型呼叫 1 次。"""
    w, src = await _picked("jia")
    before_cands, before_name = dict(_cands(w)), w.draft()["fields"]["estate_name"]
    assert before_name == "瑞光宏匯B個人"
    res, p = await _t(w, f"不對，是{Q_NAME}那間，租金 12000", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", Q_NAME), rent="12000")],
                      lenient=[_ids_resp(["56906", "56905"])])
    v = _v(res)
    assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_KEEP], v
    assert WC.V_CANDIDATE_NAME_NEW not in v and WC.V_CANDIDATE_RETRACT_TYPED not in v, v
    assert _cands(w) == before_cands and _cands(w)["picked"] == "56906"
    assert w.draft()["fields"]["estate_name"] == before_name
    assert w.draft()["fields"]["rent"] == "12000"                                     # 本回合非名稱欄照合併
    assert len(p.lenient_calls) == 1 and res.trace.llm_calls >= 1
    assert res.trace.pending_id is None and _ask(res)                                 # 不重列（沒有候選清單）、其餘欄位仍缺
    res2, _p = await _t(w, src.rest_text, [_out(MODEL_SAID)] * 2, intents=[_intent(CC, **src.rest)])
    assert _card_id(w, res2) == "56906"                                               # 維持選定 ⇒ 補齊即出選定那筆的卡


async def test_q1_control_without_precheck_unbinds_and_requeries(api, monkeypatch):
    """正對照（monkeypatch 版）：拿掉前置查找 ⇒ 解綁重查（q1 那支失敗的樣子：記 `name_new`、候選集清掉）。"""
    async def never(self, acc, identity, agent_state, cands):
        return False

    monkeypatch.setattr(RT, "_write_candidates_name_precheck", never)
    w, src = await _picked("jia")
    res, _p = await _t(w, f"不對，是{Q_NAME}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", Q_NAME), **src.rest)],
                       lenient=[_ids_resp(["56906", "56905"])])
    assert WC.V_CANDIDATE_NAME_NEW in _v(res) and w.draft()["fields"]["estate_name"] == Q_NAME


async def test_q2_lenient_miss_unbinds_and_requery_reuses_the_same_lenient_result(api):
    """(q2) 同 q1 但寬鬆回不含現選定 ⇒ `precheck:miss`、解綁重查，重查列出的候選＝前置查找那份（56907 一筆）、本回合寬鬆模型
    呼叫＝1（前置查找與重查共用 `run_once` 同一把鍵）。"""
    w, src = await _picked("jia")
    res, p = await _t(w, f"不對，是{Q_OTHER}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", Q_OTHER), **src.rest)],
                      lenient=[_ids_resp(["67652"])])
    v = _v(res)
    assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_MISS], v
    assert WC.V_CANDIDATE_NAME_NEW in v, v
    assert len(p.lenient_calls) == 1 and res.trace.llm_calls == 1, (len(p.lenient_calls), res.trace.llm_calls)
    assert _pick_ids(res)[0] == "67652" and "56906" not in _pick_ids(res), res.answer
    assert _cands(w)["ids"] == _pick_ids(res) and _cands(w)["picked"] is None


@pytest.mark.parametrize("status, rows, expect", [
    ("one", [{"id": "56906", "title": "瑞光宏匯B個人"}], "keep"),
    ("one", [{"id": "56907", "title": "瑞光宏匯C個人(空租)"}], "miss"),
    ("many", [{"id": "56905", "title": "瑞光宏匯A法人"}, {"id": "56906", "title": "瑞光宏匯B個人"}], "keep"),
    ("many", [{"id": "56905", "title": "瑞光宏匯A法人"}, {"id": "56907", "title": "瑞光宏匯C個人(空租)"}], "miss"),
], ids=["one_is_picked", "one_is_other", "many_has_picked", "many_without_picked"])
async def test_q3_exact_lookup_one_or_many(api, monkeypatch, status, rows, expect):
    """(q3) 精確查找 `one` 且＝現選定 ⇒ 維持；`one` 且≠現選定 ⇒ 解綁重查；`many` 含現選定 ⇒ 維持。精確查找命中時不叫寬鬆模型。"""
    calls = _spy_lookups(monkeypatch, estate={Q_NAME: (status, rows)})
    w, src = await _picked("jia")
    res, p = await _t(w, f"不對，是{Q_NAME}那間，租金 12000", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", Q_NAME), rent="12000")])
    v = _v(res)
    want = WC.V_CANDIDATE_NAME_PRECHECK_KEEP if expect == "keep" else WC.V_CANDIDATE_NAME_PRECHECK_MISS
    assert _precheck_marks(res) == [want], v
    assert calls["precheck"] == 1
    if expect == "keep":
        assert WC.V_CANDIDATE_NAME_NEW not in v and _cands(w)["picked"] == "56906"
        assert w.draft()["fields"]["estate_name"] == "瑞光宏匯B個人" and p.lenient_calls == []
    else:
        assert WC.V_CANDIDATE_NAME_NEW in v


async def _bill_picked(monkeypatch=None):
    """帳單候選集（延期繳費，物件範圍 67652；ids＝709740、709739）已選定 709740 的狀態。"""
    w = _World()
    keelung = "基隆溫馨一人宅套房"
    await _t(w, f"{keelung} 7月那期 延後 3 天",
             intents=[_intent(DUE, estate_name=keelung, period="7月那期", days="3")])
    c = dict(_cands(w), picked="709740")
    assert c["type"] == "bill" and c.get(WC.SCOPE_ESTATE_KEY) == "67652", c
    assert WC.load_write_candidates(c)[0] == c
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    return w


@pytest.mark.parametrize("estate_id, expect", [("67652", "keep"), ("99999", "miss")], ids=["scope_estate", "other_estate"])
async def test_q4_bill_compares_the_scope_estate(api, monkeypatch, estate_id, expect):
    """(q4) 型別 bill：精確物件查找含選定物件（帳單候選的物件範圍）⇒ 維持；不含 ⇒ 解綁。"""
    calls = _spy_lookups(monkeypatch, estate={"某某新社區": ("many", [
        {"id": estate_id, "title": "某某新社區A"}, {"id": "88888", "title": "某某新社區B"}])})
    w = await _bill_picked()
    before = dict(_cands(w))
    res, _p = await _t(w, "不是，是某某新社區", [_out(MODEL_SAID)] * 2, intents=[_cmd(DUE, ("name", "某某新社區"))])
    v = _v(res)
    assert calls["precheck"] == 1 and ("estate", "某某新社區") in calls["lookups"]
    if expect == "keep":
        assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_KEEP], v
        assert _cands(w) == before and w.draft()["fields"]["estate_name"] == "基隆溫馨一人宅套房"
        assert WC.V_CANDIDATE_NAME_NEW not in v
    else:
        assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_MISS], v
        assert WC.V_CANDIDATE_NAME_NEW in v


async def _manual_bill_contract_picked():
    """手開帳單、物件一物件多份有效合約（型別 contract、欄 `estate_name`；ids＝89296、88247、84972）已選定 89296。"""
    text, fields, _ctype, _key, _ids = __import__(
        "tests.unit.agent.test_a2a_write_candidates_req", fromlist=["SHAPES"]).SHAPES["estate_many_valid_contracts"]
    w = _World()
    await _t(w, text, intents=[_intent(MB, **{k: v for k, v in fields.items() if k != "action"})])
    c = dict(_cands(w), picked="89296")
    assert c["type"] == "contract" and c["field"] == "estate_name", c
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    return w


async def test_q5_manual_bill_estate_name_compares_the_estate_of_the_picked_contract(api, monkeypatch):
    """(q5) 手開帳單 `estate_name` 型別 contract：精確物件查找含選定合約所屬物件（`offered_rows` 的 `estate_id`）⇒ 維持；
    `offered_rows` 沒有該列的 `estate_id` ⇒ 不比對（precheck 0 次出向）、照舊解綁。"""
    calls = _spy_lookups(monkeypatch, estate={"某某新社區": ("many", [
        {"id": "67652", "title": "某某新社區A"}, {"id": "88888", "title": "某某新社區B"}])})
    w = await _manual_bill_contract_picked()
    before = dict(_cands(w))
    res, _p = await _t(w, "不是，是某某新社區", [_out(MODEL_SAID)] * 2, intents=[_cmd(MB, ("name", "某某新社區"))])
    assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_KEEP], _v(res)
    assert _cands(w) == before and WC.V_CANDIDATE_NAME_NEW not in _v(res)
    # 取不到 `estate_id`：投影拿掉該鍵 ⇒ 不比對
    calls2 = _spy_lookups(monkeypatch, estate={"某某新社區": ("many", [
        {"id": "67652", "title": "某某新社區A"}, {"id": "88888", "title": "某某新社區B"}])})
    orig_min = WC.minimize_row
    monkeypatch.setattr(WC, "minimize_row",
                        lambda t, r: {k: v for k, v in orig_min(t, r).items() if k != "estate_id"})
    w2 = await _manual_bill_contract_picked()
    res2, _p = await _t(w2, "不是，是某某新社區", [_out(MODEL_SAID)] * 2, intents=[_cmd(MB, ("name", "某某新社區"))])
    assert _precheck_marks(res2) == [WC.V_CANDIDATE_NAME_PRECHECK_MISS], _v(res2)
    assert calls2["precheck"] == 0 and WC.V_CANDIDATE_NAME_NEW in _v(res2)     # 沒比對編號 ⇒ 連前置查找都不叫


@pytest.mark.parametrize("how", ["error", "exception"])
async def test_q6_lookup_failure_falls_back_to_the_current_unbind(api, monkeypatch, how):
    """(q6) 前置查找 `error`／丟例外 ⇒ 不比對、記 `precheck:miss`、照舊解綁重查（與改前同；重查那次走原查找）。"""
    from services.agent.tools import confirm as C
    orig = C._resolve_estate_rows
    seen: list = []

    async def flaky(api_, role_id, user_id, ref):
        seen.append(ref.strip())
        if ref.strip() == Q_OTHER and len(seen) == 1:
            if how == "exception":
                raise RuntimeError("boom")
            return "error", None, []
        return await orig(api_, role_id, user_id, ref)

    monkeypatch.setattr(C, "_resolve_estate_rows", flaky)
    w, src = await _picked("jia")
    seen.clear()                                                              # 只數本回合的精確查找
    res, p = await _t(w, f"不對，是{Q_OTHER}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                      intents=[_cmd(CC, ("name", Q_OTHER), **src.rest)], lenient=[_ids_resp(["67652"])])
    v = _v(res)
    assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_MISS], v
    assert WC.V_CANDIDATE_NAME_NEW in v and WC.V_CANDIDATE_NAME_PRECHECK_KEEP not in v
    assert seen[:2] == [Q_OTHER, Q_OTHER] and len(p.lenient_calls) == 1       # 前置 1 次＋重查 1 次精確查找；寬鬆仍 ≤1


async def test_q7_contract_ref_compares_the_picked_contract(api, monkeypatch):
    """(q7) 型別 contract、欄 `contract_ref`：合約查找含現選定 ⇒ 維持。"""
    _spy_lookups(monkeypatch, contract={"某某新合約": ("many", [
        {"id": "990102", "title": "合成展示合約 乙"}, {"id": "990101", "title": "合成展示合約 甲"}])})
    from tests.unit.agent.test_a2a_write_candidates_req import SHAPES
    text, fields, _ctype, _key, _ids = SHAPES["contract_ref_many"]
    w = _World()
    await _t(w, text, intents=[_intent(MB, **{k: v for k, v in fields.items() if k != "action"})])
    c = dict(_cands(w), picked="990102")
    assert c["type"] == "contract" and c["field"] == "contract_ref", c
    w.state["agent"][WRITE_CANDIDATES_KEY] = c
    res, _p = await _t(w, "不是，是某某新合約", [_out(MODEL_SAID)] * 2, intents=[_cmd(MB, ("name", "某某新合約"))])
    assert _precheck_marks(res) == [WC.V_CANDIDATE_NAME_PRECHECK_KEEP], _v(res)
    assert _cands(w) == c and WC.V_CANDIDATE_NAME_NEW not in _v(res)
    # 不含現選定 ⇒ 解綁
    _spy_lookups(monkeypatch, contract={"某某新合約": ("many", [
        {"id": "990101", "title": "合成展示合約丙"}, {"id": "990103", "title": "合成展示合約丁"}])})
    w2 = _World()
    await _t(w2, text, intents=[_intent(MB, **{k: v for k, v in fields.items() if k != "action"})])
    w2.state["agent"][WRITE_CANDIDATES_KEY] = dict(_cands(w2), picked="990102")
    res2, _p = await _t(w2, "不是，是某某新合約", [_out(MODEL_SAID)] * 2, intents=[_cmd(MB, ("name", "某某新合約"))])
    assert _precheck_marks(res2) == [WC.V_CANDIDATE_NAME_PRECHECK_MISS], _v(res2)


async def test_q8_precheck_trace_records_closed_codes_only(api):
    """(q8) `violations` 只含封閉碼：前置查找只記 `precheck:keep`／`:miss`，整個 trace 不含名稱或候選編號作為內容。"""
    w, src = await _picked("jia")
    res, _p = await _t(w, f"不對，是{Q_NAME}那間 {src.rest_text}", [_out(MODEL_SAID)] * 2,
                       intents=[_cmd(CC, ("name", Q_NAME), **src.rest)], lenient=[_ids_resp(["56906", "56905"])])
    v = _v(res)
    assert set(_precheck_marks(res)) <= {WC.V_CANDIDATE_NAME_PRECHECK_KEEP, WC.V_CANDIDATE_NAME_PRECHECK_MISS}
    assert not [m for m in v if Q_NAME in m or "56906" in m or "56905" in m or "56907" in m], v


async def test_q_identity_gate_failure_means_zero_outbound_calls(api, monkeypatch):
    """身分閘不過 ⇒ `name_precheck_ids` 0 次出向（精確查找、寬鬆比對都不叫）、回 `None`（不比對）。"""
    from services.agent.tools import confirm as C
    calls = _spy_lookups(monkeypatch)
    monkeypatch.setattr(C, "_name_lenient_identity_ok", lambda identity: (False, None, None))
    ids = await C.name_precheck_ids(None, CC, {"action": CC}, field="estate_name", cand_type="estate",
                                    name=Q_NAME, missing_label="物件", name_lenient=None)
    assert ids is None and calls["lookups"] == []
    monkeypatch.setattr(C, "_name_lenient_identity_ok", lambda identity: (True, "20151", "12291"))
    ids = await C.name_precheck_ids(None, CC, {"action": CC}, field="estate_name", cand_type="estate",
                                    name="", missing_label="物件", name_lenient=None)
    assert ids is None and calls["lookups"] == []                             # 空名稱 ⇒ 不查
