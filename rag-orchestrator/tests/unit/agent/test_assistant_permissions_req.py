"""unit：站內幫手 S5 權限（plan-assistant-11-items-20261014 §3i 第 1～8 點；A1 查無、A3(a)～(e)）。

被測物：`mcp_facade`（站內幫手金鑰必帶 user_id、F1 會話綁身分、viewer）、`tools/jgb2`
（查無 vs 沒查成）、`runtime`（前置查詢判定、確認卡建立者、釘住範圍閘）、`turn_context`／
`completed_actions`（新動作單號、物件只印名稱）、`services/jgb/transport.py`（F8 log、4xx、
6b 依團隊折疊、讀取紀錄）、`jgb_system_api`（role＋viewer）。
資料走真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`，contract: proposed）；
全部離線。每條附正對照；變異清單見回報。
"""
from __future__ import annotations

import ast
import asyncio
import json
import logging
import sys
import types
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from tests.unit.agent.confirm_pool_double import attach_token_tx  # 第 3 步 A7：token 寫入交易替身

from services import jgb_system_api as api_mod
from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.completed_actions import completed_actions_line
from services.agent.confirm_card import render_receipt
from services.agent.identity import Identity
from services.agent.runtime import (
    PENDING_CONFIRM_KEY,
    PRE_LOOKUP_LABEL,
    PRE_LOOKUP_NOT_FOUND_TEXT,
    SCOPE_EXIT_TEXT,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    _recent_ref_ids,
)
from services.agent.tools import action as action_tools
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.registry import Provenance, ToolRegistry, ToolResult
from services.agent.turn_context import OUTCOME_REF_TYPES, make_outcome, receipt_ref
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb import transport as tr
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RecordingTransport

from tests.unit.agent.test_assistant_write_actions_req import (
    _bill_payload,
    _contract_payload,
    _estate_payload,
)
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, FakeRegistry, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call, _final_response,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
ROLE, FOREIGN_ROLE = "20151", "30999"
OWNER, PART = "12291", "990002"
TODAY = date(2026, 10, 15)
#: fixture 人工查證：只有 12291 看得到的帳單／合約／物件
OWNER_ONLY_BILL, OWNER_ONLY_CONTRACT = 769258, 79994
OWNER_ONLY_ESTATE, OWNER_ONLY_ESTATE_TITLE = 22491, "台北大安-古亭歐風優質套房B"
ESTATE_A, ESTATE_A_TITLE = 68926, "測試物件"
SERVICES_AGENT = Path(__file__).resolve().parents[3] / "services" / "agent"


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)


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


def _pm(user=OWNER, role=ROLE, **over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b", role_id=role,
                user_id=user, session_id="mcp:1:4:s5", api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


def _pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    pool.fetchrow = AsyncMock(return_value={"x": 1})          # assert_redeemed ⇒ True
    return attach_token_tx(pool)


# ════════════════════════════════════════════════════════════════════
# 第 1 點：站內幫手金鑰必帶 user_id、字面 anonymous 拒、vendor 不在 key 範圍 403
# ════════════════════════════════════════════════════════════════════
def _headers(**payload) -> dict:
    base = {"vendor_id": 4, "session_id": "s1", "target_user": "property_manager", "mode": "b2b",
            "role_id": ROLE}
    base.update(payload)
    return {"x-jgb-identity": json.dumps({k: v for k, v in base.items() if v is not None})}


async def _vendor_ok(vendor_id):
    return True


async def test_assistant_key_requires_user_id(monkeypatch):
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "5, 7")
    with pytest.raises(F.McpRequestError) as err:
        await F.parse_identity(_headers(), key={"id": 7, "vendor_ids": None}, vendor_check=_vendor_ok)
    assert (err.value.status, err.value.code) == (400, F.ERR_IDENTITY_NO_USER)
    ok = await F.parse_identity(_headers(user_id=OWNER), key={"id": 7, "vendor_ids": None},
                                vendor_check=_vendor_ok)
    assert ok.user_id == OWNER
    # 正對照：不在名單的金鑰照舊（pm 單證）
    other = await F.parse_identity(_headers(), key={"id": 9, "vendor_ids": None}, vendor_check=_vendor_ok)
    assert other.user_id is None
    # 未設定 ⇒ 不對任何金鑰啟用
    monkeypatch.delenv("AGENT_ASSISTANT_KEY_IDS", raising=False)
    assert (await F.parse_identity(_headers(), key={"id": 7, "vendor_ids": None},
                                   vendor_check=_vendor_ok)).user_id is None


def test_bad_assistant_key_ids_fail_loud_at_startup(monkeypatch):
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "5,x")
    with pytest.raises(RuntimeError):
        F.assistant_key_ids()
    with pytest.raises(RuntimeError):
        F.build_registry(F.FacadeDeps(get_db_pool=lambda: None))
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "5,7")
    assert F.assistant_key_ids() == frozenset({5, 7})


async def test_literal_anonymous_user_id_is_rejected():
    with pytest.raises(F.McpRequestError) as err:
        await F.parse_identity(_headers(user_id="anonymous"), key={"id": 9, "vendor_ids": None},
                               vendor_check=_vendor_ok)
    assert (err.value.status, err.value.code) == (400, F.ERR_IDENTITY_MALFORMED)


