"""unit：`to_openai_tools` 的 OpenAI strict function-calling 合法性（真線路 400 修復）。

背景：`registry.py:to_openai_tools` 對每個工具發 `"strict": True`，但
`parameters` 只補了 `additionalProperties: False`，沒有讓 `required` 涵蓋
`properties` 全部鍵——OpenAI strict function calling 要求 `required` 列出
`properties` 的每一個鍵。`jgb2.query.*` 的 `ref`／`keyword` 選填 ⇒ 真線路
（gpt-5-mini）回 400 `'required' is required to be supplied and to be an
array including every key in properties`。

覆蓋：
- `jgb2.query.bills` 序列化後 `required` 涵蓋全部鍵、`additionalProperties`
  ＝False、選填鍵（ref／keyword）可為 null、必填鍵（face）維持 enum 字串
- `agent.turn`（facade_only）不出現在 `to_openai_tools`
- 巢狀 object 每一層都被處理
- `registry.call()` 端選填鍵仍可整個省略（語義不變，用的是原始 input_schema）
- round-trip：`_openai_strict_parameters` 輸出的 `required` ⊇ `properties` 全部鍵

全部離線、假工具，不接觸真 DB／真 LLM／真 OpenAI。
"""
import pytest

from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry, ToolResult, _openai_strict_parameters

pytestmark = pytest.mark.unit


async def _ok_fn(identity, args):
    return ToolResult(ok=True, data={"echo": args}, text_for_model="ok")


def _identity(*, mode="b2b", target_user="tenant", api_key_id=1, vendor_id=1):
    return Identity(
        vendor_id=vendor_id,
        target_user=target_user,
        mode=mode,
        api_key_id=api_key_id,
        session_id="s1",
    )


def _jgb2_bills_spec():
    """對齊 `mcp_facade.py:_jgb2_spec` 的實際形狀（face 必填 enum，ref／keyword 選填）。"""
    return {
        "name": "jgb2.query.bills",
        "description": "查詢 bills 領域的決定性事實。",
        "input_schema": {
            "type": "object",
            "properties": {
                "face": {"type": "string", "enum": ["current", "history"]},
                "ref": {"type": "string"},
                "keyword": {"type": "string"},
            },
            "required": ["face"],
            "additionalProperties": False,
        },
        "scope": "read",
        "stage": {"property_manager": "M0", "tenant": "M0"},
    }


def _agent_turn_spec():
    return {
        "name": "agent.turn",
        "description": "整回合工具。",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
        "scope": "read",
        "stage": {"property_manager": "M0", "tenant": "M0"},
        "facade_only": True,
    }


def _nested_spec():
    """人造 fixture：巢狀 object（filter 選填、內含必填 city／選填 zip）。"""
    return {
        "name": "kb.search2",
        "description": "",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "filter": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "zip": {"type": "string"},
                    },
                    "required": ["city"],
                    "additionalProperties": False,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "scope": "read",
        "stage": {"tenant": "M0"},
    }


def _registry_with(*specs) -> ToolRegistry:
    reg = ToolRegistry()
    for spec in specs:
        reg.register(spec, _ok_fn)
    return reg


# ---------------------------------------------------------------------------
# (a) jgb2.query.bills 序列化後的 required／additionalProperties／nullable
# ---------------------------------------------------------------------------


def test_jgb2_bills_required_covers_all_keys_and_ref_keyword_nullable():
    reg = _registry_with(_jgb2_bills_spec())
    identity = _identity()
    tools = reg.to_openai_tools(identity, "M0")
    assert len(tools) == 1
    params = tools[0]["function"]["parameters"]

    assert set(params["required"]) == {"face", "ref", "keyword"}
    assert params["additionalProperties"] is False

    face_schema = params["properties"]["face"]
    assert face_schema["type"] == "string"
    assert face_schema["enum"] == ["current", "history"]

    ref_schema = params["properties"]["ref"]
    assert ref_schema["type"] == ["string", "null"]
    keyword_schema = params["properties"]["keyword"]
    assert keyword_schema["type"] == ["string", "null"]

    assert tools[0]["function"]["strict"] is True


# ---------------------------------------------------------------------------
# (b) facade_only 工具不出現在 to_openai_tools
# ---------------------------------------------------------------------------


def test_facade_only_agent_turn_excluded_from_openai_tools():
    reg = _registry_with(_agent_turn_spec())
    identity = _identity()
    tools = reg.to_openai_tools(identity, "M0")
    assert tools == []


# ---------------------------------------------------------------------------
# (c) 巢狀 object 每一層都處理
# ---------------------------------------------------------------------------


def test_nested_object_every_level_gets_additional_properties_false_and_full_required():
    reg = _registry_with(_nested_spec())
    identity = _identity(mode="b2c", target_user="tenant")
    tools = reg.to_openai_tools(identity, "M0")
    params = tools[0]["function"]["parameters"]

    # 頂層：query 必填、filter 選填（原 required 只有 query）
    assert set(params["required"]) == {"query", "filter"}
    assert params["additionalProperties"] is False

    filter_schema = params["properties"]["filter"]
    # filter 本身選填 ⇒ type 多收 null（["object","null"]），object 內部形狀不變
    assert filter_schema["type"] == ["object", "null"]
    assert filter_schema["additionalProperties"] is False
    assert set(filter_schema["required"]) == {"city", "zip"}
    assert filter_schema["properties"]["zip"]["type"] == ["string", "null"]
    # city 在巢狀層是必填 ⇒ 型別不變
    assert filter_schema["properties"]["city"]["type"] == "string"


# ---------------------------------------------------------------------------
# (d) call() 端選填鍵仍可省略（語義不變，走的是原始 input_schema）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_still_accepts_optional_keys_omitted():
    reg = _registry_with(_jgb2_bills_spec())
    identity = _identity()
    result = await reg.call(
        identity,
        "jgb2.query.bills",
        {"face": "current"},
        timeout_s=1.0,
        stage="M0",
    )
    assert result.ok is True
    assert result.error is None


# ---------------------------------------------------------------------------
# (e) round-trip：_openai_strict_parameters 輸出 required ⊇ properties 全部鍵
# ---------------------------------------------------------------------------


def _assert_required_covers_properties_recursively(schema: dict) -> None:
    if not isinstance(schema, dict):
        return
    if "properties" in schema:
        props = schema["properties"]
        assert set(schema.get("required", [])) == set(props.keys()), schema
        assert schema.get("additionalProperties") is False
        for sub in props.values():
            _assert_required_covers_properties_recursively(sub)
    if "items" in schema:
        _assert_required_covers_properties_recursively(schema["items"])
    for key in ("anyOf", "oneOf", "allOf"):
        for branch in schema.get(key, []) or []:
            _assert_required_covers_properties_recursively(branch)


def test_round_trip_required_covers_properties_for_jgb2_and_nested():
    for input_schema in (
        _jgb2_bills_spec()["input_schema"],
        _nested_spec()["input_schema"],
    ):
        out = _openai_strict_parameters(input_schema)
        _assert_required_covers_properties_recursively(out)


def test_openai_strict_parameters_does_not_mutate_input():
    original = _jgb2_bills_spec()["input_schema"]
    import copy

    snapshot = copy.deepcopy(original)
    _openai_strict_parameters(original)
    assert original == snapshot
