"""unit：`ToolRegistry`（spec agentic-mcp-orchestration 任務 1.3｜R1.3, R2.2, R2.3, R3.5, R3.6, R11.4）。

覆蓋：
- `specs_for` 唯一規則（audience×stage 白名單矩陣、`readonly_view` 遮 write、
  `facade_only` 對 `for_model`／`readonly_view` 的排除）
- `call()` 守門四步（可見性→scope/token→速率→schema）＋逾時＋fn 例外
- 不變量 18（六個身分鍵各一，register() 內擋）
- `to_openai_tools`／`openapi` 兩種面

全部離線、假工具、假時鐘，不接觸真 DB／真 LLM。
"""
import asyncio

import pytest

from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry, ToolResult

pytestmark = pytest.mark.unit


async def _ok_fn(identity, args):
    return ToolResult(ok=True, data={"echo": args}, text_for_model="ok")


def _identity(target_user, *, mode="b2c", api_key_id=1, vendor_id=1, session_id="s1"):
    return Identity(
        vendor_id=vendor_id,
        target_user=target_user,
        mode=mode,
        api_key_id=api_key_id,
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# design 元件 2 的 audience × stage 白名單矩陣（縮影：每組一個代表工具）
# ---------------------------------------------------------------------------


def _matrix_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        {
            "name": "kb.get",
            "description": "",
            "input_schema": {"type": "object", "properties": {"kb_id": {"type": "string"}}},
            "scope": "read",
            "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "kb.search",
            "description": "",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
            "scope": "read",
            "stage": {"property_manager": "M0", "tenant": "M0"},  # prospect 永不可見
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "help.read",
            "description": "",
            "input_schema": {"type": "object", "properties": {"slug": {"type": "string"}}},
            "scope": "read",
            "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "jgb2.query.bills",
            "description": "",
            "input_schema": {"type": "object", "properties": {"face": {"type": "string"}}},
            "scope": "read",
            "stage": {"property_manager": "M0", "tenant": "M0"},  # prospect 永不可見
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "session.slots.get",
            "description": "",
            "input_schema": {"type": "object", "properties": {"key": {"type": "string"}}},
            "scope": "read",
            "stage": {"prospect": "M1", "property_manager": "M1", "tenant": "M1"},
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "confirm.request",
            "description": "",
            "input_schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}, "payload": {"type": "object"}},
            },
            "scope": "read",
            "stage": {"prospect": "M1", "property_manager": "M1", "tenant": "M1"},
        },
        _ok_fn,
    )
    reg.register(
        {
            "name": "jgb2.action.pay",
            "description": "",
            "input_schema": {
                "type": "object",
                "properties": {
                    "payload": {"type": "object"},
                    "confirmation_token": {"type": "string"},
                },
            },
            "scope": "write",
            "stage": {"property_manager": "M5", "tenant": "M4"},  # prospect 永不可見
        },
        _ok_fn,
    )
    return reg


MATRIX = [
    # (tool, audience, stage, expected_visible)
    ("kb.get", "prospect", "M0", True),
    ("kb.get", "property_manager", "M0", True),
    ("kb.get", "tenant", "M0", True),
    ("kb.search", "prospect", "M0", False),
    ("kb.search", "property_manager", "M0", True),
    ("kb.search", "tenant", "M0", True),
    ("help.read", "prospect", "M0", True),
    ("help.read", "property_manager", "M0", True),
    ("help.read", "tenant", "M0", True),
    ("jgb2.query.bills", "prospect", "M0", False),
    ("jgb2.query.bills", "property_manager", "M0", True),
    ("jgb2.query.bills", "tenant", "M0", True),
    ("session.slots.get", "prospect", "M0", False),  # 未達 M1
    ("session.slots.get", "prospect", "M1", True),
    ("session.slots.get", "property_manager", "M1", True),
    ("session.slots.get", "tenant", "M1", True),
    ("confirm.request", "tenant", "M0", False),
    ("confirm.request", "tenant", "M1", True),
    ("jgb2.action.pay", "prospect", "M5", False),  # prospect 永不可見
    ("jgb2.action.pay", "tenant", "M0", False),  # 未達 M4
    ("jgb2.action.pay", "tenant", "M4", True),
    ("jgb2.action.pay", "tenant", "M5", True),  # M5 <= 目前部署 stage 仍可見（<=）
    ("jgb2.action.pay", "property_manager", "M4", False),  # 未達 M5
    ("jgb2.action.pay", "property_manager", "M5", True),
]


