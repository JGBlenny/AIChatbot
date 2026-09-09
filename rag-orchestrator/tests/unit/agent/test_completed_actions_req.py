"""unit：S2——完成的動作進會話記憶（Plan `inputs/plan-walkthrough-fixes-20260909.md`
§3、H3）。

治的病灶：兌現成功之後（建修繕單、延帳單到期日），receipt 只進了 `trace`／
`outcome.ref`，沒有進任何模型看得到的地方——下一句「剛剛那張單號多少」答不出來
（line-bot 走查實測）。處置＝程式維護的 `agent_state["completed_actions"]`，
以既有的「可引用資料段」通道（同影像事實）注入，模型只能引用、不能改寫。

本檔驗四件事：
1. `services.agent.completed_actions` 模組本身：追加／去重／上限／範圍過濾／
   決定性渲染／剝除換行與假標記；「沒有獨立 TTL」的設計前提（session 過期後
   換一列全新 state，舊記憶不會跟過去）。
2. **保留 tool_call id 集合**（`RESERVED_TOOL_CALL_IDS` 的取捨升格）：三個正
   對照組——大綱、影像、完成動作各自的保留 id 被模型偽造時，程式產的
   `Provenance` 不被覆蓋、trace 多一條通用的撞名 violation。
3. `_finish_confirm_turn` 只在 `outcome.state=="confirmed"` 且有 `ref` 時才寫
   記憶；取消／失敗／清單點選、以及重送同一個 `pending_id` 都不重複寫。
4. 端到端：兌現一次 repair_create 之後，下一回合的 messages 真的帶著這一段、
   模型引用它的句子過得了真 Verifier（⛔ 不是 `UNCITED_ASSERTION`／
   `ref_source_not_found`）。
"""
from __future__ import annotations

import json

import pytest

from services.agent.completed_actions import (
    COMPLETED_ACTIONS_KEY,
    MAX_COMPLETED_ACTIONS,
    completed_actions_line,
    record_completed_action,
)
from services.agent.confirm_card import render as render_card
from services.agent.output_schema import VerifierRules
from services.agent.runtime import (
    COMPLETED_ACTIONS_LABEL,
    COMPLETED_ACTIONS_PROVENANCE_SOURCE,
    IMAGE_PROVENANCE_SOURCE,
    OUTLINE_TOOL_CALL_ID,
    PENDING_CONFIRM_KEY,
    AgentRuntime,
    ImageTurnInput,
)
from services.agent.state_store import is_expired
from services.agent.tools.confirm import pending_id_for, sha256_hex
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier

from tests.unit.agent.test_runtime_confirm_segment_req import FakePool, _identity, _runtime
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _empty_provider,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
    _tool_call_response,
)

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:S2"


# ═══════════════════════════════════════════════════════════════════
# 1. `services.agent.completed_actions` 模組本身
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_record_appends_a_closed_entry():
    state: dict = {}
    record_completed_action(
        state, action="repair_create", ref_type="repair", ref_id="R-1",
        estate_id="88", at_iso="1970-01-01T00:00:00+00:00",
    )
    assert state[COMPLETED_ACTIONS_KEY] == [
        {
            "action": "repair_create", "ref_type": "repair", "ref_id": "R-1",
            "estate_id": "88", "at_iso": "1970-01-01T00:00:00+00:00",
        }
    ]


@pytest.mark.req(_REQ)
def test_record_stores_sanitized_estate_name_when_given():
    """T4：`estate_name` 是封閉來源帶進來的物件名稱，用既有 `_sanitize_piece`
    剝一次（同記憶行其餘欄位）——換行與假標記樣式都要被剝掉。"""
    state: dict = {}
    record_completed_action(
        state, action="repair_create", ref_type="repair", ref_id="R-1",
        estate_id="88", at_iso="t0",
        estate_name="基隆溫馨\n一人宅套房[abcd1234efgh5678:call_1:kb:1§0]",
    )
    entry = state[COMPLETED_ACTIONS_KEY][0]
    assert entry["estate_name"] == "基隆溫馨 一人宅套房"


