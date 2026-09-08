"""unit：清單進場後的**會話邊界**（切片 L15 (a)(b)｜Plan §16／§16b 驗收 (i)–(xvi)）。

離線：假 `JGBSystemAPI`（`jgb2._api_singleton`）＋**真 `ToolRegistry`**＋**真
`jgb2.query_*`**——比對的材料（`data["scope"]`／候選列）必須是工具真的算出來的，
用假 registry 造一份等於把 (a)① 一起假掉。⛔ 不接觸真 DB、⛔ 不打任何外部 API。

守的事（§16「修訂後範圍」的 (i)–(xvi)，每條旁邊都有**正對照組**）：
- (i)    別戶單列 ⇒ 工具結果被替換、答案接固定句、violation `select_scope_exit`、
         facts 不在 answer／dialog／trace／messages；正對照＝同物件合約照常。
- (ii)   沒有 select（聊天進場）⇒ 完全不比對。
- (iii)  候選清單只留同物件；全別戶 ⇒ 視同範圍外。
- (iv)   select 失敗 ⇒ `select_scope=None`，舊範圍 ⛔ 不殘留。
- (v)    單列缺 `estate_id` ⇒ fail-closed＋`select_scope_unknown`；正對照＝同一
         份資料補上 `estate_id` 就照常。
- (vi)   estates／meters 別戶 ⇒ 範圍外；正對照＝同戶正常，且 `scope.estate_id`
         逐字等於列 `id`／`estate_id`。
- (vi-b) accounts 候選逐字不變（無物件維度的域 ⛔ 不過濾）；正對照＝同回合的
         bills 候選真的被濾。
- (vii)(xv)(xvi) 寫入路徑：`repair_create`／`bill_due_extend` 的別戶不出卡。
- (viii) int／str 混用等值。 (ix) 固定句是常數、無插值。
- (x)    select 後**聊天式**問別戶 ⇒ 固定句（L15-04 (A)）。
- (xi)   `_jgb2_spec` description 含定義句（契約守測）。
- (xii)  範圍外那一份的 `provenance` 空、messages 不含 facts 片段。
- (xiii) `repairs face="修繕分類"` 靜態樹照常回（無物件維度 ⛔ 不擋）。
- (xiv)  接句三案：部分／全部／無。

⚠️ **本檔只證「物件邊界」，⛔ 不證跨 role 隔離**（L15-15）：假 API 的可見範圍
   本來就是同一個 role，跨 role 的圈定在 jgb2 API 那一側，不在這裡。
"""
from __future__ import annotations

import json

import pytest

from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.mcp_facade import JGB2_EXTRA_PROPERTIES, _as_tool_result, _jgb2_spec
from services.agent.output_schema import VerifierRules
from services.agent.runtime import (
    SCOPE_EXIT_TEXT,
    SCOPE_TOOL_TEXT,
    SELECT_NOT_FOUND_TEXT,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    _enforce_tool_scope,
    _SELECT_DEFAULT_FACE,
)
from services.agent.tools import jgb2
from services.agent.tools.registry import Provenance, ToolRegistry, ToolResult
from services.agent.verifier import OutputVerifier
from services.jgb.bills import build_bill_anomaly_facts

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeVerifier,
    _empty_provider,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
)

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R10-c"

# ---------------------------------------------------------------------------
# 素材：兩個物件（E1／E2），每一域各兩列
# ---------------------------------------------------------------------------
_E1 = 111          # int：(viii) 的一半（另一半是字串 estate_id 的合約列）
_E2 = 222

_BILL_E1 = {
    "id": 900001, "estate_id": _E1, "title": "信義區套房A 八月租金",
    "status": 1, "date_expire": 20260815, "amount": 18000,
    "contract_title": "信義區套房A 租約",
}
_BILL_E1_OTHER = {
    "id": 900003, "estate_id": _E1, "title": "信義區套房A 九月租金",
    "status": 1, "date_expire": 20260915, "amount": 18500,
    "contract_title": "信義區套房A 租約",
}
_BILL_E2 = {
    "id": 900002, "estate_id": _E2, "title": "大安區套房B 八月租金",
    "status": 1, "date_expire": 20260820, "amount": 26000,
    "contract_title": "大安區套房B 租約",
}
#: (v)：**缺 `estate_id`** 的列；正對照是同一份資料補上欄位的孿生列。
_BILL_NO_ESTATE = {
    "id": 900009, "title": "無物件欄位的帳單", "status": 1,
    "date_expire": 20260901, "amount": 1234, "contract_title": "無物件欄位 租約",
}
_BILL_NO_ESTATE_CTRL = {**_BILL_NO_ESTATE, "id": 900010, "estate_id": _E1}

_CONTRACT_E1 = {
    "id": 700001, "estate_id": _E1, "title": "信義區套房A 租約", "status": 4,
    "bit_status": 2, "date_start": 20250101, "date_end": 20261231, "is_newest": 1,
}
#: ⚠️ `estate_id` 刻意是**字串**——(viii) 的 int／str 混用就靠它與 `_BILL_E2` 配對。
_CONTRACT_E2 = {
    "id": 700002, "estate_id": str(_E2), "title": "大安區套房B 租約", "status": 4,
    "bit_status": 2, "date_start": 20250201, "date_end": 20270131, "is_newest": 1,
}

