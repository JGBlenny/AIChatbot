"""unit：LIFF 清單點選機器值 `select:<type>:<id>`（子 spec `agent-write-tools` W8 (1)）。

離線：假 `JGBSystemAPI`（`jgb2._api_singleton`）＋**真 `ToolRegistry`**——這一段的
守門有一半在 registry（可見性／速率／schema／身分鍵剝除），用假 registry 測等於
把它們一起假掉。⛔ 不接觸真 DB、⛔ 不打任何外部 API。

守的事（Plan W8 驗收 (i)–(vii)）：
- (i)   命中 ⇒ `answer` 逐字＝該域 face builder 的產出、`kind=="answer"`、模型 0 次呼叫；
        正對照＝不存在的 id ⇒ 固定句「查無此筆」。
- (ii)  `_SELECT_DEFAULT_FACE` 三個 face 的 facts ⛔ 不含 `@` 與電話樣式；
        正對照＝**同一列資料**以「簽署排障」face 產出就含 `@`（S8-1 的病灶本身）。
- (iii) facts 含 URL ⇒ 「查無此筆」（`_verify_routes` 出口複查）。
- (iv)  dialog 末則 assistant ＝程式摘要，⛔ 不含 facts 任一行（S8-3）。
- (v)   trace 與 `usage_events` 序列化 ⛔ 不含 id 原值、含 `select_type`／`has_ref`（S8-6）。
- (vi)  無 COLLECTING 列 ⇒ 仍回 facts、trace `slot_written=False`。
- (vii) 缺 `user_id` ⇒ 「查無此筆」且 trace 有 violation；正對照＝帶 `user_id` 得 facts（S8-12）。

⚠️ 每個「取不到／不觸發」的斷言旁都放一個**已知必然存在**的正對照組——工具或
   條件壞掉時要看得出來是工具壞了，不是目標不存在。
"""
from __future__ import annotations

import json
import types

import pytest

from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.mcp_facade import JGB2_EXTRA_PROPERTIES, _as_tool_result, _jgb2_spec
from services.agent.output_schema import VerifierRules
from services.agent.runtime import (
    SELECT_DIALOG_SUMMARY,
    SELECT_NOT_FOUND_TEXT,
    AgentRuntime,
    _SELECT_DEFAULT_FACE,
    _SELECT_TYPE_TO_TOOL,
    _parse_select_value,
)
from services.agent import runtime as runtime_mod
from services.agent.tools import jgb2
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.agent.verifier import _PHONE_RE, OutputVerifier
from services.jgb.bills import BILL_FACE_BUILDERS, build_bill_anomaly_facts
from services.jgb.contracts import FACE_BUILDERS as CONTRACT_FACE_BUILDERS
from services.jgb.contracts import build_renew_facts, build_sign_facts
from services.jgb.repairs import REPAIR_FACE_BUILDERS, build_repair_status_facts

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeVerifier,
    _empty_provider,
    _final_response,
)

pytestmark = pytest.mark.unit

from datetime import date as _date  # noqa: E402  — 見下方 `_freeze_today`

from services.jgb import bills as _bills  # noqa: E402  — 時鐘凍結的唯一注入點


#: **模組層凍結時鐘**（S1／H1 起）：`confirm.request` 與兌現路徑都會拿
#: `bills._today()` 去比對標了 `not_before_today` 的日期欄位
#: （`confirm_card.CONFIRM_FIELD_ATTRS`）。本檔的凍結 payload 是 2026-08 的日期，
#: 若跟著真實時鐘走，這些案例會在 2026-08-18 之後集體轉紅——而它們驗的是**兌現與
#: 雜湊語義**，⛔ 不是日期政策（日期閘門本身由 `test_confirm_date_gate_req.py` 驗）。
#: ⛔ 不改 payload 的日期：那些日期同時被寫進斷言字串與雜湊。
@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: _date(2026, 8, 15))

_REQ = "agentic-mcp-orchestration:R10-c"

# ⚠️ 檔名帶 `_unit_`（比照 `test_agent_turn_unit_req.py`／`test_mcp_facade_unit_req.py`）：
#    本 repo 的 pytest 走預設 prepend import 模式、`tests/` 底下**沒有** `__init__.py`，
#    模組名＝檔名 ⇒ unit 與 integration 同名檔會在**收集期**互撞
#    （`import file mismatch: ... test_select_entry_req.py`），整個 `unit` 層一起收不起來。
#    整合層那一份維持 `tests/integration/agent/test_select_entry_req.py`。