async def test_vendor_outside_key_scope_is_403():
    with pytest.raises(F.McpRequestError) as err:
        await F.parse_identity(_headers(user_id=OWNER), key={"id": 9, "vendor_ids": [1]},
                               vendor_check=_vendor_ok)
    assert (err.value.status, err.value.code) == (403, F.ERR_VENDOR_OUT_OF_KEY_SCOPE)


async def test_identity_keys_are_stripped_and_pm_write_without_user_id_is_no_match():
    seen: list = []
    spec = {"name": "jgb2.query.bills", "description": "x", "scope": "read",
            "input_schema": {"type": "object", "properties": {"face": {"type": "string"}},
                             "additionalProperties": False},
            "stage": {"property_manager": "M0"}}

    async def fn(identity, args):
        seen.append(dict(args))
        return ToolResult(ok=True, data={})

    reg = ToolRegistry()
    reg.register(spec, fn)
    await reg.call(_pm(), "jgb2.query.bills", {"face": "x", "role_id": "1", "user_id": "2"},
                   timeout_s=3, stage="M1")
    assert seen == [{"face": "x"}]
    # runtime 記 violation（身分鍵被剝）
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[_fake_tool_call(
            "kb.get", {"kb_id": "1", "role_id": "999"}, call_id="c1")])),
        _final_response(answer="好的。")])
    rt = AgentRuntime(provider, FakeRegistry(), FakeVerifier([VerifierVerdict(ok=True)] * 3),
                      FakeAssembler(), Budget(), stage="M1", clock=FakeClock())
    res = await rt.run_turn(_pm(), "麻煩幫我看一下這筆資料的狀況謝謝", {})
    assert "IDENTITY_KEY:role_id" in res.trace.violations
    # pm 寫入缺 user_id ⇒ NO_MATCH
    wreg = ToolRegistry(write_tools_enabled=True, redeem_checker=AsyncMock(return_value=True))
    for s, f in action_tools.ACTION_SPECS:
        wreg.register(s, f)
    r = await wreg.call(_pm(user=None), "jgb2.action.estate_create",
                        {"payload": _estate_payload(), "confirmation_token": "t"},
                        timeout_s=5, stage="M1", for_model=True)
    assert (r.ok, r.error) == (False, "NO_MATCH")


