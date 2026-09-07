"""unit：MCP 門面的請求層閘與工具接線（spec agentic-mcp-orchestration 任務 1.7）。

涵蓋（design 元件 4）：
- `parse_identity` fail-closed 三型（JSON 不合法／缺 vendor_id／缺 session_id ⇒ 400）
  ＋兩型正規化（未知 target_user ⇒ tenant、mode 缺／非法 ⇒ b2c）
  ＋兩型 403（vendor 不在表、header vendor 不在 key 的 vendor_ids 內）。
- `check_origin` 三態＋`MCP_ALLOWED_ORIGINS` 未設定 ⇒ 啟動紅。
- `ToolError` 訊息只含業務代碼。
- 工具接線的每個 ToolSpec 都過 `registry.register`（不變量 27：無身分鍵）。
- **回歸鎖**：`/mcp` 的計量欄位 ⛔ 不含 `session_id`——傳進 `begin()` 就會被
  `INTERNAL_RULES` 的 `backtest_` 前綴判成內部流量而免額度（決策 13 要防的正是這個）。

⛔ 本檔不 import `mcp` SDK：2026-09-04 實查 mcp==2.1.1 與 fastapi==0.104.1
相依衝突（anyio<4 vs anyio>=4.9），正式 image 未裝，見 requirements.txt。
需要 SDK 的斷言（真 `ToolError` 型別）以 `mcp_sdk_available()` 分流。

⚠️ **檔名帶 `_unit_`，⛔ 不要改成 `test_mcp_facade_req.py`**：`tests/` 底下沒有
`__init__.py`，pytest 以檔名當模組名，與
`tests/integration/agent/test_mcp_facade_req.py`（該路徑被
`scripts/audit/checks/agent_boundary.py` 的不變量 31 逐字引用，不可改名）同名的話，
全量收集會 `import file mismatch` 而**整個 unit 層中斷**（1.7 實跑逼出；
1.4 的 `test_kb_tools_req.py` 已先踩過同一個坑）。
"""
import pytest

from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.agent import mcp_facade as F

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:1.7"


def _headers(identity_json=None, origin=None, api_key="k"):
    h = {}
    if api_key is not None:
        h["x-api-key"] = api_key
    if identity_json is not None:
        h["X-JGB-Identity"] = identity_json          # 刻意混大小寫：取值必須不敏感
    if origin is not None:
        h["Origin"] = origin
    return h


def _always_exists(_vendor_id):
    return True


# ════════════════════════════════════════════════════════════════════
# parse_identity：fail-closed 三型
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("raw,code", [
    ("{not json", F.ERR_IDENTITY_MALFORMED),
    ("[1,2,3]", F.ERR_IDENTITY_MALFORMED),
    ('{"session_id": "s1"}', F.ERR_IDENTITY_NO_VENDOR),
    ('{"vendor_id": "abc", "session_id": "s1"}', F.ERR_IDENTITY_NO_VENDOR),
    ('{"vendor_id": 1}', F.ERR_IDENTITY_NO_SESSION),
    ('{"vendor_id": 1, "session_id": "   "}', F.ERR_IDENTITY_NO_SESSION),
])
async def test_parse_identity_fail_closed_400(raw, code):
    with pytest.raises(F.McpRequestError) as e:
        await F.parse_identity(_headers(raw), key={"id": 7},
                               vendor_check=_always_exists)
    assert (e.value.status, e.value.code) == (400, code)


@pytest.mark.req(_SPEC)
async def test_parse_identity_missing_header_is_400():
    """完全沒帶 X-JGB-Identity 也算解析失敗（⛔ 不得預設出一個身分）。"""
    with pytest.raises(F.McpRequestError) as e:
        await F.parse_identity(_headers(None), key={"id": 7},
                               vendor_check=_always_exists)
    assert e.value.status == 400


