"""unit：入口隔離（`Identity.entry`）＋寫入工具旗標＋健檢兩旗
（子 spec `agent-write-tools` W1a｜DSP-038-1｜R4.4）。

三個面各一條、**互不代替**（Plan W1 驗收）：
  (i)   `specs_for`：可見清單
  (ii)  `registry.call(for_model=True)`：真的呼叫得到／呼叫不到
  (iii) `compute_agent_health` 的兩支旗標實得

⚠️ 為什麼 (i) 不能代替 (ii)：`specs_for` 是「模型看得到什麼」，`call()` 是
「實際打得通什麼」。Runtime 的兌現段是**繞過模型**直接呼 `registry.call(...)` 的
（W3），那條路只受 `call()` 的守門管——只驗清單會讓「清單裡沒有、但直呼還是通」
這個形狀完全看不見。

全部離線：假工具、假 pool、monkeypatch env，⛔ 不接觸真 DB／真 LLM。
"""
from __future__ import annotations

import pytest

from services.agent import health as health_mod
from services.agent.identity import DEFAULT_ENTRY_CHANNEL, Identity
from services.agent.tools.registry import (
    AGENT_WRITE_TOOLS_ENV,
    ToolRegistry,
    ToolResult,
    write_tools_enabled,
)

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.4"

#: 假的寫入工具＝**W4 會註冊的形狀**（`scope=write` ＋ `mcp_only=True` ＋ stage 依
#: design 元件 2 表：pm M1／tenant M4；prospect 缺鍵＝永不可見）。
_ACTION_SPEC = {
    "name": "jgb2.action.bill_due_extend",
    "description": "延後帳單到期日",
    "input_schema": {
        "type": "object",
        # ⚠️ `confirmation_token` 必須在 properties 裡（registry.register 會補
        #    additionalProperties=False，守門②放行後第④步才不會擋成 INVALID_INPUT）。
        "properties": {
            "payload": {"type": "object"},
            "confirmation_token": {"type": "string"},
        },
        "required": ["payload", "confirmation_token"],
    },
    "scope": "write",
    "mcp_only": True,
    "stage": {"property_manager": "M1", "tenant": "M4"},
}

_READ_SPEC = {
    "name": "kb.get",
    "description": "",
    "input_schema": {"type": "object", "properties": {"kb_id": {"type": "string"}}},
    "scope": "read",
    "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
}


async def _ok_fn(identity, args):
    return ToolResult(ok=True, data={"receipt": {"id": "R-1"}}, text_for_model="ok")


async def _always_redeemed(token, session_id):
    """本檔驗的是入口／旗標兩道閘，⛔ 不驗確認兌現（那是 W4 wrapper 的事，
    專責檔 `test_action_tools_req.py`）⇒ 恆真 checker，讓可見的工具**真的**通到底。"""
    return True


def _registry(**kwargs) -> ToolRegistry:
    kwargs.setdefault("redeem_checker", _always_redeemed)
    reg = ToolRegistry(**kwargs)
    reg.register(_READ_SPEC, _ok_fn)
    reg.register(_ACTION_SPEC, _ok_fn)
    return reg


def _pm(**overrides) -> Identity:
    base = dict(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="1", session_id="s1", api_key_id=1,
    )
    base.update(overrides)
    return Identity(**base)


# ---------------------------------------------------------------------------
# 0. 旗標解析與預設
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_flag_defaults_to_false_and_parses_truthy_values(monkeypatch):
    """未設 ⇒ False（fail-closed）；`{1,true,on,yes}` 不分大小寫 ⇒ True。"""
    monkeypatch.delenv(AGENT_WRITE_TOOLS_ENV, raising=False)
    assert write_tools_enabled() is False
    for truthy in ("1", "true", "TRUE", "on", "Yes"):
        monkeypatch.setenv(AGENT_WRITE_TOOLS_ENV, truthy)
        assert write_tools_enabled() is True, truthy
    for falsy in ("0", "false", "", "  ", "maybe"):
        monkeypatch.setenv(AGENT_WRITE_TOOLS_ENV, falsy)
        assert write_tools_enabled() is False, falsy


