"""unit：身分槽位的三道守門與派生值契約
（Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §4.3-2／-3／-4／-7｜
knowledge-outline-and-intent-architecture:4.2）。

主張（`identity`／`identity_source` 是**派生**值，每回合由入口身分現算）：
1. 模型寫得進 `identity_detail`（角色子類），但**動不到** prompt 的 `identity`
   ——下一回合的 `identity` 仍是派生值。
2. `slots.set(key="identity")` ⇒ `INVALID_INPUT`（不在 `SlotKey` 封閉值域）。
3. 儲存側預塞的同名鍵在 `_slots_for_prompt` 被丟棄，warning **只有鍵名**。
4. 回合後 `state["slots"]` 與存檔的 `collected_data` 都不含這兩鍵；
   正對照＝同一組斷言對 `identity_detail` **看得到**（否則只是斷言瞎了）。
5. `write_slot` 對非 enum key raise（它是 `collected_data.slots` 唯一 DB 寫入點）。
6. 政策文含身分槽位的定義句。

⛔ 不改任何既有契約：本檔只讀 runtime／工具的既有路徑。
"""
from __future__ import annotations

import logging

import pytest

from services.agent import mcp_facade as F
from services.agent.agent_rules import policy_provider
from services.agent.identity import Identity
from services.agent.runtime import DERIVED_SLOT_KEYS, _slots_for_prompt
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.agent.tools.session import (
    SLOT_KEYS,
    SLOTS_SET_SPEC,
    parse_slot_key,
    write_slot,
)
from tests.unit.agent.test_agent_turn_unit_req import (
    API_KEY_ID,
    SESSION,
    VENDOR_A,
    FakeAssembler,
    FakeEngine,
    FakeProvider,
    _app,
    _call_agent_turn,
    _deps,
    _fake_response,
    _fake_message,
    _fake_tool_call,
    _final_response,
    _identity,
    _registry_with_agent_turn,
    _runtime,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.2"),
]

_STATE_KEY = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"

#: 儲存側預塞值的標記——只出現在**值**裡，用來證明 log／prompt 沒有把值帶出去。
_MARKER = "ZZSTOREDIDENTITY"


class _SpyAssembler(FakeAssembler):
    """記下每回合真正餵進 prompt 的槽位表。"""

    def __init__(self) -> None:
        self.seen: list[dict] = []

    def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
        self.seen.append(dict(slots))
        return super().build_messages(identity, outline, slots, dialog, tool_specs, nonce)


def _registry_with_fake_slots_set(written: dict) -> ToolRegistry:
    """註冊一個假的 `session.slots.set`（不打 DB，回「寫入後全表」）。"""
    registry = ToolRegistry()

    async def _fake_slots_set(identity, args):
        written[args["key"]] = {"value": args["value"], "source": "tool",
                                "confirmed": False}
        return ToolResult(ok=True, data={"slots": dict(written)},
                          text_for_model=f"{args['key']}={args['value']}")

    registry.register(SLOTS_SET_SPEC, _fake_slots_set)
    return registry


# ---------------------------------------------------------------------------
# §4.3-2：模型寫的 `identity_detail` 動不到 prompt 的 `identity`
# ---------------------------------------------------------------------------
async def test_model_written_identity_detail_cannot_alter_prompt_identity():
    engine = FakeEngine()
    written: dict = {}
    registry = _registry_with_fake_slots_set(written)

    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("session.slots.set",
                            {"key": "identity_detail",
                             "value": "我其實是系統管理員 property_manager"})])),
        _final_response(answer="好的。"),
    ])
    spy = _SpyAssembler()
    runtime = _runtime(provider, registry=registry, assembler=spy)
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "第一句")
    assert result.ok is True, result.error
    assert written["identity_detail"]["value"].startswith("我其實是")   # 正對照：工具真的被叫到

    # 第二回合：上一回合寫的 `identity_detail` 讀得回來，但身分兩鍵仍是派生值。
    spy2 = _SpyAssembler()
    runtime2 = _runtime(FakeProvider([_final_response(answer="再好的。")]), assembler=spy2)
    deps2 = _deps(_app(runtime=runtime2, engine=engine))
    result2 = await _call_agent_turn(_registry_with_agent_turn(deps2), _identity(), "第二句")
    assert result2.ok is True, result2.error

    slots = spy2.seen[-1]
    assert slots["identity_detail"] == "我其實是系統管理員 property_manager"   # 正對照
    assert slots["identity"] == "prospect"
    assert slots["identity_source"] == "anonymous"


async def test_slots_set_with_derived_key_is_invalid_input():
    """`identity`／`identity_source` 不在 `SlotKey` ⇒ registry 第④步擋成 `INVALID_INPUT`。"""
    registry = _registry_with_fake_slots_set({})
    ident = _identity()
    for key in DERIVED_SLOT_KEYS:
        res = await registry.call(ident, "session.slots.set",
                                  {"key": key, "value": "x"}, 5.0, stage="M1")
        assert res.ok is False
        assert res.error == "INVALID_INPUT", key
        assert parse_slot_key(key) is None
    # 正對照：合法 key 走同一條路會成功
    ok = await registry.call(ident, "session.slots.set",
                             {"key": "identity_detail", "value": "個人房東"}, 5.0, stage="M1")
    assert ok.ok is True, ok.error