# ---------------------------------------------------------------------------
# 素材：三域各一列。**同一列合約資料**同時餵「續約」與「簽署排障」——
# (ii) 的正對照就靠這一點：揭露面的差別來自 face，不是來自資料。
# ---------------------------------------------------------------------------
_BILL_ROW = {
    "id": 900001,
    "title": "2026 年 8 月租金",
    "status": 1,
    "date_expire": 20260815,
    "amount": 18000,
    "contract_title": "信義區套房A 租約",
}
_CONTRACT_ROW = {
    "id": 700007,
    "title": "信義區套房A 租約",
    "status": 4,
    "bit_status": 2,
    "date_start": 20250101,
    "date_end": 20261231,
    "is_newest": 1,
    # ⚠️ 這兩欄是 S8-1 的病灶本身：「簽署排障」face 會把它們原文印出來。
    "to_user_email": "tenant.leaker@example.com",
    "to_user_phone": "0912345678",
    "to_user_connect": 1,
}
_REPAIR_ROW = {
    "id": 555001,
    "estate_title": "信義區套房A",
    "broken_reason": "冷氣不冷",
    "broken_note": "客廳那台",
    "status": 1,
    "created_at": "2026-09-01 10:00:00",
}


class _FakeApi:
    """可配置的假 `JGBSystemAPI`（同 `test_jgb2_tools_req.py` 的 `_FakeApi` 形狀）。"""

    def __init__(self):
        self.bills: list[dict] = []
        self.contracts: list[dict] = []
        self.repairs: list[dict] = []
        self.calls: list[tuple[str, dict]] = []

    @staticmethod
    def _ok(rows):
        return {"success": True, "data": list(rows)}

    async def get_bills(self, **kw):
        self.calls.append(("get_bills", kw))
        ref = kw.get("bill_ref")
        rows = [r for r in self.bills if str(r["id"]) == str(ref)] if ref else self.bills
        return self._ok(rows)

    async def get_contracts(self, **kw):
        self.calls.append(("get_contracts", kw))
        ref = kw.get("contract_ids")
        rows = [r for r in self.contracts if str(r["id"]) == str(ref)] if ref else self.contracts
        return self._ok(rows)

    async def get_repairs(self, **kw):
        self.calls.append(("get_repairs", kw))
        return self._ok(self.repairs)


@pytest.fixture()
def fake_api(monkeypatch):
    api = _FakeApi()
    api.bills = [dict(_BILL_ROW)]
    api.contracts = [dict(_CONTRACT_ROW)]
    api.repairs = [dict(_REPAIR_ROW)]
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api


def _real_registry() -> ToolRegistry:
    """真 `ToolRegistry` ＋ 真 `jgb2.query_*`（`_jgb2_spec` 走與門面同一份工廠）。"""
    reg = ToolRegistry()
    for domain, builders, fn in (
        ("bills", BILL_FACE_BUILDERS, jgb2.query_bills),
        ("contracts", CONTRACT_FACE_BUILDERS, jgb2.query_contracts),
        ("repairs", REPAIR_FACE_BUILDERS, jgb2.query_repairs),
    ):

        def _make(fn=fn):
            async def _query(identity, args):
                return _as_tool_result(await fn(identity, args))

            return _query

        reg.register(
            _jgb2_spec(
                domain,
                sorted(builders.keys()),
                extra_properties=JGB2_EXTRA_PROPERTIES.get(domain),
            ),
            _make(),
        )
    return reg


def _route_verifier(**over) -> OutputVerifier:
    """真 `OutputVerifier`——(iii) 要的是它**真的**那把 `_verify_routes` 尺。"""
    rules = dict(
        version="test", sha256="0" * 64, sensitive_patterns=[], negation_terms=[],
        forbid_terms=[], allowed_routes=[], assertion_terms=[],
    )
    rules.update(over)
    return OutputVerifier(VerifierRules(**rules))


class _FakePool:
    """只實作 `execute`：`write_slot` 用得到的唯一方法。"""

    def __init__(self, status="UPDATE 1"):
        self.status = status
        self.calls: list[tuple] = []

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        return self.status