@pytest.mark.req(_REQ)
def test_identity_entry_defaults_to_rest():
    """⛔ 預設不得是 `"mcp"`——「忘了設」不可以等於「拿到寫入權」。"""
    assert DEFAULT_ENTRY_CHANNEL == "rest"
    assert Identity(vendor_id=1).entry == "rest"
    assert _pm().entry == "rest"
    assert _pm(entry="mcp").entry == "mcp"


# ---------------------------------------------------------------------------
# (i) specs_for：三種組合
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_specs_for_hides_mcp_only_from_default_rest_identity():
    """不帶 `entry` 的 Identity（＝REST 入口、health 探針、outline／eval 的假身分）
    ⇒ 拿不到 `mcp_only` 工具，即使旗標開著、stage 也到了。"""
    reg = _registry(write_tools_enabled=True)
    names = {s["name"] for s in reg.specs_for(_pm(), "M1", for_model=True)}
    assert "jgb2.action.bill_due_extend" not in names
    # 正對照組：同一次呼叫拿得到 read 工具 ⇒ 可見性規則本身沒壞
    assert "kb.get" in names


@pytest.mark.req(_REQ)
def test_specs_for_shows_mcp_only_when_entry_mcp_and_flag_on_and_stage_reached():
    reg = _registry(write_tools_enabled=True)
    names = {s["name"] for s in reg.specs_for(_pm(entry="mcp"), "M1", for_model=True)}
    assert "jgb2.action.bill_due_extend" in names

    # stage 未達（tenant 要 M4）⇒ 仍不可見：旗標 **AND** stage，⛔ 不是二選一
    tenant = Identity(
        vendor_id=1, target_user="tenant", mode="b2c",
        session_id="s1", api_key_id=1, entry="mcp",
    )
    assert "jgb2.action.bill_due_extend" not in {
        s["name"] for s in reg.specs_for(tenant, "M1", for_model=True)
    }
    assert "jgb2.action.bill_due_extend" in {
        s["name"] for s in reg.specs_for(tenant, "M4", for_model=True)
    }


@pytest.mark.req(_REQ)
def test_specs_for_hides_mcp_only_when_flag_off(monkeypatch):
    """旗標關 ⇒ 連 MCP 入口都看不到（R4.4）。釘住的值與現讀 env 兩種來源各驗一次。"""
    reg_pinned = _registry(write_tools_enabled=False)
    assert "jgb2.action.bill_due_extend" not in {
        s["name"] for s in reg_pinned.specs_for(_pm(entry="mcp"), "M1", for_model=True)
    }

    monkeypatch.delenv(AGENT_WRITE_TOOLS_ENV, raising=False)
    reg_env = _registry()          # write_tools_enabled=None ⇒ 現讀 env
    assert "jgb2.action.bill_due_extend" not in {
        s["name"] for s in reg_env.specs_for(_pm(entry="mcp"), "M1", for_model=True)
    }
    # 正對照組：同一個 registry，把 env 打開就看得見 ⇒ 上面看不見是旗標關的緣故
    monkeypatch.setenv(AGENT_WRITE_TOOLS_ENV, "true")
    assert "jgb2.action.bill_due_extend" in {
        s["name"] for s in reg_env.specs_for(_pm(entry="mcp"), "M1", for_model=True)
    }


@pytest.mark.req(_REQ)
def test_mcp_only_is_orthogonal_to_readonly_view_and_for_model():
    """`readonly_view` 仍照舊擋 write（DSP-016）；`for_model=False`（門面視角）
    也不會讓 `mcp_only` 對 REST 身分現形。"""
    reg = _registry(write_tools_enabled=True)
    assert "jgb2.action.bill_due_extend" not in {
        s["name"] for s in reg.specs_for(_pm(entry="mcp"), "M1", readonly_view=True)
    }
    assert "jgb2.action.bill_due_extend" not in {
        s["name"] for s in reg.specs_for(_pm(), "M1", for_model=False)
    }
    assert "jgb2.action.bill_due_extend" in {
        s["name"] for s in reg.specs_for(_pm(entry="mcp"), "M1", for_model=False)
    }