@pytest.mark.parametrize("tool,audience,stage,expected", MATRIX)
def test_whitelist_matrix_specs_for(tool, audience, stage, expected):
    reg = _matrix_registry()
    identity = _identity(audience if audience != "property_manager" else "property_manager")
    names = {s["name"] for s in reg.specs_for(identity, stage)}
    assert (tool in names) is expected


def test_readonly_view_hides_write_tools():
    reg = _matrix_registry()
    identity = _identity("tenant")
    visible_normal = {s["name"] for s in reg.specs_for(identity, "M5")}
    visible_readonly = {s["name"] for s in reg.specs_for(identity, "M5", readonly_view=True)}
    assert "jgb2.action.pay" in visible_normal
    assert "jgb2.action.pay" not in visible_readonly
    # read 工具不受影響
    assert "kb.get" in visible_readonly


def test_facade_only_hidden_from_model_and_readonly_view_but_visible_to_facade():
    reg = ToolRegistry()
    reg.register(
        {
            "name": "agent.turn",
            "description": "",
            "input_schema": {"type": "object", "properties": {"message": {"type": "string"}}},
            "scope": "read",
            "stage": {"prospect": "M1"},
            "facade_only": True,
        },
        _ok_fn,
    )
    identity = _identity("prospect")
    # for_model=True（PromptAssembler 視角）⇒ 不可見
    assert reg.specs_for(identity, "M1", for_model=True) == []
    # readonly_view=True（影子視圖）⇒ 不可見，即使 for_model=False
    assert reg.specs_for(identity, "M1", readonly_view=True, for_model=False) == []
    # 門面視角（for_model=False, readonly_view=False）⇒ 可見
    names = {s["name"] for s in reg.specs_for(identity, "M1", for_model=False, readonly_view=False)}
    assert "agent.turn" in names


# ---------------------------------------------------------------------------
# call() 守門四步
# ---------------------------------------------------------------------------


async def test_call_invisible_tool_returns_no_match_and_records_forbidden():
    reg = _matrix_registry()
    identity = _identity("prospect")
    result = await reg.call(identity, "kb.search", {"query": "x"}, timeout_s=1, stage="M0")
    assert result.ok is False
    assert result.error == "NO_MATCH"
    violations = reg.last_violations()
    assert any(v["name"] == "kb.search" and v["note"] == "FORBIDDEN" for v in violations)


async def test_call_unknown_tool_name_returns_no_match():
    reg = _matrix_registry()
    identity = _identity("tenant")
    result = await reg.call(identity, "no.such.tool", {}, timeout_s=1, stage="M0")
    assert result.ok is False
    assert result.error == "NO_MATCH"


async def test_call_write_tool_without_readonly_but_missing_token_needs_confirmation():
    reg = _matrix_registry()
    identity = _identity("tenant")
    result = await reg.call(
        identity, "jgb2.action.pay", {"payload": {}}, timeout_s=1, stage="M4"
    )
    assert result.ok is False
    assert result.error == "CONFIRMATION_REQUIRED"


async def test_call_write_tool_with_token_present_succeeds():
    reg = _matrix_registry()
    identity = _identity("tenant")
    result = await reg.call(
        identity,
        "jgb2.action.pay",
        {"payload": {}, "confirmation_token": "tok-1"},
        timeout_s=1,
        stage="M4",
    )
    assert result.ok is True