def _identity(**over) -> Identity:
    base = dict(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="88", api_key_id=1,
        session_id="mcp:1:1:s1", entry="mcp",
    )
    base.update(over)
    return Identity(**base)


def _runtime(*, registry=None, provider=None, pool=None, verifier=None, readonly_view=False):
    return AgentRuntime(
        provider or _empty_provider(),
        registry if registry is not None else _real_registry(),
        verifier if verifier is not None else _route_verifier(),
        FakeAssembler(),
        Budget(),
        stage="M1",
        clock=FakeClock(),
        db_pool=pool,
        readonly_view=readonly_view,
    )


# ════════════════════════════════════════════════════════════════════
# 0. 機器值形狀：fullmatch、⛔ 不 NFKC、⛔ 不 strip（S8-8）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_select_value_is_full_match_only_and_type_domain_is_closed():
    assert _parse_select_value("select:bill:900001") == ("bill", "900001")
    assert _parse_select_value("select:contract:C-7_a") == ("contract", "C-7_a")
    assert _parse_select_value("select:repair:555001") == ("repair", "555001")
    for bad in (
        " select:bill:900001",            # 前置空白 ⇒ 自由文字
        "select:bill:900001 ",            # 後置空白
        "select:bill:900001 是什麼意思？",   # 子字串誤觸發
        "select：bill：900001",            # 全形（⛔ 不 NFKC）
        "select:estate:900001",           # 第一版不開（S8-13）
        "select:meter:900001",            # 第一版不開（S8-5：meter_ref 不在 SlotKey）
        "select:bill:",                   # 空 id
        "select:bill:" + "9" * 33,        # 超過 32 字
        "select:bill:9000/01",            # 值域外字元
        "confirm_submit:0123456789abcdef",
    ):
        assert _parse_select_value(bad) is None, bad
    # 正對照：上面那把尺不是恆回 None——合法值真的解得出來（第一行已證）
    assert set(_SELECT_TYPE_TO_TOOL) == {"bill", "contract", "repair"}
    assert set(_SELECT_DEFAULT_FACE) == set(_SELECT_TYPE_TO_TOOL)
    assert _SELECT_TYPE_TO_TOOL == {
        "bill": "jgb2.query.bills",
        "contract": "jgb2.query.contracts",
        "repair": "jgb2.query.repairs",
    }


@pytest.mark.req(_REQ)
def test_select_slot_keys_are_inside_the_closed_slot_enum():
    """`<type>_ref` 三個鍵都必須在 `SlotKey` 封閉值域內；`meter_ref` **不在**（S8-5）。"""
    from services.agent.tools.session import SLOT_KEYS

    for select_type in _SELECT_TYPE_TO_TOOL:
        assert f"{select_type}_ref" in SLOT_KEYS
    assert "meter_ref" not in SLOT_KEYS   # 這正是第一版不開 meter 的理由


# ════════════════════════════════════════════════════════════════════
# 1. 守門：entry / readonly_view（同確認段）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_rest_entry_does_not_intercept(fake_api):
    """`entry != "mcp"` ⇒ 整段不執行、⛔ 不呼叫工具，訊息照常進模型。

    正對照組：同一句訊息換成 MCP 身分就攔得到。
    """
    # ⚠️ 這兩個守門測試量的是「有沒有進模型」，故 verifier 用永遠放行的替身，
    #    ⛔ 不讓 Verifier 的拒因把假 provider 的腳本吃掉而變成另一種紅。
    rt = _runtime(provider=FakeProvider([_final_response(answer="模型接手了")]),
                  verifier=FakeVerifier())
    result = await rt.run_turn(_identity(entry="rest"), "select:bill:900001", {})
    assert result.answer == "模型接手了"
    assert fake_api.calls == []

    rt2 = _runtime(provider=FakeProvider([_final_response(answer="模型接手了")]))
    hit = await rt2.run_turn(_identity(), "select:bill:900001", {})
    assert hit.answer == build_bill_anomaly_facts(_BILL_ROW, "")


