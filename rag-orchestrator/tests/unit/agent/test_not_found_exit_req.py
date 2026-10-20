"""unit：站內幫手 S5 修正輪——查無 ⇒ 程式固定句出口（2026-10-15）。

依據：plan-assistant-11-items-20261014 §3i 第 2 點（查無與沒查成分開；停止條件「查無固定句
3 次中 >1 次未被引用」⇒ 改程式出口）、§3f（S2 `missing_fields_ask_text`＋runtime 程式追問
出口是同型先例）、§7 業主裁示。凍結驗收 A1「查不到時明說查不到、⛔ 編造」、A3(b)「越權時回答
不洩漏內容、改說固定句」。S5-live 證據：11 次只有 4 次明說查不到，其餘反問或轉人。

被測物：
  - `runtime`：`jgb2.query.*`／`confirm.request` 回**帶查無標記**（`jgb2.NOT_FOUND_SOURCE`）
    的 `NO_MATCH`、非文件回合、本回合尚無查到的資料 ⇒ 以程式結束回合（`kind=answer`、
    `outcome=answered`、answer＝`PRE_LOOKUP_NOT_FOUND_TEXT`），violation `jgb2_not_found_exit`；
  - `mcp_facade._open_repairs`＋`confirm.request`：`repair_create` 出卡端，上游成功、帶 viewer
    零命中 ⇒ 查無固定句、⛔ 出卡、零 token；上游失敗（沒查成）仍照舊出卡。

資料走真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`）＋真
`mcp_facade.build_registry`；模型以 `FakeProvider` 腳本化（第二步故意寫一句模型反問，
被呼叫到就代表出口沒接住）。全部離線。
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from tests.unit.agent.confirm_pool_double import attach_token_tx  # 第 3 步 A7：token 寫入交易替身

from services import jgb_system_api as api_mod
from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.runtime import PRE_LOOKUP_NOT_FOUND_TEXT, AgentRuntime
from services.agent.tools import jgb2 as jgb2_tools
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RecordingTransport

from tests.unit.agent.test_assistant_write_actions_req import _contract_payload
from tests.unit.agent.test_document_turn_req import _doc_input
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call, _final_response,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
ROLE, FOREIGN_ROLE = "20151", "30999"
OWNER, PART = "12291", "990002"
#: fixture 人工查證（同 `test_assistant_permissions_req`）：只有 12291 看得到
OWNER_ONLY_BILL, OWNER_ONLY_CONTRACT = "769258", "79994"
OWNER_ONLY_ESTATE, OWNER_ONLY_ESTATE_TITLE = 22491, "台北大安-古亭歐風優質套房B"
#: 不存在的帳單編號（12291 也查不到；測試內以工具結果自證）
MISSING_BILL = "9876543"
EXIT_MARK = "jgb2_not_found_exit"
MODEL_ASK = "請確認編號是否正確？"          # 模型若被叫到第二步就會說這句（S5-live 實錄形狀）
_LONG_MSG = "麻煩幫我查一下這筆資料的狀況好嗎謝謝"   # 長句 ⇒ 不觸發前置查詢（只走模型工具）


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    from datetime import date
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 10, 15))


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


def _pm(user=OWNER, role=ROLE) -> Identity:
    return F.namespaced_identity(Identity(
        vendor_id=4, target_user="property_manager", mode="b2b", role_id=role, user_id=user,
        session_id="s5fix", api_key_id=1, entry="mcp"))


def _pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    pool.fetchrow = AsyncMock(return_value=None)
    return attach_token_tx(pool)


class _Reg:
    """真 `mcp_facade.build_registry` 的薄包裝：記下每一次工具呼叫的結果（測試前提自證用）。"""

    def __init__(self, pool):
        self.pool = pool
        self.inner = F.build_registry(F.FacadeDeps(get_db_pool=lambda: pool, stage="M1"))
        self.results: list = []

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        return self.inner.to_openai_tools(identity, stage, readonly_view=readonly_view)

    def specs_for(self, *a, **kw):
        return self.inner.specs_for(*a, **kw)

    async def call(self, identity, name, args, timeout_s, **kw):
        result = await self.inner.call(identity, name, args, timeout_s, **kw)
        self.results.append((name, result))
        return result


def _call(name: str, args: dict, call_id: str = "c1"):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(name, args, call_id=call_id)]))


async def _run(identity, steps, *, document=None, message=_LONG_MSG):
    """`steps`＝模型依序要打的工具呼叫；之後接一句模型反問（被叫到＝出口沒接住）。"""
    pool = _pool()
    reg = _Reg(pool)
    script = [_call(n, a, call_id=f"c{i}") for i, (n, a) in enumerate(steps, 1)]
    script.append(_final_response(kind="ask", answer=MODEL_ASK))
    provider = FakeProvider(script)
    rt = AgentRuntime(provider, reg, FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(),
                      Budget(), stage="M1", clock=FakeClock())
    kw = {"document": document} if document is not None else {}
    res = await rt.run_turn(identity, message, {}, **kw)
    return res, reg, provider


def _bill(ref):
    return ("jgb2.query.bills", {"face": "帳單異常", "ref": ref})


def _contract(ref):
    return ("jgb2.query.contracts", {"face": "合約基本資料", "ref": ref})


def _assert_program_not_found(res, reg, provider, *, leaked=()):
    name, first = reg.results[-1]
    assert (first.ok, first.error) == (False, "NO_MATCH")                 # 前提：真的是查無結果
    assert [p.source for p in first.provenance] == [jgb2_tools.NOT_FOUND_SOURCE]
    assert res.kind == "answer"
    assert res.answer == PRE_LOOKUP_NOT_FOUND_TEXT == jgb2_tools.NOT_FOUND_TEXT
    assert res.outcome["state"] == "answered" and res.outcome["expects"] == "text"
    assert EXIT_MARK in res.trace.violations
    assert len(provider.calls) == 1, "模型只被叫到工具那一步（⛔ 交模型改寫）"
    assert res.trace.llm_calls == 1
    for value in leaked:
        assert value not in res.answer


# ════════════════════════════════════════════════════════════════════
# A1／A3(b)：帳單／合約查無 ⇒ 程式固定句
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("who,step", [
    (dict(user=PART), _bill(OWNER_ONLY_BILL)),                    # 同團隊、看不到的帳單
    (dict(user=PART), _contract(OWNER_ONLY_CONTRACT)),            # 同團隊、看不到的合約
    (dict(user=OWNER), _bill(MISSING_BILL)),                      # 不存在的帳單
    (dict(user=OWNER, role=FOREIGN_ROLE), _bill(OWNER_ONLY_BILL)),        # 他團隊身分
    (dict(user=OWNER, role=FOREIGN_ROLE), _contract(OWNER_ONLY_CONTRACT)),
], ids=["990002-bill", "990002-contract", "12291-missing-bill", "30999-bill", "30999-contract"])
async def test_marked_not_found_ends_the_turn_with_the_fixed_sentence(api, who, step):
    res, reg, provider = await _run(_pm(**who), [step])
    _assert_program_not_found(res, reg, provider, leaked=(OWNER_ONLY_BILL, OWNER_ONLY_CONTRACT))


async def test_visible_bill_still_goes_to_the_model(api):
    """正對照：12291 查自己看得到的 769258 ⇒ 有資料、出口 ⛔ 介入（模型被叫第二次）。"""
    res, reg, provider = await _run(_pm(), [_bill(OWNER_ONLY_BILL)])
    assert reg.results[0][1].ok is True
    assert EXIT_MARK not in res.trace.violations
    assert len(provider.calls) == 2


class _FailingApi:
    """上游一律 500（沒查成）。"""

    def __getattr__(self, name):
        async def _fail(*a, **kw):
            return {"success": False, "data": [], "error": {"code": 500, "message": "x"}}
        return _fail


@pytest.mark.parametrize("step", [_bill(OWNER_ONLY_BILL), _contract(OWNER_ONLY_CONTRACT)],
                         ids=["bill", "contract"])
async def test_upstream_failure_does_not_take_the_exit(monkeypatch, step):
    """沒查成（上游 500）⇒ 無標記 `NO_MATCH` ⇒ 不走出口、程式 ⛔ 說查不到（照舊交模型）。"""
    monkeypatch.setattr(jgb2_tools, "_api_singleton", _FailingApi())
    res, reg, provider = await _run(_pm(), [step])
    first = reg.results[0][1]
    assert (first.ok, first.error, first.provenance) == (False, "NO_MATCH", [])   # 前提：沒查成形狀
    assert EXIT_MARK not in res.trace.violations
    assert len(provider.calls) == 2
    assert res.answer != PRE_LOOKUP_NOT_FOUND_TEXT


async def test_found_data_earlier_in_the_turn_keeps_the_model(api):
    """本回合已查到資料（grounded）後才遇到查無 ⇒ 程式 ⛔ 說「查不到」（會與資料矛盾），
    交模型；正對照＝同一個查無呼叫單獨出現時走出口。"""
    res, reg, provider = await _run(_pm(), [_bill(OWNER_ONLY_BILL), _bill(MISSING_BILL)])
    assert reg.results[0][1].ok is True
    assert reg.results[1][1].error == "NO_MATCH" and reg.results[1][1].provenance
    assert EXIT_MARK not in res.trace.violations
    assert len(provider.calls) == 3
    res2, reg2, provider2 = await _run(_pm(), [_bill(MISSING_BILL)])
    _assert_program_not_found(res2, reg2, provider2)


async def test_document_turn_does_not_take_the_exit(api):
    """文件回合 ⇒ 不走出口（照舊交模型、由文件回合的既有規則處理）；正對照見上。"""
    res, reg, provider = await _run(_pm(user=PART), [_bill(OWNER_ONLY_BILL)],
                                    document=_doc_input())
    assert [p.source for p in reg.results[0][1].provenance] == [jgb2_tools.NOT_FOUND_SOURCE]
    assert EXIT_MARK not in res.trace.violations
    assert len(provider.calls) == 2


# ════════════════════════════════════════════════════════════════════
# confirm.request 出卡端：物件／合約解析零筆、修繕單物件帶 viewer 零命中
# ════════════════════════════════════════════════════════════════════
def _confirm(payload: dict):
    return ("confirm.request", {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)})


_REPAIR = {"action": "repair_create", "estate_name": OWNER_ONLY_ESTATE_TITLE, "description": "冷氣不冷"}


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_repair_card_for_an_unseen_estate_is_the_fixed_sentence(api):
    """990002 對看不到的 22491 建修繕單（業主多語意實測 3／3 重現出卡）⇒ 出卡端固定句、零 token。"""
    res, reg, provider = await _run(_pm(user=PART), [_confirm(_REPAIR)])
    _assert_program_not_found(res, reg, provider, leaked=(str(OWNER_ONLY_ESTATE),))
    reg.pool.execute.assert_not_awaited()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert reg.pool.insert.await_count == 0 and reg.pool.burn.await_count == 0                                  # 零 token
    assert res.outcome["state"] != "confirm_pending"
    estate_call = [c for c in api._mock_transport.calls if c[1] == "/api/external/v1/estates"][-1]
    assert estate_call[2]["viewer_user_id"] == PART                        # 以 viewer 查的


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_repair_card_for_a_visible_estate_is_still_issued(api):
    """正對照：12291 同一句 ⇒ 照常出卡（token 寫一次）、出口 ⛔ 介入。"""
    res, reg, provider = await _run(_pm(), [_confirm(_REPAIR)])
    assert res.outcome["state"] == "confirm_pending"
    assert reg.results[0][1].data["estate_id"] == str(OWNER_ONLY_ESTATE)
    assert reg.pool.insert.await_count == 1
    assert EXIT_MARK not in res.trace.violations


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_repair_card_when_the_estate_lookup_failed_is_still_issued(api, monkeypatch):
    """上游失敗（沒查成）⇒ 仍維持現行「解析不出照常出卡、兌現端再擋」（⛔ 說查不到）。"""
    async def _fail(**kw):
        return {"success": False, "data": [], "error": {"code": 500, "message": "x"}}
    monkeypatch.setattr(api, "get_estate_status", _fail)
    res, reg, provider = await _run(_pm(user=PART), [_confirm(_REPAIR)])
    assert res.outcome["state"] == "confirm_pending"
    assert reg.results[0][1].data["estate_id"] is None
    assert reg.pool.insert.await_count == 1
    assert EXIT_MARK not in res.trace.violations


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_contract_card_for_an_unseen_estate_is_the_fixed_sentence(api):
    """`confirm.request` 物件解析零筆（`_not_found_result`）同樣走出口。"""
    payload = _contract_payload(estate_name=OWNER_ONLY_ESTATE_TITLE)
    res, reg, provider = await _run(_pm(user=PART), [_confirm(payload)])
    _assert_program_not_found(res, reg, provider, leaked=(str(OWNER_ONLY_ESTATE),))
    reg.pool.execute.assert_not_awaited()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert reg.pool.insert.await_count == 0 and reg.pool.burn.await_count == 0
    # 正對照：12291 同一份 payload ⇒ 出卡
    ok, _, _ = await _run(_pm(), [_confirm(payload)])
    assert ok.outcome["state"] == "confirm_pending"


async def test_open_repairs_injection_shapes(api, monkeypatch):
    """`_open_repairs` 三種結果：帶 viewer 零命中 ⇒ `{"not_found": True}`；看得到 ⇒ dict 帶
    `estate_id`；上游失敗 ⇒ `None`；沒帶 viewer ⇒ `None`（⛔ 下查無結論）。"""
    from services.agent.tools import confirm as cm

    orig = cm.confirm_request
    captured = {}

    async def _spy(identity, args, *, db_pool, open_repairs=None, **kw):
        captured["fn"] = open_repairs
        return await orig(identity, args, db_pool=db_pool, open_repairs=open_repairs, **kw)

    monkeypatch.setattr(cm, "confirm_request", _spy)       # build_registry 於呼叫時才 import
    reg = F.build_registry(F.FacadeDeps(get_db_pool=_pool, stage="M1"))
    await reg.call(_pm(), "confirm.request", {"summary": "x", "payload": json.dumps(_REPAIR)},
                   5, stage="M1", for_model=True)
    fn = captured["fn"]
    assert await fn(_pm(user=PART), OWNER_ONLY_ESTATE_TITLE) == {"not_found": True}
    seen = await fn(_pm(), OWNER_ONLY_ESTATE_TITLE)
    assert seen["estate_id"] == str(OWNER_ONLY_ESTATE)
    no_viewer = F.namespaced_identity(Identity(
        vendor_id=4, target_user="property_manager", mode="b2b", role_id=ROLE, user_id=None,
        session_id="s5fix", api_key_id=1, entry="mcp"))
    assert await fn(no_viewer, "查無此物件XYZ") is None

    async def _fail(**kw):
        return {"success": False, "data": [], "error": {"code": 500, "message": "x"}}
    monkeypatch.setattr(api, "get_estate_status", _fail)
    assert await fn(_pm(user=PART), OWNER_ONLY_ESTATE_TITLE) is None


@pytest.fixture()
def _aplus_proposal_off(monkeypatch):
    """A+ 片（`AGENT_WRITE_PROPOSAL`）：本檔以「模型自呼 `confirm.request`、以模型參數執行」為載具的
    測試＝開關 off 的正對照（開關 on 時該路徑已收掉）。開關 on 的程式路徑由
    `test_aplus_card_program_only_req.py` 驗出卡、缺欄追問、查無固定句、帳單候選點選、照片與物件記憶前處理；
    本檔其餘行為在開關 on 時沒有另寫程式路徑版本。"""
    monkeypatch.setenv("AGENT_WRITE_PROPOSAL", "off")