async def test_call_write_tool_under_readonly_view_returns_no_match():
    reg = _matrix_registry()
    identity = _identity("tenant")
    result = await reg.call(
        identity,
        "jgb2.action.pay",
        {"payload": {}, "confirmation_token": "tok-1"},
        timeout_s=1,
        stage="M4",
        readonly_view=True,
    )
    assert result.ok is False
    assert result.error == "NO_MATCH"


async def test_call_invalid_input_schema_returns_invalid_input():
    reg = _matrix_registry()
    identity = _identity("tenant")
    # kb.get 的 kb_id 要求 string，這裡傳 int
    result = await reg.call(
        identity, "kb.get", {"kb_id": 123}, timeout_s=1, stage="M0"
    )
    assert result.ok is False
    assert result.error == "INVALID_INPUT"


async def test_call_timeout_returns_tool_timeout():
    reg = _matrix_registry()

    async def _slow_fn(identity, args):
        await asyncio.sleep(10)
        return ToolResult(ok=True)

    reg.register(
        {
            "name": "slow.tool",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "scope": "read",
            "stage": {"tenant": "M0"},
        },
        _slow_fn,
    )
    identity = _identity("tenant")
    result = await reg.call(identity, "slow.tool", {}, timeout_s=0.01, stage="M0")
    assert result.ok is False
    assert result.error == "TOOL_TIMEOUT"


async def test_call_fn_exception_returns_no_match_and_records_exc_note():
    reg = ToolRegistry()

    async def _boom_fn(identity, args):
        raise RuntimeError("boom")

    reg.register(
        {
            "name": "boom.tool",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "scope": "read",
            "stage": {"tenant": "M0"},
        },
        _boom_fn,
    )
    identity = _identity("tenant")
    result = await reg.call(identity, "boom.tool", {}, timeout_s=1, stage="M0")
    assert result.ok is False
    assert result.error == "NO_MATCH"
    violations = reg.last_violations()
    assert any(
        v["name"] == "boom.tool" and v["note"] == "EXC:RuntimeError" for v in violations
    )


# ---------------------------------------------------------------------------
# 速率限制：key = (api_key_id, vendor_id)，⛔ 不含 session_id
# ---------------------------------------------------------------------------


async def test_rate_limit_exceeded_returns_rate_limited(monkeypatch):
    monkeypatch.setenv("RATE_PER_MIN", "2")
    clock = {"t": 0.0}
    reg = ToolRegistry(clock=lambda: clock["t"])
    reg.register(
        {
            "name": "help.read",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "scope": "read",
            "stage": {"tenant": "M0"},
        },
        _ok_fn,
    )
    identity = _identity("tenant", api_key_id=1, vendor_id=1)
    r1 = await reg.call(identity, "help.read", {}, timeout_s=1, stage="M0")
    r2 = await reg.call(identity, "help.read", {}, timeout_s=1, stage="M0")
    r3 = await reg.call(identity, "help.read", {}, timeout_s=1, stage="M0")
    assert r1.ok is True and r2.ok is True
    assert r3.ok is False and r3.error == "RATE_LIMITED"


async def test_rate_limit_key_excludes_session_id_changing_session_does_not_reset(
    monkeypatch,
):
    monkeypatch.setenv("RATE_PER_MIN", "1")
    clock = {"t": 0.0}
    reg = ToolRegistry(clock=lambda: clock["t"])
    reg.register(
        {
            "name": "help.read",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "scope": "read",
            "stage": {"tenant": "M0"},
        },
        _ok_fn,
    )
    identity_a = _identity("tenant", api_key_id=1, vendor_id=1, session_id="session-A")
    identity_b = _identity("tenant", api_key_id=1, vendor_id=1, session_id="session-B")
    r1 = await reg.call(identity_a, "help.read", {}, timeout_s=1, stage="M0")
    # 換一個全新的 session_id，同一把 key/vendor ⇒ 桶仍是同一個，第二次應被擋
    r2 = await reg.call(identity_b, "help.read", {}, timeout_s=1, stage="M0")
    assert r1.ok is True
    assert r2.ok is False and r2.error == "RATE_LIMITED"