@pytest.mark.req(_SPEC)
async def test_parse_identity_normalizes_unknown_target_user_to_tenant():
    ident = await F.parse_identity(
        _headers('{"vendor_id": 1, "session_id": "s1", "target_user": "hacker"}'),
        key={"id": 7}, vendor_check=_always_exists)
    assert ident.target_user == "tenant"
    # 正對照組：已知角色不得被改動
    ok = await F.parse_identity(
        _headers('{"vendor_id": 1, "session_id": "s1", "target_user": "prospect"}'),
        key={"id": 7}, vendor_check=_always_exists)
    assert ok.target_user == "prospect"


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("payload,expected", [
    ('{"vendor_id": 1, "session_id": "s"}', "b2c"),
    ('{"vendor_id": 1, "session_id": "s", "mode": "B2B"}', "b2c"),   # 大小寫不算合法值
    ('{"vendor_id": 1, "session_id": "s", "mode": "nonsense"}', "b2c"),
    ('{"vendor_id": 1, "session_id": "s", "mode": "b2b"}', "b2b"),   # 正對照組
])
async def test_parse_identity_mode_normalization(payload, expected):
    ident = await F.parse_identity(_headers(payload), key={"id": 7},
                                   vendor_check=_always_exists)
    assert ident.mode == expected


@pytest.mark.req(_SPEC)
async def test_parse_identity_unknown_vendor_is_403_and_counted():
    F.reset_premise_stats()
    with pytest.raises(F.McpRequestError) as e:
        await F.parse_identity(_headers('{"vendor_id": 424242, "session_id": "s"}'),
                               key={"id": 7}, vendor_check=lambda _v: False)
    assert (e.value.status, e.value.code) == (403, F.ERR_VENDOR_UNKNOWN)
    assert F.premise_stats()["vendor_not_in_table"] == 1


@pytest.mark.req(_SPEC)
async def test_key_vendor_scope_mismatch_is_403():
    key = {"id": 7, "vendor_ids": [2]}
    with pytest.raises(F.McpRequestError) as e:
        await F.parse_identity(_headers('{"vendor_id": 1, "session_id": "s"}'),
                               key=key, vendor_check=_always_exists)
    assert (e.value.status, e.value.code) == (403, F.ERR_VENDOR_OUT_OF_KEY_SCOPE)
    # 正對照組：同一把 key 對 vendor 2 應放行
    ident = await F.parse_identity(_headers('{"vendor_id": 2, "session_id": "s"}'),
                                   key=key, vendor_check=_always_exists)
    assert ident.vendor_id == 2 and ident.api_key_id == 7


@pytest.mark.req(_SPEC)
async def test_key_vendor_ids_null_means_unrestricted():
    """`vendor_ids IS NULL` ＝ 不限；空陣列 ＝ 全拒（⛔ 兩者不可混用）。"""
    unrestricted = await F.parse_identity(
        _headers('{"vendor_id": 9, "session_id": "s"}'),
        key={"id": 1, "vendor_ids": None}, vendor_check=_always_exists)
    assert unrestricted.vendor_id == 9
    with pytest.raises(F.McpRequestError) as e:
        await F.parse_identity(_headers('{"vendor_id": 9, "session_id": "s"}'),
                               key={"id": 1, "vendor_ids": []},
                               vendor_check=_always_exists)
    assert e.value.code == F.ERR_VENDOR_OUT_OF_KEY_SCOPE


@pytest.mark.req(_SPEC)
async def test_parse_identity_requires_vendor_check_argument():
    """`vendor_check` 是必填關鍵字——⛔ 不給預設值（預設值等於預設放行）。"""
    with pytest.raises(TypeError):
        await F.parse_identity(_headers('{"vendor_id": 1, "session_id": "s"}'))