# ════════════════════════════════════════════════════════════════════
# 第 1 點：執行期覆蓋——每條 agent 工具路徑的每一筆 jgb2 呼叫都帶 role＋viewer
# ════════════════════════════════════════════════════════════════════
def _api_method_names() -> set:
    tree = ast.parse((SERVICES_AGENT.parent / "jgb_system_api.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "JGBSystemAPI")
    return {f.name for f in cls.body
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and not f.name.startswith("_")}


def _ast_call_sites(methods: set) -> set:
    """`services/agent/**` 內呼叫 `JGBSystemAPI` 公開方法的點：`(檔名, 外層函式 qualname, 方法)`。"""
    sites: set = set()
    for path in sorted(SERVICES_AGENT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def walk(node, stack):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    walk(child, stack + [child.name])
                    continue
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr in methods):
                    sites.add((path.name, ".<locals>.".join(stack), child.func.attr))
                walk(child, stack)

        walk(tree, [])
    return sites


class _RowEngine:
    """F1 用的 `form_sessions` 替身：多列、有列 id、`user_id` 欄、COLLECTING／COMPLETED。"""

    def __init__(self):
        self.rows: list = []

    def _collecting(self, sid):
        return [r for r in self.rows if r["sid"] == sid and r["state"] == "COLLECTING"]

    async def get_state(self, sid):
        rows = self._collecting(sid)
        return json.loads(json.dumps(rows[-1]["data"])) if rows else None

    async def get_state_row(self, sid):
        rows = self._collecting(sid)
        if not rows:
            return None
        r = rows[-1]
        return {"id": r["id"], "user_id": r["user_id"], "collected_data": json.loads(json.dumps(r["data"]))}

    async def start(self, sid, user_id, vendor_id, config_key, seed_topic=None, role_id=None):
        data = {"config_key": config_key, "collected_fields": {}, "asked_count": 0,
                "session_id": sid, "user_id": user_id, "vendor_id": vendor_id, "role_id": role_id}
        self.rows.append({"id": len(self.rows) + 1, "sid": sid, "user_id": user_id,
                          "state": "COLLECTING", "data": json.loads(json.dumps(data))})
        return data

    async def save(self, sid, state):
        raise AssertionError("⛔ 不得再以 session_id 存「最新一列」")

    async def save_by_id(self, row_id, state):
        for r in self.rows:
            if r["id"] == row_id and r["state"] == "COLLECTING":
                r["data"] = json.loads(json.dumps(state))

    async def close(self, sid):
        for r in self._collecting(sid):
            r["state"] = "COMPLETED"


async def test_every_jgb2_call_from_every_agent_path_carries_role_and_viewer(api, monkeypatch):
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    monkeypatch.delenv("AGENT_ASSISTANT_KEY_IDS", raising=False)

    # 記下每一次 API 呼叫的**呼叫端**（檔名＋qualname），對 AST 呼叫點做覆蓋比對
    methods = _api_method_names()
    covered: set = set()
    for name in methods:
        original = getattr(api, name)

        def make(n, fn):
            async def wrapper(*a, **k):
                caller = sys._getframe(1).f_code
                covered.add((Path(caller.co_filename).name, caller.co_qualname, n))
                return await fn(*a, **k)
            return wrapper
        setattr(api, name, make(name, original))

    class _Spy:
        async def run_turn(self, identity, message, state, **kw):
            return types.SimpleNamespace(answer="ok", kind="answer", handoff=None,
                                         quick_replies=[], trace=types.SimpleNamespace(trace_id="t"),
                                         outcome=None)

    pool = _pool()
    app = types.SimpleNamespace(state=types.SimpleNamespace(
        agent_runtime=_Spy(), agent_session_store=_RowEngine(),
        agent_audiences=frozenset({"property_manager"})))
    deps = F.FacadeDeps(get_db_pool=lambda: pool, get_app=lambda: app, stage="M1")
    reg = F.build_registry(deps)
    who = F.namespaced_identity(_pm())

    async def call(name, args):
        return await reg.call(who, name, args, timeout_s=10, stage="M1", for_model=True)

    bill = [b for b in fixture_store._DATA["bills"] if b["id"] == OWNER_ONLY_BILL][0]
    before = date(bill["date_expire"] // 10000, bill["date_expire"] // 100 % 100, bill["date_expire"] % 100)
    after = max(before, TODAY) + timedelta(days=3)
    due_payload = {"action": "bill_due_extend", "bill_id": str(OWNER_ONLY_BILL),
                   "date_expire_before": before.strftime("%Y%m%d"), "days": 3,
                   "date_expire_after": after.strftime("%Y%m%d")}
    category = fixture_store._DATA["repair_categories"][0]["name"]

    await call("jgb2.query.bills", {"face": "帳單異常", "ref": str(OWNER_ONLY_BILL)})
    await call("jgb2.query.bills", {"face": "帳單異常", "keyword": "租金"})
    await call("jgb2.query.bills", {"face": "帳單異常"})
    await call("jgb2.query.contracts", {"face": "合約基本資料", "ref": str(OWNER_ONLY_CONTRACT)})
    await call("jgb2.query.contracts", {"face": "合約基本資料", "keyword": "測試"})
    await call("jgb2.query.contracts", {"face": "合約基本資料"})
    await call("jgb2.query.meters", {"face": sorted(__import__("services.jgb.iot", fromlist=["x"]).METER_FACE_BUILDERS)[0], "keyword": "電"})
    await call("jgb2.query.accounts", {"face": "團隊成員權限", "ref": OWNER})
    await call("jgb2.query.accounts", {"face": "團隊成員權限", "keyword": "a"})
    await call("jgb2.query.estates", {"face": "物件現況診斷", "keyword": ESTATE_A_TITLE})
    await call("jgb2.query.repairs", {"face": "修繕進度"})
    await call("jgb2.stats.unpaid_bills", {"scope": "overdue"})
    await call("jgb2.stats.in_progress_repairs", {})
    await call("jgb2.stats.expiring_contracts", {"months": 3})
    s = {"summary": "確認"}
    await call("confirm.request", {**s, "payload": json.dumps({
        "action": "repair_create", "estate_name": ESTATE_A_TITLE, "description": "壞了",
        "category_name": category}, ensure_ascii=False)})
    await call("confirm.request", {**s, "payload": json.dumps({
        "action": "bill_due_extend", "estate_name": ESTATE_A_TITLE, "period": "這個月", "days": 3},
        ensure_ascii=False)})
    await call("confirm.request", {**s, "payload": json.dumps(_contract_payload(), ensure_ascii=False)})
    await call("confirm.request", {**s, "payload": json.dumps(_bill_payload(), ensure_ascii=False)})
    await call("confirm.request", {**s, "payload": json.dumps(
        {k: v for k, v in _bill_payload(estate_name=ESTATE_A_TITLE).items() if k != "contract_ref"},
        ensure_ascii=False)})
    await call("jgb2.action.bill_due_extend", {"payload": due_payload, "confirmation_token": "t1"})
    await call("jgb2.action.repair_create", {"payload": {
        "action": "repair_create", "estate_name": ESTATE_A_TITLE, "description": "壞了"},
        "confirmation_token": "t2"})
    await call("jgb2.action.estate_create", {"payload": _estate_payload(), "confirmation_token": "t3"})
    await call("jgb2.action.contract_create", {"payload": dict(_contract_payload(), estate_id=ESTATE_A),
                                               "confirmation_token": "t4"})
    await call("jgb2.action.manual_bill_create", {"payload": dict(_bill_payload(), contract_id=89481),
                                                  "confirmation_token": "t5"})
    # 照片回合（門面閉包 `_repair_category_tree`）
    from services.agent import image_fetch

    async def fetch(url, *, timeout_s):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (8, 8)).save(buf, format="JPEG")
        return image_fetch.FetchedImage(data=buf.getvalue(), content_type="image/jpeg")

    async def recognize(*a, **k):
        return {"is_damage": False, "confidence": 0.1}
    monkeypatch.setattr(F, "_image_fetch_one", fetch)
    monkeypatch.setattr(F, "_image_recognize_batch", recognize)
    image_fetch.reset_image_count_cap()
    turn = await reg.call(_pm(session_id="s5img"), F.AGENT_TURN_NAME,
                          {"message": "看照片", "image_urls": ["https://relay.jgbsmart.com/a.jpg"]},
                          timeout_s=30, stage="M1")
    assert turn.ok, turn.error

    # ① 每一筆實際送出的 params／body 都帶 role 與 viewer（寫入 body：role_id＋user_id）
    calls = api._mock_transport.calls
    bodies = api._mock_transport.bodies
    assert len(calls) >= 28
    missing = []
    for (method, path, params), body in zip(calls, bodies):
        source = body if method in ("POST", "PATCH") else (params or {})
        if method in ("POST", "PATCH"):
            ok = source.get("role_id") not in (None, "") and source.get("user_id") not in (None, "")
        else:
            has_role, has_viewer = tr.JGBMockTransport._identity_flags(path, source)
            ok = has_role and has_viewer
        if not ok:
            missing.append((method, tr.endpoint_template(method, path)))
    assert missing == [], f"沒帶 role＋viewer 的 jgb2 呼叫：{missing}"
    # ② AST 呼叫點每一個都被上面至少一條執行期路徑跑到
    sites = _ast_call_sites(methods)
    agent_files = {p.name for p in SERVICES_AGENT.rglob("*.py")}
    covered_agent = {c for c in covered if c[0] in agent_files}
    assert sites, "正對照：AST 掃描要找得到呼叫點"
    assert sites - covered_agent == set(), f"沒被執行期測試跑到的呼叫點：{sites - covered_agent}"


# ════════════════════════════════════════════════════════════════════
# 第 2 點：查無 vs 沒查成
# ════════════════════════════════════════════════════════════════════
class _CannedApi:
    def __init__(self, resp):
        self.resp = resp

    async def get_bills(self, **kw):
        return self.resp

    async def get_contracts(self, **kw):
        return self.resp


@pytest.mark.parametrize("resp,shape", [
    ({"success": True, "data": []}, "not_found"),
    ({"success": False, "error": {"code": 404, "message": "x"}}, "not_found"),
    ({"success": False, "error": {"code": 403, "message": "x"}}, "not_found"),
    ({"success": False, "error": {"code": 500, "message": "x"}}, "failed"),
    ({"success": False, "error": {"code": 401, "message": "x"}}, "failed"),
    ({"success": False, "data": []}, "failed"),
])
async def test_not_found_and_failed_are_two_shapes(monkeypatch, resp, shape):
    monkeypatch.setattr(jgb2_tools, "_api_singleton", _CannedApi(resp))
    r = await jgb2_tools.query_contracts(_pm(), {"face": "合約基本資料", "ref": "123"})
    if shape == "not_found":
        assert r == jgb2_tools._not_found()
        assert r["provenance"][0]["text"] == PRE_LOOKUP_NOT_FOUND_TEXT == jgb2_tools.NOT_FOUND_TEXT
    else:
        assert r == {"ok": False, "error": "NO_MATCH"}                 # ⛔ 附任何句子


async def test_pre_lookup_only_counts_marked_not_found(monkeypatch):
    marked = ToolResult(ok=False, error="NO_MATCH",
                        provenance=[Provenance(source=jgb2_tools.NOT_FOUND_SOURCE,
                                               text=jgb2_tools.NOT_FOUND_TEXT, citable=True)])

    async def run(results):
        provider = FakeProvider([_final_response(answer="好的。")])
        rt = AgentRuntime(provider, FakeRegistry(call_results=results),
                          FakeVerifier([VerifierVerdict(ok=True)] * 3), FakeAssembler(), Budget(),
                          stage="M1", clock=FakeClock())
        res = await rt.run_turn(_pm(), "999999", {})
        blocks = [str(m.get("content")) for m in provider.calls[0]["messages"] if m.get("role") == "user"]
        return res, blocks

    res, blocks = await run([ToolResult(ok=False, error="NO_MATCH")])   # 上游 500 ⇒ 無標記
    assert not any(PRE_LOOKUP_LABEL in b for b in blocks)
    assert res.trace.pre_lookup == {"kind": "id", "hits": 0}
    res2, blocks2 = await run([marked] * 3)                             # 正對照：查無 ⇒ 注入
    assert any(PRE_LOOKUP_NOT_FOUND_TEXT in b for b in blocks2)


async def test_query_bills_for_unseen_bill_cites_the_not_found_sentence(api):
    for ident in (_pm(user=PART), _pm(user=OWNER, role=FOREIGN_ROLE)):
        r = await jgb2_tools.query_bills(ident, {"face": "帳單異常", "ref": str(OWNER_ONLY_BILL)})
        assert r == jgb2_tools._not_found()
        assert str(OWNER_ONLY_BILL) not in json.dumps(r, ensure_ascii=False)
    c = await jgb2_tools.query_contracts(_pm(user=OWNER, role=FOREIGN_ROLE),
                                         {"face": "合約基本資料", "ref": str(OWNER_ONLY_CONTRACT)})
    assert c == jgb2_tools._not_found()
    ok = await jgb2_tools.query_bills(_pm(), {"face": "帳單異常", "ref": str(OWNER_ONLY_BILL)})
    assert ok["ok"] is True                                              # 正對照


async def test_get_bills_exception_logs_class_name_only(api, monkeypatch, caplog):
    """F8：`get_bills` 解析例外只記類別名（⛔ 例外訊息——可能帶 query／識別碼）。
    ⚠️ 回傳形狀（`success:false`）的改動被既有測試擋住，見回報。"""
    async def boom(*a, **k):
        raise RuntimeError(f"role_id={ROLE}&user_id={OWNER}")
    monkeypatch.setattr(api, "get_bill_detail", boom)
    with caplog.at_level(logging.DEBUG):
        await api.get_bills(ROLE, OWNER, bill_ref="123456", viewer_user_id=OWNER)
    blob = "\n".join(r.getMessage() for r in caplog.records)
    assert "RuntimeError" in blob and OWNER not in blob and ROLE not in blob


# ════════════════════════════════════════════════════════════════════
# 第 6 點：F8——真 HTTP transport 的 log 只有方法／樣板／類別／狀態碼；4xx 保留
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("status", [403, 404, 500])
async def test_real_transport_logs_template_only_and_keeps_4xx(monkeypatch, caplog, status):
    def handler(request):
        return httpx.Response(status, json={"detail": "x"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(tr.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    t = tr.RealHttpTransport("https://jgb.example.test", "k", 3)
    with caplog.at_level(logging.DEBUG, logger=tr.__name__):
        resp = await t.send("GET", f"/api/external/v1/roles/{ROLE}/members/{OWNER}/permissions",
                            params={"keyword": "王小明", "viewer_user_id": OWNER, "role_id": ROLE})
    assert resp["success"] is False
    assert resp["error"]["code"] == (status if status < 500 else 500)
    blob = "\n".join(r.getMessage() for r in caplog.records if r.name == tr.__name__)
    assert "/roles/{role_id}/members/{user_id}/permissions" in blob and "HTTPStatusError" in blob
    for secret in (ROLE, OWNER, "王小明", "jgb.example.test"):
        assert secret not in blob


# ════════════════════════════════════════════════════════════════════
# 第 6b 點：替身讀端點依團隊折疊
# ════════════════════════════════════════════════════════════════════
async def test_foreign_team_reads_fold_like_not_found(api):
    m = api._mock_transport.inner
    own = await m.send("GET", f"/api/external/v1/bills/{OWNER_ONLY_BILL}",
                       params={"role_id": ROLE, "viewer_user_id": OWNER})
    assert own["success"] is True                                        # 正對照
    for path, params in (
        (f"/api/external/v1/bills/{OWNER_ONLY_BILL}", {"role_id": FOREIGN_ROLE, "viewer_user_id": OWNER}),
        (f"/api/external/v1/estates/{ESTATE_A}", {"role_id": FOREIGN_ROLE, "viewer_user_id": OWNER}),
        (f"/api/external/v1/estates/{OWNER_ONLY_ESTATE}", {"role_id": ROLE, "viewer_user_id": PART}),
    ):
        r = await m.send("GET", path, params=params)
        assert r["success"] is False and r["error"]["code"] == 404, path
    for path in ("/api/external/v1/bills", "/api/external/v1/contracts/status-overview",
                 "/api/external/v1/repairs"):
        r = await m.send("GET", path, params={"role_id": FOREIGN_ROLE})
        assert r["success"] is True and r["data"] == [], path
        own_list = await m.send("GET", path, params={"role_id": ROLE})
        assert own_list["data"], f"正對照：{path} 本團隊列表非空"


async def test_estate_detail_sends_role_and_viewer(api):
    r = await api.get_estate_detail(estate_id=ESTATE_A, role_id=ROLE, viewer_user_id=OWNER)
    assert r["success"] is True
    _, path, params = api._mock_transport.calls[-1]
    assert params == {"role_id": ROLE, "viewer_user_id": OWNER}
    r2 = await api.get_estate_detail(estate_id=ESTATE_A, role_id=ROLE, viewer_user_id=PART)
    assert r2["success"] is False


async def test_patch_due_date_body_carries_identity_and_folds_unseen_bill(api):
    ok = await api.agent_patch_bill_due_date(OWNER_ONLY_BILL, "2027-07-01", role_id=ROLE, user_id=OWNER)
    assert ok["success"] is True
    assert api._mock_transport.bodies[-1] == {"due_date": "2027-07-01", "role_id": ROLE, "user_id": OWNER}
    no = await api.agent_patch_bill_due_date(OWNER_ONLY_BILL, "2027-07-02", role_id=ROLE, user_id=PART)
    assert no["success"] is False and no["error"]["code"] == 404


# ════════════════════════════════════════════════════════════════════
# 第 7 點：accounts 的 ref 組路徑前只收純數字
# ════════════════════════════════════════════════════════════════════
async def test_accounts_ref_must_be_digits(api):
    for bad in ("../1", "1/permissions", "1?x=1", "abc"):
        r = await jgb2_tools.query_accounts(_pm(), {"face": "團隊成員權限", "ref": bad})
        assert r == {"ok": False, "error": "INVALID_INPUT"}
    assert not any("/members/.." in c[1] or "?" in c[1] for c in api._mock_transport.calls)
    ok = await jgb2_tools.query_accounts(_pm(), {"face": "團隊成員權限", "ref": OWNER})
    assert ok["ok"] is True                                              # 正對照


# ════════════════════════════════════════════════════════════════════
# 第 1 點：替身讀取紀錄（只記布林，寫入紀錄行數不受影響）
# ════════════════════════════════════════════════════════════════════
async def test_read_log_records_flags_only(api, monkeypatch, tmp_path):
    log = tmp_path / "writes.jsonl"
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    await api.get_contracts(ROLE, keyword="測試", viewer_user_id=OWNER)
    await api.get_repair_categories()
    reads = [json.loads(x) for x in (tmp_path / ("writes.jsonl" + tr.JGBMockTransport.READ_LOG_SUFFIX)
                                     ).read_text(encoding="utf-8").splitlines()]
    assert reads == [
        {"endpoint_key": "contracts", "template": "/api/external/v1/contracts/status-overview",
         "has_role_id": True, "has_viewer": True},
        {"endpoint_key": "repair_categories", "template": "/api/external/v1/repairs/categories",
         "has_role_id": False, "has_viewer": False},
    ]
    text = (tmp_path / ("writes.jsonl" + tr.JGBMockTransport.READ_LOG_SUFFIX)).read_text(encoding="utf-8")
    for value in (ROLE, OWNER, "測試"):
        assert value not in text
    assert not log.exists()                                              # 讀 ⛔ 進寫入紀錄


# ════════════════════════════════════════════════════════════════════
# 主 session 2026-10-15 補測：990002 對只有 12291 看得到的物件建修繕單
# ════════════════════════════════════════════════════════════════════
async def test_part_member_cannot_create_a_repair_on_an_unseen_estate(api, monkeypatch, tmp_path):
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(tmp_path / "w.jsonl"))
    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=AsyncMock(return_value=True))
    for s, f in action_tools.ACTION_SPECS:
        reg.register(s, f)
    payload = {"action": "repair_create", "estate_name": OWNER_ONLY_ESTATE_TITLE,
               "description": "冷氣不冷"}
    before = len(api._mock_transport.inner.repair_fixtures.rows())
    # 兌現端（偽造 payload 直呼寫入工具）：NO_MATCH、⛔ 發出寫入
    r = await reg.call(_pm(user=PART), "jgb2.action.repair_create",
                       {"payload": payload, "confirmation_token": "forged"},
                       timeout_s=5, stage="M1", for_model=True)
    assert (r.ok, r.error) == (False, "NO_MATCH")
    assert len(api._mock_transport.inner.repair_fixtures.rows()) == before
    assert not (tmp_path / "w.jsonl").exists()
    estate_call = [c for c in api._mock_transport.calls if c[1] == "/api/external/v1/estates"][-1]
    assert estate_call[2]["viewer_user_id"] == PART
    # 正對照：12291 同一句照常建單
    ok = await reg.call(_pm(), "jgb2.action.repair_create",
                        {"payload": payload, "confirmation_token": "real"},
                        timeout_s=5, stage="M1", for_model=True)
    assert ok.ok, ok.error
    assert len(api._mock_transport.inner.repair_fixtures.rows()) == before + 1


async def test_card_side_estate_lookup_uses_viewer(api, monkeypatch):
    """出卡端：`_open_repairs` 以 viewer 解析——990002 解析不出 22491 ⇒ 帶 viewer 零命中
    ⇒ 查無固定句、⛔ 出卡（S5 修正輪，主 session 2026-10-15 裁示）；12291 解析得出（正對照）。"""
    pool = _pool()
    deps = F.FacadeDeps(get_db_pool=lambda: pool, stage="M1")
    reg = F.build_registry(deps)
    args = {"summary": "確認", "payload": json.dumps({
        "action": "repair_create", "estate_name": OWNER_ONLY_ESTATE_TITLE, "description": "冷氣不冷"},
        ensure_ascii=False)}
    part = await reg.call(F.namespaced_identity(_pm(user=PART)), "confirm.request", args,
                          timeout_s=10, stage="M1", for_model=True)
    assert (part.ok, part.error) == (False, "NO_MATCH") and [p.source for p in part.provenance] == [jgb2_tools.NOT_FOUND_SOURCE]
    estate_call = [c for c in api._mock_transport.calls if c[1] == "/api/external/v1/estates"][-1]
    assert estate_call[2]["viewer_user_id"] == PART
    own = await reg.call(F.namespaced_identity(_pm()), "confirm.request", args,
                         timeout_s=10, stage="M1", for_model=True)
    assert own.ok and own.data["estate_id"] == str(OWNER_ONLY_ESTATE)


async def test_confirm_request_unseen_estate_for_contract_is_not_found(api):
    from services.agent.tools.confirm import confirm_request
    payload = _contract_payload(estate_name=OWNER_ONLY_ESTATE_TITLE)
    r = await confirm_request(_pm(user=PART), {"summary": "x", "payload": json.dumps(payload, ensure_ascii=False)},
                              db_pool=_pool())
    assert r.ok is False and r.error == "NO_MATCH"
    assert [p.source for p in r.provenance] == [jgb2_tools.NOT_FOUND_SOURCE]
    ok = await confirm_request(_pm(), {"summary": "x", "payload": json.dumps(payload, ensure_ascii=False)},
                               db_pool=_pool())
    assert ok.ok is True                                                 # 正對照


# ════════════════════════════════════════════════════════════════════
# 第 3 點：F1——會話與確認卡綁 (user_id, role_id)
# ════════════════════════════════════════════════════════════════════
class _SeeRuntime:
    """記下每回合拿到的 state（看得到前一人的 dialog 嗎）；回合結束時寫一句 dialog。"""

    def __init__(self, gate=None):
        self.seen: list = []
        self.gate = gate

    async def run_turn(self, identity, message, state, **kw):
        agent = state.setdefault("agent", {})
        self.seen.append(json.loads(json.dumps(agent)))
        if self.gate is not None and message == "A":
            await self.gate.wait()
        agent.setdefault("dialog", []).append({"role": "user", "content": message})
        return types.SimpleNamespace(answer="ok", kind="answer", handoff=None, quick_replies=[],
                                     trace=types.SimpleNamespace(trace_id="t"), outcome=None)


def _turn_registry(engine, runtime):
    app = types.SimpleNamespace(state=types.SimpleNamespace(
        agent_runtime=runtime, agent_session_store=engine,
        agent_audiences=frozenset({"property_manager"})))
    reg = ToolRegistry()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(F.FacadeDeps(get_db_pool=lambda: None,
                                                                    get_app=lambda: app)))
    return reg


async def _turn(reg, identity, message):
    return await reg.call(identity, F.AGENT_TURN_NAME, {"message": message}, 10.0, stage="M1")


async def test_same_session_other_user_gets_a_fresh_conversation():
    engine, rt = _RowEngine(), _SeeRuntime()
    reg = _turn_registry(engine, rt)
    await _turn(reg, _pm(session_id="s"), "我是 12291")
    await _turn(reg, _pm(session_id="s"), "第二句")
    assert any(m["content"] == "我是 12291" for m in rt.seen[-1].get("dialog", []))   # 正對照：同人續用
    await _turn(reg, _pm(session_id="s", user=PART), "換人")
    assert rt.seen[-1].get("dialog", []) == []                          # 讀不到前一人的對話
    assert [r["state"] for r in engine.rows] == ["COMPLETED", "COLLECTING"]
    assert engine.rows[-1]["user_id"] == PART


async def test_same_user_other_role_resets_and_anonymous_rules():
    engine, rt = _RowEngine(), _SeeRuntime()
    reg = _turn_registry(engine, rt)
    await _turn(reg, _pm(session_id="s"), "一")
    await _turn(reg, _pm(session_id="s", role="20152"), "二")
    assert rt.seen[-1].get("dialog", []) == []
    anon = dict(vendor_id=4, target_user="property_manager", mode="b2b", session_id="a",
                api_key_id=1, entry="mcp")
    await _turn(reg, Identity(**anon), "匿名一")
    await _turn(reg, Identity(**anon), "匿名二")
    assert any(m["content"] == "匿名一" for m in rt.seen[-1]["dialog"])   # 匿名續匿名
    await _turn(reg, Identity(**anon, user_id=OWNER, role_id=ROLE), "具名")
    assert rt.seen[-1].get("dialog", []) == []                          # 匿名→具名重置


async def test_interleaved_turns_do_not_overwrite_the_new_row():
    """F1 併發：A 載入舊列後卡住、B（另一人）關舊列開新列、A 再存 ⇒ A 寫不到新列。"""
    engine = _RowEngine()
    gate = asyncio.Event()
    rt = _SeeRuntime(gate=gate)
    reg = _turn_registry(engine, rt)
    await _turn(reg, _pm(session_id="s"), "起頭")
    task_a = asyncio.ensure_future(_turn(reg, _pm(session_id="s"), "A"))
    await asyncio.sleep(0.05)
    await _turn(reg, _pm(session_id="s", user=PART), "B")
    gate.set()
    await task_a
    new_row = [r for r in engine.rows if r["state"] == "COLLECTING"]
    assert len(new_row) == 1 and new_row[0]["user_id"] == PART
    contents = [m["content"] for m in new_row[0]["data"]["agent"]["dialog"]]
    assert contents == ["B"], "A 的存檔 ⛔ 不得覆寫 B 新開的列"


async def _confirm_runtime(pool):
    return AgentRuntime(FakeProvider([]), FakeRegistry(), FakeVerifier(), FakeAssembler(), Budget(),
                        stage="M1", clock=FakeClock(), db_pool=pool)


async def test_other_user_cannot_press_the_card_and_old_pending_without_creator_is_dead():
    pid = "0123456789abcdef"
    for creator, who, expect_redeem in (
        ({"user_id": OWNER, "role_id": ROLE}, _pm(user=PART), False),       # 換人
        ({"user_id": OWNER, "role_id": ROLE}, _pm(role="20152"), False),    # 同人換 role
        (None, _pm(), False),                                               # 舊 pending 無建立者
        ({"user_id": OWNER, "role_id": ROLE}, _pm(), True),                  # 正對照
    ):
        pending = {"action": "estate_create", "payload": {"action": "estate_create"},
                   "card_sha256": "x" * 64}
        if creator is not None:
            pending["creator"] = creator
        state = {"agent": {PENDING_CONFIRM_KEY: {pid: dict(pending)}}}
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=None)
        rt = await _confirm_runtime(pool)
        res = await rt.run_turn(who, f"confirm_submit:{pid}", state)
        assert res.answer == "這筆確認已失效，請重新確認一次。"
        assert (pool.fetchrow.await_count > 0) is expect_redeem, creator  # ⛔ 燒 token
        assert "receipt" not in state["agent"][PENDING_CONFIRM_KEY][pid]


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_card_turn_stores_the_creator():
    data = {"pending_id": "0123456789abcdef", "card": "卡", "action": "estate_create",
            "payload": {"action": "estate_create"}, "quick_replies": [], "hint": "", "estate_id": None}
    rt = AgentRuntime(FakeProvider([_fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "x", "payload": "{}"}, call_id="c1")]))]),
        FakeRegistry(call_results=[ToolResult(ok=True, data=data)]),
        FakeVerifier(), FakeAssembler(), Budget(), stage="M1", clock=FakeClock())
    state: dict = {}
    await rt.run_turn(_pm(), "麻煩幫我把這筆資料建立起來好嗎謝謝", state)
    assert state["agent"][PENDING_CONFIRM_KEY]["0123456789abcdef"]["creator"] == {
        "user_id": OWNER, "role_id": ROLE}