@pytest.mark.req(_REQ)
async def test_readonly_view_does_not_intercept(fake_api):
    """影子回合（`readonly_view`）⇒ 整段不執行：⛔ 不寫槽位、⛔ 不作廢待確認筆。

    正對照組：同一份設定關掉 `readonly_view` 就攔得到。
    """
    rt = _runtime(provider=FakeProvider([_final_response(answer="影子回合")]),
                  readonly_view=True, verifier=FakeVerifier())
    result = await rt.run_turn(_identity(), "select:bill:900001", {})
    assert result.answer == "影子回合"
    assert fake_api.calls == []

    rt2 = _runtime(provider=FakeProvider([_final_response(answer="影子回合")]))
    hit = await rt2.run_turn(_identity(), "select:bill:900001", {})
    assert hit.trace.select_type == "bill"


# ════════════════════════════════════════════════════════════════════
# 2. (i) 命中逐字＝builder 產出、模型 0 次；正對照＝不存在 id ⇒ 固定句
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_select_bill_answer_is_verbatim_builder_output_and_model_not_called(fake_api):
    provider = FakeProvider([_final_response(answer="⛔ 模型不該被叫到")])
    rt = _runtime(provider=provider)
    state: dict = {}

    result = await rt.run_turn(_identity(), "select:bill:900001", state)

    assert result.kind == "answer"
    assert result.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert result.trace.llm_calls == 0
    assert provider.calls == []            # 模型 0 次呼叫
    assert result.trace.select_type == "bill" and result.trace.has_ref is True
    # 走的是封閉表指定的工具與最小揭露 face
    assert [c[0] for c in fake_api.calls] == ["get_bills"]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize(
    "select_type,ref,expected",
    [
        ("bill", "900001", lambda: build_bill_anomaly_facts(_BILL_ROW, "")),
        ("contract", "700007", lambda: build_renew_facts(_CONTRACT_ROW, "")),
        ("repair", "555001", lambda: build_repair_status_facts(_REPAIR_ROW, "")),
    ],
)
async def test_select_all_three_types_return_their_default_face_facts(
    fake_api, select_type, ref, expected
):
    rt = _runtime(provider=FakeProvider([_final_response(answer="⛔ 不該被叫到")]))
    result = await rt.run_turn(_identity(), f"select:{select_type}:{ref}", {})
    assert result.answer == expected()
    assert result.kind == "answer"


@pytest.mark.req(_REQ)
async def test_select_missing_row_returns_the_single_fixed_sentence(fake_api):
    """空／不在範圍 ⇒ **同一句**「查無此筆」（⛔ 不洩存在性）。

    正對照組：同一支假 API、換成存在的 id 就拿得到 facts。
    """
    rt = _runtime(provider=FakeProvider([_final_response(answer="⛔ 不該被叫到")]))
    miss = await rt.run_turn(_identity(), "select:bill:999999", {})
    assert miss.answer == SELECT_NOT_FOUND_TEXT
    assert miss.kind == "answer"

    rt2 = _runtime(provider=FakeProvider([_final_response(answer="⛔ 不該被叫到")]))
    hit = await rt2.run_turn(_identity(), "select:bill:900001", {})
    assert hit.answer != SELECT_NOT_FOUND_TEXT


# ════════════════════════════════════════════════════════════════════
# 3. (ii) 三個預設 face 的 facts ⛔ 不含 email／電話；正對照＝簽署排障含 `@`
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_default_faces_never_emit_email_or_phone_while_sign_face_does():
    """⛔⛔ 這條是 email 面的**唯一**控制（`_verify_routes` 沒有 email 樣式）。

    正對照組（S8-1 的病灶本身）：**同一列合約資料**改用「簽署排障」face
    就會印出 `@` 與電話——證明這條斷言不是因為素材裡根本沒有 email 才綠。
    """
    builders = {
        "bill": (BILL_FACE_BUILDERS, _BILL_ROW),
        "contract": (CONTRACT_FACE_BUILDERS, _CONTRACT_ROW),
        "repair": (REPAIR_FACE_BUILDERS, _REPAIR_ROW),
    }
    for select_type, face in _SELECT_DEFAULT_FACE.items():
        registry, row = builders[select_type]
        assert face in registry, (select_type, face)   # face 名真的存在於 builder 表
        facts = registry[face](row, "")
        assert "@" not in facts, (select_type, face)
        assert _PHONE_RE.search(facts) is None, (select_type, face)

    leaky = build_sign_facts(_CONTRACT_ROW, "")
    assert "@" in leaky and _CONTRACT_ROW["to_user_email"] in leaky
    assert _PHONE_RE.search(leaky) is not None
    # ⛔ 「簽署排障」不得成為任何一個預設 face
    assert "簽署排障" not in set(_SELECT_DEFAULT_FACE.values())


