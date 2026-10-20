"""unit：主線第 3 步 #2——「新增一支寫入動作只要登錄，不改流程」的假動作測試。

凍結驗收清單 `.kiro/specs/agentic-mcp-orchestration/acceptance-conversation-architecture-step3-20261018.md`
#2：假動作**只**以本測試自身註冊或 patch 加入下列登錄——
  - `write_forms.FORMS`（含一個宣告出卡前預檢 `FormPrecheck` 的假表單）；
  - `confirm_card.CONFIRM_ACTIONS`、`confirm_card._RENDERERS`、`confirm_card.CONFIRM_FIELD_ATTRS`；
  - 測試自建 `ToolRegistry` 以 `register()` 註冊的假寫入工具 `jgb2.action.<假動作>`；
⛔ patch 任何流程函式（runtime／confirm.request／兌現段一律走正式碼）。
走完：收欄位（缺欄追問）→ 出卡（預檢重算系統欄位、enum 標籤轉代碼）→ 更正（A2 燒綁定卡、
重出卡）→ 送出／取消；另含預檢查無（看不到＝不存在同一句、零 token）、送出後「修改剛送出的那一筆」
（#9g：程式固定句、無新卡；正對照另開一筆照常出卡）。

「DB」＝`tests.unit.agent.token_db_double.FakeTokenDB`（同 `test_step3_write_lifecycle_req.py`）。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from services.agent import confirm_card as CC
from services.agent import mcp_facade as F
from services.agent import write_forms as WF
from services.agent.agent_session import LAST_SUBMITTED_KEY, PENDING_CONFIRM_KEY, WRITE_DRAFT_KEY
from services.agent.budget import Budget
from services.agent.confirm_card import CANCELLED_TEXT, CONFIRMATION_REQUIRED_TEXT
from services.agent.runtime import AgentRuntime
from services.agent.tools import confirm as C
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.jgb import bills as _bills

from tests.unit.agent.test_runtime_req import FakeAssembler, FakeClock, VerifierVerdict
from tests.unit.agent.test_write_draft_flow_req import _intent, _out, _pm, _Provider, _RulesVerifier
from tests.unit.agent.token_db_double import FakeTokenDB

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-conversation-architecture-step3-A")]

TODAY = date(2026, 10, 17)
FAKE = "fake_note"
FAKE_TOOL = f"jgb2.action.{FAKE}"
OWNER_NAME = "王小明"           # 預檢讀到的列上的值（系統欄位，使用者從沒講過）
VISIBLE_REF = "5"
HIDDEN_REF = "6"


# ---------------------------------------------------------------------------
# 假動作的登錄（只有資料與宣告；⛔ 流程函式）
# ---------------------------------------------------------------------------
class _Lookups:
    """預檢宣告的帶 viewer 唯讀查詢替身：記下每次呼叫的 (role_id, user_id, ref)。"""

    def __init__(self):
        self.calls: list = []

    async def __call__(self, api, role_id, user_id, ref):
        self.calls.append((role_id, user_id, str(ref)))
        if str(ref) == VISIBLE_REF:
            return "one", {"id": int(VISIBLE_REF), "owner": OWNER_NAME}
        return "none", None


def _derive(payload: dict, row: dict, *, today: date) -> bool:
    owner = row.get("owner")
    if not isinstance(owner, str) or not owner:
        return False
    payload["note_owner"] = owner
    return True


def _fake_form(lookup) -> WF.WriteForm:
    return WF.WriteForm(
        action=FAKE,
        title_zh="建立測試便條",
        fields=(
            WF.FormField("note_ref", "便條編號", "int"),
            WF.FormField("note_text", "便條內容", "text", max_len=100),
            WF.FormField("remind_on", "提醒日", "date"),
            WF.FormField("level", "便條等級", "enum", choices=("1", "2"), payload_type="int",
                         choice_labels=("普通", "重要")),
            WF.FormField("note_owner", "便條所屬", "text", source=WF.SOURCE_SYSTEM),
        ),
        requirements=(
            WF.Requirement(required_any_of=(("note_ref",),), ask_group=("note_ref",)),
            WF.Requirement(required_any_of=(("note_text",),), ask_group=("note_text",)),
            WF.Requirement(required_any_of=(("remind_on",),), ask_group=("remind_on",)),
        ),
        presence=WF.PRESENCE_GIVEN,
        precheck=WF.FormPrecheck(id_key="note_ref", lookup=lookup, derive=_derive,
                                 derived_keys=("note_owner",)),
    )


_LEVEL_ZH = {1: "普通", 2: "重要"}


def _render_fake(payload, today):
    text = CC._require_text(payload, "note_text", FAKE)
    ref = CC._require_ref(payload, "note_ref", FAKE)
    remind = CC._parse_date(payload.get("remind_on"), "remind_on", FAKE)
    owner = CC._require_text(payload, "note_owner", FAKE)
    level = _LEVEL_ZH.get(payload.get("level"), "普通")
    return CC._lines_to_card("請確認建立便條", [
        ("便條編號", ref), ("便條內容", text), ("提醒日", CC._fmt_date(remind)),
        ("便條等級", level), ("便條所屬", owner),
    ])


class _FakeWriteTool:
    def __init__(self):
        self.payloads: list = []

    async def __call__(self, identity, args):
        self.payloads.append(dict(args.get("payload") or {}))
        return ToolResult(ok=True, data={"receipt": {"id": "N1"}})


def _fake_spec() -> dict:
    return {
        "name": FAKE_TOOL,
        "description": "建立一張測試便條（只存在於本測試）。",
        "input_schema": {
            "type": "object",
            "properties": {"payload": {"type": "object"}, "confirmation_token": {"type": "string"}},
            "required": ["payload", "confirmation_token"],
            "additionalProperties": False,
        },
        "scope": "write",
        "mcp_only": True,
        "stage": {"property_manager": "M1"},
    }


class _Reg:
    """測試自建登錄表：先 `register()` 假寫入工具，再接上正式 `mcp_facade.build_registry`。"""

    def __init__(self, db, write_tool):
        reg = ToolRegistry()
        reg.register(_fake_spec(), write_tool)
        self.inner = F.build_registry(F.FacadeDeps(get_db_pool=lambda: db, stage="M1"), registry=reg)
        self.results: list = []

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        return self.inner.to_openai_tools(identity, stage, readonly_view=readonly_view)

    def specs_for(self, *a, **kw):
        return self.inner.specs_for(*a, **kw)

    async def call(self, identity, name, args, timeout_s, **kw):
        result = await self.inner.call(identity, name, args, timeout_s, **kw)
        self.results.append((name, args, result))
        return result


@pytest.fixture()
def world(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)
    monkeypatch.delenv("AGENT_WRITE_DRAFT", raising=False)
    monkeypatch.delenv(WF.WRITE_LIFECYCLE_ENV, raising=False)          # 未設＝on
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    lookup = _Lookups()
    # ── 登錄（#2 允許的四份＋自建 registry）──────────────────────────────
    monkeypatch.setitem(WF.FORMS, FAKE, _fake_form(lookup))
    monkeypatch.setattr(CC, "CONFIRM_ACTIONS", CC.CONFIRM_ACTIONS + (FAKE,))
    monkeypatch.setitem(CC._RENDERERS, FAKE, _render_fake)
    monkeypatch.setitem(CC.CONFIRM_FIELD_ATTRS, FAKE, {"remind_on": frozenset({CC.NOT_BEFORE_TODAY})})
    return _World(lookup)


class _World:
    def __init__(self, lookup):
        self.lookup = lookup
        self.ident = _pm()
        self.db = FakeTokenDB()
        self.tool = _FakeWriteTool()
        self.reg = _Reg(self.db, self.tool)
        self.state: dict = {}

    async def turn(self, message, *, intents=None, script=()):
        provider = _Provider(list(script), intents)
        rt = AgentRuntime(provider, self.reg, _RulesVerifier([VerifierVerdict(ok=True)] * 6),
                          FakeAssembler(), Budget(), stage="M1", clock=FakeClock(), db_pool=self.db)
        res = await rt.run_turn(self.ident, message, self.state)
        if not script:
            assert provider.calls == [], "主模型不該被呼叫（程式優先）"
        return res

    def draft(self):
        return (self.state.get("agent") or {}).get(WRITE_DRAFT_KEY)

    def pending(self) -> dict:
        return (self.state.get("agent") or {}).get(PENDING_CONFIRM_KEY) or {}

    def writes(self) -> list:
        return [n for n, _a, _r in self.reg.results if n.startswith("jgb2.action.")]


MSG_1 = "幫我建一張重要的便條：編號 5，內容 換燈泡"
MSG_2 = "提醒日 2026/11/30"
MSG_FIX = "內容改成修水龍頭"


async def _to_card(w: _World):
    """收欄位（缺「提醒日」⇒ 程式追問）→ 補上 ⇒ 出卡。"""
    r1 = await w.turn(MSG_1, intents=[_intent(FAKE, note_ref="5", note_text="換燈泡", level="重要")])
    assert r1.outcome["state"] == "clarifying", r1.answer
    assert r1.answer == C.MISSING_FIELDS_ASK_TEMPLATE.format(labels="提醒日")
    assert w.draft()["action"] == FAKE and w.db.rows == []
    r2 = await w.turn(MSG_2, intents=[_intent(FAKE, remind_on="2026-11-30")])
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    return r2, r2.trace.pending_id


async def test_2_fake_action_collect_card_correct_submit(world):
    w = world
    r2, pid1 = await _to_card(w)
    # 出卡：預檢以 viewer（本人 user_id）讀那一筆、系統欄位由讀到的列重算；enum 標籤 → 代碼 → 卡上標籤
    assert w.lookup.calls and all(c[1] == w.ident.user_id and c[2] == VISIBLE_REF for c in w.lookup.calls)
    assert f"・便條所屬：{OWNER_NAME}" in r2.answer
    assert "・便條等級：重要" in r2.answer and "・提醒日：2026/11/30" in r2.answer
    assert w.pending()[pid1]["payload"]["level"] == 2
    assert w.pending()[pid1]["payload"]["note_owner"] == OWNER_NAME
    assert w.draft() is not None                                   # A1：出卡保留草稿
    assert w.db.live_pids(w.ident.session_id) == [pid1]
    # 更正 ⇒ A2：燒綁定卡、由草稿重出卡
    r3 = await w.turn(MSG_FIX, intents=[_intent(FAKE, note_text="修水龍頭")])
    assert r3.outcome["state"] == "confirm_pending", r3.answer
    pid2 = r3.trace.pending_id
    assert pid2 and pid2 != pid1 and "write_draft_card_reissue" in r3.trace.violations
    assert "・便條內容：修水龍頭" in r3.answer and f"・便條所屬：{OWNER_NAME}" in r3.answer
    assert w.db.redeemed(pid1) is True and w.db.live_pids(w.ident.session_id) == [pid2]
    # 舊卡送出 ⇒ 失效句、零寫入；新卡送出 ⇒ 正式兌現段呼叫假寫入工具恰一次
    old = await w.turn(f"confirm_submit:{pid1}")
    assert old.answer == CONFIRMATION_REQUIRED_TEXT and w.writes() == []
    new = await w.turn(f"confirm_submit:{pid2}")
    assert new.outcome["state"] == "confirmed", new.answer
    assert w.writes() == [FAKE_TOOL]
    assert w.tool.payloads == [w.pending()[pid2]["payload"]]
    assert w.tool.payloads[0]["note_text"] == "修水龍頭"
    assert w.draft() is None                                       # A1：送出成功清草稿


async def test_2_fake_action_cancel(world):
    w = world
    _r2, pid = await _to_card(w)
    res = await w.turn(f"confirm_cancel:{pid}")
    assert res.answer == CANCELLED_TEXT
    assert w.writes() == [] and w.draft() is None and w.db.redeemed(pid) is True


async def test_2_fake_action_precheck_hidden_reads_like_missing(world):
    """宣告的預檢查無 ⇒ 查無固定句（看不到＝不存在同一句）、零 token、零寫入。"""
    w = world
    await w.turn(MSG_1.replace("編號 5", f"編號 {HIDDEN_REF}"),
                 intents=[_intent(FAKE, note_ref=HIDDEN_REF, note_text="換燈泡", level="重要")])
    res = await w.turn(MSG_2, intents=[_intent(FAKE, remind_on="2026-11-30")],
                       script=[_out(), _out()])
    assert res.trace.pending_id is None and res.outcome["state"] != "confirm_pending"
    assert w.lookup.calls and w.lookup.calls[-1][2] == HIDDEN_REF
    cr = [r for n, _a, r in w.reg.results if n == "confirm.request"][-1]
    nf = C._not_found_result()
    assert (cr.ok, cr.error, cr.text_for_model) == (nf.ok, nf.error, nf.text_for_model)
    assert w.db.rows == [] and w.writes() == [] and w.pending() == {}


def _intent_mod(action: str, modifies: bool, **fields):
    return _intent(raw=json.dumps({
        "action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()],
        WF.MODIFIES_SUBMITTED_KEY: modifies}, ensure_ascii=False))


async def test_2_fake_action_submitted_edit_is_blocked_and_new_one_still_works(world):
    """#2 × #9g：假動作送出後，AI 判「修改剛送出的那一筆」⇒ 程式固定句、無新卡、寫入 1 次；
    正對照：明確另開一筆同動作（布林 false、欄位齊）⇒ 照常出新卡。流程與真動作同一套（只靠登錄）。"""
    w = world
    _r2, pid1 = await _to_card(w)
    ok = await w.turn(f"confirm_submit:{pid1}")
    assert ok.outcome["state"] == "confirmed", ok.answer
    assert w.state["agent"][LAST_SUBMITTED_KEY] == {"action": FAKE, "pending_id": pid1, "idle_turns": 0}
    res = await w.turn(MSG_FIX, intents=[_intent_mod(FAKE, True, note_text="修水龍頭")])
    assert res.answer == WF.SUBMITTED_EDIT_TEXT
    assert WF.V_SUBMITTED_EDIT_BLOCKED in res.trace.violations
    assert w.writes() == [FAKE_TOOL] and w.db.pids(w.ident.session_id) == [pid1]
    assert w.draft() is None
    # 正對照：另開一筆（欄位齊）⇒ 新卡
    new = await w.turn("再建一張便條：編號 5，內容 倒垃圾，提醒日 2026/11/30，普通",
                       intents=[_intent_mod(FAKE, False, note_ref="5", note_text="倒垃圾",
                                            remind_on="2026-11-30", level="普通")])
    assert new.outcome["state"] == "confirm_pending", new.answer
    assert new.trace.pending_id not in (None, pid1)
    assert LAST_SUBMITTED_KEY not in w.state["agent"]


def test_2_registrations_are_the_only_patch_points():
    """前提自證：未 patch 時假動作不在任何登錄裡（測試只靠登錄把它加進來）。"""
    assert FAKE not in WF.FORMS and FAKE not in CC.CONFIRM_ACTIONS
    assert FAKE not in CC._RENDERERS and FAKE not in CC.CONFIRM_FIELD_ATTRS
    # 追問詞彙的 import 期快照沒有假表單的標籤 ⇒ 上面「缺提醒日」的程式追問證明詞彙是呼叫當下導出
    assert "提醒日" not in WF.MISSING_LABEL_VOCAB and "提醒日" not in WF.missing_label_vocab()
