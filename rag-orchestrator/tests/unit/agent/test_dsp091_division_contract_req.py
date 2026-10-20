"""unit：DSP-091 分工防偏離片（DG）——分工契約測試。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-division-guard-20261020.md` §4.1 DG-1～DG-5；
凍結驗收 `acceptance-division-guard-20261020.md` 的 V1（DG-R1）、V2（DG-R2）、V3（DG-R3）。

四組測試：
  (a) 必過契約 `test_c*`：DSP-091 分工表「程式」列中已接手的環節，現行程式必須全過；
  (b) 現況探針 `test_kd*_probe`：斷言「仍由模型主導」的偏離還在。偏離被修掉時探針失敗——
      **不是**壞掉，是要人手動「移出登記、改寫成必過契約、更新目標正本 §3.1 清單與程式註解」；
  (c) 登記完整 `test_registry_*`：分工表 R1～R6 每列都對得到必過測試或 KD；
  (d) 靜態 `test_static_*`／`test_reason_*`；
  (e) V3 `test_v3_*`：六種情境各出現正確的 `confirm_source:` 標記、每次執行恰一筆。
登記資料在 `dsp091_known_deviations.py`（與目標正本 §3.1 一致，不變量 45 核對）。
裝置沿用 `test_aplus_card_program_only_req.py`（`_World`、`_turn_p`、`_proposal` 等）。
"""
from __future__ import annotations

import ast
import itertools
import json
import re
from pathlib import Path

import pytest

from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.agent_session import SELECT_SCOPE_KEY, WRITE_CANDIDATES_KEY
from services.agent.budget import Budget
from services.agent.output_schema import AgentOutput
from services.agent.runtime import (
    CONFIRM_SOURCE_PREFIX, WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY, AgentRuntime,
)
from services.agent.tools import confirm as C

from tests.unit.agent import dsp091_known_deviations as REG
from tests.unit.agent.test_aplus_card_program_only_req import (  # noqa: F401 — fixture／helper 匯入
    ACTIONS, GOOD, PROPOSAL_ENV, SPECIAL_SAID, _nested, _proposal, _runtime_functions, _seed_draft,
    _sent_payload, _text_key, _turn_p, _with_carry, _with_select_scope,
)
from tests.unit.agent.test_assistant_documents_photos_req import (  # noqa: F401
    _RealConfirmRegistry, _pm, _receipt_doc, _rt,
)
from tests.unit.agent.test_s3_live_fixes_req import _FULL_TYPED, _deed
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, VerifierVerdict, _final_response,
)
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    REPAIR_TEXT, _env, _RouteVerifier, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    KEELUNG_ESTATE, STUDENT_ESTATE, _call, _intent, _out, _Provider,
)

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-division-guard")]

RUNTIME_PATH = Path(runtime_mod.__file__)
AGENT_DIR = RUNTIME_PATH.parent
THIS_FILE = Path(__file__)
KD_BY_ID = {kd["id"]: kd for kd in REG.KNOWN_DEVIATIONS}
KD_HINT = ("{kd} 已不成立：移出登記（dsp091_known_deviations.py）、改寫成必過契約、"
           "更新目標正本 §3.1 清單與程式註解")


def _sources(w: _World, res) -> list:
    return [v for v in res.trace.violations if v.startswith(CONFIRM_SOURCE_PREFIX)]


def _exactly_one_per_execution(w: _World, res) -> str:
    """V3：registry 的 `confirm.request` 執行次數＝`confirm_source:` 標記數，且恰一次。"""
    marks = _sources(w, res)
    assert len(w.reg.confirm_calls()) == 1, w.reg.confirm_calls()
    assert len(marks) == 1, marks
    return marks[0][len(CONFIRM_SOURCE_PREFIX):]


# ════════════════════════════════════════════════════════════════════
# (a) 必過契約
# ════════════════════════════════════════════════════════════════════
def _c1_payload(shape: str, action: str) -> dict:
    text, good = GOOD[action]
    bad_key = next(iter(good))
    if shape == "valued_with_bad":
        return {"action": action, **good, bad_key: "完全沒說過的字" if isinstance(good[bad_key], str) else 98765}
    if shape == "valued":
        return {"action": action, **good}
    if shape == "nested":
        return _nested(action, {"action": action, **good})
    if shape == "nested_str":
        return _nested(action, {"action": action, **good}, as_str=True)
    if shape == "other_action":
        other = next(a for a in ACTIONS if a != action)
        return {"action": other, **GOOD[other][1]}
    return {"action": action}                                      # no_value