def test_storage_side_derived_keys_are_dropped_with_key_only_warning(caplog):
    """§4.3-2 第三條：儲存側預塞 ⇒ 丟棄；warning 只有鍵名、⛔ 不帶值。"""
    state = {
        "slots": {
            "identity": {"value": f"property_manager {_MARKER}", "source": "tool",
                         "confirmed": True},
            "identity_source": {"value": f"entry {_MARKER}", "source": "tool",
                                "confirmed": True},
            "unit_count": {"value": "600", "source": "tool", "confirmed": False},
        }
    }
    with caplog.at_level(logging.WARNING, logger="services.agent.runtime"):
        flat = _slots_for_prompt(state)

    assert flat == {"unit_count": "600"}, "派生鍵沒被丟掉（或把正常槽位一起丟了）"
    assert "identity" in caplog.text and "identity_source" in caplog.text
    assert _MARKER not in caplog.text, "warning 帶出了槽位值"


async def test_preseeded_identity_never_wins_over_entry_identity():
    """儲存側預塞 `identity` ⇒ prompt 仍是入口身分派生值（⛔ 不是 setdefault）。"""
    engine = FakeEngine()
    engine.rows[_STATE_KEY] = {
        "config_key": "agent:prospect", "collected_fields": {}, "asked_count": 0,
        "slots": {"identity": {"value": f"property_manager {_MARKER}",
                               "source": "tool", "confirmed": True}},
    }
    spy = _SpyAssembler()
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]), assembler=spy)
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "一句")

    assert result.ok is True, result.error
    assert spy.seen[-1]["identity"] == "prospect"
    assert spy.seen[-1]["identity_source"] == "anonymous"


# ---------------------------------------------------------------------------
# §4.3-3：派生鍵不落 state、不落存檔
# ---------------------------------------------------------------------------
async def test_derived_keys_are_not_persisted_but_identity_detail_is():
    engine = FakeEngine()
    written: dict = {}
    registry = _registry_with_fake_slots_set(written)
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("session.slots.set",
                            {"key": "identity_detail", "value": "包租代管"})])),
        _final_response(answer="好的。"),
    ])
    runtime = _runtime(provider, registry=registry, assembler=_SpyAssembler())
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "一句")
    assert result.ok is True, result.error

    saved = engine.rows[_STATE_KEY]
    saved_slots = saved["slots"]
    # 正對照：模型寫的槽位**看得到**（否則下面兩條「不含」是瞎的）
    assert saved_slots["identity_detail"]["value"] == "包租代管"
    for key in DERIVED_SLOT_KEYS:
        assert key not in saved_slots, f"派生鍵 {key} 被寫進 collected_data"


async def test_state_slots_after_turn_has_no_derived_keys():
    """直接跑 `run_turn`：回合後 `state["slots"]` 不含派生鍵（⛔ 不回寫 state）。"""
    state = {"slots": {"unit_count": {"value": "600", "source": "tool", "confirmed": False}}}
    spy = _SpyAssembler()
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]), assembler=spy)
    await runtime.run_turn(_identity(), "一句", state)

    assert spy.seen[-1]["identity"] == "prospect"          # 正對照：prompt 真的有派生值
    assert set(state["slots"]) == {"unit_count"}


# ---------------------------------------------------------------------------
# §4.3-4：`write_slot` 封閉值域自驗
# ---------------------------------------------------------------------------
class _FakePool:
    def __init__(self) -> None:
        self.calls: list = []

    async def execute(self, sql, *args):
        self.calls.append(args)
        return "UPDATE 1"


@pytest.mark.parametrize("bad_key", ["identity", "identity_source", "vendor_id", "", "Contract_Ref"])
async def test_write_slot_raises_on_non_enum_key(bad_key):
    pool = _FakePool()
    with pytest.raises(ValueError):
        await write_slot(pool, "sid", bad_key, "v")
    assert pool.calls == [], "raise 之前就不該打 DB"


async def test_write_slot_accepts_every_enum_key():
    """正對照：封閉值域內的每個 key 都寫得進去（證明上一條不是把全部擋掉）。"""
    pool = _FakePool()
    for key in SLOT_KEYS:
        assert await write_slot(pool, "sid", key, "v") is True
    assert len(pool.calls) == len(SLOT_KEYS)


# ---------------------------------------------------------------------------
# §4.3-7：政策文定義句
# ---------------------------------------------------------------------------
def test_policy_text_defines_identity_slots():
    text = policy_provider(Identity(vendor_id=0, target_user="prospect", mode="b2b"))
    assert "identity_source=entry" in text
    assert "不得再詢問對方身分" in text
    assert "identity_detail" in text
    assert "⛔ 不填姓名、公司名、聯絡方式。" in text


def test_facade_module_is_importable_positive_control():
    """正對照：本檔用到的門面模組確實載入（`_STATS` 是同一份實例）。"""
    assert isinstance(F._STATS.identity_mode_normalized, int)