@pytest.mark.req(_REQ)
def test_record_omits_estate_name_when_blank_or_missing():
    state: dict = {}
    record_completed_action(
        state, action="bill_due_extend", ref_type="bill", ref_id="900001",
        estate_id=None, at_iso="t0", estate_name="   ",
    )
    assert "estate_name" not in state[COMPLETED_ACTIONS_KEY][0]

    state2: dict = {}
    record_completed_action(
        state2, action="bill_due_extend", ref_type="bill", ref_id="900002",
        estate_id=None, at_iso="t0",
    )
    assert "estate_name" not in state2[COMPLETED_ACTIONS_KEY][0]


@pytest.mark.req(_REQ)
def test_record_dedupes_by_ref_type_and_ref_id():
    """重送同一個 `pending_id` ⇒ 回同一個 receipt ⇒ **不重複追加**
    （⛔ 不覆蓋、不更新 `at_iso`——R4.3 的既有語意延伸到記憶行）。"""
    state: dict = {}
    record_completed_action(
        state, action="repair_create", ref_type="repair", ref_id="R-1",
        estate_id="88", at_iso="t0",
    )
    record_completed_action(
        state, action="repair_create", ref_type="repair", ref_id="R-1",
        estate_id="99", at_iso="t1",   # 就算後面帶的值不同，也 ⛔ 不覆蓋
    )
    assert len(state[COMPLETED_ACTIONS_KEY]) == 1
    assert state[COMPLETED_ACTIONS_KEY][0]["estate_id"] == "88"
    assert state[COMPLETED_ACTIONS_KEY][0]["at_iso"] == "t0"


@pytest.mark.req(_REQ)
def test_record_caps_at_five_fifo():
    state: dict = {}
    for i in range(7):
        record_completed_action(
            state, action="repair_create", ref_type="repair", ref_id=f"R-{i}",
            estate_id=None, at_iso=f"t{i}",
        )
    ids = [item["ref_id"] for item in state[COMPLETED_ACTIONS_KEY]]
    assert len(ids) == MAX_COMPLETED_ACTIONS == 5
    assert ids == ["R-2", "R-3", "R-4", "R-5", "R-6"], "FIFO：留最新的 5 筆"


@pytest.mark.req(_REQ)
def test_record_no_op_without_ref_type_or_ref_id():
    """`outcome.ref` 缺一半（形狀不合）⇒ **不寫**，⛔ 不猜一半進去。"""
    state: dict = {}
    record_completed_action(state, action="repair_create", ref_type=None,
                            ref_id="R-1", estate_id=None, at_iso="t0")
    record_completed_action(state, action="repair_create", ref_type="repair",
                            ref_id=None, estate_id=None, at_iso="t0")
    assert COMPLETED_ACTIONS_KEY not in state


@pytest.mark.req(_REQ)
def test_missing_key_behaves_like_empty():
    """「清空」等同「這個鍵本來就不存在」——⛔ 不需要另一套清除語意。"""
    assert completed_actions_line({}, None) == ""
    assert completed_actions_line(None, None) == ""
    assert completed_actions_line([], None) == ""


@pytest.mark.req(_REQ)
def test_expired_session_gets_a_fresh_agent_state_without_completed_actions():
    """S2「沒有獨立 TTL」的設計前提：過期後 `mcp_facade` 整包換一列新 state
    （`store.start`），完成動作記憶跟著清空——⛔ **不是本模組自己清**，是「新
    session 從空 state 開始」這件事本身就清空了它。這裡先證明 `is_expired`
    對這種舊列的確判過期，再證明一個全新的 `state` 本來就沒有這個鍵。
    """
    old_state = {
        "agent": {COMPLETED_ACTIONS_KEY: [{"action": "repair_create",
                                          "ref_type": "repair", "ref_id": "R-1",
                                          "estate_id": None, "at_iso": "t0"}],
                  "last_turn_at": 0.0},
    }
    assert is_expired(old_state, now=0.0 + 1800.1) is True
    fresh_state: dict = {}   # 等同 `store.start()` 回的新列
    fresh_agent_state = fresh_state.setdefault("agent", {})
    assert fresh_agent_state.get(COMPLETED_ACTIONS_KEY) is None