@pytest.mark.parametrize("shape", ["valued", "valued_with_bad", "nested", "nested_str",
                                   "no_value", "other_action"])
@pytest.mark.parametrize("action", ACTIONS)
async def test_c1_model_confirm_never_executes_with_model_args(api, action, shape):
    """V1 (1)：三開關 on、一般寫入回合，模型以任意參數（有值、巢狀、無值、他動作）自呼 `confirm.request`，
    送進 registry 的 payload 只會是 `{action, **to_payload(草稿)}`（summary 常數）或不執行。"""
    text, _good = GOOD[action]
    w = _World()
    if shape == "no_value":
        _seed_draft(w, action, {_text_key(action): SPECIAL_SAID})
    res, _p = await _turn_p(w, text, [_proposal(_c1_payload(shape, action)), _out()])
    assert WF.V_WRITE_PROPOSAL in res.trace.violations
    calls = w.reg.confirm_calls()
    draft = w.draft()
    for args, _result in calls:
        assert draft is not None
        assert args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
        assert _sent_payload(args) == {"action": draft["action"],
                                       **WF.to_payload(draft["action"], draft["fields"])}
    for mark in _sources(w, res):
        assert mark.startswith(CONFIRM_SOURCE_PREFIX + "program_"), mark   # 一般回合沒有模型來源


async def test_c1_positive_control_the_switch_off_run_does_execute_model_args(api, monkeypatch):
    """V1 (1) 正對照：同一份提議在開關 off 時以模型參數執行（證明上面的斷言不是空轉）。"""
    monkeypatch.setenv(PROPOSAL_ENV, "off")
    action = "repair_create"
    text, good = GOOD[action]
    w = _World()
    await _turn_p(w, text, [_proposal({"action": action, **good}), _out(), _out()])
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == "確認"


_MISSING_FIELDS_TURN = (
    "新增物件 測試新物件甲 台北市",
    [_proposal({"action": "estate_create", "title": "測試新物件甲", "city": "台北市"}), _out()],
)


async def test_c2_missing_fields_ask_is_the_program_text(api):
    """V1 (2)：缺欄追問文字＝`missing_fields_ask_text`（程式文字），主模型不寫；`asked` 由
    `_write_draft_record_asked` 寫入，值＝`asked_keys_for_labels`。"""
    w = _World()
    res, provider = await _turn_p(w, *_MISSING_FIELDS_TURN)
    (args, result), = w.reg.confirm_calls()
    assert result.error == "INVALID_INPUT" and result.data["missing_fields"]
    assert res.answer == C.missing_fields_ask_text(result)
    assert res.outcome["state"] == "clarifying"
    assert len(provider.calls) == 1                                # 只有第一次（提議）叫了模型
    assert w.draft()["asked"] == WF.asked_keys_for_labels("estate_create", result.data["missing_fields"])


def test_c2_asked_has_a_single_writer():
    """V1 (2)（靜態）：把非空欄位鍵寫進 `["asked"]` 的指派只在 `_write_draft_record_asked`；
    正對照：該函式本身命中。"""
    funcs = _runtime_functions()
    (writer,) = funcs["_write_draft_record_asked"]
    assert '["asked"] = keys' in writer
    for name, sources in funcs.items():
        if name == "_write_draft_record_asked":
            continue
        for src in sources:
            assert '["asked"] = keys' not in src, name


@pytest.mark.parametrize("button", ["confirm_submit", "confirm_cancel", "confirm_edit"])
async def test_c3_confirm_button_turns_never_call_the_model(api, button):
    """V1 (3)：送出／取消／修改回合不呼叫主模型，`answer` 是程式文字。"""
    w = _World()
    _res, pid = await w.repair_card()
    payload = w.pending()[pid]["payload"]
    res, provider = await _turn_p(w, f"{button}:{pid}", [], program_first=True)
    assert provider.calls == []
    if button == "confirm_cancel":
        assert res.answer == runtime_mod.CANCELLED_TEXT
    elif button == "confirm_edit":
        assert res.answer == WF.edit_ask_text("repair_create", payload)
    else:
        assert res.outcome["state"] == "confirmed" and res.answer
        assert w.writes() == ["jgb2.action.repair_create"]


