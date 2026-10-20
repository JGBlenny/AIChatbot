"""unit：主線第 3 步 A 片——草稿生命週期（A1）、「修改」按鈕（A3）、唯一有效卡（A7）、
卡後改欄位（A2）。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-conversation-architecture-step3-20261018.md`
§4「A」表；凍結驗收清單同目錄 `acceptance-conversation-architecture-step3-20261018.md`
#5 (a)～(g)、#9a～#9i、#9l～#9n、#9q、#9r、#9t、#9aa 的**單元＋DB 證據**。

「DB」＝`tests.unit.agent.token_db_double.FakeTokenDB`：有狀態的 `agent_confirmation_tokens`
記憶體表，只認 `tools/confirm.py` 的 SQL 常數（`redeemed` 欄位真的被改、兌現真的看
`session_id`／`pending_id`／`redeemed`／`expires_at`）。並行交錯（#9p）以真 PG 另驗：
`tests/integration/agent/test_step3_unique_card_pg_req.py`。

資料與工具走真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`）＋真
`mcp_facade.build_registry`；全部離線。期望值由測試自己寫死（fixture 原始 JSON 人工查證）：
  - 67338「學生獨立套房可租補」：只有 12291 看得到；
  - 67652「基隆溫馨一人宅套房」：帳單 709744（2026-11 那期，date_expire 20261101）。
「寫入次數」＝`_Reg.results` 中 `jgb2.action.*` 的呼叫數（兌現段唯一的寫入出口）。
"""
from __future__ import annotations

import copy
import json
from datetime import date
from types import SimpleNamespace

import pytest

from services import jgb_system_api as api_mod
from services.agent import write_forms as WF
from services.agent.agent_session import (
    LAST_SUBMITTED_KEY, PENDING_CONFIRM_KEY, SELECT_SCOPE_KEY, WRITE_DRAFT_KEY,
)
from services.agent.budget import Budget
from services.agent.confirm_card import CANCELLED_TEXT, CONFIRMATION_REQUIRED_TEXT
from services.agent.runtime import AgentRuntime
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RecordingTransport

from tests.unit.agent.test_runtime_req import FakeAssembler, FakeClock, FakeVerifier, VerifierVerdict
from tests.unit.agent.test_write_draft_flow_req import (
    FIXTURE, KEELUNG_ESTATE, STUDENT_ESTATE, _call, _confirm_args, _intent, _out, _pm, _Provider,
    _Reg, _RulesVerifier,
)
from tests.unit.agent.token_db_double import FakeTokenDB

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-conversation-architecture-step3-A")]