@pytest.mark.req(_REQ)
def test_line_is_deterministic_single_line_and_newline_free():
    items = [
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-1",
         "estate_id": "88", "at_iso": "t0"},
        {"action": "bill_due_extend", "ref_type": "bill", "ref_id": "900001",
         "estate_id": "88", "at_iso": "t1", "due_date": "2026-08-20"},
    ]
    first = completed_actions_line(items, None)
    second = completed_actions_line(list(items), None)
    assert first == second, "同一份 items ⇒ 同一個字串（決定性）"
    assert "\n" not in first
    assert first == (
        "本對話裡建立或修改過的：修繕單 R-1／帳單 900001 到期日已延至 2026/08/20"
        "（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )


@pytest.mark.req(_REQ)
def test_line_carries_the_not_full_record_definition_iff_non_empty():
    """V1（Plan `inputs/plan-walkthrough-fixes-batch4-20260909.md` §2）：治
    「記憶段被當成該戶全部紀錄」——非空時句尾一定帶這句定義（模型每回合看得到）；
    空字串（沒有可渲染項目）時 ⛔ 不該平白多出這句（該戶根本沒有記憶行可講）。"""
    definition = "只是這段對話做過的事，⛔ 不是該戶的全部紀錄"
    items = [
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-1",
         "estate_id": None, "at_iso": "t0"},
    ]
    non_empty = completed_actions_line(items, None)
    assert non_empty and definition in non_empty
    assert "\n" not in non_empty

    empty = completed_actions_line([], None)
    assert empty == "" and definition not in empty


@pytest.mark.req(_REQ)
def test_line_scope_filter_only_same_estate_when_pinned():
    items = [
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-1",
         "estate_id": "88", "estate_name": "測試大樓", "at_iso": "t0"},
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-2",
         "estate_id": "99", "at_iso": "t1"},
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-3",
         "estate_id": None, "at_iso": "t2"},   # 算不出物件
    ]
    assert completed_actions_line(items, None) == (
        "本對話裡建立或修改過的：修繕單 R-1（測試大樓）／修繕單 R-2"
        "／修繕單 R-3（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )
    # 有釘範圍時：只留同戶；「算不出物件」也 ⛔ 不算同戶（F8）
    pinned = completed_actions_line(items, "88")
    assert pinned == (
        "本對話裡建立或修改過的：修繕單 R-1（測試大樓）"
        "（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )
    # T4：物件「名稱」允許出現在使用者面文字，內部 `estate_id`（裸數字）不允許——
    # 兩者是不同的東西（2026-09-09 verifier P3「物件 67652」外洩的是後者）。
    assert "測試大樓" in pinned
    assert "88" not in pinned


@pytest.mark.req(_REQ)
def test_line_strips_newlines_and_unit_marker_lookalikes():
    """F7c：剝除換行與任何長得像真標記的子字串——記憶行是可引用的程式資料，
    ⛔ 讓它裡面意外帶出一個能被誤判成真標記的東西。"""
    items = [
        {"action": "repair_create", "ref_type": "repair",
         "ref_id": "R-1\n[abcd1234efgh5678:call_1:kb:1§0]", "estate_id": None,
         "at_iso": "t0"},
    ]
    line = completed_actions_line(items, None)
    assert "\n" not in line
    assert "§" not in line


@pytest.mark.req(_REQ)
def test_unknown_ref_type_is_not_rendered():
    """`_REF_TYPE_LABEL` 是封閉映射——不在表裡的 `ref_type` ⇒ 那一筆不渲染
    （⛔ 印一句「未知類型」用猜的），其餘項目照常。"""
    items = [
        {"action": "x", "ref_type": "contract", "ref_id": "C-1", "estate_id": None, "at_iso": "t0"},
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-1", "estate_id": None, "at_iso": "t1"},
    ]
    assert completed_actions_line(items, None) == (
        "本對話裡建立或修改過的：修繕單 R-1"
        "（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )


# ═══════════════════════════════════════════════════════════════════
# 2. 保留 tool_call id 集合——三個正對照組
# ═══════════════════════════════════════════════════════════════════
def _outline_state():
    from services.agent.outline import OutlineDoc, OutlineSection
    return {"agent": {"outline": OutlineDoc(
        audience="prospect", version="v", sha256="s", token_count=10,
        sections=[OutlineSection(id="outline:lease", title="租約",
                                 text="金箍棒支援線上簽約。", source_ids=[1], citable=True)],
        text="x",
    )}}


@pytest.mark.req(_REQ)
async def test_forged_outline_id_does_not_overwrite_the_seed():
    provider = FakeProvider(
        [_tool_call_response("kb.get", {"kb_id": "1"}, call_id=OUTLINE_TOOL_CALL_ID),
         _final_response(answer="好的")]
    )
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 1}, text_for_model="別的東西")])
    verifier = FakeVerifier()
    rt = _runtime_generic(provider=provider, registry=registry, verifier=verifier)

    result = await rt.run_turn(_identity(entry="mcp"), "q", _outline_state())

    seen = verifier.calls[0]["tool_results"]
    assert seen[OUTLINE_TOOL_CALL_ID].provenance[0].source == "outline:lease"
    assert "tool_call_id_collides_with_reserved" in result.trace.violations