async def _select_turn(w: _World, message: str):
    """`select:` 回合（同 step3 #9aa 的裝置：`_RouteVerifier`、空腳本的 provider）。"""
    provider = _Provider([], None)
    rt = AgentRuntime(provider, w.reg, _RouteVerifier([VerifierVerdict(ok=True)] * 6),
                      FakeAssembler(), Budget(), stage="M1", clock=FakeClock(), db_pool=w.db)
    return await rt.run_turn(w.ident, message, w.state), provider


async def test_c4_select_button_turn_never_calls_the_model(api):
    """V1 (4)：`select:` 按鈕回合的選取不經模型（主模型 0 次呼叫），範圍由程式釘住。"""
    w = _World()
    res, provider = await _select_turn(w, "select:bill:709744")
    assert provider.calls == []
    assert w.state["agent"][SELECT_SCOPE_KEY]["estate_id"] == "67652"


async def test_c5_card_answer_is_the_formatter_text(api):
    """V1 (5)：確認卡 `answer` 逐字等於 formatter 產出的卡文字（`confirm.request` 結果的 `card`），
    且待確認筆的 `card_sha256` 是同一段文字的雜湊。"""
    w = _World()
    res, pid = await w.repair_card()
    (_args, result), = w.reg.confirm_calls()
    assert res.answer == result.data["card"]
    assert w.pending()[pid]["card_sha256"] == runtime_mod.sha256_hex(result.data["card"])
    assert res.quick_replies == C.confirm_quick_replies(pid)


def test_c6_buttons_come_only_from_the_program_schema():
    """V1 (6)（靜態）：`AgentOutput` 沒有按鈕欄位；模型迴圈（`_run_model_loop`）裡 `quick_replies` 的
    來源只有程式（`confirm_quick_replies`、候選按鈕、空串列），沒有任何一處讀模型輸出的欄位。"""
    assert not [k for k in AgentOutput.model_fields if re.search(r"button|quick|reply", k, re.I)]
    (src,) = _runtime_functions()["_run_model_loop"]
    assert not re.search(r"(out|agent_out|output|parsed)\.(quick_replies|buttons?)", src)


async def test_c6_buttons_come_only_from_the_program(api):
    """V1 (6)：模型輸出帶 `quick_replies` 額外鍵 ⇒ 結果的按鈕仍是空的。"""
    w = _World()
    extra = {"quick_replies": [{"label": "偷塞", "value": "confirm_submit:x"}]}
    res, _p = await _turn_p(w, "今天天氣如何", [_out(raw_extra=extra)], intents=[_intent("none")])
    assert res.quick_replies == []


# ════════════════════════════════════════════════════════════════════
# (b) 現況探針：偏離仍在（消失即失敗，要人手動移出登記）
# ════════════════════════════════════════════════════════════════════
def _anchor_present(kd_id: str) -> None:
    for fname, symbol in KD_BY_ID[kd_id]["anchors"]:
        text = (AGENT_DIR / fname).read_text(encoding="utf-8")
        assert symbol in text, KD_HINT.format(kd=kd_id) + f"（錨點 {fname}:{symbol} 不見了）"


async def test_kd1_probe_select_scope_turn_model_confirm_is_executed(api):
    """KD-1：三開關 on 的點選範圍回合，模型自呼 `confirm.request` 的參數照舊執行（summary＝模型給的「確認」）。"""
    _anchor_present("KD-1")
    w = _World()
    _with_select_scope(w)
    payload = {"action": "repair_create", "estate_name": STUDENT_ESTATE, "description": "冷氣不冷"}
    res, _p = await _turn_p(w, "再出一次確認卡", [_proposal(payload), _out(), _out()])
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == "確認", KD_HINT.format(kd="KD-1")
    assert _sent_payload(args) == payload, KD_HINT.format(kd="KD-1")
    assert "confirm_source:model:select_scope" in res.trace.violations
    assert WF.V_WRITE_PROPOSAL not in res.trace.violations


def test_kd1_probe_the_proposal_branch_excludes_readonly_view_and_select_scope():
    """KD-1（靜態）：A+ 提議分支條件仍排除點選範圍與唯讀檢視。"""
    cond = _proposal_branch_condition_src()
    assert "SELECT_SCOPE_KEY" in cond and "readonly_view" in cond, KD_HINT.format(kd="KD-1")