_REPAIR_E1 = {
    "id": 555001, "estate_id": _E1, "estate_title": "信義區套房A",
    "broken_reason": "冷氣不冷", "broken_note": "客廳那台", "status": 1,
    "created_at": "2026-09-01 10:00:00",
}
_REPAIR_E2 = {
    "id": 555002, "estate_id": _E2, "estate_title": "大安區套房B",
    "broken_reason": "馬桶不通", "broken_note": "主臥", "status": 1,
    "created_at": "2026-09-02 10:00:00",
}

_METER_E1 = {"id": 400001, "estate_id": _E1, "name": "A 棟電表", "manufacturer": "DAE"}
_METER_E2 = {"id": 400002, "estate_id": _E2, "name": "B 棟電表", "manufacturer": "DAE"}

_ESTATE_E1 = {"id": _E1, "title": "信義區套房A", "status": 2}
_ESTATE_E2 = {"id": _E2, "title": "大安區套房B", "status": 2}

_MEMBERS = [
    {"member_user_id": 100, "title": "陳小明"},
    {"member_user_id": 292, "title": "陳大文"},
]

#: 假 face：meters／estates／accounts 的真 builder 需要另一組欄位，而本檔要驗的
#: 是**範圍**不是 facts 措辭 ⇒ 用最小 builder（同 `test_jgb2_tools_req.py` 慣例）。
_METER_FACE = "__meter_face__"
_ESTATE_FACE = "__estate_face__"
_ACCOUNT_FACE = "__account_face__"


class _FakeApi:
    """假 `JGBSystemAPI`：兩個物件的資料都在，**要不要跨戶取決於受測程式**。

    ⚠️ 這一點是尺的自證：假 API ⛔ 不自己過濾物件（`get_repairs` 的 `estate_id`
    除外，那是既有透傳契約），所以「別戶查得到」是預設狀態；測試看到的隔離
    一定來自 Runtime 的比對，不是來自素材恰好沒有那一列。
    """

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.bills = [_BILL_E1, _BILL_E1_OTHER, _BILL_E2,
                      _BILL_NO_ESTATE, _BILL_NO_ESTATE_CTRL]
        self.contracts = [_CONTRACT_E1, _CONTRACT_E2]
        self.repairs = [_REPAIR_E1, _REPAIR_E2]
        self.meters = [_METER_E1, _METER_E2]
        self.estates = [_ESTATE_E1, _ESTATE_E2]

    @staticmethod
    def _ok(rows):
        return {"success": True, "data": [dict(r) for r in rows]}

    async def get_bills(self, **kw):
        self.calls.append(("get_bills", kw))
        ref, keyword = kw.get("bill_ref"), kw.get("keyword")
        if ref:
            return self._ok([r for r in self.bills if str(r["id"]) == str(ref)])
        if keyword:
            return self._ok([r for r in self.bills if str(keyword) in r["title"]])
        return self._ok(self.bills)

    async def get_contracts(self, **kw):
        self.calls.append(("get_contracts", kw))
        ref, keyword = kw.get("contract_ids"), kw.get("keyword")
        if ref:
            return self._ok([r for r in self.contracts if str(r["id"]) == str(ref)])
        if keyword:
            return self._ok([r for r in self.contracts if str(keyword) in r["title"]])
        return self._ok(self.contracts)

    async def get_repairs(self, **kw):
        self.calls.append(("get_repairs", kw))
        estate_id = kw.get("estate_id")
        rows = self.repairs
        if estate_id:
            rows = [r for r in rows if str(r["estate_id"]) == str(estate_id)]
        return self._ok(rows)

    async def get_repair_categories(self, **kw):
        self.calls.append(("get_repair_categories", kw))
        return self._ok([{"id": 1, "name": "家電維修", "items": [{"id": 11, "name": "電熱水器"}]}])

    async def get_meters(self, **kw):
        self.calls.append(("get_meters", kw))
        keyword = kw.get("keyword")
        if keyword:
            return self._ok([r for r in self.meters
                             if str(keyword) == str(r["id"]) or str(keyword) in r["name"]])
        return self._ok(self.meters)

    async def get_estate_status(self, **kw):
        self.calls.append(("get_estate_status", kw))
        keyword = kw.get("keyword")
        rows = [r for r in self.estates
                if str(keyword) == str(r["id"]) or str(keyword) in r["title"]]
        return self._ok(rows or [{"found": False, "keyword": keyword}])

    async def get_estate_detail(self, **kw):
        self.calls.append(("get_estate_detail", kw))
        return self._ok([{"id": kw.get("estate_id"), "rent": 15000}])

    async def get_team_members(self, **kw):
        self.calls.append(("get_team_members", kw))
        return self._ok(_MEMBERS)

    async def get_member_permissions(self, **kw):
        self.calls.append(("get_member_permissions", kw))
        return self._ok([{"user_id": kw.get("user_id"), "is_owner": False}])


@pytest.fixture()
def fake_api(monkeypatch):
    monkeypatch.setitem(jgb2.METER_FACE_BUILDERS, _METER_FACE,
                        lambda row, q: f"電表 {row['id']}")
    monkeypatch.setitem(jgb2.ESTATE_FACE_BUILDERS, _ESTATE_FACE,
                        lambda row, detail, q: f"物件 {row.get('id')}")
    monkeypatch.setitem(jgb2.ACCOUNT_FACE_BUILDERS, _ACCOUNT_FACE,
                        lambda member, q: f"成員 {member.get('user_id')}")
    api = _FakeApi()
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api