TODAY = date(2026, 10, 17)
REPAIR_TEXT = f"{STUDENT_ESTATE} 冷氣不冷"
LIFECYCLE_ENV = WF.WRITE_LIFECYCLE_ENV


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)
    monkeypatch.delenv("AGENT_WRITE_DRAFT", raising=False)
    monkeypatch.delenv(LIFECYCLE_ENV, raising=False)          # 未設＝on（開關的預設）
    monkeypatch.delenv(WF.WRITE_PROPOSAL_ENV, raising=False)  # A+ 片：未設＝on
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv(MOCK_WRITE_LOG_ENV, raising=False)
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
class _World:
    """一個 session 的測試世界：同一張 token 表、同一個 registry（寫入計數跨回合累計）。"""

    def __init__(self, ident=None):
        self.ident = ident or _pm()
        self.db = FakeTokenDB()
        self.reg = _Reg(self.db)
        self.state: dict = {}

    def runtime(self, provider, *, program_first: bool = True, readonly_view: bool = False):
        verifier = (_RulesVerifier if program_first else FakeVerifier)([VerifierVerdict(ok=True)] * 6)
        return AgentRuntime(provider, self.reg, verifier, FakeAssembler(), Budget(), stage="M1",
                            clock=FakeClock(), db_pool=self.db, readonly_view=readonly_view)

    async def turn(self, message, *, script=(), intents=None, program_first: bool = True,
                   state=None, readonly_view: bool = False):
        provider = _Provider(list(script), intents)
        rt = self.runtime(provider, program_first=program_first, readonly_view=readonly_view)
        res = await rt.run_turn(self.ident, message, self.state if state is None else state)
        assert rt._write_intent_calls == {}
        return res

    async def repair_card(self, text: str = REPAIR_TEXT, **fields):
        """程式優先出一張修繕卡（主模型不被呼叫）。"""
        values = {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷", **fields}
        res = await self.turn(text, intents=[_intent("repair_create", **values)])
        assert res.outcome["state"] == "confirm_pending", res.answer
        return res, res.trace.pending_id

    def writes(self) -> list:
        return [name for name, _args, _res in self.reg.results if name.startswith("jgb2.action.")]

    def draft(self):
        return (self.state.get("agent") or {}).get(WRITE_DRAFT_KEY)

    def pending(self) -> dict:
        return (self.state.get("agent") or {}).get(PENDING_CONFIRM_KEY) or {}

    @property
    def session_id(self) -> str:
        return self.ident.session_id


def _chat_turn_args():
    """非寫入相關的文字回合：意圖 none、主模型回一句一般回答。"""
    return dict(script=[_out("好的，有需要再跟我說。")], intents=[_intent("none")])


# ════════════════════════════════════════════════════════════════════
# #5 草稿生命週期（A1）
# ════════════════════════════════════════════════════════════════════
async def test_5a_card_keeps_the_draft(api):
    """#5 (a)：出卡後草稿仍在（同一個動作、欄位就是使用者講的那兩欄）。"""
    w = _World()
    _res, pid = await w.repair_card()
    assert w.draft() is not None
    assert w.draft()["action"] == "repair_create"
    assert w.draft()["fields"] == {"estate_name": STUDENT_ESTATE, "description": "冷氣不冷"}
    assert w.pending()[pid]["action"] == "repair_create"


async def test_5a_off_switch_card_clears_the_draft_as_before(api, monkeypatch):
    """#5 (a) 正對照：開關 off ⇒ 現行「出卡即清」。"""
    monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    await w.repair_card()
    assert w.draft() is None


async def test_5b_cancel_clears_the_draft(api):
    w = _World()
    _res, pid = await w.repair_card()
    res = await w.turn(f"confirm_cancel:{pid}")
    assert res.answer == CANCELLED_TEXT
    assert w.draft() is None
    assert w.db.redeemed(pid) is True
    assert w.writes() == []


async def test_5c_receipt_write_clears_the_draft(api):
    """#5 (c)：送出成功（寫 receipt）⇒ 草稿清空；寫入恰 1 次。"""
    w = _World()
    _res, pid = await w.repair_card()
    assert w.draft() is not None                         # 前提：出卡後仍在
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "confirmed", res.answer
    assert isinstance(w.pending()[pid].get("receipt"), dict)
    assert w.draft() is None
    assert w.writes() == ["jgb2.action.repair_create"]


async def test_5c_error_receipt_also_clears_the_draft(api, monkeypatch):
    """#5 (c)「任一 receipt 寫入」：寫入失敗也寫 receipt（error）⇒ 草稿同樣清空。"""
    w = _World()
    _res, pid = await w.repair_card()
    monkeypatch.setenv("MOCK_FAIL_NEXT_WRITE", "1")
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "failed", res.answer
    assert w.pending()[pid].get("receipt", {}).get("error")
    assert w.draft() is None


async def test_5d_idle_text_turns_while_card_pending_clear_the_draft(api):
    """#5 (d)：確認待決期間連續 `DRAFT_IDLE_LIMIT` 個非寫入相關文字回合 ⇒ 草稿清空（只清草稿）。"""
    w = _World()
    _res, pid = await w.repair_card()
    for i in range(WF.DRAFT_IDLE_LIMIT):
        assert w.draft() is not None, f"第 {i} 個閒聊回合前草稿應仍在"
        res = await w.turn("今天天氣如何", **_chat_turn_args())
    assert w.draft() is None
    assert WF.V_DRAFT_CLEARED_IDLE in res.trace.violations
    # 只清草稿：綁定的卡（pending 與 DB 列）不動
    assert pid in w.pending() and "receipt" not in w.pending()[pid]
    assert w.db.redeemed(pid) is False


async def test_5e_edit_resets_idle_turns_and_keeps_the_draft(api):
    """#5 (e)：按「修改」⇒ `idle_turns`＝0、草稿保留、程式問改哪一項（⛔ `CANCELLED_TEXT`）。"""
    w = _World()
    _res, pid = await w.repair_card()
    await w.turn("今天天氣如何", **_chat_turn_args())
    assert w.draft()["idle_turns"] == 1                  # 前提：已累加
    res = await w.turn(f"confirm_edit:{pid}")
    assert w.draft() is not None and w.draft()["idle_turns"] == 0
    assert res.answer != CANCELLED_TEXT
    assert res.answer == WF.edit_ask_text("repair_create", w.pending()[pid]["payload"])
    assert "物件" in res.answer and "問題描述" in res.answer   # 卡上欄位標籤（表單宣告）
    assert res.outcome["state"] == "clarifying" and res.outcome["expects"] == "text"
    assert w.db.redeemed(pid) is True                    # token 照燒
    assert w.writes() == []


async def test_5f_button_turns_do_not_count_idle(api):
    """#5 (f)：按鈕回合不累加 idle（錯 pid、過期卡的送出都不動 `idle_turns`）。"""
    w = _World()
    _res, pid = await w.repair_card()
    await w.turn("今天天氣如何", **_chat_turn_args())
    assert w.draft()["idle_turns"] == 1
    await w.turn(f"confirm_submit:{'0' * 16}")           # 不認得的 pid
    assert w.draft() is not None and w.draft()["idle_turns"] == 1
    w.db.advance(10_000)                                 # 卡過期
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.draft() is not None and w.draft()["idle_turns"] == 1
    assert w.writes() == []


async def test_5g_bound_card_redeems_as_before_after_idle_clear(api):
    """#5 (g)：idle 清草稿後，綁定卡的兌現與現行相同（照常送出、寫入 1 次、回收據）。"""
    w = _World()
    _res, pid = await w.repair_card()
    for _ in range(WF.DRAFT_IDLE_LIMIT):
        await w.turn("今天天氣如何", **_chat_turn_args())
    assert w.draft() is None
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "confirmed", res.answer
    assert w.writes() == ["jgb2.action.repair_create"]
    assert w.db.redeemed(pid) is True


# ════════════════════════════════════════════════════════════════════
# #9h 修改照燒 token（A3）——三種按鈕交叉重送
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("second", ["confirm_submit", "confirm_edit", "confirm_cancel"])
async def test_9h_edit_burns_token_and_any_resend_never_confirms(api, second):
    w = _World()
    _res, pid = await w.repair_card()
    first = await w.turn(f"confirm_edit:{pid}")
    assert first.answer != CANCELLED_TEXT
    assert w.db.redeemed(pid) is True and w.draft() is not None
    again = await w.turn(f"{second}:{pid}")
    assert again.outcome["state"] != "confirmed", (second, again.answer)
    assert again.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []
    assert "receipt" not in w.pending()[pid]
    if second == "confirm_cancel":
        assert w.draft() is None                         # 使用者不要了 ⇒ 草稿清
    else:
        assert w.draft() is not None


@pytest.mark.parametrize("first", ["confirm_submit", "confirm_cancel"])
async def test_9h_edit_after_a_result_returns_the_same_result(api, first):
    """先送出／先取消、再按修改 ⇒ R4.3 回同一個結果（⛔ 改寫 receipt、⛔ 問改哪一項）。"""
    w = _World()
    _res, pid = await w.repair_card()
    r1 = await w.turn(f"{first}:{pid}")
    receipt = copy.deepcopy(w.pending()[pid]["receipt"])
    r2 = await w.turn(f"confirm_edit:{pid}")
    assert r2.answer == r1.answer
    assert w.pending()[pid]["receipt"] == receipt
    assert len(w.writes()) == (1 if first == "confirm_submit" else 0)


async def test_9h_off_switch_edit_is_cancel_as_before(api, monkeypatch):
    """開關 off ⇒「修改」＝現行「取消」語義（`CANCELLED_TEXT`、receipt cancelled）。"""
    monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    _res, pid = await w.repair_card()
    res = await w.turn(f"confirm_edit:{pid}")
    assert res.answer == CANCELLED_TEXT
    assert w.pending()[pid]["receipt"] == {"cancelled": True}
    assert w.db.redeemed(pid) is True


# ════════════════════════════════════════════════════════════════════
# A2 卡後改欄位＋A7 唯一有效卡（#9a～#9g、#9i、#9l～#9n、#9q、#9r、#9t、#9aa、#9b′）
# ════════════════════════════════════════════════════════════════════
NEW_DESC = "熱水器壞了"
CORRECT_TEXT = f"不是冷氣，改成{NEW_DESC}"


def _correct_intent(**fields):
    return [_intent("repair_create", **(fields or {"description": NEW_DESC}))]


def _model_repair_payload(description: str = "冷氣不冷", estate: str = STUDENT_ESTATE) -> dict:
    return {"action": "repair_create", "estate_name": estate, "description": description}


async def _model_card(w: "_World", description: str = "冷氣不冷", estate: str = STUDENT_ESTATE,
                      *, state=None):
    """模型**自己**呼叫 `confirm.request` 出卡（程式優先關：`FakeVerifier` 無 rules）。"""
    res = await w.turn(f"{estate} {description}",
                       script=[_call("confirm.request",
                                     _confirm_args(_model_repair_payload(description, estate)))],
                       program_first=False, state=state)
    return res, res.trace.pending_id


async def _after_output_card(w: "_World", description: str):
    """輸出後觸發點出卡：主模型先回一句（程式優先關），程式依意圖判斷結果觸發 `confirm.request`。"""
    res = await w.turn(f"{STUDENT_ESTATE} {description}", script=[_out()],
                       intents=[_intent("repair_create", estate_name=STUDENT_ESTATE,
                                        description=description)],
                       program_first=False)
    return res, res.trace.pending_id


def _bill_seed(w: "_World") -> None:
    w.state = {"agent": {
        "dialog": [{"role": "user", "content": "我想把一張帳單延後繳"},
                   {"role": "assistant", "content": "好的。"},
                   {"role": "user", "content": f"{KEELUNG_ESTATE} 11月那期"},
                   {"role": "assistant", "content": "好的。"}],
        WRITE_DRAFT_KEY: {"action": "bill_due_extend",
                          "fields": {"estate_name": KEELUNG_ESTATE, "period": "11月那期"},
                          "idle_turns": 0,
                          "created_by_role": __import__(
                              "services.agent.runtime", fromlist=["_write_draft_owner"]
                          )._write_draft_owner(w.ident),
                          "asked": ["days"]},
    }}


async def _bill_card(w: "_World"):
    _bill_seed(w)
    res = await w.turn("延 7 天", intents=[_intent("bill_due_extend", days="7")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・帳單編號：709744" in res.answer
    return res, res.trace.pending_id


# ── A2 本體 ─────────────────────────────────────────────────────────
async def test_a2_correction_reissues_one_card_and_burns_the_bound_one(api):
    """A2：卡後改欄位（值不同）⇒ 綁定卡經 `redeem_pending` 燒掉、經 `confirm_request` 重出新卡；
    同 session 可兌現 pid 恰 1；舊 pid 送出失敗、新 pid 送出成功（寫入 1 次）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    r2 = await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    pid2 = r2.trace.pending_id
    assert pid2 and pid2 != pid1
    assert "write_draft_card_reissue" in r2.trace.violations
    assert f"・問題描述：{NEW_DESC}" in r2.answer and f"・物件：{STUDENT_ESTATE}" in r2.answer
    assert (pid1, w.session_id) in w.db.redeem_calls          # 以既有 redeem_pending 燒綁定卡
    assert w.db.redeemed(pid1) is True
    assert w.db.live_pids(w.session_id) == [pid2]
    assert w.pending()[pid1].get("invalidated") is True
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT and old.outcome["state"] == "failed"
    assert w.writes() == []
    new = await w.turn(f"confirm_submit:{pid2}")
    assert new.outcome["state"] == "confirmed", new.answer
    assert w.writes() == ["jgb2.action.repair_create"]


async def test_9c_bound_card_already_redeemed_never_reissues(api):
    """#9c（S3）：A2 回合前舊 pid 已被兌現（另一分頁以舊狀態送出）⇒ 燒不到 ⇒ ⛔ 重出卡、
    程式固定句、無新 pending；寫入總計 1 次。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    stale = copy.deepcopy(w.state)
    done = await w.turn(f"confirm_submit:{pid1}")                 # 他處先送出
    assert done.outcome["state"] == "confirmed"
    rows_before = len(w.db.rows)
    res = await w.turn(CORRECT_TEXT, intents=_correct_intent(), state=stale)
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert res.outcome["state"] == "failed"
    assert "write_draft_reissue_burn_failed" in res.trace.violations
    assert res.trace.pending_id is None
    assert list((stale["agent"].get(PENDING_CONFIRM_KEY) or {})) == [pid1]
    assert len(w.db.rows) == rows_before and w.db.live_pids(w.session_id) == []
    assert w.writes() == ["jgb2.action.repair_create"]


@pytest.mark.parametrize("proposal", ["on", "off"])
async def test_9d_repeating_the_same_value_never_reissues(api, monkeypatch, proposal):
    """#9d（S4）：卡後只重複原值 ⇒ 無新 pending、原 pid 仍可送出。

    A+ 片（改寫，原意圖不變）：`proposal=off`＝改前行為的正對照（交回模型、記
    `write_draft_reissue_skipped_same_values`）；`proposal=on`＝程式重出同一張卡（AP-R3「卡片還在」），
    同樣無新 pending、無新 token、原 pid 可送出。"""
    if proposal == "off":
        monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")
    w = _World()
    _r1, pid1 = await w.repair_card()
    res = await w.turn("就是冷氣不冷", script=[_out("請按卡片上的按鈕確認。")],
                       intents=_correct_intent(description="冷氣不冷"))
    if proposal == "off":
        assert res.outcome["state"] != "confirm_pending", res.answer
        assert "write_draft_reissue_skipped_same_values" in res.trace.violations
    else:
        assert res.outcome["state"] == "confirm_pending", res.answer
        assert res.answer.startswith(WF.CARD_STILL_VALID_TEXT + "\n"), res.answer
        assert res.trace.pending_id == pid1
        assert WF.V_CARD_STILL_VALID in res.trace.violations
    assert list(w.pending()) == [pid1] and w.db.pids(w.session_id) == [pid1]
    assert w.db.live_pids(w.session_id) == [pid1]
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert w.writes() == ["jgb2.action.repair_create"]


async def test_9e_reissued_card_comes_from_the_draft_not_from_pending_payload(api):
    """#9e（S5）：pending payload 裡**非使用者原話**的值（這裡人為塞進去）⛔ 進新草稿／新卡；
    綁定卡的 payload 原樣不動（只標 `invalidated`）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.pending()[pid1]["payload"]["estate_name"] = "竄改的物件"
    w.pending()[pid1]["payload"]["note"] = "非使用者原話"
    before = copy.deepcopy(w.pending()[pid1]["payload"])
    r2 = await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    pid2 = r2.trace.pending_id
    new_payload = w.pending()[pid2]["payload"]
    assert new_payload.get("estate_name") == STUDENT_ESTATE
    assert "note" not in new_payload and "竄改的物件" not in r2.answer
    assert w.draft()["fields"] == {"estate_name": STUDENT_ESTATE, "description": NEW_DESC}
    assert w.pending()[pid1]["payload"] == before                # ⛔ 改 pending 內容


async def test_9f_free_text_send_never_becomes_a_submit(api):
    """#9f（S6）：自由文字「好，送出」⇒ 寫入 0、`redeemed=false`（送出只走按鈕）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    res = await w.turn("好，送出", script=[_out("請按卡片上的「送出」按鈕。")],
                       intents=[_intent("repair_create")])
    assert res.outcome["state"] != "confirmed"
    assert w.writes() == []
    assert w.db.redeemed(pid1) is False
    assert w.db.live_pids(w.session_id) == [pid1]


def _intent_mod(action: str, modifies, **fields):
    """意圖判斷的假回應，帶 #9g 布林欄位（`WF.MODIFIES_SUBMITTED_KEY`）。"""
    return _intent(raw=json.dumps({
        "action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()],
        WF.MODIFIES_SUBMITTED_KEY: modifies}, ensure_ascii=False))


def _mark(w: "_World"):
    return (w.state.get("agent") or {}).get(LAST_SUBMITTED_KEY)


async def _submitted(w: "_World"):
    _r1, pid1 = await w.repair_card()
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    return pid1


@pytest.mark.parametrize("path", ["program_first", "after_output"])
async def test_9g_correction_after_submit_never_reissues(api, path):
    """#9g（業主 2026-10-19 裁定）：送出成功後，AI 判定「修改剛送出的那一筆」（布林 true）⇒ 程式固定句
    `SUBMITTED_EDIT_TEXT`、無新卡（無新 pid）、不建草稿、寫入 1 次、trace 記 violation。
    兩個觸發點（程式優先／輸出後）都擋。"""
    w = _World()
    pid1 = await _submitted(w)
    assert _mark(w) == {"action": "repair_create", "pending_id": pid1, "idle_turns": 0}
    res = await w.turn(CORRECT_TEXT, script=[_out()], program_first=(path == "program_first"),
                       intents=[_intent_mod("repair_create", True, description=NEW_DESC)])
    assert res.answer == WF.SUBMITTED_EDIT_TEXT
    assert res.outcome["state"] == "answered", res.outcome
    assert WF.V_SUBMITTED_EDIT_BLOCKED in res.trace.violations
    assert WF.V_PROGRAM_CONFIRM not in res.trace.violations
    assert res.trace.llm_calls == (0 if path == "program_first" else 1)
    assert w.writes() == ["jgb2.action.repair_create"]           # 寫入 1 次
    assert w.db.pids(w.session_id) == [pid1]                      # 無新 pid
    assert list(w.pending()) == [pid1]
    assert w.draft() is None                                      # 不建草稿
    # 同一句再說一次 ⇒ 同一句回覆（標記保留）
    again = await w.turn(CORRECT_TEXT, script=[_out()],
                         intents=[_intent_mod("repair_create", True, description=NEW_DESC)])
    assert again.answer == WF.SUBMITTED_EDIT_TEXT
    assert w.db.pids(w.session_id) == [pid1]


async def test_9g_positive_control_new_request_same_action_issues_a_card(api):
    """#9g 正對照：送出後明確要另開一筆同動作（布林 false、欄位齊）⇒ 照常收欄位出新卡；標記清掉。"""
    w = _World()
    pid1 = await _submitted(w)
    res = await w.turn(f"{KEELUNG_ESTATE} 另外報修 漏水",
                       intents=[_intent_mod("repair_create", False, estate_name=KEELUNG_ESTATE,
                                            description="漏水")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations
    pid2 = res.trace.pending_id
    assert pid2 and pid2 != pid1 and w.db.live_pids(w.session_id) == [pid2]
    assert _mark(w) is None                                       # 新的一張卡出了 ⇒ 標記清
    ok = await w.turn(f"confirm_submit:{pid2}")
    assert ok.outcome["state"] == "confirmed"
    assert w.writes() == ["jgb2.action.repair_create"] * 2


async def test_9g_other_action_with_true_flag_is_not_blocked(api):
    """#9g：布林 true 但意圖動作 ≠ 標記動作 ⇒ 不擋（照原流程）。"""
    w = _World()
    await _submitted(w)
    res = await w.turn("把基隆那期帳單延 7 天", script=[_out()],
                       intents=[_intent_mod("bill_due_extend", True, days="7")])
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations
    assert res.answer != WF.SUBMITTED_EDIT_TEXT


@pytest.mark.parametrize("write_draft", ["on", "off"])
async def test_9g_mark_written_only_while_write_draft_is_on(api, monkeypatch, write_draft):
    """#9g 標記唯一的讀者是草稿的程式判斷點 ⇒ `AGENT_WRITE_DRAFT=off` 時送出成功 ⛔ 寫標記
    （否則只是多一個下一回合就被清掉的鍵，並改變 golden 的 agent_state 鍵集合）。on＝正對照。"""
    w = _World()
    _r1, pid1 = await w.repair_card()                         # 出卡時草稿機制開著
    monkeypatch.setenv("AGENT_WRITE_DRAFT", write_draft)     # 送出那一回合才切換
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert w.writes() == ["jgb2.action.repair_create"]
    if write_draft == "on":
        assert _mark(w) == {"action": "repair_create", "pending_id": pid1, "idle_turns": 0}
    else:
        assert _mark(w) is None
        assert LAST_SUBMITTED_KEY not in w.state.get("agent", {})


async def test_9g_off_switch_keeps_current_behaviour(api, monkeypatch):
    """#9g 開關 off ⇒ 現行行為：不記標記、schema 無布林欄位、同一句（即使回 true）照常出新卡。"""
    monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    pid1 = await _submitted(w)
    assert _mark(w) is None
    provider = _Provider([_out()], [_intent_mod("repair_create", True, description=NEW_DESC)])
    rt = w.runtime(provider)
    res = await rt.run_turn(w.ident, CORRECT_TEXT, w.state)
    (call,) = provider.intent_calls
    schema = call["response_format"]["json_schema"]["schema"]
    assert WF.MODIFIES_SUBMITTED_KEY not in schema["properties"]
    assert schema["required"] == ["action", "fields"]
    assert WF.MODIFIES_SUBMITTED_RULE not in call["messages"][0]["content"]
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer   # 現行：物件記憶補上 ⇒ 新卡
    assert res.trace.pending_id != pid1


async def test_9g_on_schema_and_prompt_carry_the_boolean(api):
    """#9g：開關 on ⇒ 意圖呼叫實際送出的 schema 有必填布林欄位、系統句含說明句；
    `WRITE_INTENT_NONE_RULE` 仍在系統句結尾（字面不動）。"""
    w = _World()
    provider = _Provider([_out()], [_intent("none")])
    rt = w.runtime(provider)
    await rt.run_turn(w.ident, "謝謝", w.state)
    (call,) = provider.intent_calls
    schema = call["response_format"]["json_schema"]["schema"]
    assert schema["properties"][WF.MODIFIES_SUBMITTED_KEY] == {
        "type": "boolean", "description": WF.MODIFIES_SUBMITTED_RULE}
    assert schema["required"] == ["action", "fields", WF.MODIFIES_SUBMITTED_KEY]
    assert schema["additionalProperties"] is False
    prompt = call["messages"][0]["content"]
    assert WF.MODIFIES_SUBMITTED_RULE in prompt
    assert prompt.endswith(WF.write_intent_description() + "\n" + WF.WRITE_INTENT_NONE_RULE)


def test_9g_off_prompt_and_schema_are_unchanged_composition():
    """off：系統句＝改動前的組法（開頭段＋\n＋說明＋\n＋NONE_RULE，無布林說明句）、schema 無布林欄位。"""
    off = WF.write_intent_system_prompt(enum_labels=False)
    assert WF.MODIFIES_SUBMITTED_RULE not in off
    assert off.endswith("fields 空陣列。\n" + WF.write_intent_description(enum_labels=False)
                        + "\n" + WF.WRITE_INTENT_NONE_RULE)
    sch = WF.write_intent_call_schema(enum_labels=False)
    assert set(sch["properties"]) == {"action", "fields"} and sch["required"] == ["action", "fields"]


@pytest.mark.parametrize("flag", [False, "true", 1, None])
async def test_9g_flag_must_be_exactly_true(api, flag):
    """布林欄位只認恰為 `true`（字串 "true"、1、null、false 一律不算）⇒ 不擋。"""
    w = _World()
    await _submitted(w)
    res = await w.turn(CORRECT_TEXT, script=[_out()],
                       intents=[_intent_mod("repair_create", flag, description=NEW_DESC)])
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations


async def test_9g_mark_cleared_by_idle_turns(api):
    """標記：`DRAFT_IDLE_LIMIT` 個無關回合 ⇒ 清；之後同一句（true）不再擋。"""
    w = _World()
    await _submitted(w)
    for i in range(WF.DRAFT_IDLE_LIMIT):
        assert _mark(w) is not None, i
        res = await w.turn("今天天氣如何", **_chat_turn_args())
    assert _mark(w) is None
    assert WF.V_LAST_SUBMITTED_CLEARED_IDLE in res.trace.violations
    res = await w.turn(CORRECT_TEXT, script=[_out()],
                       intents=[_intent_mod("repair_create", True, description=NEW_DESC)])
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations


async def test_9g_mark_cleared_by_cancel(api):
    """標記：按取消（此處對已送出那張重送取消）⇒ 清；R4.3 receipt 不被覆寫。"""
    w = _World()
    pid1 = await _submitted(w)
    receipt = copy.deepcopy(w.pending()[pid1]["receipt"])
    await w.turn(f"confirm_cancel:{pid1}")
    assert _mark(w) is None
    assert w.pending()[pid1]["receipt"] == receipt


@pytest.mark.parametrize("bad", [
    {"action": "repair_create", "pending_id": "x" * 65, "idle_turns": 0},
    {"action": "not_an_action", "pending_id": "abc", "idle_turns": 0},
    {"action": "repair_create", "pending_id": "abc", "idle_turns": True},
    {"action": "repair_create", "pending_id": "abc", "idle_turns": 0, "token": "t"},
    {"action": "repair_create", "pending_id": "a b", "idle_turns": 0},
    "repair_create",
])
async def test_9g_tampered_mark_is_dropped(api, bad):
    """標記讀回一律不可信：形狀不合 ⇒ 丟棄＋violation、不擋。"""
    w = _World()
    await _submitted(w)
    w.state["agent"][LAST_SUBMITTED_KEY] = bad
    res = await w.turn(CORRECT_TEXT, script=[_out()],
                       intents=[_intent_mod("repair_create", True, description=NEW_DESC)])
    assert WF.V_LAST_SUBMITTED_SHAPE_INVALID in res.trace.violations
    assert WF.V_SUBMITTED_EDIT_BLOCKED not in res.trace.violations


async def test_9g_readonly_view_never_touches_the_mark(api):
    w = _World()
    await _submitted(w)
    before = copy.deepcopy(_mark(w))
    await w.turn("今天天氣如何", readonly_view=True, **_chat_turn_args())
    assert _mark(w) == before


async def test_9g_bound_card_with_receipt_and_leftover_draft_never_reissues(api):
    """#9g 的 A2 閘本身：綁定卡已有 receipt、草稿仍在（以舊狀態補回草稿模擬）⇒ ⛔ 重出卡。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    draft = copy.deepcopy(w.draft())
    await w.turn(f"confirm_submit:{pid1}")
    w.state["agent"][WRITE_DRAFT_KEY] = draft
    res = await w.turn(CORRECT_TEXT, script=[_out()], intents=_correct_intent())
    assert "write_draft_reissue_skipped_has_receipt" in res.trace.violations
    assert res.outcome["state"] != "confirm_pending", res.answer
    assert w.db.pids(w.session_id) == [pid1]
    assert w.writes() == ["jgb2.action.repair_create"]


# ── #9a／#9l 三條出卡路徑各出兩張卡 ─────────────────────────────────
async def _two_cards(w: "_World", path: str):
    if path == "model":
        _a, p1 = await _model_card(w, "冷氣不冷")
        _b, p2 = await _model_card(w, NEW_DESC)
    elif path == "program_first":
        _a, p1 = await w.repair_card()
        b = await w.turn(f"{STUDENT_ESTATE} {NEW_DESC}", intents=[_intent(
            "repair_create", estate_name=STUDENT_ESTATE, description=NEW_DESC)])
        p2 = b.trace.pending_id
    else:
        _a, p1 = await _after_output_card(w, "冷氣不冷")
        _b, p2 = await _after_output_card(w, NEW_DESC)
    assert p1 and p2 and p1 != p2, (p1, p2)
    return p1, p2


@pytest.mark.parametrize("switch", ["on", "off"])
@pytest.mark.parametrize("path", ["model", "program_first", "after_output"])
async def test_9a_9l_two_cards_any_path_first_one_is_dead(api, monkeypatch, path, switch):
    """#9a：三條出卡路徑各出兩張卡、送第一張 ⇒ `CONFIRMATION_REQUIRED_TEXT`、outcome failed、
    寫入 0、DB `redeemed=true`。#9l：開關 off 同樣通過（A7 ⛔ 隨開關關閉）。"""
    if switch == "off":
        monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    p1, p2 = await _two_cards(w, path)
    assert w.db.redeemed(p1) is True
    assert w.db.live_pids(w.session_id) == [p2]
    res = await w.turn(f"confirm_submit:{p1}")
    assert res.answer == CONFIRMATION_REQUIRED_TEXT
    assert res.outcome["state"] == "failed"
    assert w.writes() == []
    ok = await w.turn(f"confirm_submit:{p2}")                      # 正對照：第二張可送出
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert len(w.writes()) == 1


# ── #9n／#9t／#9b′（A7(1) 交易） ───────────────────────────────────
async def test_9n_burn_and_insert_share_one_transaction(api):
    """#9n（含 DSP-092）：鎖、燒舊 token、INSERT 新 token 三句在同一個 `conn.transaction()` 內，
    順序 begin→lock→burn→insert→commit；鎖以本 session_id 取。"""
    w = _World()
    await w.repair_card()
    assert w.db.tx_log == ["begin", "lock", "burn", "insert", "commit"]
    assert w.db.locks == [w.session_id]
    src = __import__("inspect").getsource(C.confirm_request)
    assert "conn.transaction()" in src and "_BURN_SESSION_TOKENS_SQL" in src
    # 原始碼層：交易區塊內第一句是鎖，接著燒、INSERT（防日後把鎖移出交易或移到燒卡之後）
    tx_at = src.index("async with conn.transaction():")
    i_lock = src.index("_LOCK_SESSION_SQL", tx_at)
    i_burn = src.index("_BURN_SESSION_TOKENS_SQL", tx_at)
    i_ins = src.index("_INSERT_TOKEN_SQL", tx_at)
    assert tx_at < i_lock < i_burn < i_ins
    assert src[tx_at:i_lock].count("await ") == 1                  # 只有鎖那一句自己的 await
    assert C._LOCK_SESSION_SQL == "SELECT pg_advisory_xact_lock(hashtext($1))"
    # 第二張卡：同樣三句、同一交易
    w.db.tx_log.clear()
    await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert w.db.tx_log == ["begin", "lock", "burn", "insert", "commit"]


@pytest.mark.parametrize("proposal", ["on", "off"])
@pytest.mark.parametrize("early", ["missing", "candidates"])
async def test_9t_early_exit_confirm_request_never_burns(api, monkeypatch, early, proposal):
    """#9t：回缺欄或候選的 `confirm.request` ⇒ ⛔ 燒（無交易），舊卡仍可兌現。

    A+ 片（改寫，原意圖不變）：`proposal=on` 時模型呼叫只當提議、值須出現在使用者原話——使用者
    句子改為含 payload 的值，程式依草稿發出的呼叫得到同一種早退；`proposal=off`＝改前行為的正對照。"""
    if proposal == "off":
        monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")
    w = _World()
    _r1, pid1 = await w.repair_card()
    log_before = list(w.db.tx_log)
    if early == "missing":
        payload = {"action": "contract_create", "estate_name": STUDENT_ESTATE}
        message = f"{STUDENT_ESTATE} 要開合約"
    else:
        payload = {"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "days": 7}
        message = f"{KEELUNG_ESTATE} 帳單延後 7 天"
    res = await w.turn(message,
                       script=[_call("confirm.request", _confirm_args(payload)), _out()],
                       program_first=False, intents=[_intent("none")])
    confirm_results = [r for n, _a, r in w.reg.results if n == "confirm.request"]
    data = confirm_results[-1].data if isinstance(confirm_results[-1].data, dict) else {}
    if early == "missing":
        assert data.get("missing_fields"), data
    else:
        assert data.get("candidates"), data
    assert w.db.tx_log == log_before
    assert w.db.live_pids(w.session_id) == [pid1]
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    del res


@pytest.mark.parametrize("path", ["model", "model_proposal_off", "program_first"])
async def test_9b_insert_error_rolls_back_and_old_card_stays_live(api, monkeypatch, path):
    """#9b′：INSERT 前注入例外 ⇒ 交易回滾（燒卡也回滾）、舊 pid 仍可兌現、無新 pending。

    A+ 片（改寫，原意圖不變）：`model` 路徑在開關 on 時模型呼叫只當提議、觸發語義同意圖合併——
    回合開始時的同動作草稿會讓它走 A2（先燒綁定卡，那是 #9b A2 版的範圍）；本條驗的是「非 A2 的
    新出卡」，故與 `program_first` 一樣先清草稿。`model_proposal_off`＝改前行為的正對照。"""
    if path == "model_proposal_off":
        monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.insert_error = RuntimeError("boom")
    if path in ("model", "model_proposal_off"):
        if path == "model":
            w.state["agent"].pop(WRITE_DRAFT_KEY, None)           # 新的程式觸發（非 A2）
        await w.turn(f"{KEELUNG_ESTATE} 漏水", script=[_call("confirm.request", _confirm_args(
            _model_repair_payload("漏水", KEELUNG_ESTATE))), _out()], program_first=False,
            intents=[_intent("none")])
    else:
        w.state["agent"].pop(WRITE_DRAFT_KEY, None)               # 新的程式觸發（非 A2）
        await w.turn(f"{KEELUNG_ESTATE} 漏水", script=[_out()], intents=[_intent(
            "repair_create", estate_name=KEELUNG_ESTATE, description="漏水")])
    assert "rollback" in w.db.tx_log
    assert w.db.redeemed(pid1) is False
    assert w.db.pids(w.session_id) == [pid1]
    assert list(w.pending()) == [pid1]
    w.db.insert_error = None
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer


MANUAL_MSG = "幫我開帳單：合約 89481，名稱 管理費，金額 1000，期限 2026/11/30"


async def _manual_bill_card(w: "_World"):
    res = await w.turn(MANUAL_MSG, intents=[_intent(
        "manual_bill_create", contract_ref="89481", title="管理費", total="1000",
        date_expire="2026-11-30")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    return res, res.trace.pending_id


def _program_text_for(early: str, res) -> str:
    """#9b（Q5）：每一種早退使用者看到的**程式固定句**（期望值由常數決定，⛔ 模型自由文字）。"""
    from services.agent import runtime as runtime_mod
    if early == "candidates":
        assert res.answer.startswith(runtime_mod.CONFIRM_CANDIDATES_TEXT), res.answer
        return res.answer
    if early == "missing":
        return C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="問題描述")
    if early == "not_found":
        return runtime_mod.PRE_LOOKUP_NOT_FOUND_TEXT
    return WF.REISSUE_NOT_ISSUED_TEXT


@pytest.mark.parametrize("early", ["no_match", "candidates", "date_before_today", "not_found",
                                   "missing", "render_failure"])
async def test_9b_a2_burn_then_confirm_request_early_exit(api, monkeypatch, early):
    """#9b′（A2）：綁定卡燒掉後 `confirm_request` 早退 ⇒ 舊 pid 兌現失敗、無新 pending、寫入 0，
    且使用者看到的是**程式固定句**（主模型本回合未被呼叫：`llm_calls == 0`）。
    早退種類以 `confirm.request` 回傳形狀自證（NO_MATCH／候選／日期閘 error／查無固定句／缺欄清單／
    render 失敗）。正常流程碰不到的兩種以注入觸發：缺欄＝`confirm` 模組的 `missing_labels` 回一欄；
    render 失敗＝`confirm` 模組的 `render` 拋 `ConfirmCardError`。"""
    from services.agent.confirm_card import ConfirmCardError
    w = _World()
    if early == "no_match":
        _r1, pid1 = await _bill_card(w)
        msg, intent = "改成 1999年1月那期", _intent("bill_due_extend", period="1999年1月那期")
    elif early == "candidates":
        _r1, pid1 = await _bill_card(w)
        msg, intent = "改成 7月那期", _intent("bill_due_extend", period="7月那期")
    elif early == "date_before_today":
        _r1, pid1 = await _manual_bill_card(w)
        msg, intent = "期限改成 2026/10/01", _intent("manual_bill_create", date_expire="2026-10-01")
    elif early == "not_found":
        _r1, pid1 = await w.repair_card()
        msg, intent = "物件改成 不存在的物件甲", _intent("repair_create", estate_name="不存在的物件甲")
    else:
        _r1, pid1 = await w.repair_card()
        msg, intent = CORRECT_TEXT, _correct_intent()[0]
        if early == "missing":
            monkeypatch.setattr(C, "missing_labels", lambda _a, _p: ["問題描述"])
        else:
            def _boom(*_a, **_k):
                raise ConfirmCardError("injected")
            monkeypatch.setattr(C, "render", _boom)
    res = await w.turn(msg, script=[_out(), _out()], intents=[intent])
    assert "write_draft_card_reissue" in res.trace.violations, res.trace.violations
    cr = [r for n, _a, r in w.reg.results if n == "confirm.request"][-1]
    data = cr.data if isinstance(cr.data, dict) else {}
    if early == "no_match":
        assert cr.ok is False and cr.error == "NO_MATCH"
    elif early == "candidates":
        assert data.get("candidates")
    elif early == "date_before_today":
        assert cr.ok is False, (cr.ok, cr.error, data)
    elif early == "missing":
        assert data.get("missing_fields") == ["問題描述"], data
    elif early == "render_failure":
        assert cr.ok is False and cr.error == "INVALID_INPUT" and not data.get("missing_fields")
    else:
        assert "pending_id" not in data, data
    assert res.outcome["state"] != "confirm_pending", res.answer
    # Q5：使用者看到程式固定句（⛔ 空白、⛔ 模型自由文字）；主模型本回合未被呼叫。
    assert res.answer and res.answer.strip()
    assert res.answer == _program_text_for(early, res), res.answer
    assert res.trace.llm_calls == 0
    assert w.db.redeemed(pid1) is True
    assert w.db.pids(w.session_id) == [pid1] and list(w.pending()) == [pid1]
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


async def test_9b_a2_burn_then_insert_exception(api):
    """#9b′（A2）：綁定卡燒掉後 INSERT 例外 ⇒ 舊 pid 兌現失敗、無新 pending、寫入 0；
    使用者看到程式固定句 `REISSUE_NOT_ISSUED_TEXT`（主模型未被呼叫）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.insert_error = RuntimeError("boom")
    res = await w.turn(CORRECT_TEXT, script=[_out(), _out()], intents=_correct_intent())
    assert "rollback" in w.db.tx_log
    assert res.answer == WF.REISSUE_NOT_ISSUED_TEXT
    assert WF.V_REISSUE_NOT_ISSUED in res.trace.violations
    assert res.trace.llm_calls == 0
    assert w.db.redeemed(pid1) is True
    assert w.db.pids(w.session_id) == [pid1] and list(w.pending()) == [pid1]
    w.db.insert_error = None
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []
    # 正對照：同一句再說一次（綁定卡已作廢 ⇒ 不再燒）⇒ 照常出新卡
    again = await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert again.outcome["state"] == "confirm_pending", again.answer


async def test_9b_q5_no_burn_nonterminal_still_goes_back_to_model(api):
    """正對照：沒有 A2 燒卡（新的程式觸發）時非終結結果照現行回模型（Q5 只在燒過綁定卡後生效）。"""
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.state["agent"].pop(WRITE_DRAFT_KEY, None)
    w.db.insert_error = RuntimeError("boom")
    res = await w.turn(f"{KEELUNG_ESTATE} 漏水", script=[_out()], intents=[_intent(
        "repair_create", estate_name=KEELUNG_ESTATE, description="漏水")])
    assert WF.V_PROGRAM_NONTERMINAL in res.trace.violations
    assert WF.V_REISSUE_NOT_ISSUED not in res.trace.violations
    assert res.trace.llm_calls == 1
    assert w.db.redeemed(pid1) is False


# ── #9q 另一 session 同 pending_id 的列 ─────────────────────────────
async def test_9q_a2_burn_never_touches_another_session_row(api):
    w = _World()
    _r1, pid1 = await w.repair_card()
    w.db.rows.append({"token": "other-token", "session_id": "another-session",
                      "payload_sha256": "x", "summary_sha256": "y",
                      "expires_at": w.db.now() + 600, "redeemed": False, "pending_id": pid1})
    r2 = await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert r2.outcome["state"] == "confirm_pending"
    other = next(r for r in w.db.rows if r["session_id"] == "another-session")
    assert other["redeemed"] is False
    assert w.db.redeemed(pid1) is True                            # 正對照：本 session 那列已燒


# ── #9i readonly_view ──────────────────────────────────────────────
async def test_9i_readonly_view_correction_changes_nothing(api):
    """#9i（業主 2026-10-19 變更裁定）：影子回合（`readonly_view`）同一句更正 ⇒ token 表不變，
    agent_state 除 `dialog` 以外全部不變。

    收窄依據：`dialog`（對話歷史）在記憶體 dict 上的附加是**既有**行為，影子呼叫端
    （`services/agent/shadow.py`）對 deepcopy 跑、從不 `save()`；本條比對 `dialog` 以外的
    全部鍵（含 `pending_confirm`、`write_draft`）。正對照：同一句非影子回合會改 token 表與 pending。"""
    w = _World()
    await w.repair_card()
    state_before = copy.deepcopy(w.state)
    rows_before = copy.deepcopy(w.db.rows)
    await w.turn(CORRECT_TEXT, script=[_out()], intents=_correct_intent(), readonly_view=True)
    assert w.db.rows == rows_before
    strip = lambda st: {k: v for k, v in st["agent"].items() if k != "dialog"}   # noqa: E731
    assert strip(w.state) == strip(state_before)
    # 正對照：非影子回合同一句 ⇒ 重出卡（token 表與 pending 都變）
    live = await w.turn(CORRECT_TEXT, intents=_correct_intent())
    assert live.outcome["state"] == "confirm_pending"
    assert w.db.rows != rows_before and strip(w.state) != strip(state_before)


# ── #9aa 清單點選作廢舊卡 ──────────────────────────────────────────
class _RouteVerifier(_RulesVerifier):
    def _verify_routes(self, text):
        return None


async def test_9aa_select_burns_old_card_in_db_and_stale_save_still_fails(api):
    w = _World()
    _r1, pid1 = await w.repair_card()
    stale = copy.deepcopy(w.state)
    provider = _Provider([], None)
    rt = AgentRuntime(provider, w.reg, _RouteVerifier([VerifierVerdict(ok=True)] * 6),
                      FakeAssembler(), Budget(), stage="M1", clock=FakeClock(), db_pool=w.db)
    res = await rt.run_turn(w.ident, "select:bill:709744", w.state)
    assert "709744" in res.answer or res.answer, res.answer
    assert w.pending()[pid1].get("invalidated") is True
    assert w.db.redeemed(pid1) is True                            # DB 同步燒
    # 他回合以**舊狀態**存檔（沒有 invalidated 標記）⇒ 舊 pid 仍兌現失敗
    assert stale["agent"][PENDING_CONFIRM_KEY][pid1].get("invalidated") is not True
    old = await w.turn(f"confirm_submit:{pid1}", state=stale)
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    assert w.writes() == []


# ── #9m／#9r 範圍閘擋下 ─────────────────────────────────────────────
async def test_9m_9r_scope_gate_block_leaves_no_redeemable_card(api):
    """#9m：範圍閘擋下後舊 pid 與新 token 皆無法兌現（`jgb2.action.*` 0 次）。
    #9r：DB 新 token 的 pid 送 `confirm_submit` ⇒ violation `confirm_unknown_pending_id`。"""
    w = _World()
    provider = _Provider([], None)
    rt = AgentRuntime(provider, w.reg, _RouteVerifier([VerifierVerdict(ok=True)] * 6),
                      FakeAssembler(), Budget(), stage="M1", clock=FakeClock(), db_pool=w.db)
    await rt.run_turn(w.ident, "select:bill:709744", w.state)       # 釘住基隆那一戶
    assert w.state["agent"][SELECT_SCOPE_KEY]["estate_id"] == "67652"
    _a, pid1 = await _model_card(w, "漏水", KEELUNG_ESTATE)          # 範圍內 ⇒ 出卡
    assert pid1 and w.db.live_pids(w.session_id) == [pid1]
    blocked = await w.turn(f"{STUDENT_ESTATE} 冷氣不冷", script=[_call(
        "confirm.request", _confirm_args(_model_repair_payload()))], program_first=False)
    assert blocked.trace.pending_id is None
    new_pids = [p for p in w.db.pids(w.session_id) if p != pid1]
    assert len(new_pids) == 1 and new_pids[0] not in w.pending()
    assert w.db.redeemed(pid1) is True                             # 舊卡已燒
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT
    new = await w.turn(f"confirm_submit:{new_pids[0]}")
    assert "confirm_unknown_pending_id" in new.trace.violations
    assert new.outcome["state"] != "confirmed"
    assert w.writes() == []


# ════════════════════════════════════════════════════════════════════
# #6 enum 由程式依表單把標籤轉代碼（A4）
# ════════════════════════════════════════════════════════════════════
def _enum_fields():
    return [(form.action, f) for form in WF.FORMS.values() for f in form.fields if f.kind == "enum"]


def test_6_every_enum_field_declares_labels_from_the_card_source():
    """#6：全部 enum 欄位（目前：修繕急迫程度、建立物件用途）都有與代碼逐位對應的標籤，
    標籤與卡上顯示同源（`confirm_card._EMERGENCY_ZH`／`USE_FOR_ZH`）。"""
    from services.agent import confirm_card as CC
    fields = dict(((a, f.key), f) for a, f in _enum_fields())
    assert set(fields) == {("repair_create", "emergency_status"), ("estate_create", "use_for")}
    em = fields[("repair_create", "emergency_status")]
    assert dict(zip(em.choices, em.choice_labels)) == {str(k): v for k, v in CC._EMERGENCY_ZH.items()}
    uf = fields[("estate_create", "use_for")]
    assert dict(zip(uf.choices, uf.choice_labels)) == dict(CC.USE_FOR_ZH)


def test_6_schema_lists_only_labels_for_enum_fields_when_on():
    """#6：開關 on ⇒ 意圖呼叫的說明對 enum 欄位只列標籤（⛔ 代碼）；off ⇒ 現行列代碼。"""
    on = WF.write_intent_call_schema(enum_labels=True)["description"]
    off = WF.write_intent_call_schema(enum_labels=False)["description"]
    for _action, f in _enum_fields():
        listing_on = f"{f.key}（只能填 {'／'.join(f.choice_labels)}）"
        listing_off = f"{f.key}（只能填 {'／'.join(f.choices)}）"
        assert listing_on in on and listing_off not in on
        assert listing_off in off
    assert WF.write_intent_system_prompt(enum_labels=True) == WF.WRITE_INTENT_SYSTEM_PROMPT


@pytest.mark.parametrize("label,code", [("非緊急", "1"), ("緊急", "2")])
def test_6_label_to_code(label, code):
    em = WF.FORMS["repair_create"].field("emergency_status")
    assert WF.enum_code_for_label(em, label) == code
    uf = WF.FORMS["estate_create"].field("use_for")
    for c, lb in zip(uf.choices, uf.choice_labels):
        assert WF.enum_code_for_label(uf, lb) == c
    for bad in ("1", "2", "不急", "很急", "", "residential"):
        assert WF.enum_code_for_label(em, bad) is None
        assert WF.enum_code_for_label(uf, bad) is None


async def test_6_runtime_sends_label_schema_and_card_shows_converted_code(api):
    """#6：意圖呼叫實際送出的系統句列標籤；意圖回標籤「非緊急」（W-R2 k1 型：使用者說「不急」）
    ⇒ 草稿存代碼 "1"、卡上「非緊急」；回「緊急」⇒ 卡上「緊急」。"""
    for label, shown in (("非緊急", "・急迫程度：非緊急"), ("緊急", "・急迫程度：緊急")):
        w = _World()
        res = await w.turn(f"{STUDENT_ESTATE} 冷氣不冷，不急", intents=[_intent(
            "repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷",
            emergency_status=label)])
        assert res.outcome["state"] == "confirm_pending", res.answer
        assert shown in res.answer
        assert w.draft()["fields"]["emergency_status"] == WF.enum_code_for_label(
            WF.FORMS["repair_create"].field("emergency_status"), label)


async def test_6_intent_system_prompt_on_wire_lists_labels(api):
    w = _World()
    provider = _Provider([_out()], [_intent("none")])
    rt = w.runtime(provider)
    await rt.run_turn(w.ident, "謝謝", w.state)
    (call,) = provider.intent_calls
    assert call["messages"][0]["content"] == WF.write_intent_system_prompt(enum_labels=True)
    assert "emergency_status（只能填 非緊急／緊急）" in call["messages"][0]["content"]


@pytest.mark.parametrize("value", ["2", "不急", "很急"])
async def test_6_non_label_value_is_missing_and_never_becomes_a_code(api, value):
    """#6：非標籤值（含直接填代碼、近義詞）⇒ 視為缺值（`write_intent_value_out_of_domain`）；
    急迫程度非必填 ⇒ 由既有預設補「非緊急」（卡上明示），⛔ 由模型填的代碼決定。"""
    w = _World()
    res = await w.turn(f"{STUDENT_ESTATE} 冷氣不冷，{value}", intents=[_intent(
        "repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷",
        emergency_status=value)])
    assert "write_intent_value_out_of_domain" in res.trace.violations
    assert "emergency_status" not in w.draft()["fields"]
    assert "・急迫程度：非緊急" in res.answer


async def test_6_required_enum_non_label_is_asked_per_form(api):
    """#6「照表單追問」：必填 enum（建立物件「用途」）給非標籤值 ⇒ 缺欄追問列「用途」。"""
    w = _World()
    res = await w.turn("幫我建立物件，用途 residential", script=[_out()], intents=[_intent(
        "estate_create", use_for="residential")])
    assert "write_intent_value_out_of_domain" in res.trace.violations
    assert "use_for" not in (w.draft() or {}).get("fields", {})
    assert "confirm_missing_fields_ask" in res.trace.violations
    assert "用途" in res.answer


async def test_6_off_switch_keeps_code_values(api, monkeypatch):
    monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    res = await w.turn(f"{STUDENT_ESTATE} 冷氣不冷，很急", intents=[_intent(
        "repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷", emergency_status="2")])
    assert "・急迫程度：緊急" in res.answer


# ════════════════════════════════════════════════════════════════════
# #9k 出卡前預檢（A6）＋ RC1 兌現端單筆探測
# ════════════════════════════════════════════════════════════════════
def _bill_payload(bill_id: str, **extra) -> dict:
    return {"action": "bill_due_extend", "bill_id": bill_id, "days": 7, **extra}


def _write_calls(api) -> list:
    return [(m, p) for m, p, _params in api._mock_transport.calls if str(m).upper() != "GET"]


async def _model_bill_turn(w: "_World", payload: dict):
    return await w.turn(f"帳單 {payload['bill_id']} 延 7 天",
                        script=[_call("confirm.request", _confirm_args(payload)), _out()],
                        program_first=False, intents=[_intent("none")])


async def test_9k_other_household_bill_reads_exactly_like_a_missing_one(api):
    """#9k：別戶帳單（709744 存在、但這位成員看不到）與不存在的編號 ⇒ 回答逐字相同、
    `confirm.request` 結果相同、寫入端點 0、無 token。"""
    stranger = _pm(user="99999")
    w1, w2 = _World(stranger), _World(stranger)
    r_other = await _model_bill_turn(w1, _bill_payload("709744"))
    r_none = await _model_bill_turn(w2, _bill_payload("99999999"))
    c_other = [r for n, _a, r in w1.reg.results if n == "confirm.request"][-1]
    c_none = [r for n, _a, r in w2.reg.results if n == "confirm.request"][-1]
    assert (c_other.ok, c_other.error, c_other.text_for_model) == (
        c_none.ok, c_none.error, c_none.text_for_model) == (False, "NO_MATCH", jgb2_tools.NOT_FOUND_TEXT)
    assert r_other.answer == r_none.answer
    assert w1.db.rows == [] and w2.db.rows == []
    assert _write_calls(api) == []
    # 正對照：看得到的那位成員同一張帳單 ⇒ 出卡
    w3 = _World()
    ok = await _model_bill_turn(w3, _bill_payload("709744"))
    assert ok.outcome["state"] == "confirm_pending", ok.answer
    # 預檢只用帶 viewer 的單筆讀
    probes = [params for m, p, params in api._mock_transport.calls
              if p.endswith("/bills") and (params or {}).get("bill_id") is not None]
    assert probes and all(params.get("viewer_user_id") for params in probes)


async def test_9k_numbered_card_original_due_date_is_the_viewer_read_value(api):
    """#9k／F8：有編號的延期卡，模型填的原／新到期日一律被 viewer 讀到的列重算。"""
    w = _World()
    res = await _model_bill_turn(w, _bill_payload(
        "709744", date_expire_before="20990101", date_expire_after="20990108"))
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・原到期日：2026/11/01" in res.answer and "2099" not in res.answer
    assert "・新到期日：2026/11/08" in res.answer
    pid = res.trace.pending_id
    assert w.pending()[pid]["payload"]["date_expire_before"] == "20261101"


async def test_9k_off_switch_numbered_card_skips_the_precheck(api, monkeypatch):
    """開關 off ⇒ 現行：有編號、無日期的 payload 不預檢（render 缺欄 ⇒ INVALID_INPUT）。"""
    monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    await _model_bill_turn(w, _bill_payload("709744"))
    c = [r for n, _a, r in w.reg.results if n == "confirm.request"][-1]
    assert (c.ok, c.error) == (False, "INVALID_INPUT")
    assert not [params for _m, p, params in api._mock_transport.calls
                if p.endswith("/bills") and (params or {}).get("bill_id") is not None]


@pytest.mark.parametrize("switch", ["on", "off"])
async def test_rc1_bill_beyond_the_first_page_can_be_redeemed(api, monkeypatch, switch):
    """A0 RC1（⛔ 掛開關）：viewer 可見第 50 名以後的帳單（709740）送出不再 `NO_MATCH`；
    兌現端可見性以 `bill_id`＋`viewer_user_id` 單筆探測。"""
    if switch == "off":
        monkeypatch.setenv(LIFECYCLE_ENV, "off")
    w = _World()
    payload = _bill_payload("709740")
    if switch == "off":                                # off：模型自己給齊日期（現行出卡路徑）
        payload.update(date_expire_before="20260701", date_expire_after="20261024")
    res = await _model_bill_turn(w, payload)
    assert res.outcome["state"] == "confirm_pending", res.answer
    pid = res.trace.pending_id
    ok = await w.turn(f"confirm_submit:{pid}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert w.writes() == ["jgb2.action.bill_due_extend"]
    probes = [params for _m, p, params in api._mock_transport.calls
              if p.endswith("/bills") and (params or {}).get("bill_id") == "709740"]
    assert probes and all(params.get("viewer_user_id") == "12291" for params in probes)


async def test_rc1_get_bills_forwards_bill_id_only_when_present(api):
    await api.get_bills(role_id="20151", user_id="12291", viewer_user_id="12291", bill_id="709740")
    await api.get_bills(role_id="20151", user_id="12291", viewer_user_id="12291", keyword="基隆")
    (_m1, _p1, first), (_m2, _p2, second) = api._mock_transport.calls[-2:]
    assert first["bill_id"] == "709740"
    assert "bill_id" not in second                       # 正對照：沒給就不送


async def test_rc1_premise_709740_is_not_on_the_first_page(api):
    """RC1 前提自證：舊寫法（只讀 viewer 列表第一頁）看不到 709740——上面那條不是恆真。"""
    rows = jgb2_tools._rows_of(await api.get_bills(
        role_id="20151", user_id="12291", viewer_user_id="12291"))
    ids = {str(r.get("id")) for r in rows}
    assert "709744" in ids or len(ids) > 0
    assert "709740" not in ids
