"""unit：專用對話 API（DSP-131；計畫 plan-dialogue-api-20261031 §5.1、§5.2 第 1～6 項）。

全部離線：ASGI transport（⛔ 真連線）、假 API key 驗證（`verify_api_key` 換成記憶體表）、
假 vendors 表、假計量落地（`finalize` 只記下 `_to_row` 會寫的那一列）、假 runtime。
認證三道檢查、`parse_identity`、`resolve_call`、`McpServiceGate`、`_invoke`、registry
守門、`agent.turn`／`agent.upload_ticket` 工具本身一律用**真的**。

對照（凍結驗收清單 §7）：
  DA2  兩入口同輸入、同 fake runtime、固定值 ⇒ 回應 dict 逐字相同；`usage_events` 列
       只差 channel／processing_path／answer_source；額度用盡的差異（F6）。
  DA3  缺金鑰、身分壞、vendor 越界、外部 Origin、超每小時上限、額度用盡 ⇒ 與 `/mcp`
       同樣被擋，HTTP 狀態依 §5.1。
  DA4  `_invoke` 對兩支工具實際會 raise 的每個代碼 ⇒ §5.1 狀態；表外代碼與未預期例外 500
       固定 body。
  DA5  新入口每呼叫恰一列、`channel="dialogue_api"`；`/mcp` 的列仍是 `"mcp"`。
  DA6  `entry="dialogue"` 的寫入工具可見性與 `/mcp` 同；`"rest"` 仍 fail-closed；
       Runtime 確認兌現段（runtime.py 尚未改）以 strict xfail 釘住，見該測試 docstring。
  F3   被服務層閘擋下的對話 API 嘗試也計入 `note_mcp_traffic`。
  F5   非 object body ⇒ 400、不進 `_invoke`；無 pydantic body 模型；`include_in_schema=False`。
  安全待查 1  body 上限與 MCP SDK 2.1.1 的 `DEFAULT_MAX_REQUEST_BODY_SIZE` 相同。
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import os
from types import SimpleNamespace

import httpx
import pytest

from routers import agent_dialogue
from services import api_key_auth
from services import usage_metering as um
from services.agent import mcp_facade as F
from services.agent import upload_store as US
from services.agent.identity import BACKEND_ENTRIES, DEFAULT_ENTRY_CHANNEL, Identity
from services.agent.tools.registry import ToolRegistry, ToolResult

from tests.unit.agent.test_agent_turn_unit_req import (
    FakeEngine,
    FakeProvider,
    _SlowRuntime,
    _app,
    _deps,
    _final_response,
    _runtime,
    _set_turns_per_hour,
)

pytestmark = pytest.mark.unit

_R = "agentic-mcp-orchestration:DSP-131"
DA2, DA3, DA4, DA5, DA6 = (f"{_R}:{n}" for n in ("DA2", "DA3", "DA4", "DA5", "DA6"))

API_KEY_ID = 7
SCOPED_KEY_ID = 8
VENDOR = 1
OTHER_VENDOR = 2
SESSION = "s-dialogue-1"
KEYS = {
    "k-open": {"id": API_KEY_ID, "name": "unit-open", "is_internal": False, "vendor_ids": None},
    "k-scoped": {"id": SCOPED_KEY_ID, "name": "unit-scoped", "is_internal": False,
                 "vendor_ids": [OTHER_VENDOR]},
}
VENDORS = {VENDOR, OTHER_VENDOR}
TURN = F.DIALOGUE_TURN_PATH
TICKET = F.DIALOGUE_UPLOAD_TICKET_PATH
PUBLIC_UPLOAD_URL = "https://chatai.example/rag-api/v1/agent/uploads"


# ═══════════════════════════════════════════════════════════════════
# 環境與假件
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)   # 任何 Origin 都拒
    monkeypatch.delenv("AGENT_ASSISTANT_KEY_IDS", raising=False)
    monkeypatch.delenv("USAGE_METERING_ENABLED", raising=False)
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "5")
    monkeypatch.setenv(US.UPLOAD_PUBLIC_URL_ENV, PUBLIC_UPLOAD_URL)
    monkeypatch.delenv(US.ATTACHMENT_INPUT_ENV, raising=False)
    _set_turns_per_hour(monkeypatch, 100)
    F.reset_agent_turn_cap()
    F.reset_premise_stats()
    US.STORE.reset()

    async def _verify(pool, key):
        return dict(KEYS[key]) if key in KEYS else None

    async def _vendor_exists(pool, vendor_id):
        return vendor_id in VENDORS

    # 只換掉「查 DB」的兩個點；`require_api_key_unconditional`／`resolve_call` 本身是真的。
    monkeypatch.setattr(api_key_auth, "verify_api_key", _verify)
    monkeypatch.setattr(F, "vendor_exists", _vendor_exists)
    yield
    F.reset_agent_turn_cap()
    F.reset_premise_stats()
    US.STORE.reset()


@pytest.fixture
def meter(monkeypatch):
    """`quota_check` 可切 ok／blocked；`finalize` 記下**真的會寫的那一列**（`um._to_row`）。"""
    rec = SimpleNamespace(rows=[], quota="ok")

    async def _quota_check(pool, vendor_id, is_internal):
        return SimpleNamespace(state=rec.quota)

    def _finalize(status="success", http_status=200, db_pool=None):
        ctx = um._ctx.get()
        if ctx is None or ctx._finalized:
            return
        ctx._finalized = True
        ctx.status = status
        ctx.http_status = http_status
        rec.rows.append(um._to_row(ctx))

    monkeypatch.setattr(um, "quota_check", _quota_check)
    monkeypatch.setattr(um, "finalize", _finalize)
    return rec


_FIXED_PID = "pid_fixed_0123456789abcdef"


class _FixedRuntime:
    """決定性 runtime：回同一張確認卡（固定 pending_id＝「固定 token」）、固定 trace_id。"""

    rules_sha = "fixed"

    def __init__(self) -> None:
        self.identities: list = []

    async def run_turn(self, identity, message, state, **kwargs):
        self.identities.append(identity)
        state.setdefault("agent", {})["turns"] = state.get("agent", {}).get("turns", 0) + 1
        return SimpleNamespace(
            answer=f"請確認：{message}（延期 3 天）",
            kind="answer",
            handoff=None,
            quick_replies=[
                {"label": "確認送出", "value": f"confirm_submit:{_FIXED_PID}"},
                {"label": "取消", "value": f"confirm_cancel:{_FIXED_PID}"},
            ],
            trace=SimpleNamespace(trace_id="trace-fixed-0001"),
            outcome={"state": "awaiting_confirm", "expects": "button",
                     "action": "bill_due_extend", "ref": None},
        )


def _setup(runtime=None, *, engine=None, upload=True, registry_cls=ToolRegistry):
    """同一份 registry／deps（兩入口共用的前提）。"""
    engine = engine if engine is not None else FakeEngine()
    deps = _deps(_app(runtime=runtime if runtime is not None else _FixedRuntime(),
                      engine=engine))
    reg = registry_cls()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    if upload:
        reg.register(F.UPLOAD_TICKET_SPEC, F._make_upload_ticket())
    return reg, deps, engine


def _http_app(registry, deps, *, gate=True):
    from fastapi import FastAPI

    a = FastAPI()
    a.include_router(agent_dialogue.build_router(registry, deps))
    if gate:
        # 與 app.py 同一個服務層閘（最外層）；`/mcp` 路徑也由它先擋。
        a.add_middleware(F.McpServiceGate, get_pool=lambda: None)
    return a


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _ident(**over) -> str:
    base = {"vendor_id": VENDOR, "session_id": SESSION, "target_user": "prospect",
            "mode": "b2b", "user_id": "88"}
    base.update(over)
    return json.dumps({k: v for k, v in base.items() if v is not None}, ensure_ascii=False)


def _headers(key="k-open", ident=None, origin=None, **ident_over) -> dict:
    h = {}
    if key is not None:
        h["X-API-Key"] = key
    h["X-JGB-Identity"] = ident if ident is not None else _ident(**ident_over)
    if origin is not None:
        h["Origin"] = origin
    return h


def _mcp_invoke(registry, deps):
    """`/mcp` 工具面實際呼叫的那一層（`build_mcp_server` 用的同一個包裝）。"""
    return F._mcp_tool_invoke(F._make_invoke(registry, deps, entry="mcp"))


async def _mcp_call(registry, deps, name, args, headers):
    return await _mcp_invoke(registry, deps)(name, SimpleNamespace(headers=headers), args)


def _strip_volatile(row: dict) -> dict:
    return {k: v for k, v in row.items()
            if k not in ("request_id", "ts", "date_tpe", "duration_ms")}


_ENTRY_FIELDS = ("channel", "processing_path", "answer_source")


# ═══════════════════════════════════════════════════════════════════
# DA2：兩入口等價
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA2)
async def test_turn_same_input_same_runtime_gives_identical_dict_and_rows(meter):
    """同一則訊息、同一個決定性 runtime（固定 pending_id／trace_id）⇒ 回應 dict 逐字相同；
    `usage_events` 列除 channel／processing_path／answer_source 外相同；runtime 收到的身分
    只差 `entry`。"""
    args = {"message": "幫我把帳單延期三天", "context": "帳單頁"}

    rt_mcp = _FixedRuntime()
    reg_m, deps_m, eng_m = _setup(rt_mcp)
    out_mcp = await _mcp_call(reg_m, deps_m, F.AGENT_TURN_NAME, args, _headers())

    rt_api = _FixedRuntime()
    reg_a, deps_a, eng_a = _setup(rt_api)
    async with _client(_http_app(reg_a, deps_a)) as c:
        resp = await c.post(TURN, json=args, headers=_headers())

    assert resp.status_code == 200, resp.text
    assert resp.json() == out_mcp
    assert set(out_mcp) == {"answer", "kind", "handoff", "quick_replies", "trace_id",
                            "session_expired", "outcome"}
    # 存下來的對話狀態也一樣（同一把命名空間鍵）；`last_turn_at` 是時鐘值，不比
    def _state_shape(rows):
        out = json.loads(json.dumps(rows))
        for st in out.values():
            assert isinstance(st["agent"].pop("last_turn_at"), (int, float))
        return out

    assert list(eng_a.rows) == list(eng_m.rows) == [f"mcp:{API_KEY_ID}:{VENDOR}:{SESSION}"]
    assert _state_shape(eng_a.rows) == _state_shape(eng_m.rows)
    assert len(eng_a.saved) == len(eng_m.saved) == 1

    # runtime 看到的身分：只差 entry
    (id_m,), (id_a,) = rt_mcp.identities, rt_api.identities
    assert (id_m.entry, id_a.entry) == ("mcp", "dialogue")
    assert dataclasses.replace(id_a, entry="mcp") == id_m

    # 一次呼叫恰一列；只差三個入口欄位
    assert len(meter.rows) == 2
    row_m, row_a = meter.rows
    assert {k: row_m[k] for k in _ENTRY_FIELDS} == {
        "channel": "mcp", "processing_path": f"mcp:{F.AGENT_TURN_NAME}",
        "answer_source": "mcp_tool"}
    assert {k: row_a[k] for k in _ENTRY_FIELDS} == {
        "channel": "dialogue_api", "processing_path": f"api:{F.AGENT_TURN_NAME}",
        "answer_source": "dialogue_api"}
    strip = lambda r: {k: v for k, v in _strip_volatile(r).items() if k not in _ENTRY_FIELDS}
    assert strip(row_a) == strip(row_m)
    assert (row_a["status"], row_a["http_status"]) == ("success", 200)


@pytest.mark.req(DA2)
async def test_turn_with_real_agent_runtime_matches_except_trace_id(meter):
    """正對照（真 `AgentRuntime`＋腳本化 provider）：除每回合現產的 `trace_id` 外逐鍵相同。"""
    args = {"message": "我想了解合約怎麼建立"}
    reg_m, deps_m, _ = _setup(_runtime(FakeProvider([_final_response(answer="先確認身分。")])))
    out_mcp = await _mcp_call(reg_m, deps_m, F.AGENT_TURN_NAME, args, _headers())

    reg_a, deps_a, _ = _setup(_runtime(FakeProvider([_final_response(answer="先確認身分。")])))
    async with _client(_http_app(reg_a, deps_a)) as c:
        resp = await c.post(TURN, json=args, headers=_headers())
    assert resp.status_code == 200, resp.text
    out_api = resp.json()
    assert out_api.pop("trace_id") and out_mcp.pop("trace_id")
    assert out_api == out_mcp


@pytest.mark.req(DA2)
async def test_upload_ticket_same_input_fixed_token_gives_identical_dict(meter, monkeypatch):
    fixed = SimpleNamespace(upload_token="upt_0123456789abcdef.FIXED", expires_at=1_793_185_000,
                            max_files=10, max_bytes=10 * 1024 * 1024,
                            accept=("image/jpeg", "image/png"))
    bindings: list = []

    def _issue(binding):
        bindings.append(binding)
        return fixed

    monkeypatch.setattr(US.STORE, "issue_ticket", _issue)
    args = {"attachment_purpose": "repair"}
    reg, deps, _ = _setup()
    out_mcp = await _mcp_call(reg, deps, F.UPLOAD_TICKET_NAME, args, _headers())
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TICKET, json=args, headers=_headers())
    assert resp.status_code == 200, resp.text
    assert resp.json() == out_mcp
    assert out_mcp["upload_url"] == PUBLIC_UPLOAD_URL
    # 兩入口綁到同一個 (api_key, vendor, user, role, session, purpose)——票跨入口通用
    assert len(bindings) == 2 and bindings[0] == bindings[1]
    assert [r["processing_path"] for r in meter.rows] == [
        f"mcp:{F.UPLOAD_TICKET_NAME}", f"api:{F.UPLOAD_TICKET_NAME}"]


@pytest.mark.req(DA2)
async def test_invalid_input_detail_is_the_same_text_on_both_entries(meter):
    """`/mcp` 的 ToolError 字串逐字不變（`"INVALID_INPUT: <detail>"`）；新入口拆成 code／detail。"""
    args = {"message": "看照片", "image_urls": ["https://x.example/a.jpg"]}
    reg, deps, _ = _setup()
    with pytest.raises(F._tool_error_cls()) as e:
        await _mcp_call(reg, deps, F.AGENT_TURN_NAME, args, _headers())
    assert str(e.value) == f"INVALID_INPUT: {F.URL_INPUT_DISABLED_DETAIL}"
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json=args, headers=_headers())
    assert resp.status_code == 400
    assert resp.json() == {"code": "INVALID_INPUT", "detail": F.URL_INPUT_DISABLED_DETAIL}


@pytest.mark.req(DA2)
async def test_quota_exhausted_difference_is_only_the_f6_one(meter):
    """F6：額度用盡時新入口由 `_invoke` 的 `quota_check` 擋，寫一列 blocked／429。
    （`/mcp` 在正式 app 由 `usage_metering_middleware` 先擋、不寫列；這裡直呼 `/mcp` 的
    `_invoke` 層，⛔ 經過那個 middleware，所以兩邊在這一層的行為相同——差異只在 app 層。）"""
    meter.quota = "blocked"
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert resp.status_code == 429
    assert resp.json() == {"code": F.ERR_QUOTA}
    assert len(meter.rows) == 1
    assert (meter.rows[0]["status"], meter.rows[0]["http_status"]) == ("blocked", 429)
    assert meter.rows[0]["channel"] == "dialogue_api"
    assert meter.rows[0]["processing_path"] == "quota_blocked"

    with pytest.raises(F._tool_error_cls()) as e:
        await _mcp_call(reg, deps, F.AGENT_TURN_NAME, {"message": "嗨"}, _headers())
    assert str(e.value) == F.ERR_QUOTA


# ═══════════════════════════════════════════════════════════════════
# DA3：各安全閘（經真的服務層閘），與 `/mcp` 同樣被擋
# ═══════════════════════════════════════════════════════════════════
_GATE_CASES = [
    ("缺金鑰", dict(key=None), 401, F.ERR_API_KEY),
    ("金鑰錯", dict(key="k-nope"), 401, F.ERR_API_KEY),
    ("身分不是 JSON", dict(ident="{nope"), 400, F.ERR_IDENTITY_MALFORMED),
    ("身分缺 vendor_id", dict(ident=json.dumps({"session_id": "s"})), 400,
     F.ERR_IDENTITY_NO_VENDOR),
    ("身分缺 session_id", dict(ident=json.dumps({"vendor_id": VENDOR})), 400,
     F.ERR_IDENTITY_NO_SESSION),
    ("vendor 不存在", dict(vendor_id=424242), 403, F.ERR_VENDOR_UNKNOWN),
    ("vendor 越出金鑰範圍", dict(key="k-scoped"), 403, F.ERR_VENDOR_OUT_OF_KEY_SCOPE),
    ("外部 Origin", dict(origin="https://evil.example"), 403, F.ERR_ORIGIN),
]


@pytest.mark.req(DA3)
@pytest.mark.parametrize("path", [TURN, TICKET])
@pytest.mark.parametrize("label,hdr,status,code", _GATE_CASES, ids=[c[0] for c in _GATE_CASES])
async def test_gate_blocks_dialogue_like_mcp(meter, path, label, hdr, status, code):
    reg, deps, engine = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(path, json={"message": "嗨", "attachment_purpose": "repair"}
                            if path == TICKET else {"message": "嗨"}, headers=_headers(**hdr))
        mcp = await c.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                           headers=_headers(**hdr))
    assert (resp.status_code, resp.json()) == (status, {"detail": code, "code": code}), label
    # 同一道閘、同一個請求對 `/mcp` 的回應完全相同
    assert (mcp.status_code, mcp.json()) == (resp.status_code, resp.json())
    assert meter.rows == [], "閘擋下的請求 ⛔ 進不到 _invoke（不寫列，與 /mcp 相同）"
    assert engine.saved == []


@pytest.mark.req(DA3)
async def test_gate_positive_control_passes_valid_request(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert resp.status_code == 200, resp.text


@pytest.mark.req(DA3)
async def test_hourly_cap_is_shared_with_mcp_and_answers_429(meter, monkeypatch):
    """每小時上限鍵是 (api_key_id, vendor_id)，兩入口共用同一個計數器。"""
    _set_turns_per_hour(monkeypatch, 1)
    F.reset_agent_turn_cap()
    reg, deps, engine = _setup()
    async with _client(_http_app(reg, deps)) as c:
        ok = await c.post(TURN, json={"message": "一"}, headers=_headers())
        blocked = await c.post(TURN, json={"message": "二"}, headers=_headers())
    assert ok.status_code == 200
    assert (blocked.status_code, blocked.json()) == (429, {"code": "RATE_LIMITED"})
    assert meter.rows[-1]["processing_path"] == f"api:{F.AGENT_TURN_NAME}:RATE_LIMITED"
    assert (meter.rows[-1]["status"], meter.rows[-1]["http_status"]) == ("blocked", 429)
    with pytest.raises(F._tool_error_cls()) as e:
        await _mcp_call(reg, deps, F.AGENT_TURN_NAME, {"message": "三"}, _headers())
    assert str(e.value) == "RATE_LIMITED"
    assert len(engine.saved) == 1


@pytest.mark.req(DA3)
async def test_identity_keys_in_body_cannot_override_identity(meter):
    """body 夾帶 vendor_id／user_id ⇒ registry 剝除（⛔ 覆寫身分）；`additionalProperties`
    仍由 registry 驗（剝完後 schema 乾淨就照跑）。"""
    rt = _FixedRuntime()
    reg, deps, _ = _setup(rt)
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨", "vendor_id": OTHER_VENDOR,
                                        "user_id": "999"}, headers=_headers())
        extra = await c.post(TURN, json={"message": "嗨", "dialog_ref": "x"},
                             headers=_headers())
    assert resp.status_code == 200, resp.text
    assert rt.identities[0].vendor_id == VENDOR and rt.identities[0].user_id == "88"
    assert (extra.status_code, extra.json()) == (400, {"code": "INVALID_INPUT"})


# ═══════════════════════════════════════════════════════════════════
# DA4：代碼 → HTTP（§5.1），逐碼
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA4)
@pytest.mark.parametrize("label,hdr,env,status,code", [
    ("API_KEY_REQUIRED", dict(key=None), {}, 401, F.ERR_API_KEY),
    ("ORIGIN_NOT_ALLOWED", dict(origin="https://evil.example"), {}, 403, F.ERR_ORIGIN),
    ("IDENTITY_MALFORMED", dict(ident="[1]"), {}, 400, F.ERR_IDENTITY_MALFORMED),
    ("IDENTITY_MISSING_VENDOR_ID", dict(ident=json.dumps({"session_id": "s"})), {}, 400,
     F.ERR_IDENTITY_NO_VENDOR),
    ("IDENTITY_MISSING_SESSION_ID", dict(ident=json.dumps({"vendor_id": VENDOR})), {}, 400,
     F.ERR_IDENTITY_NO_SESSION),
    ("IDENTITY_MISSING_USER_ID", dict(user_id=None), {"AGENT_ASSISTANT_KEY_IDS": str(API_KEY_ID)},
     400, F.ERR_IDENTITY_NO_USER),
    ("VENDOR_UNKNOWN", dict(vendor_id=424242), {}, 403, F.ERR_VENDOR_UNKNOWN),
    ("VENDOR_NOT_IN_KEY_SCOPE", dict(key="k-scoped"), {}, 403, F.ERR_VENDOR_OUT_OF_KEY_SCOPE),
])
async def test_request_layer_codes_without_gate_keep_their_status(
        meter, monkeypatch, label, hdr, env, status, code):
    """閘不在時（縱深第二層）`_invoke` 自己的 `resolve_call(entry="dialogue")` 擋；
    `McpRequestError.status` 一路帶到 HTTP，body 與閘相同。"""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps, gate=False)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers(**hdr))
    assert (resp.status_code, resp.json()) == (status, {"detail": code, "code": code}), label
    assert F.DIALOGUE_STATUS_BY_CODE[code] == status
    assert meter.rows == []


@pytest.mark.req(DA4)
async def test_metering_unavailable_is_503(meter, monkeypatch):
    monkeypatch.setenv("USAGE_METERING_ENABLED", "false")
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (503, {"code": F.ERR_METERING})


@pytest.mark.req(DA4)
async def test_agent_unavailable_is_503_and_writes_one_row(meter):
    deps = _deps(_app(engine=FakeEngine()))          # 沒有 agent_runtime
    reg = ToolRegistry()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (503, {"code": F.ERR_AGENT_UNAVAILABLE})
    assert [(r["status"], r["http_status"], r["processing_path"]) for r in meter.rows] == [
        ("error", 503, f"api:{F.AGENT_TURN_NAME}:{F.ERR_AGENT_UNAVAILABLE}")]


@pytest.mark.req(DA4)
async def test_preflight_invalid_input_long_session_is_400(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"},
                            headers=_headers(session_id="s" * 120))
    assert (resp.status_code, resp.json()) == (400, {"code": "INVALID_INPUT"})
    assert meter.rows[-1]["processing_path"] == f"api:{F.AGENT_TURN_NAME}:INVALID_INPUT"


@pytest.mark.req(DA4)
async def test_upload_ticket_namespace_failure_is_400(meter):
    """非 agent.turn 的工具：`namespaced_identity` 組不出鍵 ⇒ INVALID_INPUT，路徑前綴跟入口。"""
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TICKET, json={"attachment_purpose": "repair"},
                            headers=_headers(session_id="s" * 120))
    assert (resp.status_code, resp.json()) == (400, {"code": "INVALID_INPUT"})
    assert meter.rows[-1]["processing_path"] == f"api:{F.UPLOAD_TICKET_NAME}:INVALID_INPUT"


@pytest.mark.req(DA4)
async def test_upload_ticket_without_user_id_is_400_with_detail(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TICKET, json={"attachment_purpose": "repair"},
                            headers=_headers(user_id=None))
        bad_enum = await c.post(TICKET, json={"attachment_purpose": "selfie"},
                                headers=_headers())
    assert (resp.status_code, resp.json()) == (
        400, {"code": "INVALID_INPUT", "detail": F.USER_ID_REQUIRED_DETAIL})
    assert (bad_enum.status_code, bad_enum.json()) == (400, {"code": "INVALID_INPUT"})


@pytest.mark.req(DA4)
async def test_invisible_identity_is_404_no_match(meter):
    """tenant 看不到 agent.turn ⇒ NO_MATCH 404（⛔ 洩成 AGENT_UNAVAILABLE）。"""
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"},
                            headers=_headers(target_user="tenant", mode="b2c"))
    assert (resp.status_code, resp.json()) == (404, {"code": "NO_MATCH"})


@pytest.mark.req(DA4)
async def test_upload_ticket_not_registered_is_404(meter):
    reg, deps, _ = _setup(upload=False)
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TICKET, json={"attachment_purpose": "repair"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (404, {"code": "NO_MATCH"})


@pytest.mark.req(DA4)
async def test_tool_timeout_is_504(meter, monkeypatch):
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "0.05")
    reg, deps, engine = _setup(_SlowRuntime())
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "很慢"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (504, {"code": "TOOL_TIMEOUT"})
    assert engine.saved == []


@pytest.mark.req(DA4)
async def test_message_over_max_length_is_400(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "字" * 2001}, headers=_headers())
    assert (resp.status_code, resp.json()) == (400, {"code": "INVALID_INPUT"})


_TOOL_RESULT_CODES = [
    ("NO_MATCH", 404), ("TOOL_TIMEOUT", 504), ("CONFIRMATION_REQUIRED", 409),
    ("INVALID_INPUT", 400), ("RATE_LIMITED", 429), (None, 404),
]


@pytest.mark.req(DA4)
@pytest.mark.parametrize("path,tool", [(TURN, F.AGENT_TURN_NAME),
                                       (TICKET, F.UPLOAD_TICKET_NAME)])
@pytest.mark.parametrize("error,status", _TOOL_RESULT_CODES)
async def test_every_registry_error_code_maps_per_table(meter, monkeypatch, path, tool,
                                                        error, status):
    """registry 的封閉代碼集（`registry.ToolError`）＋`error=None` 逐一對 §5.1。
    `CONFIRMATION_REQUIRED` 對這兩支 read 工具走不到，仍照表 409。"""
    reg, deps, _ = _setup()

    async def _call(identity, name, args, timeout_s, **kw):
        assert name == tool
        return ToolResult(ok=False, error=error)

    monkeypatch.setattr(reg, "call", _call)
    body = {"message": "嗨"} if path == TURN else {"attachment_purpose": "repair"}
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(path, json=body, headers=_headers())
    assert (resp.status_code, resp.json()) == (status, {"code": error or "NO_MATCH"})
    assert len(meter.rows) == 1 and meter.rows[0]["http_status"] == 200   # 計量照舊：工具已回
    # `/mcp` 同一個結果 ⇒ ToolError 字串就是代碼
    with pytest.raises(F._tool_error_cls()) as e:
        await _mcp_call(reg, deps, tool, body, _headers())
    assert str(e.value) == (error or "NO_MATCH")


def test_registry_closed_error_domain_is_fully_mapped():
    """registry 的 `ToolError` 值域每一個都在 §5.1 表內（新增代碼忘了對表 ⇒ 紅）。"""
    from typing import get_args

    from services.agent.tools import registry as R

    assert set(get_args(R.ToolError)) <= set(F.DIALOGUE_STATUS_BY_CODE)


def test_status_table_matches_plan_5_1():
    assert F.DIALOGUE_STATUS_BY_CODE == {
        "IDENTITY_MALFORMED": 400, "IDENTITY_MISSING_VENDOR_ID": 400,
        "IDENTITY_MISSING_SESSION_ID": 400, "IDENTITY_MISSING_USER_ID": 400,
        "API_KEY_REQUIRED": 401,
        "ORIGIN_NOT_ALLOWED": 403, "VENDOR_UNKNOWN": 403, "VENDOR_NOT_IN_KEY_SCOPE": 403,
        "INVALID_INPUT": 400, "NO_MATCH": 404, "RATE_LIMITED": 429, "QUOTA_EXCEEDED": 429,
        "AGENT_UNAVAILABLE": 503, "METERING_UNAVAILABLE": 503, "TOOL_TIMEOUT": 504,
        "CONFIRMATION_REQUIRED": 409,
    }
    assert F.dialogue_status_for("SOMETHING_ELSE") == 500
    assert F.dialogue_status_for(None) == 500


@pytest.mark.req(DA4)
async def test_out_of_table_code_is_500_fixed_body(meter, monkeypatch):
    reg, deps, _ = _setup()

    async def _call(identity, name, args, timeout_s, **kw):
        return ToolResult(ok=False, error="WEIRD_NEW_CODE")

    monkeypatch.setattr(reg, "call", _call)
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (500, {"code": "INTERNAL_ERROR"})
    assert "WEIRD" not in resp.text


@pytest.mark.req(DA4)
async def test_unexpected_exception_is_500_without_exception_text(meter, monkeypatch):
    reg, deps, _ = _setup()

    async def _boom(identity, name, args, timeout_s, **kw):
        raise RuntimeError("SECRET-DSN postgres://user:pw@host/db")

    monkeypatch.setattr(reg, "call", _boom)
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, json={"message": "嗨"}, headers=_headers())
    assert (resp.status_code, resp.json()) == (500, {"code": "INTERNAL_ERROR"})
    assert "SECRET" not in resp.text and "postgres" not in resp.text
    assert [(r["status"], r["http_status"]) for r in meter.rows] == [("error", 500)]
    # `/mcp` 那一側照舊原樣往上拋（交給 SDK），⛔ 被包成 ToolError
    with pytest.raises(RuntimeError):
        await _mcp_call(reg, deps, F.AGENT_TURN_NAME, {"message": "嗨"}, _headers())


# ═══════════════════════════════════════════════════════════════════
# F5：body
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA4)
@pytest.mark.parametrize("raw", [b"[]", b'"hi"', b"1", b"null", b"{nope", b"", b"\xff\xfe{}",
                                 b'[{"message": "x"}]'])
@pytest.mark.parametrize("path", [TURN, TICKET])
async def test_non_object_body_is_400_and_never_reaches_invoke(meter, path, raw):
    rt = _FixedRuntime()
    reg, deps, engine = _setup(rt)
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(path, content=raw,
                            headers={**_headers(), "Content-Type": "application/json"})
    assert (resp.status_code, resp.json()) == (400, {"code": "INVALID_INPUT"})
    assert meter.rows == [] and rt.identities == [] and engine.saved == []
    assert "input" not in resp.json(), "⛔ 回顯輸入（pydantic 422 的形狀）"


def test_router_has_no_pydantic_body_model_and_is_hidden_from_schema():
    from fastapi import FastAPI
    from fastapi.routing import APIRoute

    reg, deps, _ = _setup()
    router = agent_dialogue.build_router(reg, deps)
    routes = {r.path: r for r in router.routes if isinstance(r, APIRoute)}
    assert set(routes) == {TURN, TICKET}
    for r in routes.values():
        assert r.methods == {"POST"}
        assert r.include_in_schema is False
        assert r.body_field is None, "⛔ pydantic body 模型（F5）"
    a = FastAPI()
    a.include_router(router)
    assert not set(a.openapi().get("paths", {})) & {TURN, TICKET}


def test_router_paths_are_under_gated_prefixes_and_not_upload_exempt():
    for path in F.DIALOGUE_PATHS:
        assert path.startswith(F.GATED_PREFIXES)
        assert path != US.UPLOAD_PATH
        assert not api_key_auth.is_exempt(path)
        assert not F.is_upload_request({"type": "http", "path": path, "method": "POST"})


def test_router_module_does_not_import_mcp_sdk():
    src = inspect.getsource(agent_dialogue)
    tree = ast.parse(src)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert names, "正對照：至少掃到 import"
    assert not [n for n in names if n == "mcp" or n.startswith("mcp.")]
    assert not hasattr(agent_dialogue, "router"), "只提供 build_router（同一份 registry）"


# ═══════════════════════════════════════════════════════════════════
# 安全待查 1：body 上限＝MCP SDK 2.1.1 的上限
# ═══════════════════════════════════════════════════════════════════
def test_body_cap_equals_mcp_sdk_default():
    from mcp.server.transport_security import DEFAULT_MAX_REQUEST_BODY_SIZE

    assert F.DIALOGUE_MAX_BODY_BYTES == DEFAULT_MAX_REQUEST_BODY_SIZE == 4 * 1024 * 1024


@pytest.mark.req(DA3)
async def test_body_over_cap_is_413_by_content_length(meter):
    rt = _FixedRuntime()
    reg, deps, _ = _setup(rt)
    big = b'{"message": "' + b"a" * F.DIALOGUE_MAX_BODY_BYTES + b'"}'
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, content=big,
                            headers={**_headers(), "Content-Type": "application/json"})
        ok = await c.post(TURN, json={"message": "a" * 100}, headers=_headers())
    assert (resp.status_code, resp.json()) == (413, {"code": F.DIALOGUE_BODY_TOO_LARGE})
    assert ok.status_code == 200          # 正對照
    assert len(rt.identities) == 1 and len(meter.rows) == 1


@pytest.mark.req(DA3)
async def test_body_over_cap_is_413_when_streamed_without_length(meter):
    rt = _FixedRuntime()
    reg, deps, _ = _setup(rt)

    async def _chunks():
        yield b'{"message": "'
        for _ in range(5):
            yield b"a" * (1024 * 1024)
        yield b'"}'

    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, content=_chunks(),
                            headers={**_headers(), "Content-Type": "application/json"})
    assert (resp.status_code, resp.json()) == (413, {"code": F.DIALOGUE_BODY_TOO_LARGE})
    assert rt.identities == [] and meter.rows == []


@pytest.mark.req(DA3)
async def test_body_cap_is_not_read_before_the_gate(meter):
    """閘先擋：沒金鑰的超大 body 回 401（⛔ 先讀 body）。"""
    reg, deps, _ = _setup()
    big = b"{" + b" " * (F.DIALOGUE_MAX_BODY_BYTES + 10) + b"}"
    async with _client(_http_app(reg, deps)) as c:
        resp = await c.post(TURN, content=big, headers=_headers(key=None))
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# DA5：計量
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA5)
async def test_each_dialogue_call_writes_exactly_one_row(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        for i in range(3):
            assert (await c.post(TURN, json={"message": f"第{i}句"},
                                 headers=_headers())).status_code == 200
        assert (await c.post(TICKET, json={"attachment_purpose": "document"},
                             headers=_headers())).status_code == 200
    assert len(meter.rows) == 4
    assert {r["channel"] for r in meter.rows} == {"dialogue_api"}
    assert {r["answer_source"] for r in meter.rows} == {"dialogue_api"}
    assert [r["processing_path"] for r in meter.rows] == (
        [f"api:{F.AGENT_TURN_NAME}"] * 3 + [f"api:{F.UPLOAD_TICKET_NAME}"])
    # 決策 13：is_internal 只由金鑰紀錄決定，session 前綴 ⛔ 不算
    assert {r["is_internal"] for r in meter.rows} == {False}
    assert {r["session_id"] for r in meter.rows} == {SESSION}


@pytest.mark.req(DA5)
async def test_mcp_rows_keep_mcp_values(meter):
    reg, deps, _ = _setup()
    await _mcp_call(reg, deps, F.AGENT_TURN_NAME, {"message": "嗨"}, _headers())
    assert len(meter.rows) == 1
    assert {k: meter.rows[0][k] for k in _ENTRY_FIELDS} == {
        "channel": "mcp", "processing_path": f"mcp:{F.AGENT_TURN_NAME}",
        "answer_source": "mcp_tool"}


def test_entry_metering_fields_fit_columns_and_cover_backend_entries():
    """欄寬：channel VARCHAR(20)、processing_path VARCHAR(60)、answer_source VARCHAR(40)。"""
    assert set(F._ENTRY_METERING) == set(BACKEND_ENTRIES)
    for entry, m in F._ENTRY_METERING.items():
        assert len(m["channel"]) <= 20 and len(m["answer_source"]) <= 40
        assert len(f"{m['path_prefix']}:{F.UPLOAD_TICKET_NAME}:INVALID_INPUT") <= 60
    assert F._ENTRY_METERING["mcp"] == {"channel": "mcp", "path_prefix": "mcp",
                                        "answer_source": "mcp_tool"}
    ident = Identity(vendor_id=1, target_user="tenant", mode="b2c", session_id="s")
    assert F._metering_fields(ident, entry="dialogue")["channel"] == "dialogue_api"
    assert F._metering_fields(ident)["channel"] == "mcp"
    with pytest.raises(ValueError):
        F._metering_fields(ident, entry="rest")


# ═══════════════════════════════════════════════════════════════════
# F3：流量計數
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA3)
async def test_gate_counts_blocked_dialogue_attempts(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        for path in (TURN, TICKET):
            assert (await c.post(path, json={}, headers=_headers(key=None))).status_code == 401
        # 反對照：同前綴但不是對話 API 的路徑，計數行為不變（不計）
        assert (await c.get("/api/v1/agent/trace", headers=_headers(key=None))).status_code == 401
    stats = F.premise_stats()
    assert F._STATS.calls_by_api_key.get("unknown") == 2, F._STATS.calls_by_api_key
    assert F._STATS.flagged_api_keys.get("unknown") == 2
    assert stats is not None


@pytest.mark.req(DA3)
async def test_successful_dialogue_call_is_counted_once(meter):
    reg, deps, _ = _setup()
    async with _client(_http_app(reg, deps)) as c:
        assert (await c.post(TURN, json={"message": "嗨"}, headers=_headers())).status_code == 200
    assert F._STATS.calls_by_api_key == {str(API_KEY_ID): 1}, "⛔ 閘與 _invoke 各計一次"


# ═══════════════════════════════════════════════════════════════════
# 同一份 registry（每分鐘上限掛在 registry 實例上）
# ═══════════════════════════════════════════════════════════════════
class _SpyRegistry(ToolRegistry):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen: list = []

    async def call(self, identity, name, args, timeout_s, **kw):
        self.seen.append((name, identity.entry))
        return await super().call(identity, name, args, timeout_s, **kw)


async def test_router_uses_the_registry_it_was_given(meter):
    reg, deps, _ = _setup(registry_cls=_SpyRegistry)
    async with _client(_http_app(reg, deps)) as c:
        await c.post(TURN, json={"message": "嗨"}, headers=_headers())
        await c.post(TICKET, json={"attachment_purpose": "repair"}, headers=_headers())
    assert reg.seen == [(F.AGENT_TURN_NAME, "dialogue"), (F.UPLOAD_TICKET_NAME, "dialogue")]


# ═══════════════════════════════════════════════════════════════════
# 結構化錯誤與 `/mcp` 包裝層
# ═══════════════════════════════════════════════════════════════════
def test_facade_call_error_str_is_the_legacy_tool_error_message():
    assert str(F.FacadeCallError("NO_MATCH", 404)) == "NO_MATCH"
    assert str(F.FacadeCallError("INVALID_INPUT", 400, "d")) == "INVALID_INPUT: d"


async def test_mcp_wrapper_converts_only_facade_errors():
    async def _raise_facade(name, ctx, args):
        raise F.FacadeCallError("INVALID_INPUT", 400, F.URL_INPUT_DISABLED_DETAIL)

    async def _raise_other(name, ctx, args):
        raise KeyError("x")

    with pytest.raises(F._tool_error_cls()) as e:
        await F._mcp_tool_invoke(_raise_facade)("t", None, {})
    assert str(e.value) == f"INVALID_INPUT: {F.URL_INPUT_DISABLED_DETAIL}"
    with pytest.raises(KeyError):
        await F._mcp_tool_invoke(_raise_other)("t", None, {})


# ═══════════════════════════════════════════════════════════════════
# DA6：entry 驗證、寫入工具可見性、確認兌現
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(DA6)
@pytest.mark.parametrize("bad", ["rest", None, "MCP", "", "api", 1, DEFAULT_ENTRY_CHANNEL])
async def test_parse_identity_and_resolve_call_reject_non_backend_entry(bad):
    with pytest.raises(ValueError):
        await F.parse_identity({"x-jgb-identity": _ident()}, key={"id": 7},
                               vendor_check=lambda _v: True, entry=bad)
    with pytest.raises(ValueError):
        await F.resolve_call(_headers(), None, entry=bad)
    with pytest.raises(ValueError):
        F._make_invoke(ToolRegistry(), _deps(_app()), entry=bad)


@pytest.mark.req(DA6)
async def test_entry_is_a_required_keyword():
    with pytest.raises(TypeError):
        await F.parse_identity({"x-jgb-identity": _ident()}, key={"id": 7},
                               vendor_check=lambda _v: True)
    with pytest.raises(TypeError):
        await F.resolve_call(_headers(), None)
    with pytest.raises(TypeError):
        F._make_invoke(ToolRegistry(), _deps(_app()))
    for fn in (F.parse_identity, F.resolve_call, F._make_invoke):
        p = inspect.signature(fn).parameters["entry"]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty


@pytest.mark.req(DA6)
@pytest.mark.parametrize("entry", sorted(BACKEND_ENTRIES))
async def test_parse_identity_stamps_the_given_backend_entry(entry):
    ident = await F.parse_identity({"x-jgb-identity": _ident()}, key={"id": 7},
                                   vendor_check=lambda _v: True, entry=entry)
    assert ident.entry == entry
    assert F.namespaced_identity(ident).entry == entry


def _write_registry():
    reg = ToolRegistry()
    reg.register(
        {"name": "jgb2.action.demo", "description": "d",
         "input_schema": {"type": "object",
                          "properties": {"payload": {"type": "object"},
                                         "confirmation_token": {"type": "string"}}},
         "scope": "write", "mcp_only": True, "stage": {"tenant": "M1"}},
        lambda *_a, **_k: None,
    )
    return reg


@pytest.mark.req(DA6)
@pytest.mark.parametrize("entry,visible", [("mcp", True), ("dialogue", True), ("rest", False),
                                           ("bogus", False), (None, False)])
def test_write_tool_visibility_dialogue_same_as_mcp_rest_fail_closed(monkeypatch, entry, visible):
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    # 寫入改接片 W8：寫入工具只給站內幫手金鑰 ⇒ 身分帶列入 `AGENT_ASSISTANT_KEY_IDS` 的金鑰 id（期望值不變）。
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "1")
    reg = _write_registry()
    ident = dataclasses.replace(
        Identity(vendor_id=1, target_user="tenant", mode="b2c", session_id="s", api_key_id=1),
        entry=entry)
    names = {s["name"] for s in reg.specs_for(ident, "M1", for_model=True)}
    assert ("jgb2.action.demo" in names) is visible


@pytest.mark.req(DA6)
def test_write_tool_invisible_to_every_entry_when_flag_off(monkeypatch):
    """正對照：旗標關 ⇒ 連後端入口也看不到（上一條的 True 不是恆真）。"""
    monkeypatch.delenv("AGENT_WRITE_TOOLS_ENABLED", raising=False)
    reg = _write_registry()
    for entry in sorted(BACKEND_ENTRIES):
        ident = Identity(vendor_id=1, target_user="tenant", mode="b2c", session_id="s",
                         entry=entry)
        assert "jgb2.action.demo" not in {s["name"] for s in reg.specs_for(ident, "M1")}


@pytest.fixture
def _freeze_confirm_today(monkeypatch):
    """與 `test_runtime_confirm_segment_req._freeze_today` 同一個凍結點（payload 是 2026-08）。"""
    from datetime import date as _date

    from services.jgb import bills as _bills

    monkeypatch.setattr(_bills, "_today", lambda: _date(2026, 8, 15))


@pytest.mark.req(DA6)
@pytest.mark.usefixtures("_freeze_confirm_today")
async def test_dialogue_entry_redeems_confirm_like_mcp():
    from tests.unit.agent import test_runtime_confirm_segment_req as C

    ok = await C._runtime(registry=C._receipt_registry(), pool=C.FakePool([C._redeem_row()])
                          ).run_turn(C._identity(entry="dialogue"), f"confirm_submit:{C._PID}",
                                     C._state_with_pending())
    assert "2026/08/18" in ok.answer


@pytest.mark.req(DA6)
@pytest.mark.usefixtures("_freeze_confirm_today")
async def test_rest_entry_still_never_redeems_and_mcp_does():
    """正對照（現況）：`mcp` 兌現得到、`rest` 一次 DB 都不碰。"""
    from tests.unit.agent import test_runtime_confirm_segment_req as C

    ok = await C._runtime(registry=C._receipt_registry(), pool=C.FakePool([C._redeem_row()])
                          ).run_turn(C._identity(entry="mcp"), f"confirm_submit:{C._PID}",
                                     C._state_with_pending())
    assert "2026/08/18" in ok.answer
    pool = C.FakePool([C._redeem_row()])
    await C._runtime(provider=C.FakeProvider([C._final_response(answer="模型接手")]),
                     registry=C._receipt_registry(), pool=pool
                     ).run_turn(C._identity(entry="rest"), f"confirm_submit:{C._PID}",
                                C._state_with_pending())
    assert pool.calls == []


def test_this_file_exists_for_invariant_31():
    """不變量 31 的對話 API 覆蓋登記指向本檔（`agent_boundary.check_31`）。"""
    assert os.path.basename(__file__) == "test_agent_dialogue_router_req.py"