# ════════════════════════════════════════════════════════════════════
# 第 4 點：釘住範圍閘擴充
# ════════════════════════════════════════════════════════════════════
async def _scoped_confirm(action, data_extra, payload_extra=None):
    payload = {"action": action, **(payload_extra or {})}
    data = {"pending_id": "0123456789abcdef", "card": "卡", "action": action, "payload": payload,
            "quick_replies": [], "hint": "", "estate_id": None, **data_extra}
    rt = AgentRuntime(FakeProvider([_fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "x", "payload": "{}"}, call_id="c1")]))]),
        FakeRegistry(call_results=[ToolResult(ok=True, data=data)]),
        FakeVerifier(), FakeAssembler(), Budget(), stage="M1", clock=FakeClock())
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "100"}}}
    res = await rt.run_turn(_pm(), "麻煩幫我把這筆資料建立起來好嗎謝謝", state)
    return res, state


@pytest.mark.parametrize("action,data_extra,payload_extra,blocked", [
    ("contract_create", {}, {"estate_id": 200}, True),
    ("contract_create", {}, {"estate_id": 100}, False),
    ("contract_create", {}, {}, True),
    ("manual_bill_create", {"scope_estate_id": "200"}, {}, True),
    ("manual_bill_create", {"scope_estate_id": "100"}, {}, False),
    ("manual_bill_create", {}, {}, True),
    ("estate_create", {}, {}, True),
    ("repair_create", {"estate_id": None}, {}, True),
    ("repair_create", {"estate_id": "100"}, {}, False),
])
async def test_scope_gate_covers_all_write_actions(action, data_extra, payload_extra, blocked):
    res, state = await _scoped_confirm(action, data_extra, payload_extra)
    if blocked:
        assert res.answer == SCOPE_EXIT_TEXT and PENDING_CONFIRM_KEY not in state["agent"]
    else:
        assert res.outcome["state"] == "confirm_pending"