def _real_registry() -> ToolRegistry:
    """真 registry ＋ 真 `jgb2.query_*`（spec 走與門面同一支工廠）。"""
    reg = ToolRegistry()
    for domain, builders, fn in (
        ("bills", jgb2.BILL_FACE_BUILDERS, jgb2.query_bills),
        ("contracts", jgb2.CONTRACT_FACE_BUILDERS, jgb2.query_contracts),
        ("repairs", jgb2.REPAIR_FACE_BUILDERS, jgb2.query_repairs),
        ("meters", jgb2.METER_FACE_BUILDERS, jgb2.query_meters),
        ("estates", jgb2.ESTATE_FACE_BUILDERS, jgb2.query_estates),
        ("accounts", jgb2.ACCOUNT_FACE_BUILDERS, jgb2.query_accounts),
    ):

        def _make(fn=fn):
            async def _query(identity, args):
                return _as_tool_result(await fn(identity, args))

            return _query

        reg.register(
            _jgb2_spec(domain, sorted(builders.keys()),
                       extra_properties=JGB2_EXTRA_PROPERTIES.get(domain)),
            _make(),
        )
    return reg


_CONFIRM_OPENAI_SPEC = {
    "type": "function",
    "function": {
        "name": "confirm__request",
        "description": "",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string"}, "payload": {"type": "string"}},
            "required": ["summary", "payload"],
            "additionalProperties": False,
        },
    },
}


class _Registry:
    """真 registry（jgb2 六域）＋ **腳本化的 `confirm.request`**。

    ⚠️ `confirm.request` 走腳本、⛔ 不真的發 token：本檔要驗的是「Runtime 有沒有
    建 pending」，而 token／卡的語義已由 `test_session_confirm_tools_req.py`／
    `test_runtime_confirm_segment_req.py` 守著。`jgb2.query.*` 一律走真的那一條，
    因為 `bill_due_extend` 的邊界就是靠 `jgb2.query.bills` 現查出來的 scope。
    """

    def __init__(self, confirm_result: ToolResult | None = None):
        self._real = _real_registry()
        self.confirm_result = confirm_result
        self.calls: list[dict] = []

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        tools = list(self._real.to_openai_tools(identity, stage, readonly_view=readonly_view))
        if self.confirm_result is not None:
            tools.append(_CONFIRM_OPENAI_SPEC)
        return tools

    async def call(self, identity, name, args, timeout_s, *, stage,
                   readonly_view=False, for_model=False):
        self.calls.append({"name": name, "args": dict(args), "for_model": for_model})
        if name == "confirm.request":
            assert self.confirm_result is not None, "腳本沒給 confirm 結果"
            return self.confirm_result
        return await self._real.call(identity, name, args, timeout_s, stage=stage,
                                     readonly_view=readonly_view, for_model=for_model)