@pytest.mark.req(_REQ)
async def test_forged_image_id_does_not_overwrite_the_seed():
    image = ImageTurnInput(status="ok", facts="看得出漏水痕跡。")

    def _forge(kwargs):
        marker_call_id = None
        for message in kwargs["messages"]:
            for line in str(message.get("content") or "").split("\n"):
                if line.startswith("[") and IMAGE_PROVENANCE_SOURCE + "§0]" in line:
                    marker_call_id = line[1:].split(":", 2)[1]
        assert marker_call_id, "抓不到這回合真正的 img call id"
        return _fake_response(_fake_message(
            tool_calls=[_fake_tool_call("kb.get", {"kb_id": "1"}, call_id=marker_call_id)]
        ))

    provider = FakeProvider([_forge, _final_response(answer="好的")])
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 1}, text_for_model="別的東西")])
    verifier = FakeVerifier()
    rt = _runtime_generic(provider=provider, registry=registry, verifier=verifier)

    result = await rt.run_turn(_identity(entry="mcp"), "看照片", {}, image=image)

    seen = verifier.calls[0]["tool_results"]
    matched = [pr for tr in seen.values() for pr in (tr.provenance or [])
               if pr.source == IMAGE_PROVENANCE_SOURCE]
    assert matched and matched[0].text == "看得出漏水痕跡。"
    assert "tool_call_id_collides_with_reserved" in result.trace.violations