# ════════════════════════════════════════════════════════════════════
# 4. (iii) facts 含 URL ⇒ 出口複查命中 ⇒ 「查無此筆」
# ════════════════════════════════════════════════════════════════════
def _facts_registry(facts: str) -> ToolRegistry:
    """真 registry 的替身：只要能回一段指定 facts 就夠（本節測的是出口複查）。"""

    class _Reg:
        def __init__(self):
            self.call_args: list[dict] = []

        def to_openai_tools(self, identity, stage, *, readonly_view=False):
            return []

        async def call(self, identity, name, args, timeout_s, *, stage,
                       readonly_view=False, for_model=False):
            self.call_args.append({"name": name, "args": dict(args)})
            return ToolResult(ok=True, data={"facts": facts})

    return _Reg()


@pytest.mark.req(_REQ)
async def test_facts_carrying_a_url_are_replaced_by_the_fixed_sentence():
    """導流白名單外的 URL ⇒ 整段改回固定句（⛔ 不遮罩後送）。

    正對照組：拿掉 URL 的**同一段** facts 就原樣送出——證明擋下來的是 URL，
    不是這條路徑本來就回不了 facts。
    """
    clean = "帳單「2026 年 8 月租金」目前狀態：未繳。"
    dirty = clean + "請至 https://evil.example.com/pay 繳費。"

    rt = _runtime(registry=_facts_registry(dirty))
    blocked = await rt.run_turn(_identity(), "select:bill:900001", {})
    assert blocked.answer == SELECT_NOT_FOUND_TEXT
    assert "select_route_not_allowed" in blocked.trace.violations

    rt2 = _runtime(registry=_facts_registry(clean))
    passed = await rt2.run_turn(_identity(), "select:bill:900001", {})
    assert passed.answer == clean
    assert "select_route_not_allowed" not in passed.trace.violations


@pytest.mark.req(_REQ)
async def test_route_check_unavailable_is_fail_closed():
    """Verifier 沒有 `_verify_routes` ⇒ **不出 facts**（fail-closed）。

    正對照組：換成真 `OutputVerifier` 的同一段 facts 就送得出去。
    """
    clean = "帳單「2026 年 8 月租金」目前狀態：未繳。"
    rt = _runtime(registry=_facts_registry(clean), verifier=FakeVerifier())
    assert not hasattr(FakeVerifier(), "_verify_routes")   # 尺的前提本身先驗一次
    blocked = await rt.run_turn(_identity(), "select:bill:900001", {})
    assert blocked.answer == SELECT_NOT_FOUND_TEXT
    assert "select_route_check_unavailable" in blocked.trace.violations

    rt2 = _runtime(registry=_facts_registry(clean))
    assert (await rt2.run_turn(_identity(), "select:bill:900001", {})).answer == clean


# ════════════════════════════════════════════════════════════════════
# 5. (iv) dialog 只寫程式摘要（S8-3）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_dialog_gets_only_the_program_summary_never_the_facts(fake_api):
    state: dict = {}
    rt = _runtime()
    result = await rt.run_turn(_identity(), "select:bill:900001", state)

    dialog = state["agent"]["dialog"]
    last = dialog[-1]
    assert last["role"] == "assistant"
    assert last["content"] == SELECT_DIALOG_SUMMARY.format(select_type="bill", ref="900001")
    # ⛔ facts 的任何一行都不得出現在 dialog 裡
    for line in [l for l in result.answer.splitlines() if l.strip()]:
        assert line not in last["content"]
    # 正對照：facts 真的有內容（不是因為 answer 是空字串才綠）
    assert len([l for l in result.answer.splitlines() if l.strip()]) >= 1