async def test_kd2_probe_document_turn_model_confirm_is_executed(api):
    """KD-2：文件回合（收據）模型自呼 `confirm.request` 照舊由模型參數出卡路徑執行；文件暫存有效
    回合同樣（`confirm_source:model:document_carry`）。"""
    _anchor_present("KD-2")
    reg = _RealConfirmRegistry()
    payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": "水電費",
               "total": 99999, "date_expire": "20261130"}
    from tests.unit.agent.test_assistant_documents_photos_req import _confirm_call
    res = await _rt(FakeProvider([_confirm_call(payload), _final_response()]), reg).run_turn(
        _pm(), "這張收據開到合約 89481，項目水電費，期限 20261130", {"agent": {}},
        document=_receipt_doc())
    assert res.outcome["state"] == "confirm_pending", KD_HINT.format(kd="KD-2")
    assert [v for v in res.trace.violations if v.startswith(CONFIRM_SOURCE_PREFIX)] == [
        "confirm_source:model:document"], KD_HINT.format(kd="KD-2")
    w = _World()
    _with_carry(w)
    res2, _p = await _turn_p(w, "再出一次確認卡", [_proposal({"action": "estate_create"}), _out(), _out()])
    (args, _r), = w.reg.confirm_calls()
    assert args["summary"] == "確認", KD_HINT.format(kd="KD-2")
    assert "confirm_source:model:document_carry" in res2.trace.violations


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_c7_unissued_proposal_reply_is_the_program_state_reply(api, monkeypatch, b_reply):
    """必過契約（B 片 B1，原 KD-3 探針改寫）：寫入情境非問句回合，提議沒轉成程式呼叫（內層動作不合）⇒
    記 `write_proposal_not_issued`，主模型 ⛔ 被叫第二次；回覆＝程式狀態回話（本案無草稿、無 live 卡 ⇒
    `NO_PENDING_WRITE_TEXT`），模型文字 ⛔ 出現。正對照：`AGENT_WRITE_REPLY_PROGRAM=off` ⇒ 改前行為（模型被叫第二次寫回話）。"""
    if b_reply == "off":
        monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    action = "repair_create"
    text, good = GOOD[action]
    other = next(a for a in ACTIONS if a != action)
    w = _World()
    res, provider = await _turn_p(w, text, [_proposal(_nested(action, {"action": other, **good})),
                                            _out("模型寫的回話。")])
    assert WF.V_WRITE_PROPOSAL_NOT_ISSUED in res.trace.violations
    assert w.reg.confirm_calls() == []
    if b_reply == "on":
        assert len(provider.calls) == 1 and "模型寫的回話" not in res.answer
        assert res.answer == WF.NO_PENDING_WRITE_TEXT
        assert WF.V_WRITE_REPLY_KD3_EXIT in res.trace.violations
        assert f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{WF.WRITE_REPLY_SOURCE_PROGRAM}" in res.trace.violations
    else:
        assert len(provider.calls) == 2 and "模型寫的回話" in res.answer


KD4_CONFIRM_PROSE = "請確認以上內容"
KD4_FIELD_ASK = "請問物件地址是？"


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_c8_model_confirm_prose_is_replaced_by_the_program_reply(api, monkeypatch, b_reply):
    """必過契約（B 片 B2／B3，原 KD-4 (i) 改前行為探針改寫）：寫入情境非問句回合（草稿存在），假模型輸出
    `kind=ask`、`ask_target=confirm_intent`「請確認以上內容」、本回合未呼叫 `confirm.request` ⇒ 回覆 ⛔ 含該句，
    改為程式狀態回話（草稿缺「問題描述」⇒ 缺欄追問樣板）；送出的 `ask_target` ⛔ 為 `confirm_intent`。
    正對照：兩開關 off ⇒ 改前行為（回覆含該句原文）。"""
    if b_reply == "off":
        monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
        monkeypatch.setenv("AGENT_STATE_CLAIM_GATE", "off")
    w = _World()
    _seed_draft(w, "repair_create", {"estate_name": STUDENT_ESTATE})
    res, _p = await _turn_p(w, "我等一下再補",
                            [_out(KD4_CONFIRM_PROSE, kind="ask", ask_target="confirm_intent")])
    assert w.draft() is not None and w.reg.confirm_calls() == []          # 前提：寫入情境、未出卡
    if b_reply == "on":
        assert KD4_CONFIRM_PROSE not in res.answer
        assert res.answer == C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="問題描述")
        assert res.ask_target != "confirm_intent"
        assert f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{WF.WRITE_REPLY_SOURCE_PROGRAM}" in res.trace.violations
    else:
        assert KD4_CONFIRM_PROSE in res.answer