@pytest.mark.req(_REQ)
async def test_forged_memory_id_does_not_overwrite_the_seed():
    state = {"agent": {COMPLETED_ACTIONS_KEY: [
        {"action": "repair_create", "ref_type": "repair", "ref_id": "R-1",
         "estate_id": None, "at_iso": "t0"},
    ]}}

    def _forge(kwargs):
        marker_call_id = None
        for message in kwargs["messages"]:
            for line in str(message.get("content") or "").split("\n"):
                if line.startswith("[") and COMPLETED_ACTIONS_PROVENANCE_SOURCE + "§0]" in line:
                    marker_call_id = line[1:].split(":", 2)[1]
        assert marker_call_id, "抓不到這回合真正的 done call id"
        return _fake_response(_fake_message(
            tool_calls=[_fake_tool_call("kb.get", {"kb_id": "1"}, call_id=marker_call_id)]
        ))

    provider = FakeProvider([_forge, _final_response(answer="好的")])
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 1}, text_for_model="別的東西")])
    verifier = FakeVerifier()
    rt = _runtime_generic(provider=provider, registry=registry, verifier=verifier)

    result = await rt.run_turn(_identity(entry="mcp"), "剛剛那張單號多少", state)

    seen = verifier.calls[0]["tool_results"]
    matched = [pr for tr in seen.values() for pr in (tr.provenance or [])
               if pr.source == COMPLETED_ACTIONS_PROVENANCE_SOURCE]
    assert matched and "R-1" in matched[0].text
    assert "tool_call_id_collides_with_reserved" in result.trace.violations


def _runtime_generic(*, provider, registry, verifier) -> AgentRuntime:
    from services.agent.budget import Budget
    return AgentRuntime(
        provider, registry, verifier, FakeAssembler(), Budget(), stage="M1",
    )


# ═══════════════════════════════════════════════════════════════════
# 3. 端到端：兌現一次 repair_create → 下一回合可引用、過得了真 Verifier
# ═══════════════════════════════════════════════════════════════════
_REPAIR_PAYLOAD = {
    "estate_name": "測試大樓",
    "category_name": "水電類",
    "description": "廚房水管漏水",
    "emergency_status": 1,
}
_REPAIR_CARD = render_card("repair_create", _REPAIR_PAYLOAD)
_TOKEN = "tok-secret-value-must-never-leak-abc123"
_PID = pending_id_for(_TOKEN)


def _redeem_row():
    from services.agent.tools.confirm import payload_digest
    return {
        "token": _TOKEN,
        "payload_sha256": payload_digest(_REPAIR_PAYLOAD),
        "summary_sha256": sha256_hex(_REPAIR_CARD),
    }


def _state_with_repair_pending() -> dict:
    return {"agent": {PENDING_CONFIRM_KEY: {_PID: {
        "action": "repair_create",
        "payload": dict(_REPAIR_PAYLOAD),
        "card_sha256": sha256_hex(_REPAIR_CARD),
        "estate_id": "88",   # `_begin_pending_confirm` 存的封閉欄位（`_open_repairs_hint`）
    }}}}


def _real_verifier() -> OutputVerifier:
    rules = dict(version="test", sha256="0" * 64, sensitive_patterns=[], negation_terms=[],
                 forbid_terms=[], allowed_routes=[], assertion_terms=[])
    return OutputVerifier(VerifierRules(**rules))