async def test_manual_bill_card_reports_the_contract_estate_for_the_scope_gate(api):
    from services.agent.tools.confirm import confirm_request
    r = await confirm_request(_pm(), {"summary": "x", "payload": json.dumps(_bill_payload(), ensure_ascii=False)},
                              db_pool=_pool())
    assert r.ok and r.data["scope_estate_id"] == str(ESTATE_A)
    assert r.data["estate_id"] is None                                   # ⛔ 重用 estate_id（物件記憶）
    est = await confirm_request(_pm(), {"summary": "x", "payload": json.dumps(_estate_payload(), ensure_ascii=False)},
                                db_pool=_pool())
    assert est.ok and "scope_estate_id" not in est.data                  # 其他動作鍵集合不變


# ════════════════════════════════════════════════════════════════════
# 第 5 點：新動作單號、物件只印名稱
# ════════════════════════════════════════════════════════════════════
def test_every_confirm_action_receipt_passes_make_outcome():
    from services.agent.confirm_card import CONFIRM_ACTIONS
    receipts = {"repair_create": {"repair_id": "12346"}, "bill_due_extend": {"bill_id": "756248"},
                "estate_create": {"estate_id": "70001"}, "contract_create": {"contract_id": "90001"},
                "manual_bill_create": {"bill_id": "800001"}}
    assert set(receipts) == set(CONFIRM_ACTIONS)
    for action, receipt in receipts.items():
        ref = receipt_ref(action, receipt)
        assert ref is not None, action
        make_outcome("confirmed", expects="none", action=action, ref=ref)
    assert "estate" in OUTCOME_REF_TYPES
    assert receipt_ref("estate_create", {"estate_id": "70 01; drop"}) is None   # 形狀檢查
    assert receipt_ref("contract_create", {"bill_id": "1"}) is None