async def test_kb_get_hourly_cap_separate_from_per_minute_rate(monkeypatch):
    monkeypatch.setenv("RATE_PER_MIN", "1000")  # 不讓每分鐘限制先觸發
    monkeypatch.setenv("KB_GET_CAP", "2")
    clock = {"t": 0.0}
    reg = ToolRegistry(clock=lambda: clock["t"])
    reg.register(
        {
            "name": "kb.get",
            "description": "",
            "input_schema": {"type": "object", "properties": {"kb_id": {"type": "string"}}},
            "scope": "read",
            "stage": {"tenant": "M0"},
        },
        _ok_fn,
    )
    identity = _identity("tenant")
    args = {"kb_id": "1"}
    r1 = await reg.call(identity, "kb.get", args, timeout_s=1, stage="M0")
    r2 = await reg.call(identity, "kb.get", args, timeout_s=1, stage="M0")
    r3 = await reg.call(identity, "kb.get", args, timeout_s=1, stage="M0")
    assert r1.ok is True and r2.ok is True
    assert r3.ok is False and r3.error == "RATE_LIMITED"


# ---------------------------------------------------------------------------
# 不變量 18：input_schema 六個身分鍵各一 ⇒ register() raise
# ---------------------------------------------------------------------------

_IDENTITY_KEYS = ["vendor_id", "role_id", "user_id", "target_user", "mode", "viewer_user_id"]


@pytest.mark.parametrize("bad_key", _IDENTITY_KEYS)
def test_register_rejects_identity_key_in_input_schema(bad_key):
    reg = ToolRegistry()
    with pytest.raises(Exception):
        reg.register(
            {
                "name": f"bad.tool.{bad_key}",
                "description": "",
                "input_schema": {"type": "object", "properties": {bad_key: {"type": "string"}}},
                "scope": "read",
                "stage": {"tenant": "M0"},
            },
            _ok_fn,
        )


def test_register_duplicate_name_raises():
    reg = ToolRegistry()
    spec = {
        "name": "dup.tool",
        "description": "",
        "input_schema": {"type": "object", "properties": {}},
        "scope": "read",
        "stage": {"tenant": "M0"},
    }
    reg.register(spec, _ok_fn)
    with pytest.raises(Exception):
        reg.register(spec, _ok_fn)


# ---------------------------------------------------------------------------
# 兩種面
# ---------------------------------------------------------------------------


def test_to_openai_tools_shape_strict_and_additional_properties_false():
    reg = _matrix_registry()
    identity = _identity("tenant")
    tools = reg.to_openai_tools(identity, "M0")
    assert tools, "應至少有可見工具"
    for tool in tools:
        assert tool["type"] == "function"
        assert tool["function"]["strict"] is True
        assert tool["function"]["parameters"]["additionalProperties"] is False


def test_to_openai_tools_excludes_facade_only():
    reg = ToolRegistry()
    reg.register(
        {
            "name": "agent.turn",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "scope": "read",
            "stage": {"prospect": "M1"},
            "facade_only": True,
        },
        _ok_fn,
    )
    identity = _identity("prospect")
    tools = reg.to_openai_tools(identity, "M1")
    assert tools == []


def test_openapi_only_lists_visible_tools():
    reg = _matrix_registry()
    identity = _identity("prospect")
    doc = reg.openapi(identity, "M0")
    names_in_paths = list(doc["paths"].keys())
    assert "/tools/kb.get" in names_in_paths
    assert "/tools/kb.search" not in names_in_paths  # prospect 永不可見
    assert "/tools/jgb2.query.bills" not in names_in_paths  # prospect 永不可見


# ---------------------------------------------------------------------------
# 1.10 P2：`call()` 端剝身分鍵（不變量 18 的呼叫端半邊）
#
# 病灶（1.9 security review）：`register()` 只擋得到 **spec 側**宣告了身分鍵；
# 呼叫端（模型 tool_call／MCP client）仍可在 args 裡夾帶 `vendor_id` 之類，
# 指望被工具函式讀走。修法：`call()` 一律剝除並記 `IDENTITY_KEY:<鍵>`。
# ---------------------------------------------------------------------------