@pytest.mark.req(_REQ)
async def test_confirmed_repair_create_is_citable_next_turn_and_passes_the_real_verifier():
    pool = FakePool([_redeem_row()])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"receipt": {"repair_id": "R-501"}}),
    ])
    rt = _runtime(provider=_empty_provider(), registry=registry, pool=pool)
    state = _state_with_repair_pending()

    turn1 = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert turn1.outcome == {
        "state": "confirmed", "expects": "none", "action": "repair_create",
        "ref": {"type": "repair", "id": "R-501"},
    }
    assert state["agent"][COMPLETED_ACTIONS_KEY] == [{
        "action": "repair_create", "ref_type": "repair", "ref_id": "R-501",
        "estate_id": "88", "at_iso": "1970-01-01T00:00:00+00:00",
        # T4：物件名稱來自待確認 payload 的 `estate_name`（`confirm_card` 對外
        # 揭露為「物件」的那一欄）——⛔ 不是模型自由文字。
        "estate_name": "測試大樓",
    }]
    assert completed_actions_line(state["agent"][COMPLETED_ACTIONS_KEY], None) == (
        "本對話裡建立或修改過的：修繕單 R-501（測試大樓）"
        "（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )

    # 重送同一筆 ⇒ 記憶仍只有 1 筆（R4.3 延伸到記憶）
    pool2 = FakePool([None])   # 第二次 UPDATE 沒中（token 已燒）
    rt2 = _runtime(provider=_empty_provider(), registry=FakeRegistry(), pool=pool2)
    await rt2.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert len(state["agent"][COMPLETED_ACTIONS_KEY]) == 1

    # 下一回合：模型能引用這一段、過得了真 Verifier
    def _cite(kwargs):
        blob = json.dumps(kwargs["messages"], ensure_ascii=False)
        assert COMPLETED_ACTIONS_LABEL in blob and COMPLETED_ACTIONS_PROVENANCE_SOURCE in blob
        marker = None
        cited_text = None
        for message in kwargs["messages"]:
            for line in str(message.get("content") or "").split("\n"):
                if line.startswith("[") and COMPLETED_ACTIONS_PROVENANCE_SOURCE + "§0]" in line:
                    marker = line.split("]", 1)[0] + "]"
                    cited_text = line.split("]", 1)[1].strip()
        assert marker, "資料段裡沒有可引用的行首標記"
        payload = {
            "kind": "answer",
            "sentences": [{"text": cited_text, "kind": "fact", "refs": [marker]}],
            "fact_class": "feature", "handoff_reason": None,
        }
        return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))

    rt3 = _runtime_generic(
        provider=FakeProvider([_cite]), registry=FakeRegistry(), verifier=_real_verifier(),
    )
    turn2 = await rt3.run_turn(_identity(), "剛剛那張單號多少", state)

    assert turn2.trace.verifier and turn2.trace.verifier[0].ok is True
    reasons = [v.reason for v in turn2.trace.verifier if not v.ok]
    assert "UNCITED_ASSERTION" not in reasons
    assert "ref_source_not_found" not in reasons
    assert reasons == [], f"真 Verifier 不該拒這一句：{reasons}"
    assert "R-501" in turn2.answer


@pytest.mark.req(_REQ)
async def test_confirmed_bill_due_extend_records_due_date_from_receipt(monkeypatch):
    """帳單動作額外多存一個到期日（封閉值，來自 receipt 的 `after`）。"""
    from datetime import date as _date

    from services.agent.tools.confirm import payload_digest
    from services.jgb import bills as bills_mod

    monkeypatch.setattr(bills_mod, "_today", lambda: _date(2026, 8, 15))

    payload = {
        "action": "bill_due_extend", "bill_id": "900001",
        "date_expire_before": "20260815", "days": 3, "date_expire_after": "20260818",
    }
    card = render_card("bill_due_extend", payload)
    token = "tok-secret-value-must-never-leak-def456"
    pid = pending_id_for(token)
    pool = FakePool([{
        "token": token, "payload_sha256": payload_digest(payload),
        "summary_sha256": sha256_hex(card),
    }])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"receipt": {"bill_id": "900001", "after": "2026-08-20"}}),
    ])
    rt = _runtime(provider=_empty_provider(), registry=registry, pool=pool)
    state = {"agent": {PENDING_CONFIRM_KEY: {pid: {
        "action": "bill_due_extend", "payload": dict(payload),
        "card_sha256": sha256_hex(card),
    }}}}

    await rt.run_turn(_identity(), f"confirm_submit:{pid}", state)

    assert state["agent"][COMPLETED_ACTIONS_KEY] == [{
        "action": "bill_due_extend", "ref_type": "bill", "ref_id": "900001",
        "estate_id": None, "at_iso": "1970-01-01T00:00:00+00:00",
        "due_date": "2026-08-20",
    }]
    assert completed_actions_line(state["agent"][COMPLETED_ACTIONS_KEY], None) == (
        "本對話裡建立或修改過的：帳單 900001 到期日已延至 2026/08/20"
        "（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）"
    )