@pytest.mark.parametrize("b_reply", ["on", "off"])
async def test_c9_model_field_ask_is_replaced_by_the_program_reply(api, monkeypatch, b_reply):
    """必過契約（B 片 B2，原 KD-4 (ii) 改前行為探針改寫）：寫入情境非問句回合、草稿缺欄，假模型輸出
    `kind=ask`、`ask_target=address`「請問物件地址是？」⇒ 回覆 ⛔ 含該句，改為程式缺欄追問（依草稿算、
    套 `MISSING_FIELDS_ASK_TEMPLATE`）。正對照：`AGENT_WRITE_REPLY_PROGRAM=off` ⇒ 改前行為（回覆含該句原文）。"""
    if b_reply == "off":
        monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    w = _World()
    _seed_draft(w, "estate_create", {"title": "測試新物件甲", "city": "台北市"})
    res, _p = await _turn_p(w, "先這樣",
                            [_out(KD4_FIELD_ASK, kind="ask", ask_target="address")])
    assert w.draft() is not None and w.reg.confirm_calls() == []          # 前提：寫入情境、草稿缺欄
    if b_reply == "on":
        assert KD4_FIELD_ASK not in res.answer
        labels = WF.missing_labels("estate_create", WF.to_payload("estate_create", w.draft()["fields"]))
        assert labels                                                      # 前提：真的缺欄
        assert res.answer == C.MISSING_FIELDS_ASK_TEMPLATE.format(labels=C.MISSING_FIELDS_SEP.join(labels))
    else:
        assert KD4_FIELD_ASK in res.answer


def test_kd5_probe_handoff_gate_only_acts_after_the_model_chose_handoff():
    """KD-5：出口閘 `_apply_handoff_data_exits` 首行 `if result.kind != "handoff": return result`
    （只在模型選了轉人後介入）；沒有收尾規則（`還有什麼／還有其他／還需要其他` 不在 agent 目錄的程式碼字串）。"""
    _anchor_present("KD-5")
    tree = ast.parse((AGENT_DIR / "exit_gates.py").read_text(encoding="utf-8"))
    (fn,) = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "_apply_handoff_data_exits"]
    body = [b for b in fn.body if not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))]
    first = ast.unparse(body[0])
    assert "result.kind != 'handoff'" in first and "return result" in first, KD_HINT.format(kd="KD-5")
    # A-2a（A2-R7）候選清單固定句「還有其他筆，不在其中請講編號」是候選清單的續列提示、
    # 不是收尾規則 ⇒ 只排除「還有其他筆」這一個寫法（負向前瞻），其餘收尾詞照舊掃。
    pattern = "還有什麼|還有其他(?!筆)|還需要其他"
    assert re.search(pattern, "還有其他需要幫忙的嗎") and not re.search(pattern, "還有其他筆，不在其中請講編號。")

    def string_constants(path: Path) -> list:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                    docs.add(id(n.body[0].value))
        return [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]

    all_consts = [c for path in AGENT_DIR.glob("*.py") for c in string_constants(path)]
    assert any("確認" in c for c in all_consts), "掃描法壞了（正對照：已知必然存在的字串沒中）"
    assert not [c for c in all_consts if re.search(pattern, c)], KD_HINT.format(kd="KD-5")


def test_kd6_probe_no_program_exit_for_empty_knowledge():
    """KD-6：知識完全查無時只記 `candidate_none_visible`（退回只給目錄），沒有程式先發的「處理不了」出口。"""
    _anchor_present("KD-6")
    text = RUNTIME_PATH.read_text(encoding="utf-8")
    assert re.search(r'violations\.append\("candidate_none_visible"\)', text), KD_HINT.format(kd="KD-6")
    funcs = _runtime_functions()
    srcs = [s for ss in funcs.values() for s in ss if "candidate_none_visible" in s]
    assert srcs and not any("return exit_gates" in s or "build_fixed" in s for s in srcs), \
        KD_HINT.format(kd="KD-6")