class _ScopeVerifier(FakeVerifier):
    """假 `verify`（模型輸出不是本檔的受測物）＋**真的** `_verify_routes`。

    select 段對 `_verify_routes` 是 fail-closed（拿不到就不出 facts），少了它整段
    會退成「查無此筆」⇒ 每一條測試都會變成假綠。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._routes = OutputVerifier(VerifierRules(
            version="test", sha256="0" * 64, sensitive_patterns=[], negation_terms=[],
            forbid_terms=[], allowed_routes=[], assertion_terms=[],
        ))

    def _verify_routes(self, text):
        return self._routes._verify_routes(text)


def _identity(**over) -> Identity:
    base = dict(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="88", api_key_id=1,
        session_id="mcp:1:1:s1", entry="mcp",
    )
    base.update(over)
    return Identity(**base)


def _runtime(*, provider=None, registry=None, verifier=None):
    return AgentRuntime(
        provider or _empty_provider(),
        registry if registry is not None else _Registry(),
        verifier or _ScopeVerifier(),
        FakeAssembler(),
        Budget(),
        stage="M1",
        clock=FakeClock(),
        db_pool=None,          # 槽位寫入不是本檔受測物（見 test_select_entry_unit_req）
    )


def _tool_call_response(name: str, args: dict, call_id: str):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(name, args, call_id)]))


async def _select(rt, state: dict, select_type: str, ref) -> None:
    """跑一個真的 `select:` 回合（⛔ 不手寫 `select_scope`——那會把 (a)② 假掉）。"""
    await rt.run_turn(_identity(), f"select:{select_type}:{ref}", state)


def _tool_messages(provider) -> list[dict]:
    """最後一次模型呼叫看到的 `role="tool"` 訊息。"""
    messages = provider.calls[-1]["messages"]
    return [m for m in messages if m.get("role") == "tool"]


def _dialog(state: dict) -> str:
    return json.dumps(state.get("agent", {}).get("dialog", []), ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# 0. (a)①：scope 鍵只長在實體列上——封閉例外逐一驗（含 (vi) 正對照、(xiii)）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_scope_key_is_on_entity_rows_and_absent_on_the_closed_exceptions(fake_api):
    """實體單列**都有** `scope`；三個封閉例外**都沒有**。

    正對照組就在同一條裡：若 `_ok_single` 一律加 scope，下半段會紅；若一律不加，
    上半段會紅。兩個方向都看得見 ⇒ 這把尺不是恆真。
    """
    ident = _identity()

    bill = await jgb2.query_bills(ident, {"face": "帳單異常", "ref": str(_BILL_E1["id"])})
    assert bill["data"]["scope"] == {"estate_id": str(_E1)}
    contract = await jgb2.query_contracts(
        ident, {"face": "續約", "ref": str(_CONTRACT_E2["id"])})
    assert contract["data"]["scope"] == {"estate_id": str(_E2)}   # 字串列逐字保留
    repair = await jgb2.query_repairs(
        ident, {"face": "修繕進度", "ref": str(_REPAIR_E1["id"])})
    assert repair["data"]["scope"] == {"estate_id": str(_E1)}
    meter = await jgb2.query_meters(ident, {"face": _METER_FACE, "ref": str(_METER_E1["id"])})
    assert meter["data"]["scope"] == {"estate_id": str(_E1)}      # (vi) 正對照：逐字＝列值
    estate = await jgb2.query_estates(ident, {"face": _ESTATE_FACE, "ref": str(_E2)})
    assert estate["data"]["scope"] == {"estate_id": str(_E2)}     # estates 比的是列 `id`

    # 封閉例外一：修繕分類靜態樹（(xiii) 的來源）
    tree = await jgb2.query_repairs(ident, {"face": "修繕分類"})
    assert "scope" not in tree["data"] and tree["data"]["facts"]
    # 封閉例外二：accounts 域（無物件維度）
    account = await jgb2.query_accounts(ident, {"face": _ACCOUNT_FACE, "ref": "292"})
    assert "scope" not in account["data"] and account["data"]["facts"]
    # 封閉例外三：estates sentinel（found=False）
    sentinel = await jgb2.query_estates(ident, {"face": _ESTATE_FACE, "ref": "不存在的物件"})
    assert sentinel["ok"] is True and "scope" not in sentinel["data"]
    # 封閉例外四：候選清單（`_ok_candidates`）⛔ 不帶 scope
    candidates = await jgb2.query_bills(ident, {"face": "帳單異常", "keyword": "套房"})
    assert candidates["data"]["candidates"] and "scope" not in candidates["data"]


@pytest.mark.req(_REQ)
async def test_row_without_estate_id_yields_scope_none_not_a_missing_key(fake_api):
    """缺欄位的實體列 ⇒ `scope` 鍵**在**、值為 `None`（(v) fail-closed 的前提）。

    正對照組：同一份資料補上 `estate_id` 就拿得到值 ⇒ 上一行不是「這一域沒 scope」。
    """
    ident = _identity()
    missing = await jgb2.query_bills(
        ident, {"face": "帳單異常", "ref": str(_BILL_NO_ESTATE["id"])})
    assert missing["data"]["scope"] == {"estate_id": None}
    ctrl = await jgb2.query_bills(
        ident, {"face": "帳單異常", "ref": str(_BILL_NO_ESTATE_CTRL["id"])})
    assert ctrl["data"]["scope"] == {"estate_id": str(_E1)}


# ════════════════════════════════════════════════════════════════════
# 1. (a)②／(iv)：select 回合寫範圍，失敗回合把它清成 None
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_select_hit_writes_the_scope_and_a_failed_select_clears_it(fake_api):
    rt = _runtime()
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])
    assert state["agent"][SELECT_SCOPE_KEY] == {"type": "bill", "estate_id": str(_E1)}

    # 換一筆別戶的 select ⇒ 覆蓋（(a)⑦）
    await _select(rt, state, "bill", _BILL_E2["id"])
    assert state["agent"][SELECT_SCOPE_KEY] == {"type": "bill", "estate_id": str(_E2)}

    # 失敗（查無此筆）⇒ **清成 None**，⛔ 舊範圍不殘留（L15-05）
    result = await rt.run_turn(_identity(), "select:bill:999999", state)
    assert result.answer == SELECT_NOT_FOUND_TEXT
    assert state["agent"][SELECT_SCOPE_KEY] is None


@pytest.mark.req(_REQ)
async def test_stale_scope_never_survives_a_failed_select(fake_api):
    """(iv)：select 失敗之後查別戶 ⇒ **正常**（沒有範圍＝不比對）。

    正對照組＝同一句話在 select 命中之後會被擋（見
    `test_out_of_scope_single_row_is_replaced_and_the_answer_gets_the_fixed_sentence`）。
    """
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E2["id"])}, "call_1"),
        _final_response(answer="這是那張帳單的說明"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", 999999)          # 失敗回合
    result = await rt.run_turn(_identity(), "900002 那張帳單呢", state)

    assert result.answer == "這是那張帳單的說明"
    assert "select_scope_exit" not in result.trace.violations
    assert SCOPE_TOOL_TEXT not in json.dumps(provider.calls[-1]["messages"], ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# 2. (i)(x)(xii)：別戶單列 ⇒ 替換＋接句；正對照＝同物件照常
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_out_of_scope_single_row_is_replaced_and_the_answer_gets_the_fixed_sentence(
    fake_api,
):
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E2["id"])}, "call_1"),
        _final_response(answer="模型憑別戶資料寫的答案"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "那 222 那戶的帳單呢？", state)   # (x) 聊天式問別戶

    assert result.answer == SCOPE_EXIT_TEXT          # 整回合都在範圍外 ⇒ 只剩固定句
    assert "select_scope_exit" in result.trace.violations
    # facts ⛔ 不進 messages（(xii)）——工具訊息只剩程式固定句
    tool_msgs = _tool_messages(provider)
    assert len(tool_msgs) == 1 and SCOPE_TOOL_TEXT in tool_msgs[0]["content"]
    leaked = build_bill_anomaly_facts(dict(_BILL_E2), "")
    fragment = _BILL_E2["title"]
    assert fragment in leaked, "尺的自證：這個片段本來就會出現在 facts 裡"
    assert fragment not in tool_msgs[0]["content"]
    assert fragment not in result.answer
    assert fragment not in _dialog(state)             # ⛔ 不進 dialog
    assert fragment not in str(result.trace)          # ⛔ 不進 trace


@pytest.mark.req(_REQ)
async def test_same_estate_contract_is_untouched(fake_api):
    """(i) 正對照：同物件的**別的域**（合約）照常回 facts、⛔ 無 violation、⛔ 無接句。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.contracts",
                            {"face": "續約", "ref": str(_CONTRACT_E1["id"])}, "call_1"),
        _final_response(answer="合約到期日在 2026/12/31"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "同一戶的合約什麼時候到期", state)

    assert result.answer == "合約到期日在 2026/12/31"
    assert SCOPE_EXIT_TEXT not in result.answer
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]
    tool_msgs = _tool_messages(provider)
    assert _CONTRACT_E1["title"] in tool_msgs[0]["content"]   # facts 真的進去了