# ════════════════════════════════════════════════════════════════════
# 6. (v) trace／usage_events ⛔ 不含 id 原值（S8-6）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_trace_and_usage_event_record_type_and_has_ref_but_never_the_id(
    fake_api, monkeypatch
):
    captured: list[dict] = []
    monkeypatch.setattr(
        runtime_mod.usage_metering, "set_agent_decision", lambda d: captured.append(d)
    )
    rt = _runtime()
    result = await rt.run_turn(_identity(), "select:bill:900001", {})

    assert len(captured) == 1
    snapshot = captured[0]
    assert snapshot["select_type"] == "bill"
    assert snapshot["has_ref"] is True
    serialized = json.dumps(snapshot, ensure_ascii=False, default=str)
    assert "900001" not in serialized
    # 正對照：這把「不含」的尺看得見已知必然存在的東西（`select_type` 的值在）
    assert '"bill"' in serialized
    # trace 物件本身同樣不帶原值
    assert "900001" not in json.dumps(
        {"select_type": result.trace.select_type, "has_ref": result.trace.has_ref,
         "slot_written": result.trace.slot_written,
         "tool_calls": [tc.args_summary for tc in result.trace.tool_calls]},
        ensure_ascii=False, default=str,
    )
    assert result.answer != SELECT_NOT_FOUND_TEXT   # 正對照：這一輪真的有命中


# ════════════════════════════════════════════════════════════════════
# 7. (vi) 槽位：有 COLLECTING 列 ⇒ 寫得進；沒有 ⇒ 仍回 facts、slot_written=False
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_slot_written_true_when_a_collecting_row_exists(fake_api):
    pool = _FakePool("UPDATE 1")
    rt = _runtime(pool=pool)
    result = await rt.run_turn(_identity(), "select:bill:900001", {})

    assert result.trace.slot_written is True
    assert len(pool.calls) == 1
    _sql, args = pool.calls[0]
    assert args[0] == "mcp:1:1:s1"      # 命名空間鍵（Runtime 收到的就是它）
    assert args[1] == "bill_ref"
    assert json.loads(args[2])["value"] == "900001"


@pytest.mark.req(_REQ)
async def test_no_collecting_row_still_answers_and_marks_slot_written_false(fake_api):
    """找不到 COLLECTING 列（`UPDATE 0`）⇒ **仍回 facts**、trace 記 False。

    正對照組：同一段流程換成 `UPDATE 1` 就是 True（上一個測試），
    證明 False 不是因為這條路徑從來沒寫過槽位。
    """
    pool = _FakePool("UPDATE 0")
    rt = _runtime(pool=pool)
    result = await rt.run_turn(_identity(), "select:bill:900001", {})

    assert result.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert result.trace.slot_written is False
    assert len(pool.calls) == 1          # 有試著寫（不是靜默跳過）


@pytest.mark.req(_REQ)
async def test_no_db_pool_still_answers(fake_api):
    """沒有 pool ⇒ 槽位寫不了，但回答照出（⛔ 不因為記不住而不答）。"""
    rt = _runtime(pool=None)
    result = await rt.run_turn(_identity(), "select:bill:900001", {})
    assert result.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert result.trace.slot_written is False


# ════════════════════════════════════════════════════════════════════
# 8. (vii) 缺 user_id ⇒ 固定句＋violation（S8-12）；正對照＝帶 user_id 得 facts
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_missing_user_id_is_the_fixed_sentence_and_leaves_a_violation(fake_api):
    """租客（雙證）缺 `user_id` ⇒ 下游靜默降級成空 ⇒ 固定句，且 trace **有聲**。

    正對照組：同一個受眾補上 `user_id` 就拿得到 facts——證明擋下來的是缺證，
    不是這條路徑對 tenant 本來就查不到。
    """
    tenant = dict(target_user="tenant", mode="b2c", role_id="20151")
    rt = _runtime()
    degraded = await rt.run_turn(_identity(user_id=None, **tenant), "select:bill:900001", {})
    assert degraded.answer == SELECT_NOT_FOUND_TEXT
    assert "select_missing_user_id" in degraded.trace.violations

    rt2 = _runtime()
    ok = await rt2.run_turn(_identity(user_id="88", **tenant), "select:bill:900001", {})
    assert ok.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert "select_missing_user_id" not in ok.trace.violations