async def test_kd7_probe_read_query_args_are_the_models(api):
    """KD-7：唯讀查詢（帳單）的參數由模型自呼工具決定——registry 收到的就是模型給的參數。"""
    _anchor_present("KD-7")
    w = _World()
    args = {"estate_name": KEELUNG_ESTATE, "keyword": "模型自己挑的篩選字"}
    res, _p = await _turn_p(w, f"{KEELUNG_ESTATE} 的帳單有哪些",
                            [_call("jgb2.query.bills", args), _out()], intents=[_intent("none")])
    names = [n for n, a, _r in w.reg.results if n == "jgb2.query.bills"]
    sent = [a for n, a, _r in w.reg.results if n == "jgb2.query.bills"]
    assert names and any(a.get("keyword") == args["keyword"] for a in sent), KD_HINT.format(kd="KD-7")


async def test_kd8_probe_typed_candidate_pick_has_no_program_path(api):
    """KD-8（A-2a 後範圍收窄，A2-R10）：唯讀查詢的候選只有 `select:` 按鈕能釘住範圍；打字說出候選名稱
    不會釘住範圍、也不會建寫入候選集。寫入名稱多筆的打字選定已由 A-2a 程式路徑接手（`pick:` ／
    `pick_id`，見 `test_a2a_write_candidates_req.py`），不在本探針範圍。"""
    _anchor_present("KD-8")
    assert runtime_mod._SELECT_VALUE_RE.pattern.startswith("select:") or "select:" in \
        runtime_mod._SELECT_VALUE_RE.pattern, KD_HINT.format(kd="KD-8")
    assert runtime_mod._SELECT_VALUE_RE.fullmatch("基隆溫馨一人宅套房") is None
    title = "台北文山-離塵一房(國泰)"                       # mock 兩筆同名物件（40303、26007）
    w = _World()
    res, provider = await _turn_p(
        w, f"{title} 現況如何",
        [_call("jgb2.query.estates", {"face": "物件現況診斷", "keyword": title}), _out()],
        intents=[_intent("none")])
    sent = [r for n, _a, r in w.reg.results if n == "jgb2.query.estates"]
    assert sent and len((sent[0].data or {}).get("candidates") or []) >= 2   # 前提：唯讀查詢回多筆候選
    res2, _p2 = await _turn_p(w, title, [_out()], intents=[_intent("none")])
    agent = w.state.get("agent") or {}
    assert agent.get(SELECT_SCOPE_KEY) is None, KD_HINT.format(kd="KD-8")
    assert agent.get(WRITE_CANDIDATES_KEY) is None, KD_HINT.format(kd="KD-8")