# ---------------------------------------------------------------------------
# (ii) registry.call：REST ⇒ NO_MATCH；MCP ⇒ 通
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_call_from_rest_identity_is_no_match_even_with_valid_token():
    """⚠️ 這條**不能**用 (i) 代替：Runtime 的兌現段是直呼 `registry.call`、不經模型
    清單，只驗清單看不見「清單沒有但直呼會通」。"""
    reg = _registry(write_tools_enabled=True)
    result = await reg.call(
        _pm(),                                   # entry 落預設 "rest"
        "jgb2.action.bill_due_extend",
        {"payload": {"bill_id": "900001"}, "confirmation_token": "tok-1"},
        timeout_s=1,
        stage="M1",
        for_model=True,
    )
    assert result.ok is False and result.error == "NO_MATCH"
    assert any(v["note"] == "FORBIDDEN" for v in reg.last_violations())


@pytest.mark.req(_REQ)
async def test_call_from_mcp_identity_succeeds():
    reg = _registry(write_tools_enabled=True)
    result = await reg.call(
        _pm(entry="mcp"),
        "jgb2.action.bill_due_extend",
        {"payload": {"bill_id": "900001"}, "confirmation_token": "tok-1"},
        timeout_s=1,
        stage="M1",
        for_model=True,
    )
    assert result.ok is True and result.data == {"receipt": {"id": "R-1"}}


@pytest.mark.req(_REQ)
async def test_call_with_flag_off_is_no_match_from_mcp_too():
    reg = _registry(write_tools_enabled=False)
    result = await reg.call(
        _pm(entry="mcp"),
        "jgb2.action.bill_due_extend",
        {"payload": {}, "confirmation_token": "tok-1"},
        timeout_s=1,
        stage="M1",
        for_model=True,
    )
    assert result.ok is False and result.error == "NO_MATCH"


# ---------------------------------------------------------------------------
# (iii) 健檢兩旗實得
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_health_reports_both_flags(monkeypatch):
    """兩旗都印得出來，且 ⛔ 不致紅（旗標關著是預設也是安全狀態）。"""
    # 健檢的其餘檢查全部走 monkeypatch 的樁：本測試只證明兩支旗的值。
    monkeypatch.setattr(health_mod.mcp_facade, "union_specs", lambda reg, stage: [_READ_SPEC])
    monkeypatch.setattr(health_mod.mcp_facade, "mcp_sdk_available", lambda: (True, ""))
    monkeypatch.setattr(health_mod.mcp_facade, "premise_stats", lambda: {})
    monkeypatch.setattr(health_mod.mcp_facade, "agent_configured", lambda: False)
    monkeypatch.setattr(health_mod, "_check_kb_reachable", _fake_kb_ok)
    monkeypatch.setattr(health_mod, "_check_agent_scope_ready", _fake_scope_ok)

    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    out = await health_mod.compute_agent_health(
        registry=_registry(write_tools_enabled=True), get_kb_pool=None, stage="M1",
    )
    assert out["checks"]["write_tools_enabled"] is True
    assert out["checks"]["use_mock_jgb_api"] is True
    assert out["status"] == "ok"

    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    out = await health_mod.compute_agent_health(
        registry=_registry(write_tools_enabled=False), get_kb_pool=None, stage="M1",
    )
    assert out["checks"]["write_tools_enabled"] is False
    assert out["checks"]["use_mock_jgb_api"] is False
    # ⛔ 兩旗皆不致紅
    assert out["status"] == "ok"


@pytest.mark.req(_REQ)
def test_health_mock_flag_defaults_to_true_like_jgb_system_api(monkeypatch):
    """`USE_MOCK_JGB_API` 未設 ⇒ True——與 `services/jgb_system_api.py` 的
    `os.getenv("USE_MOCK_JGB_API", "true")` 同語義（⛔ 兩邊不得分岔）。"""
    monkeypatch.delenv("USE_MOCK_JGB_API", raising=False)
    assert health_mod._use_mock_jgb_api() is True


async def _fake_kb_ok(get_kb_pool):
    return True, "ok"