# ════════════════════════════════════════════════════════════════════
# 9. (viii) 清單點選 ⇒ 尚未兌現的待確認筆作廢；⛔ 已有 receipt 的不動
# ════════════════════════════════════════════════════════════════════
from services.agent.confirm_card import CONFIRMATION_REQUIRED_TEXT  # noqa: E402
from services.agent.confirm_card import render as render_card  # noqa: E402
from services.agent.runtime import PENDING_CONFIRM_KEY  # noqa: E402
from services.agent.tools.confirm import (  # noqa: E402
    payload_digest,
    pending_id_for,
    sha256_hex,
)

_ACTION_PAYLOAD = {
    "action": "bill_due_extend",
    "bill_id": "900001",
    "date_expire_before": "20260815",
    "days": 3,
    "date_expire_after": "20260818",
}
_ACTION_CARD = render_card("bill_due_extend", _ACTION_PAYLOAD)
_TOKEN = "tok-secret-value-must-never-leak-0123456789"
_PID = pending_id_for(_TOKEN)
_CLEAN_FACTS = "帳單「2026 年 8 月租金」目前狀態：未繳。"


class _DualPool:
    """`fetchrow`（兌現）＋`execute`（寫槽位）——這一節兩條路都會走到。"""

    def __init__(self, rows):
        self._rows = list(rows)
        self.fetchrow_calls: list[tuple] = []
        self.execute_calls: list[tuple] = []

    async def fetchrow(self, sql, *args):
        self.fetchrow_calls.append((sql, args))
        return self._rows.pop(0) if self._rows else None

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))
        return "UPDATE 1"


def _redeem_row():
    return {"token": _TOKEN,
            "payload_sha256": payload_digest(_ACTION_PAYLOAD),
            "summary_sha256": sha256_hex(_ACTION_CARD)}


class _MixedRegistry:
    """依工具名分派：查詢回 facts、寫入回 receipt。"""

    def __init__(self):
        self.calls: list[str] = []

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        return []

    async def call(self, identity, name, args, timeout_s, *, stage,
                   readonly_view=False, for_model=False):
        self.calls.append(name)
        if name == "jgb2.query.bills":
            return ToolResult(ok=True, data={"facts": _CLEAN_FACTS})
        if name == "jgb2.action.bill_due_extend":
            return ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}})
        return ToolResult(ok=False, error="NO_MATCH")


def _state_with_pending(**over) -> dict:
    pending = {"action": "bill_due_extend", "payload": dict(_ACTION_PAYLOAD),
               "card_sha256": sha256_hex(_ACTION_CARD)}
    pending.update(over)
    return {"agent": {PENDING_CONFIRM_KEY: {_PID: pending}}}


@pytest.mark.req(_REQ)
async def test_select_invalidates_pending_without_receipt_so_resubmit_is_refused():
    """出卡 → `select:` → 重送同一 `pending_id` ⇒ `CONFIRMATION_REQUIRED` 固定句。"""
    pool = _DualPool([_redeem_row()])
    rt = _runtime(registry=_MixedRegistry(), pool=pool)
    state = _state_with_pending()

    picked = await rt.run_turn(_identity(), "select:bill:900001", state)
    assert picked.answer == _CLEAN_FACTS
    entry = state["agent"][PENDING_CONFIRM_KEY][_PID]
    assert entry["invalidated"] is True
    assert "receipt" not in entry            # ⛔ 只標記、不偽造 receipt、不刪 dict

    resubmit = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert resubmit.answer == CONFIRMATION_REQUIRED_TEXT


@pytest.mark.req(_REQ)
async def test_select_never_touches_a_pending_that_already_has_a_receipt():
    """正對照組（R4.3 不變）：出卡 → 送出成功 → `select:` → 重送同一 pid
    ⇒ **仍回同一個 receipt id**，⛔ 不被作廢、⛔ 不重複建單。"""
    pool = _DualPool([_redeem_row()])          # 第二次 fetchrow ⇒ None（已兌現）
    rt = _runtime(registry=_MixedRegistry(), pool=pool)
    state = _state_with_pending()

    submitted = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert submitted.trace.receipt_id == "BILL-77"
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"id": "BILL-77"}

    await rt.run_turn(_identity(), "select:bill:900001", state)
    entry = state["agent"][PENDING_CONFIRM_KEY][_PID]
    assert "invalidated" not in entry          # ⛔ 已有 receipt 的筆不受影響

    again = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert again.trace.receipt_id == "BILL-77"
    assert again.answer == submitted.answer