@pytest.mark.req(_REQ)
async def test_without_select_scope_nothing_is_compared(fake_api):
    """(ii)：聊天進場（沒有 select）⇒ 別戶查得到、⛔ 無 violation、⛔ 無接句。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E2["id"])}, "call_1"),
        _final_response(answer="那張帳單的說明"),
    ])
    rt = _runtime(provider=provider)
    result = await rt.run_turn(_identity(), "900002 這張帳單", {})

    assert result.answer == "那張帳單的說明"
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]
    assert _BILL_E2["title"] in _tool_messages(provider)[0]["content"]


# ════════════════════════════════════════════════════════════════════
# 3. (iii)(vi-b)：候選清單過濾
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_candidates_are_filtered_down_to_the_scope(fake_api):
    """(iii)：keyword 命中兩戶 ⇒ 只有同戶那幾列進文字；⛔ 不算範圍外（有留下 ⇒ 算 in）。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "keyword": "套房"}, "call_1"),
        _final_response(answer="你這一戶有兩張帳單"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "我這邊有哪些帳單", state)

    content = _tool_messages(provider)[0]["content"]
    assert str(_BILL_E1["id"]) in content and str(_BILL_E1_OTHER["id"]) in content
    assert str(_BILL_E2["id"]) not in content        # 別戶那一列被濾掉
    assert _BILL_E2["title"] not in content
    assert "符合 2 筆" in content                     # 重繪過（原本是 3 筆）
    assert result.answer == "你這一戶有兩張帳單"       # 有留下 ⇒ ⛔ 不接固定句
    assert "select_scope_exit" not in result.trace.violations