# ════════════════════════════════════════════════════════════════════
# (c) 登記完整
# ════════════════════════════════════════════════════════════════════
def _this_file_test_names() -> set:
    tree = ast.parse(THIS_FILE.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")}


#: 登記中的 KD 編號（B 片接手 KD-3、KD-4 後移出；計畫 plan-b-write-replies-program-20261020 §4.1 B6）。
REGISTERED_KD_NUMBERS = (1, 2, 5, 6, 7, 8)


def test_registry_has_kd1_to_kd8_and_each_has_takeover_and_anchor():
    assert [kd["id"] for kd in REG.KNOWN_DEVIATIONS] == [f"KD-{i}" for i in REGISTERED_KD_NUMBERS]
    for kd in REG.KNOWN_DEVIATIONS:
        assert kd["takeover"] and kd["comment_token"] and kd["anchors"] and kd["row"], kd["id"]


def test_registry_every_division_row_has_a_must_pass_test_or_a_kd():
    assert sorted(REG.DIVISION_ROWS) == [f"R{i}" for i in range(1, 7)]
    for rid, row in REG.DIVISION_ROWS.items():
        assert row["tests"] or row["kds"], f"{rid} {row['name']} 沒有對應的必過測試或 KD"
        for kd in row["kds"]:
            assert kd in KD_BY_ID, (rid, kd)


def test_registry_listed_test_names_exist():
    names = _this_file_test_names()
    for rid, row in REG.DIVISION_ROWS.items():
        for t in row["tests"]:
            assert t in names, (rid, t)
    # 正對照：每個 KD 都有一支探針
    for i in REGISTERED_KD_NUMBERS:
        assert any(n.startswith(f"test_kd{i}_probe") for n in names), f"KD-{i} 缺探針"
    # 已移出登記的 KD（B 片接手）⇒ 探針已刪、改成必過契約（⛔ 留著會失敗的探針）
    for i in (3, 4):
        assert not any(n.startswith(f"test_kd{i}_probe") for n in names), f"KD-{i} 已移出登記，探針應已刪"


# ════════════════════════════════════════════════════════════════════
# (d) 靜態
# ════════════════════════════════════════════════════════════════════
def test_static_begin_pending_confirm_has_exactly_one_call_site():
    text = RUNTIME_PATH.read_text(encoding="utf-8")
    assert len(re.findall(r"self\._begin_pending_confirm\(", text)) == 1
    assert len(re.findall(r"def _begin_pending_confirm\(", text)) == 1       # 正對照：定義存在


def _proposal_branch_condition_src() -> str:
    text = RUNTIME_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    (loop,) = [n for n in ast.walk(tree)
               if isinstance(n, ast.AsyncFunctionDef) and n.name == "_run_model_loop"]
    found = [n for n in ast.walk(loop)
             if isinstance(n, ast.If)
             and "_write_proposal_active()" in ast.unparse(n.test)
             and "SELECT_SCOPE_KEY" in ast.unparse(n.test)]
    assert len(found) == 1, "找不到 A+ 提議分支條件"
    return ast.unparse(found[0].test)


class _Stub:
    def __init__(self, active: bool, readonly_view: bool):
        self._active, self.readonly_view = active, readonly_view

    def _write_proposal_active(self) -> bool:
        return self._active


_STATE_CASES = list(itertools.product([True, False], [False, True], [False, True], [False, True],
                                      [False, True]))


@pytest.mark.parametrize("active,document,carry,scope,view", _STATE_CASES)
def test_reason_function_agrees_with_the_proposal_branch(active, document, carry, scope, view):
    """一般模型自呼回合：理由函式判為 `unregistered`（＝須由程式）⇔ A+ 提議分支條件為真。
    分支條件取自 `_run_model_loop` 的真實 AST（不是複製一份），要是條件被改壞，這裡兩邊就分歧。"""
    cond_src = _proposal_branch_condition_src()
    agent_state: dict = {}
    if carry:
        from services.agent.agent_session import AgentSession
        AgentSession(agent_state).write_document_carry("estate_create", [("address", "某路 1 號")], None)
        assert runtime_mod._document_carry_of(agent_state) is not None
    if scope:
        agent_state[SELECT_SCOPE_KEY] = {"type": "bill", "estate_id": "67652"}
    doc = object() if document else None
    env = {"name": runtime_mod.CONFIRM_TOOL_NAME, "CONFIRM_TOOL_NAME": runtime_mod.CONFIRM_TOOL_NAME,
           "wd_program": False, "self": _Stub(active, view), "document": doc,
           "agent_state": agent_state, "_document_carry_of": runtime_mod._document_carry_of,
           "SELECT_SCOPE_KEY": SELECT_SCOPE_KEY}
    branch = bool(eval(compile(cond_src, "<branch>", "eval"), {}, env))
    reason = runtime_mod._confirm_model_reason(proposal_active=active, document=doc,
                                               agent_state=agent_state, readonly_view=view)
    assert (reason == "unregistered") == branch, (reason, branch, cond_src)


@pytest.mark.parametrize("kwargs,expected", [
    (dict(proposal_active=False, document=None, agent_state={}, readonly_view=False), "flag_off"),
    (dict(proposal_active=True, document=object(), agent_state={}, readonly_view=False), "document"),
    (dict(proposal_active=True, document=None, agent_state={SELECT_SCOPE_KEY: {"type": "bill"}},
          readonly_view=False), "select_scope"),
    (dict(proposal_active=True, document=None, agent_state={}, readonly_view=True), "readonly_view"),
    (dict(proposal_active=True, document=None, agent_state={}, readonly_view=False), "unregistered"),
])
def test_reason_function_value_domain(kwargs, expected):
    assert runtime_mod._confirm_model_reason(**kwargs) == expected


def _transition_comment_blocks() -> list:
    """「過渡修正」所在的連續註解區塊（整段文字）。"""
    lines = RUNTIME_PATH.read_text(encoding="utf-8").splitlines()
    blocks, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("#"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("#"):
                j += 1
            block = "\n".join(lines[i:j])
            if "過渡修正" in block:
                blocks.append(block)
            i = j
        else:
            i += 1
    return blocks


def test_static_every_transition_comment_names_a_registered_takeover():
    blocks = _transition_comment_blocks()
    # 正對照：全 runtime.py 至少 2 處『過渡修正』註解（KD-1／KD-2 的 AP-5 與 `elif` 兩處；原 KD-3 的兩處
    # 隨 B 片接手改寫成現況註解、不再是過渡修正）。
    assert len(blocks) >= 2, "正對照：全 runtime.py 至少 2 處『過渡修正』註解"
    tokens = {kd["comment_token"] for kd in REG.KNOWN_DEVIATIONS if kd["has_comment"]}
    for b in blocks:
        assert any(t in b for t in tokens), f"『過渡修正』註解沒寫登記中的接手片：\n{b}"


def test_static_every_commented_kd_has_a_comment():
    blocks = _transition_comment_blocks()
    for kd in REG.KNOWN_DEVIATIONS:
        if kd["has_comment"]:
            assert any(kd["id"] in b and kd["comment_token"] in b for b in blocks), \
                f"{kd['id']} 標有註解，但沒有一處『過渡修正』註解同時寫出 {kd['id']} 與 {kd['comment_token']}"


def test_static_elif_comment_covers_both_cases():
    """DG-5：`elif` 呼叫 `_write_draft_merge_model_confirm` 前的註解同時寫明開關 off（回復開關）與
    開關 on 的點選範圍、唯讀檢視回合（KD-1、A-2）。"""
    blocks = [b for b in _transition_comment_blocks() if "回復開關" in b]
    assert len(blocks) == 1
    b = blocks[0]
    for needle in ("AP-R7", "非目標組態", "點選範圍", "唯讀檢視", "KD-1", "A-2"):
        assert needle in b, needle


# ════════════════════════════════════════════════════════════════════
# (e) V3：六種情境各出現正確的 `confirm_source:` 且每次執行恰一筆
# ════════════════════════════════════════════════════════════════════
async def test_v3_program_draft(api):
    w = _World()
    res, _pid = await w.repair_card()
    assert _exactly_one_per_execution(w, res) == "program_draft"


async def test_v3_program_proposal(api):
    w = _World()
    text, good = GOOD["repair_create"]
    res, _p = await _turn_p(w, text, [_proposal({"action": "repair_create", **good}), _out()])
    assert _exactly_one_per_execution(w, res) == "program_proposal"


async def test_v3_program_proposal_missing_fields_also_gets_one_mark(api):
    """缺欄追問（回缺欄、不出卡）同樣恰一筆。"""
    w = _World()
    res, _p = await _turn_p(w, *_MISSING_FIELDS_TURN)
    assert res.outcome["state"] == "clarifying"
    assert _exactly_one_per_execution(w, res) == "program_proposal"


async def test_v3_program_document(api):
    reg = _RealConfirmRegistry()
    res = await _rt(FakeProvider([]), reg).run_turn(
        _pm(), "幫我用這份建物謄本建立一筆物件。", {"agent": {}}, document=_deed(_FULL_TYPED))
    marks = [v for v in res.trace.violations if v.startswith(CONFIRM_SOURCE_PREFIX)]
    assert marks == [CONFIRM_SOURCE_PREFIX + "program_document"], marks
    assert len(reg.results) == 1


async def test_v3_select_scope(api):
    w = _World()
    _with_select_scope(w)
    res, _p = await _turn_p(w, "再出一次確認卡", [_proposal({"action": "repair_create"}), _out(), _out()])
    assert _exactly_one_per_execution(w, res) == "model:select_scope"


async def test_v3_document_carry(api):
    w = _World()
    _with_carry(w)
    res, _p = await _turn_p(w, "再出一次確認卡", [_proposal({"action": "repair_create"}), _out(), _out()])
    # 暫存動作與提議動作不同 ⇒ 路上會清暫存；標記仍反映進場當下的狀態
    assert _exactly_one_per_execution(w, res) == "model:document_carry"


async def test_v3_flag_off(api, monkeypatch):
    monkeypatch.setenv(PROPOSAL_ENV, "off")
    w = _World()
    text, good = GOOD["repair_create"]
    res, _p = await _turn_p(w, text, [_proposal({"action": "repair_create", **good}), _out(), _out()])
    assert _exactly_one_per_execution(w, res) == "model:flag_off"


async def test_v3_no_confirm_request_means_no_mark(api):
    """正對照：沒有 `confirm.request` 的回合沒有任何 `confirm_source:`。"""
    w = _World()
    res, _p = await _turn_p(w, "今天天氣如何", [_out()], intents=[_intent("none")])
    assert _sources(w, res) == []