def test_estate_is_shown_by_name_never_by_id():
    items = [{"action": "estate_create", "ref_type": "estate", "ref_id": "70001",
              "estate_id": "70001", "at_iso": "t", "estate_name": "幸福小窩"}]
    line = completed_actions_line(items, None)
    assert "幸福小窩" in line and "70001" not in line
    assert "70001" not in _recent_ref_ids({"completed_actions": items}, [])
    assert "1234567" in _recent_ref_ids(
        {"completed_actions": [{"ref_type": "bill", "ref_id": "1234567"}]}, [])   # 正對照
    text = render_receipt("estate_create", _estate_payload(), {"estate_id": "70001"})
    assert "幸福小窩" in text and "70001" not in text


@pytest.fixture()
def _aplus_proposal_off(monkeypatch):
    """A+ 片（`AGENT_WRITE_PROPOSAL`）：本檔以「模型自呼 `confirm.request`、以模型參數執行」為載具的
    測試＝開關 off 的正對照（開關 on 時該路徑已收掉）。開關 on 的程式路徑由
    `test_aplus_card_program_only_req.py` 驗出卡、缺欄追問、查無固定句、帳單候選點選、照片與物件記憶前處理；
    本檔其餘行為在開關 on 時沒有另寫程式路徑版本。"""
    monkeypatch.setenv("AGENT_WRITE_PROPOSAL", "off")