@pytest.mark.req(_REQ)
async def test_candidates_all_out_of_scope_are_treated_as_out(fake_api):
    """(iii) 後半：候選全是別戶 ⇒ 視同範圍外（空清單 ⛔ 不當成「查無」放行）。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "keyword": "大安區"}, "call_1"),
        _final_response(answer="模型憑別戶清單寫的答案"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "大安區那邊的帳單", state)

    assert result.answer == SCOPE_EXIT_TEXT
    assert "select_scope_exit" in result.trace.violations
    assert _BILL_E2["title"] not in _tool_messages(provider)[0]["content"]


@pytest.mark.req(_REQ)
async def test_accounts_candidates_are_never_filtered_while_bills_are(fake_api):
    """(vi-b)：同一回合裡 accounts 候選逐字不變、bills 候選被濾——**同一把尺兩個方向**。

    accounts 的列沒有 `estate_id`；若過濾套到它身上，這一域會整個變成「範圍外」。
    """
    provider = FakeProvider([
        _tool_call_response("jgb2.query.accounts",
                            {"face": _ACCOUNT_FACE, "keyword": "陳"}, "call_1"),
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "keyword": "套房"}, "call_2"),
        _final_response(answer="兩位成員都在，帳單只列你這一戶"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "團隊有誰？我這戶有哪些帳單", state)

    msgs = {m["tool_call_id"]: m["content"] for m in _tool_messages(provider)}
    # 兩位成員都還在、筆數沒被改寫（⛔ 沒有任何一列被當成「別戶」濾掉）
    for member in _MEMBERS:
        assert member["title"] in msgs["call_1"]
    assert "符合 2 筆" in msgs["call_1"]
    assert SCOPE_TOOL_TEXT not in msgs["call_1"]
    assert str(_BILL_E2["id"]) not in msgs["call_2"]  # 正對照：bills 真的被濾了
    assert result.answer == "兩位成員都在，帳單只列你這一戶"
    assert SCOPE_EXIT_TEXT not in result.answer
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]


# ════════════════════════════════════════════════════════════════════
# 4. (v)(vi)(viii)(xiii)：fail-closed、estates／meters、int/str、分類樹
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_row_missing_estate_id_is_fail_closed_with_a_violation(fake_api):
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_NO_ESTATE["id"])}, "call_1"),
        _final_response(answer="模型憑那張帳單寫的答案"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "900009 這張", state)

    assert result.answer == SCOPE_EXIT_TEXT
    assert "select_scope_unknown" in result.trace.violations
    assert "select_scope_exit" in result.trace.violations


@pytest.mark.req(_REQ)
async def test_the_same_row_with_an_estate_id_goes_through(fake_api):
    """(v) 正對照：同一份資料**補上 `estate_id`** 就照常 ⇒ 上一條擋的是缺值，不是這一域。"""
    provider = FakeProvider([
        _tool_call_response(
            "jgb2.query.bills",
            {"face": "帳單異常", "ref": str(_BILL_NO_ESTATE_CTRL["id"])}, "call_1"),
        _final_response(answer="這張帳單的說明"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "900010 這張", state)

    assert result.answer == "這張帳單的說明"
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("tool,args,leak", [
    ("jgb2.query.estates", {"face": _ESTATE_FACE, "ref": str(_E2)}, "物件 222"),
    ("jgb2.query.meters", {"face": _METER_FACE, "ref": str(_METER_E2["id"])}, "電表 400002"),
])
async def test_estates_and_meters_of_another_estate_are_out_of_scope(
    fake_api, tool, args, leak
):
    """(vi)：L15-02 的兩域也在邊界內。"""
    provider = FakeProvider([
        _tool_call_response(tool, args, "call_1"),
        _final_response(answer="模型憑別戶資料寫的答案"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "那另一戶呢", state)

    assert result.answer == SCOPE_EXIT_TEXT
    assert "select_scope_exit" in result.trace.violations
    assert leak not in _tool_messages(provider)[0]["content"]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("tool,args,expected", [
    ("jgb2.query.estates", {"face": _ESTATE_FACE, "ref": str(_E1)}, "物件 111"),
    ("jgb2.query.meters", {"face": _METER_FACE, "ref": str(_METER_E1["id"])}, "電表 400001"),
])
async def test_estates_and_meters_of_the_same_estate_are_normal(fake_api, tool, args, expected):
    """(vi) 正對照：同戶的 estates／meters 照常回 facts、⛔ 無 violation。"""
    provider = FakeProvider([
        _tool_call_response(tool, args, "call_1"),
        _final_response(answer="這一戶的說明"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "這一戶的物件與電表", state)

    assert result.answer == "這一戶的說明"
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]
    assert expected in _tool_messages(provider)[0]["content"]


@pytest.mark.req(_REQ)
async def test_int_and_str_estate_ids_compare_equal(fake_api):
    """(viii)：`select` 的列 `estate_id` 是 int（222），合約列是字串（"222"）⇒ 同戶。

    正對照組：同一支查詢換成別戶合約（int 111）⇒ 範圍外 ⇒ 證明不是「一律放行」。
    """
    provider = FakeProvider([
        _tool_call_response("jgb2.query.contracts",
                            {"face": "續約", "ref": str(_CONTRACT_E2["id"])}, "call_1"),
        _final_response(answer="同一戶的合約"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E2["id"])      # estate_id 是 int 222
    result = await rt.run_turn(_identity(), "這戶的合約", state)
    assert result.answer == "同一戶的合約"
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]

    provider2 = FakeProvider([
        _tool_call_response("jgb2.query.contracts",
                            {"face": "續約", "ref": str(_CONTRACT_E1["id"])}, "call_1"),
        _final_response(answer="別戶的合約"),
    ])
    rt2 = _runtime(provider=provider2)
    state2: dict = {}
    await _select(rt2, state2, "bill", _BILL_E2["id"])
    result2 = await rt2.run_turn(_identity(), "另一戶的合約", state2)
    assert result2.answer == SCOPE_EXIT_TEXT


@pytest.mark.req(_REQ)
async def test_repair_category_tree_is_not_blocked_by_the_scope(fake_api):
    """(xiii)：靜態分類樹沒有物件維度 ⇒ 照常回、⛔ 無 violation、⛔ 無接句。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.repairs", {"face": "修繕分類"}, "call_1"),
        _final_response(answer="可選的分類有這些"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "有哪些修繕分類", state)

    assert result.answer == "可選的分類有這些"
    assert not [v for v in result.trace.violations if v.startswith("select_scope")]
    assert "家電維修" in _tool_messages(provider)[0]["content"]


# ════════════════════════════════════════════════════════════════════
# 5. (xiv)：接句三案（部分／全部含 handoff／無）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_partial_out_of_scope_appends_the_sentence_at_the_end(fake_api):
    provider = FakeProvider([
        _tool_call_response("jgb2.query.contracts",
                            {"face": "續約", "ref": str(_CONTRACT_E1["id"])}, "call_1"),
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E2["id"])}, "call_2"),
        _final_response(answer="你這一戶的合約到 2026/12/31"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "我的合約？另外 222 那戶的帳單？", state)

    assert result.answer == "你這一戶的合約到 2026/12/31\n" + SCOPE_EXIT_TEXT
    assert result.kind == "answer"
    assert _dialog(state).count(SCOPE_EXIT_TEXT) == 1     # dialog 存的是接句後那一份