_IDENTITY_KEYS_CALL = ["vendor_id", "role_id", "user_id",
                       "target_user", "mode", "viewer_user_id"]


def _echo_registry() -> ToolRegistry:
    """一個把收到的 args 原樣回傳的工具（schema 允許 kb_id）。"""
    reg = ToolRegistry()
    reg.register(
        {
            "name": "kb.get",
            "description": "",
            "input_schema": {"type": "object",
                             "properties": {"kb_id": {"type": "string"}}},
            "scope": "read",
            "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
        },
        _ok_fn,
    )
    return reg


@pytest.mark.req("agentic-mcp-orchestration:1.10")
@pytest.mark.parametrize("bad_key", _IDENTITY_KEYS_CALL)
async def test_call_strips_identity_keys_from_args(bad_key):
    """夾帶的身分鍵：fn 收不到，且 violations 記到 `IDENTITY_KEY:<鍵>`。"""
    reg = _echo_registry()
    identity = _identity("tenant")

    result = await reg.call(
        identity, "kb.get", {"kb_id": "1", bad_key: "攻擊值"}, 1.0, stage="M0")

    assert result.ok is True, f"剝除不該讓呼叫失敗：{result}"
    assert result.data["echo"] == {"kb_id": "1"}, (
        f"fn 收到了身分鍵：{result.data['echo']}")
    notes = [v["note"] for v in reg.last_violations()]
    assert f"IDENTITY_KEY:{bad_key}" in notes, notes


@pytest.mark.req("agentic-mcp-orchestration:1.10")
async def test_call_without_identity_keys_records_no_violation():
    """正對照組：不夾帶身分鍵 ⇒ violations 空（證明上一條不是恆記）。"""
    reg = _echo_registry()
    identity = _identity("tenant")

    result = await reg.call(identity, "kb.get", {"kb_id": "1"}, 1.0, stage="M0")

    assert result.ok is True
    assert result.data["echo"] == {"kb_id": "1"}
    assert reg.last_violations() == [], reg.last_violations()


@pytest.mark.req("agentic-mcp-orchestration:1.10")
async def test_call_does_not_mutate_caller_args():
    """剝除走新字典 ⇒ ⛔ 不改到呼叫端手上的 dict。"""
    reg = _echo_registry()
    args = {"kb_id": "1", "vendor_id": 99}

    await reg.call(_identity("tenant"), "kb.get", args, 1.0, stage="M0")

    assert args == {"kb_id": "1", "vendor_id": 99}


@pytest.mark.req("agentic-mcp-orchestration:1.10")
def test_register_closes_schema_with_additional_properties_false():
    """`register()` 補 `additionalProperties: False`，且⛔ 不汙染呼叫端的原字典。"""
    original_schema = {"type": "object", "properties": {"kb_id": {"type": "string"}}}
    spec = {
        "name": "kb.get",
        "description": "",
        "input_schema": original_schema,
        "scope": "read",
        "stage": {"tenant": "M0"},
    }
    reg = ToolRegistry()
    reg.register(spec, _ok_fn)

    stored = reg.specs_for(_identity("tenant"), "M0")[0]
    assert stored["input_schema"]["additionalProperties"] is False
    assert "additionalProperties" not in original_schema, "改到呼叫端的模組級常數了"


@pytest.mark.req("agentic-mcp-orchestration:1.10")
async def test_closed_schema_rejects_undeclared_non_identity_key():
    """封閉 schema 的效果：未宣告的**非身分**鍵仍走 `INVALID_INPUT`。

    正對照：這證明 `additionalProperties: False` 真的生效——身分鍵之所以不會
    變成 `INVALID_INPUT`，是因為它們在④之前就被⓪剝掉了，不是這條規則沒作用。
    """
    reg = _echo_registry()

    result = await reg.call(
        _identity("tenant"), "kb.get", {"kb_id": "1", "nonsense": 1}, 1.0, stage="M0")

    assert result.ok is False and result.error == "INVALID_INPUT", result