# ════════════════════════════════════════════════════════════════════
# Origin 三態
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_origin_absent_is_allowed(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://ok.example")
    F.check_origin(_headers('{"vendor_id":1}'))          # 缺 Origin ⇒ 放行


@pytest.mark.req(_SPEC)
def test_origin_in_allowlist_is_allowed(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://ok.example,https://two.example")
    F.check_origin(_headers('{"vendor_id":1}', origin="https://two.example"))


@pytest.mark.req(_SPEC)
def test_origin_not_in_allowlist_is_403_and_counted(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://ok.example")
    F.reset_premise_stats()
    with pytest.raises(F.McpRequestError) as e:
        F.check_origin(_headers('{"vendor_id":1}', origin="https://evil.example"))
    assert (e.value.status, e.value.code) == (403, F.ERR_ORIGIN)
    assert F.premise_stats()["origin_not_allowed"] == 1


@pytest.mark.req(_SPEC)
def test_empty_origin_set_sentinel_rejects_every_origin(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    assert F.load_allowed_origins() == frozenset()
    F.check_origin(_headers('{"vendor_id":1}'))          # 缺 Origin 仍放行
    with pytest.raises(F.McpRequestError):
        F.check_origin(_headers('{"vendor_id":1}', origin="https://any.example"))


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("value", [None, "", "   "])
def test_allowed_origins_unset_raises_at_startup(monkeypatch, value):
    """未設定／空字串 ⇒ raise。⛔ 不得與「刻意空集合」共用同一表示法。"""
    if value is None:
        monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("MCP_ALLOWED_ORIGINS", value)
    with pytest.raises(RuntimeError, match="MCP_ALLOWED_ORIGINS"):
        F.load_allowed_origins()


@pytest.mark.req(_SPEC)
def test_service_gate_construction_fails_loud_without_allowlist(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        F.McpServiceGate(lambda *_a: None, get_pool=lambda: None)


# ════════════════════════════════════════════════════════════════════
# ToolError 訊息只含代碼
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("code", ["NO_MATCH", "TOOL_TIMEOUT", "RATE_LIMITED",
                                  "INVALID_INPUT", "CONFIRMATION_REQUIRED",
                                  F.ERR_API_KEY, F.ERR_ORIGIN, F.ERR_QUOTA])
def test_tool_error_message_is_code_only(code):
    assert F._tool_error_message(code) == code


@pytest.mark.req(_SPEC)
def test_tool_error_message_of_none_defaults_to_no_match():
    assert F._tool_error_message(None) == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_tool_error_instance_carries_only_the_code():
    """訊息只含代碼——⛔ 不論用的是 SDK 的 ToolError 還是無 SDK 時的替身。"""
    exc = F._tool_error_cls()(F._tool_error_message("NO_MATCH"))
    assert str(exc) == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_tool_error_cls_prefers_the_sdk_class_when_available():
    available, reason = F.mcp_sdk_available()
    if not available:
        assert F._tool_error_cls() is F.FacadeToolError
        pytest.skip(f"[env] MCP SDK 未安裝（{reason}）→ 未驗「真的用 SDK 的 ToolError」")
    from mcp.server.mcpserver.exceptions import ToolError

    assert F._tool_error_cls() is ToolError


# ════════════════════════════════════════════════════════════════════
# 工具接線：所有 spec 過 registry.register（不變量 27）
# ════════════════════════════════════════════════════════════════════
def _deps():
    return F.FacadeDeps(get_db_pool=lambda: None, get_kb_pool=lambda: None,
                        get_retriever=lambda: None)


@pytest.mark.req(_SPEC)
def test_build_registry_registers_expected_tools():
    reg = F.build_registry(_deps())
    names = {s["name"] for s in F.union_specs(reg, "M0")}
    assert names == {
        "kb.get", "kb.search", "help.read",
        "jgb2.query.bills", "jgb2.query.contracts", "jgb2.query.accounts",
        "jgb2.query.meters", "jgb2.query.estates", "jgb2.query.repairs",
    }


@pytest.mark.req(_SPEC)
def test_registered_specs_carry_no_identity_keys():
    """不變量 27 的正對照：`register()` 本身就是檢查點，能建起來即代表無身分鍵。"""
    from services.agent.tools.registry import _IDENTITY_KEYS

    reg = F.build_registry(_deps())
    for spec in F.union_specs(reg, "M0"):
        props = set((spec.get("input_schema") or {}).get("properties", {}).keys())
        assert not (props & _IDENTITY_KEYS), spec["name"]
    # 反對照：真的塞一個身分鍵進去必須被 register 擋下（否則上面那圈是空跑）
    bad = dict(F.HELP_READ_SPEC)
    bad["name"] = "help.read.bad"
    bad["input_schema"] = {"type": "object",
                           "properties": {"slug": {"type": "string"},
                                          "vendor_id": {"type": "integer"}}}
    with pytest.raises(ValueError, match="身分鍵"):
        reg.register(bad, lambda *_a, **_k: None)


@pytest.mark.req(_SPEC)
def test_prospect_cannot_see_kb_search_or_jgb2():
    reg = F.build_registry(_deps())
    prospect = Identity(vendor_id=1, target_user="prospect", mode="b2c")
    visible = {s["name"] for s in reg.specs_for(prospect, "M0", for_model=False)}
    assert "kb.get" in visible and "help.read" in visible      # 正對照組
    assert "kb.search" not in visible
    assert not any(n.startswith("jgb2.query.") for n in visible)


@pytest.mark.req(_SPEC)
def test_jgb2_face_enum_comes_from_the_face_builder_registries():
    from services.jgb.bills import BILL_FACE_BUILDERS

    reg = F.build_registry(_deps())
    spec = next(s for s in F.union_specs(reg, "M0") if s["name"] == "jgb2.query.bills")
    assert set(spec["input_schema"]["properties"]["face"]["enum"]) == set(BILL_FACE_BUILDERS)


# ════════════════════════════════════════════════════════════════════
# 薄包裝簽名生成（SDK 由函式簽名推 input schema）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_build_wrapper_signature_matches_input_schema():
    import inspect
    import typing

    captured = {}

    async def _invoke(name, ctx, args):
        captured["name"], captured["args"] = name, args
        return {"facts": "ok"}

    reg = F.build_registry(_deps())
    spec = next(s for s in F.union_specs(reg, "M0") if s["name"] == "jgb2.query.bills")

    class _FakeContext:      # SDK 未安裝時的替身：只需要有 `.headers`
        headers = {}

    fn = F._build_wrapper(spec, _invoke, _FakeContext)
    sig = inspect.signature(fn)
    assert list(sig.parameters) == ["ctx", "face", "ref", "keyword"]
    assert typing.get_origin(sig.parameters["face"].annotation) is typing.Literal
    assert sig.parameters["ref"].default is None

    out = await fn(_FakeContext(), face=sorted(spec["input_schema"]["properties"]["face"]["enum"])[0])
    assert out == {"facts": "ok"}
    assert captured["name"] == "jgb2.query.bills"
    # 未提供的選填參數 ⛔ 不得以 None 傳給 registry（schema 型別會判 INVALID_INPUT）
    assert set(captured["args"]) == {"face"}


# ════════════════════════════════════════════════════════════════════
# 額度：/mcp ⛔ 不套 INTERNAL_RULES 的 session 前綴（決策 13）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_metering_fields_exclude_session_id_and_message():
    """回歸鎖：把 session_id 傳進 `begin()` ⇒ `backtest_` 前綴會被判成內部流量
    而免額度，等於呼叫方可以自己關掉本系統唯一的控制（design 決策 13）。"""
    ident = Identity(vendor_id=1, target_user="tenant", mode="b2c",
                     session_id="backtest_should_still_be_metered")
    fields = F._metering_fields(ident)
    assert "session_id" not in fields
    assert "message" not in fields
    assert fields["vendor_id"] == 1 and fields["channel"] == "mcp"

    # 反對照：同一組 fields 加回 session_id 就會被判成內部流量
    from services.usage_metering import INTERNAL_RULES

    assert not any(pred(fields) for _k, pred in INTERNAL_RULES)
    leaky = dict(fields, session_id=ident.session_id)
    assert any(pred(leaky) for _k, pred in INTERNAL_RULES)


@pytest.mark.req(_SPEC)
def test_stamp_metering_context_uses_key_is_internal_not_session_prefix():
    from services.usage_metering import UsageContext
    from datetime import datetime, timezone

    ctx = UsageContext(request_id="r", ts=datetime.now(timezone.utc))
    ident = Identity(vendor_id=1, target_user="tenant", mode="b2c",
                     session_id="backtest_x")
    F._stamp_metering_context(ctx, ident, is_internal=False, name="kb.get")
    assert ctx.session_id == "backtest_x"
    assert ctx.is_internal is False and ctx.internal_kind is None
    assert ctx.processing_path == "mcp:kb.get"

    F._stamp_metering_context(ctx, ident, is_internal=True, name="kb.get")
    assert ctx.is_internal is True and ctx.internal_kind == "api_key"


# ════════════════════════════════════════════════════════════════════
# 服務層閘 ⛔ 不看 RAG_API_AUTH_ENFORCE
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_require_api_key_unconditional_401_even_when_enforce_off(monkeypatch):
    from fastapi import HTTPException

    from services.api_key_auth import require_api_key_unconditional

    monkeypatch.delenv("RAG_API_AUTH_ENFORCE", raising=False)
    with pytest.raises(HTTPException) as e:
        await require_api_key_unconditional({"x-api-key": "nope"}, None)
    assert e.value.status_code == 401


@pytest.mark.req(_SPEC)
def test_gated_prefixes_are_not_exempt():
    from services.api_key_auth import _EXEMPT_PREFIX, is_exempt

    for prefix in F.GATED_PREFIXES:
        assert not is_exempt(prefix)
    assert not any(str(p).startswith("/mcp") for p in _EXEMPT_PREFIX)
    # 正對照組：真的被豁免的路徑仍然豁免（否則上面兩行可能只是 is_exempt 壞了）
    assert is_exempt("/docs")


@pytest.mark.req(_SPEC)
def test_as_tool_result_wraps_1_5_1_6_dict_shapes():
    ok = F._as_tool_result({"ok": True, "data": {"facts": "x"},
                            "provenance": [{"source": "jgb2:bills#1", "text": "x",
                                            "citable": True}],
                            "text_for_model": "x"})
    assert isinstance(ok, ToolResult) and ok.ok and ok.provenance[0].source == "jgb2:bills#1"
    bad = F._as_tool_result({"ok": False, "error": "NO_MATCH"})
    assert bad.ok is False and bad.error == "NO_MATCH"
    assert F._as_tool_result("garbage").error == "NO_MATCH"      # fail-closed


@pytest.mark.req(_SPEC)
def test_union_specs_respects_stage_ceiling(monkeypatch):
    """`union_specs` 用 `specs_for` ⇒ stage 上限自動生效（M4/M5 工具在 M0 不註冊）。

    ⚠️ DSP-038-1／W1b：假 write 工具改成 W4 的合法形狀——`mcp_only=True`
    （`register()` 對 `scope="write"` 缺它會 raise）＋ `confirmation_token` 在
    `properties` 裡；旗標打開，`union_specs` 的探針自帶 `entry="mcp"`。
    ⛔ 旗標不開的話兩個斷言都會「不可見」而變成恆真，stage 上限根本沒被驗到。
    """
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    reg = F.build_registry(_deps())
    reg.register(
        {"name": "jgb2.action.demo", "description": "d",
         "input_schema": {"type": "object",
                          "properties": {"payload": {"type": "object"},
                                         "confirmation_token": {"type": "string"}}},
         "scope": "write", "mcp_only": True, "stage": {"tenant": "M4"}},
        lambda *_a, **_k: None,
    )
    assert "jgb2.action.demo" not in {s["name"] for s in F.union_specs(reg, "M0")}
    assert "jgb2.action.demo" in {s["name"] for s in F.union_specs(reg, "M4")}


@pytest.mark.req(_SPEC)
def test_registry_is_a_real_tool_registry():
    assert isinstance(F.build_registry(_deps()), ToolRegistry)