@pytest.mark.req(_REQ)
async def test_all_out_of_scope_replaces_even_a_model_handoff_and_never_caches_it(fake_api):
    """全範圍外＋模型自判 handoff ⇒ 固定句、`kind="answer"`、handoff cache ⛔ 無此鍵。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E2["id"])}, "call_1"),
        _final_response(kind="handoff", answer="我幫你轉真人", handoff_reason="no_grounding"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "222 那戶的帳單", state)

    assert result.answer == SCOPE_EXIT_TEXT
    assert result.kind == "answer" and result.handoff is None
    assert result.trace.final_kind == "answer"
    assert state["agent"].get("handoff_cache", {}) == {}


@pytest.mark.req(_REQ)
async def test_no_out_of_scope_means_the_answer_is_byte_identical(fake_api):
    """(xiv) 第三案（正對照）：完全沒有範圍外 ⇒ 答案逐字不動、⛔ 不含固定句。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills",
                            {"face": "帳單異常", "ref": str(_BILL_E1["id"])}, "call_1"),
        _final_response(answer="你這張帳單 8/15 到期"),
    ])
    rt = _runtime(provider=provider)
    state: dict = {}
    await _select(rt, state, "bill", _BILL_E1["id"])

    result = await rt.run_turn(_identity(), "我這張帳單什麼時候到期", state)

    assert result.answer == "你這張帳單 8/15 到期"
    assert SCOPE_EXIT_TEXT not in result.answer


# ════════════════════════════════════════════════════════════════════
# 6. (vii)(xv)(xvi)：寫入路徑（confirm.request）
# ════════════════════════════════════════════════════════════════════
def _repair_confirm_result(estate_id) -> ToolResult:
    payload = {"action": "repair_create", "estate_name": "某物件",
               "category_name": "家電維修", "description": "冷氣不冷", "emergency_status": 1}
    data = {"pending_id": "a" * 16, "action": "repair_create", "payload": payload,
            "card": "【修繕單】確認要建立嗎？", "quick_replies": [], "hint": ""}
    if estate_id is not None:
        data["estate_id"] = estate_id
    return ToolResult(ok=True, data=data)


def _bill_confirm_result(bill_id) -> ToolResult:
    payload = {"action": "bill_due_extend", "bill_id": str(bill_id),
               "date_expire_before": "20260815", "days": 3, "date_expire_after": "20260818"}
    return ToolResult(ok=True, data={
        "pending_id": "b" * 16, "action": "bill_due_extend", "payload": payload,
        "card": "【帳單延期】確認要送出嗎？", "quick_replies": [],
    })


def _confirm_script():
    return [_fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "s", "payload": "{}"}, "call_1")]))]


async def _run_confirm(confirm_result, select_ref):
    registry = _Registry(confirm_result=confirm_result)
    provider = FakeProvider(_confirm_script())
    rt = _runtime(provider=provider, registry=registry)
    state: dict = {}
    await _select(rt, state, "bill", select_ref)
    result = await rt.run_turn(_identity(), "幫我送出", state)
    return result, state, registry


@pytest.mark.req(_REQ)
async def test_repair_create_for_another_estate_never_creates_a_pending(fake_api):
    """(vii)(xv)：別戶 ⇒ 不建 pending、固定句。正對照＝同戶照常出卡。"""
    from services.agent.runtime import PENDING_CONFIRM_KEY

    result, state, _ = await _run_confirm(_repair_confirm_result(str(_E2)), _BILL_E1["id"])
    assert result.answer == SCOPE_EXIT_TEXT
    assert PENDING_CONFIRM_KEY not in state["agent"]
    assert "select_scope_exit" in result.trace.violations

    ok, ok_state, _ = await _run_confirm(_repair_confirm_result(str(_E1)), _BILL_E1["id"])
    assert ok.kind == "ask" and ok.answer.startswith("【修繕單】")
    assert list(ok_state["agent"][PENDING_CONFIRM_KEY]) == ["a" * 16]


@pytest.mark.req(_REQ)
async def test_repair_create_with_an_unresolvable_estate_still_shows_the_card(fake_api):
    """(xv)：`estate_id` 為 `None`（解析不出物件）⇒ **放行**——執行時同一支
    `_resolve_estate` 必 `NO_MATCH`，跨戶寫入不可能發生。"""
    from services.agent.runtime import PENDING_CONFIRM_KEY

    result, state, _ = await _run_confirm(_repair_confirm_result(None), _BILL_E1["id"])
    assert result.kind == "ask" and result.answer.startswith("【修繕單】")
    assert list(state["agent"][PENDING_CONFIRM_KEY]) == ["a" * 16]


@pytest.mark.req(_REQ)
async def test_bill_due_extend_is_bounded_by_the_estate_not_the_bill(fake_api):
    """(xvi)：同物件**不同帳單** ⇒ 出卡；別戶 ⇒ 固定句；查不到那張帳單 ⇒ 固定句。"""
    from services.agent.runtime import PENDING_CONFIRM_KEY

    # 同物件、不同帳單（select 的是 900001，要延的是 900003）⇒ 放行
    ok, ok_state, registry = await _run_confirm(
        _bill_confirm_result(_BILL_E1_OTHER["id"]), _BILL_E1["id"])
    assert ok.kind == "ask" and ok.answer.startswith("【帳單延期】")
    assert list(ok_state["agent"][PENDING_CONFIRM_KEY]) == ["b" * 16]
    probe = [c for c in registry.calls
             if c["name"] == "jgb2.query.bills" and c["for_model"] is False]
    assert probe and probe[-1]["args"] == {
        "face": _SELECT_DEFAULT_FACE["bill"], "ref": str(_BILL_E1_OTHER["id"])
    }

    # 別戶帳單 ⇒ 不建 pending
    out, out_state, _ = await _run_confirm(
        _bill_confirm_result(_BILL_E2["id"]), _BILL_E1["id"])
    assert out.answer == SCOPE_EXIT_TEXT
    assert PENDING_CONFIRM_KEY not in out_state["agent"]

    # 查不到那張帳單（拿不到證據）⇒ **fail-closed**
    missing, missing_state, _ = await _run_confirm(
        _bill_confirm_result(999999), _BILL_E1["id"])
    assert missing.answer == SCOPE_EXIT_TEXT
    assert PENDING_CONFIRM_KEY not in missing_state["agent"]


