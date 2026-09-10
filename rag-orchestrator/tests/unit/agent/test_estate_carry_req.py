"""unit：#10 物件記憶 `estate_carry`（Plan 第六批單元 B，
`inputs/plan-walkthrough-fixes-batch6-20260910.md`）。

病灶：使用者先講「基隆獨立共生公寓」再傳照片／再說「幫我報修」，模型手上沒有
「剛剛講的是哪個物件」的東西，於是回頭反問（或把 `estate_name` 留空 ⇒
`confirm.request` 直接 `INVALID_INPUT`）。

守的事：
1. **封閉形狀**：`state["agent"]["estate_carry"]` 只有 `name`／`id` 兩鍵；讀出來
   的東西形狀不對一律當沒有（這份狀態會序列化進 `form_sessions.collected_data`
   再讀回來，⛔ 不得假設形狀正確）。
2. **三個寫點**：(a) `confirm.request` 出卡成功、(b) pre-lookup 物件關鍵字唯一
   命中、(c) 模型自己查 `jgb2.query.estates` 唯一命中。
3. **兩個讀點**：`confirm.request` payload 缺 `estate_name` 由程式補
   （`repair_create`／`bill_due_extend` 兩支）；照片回合資料段多一句
   「本對話最近提到的物件：X」且 **`citable=False`**。
4. **範圍釘住（`SELECT_SCOPE_KEY`）不覆寫、不注入**；`_apply_scope_exit` 清除。
5. **⛔ 名稱不進 trace／violations**——物件名稱等同識別碼，trace 與計量表都會
   序列化落地。
正對照：模型有給 `estate_name` ⇒ 逐字不動；沒有記憶 ⇒ 完全不注入。

⛔ 不接真 OpenAI、不接真 DB（沿用既有假件）。
"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.runtime import (
    ESTATE_CARRY_KEY,
    ESTATE_CARRY_LABEL,
    ESTATE_CARRY_NAME_MAX_CHARS,
    ESTATE_CARRY_TEXT_PREFIX,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    ImageTurnInput,
    TurnResult,
    TurnTrace,
    _apply_estate_carry_to_confirm_args,
    _apply_scope_exit,
    _estate_carry_from_estates_data,
    _estate_carry_of,
    _write_estate_carry,
)
from services.agent.tools.registry import ToolResult

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    VerifierVerdict,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
    _identity,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:linebot-20260910-estate-carry"),
]

_ESTATES_TOOL = "jgb2.query.estates"
_NAME = "基隆獨立共生公寓"

#: ⚠️ **本檔不想觸發 pre-lookup 的回合一律用長句**：`_pre_lookup_trigger` 對
#: 「≤6 字、無數字／標點／空白」的整句會**先打一次 `jgb2.query.estates`**，
#: 那一次會吃掉 `FakeRegistry` 排隊中的第一個結果，接著要驗的 `confirm.request`
#: 就拿到空佇列的 `NO_MATCH`——症狀是「寫點沒寫」，實際上是測試前提不成立。
_LONG_MSG = "幫我報一張修繕單好嗎謝謝"
_PHOTO_MSG = "這張照片這樣子需要報修嗎"


def _runtime(provider, registry=None, verifier=None):
    return AgentRuntime(
        provider, registry or FakeRegistry(),
        verifier or FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(),
        Budget(), stage="M1", clock=FakeClock(),
    )


def _confirm_args(payload: dict) -> dict:
    return {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)}


def _confirm_ok_result(payload: dict, estate_id="77"):
    return ToolResult(ok=True, data={
        "pending_id": "0123456789abcdef", "card": "即將建立修繕單",
        "action": payload["action"], "payload": dict(payload),
        "quick_replies": [], "hint": None, "estate_id": estate_id,
    }, text_for_model="")


def _estates_scoped(estate_id="77"):
    """`query_estates` 的 `_ok_single(scoped=True)`：命中恰一列 ⇒ 帶 `scope`。"""
    return ToolResult(ok=True, data={"facts": "這個物件位於基隆市。",
                                     "scope": {"estate_id": estate_id}},
                      text_for_model="")


def _estates_candidates(rows):
    return ToolResult(ok=True, data={"facts": "找到以下物件。", "candidates": list(rows)},
                      text_for_model="")


# ════════════════════════════════════════════════════════════════════
# A. 純函式：封閉形狀
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("state", [
    None, "not a dict", {}, {ESTATE_CARRY_KEY: None}, {ESTATE_CARRY_KEY: "x"},
    {ESTATE_CARRY_KEY: {"id": "77"}}, {ESTATE_CARRY_KEY: {"name": ""}},
    {ESTATE_CARRY_KEY: {"name": "   "}}, {ESTATE_CARRY_KEY: {"name": 123}},
])
def test_reader_treats_any_off_shape_as_absent(state):
    assert _estate_carry_of(state) is None


def test_reader_normalises_to_exactly_two_keys():
    got = _estate_carry_of({ESTATE_CARRY_KEY: {"name": "  某物件  ", "id": " 77 ", "extra": "x"}})
    assert got == {"name": "某物件", "id": "77"}
    # 正對照：id 缺值就是 None（⛔ 不猜）
    assert _estate_carry_of({ESTATE_CARRY_KEY: {"name": "某物件"}}) == {"name": "某物件", "id": None}


def test_writer_stores_only_name_and_id():
    st: dict = {}
    assert _write_estate_carry(st, _NAME, 77) is True
    assert set(st[ESTATE_CARRY_KEY]) == {"name", "id"}
    assert st[ESTATE_CARRY_KEY] == {"name": _NAME, "id": "77"}


@pytest.mark.parametrize("name", [None, 123, "", "   ", "長" * (ESTATE_CARRY_NAME_MAX_CHARS + 1)])
def test_writer_rejects_non_names_and_over_long_names(name):
    st: dict = {}
    assert _write_estate_carry(st, name) is False
    assert ESTATE_CARRY_KEY not in st


def test_writer_refuses_while_scope_is_pinned():
    st = {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "9"}}
    assert _write_estate_carry(st, _NAME, "77") is False
    assert ESTATE_CARRY_KEY not in st
    # 正對照：同一支、同樣的名稱，沒釘範圍時是寫得進去的
    st2: dict = {}
    assert _write_estate_carry(st2, _NAME, "77") is True


def test_estates_data_to_carry_only_when_exactly_one():
    assert _estate_carry_from_estates_data({"facts": "…", "scope": {"estate_id": "77"}}, "基隆共生宅") \
        == ("基隆共生宅", "77")
    assert _estate_carry_from_estates_data({"candidates": [{"title": _NAME, "id": "77"}]}, "共生") \
        == (_NAME, "77")


@pytest.mark.parametrize("data", [
    None, "x", {}, {"facts": "查無"},
    {"candidates": []},
    {"candidates": [{"title": "A", "id": "1"}, {"title": "B", "id": "2"}]},   # 多筆 ⇒ ⛔ 不挑第一筆
    {"candidates": [{"found": False}]},                                       # 查無哨兵
])
def test_estates_data_without_a_single_hit_yields_nothing(data):
    assert _estate_carry_from_estates_data(data, "共生") is None


# ════════════════════════════════════════════════════════════════════
# B. 讀點純函式：confirm payload 補值
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action", ["repair_create", "bill_due_extend"])
def test_fills_missing_estate_name_for_both_confirm_actions(action):
    args = _confirm_args({"action": action})
    new, applied = _apply_estate_carry_to_confirm_args(args, {"name": _NAME, "id": "77"})
    assert applied == ["estate_name"]
    assert json.loads(new["payload"])["estate_name"] == _NAME


@pytest.mark.parametrize("existing", [_NAME, "別的物件"])
def test_model_supplied_estate_name_is_untouched(existing):
    args = _confirm_args({"action": "repair_create", "estate_name": existing})
    new, applied = _apply_estate_carry_to_confirm_args(args, {"name": "記憶裡的物件", "id": "77"})
    assert applied == [] and new is args


@pytest.mark.parametrize("args,carry", [
    (_confirm_args({"action": "not_an_action"}), {"name": _NAME}),
    ({"summary": "x", "payload": "not json"}, {"name": _NAME}),
    ({"summary": "x", "payload": json.dumps(["list"])}, {"name": _NAME}),
    (_confirm_args({"action": "repair_create"}), None),
    (_confirm_args({"action": "repair_create"}), {"name": "  "}),
    ("not a dict", {"name": _NAME}),
])
def test_untouched_when_shape_or_carry_is_off(args, carry):
    new, applied = _apply_estate_carry_to_confirm_args(args, carry)
    assert applied == [] and new is args


def test_empty_string_estate_name_counts_as_missing():
    args = _confirm_args({"action": "repair_create", "estate_name": "   "})
    new, applied = _apply_estate_carry_to_confirm_args(args, {"name": _NAME})
    assert applied == ["estate_name"]
    assert json.loads(new["payload"])["estate_name"] == _NAME


# ════════════════════════════════════════════════════════════════════
# C. 寫點 (a)：`confirm.request` 出卡成功
# ════════════════════════════════════════════════════════════════════
async def test_write_point_a_card_issued_records_the_estate():
    state = {"agent": {}}
    payload = {"action": "repair_create", "estate_name": _NAME}
    registry = FakeRegistry(call_results=[_confirm_ok_result(payload)])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("confirm.request", _confirm_args(payload), call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), _LONG_MSG, state)

    # 前提正對照：卡**真的出了**（否則下面那條「沒寫進去」只是在驗一個沒跑到的分支）
    assert result.outcome["state"] == "confirm_pending"
    assert state["agent"][ESTATE_CARRY_KEY] == {"name": _NAME, "id": "77"}
    assert _NAME not in json.dumps(result.trace.violations, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# D. 寫點 (b)：pre-lookup 物件關鍵字唯一命中
# ════════════════════════════════════════════════════════════════════
async def test_write_point_b_pre_lookup_unique_hit_records_the_estate():
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[_estates_scoped("77")])
    result = await _runtime(FakeProvider([_final_response(answer="好的")]), registry) \
        .run_turn(_identity(), "基隆共生宅", state)

    called = [c for c in registry.call_args if c["name"] == _ESTATES_TOOL]
    assert called, "pre-lookup 沒有真的打 estates——前提不成立"
    assert state["agent"][ESTATE_CARRY_KEY] == {"name": "基隆共生宅", "id": "77"}
    # ⛔ 名稱不進 trace：只留一個無名稱的標記
    assert "estate_carry_set" in result.trace.violations
    assert "基隆共生宅" not in json.dumps(result.trace.violations, ensure_ascii=False)


async def test_write_point_b_does_not_fire_when_lookup_finds_nothing():
    """正對照：同一條路、查無 ⇒ ⛔ 不記（證明不是「有查就記」）。"""
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"facts": "在對外刊登清單中找不到這個物件。"}, text_for_model="")])
    await _runtime(FakeProvider([_final_response(answer="查無")]), registry) \
        .run_turn(_identity(), "不存在宅", state)
    assert ESTATE_CARRY_KEY not in state["agent"]


# ════════════════════════════════════════════════════════════════════
# E. 寫點 (c)：模型自己查 estates 唯一命中（整句就是物件名稱那條路）
# ════════════════════════════════════════════════════════════════════
async def test_write_point_c_model_estates_query_unique_hit_records_the_estate():
    """`基隆獨立共生公寓` 8 字，過不了 pre-lookup 的 6 字閘 ⇒ 由模型查那一次接上。"""
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[
        _estates_candidates([{"title": _NAME, "id": "77"}])])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call(_ESTATES_TOOL, {"keyword": _NAME}, call_id="c1")])),
        _final_response(answer="找到了"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), _NAME, state)

    assert state["agent"][ESTATE_CARRY_KEY] == {"name": _NAME, "id": "77"}
    assert _NAME not in json.dumps(result.trace.violations, ensure_ascii=False)


async def test_write_point_c_ignores_multi_candidate_results():
    """正對照：多筆候選 ⇒ ⛔ 不挑第一筆。"""
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[
        _estates_candidates([{"title": "A宅", "id": "1"}, {"title": "B宅", "id": "2"}])])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call(_ESTATES_TOOL, {"keyword": "共生"}, call_id="c1")])),
        _final_response(answer="有兩個"),
    ])
    await _runtime(provider, registry).run_turn(_identity(), "共生宅有哪些方案", state)
    assert ESTATE_CARRY_KEY not in state["agent"]


# ════════════════════════════════════════════════════════════════════
# F. 讀點：跨回合補進 `confirm.request`
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action", ["repair_create", "bill_due_extend"])
async def test_read_point_fills_estate_name_on_a_later_turn(action):
    state = {"agent": {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    registry = FakeRegistry(call_results=[_confirm_ok_result({"action": action, "estate_name": _NAME})])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("confirm.request", _confirm_args({"action": action}), call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), _LONG_MSG, state)

    sent = [c for c in registry.call_args if c["name"] == "confirm.request"]
    assert sent, "confirm.request 沒被送進 registry——前提不成立"
    assert json.loads(sent[0]["args"]["payload"])["estate_name"] == _NAME
    assert "estate_carry_applied:estate_name" in result.trace.violations
    assert _NAME not in json.dumps(result.trace.violations, ensure_ascii=False)


async def test_read_point_leaves_a_model_supplied_name_alone():
    """正對照：模型自己填了別的物件 ⇒ 逐字不動。"""
    state = {"agent": {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    original = _confirm_args({"action": "repair_create", "estate_name": "台北另一處"})
    registry = FakeRegistry(call_results=[
        _confirm_ok_result({"action": "repair_create", "estate_name": "台北另一處"})])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("confirm.request", original, call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), _LONG_MSG, state)

    sent = [c for c in registry.call_args if c["name"] == "confirm.request"]
    assert json.loads(sent[0]["args"]["payload"])["estate_name"] == "台北另一處"
    assert not any(v.startswith("estate_carry_applied") for v in result.trace.violations)


async def test_read_point_is_not_one_shot():
    """同一段對話可能連開兩張單 ⇒ 補完 ⛔ 不清掉記憶。"""
    state = {"agent": {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    registry = FakeRegistry(call_results=[
        _confirm_ok_result({"action": "repair_create", "estate_name": _NAME})])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("confirm.request", _confirm_args({"action": "repair_create"}), call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    await _runtime(provider, registry).run_turn(_identity(), _LONG_MSG, state)
    assert state["agent"][ESTATE_CARRY_KEY] == {"name": _NAME, "id": "77"}


# ════════════════════════════════════════════════════════════════════
# G. 讀點：照片回合資料段
# ════════════════════════════════════════════════════════════════════
def _image_ok():
    return ImageTurnInput(status="ok", facts="看得出天花板有水漬。", processed=1, total=1)


async def test_photo_turn_injects_the_sentence_as_a_non_citable_piece():
    state = {"agent": {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    provider = FakeProvider([_final_response(answer="請問急不急？")])
    result = await _runtime(provider, FakeRegistry(), verifier) \
        .run_turn(_identity(), _PHOTO_MSG, state, image=_image_ok())

    sentence = ESTATE_CARRY_TEXT_PREFIX + _NAME
    blob = json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    assert sentence in blob, "照片回合沒有注入物件記憶那一句"
    assert ESTATE_CARRY_LABEL in blob

    # ⛔ `citable=False`：這是程式組的一句會話記憶，⛔ 不是可引用的事實來源
    assert verifier.calls, "Verifier 沒被呼叫——前提不成立"
    carried = [tr for cid, tr in verifier.calls[0]["tool_results"].items()
               if cid.startswith("est-")]
    assert len(carried) == 1
    assert carried[0].provenance[0].citable is False
    # ⛔ 名稱不進 trace
    assert _NAME not in json.dumps(result.trace.violations, ensure_ascii=False)


async def test_photo_turn_without_any_memory_injects_nothing():
    """正對照：沒有記憶 ⇒ 那一段完全不出現（證明不是整支恆常注入）。"""
    provider = FakeProvider([_final_response(answer="請問急不急？")])
    await _runtime(provider, FakeRegistry()).run_turn(
        _identity(), _PHOTO_MSG, {"agent": {}}, image=_image_ok())
    blob = json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    assert ESTATE_CARRY_TEXT_PREFIX not in blob
    assert ESTATE_CARRY_LABEL not in blob


async def test_non_photo_turn_does_not_inject_the_sentence():
    """讀點只掛在照片回合——一般回合 ⛔ 不多印一段。"""
    state = {"agent": {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    provider = FakeProvider([_final_response(answer="好的")])
    await _runtime(provider, FakeRegistry()).run_turn(_identity(), _LONG_MSG, state)
    assert ESTATE_CARRY_TEXT_PREFIX not in json.dumps(provider.calls[0]["messages"], ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# H. 範圍：釘住不覆寫、不注入；範圍外清除
# ════════════════════════════════════════════════════════════════════
async def test_pinned_scope_does_not_overwrite_the_memory():
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "9"},
                       ESTATE_CARRY_KEY: {"name": "原本的物件", "id": "9"}}}
    registry = FakeRegistry(call_results=[_estates_scoped("77")])
    await _runtime(FakeProvider([_final_response(answer="好的")]), registry) \
        .run_turn(_identity(), "基隆共生宅", state)
    assert state["agent"][ESTATE_CARRY_KEY] == {"name": "原本的物件", "id": "9"}


async def test_pinned_scope_does_not_inject_the_sentence_on_a_photo_turn():
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "9"},
                       ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}}
    provider = FakeProvider([_final_response(answer="請問急不急？")])
    await _runtime(provider, FakeRegistry()).run_turn(
        _identity(), _PHOTO_MSG, state, image=_image_ok())
    assert ESTATE_CARRY_TEXT_PREFIX not in json.dumps(provider.calls[0]["messages"], ensure_ascii=False)


def _turn_result() -> TurnResult:
    return TurnResult(kind="answer", answer="原本的答案", handoff=None,
                      quick_replies=[], trace=TurnTrace(trace_id="t"))


def test_scope_exit_clears_the_memory():
    st = {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}
    _apply_scope_exit(_turn_result(), scope_in=1, scope_out=1, agent_state=st)
    assert ESTATE_CARRY_KEY not in st


def test_scope_exit_leaves_the_memory_when_nothing_was_out_of_scope():
    """正對照：沒有範圍外 ⇒ 逐字不動（證明不是「每回合都清」）。"""
    st = {ESTATE_CARRY_KEY: {"name": _NAME, "id": "77"}}
    _apply_scope_exit(_turn_result(), scope_in=2, scope_out=0, agent_state=st)
    assert st[ESTATE_CARRY_KEY] == {"name": _NAME, "id": "77"}


def test_scope_exit_without_state_still_does_its_original_three_things():
    """模組級函式：測試直接呼叫它時不必給狀態（⛔ 不得因此炸掉）。"""
    out = _apply_scope_exit(_turn_result(), scope_in=0, scope_out=1)
    assert out.kind == "answer" and out.answer != "原本的答案"