async def _fake_scope_ok(get_api_key_pool):
    return True, "ok"


# ---------------------------------------------------------------------------
# (iv) S-5：憑證為空 ⇒ **建構期**大聲失敗（W1b）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_real_http_transport_refuses_empty_credential():
    """⚠️ 回歸守測：空憑證的 `X-API-Key` 送出去只會拿到 401，而那個 401 會被
    `_fallback_response()` 折成「暫時無法取得資料」——「這台機器沒帶憑證」於是
    看起來和「jgb2 剛好掛了」一模一樣。⛔ 不得改回「建得起來、呼叫時才失敗」。
    """
    from services.jgb.transport import MissingCredentialError, RealHttpTransport

    for empty in ("", "   ", None):
        with pytest.raises(MissingCredentialError):
            RealHttpTransport("https://example.invalid", empty, 1.0)
    # 正對照組：非空憑證建得起來 ⇒ 上面的 raise 是空值擋的，不是建構本身壞了
    assert RealHttpTransport("https://example.invalid", "K", 1.0).api_key == "K"


@pytest.mark.req(_REQ)
def test_jgb_system_api_fails_loud_when_real_mode_has_no_credential(monkeypatch):
    """`USE_MOCK_JGB_API=false` ＋ 無 `JGB_API_KEY` ⇒ `JGBSystemAPI()` 當場炸。"""
    from services.jgb.transport import MissingCredentialError
    from services.jgb_system_api import JGBSystemAPI

    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    monkeypatch.setenv("JGB_API_KEY", "")
    with pytest.raises(MissingCredentialError):
        JGBSystemAPI()

    # 正對照組①：有憑證就建得起來（且真的是 real 模式）
    monkeypatch.setenv("JGB_API_KEY", "dummy-key")
    assert JGBSystemAPI().use_mock is False
    # 正對照組②：mock 模式不受影響，且**不持有** real transport
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setenv("JGB_API_KEY", "")
    assert JGBSystemAPI()._real_transport is None


# ---------------------------------------------------------------------------
# (v) R8：健檢第三支旗 `verifier_observe_only`
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_verifier_observe_only_parses_truthy_and_defaults_false(monkeypatch):
    monkeypatch.delenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, raising=False)
    assert health_mod.verifier_observe_only() is False
    for truthy in ("1", "true", "YES", "On"):
        monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, truthy)
        assert health_mod.verifier_observe_only() is True, truthy
    for falsy in ("0", "false", "", "  ", "maybe"):
        monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, falsy)
        assert health_mod.verifier_observe_only() is False, falsy


@pytest.mark.req(_REQ)
async def test_health_reports_verifier_observe_only(monkeypatch):
    """三支旗都印得出來、都 ⛔ 不致紅；`verifier_observe_only` 與 `entry` 無關。"""
    monkeypatch.setattr(health_mod.mcp_facade, "union_specs", lambda reg, stage: [_READ_SPEC])
    monkeypatch.setattr(health_mod.mcp_facade, "mcp_sdk_available", lambda: (True, ""))
    monkeypatch.setattr(health_mod.mcp_facade, "premise_stats", lambda: {})
    monkeypatch.setattr(health_mod.mcp_facade, "agent_configured", lambda: False)
    monkeypatch.setattr(health_mod, "_check_kb_reachable", _fake_kb_ok)
    monkeypatch.setattr(health_mod, "_check_agent_scope_ready", _fake_scope_ok)
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

    monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, "1")
    out = await health_mod.compute_agent_health(
        registry=_registry(write_tools_enabled=True), get_kb_pool=None, stage="M1")
    assert out["checks"]["verifier_observe_only"] is True
    assert out["status"] == "ok", "⛔ 這支旗不致紅（它是組態事實，不是故障）"

    # 正對照組：關掉就印 False ⇒ 上面的 True 不是硬編的
    monkeypatch.delenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, raising=False)
    out = await health_mod.compute_agent_health(
        registry=_registry(write_tools_enabled=True), get_kb_pool=None, stage="M1")
    assert out["checks"]["verifier_observe_only"] is False