@pytest.mark.req(_REQ)
async def test_write_path_is_untouched_without_a_select_scope(fake_api):
    """(vii) 正對照：沒有 select 範圍 ⇒ 兩個 action 都照常出卡、⛔ 不發現查那一次。"""
    from services.agent.runtime import PENDING_CONFIRM_KEY

    for confirm_result in (_repair_confirm_result(str(_E2)),
                           _bill_confirm_result(_BILL_E2["id"])):
        registry = _Registry(confirm_result=confirm_result)
        rt = _runtime(provider=FakeProvider(_confirm_script()), registry=registry)
        state: dict = {}
        result = await rt.run_turn(_identity(), "幫我送出", state)
        assert result.kind == "ask", result.answer
        assert state["agent"][PENDING_CONFIRM_KEY]
        assert [c for c in registry.calls if c["name"] == "jgb2.query.bills"] == []


# ════════════════════════════════════════════════════════════════════
# 7. (ix)(xi)(xii)：常數、契約描述、替換後的三份
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_the_fixed_sentences_are_constants_without_interpolation():
    """(ix)：兩句固定句逐字釘住，且 ⛔ 無任何插值位。"""
    assert SCOPE_EXIT_TEXT == "這個對話只看你點選的那一戶；要查別戶請回清單點那一戶。"
    assert SCOPE_TOOL_TEXT == "（這一筆不在本對話的範圍內）"
    for text in (SCOPE_EXIT_TEXT, SCOPE_TOOL_TEXT):
        assert "{" not in text and "%" not in text
        assert str(_E1) not in text and str(_E2) not in text


@pytest.mark.req(_REQ)
def test_jgb2_descriptions_carry_the_definition_sentences():
    """(xi)：contracts／bills 各補一句定義；其餘域逐位元不變（正對照）。"""
    faces = ["甲", "乙"]
    contracts = F._jgb2_spec("contracts", faces)["description"]
    bills = F._jgb2_spec("bills", faces)["description"]
    assert "keyword 是物件名稱或承租人名；帳單編號查不到合約，同戶合約先用該帳單的物件名稱查" in contracts
    assert "keyword 是物件名稱" in bills
    assert "承租人名" not in bills                     # bills 只加自己那一句

    base = ("查詢 repairs 領域的決定性事實；face 決定回傳哪一組 facts，"
            "ref／keyword 只能在已確立的範圍內縮小。")
    assert F._jgb2_spec("repairs", faces)["description"] == base
    for domain in ("repairs", "meters", "estates", "accounts"):
        desc = F._jgb2_spec(domain, faces)["description"]
        assert "keyword 是物件名稱" not in desc


@pytest.mark.req(_REQ)
def test_out_of_scope_replacement_clears_all_three_views():
    """(xii)：替換後 `provenance` 空、`text_for_model` 是固定句、`data` 無 facts／候選。

    正對照組：同戶那一份**原樣**回來（同一支函式、同一份輸入形狀）。
    """
    violations: list[str] = []
    result = ToolResult(
        ok=True,
        data={"facts": "別戶的機密事實", "candidates": None, "scope": {"estate_id": "222"}},
        provenance=[Provenance(source="jgb2:bills#900002", text="別戶的機密事實",
                               citable=True)],
        text_for_model="別戶的機密事實",
    )
    assert _enforce_tool_scope("jgb2.query.bills", result, "111", None, violations) == "out"
    assert result.provenance == []
    assert result.text_for_model == SCOPE_TOOL_TEXT
    assert result.data == {"facts": "", "candidates": None, "skip_refine": True}
    assert violations == ["select_scope_exit"]

    same = ToolResult(
        ok=True,
        data={"facts": "同戶的事實", "candidates": None, "scope": {"estate_id": "111"}},
        provenance=[Provenance(source="jgb2:bills#900001", text="同戶的事實", citable=True)],
        text_for_model="同戶的事實",
    )
    kept: list[str] = []
    assert _enforce_tool_scope("jgb2.query.bills", same, "111", None, kept) == "in"
    assert same.text_for_model == "同戶的事實" and kept == []


@pytest.mark.req(_REQ)
def test_non_jgb2_tools_are_never_compared():
    """(3c) 正對照：非 `jgb2.query.*` 的工具結果一律不比對（`kb.get` 沒有物件維度）。"""
    violations: list[str] = []
    result = ToolResult(ok=True, data={"facts": "知識庫內容"}, text_for_model="知識庫內容")
    assert _enforce_tool_scope("kb.get", result, "111", None, violations) is None
    assert result.text_for_model == "知識庫內容" and violations == []
