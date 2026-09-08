"""unit：`jgb2.action.*` 寫入型工具＋`register()` 對 write 的強制守門
（子 spec `agent-write-tools` W1b F2／W4｜DSP-038｜S-8／S-9）。

覆蓋（每條一個唯一預期，⛔ 不互相代替）：
- (F2) `register()` 對 `scope=="write"` 缺 `mcp_only=True` ⇒ **註冊當下 raise**。
- (S-9) 共用 wrapper：沒綁 checker／沒帶 token／錯 session／未兌現 ⇒ 一律
  `CONFIRMATION_REQUIRED`，且 **handler 一次都沒被叫到**（⛔ 不是「叫了才擋」）。
- (S-8) pm 缺 `user_id` ⇒ `NO_MATCH`（讀是單證、寫不是）。
- 範圍讀：帳單不在可見清單／物件名稱查不到 ⇒ `NO_MATCH`，且**替身無任何變更**。
- 正向：替身 receipt；`repair_create` 接受**父節點分類＋空描述**。
- 失敗注入（`MOCK_FAIL_NEXT_WRITE`）⇒ 誠實回錯且**不留殘單**。
- 冪等：同一把 token 送兩次 ⇒ 同一份 receipt、替身只變一次。

全部離線：真 `JGBSystemAPI` ＋ `JGBMockTransport`（純記憶體 fixture），
假 checker，⛔ 不接觸真 DB／真 LLM／真網路。
"""
from __future__ import annotations

import pytest

from services.agent.identity import Identity
from services.agent.tools import action as action_tools
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.jgb_system_api import JGBSystemAPI

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.2"

#: demo fixture 的既有資料（`services/jgb/fixture_data/demo_vendor4.json`）：
#: 帳單 900001 到期日 20260815、宣告可見於 user 9001（合成凍結鏈；demo 用戶 12291 只看真資料列）；物件 456 title「信義區套房A」。
_ROLE = "20151"
_USER = "9001"
_BILL = "900001"
_BILL_DUE = 20260815
_ESTATE_NAME = "信義區套房A"
#: 分類樹的**父節點**名稱（`repair_categories` 的大類；⛔ 不是葉節點）。
_PARENT_CATEGORY = "家電維修"


def _pm(**over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b",
                role_id=_ROLE, user_id=_USER, session_id="mcp:1:4:s1",
                api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


@pytest.fixture()
def api(monkeypatch) -> JGBSystemAPI:
    """真 `JGBSystemAPI` ＋替身 transport（每個測試一份獨立 fixture 狀態）。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    instance = JGBSystemAPI()
    monkeypatch.setattr(jgb2_tools, "_api_singleton", instance)
    return instance


class _Calls:
    """記錄 checker 收到的 `(token, session_id)`，並可設定它回什麼。"""

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.seen: list = []

    async def __call__(self, token, session_id):
        self.seen.append((token, session_id))
        return self.ok


def _registry(checker=None, *, write_flag: bool = True) -> ToolRegistry:
    reg = ToolRegistry(write_tools_enabled=write_flag, redeem_checker=checker)
    for spec, fn in action_tools.ACTION_SPECS:
        reg.register(spec, fn)
    return reg


async def _call(reg: ToolRegistry, name: str, payload: dict, *,
                identity: Identity = None, token: str = "tok-1") -> ToolResult:
    args = {"payload": payload}
    if token is not None:
        args["confirmation_token"] = token
    return await reg.call(identity or _pm(), name, args, timeout_s=5,
                          stage="M1", for_model=True)


def _extend_payload(**over) -> dict:
    base = {"action": "bill_due_extend", "bill_id": _BILL,
            "date_expire_before": _BILL_DUE, "days": 3,
            "date_expire_after": 20260818}
    base.update(over)
    return base


def _repair_payload(**over) -> dict:
    base = {"action": "repair_create", "estate_name": _ESTATE_NAME,
            "category_name": _PARENT_CATEGORY, "description": "熱水器不會熱",
            "emergency_status": 1}
    base.update(over)
    return base


def _bill_due(api: JGBSystemAPI, bill_id: int = int(_BILL)) -> int:
    """直接讀替身 fixture 的到期日（⛔ 不經被測的那條路，避免自證）。"""
    return api._mock_transport.fixtures.by_id(bill_id)["date_expire"]


def _repair_count(api: JGBSystemAPI) -> int:
    return len(api._mock_transport.repair_fixtures.rows())


# ---------------------------------------------------------------------------
# F2：register() 對 scope="write" 的兩條硬性要求
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_register_rejects_write_tool_without_mcp_only():
    """⛔「忘了寫 `mcp_only`」不得只是少一道閘——它必須註冊不進來。"""
    reg = ToolRegistry(write_tools_enabled=True)
    spec = {
        "name": "jgb2.action.forgot_mcp_only",
        "description": "",
        "input_schema": {"type": "object",
                         "properties": {"payload": {"type": "object"},
                                        "confirmation_token": {"type": "string"}}},
        "scope": "write",
        "stage": {"tenant": "M4"},
    }
    with pytest.raises(ValueError) as e:
        reg.register(spec, lambda *_a, **_k: None)
    assert "mcp_only" in str(e.value)

    # 正對照組：補上 `mcp_only=True` 的同一份 spec 註冊得進來
    # ⇒ 上面的 raise 是這一條規則擋的，不是 spec 本身有別的毛病。
    reg.register({**spec, "mcp_only": True}, lambda *_a, **_k: None)
    assert "jgb2.action.forgot_mcp_only" in {
        s["name"] for s in reg.specs_for(
            Identity(vendor_id=1, target_user="tenant", mode="b2c", entry="mcp"),
            "M4", for_model=True)
    }


@pytest.mark.req(_REQ)
def test_write_tool_hidden_from_rest_entry_even_if_mcp_only_missing_in_spec_dict():
    """繞過 `register()` 直接塞進 `_specs` 的 write spec（＝沒有 `mcp_only`）
    仍然對 REST 入口不可見——兩道防線互為備援，⛔ 不得只剩註冊期那一道。"""
    reg = ToolRegistry(write_tools_enabled=True)
    reg._specs["jgb2.action.smuggled"] = {          # noqa: SLF001 — 刻意繞過
        "name": "jgb2.action.smuggled", "description": "",
        "input_schema": {"type": "object", "properties": {}},
        "scope": "write", "stage": {"tenant": "M4"},
    }
    rest = Identity(vendor_id=1, target_user="tenant", mode="b2c")   # entry 落 "rest"
    assert "jgb2.action.smuggled" not in {
        s["name"] for s in reg.specs_for(rest, "M4", for_model=True)}
    # 正對照組：同一支工具對 mcp 入口可見 ⇒ 上面看不見是**入口**擋的
    mcp = Identity(vendor_id=1, target_user="tenant", mode="b2c", entry="mcp")
    assert "jgb2.action.smuggled" in {
        s["name"] for s in reg.specs_for(mcp, "M4", for_model=True)}


# ---------------------------------------------------------------------------
# S-9：共用 wrapper 的兌現閘（四種擋法，handler 都不得被叫到）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_no_redeem_checker_bound_is_confirmation_required(api):
    """沒接線 ⇒ 一律擋，⛔ 不是「沒接線就跳過檢查」。"""
    reg = _registry(checker=None)
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert result.ok is False and result.error == "CONFIRMATION_REQUIRED"
    assert _bill_due(api) == _BILL_DUE, "被擋下的呼叫不得改到任何資料"


@pytest.mark.req(_REQ)
async def test_missing_token_is_confirmation_required(api):
    reg = _registry(_Calls(ok=True))
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload(),
                         token=None)
    assert result.ok is False and result.error == "CONFIRMATION_REQUIRED"
    assert _bill_due(api) == _BILL_DUE


@pytest.mark.req(_REQ)
async def test_not_redeemed_token_is_confirmation_required(api):
    """checker 回 False（未兌現／已過期／不是這個 session 的——四者不細分）。"""
    checker = _Calls(ok=False)
    reg = _registry(checker)
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert result.ok is False and result.error == "CONFIRMATION_REQUIRED"
    assert _bill_due(api) == _BILL_DUE
    # 正對照組：checker 真的被問過，且問的是 (token, 這個 session)
    assert checker.seen == [("tok-1", "mcp:1:4:s1")]


@pytest.mark.req(_REQ)
async def test_checker_receives_caller_session_id_not_payload(api):
    """跨 session 兌現的擋法在 checker 手上 ⇒ wrapper 必須把**呼叫者的**
    `session_id` 交出去（⛔ 不是 payload 裡的任何欄位）。"""
    checker = _Calls(ok=True)
    reg = _registry(checker)
    await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload(),
                identity=_pm(session_id="mcp:1:4:other"))
    assert checker.seen[-1][1] == "mcp:1:4:other"


# ---------------------------------------------------------------------------
# S-8：pm 寫入要雙證
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_pm_without_user_id_is_no_match(api):
    """pm 的**讀**是刻意的單證路徑；**寫**不是——缺 `user_id` ⇒ NO_MATCH。"""
    reg = _registry(_Calls(ok=True))
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload(),
                         identity=_pm(user_id=None))
    assert result.ok is False and result.error == "NO_MATCH"
    assert _bill_due(api) == _BILL_DUE
    # 正對照組：同一次呼叫補上 user_id 就成功 ⇒ 擋的是雙證，不是別的東西
    ok = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert ok.ok is True


# ---------------------------------------------------------------------------
# 形狀契約（沿用 confirm_card.render）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_inconsistent_dates_are_invalid_input(api):
    """`before + days != after` ⇒ INVALID_INPUT，⛔ 不代算、⛔ 不挑一個來執行。"""
    reg = _registry(_Calls(ok=True))
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME,
                         _extend_payload(days=30))
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert _bill_due(api) == _BILL_DUE


@pytest.mark.req(_REQ)
async def test_repair_missing_description_key_is_invalid_input(api):
    """描述**可以是空字串**，但鍵必須存在（「沒填」與「忘了帶」是兩件事）。"""
    reg = _registry(_Calls(ok=True))
    payload = _repair_payload()
    payload.pop("description")
    before = _repair_count(api)
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME, payload)
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert _repair_count(api) == before


# ---------------------------------------------------------------------------
# 範圍讀（寫之前先讀一次）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_bill_outside_visible_scope_is_no_match(api):
    """不在可見清單裡的帳單編號 ⇒ NO_MATCH，且替身完全沒被寫到。"""
    reg = _registry(_Calls(ok=True))
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME,
                         _extend_payload(bill_id="999999"))
    assert result.ok is False and result.error == "NO_MATCH"
    assert _bill_due(api) == _BILL_DUE


@pytest.mark.req(_REQ)
async def test_unknown_estate_name_is_no_match(api):
    reg = _registry(_Calls(ok=True))
    before = _repair_count(api)
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME,
                         _repair_payload(estate_name="不存在的物件名稱"))
    assert result.ok is False and result.error == "NO_MATCH"
    assert _repair_count(api) == before


@pytest.mark.req(_REQ)
async def test_unknown_category_name_is_invalid_input(api):
    """分類名稱不在分類樹裡 ⇒ 拒，⛔ 不退回「隨便挑一個大類」。"""
    reg = _registry(_Calls(ok=True))
    before = _repair_count(api)
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME,
                         _repair_payload(category_name="宇宙維修"))
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert _repair_count(api) == before


# ---------------------------------------------------------------------------
# 正向：替身 receipt
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_bill_due_extend_returns_receipt_and_moves_due_date(api):
    reg = _registry(_Calls(ok=True))
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert result.ok is True
    receipt = result.data["receipt"]
    assert receipt["bill_id"] == _BILL
    assert receipt["before"] == "2026-08-15"
    assert receipt["after"] == "2026-08-18"
    # 替身真的被改到（⛔ 不只是回了一句好聽的話）
    assert _bill_due(api) == 20260818


@pytest.mark.req(_REQ)
async def test_repair_create_accepts_parent_category_and_empty_description(api):
    """line-bot 線③：分類樹涵蓋不到 ⇒ 退回大類、描述留空，照樣開得成單。"""
    reg = _registry(_Calls(ok=True))
    before = _repair_count(api)
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME,
                         _repair_payload(description=""))
    assert result.ok is True, result
    receipt = result.data["receipt"]
    assert receipt["repair_id"]
    assert _repair_count(api) == before + 1
    row = api._mock_transport.repair_fixtures.by_id(int(receipt["repair_id"]))
    # 父節點分類 ⇒ category_id 是該大類在分類樹裡的 id（依名稱查，⛔ 不寫死——分類樹是替身資料）、
    # item_id **未指定**（⛔ 不編葉節點）
    from services.jgb.repair_fixtures import repair_categories
    parent_ids = [c["id"] for c in repair_categories() if c.get("name") == _PARENT_CATEGORY]
    assert parent_ids, f"分類樹找不到大類 {_PARENT_CATEGORY!r}"
    assert row["category_id"] == parent_ids[0] and row["item_id"] is None


@pytest.mark.req(_REQ)
async def test_repair_create_fills_missing_category_and_urgency(api):
    """delta4（業主 2026-09-08 採）：分類缺值 ⇒ 歸分類樹的「其他」大類（依名稱解、item 未指定）；
    急迫缺值 ⇒ 1（非緊急）。⛔ 不寫死 id——分類樹是替身資料。"""
    reg = _registry(_Calls(ok=True))
    payload = _repair_payload()
    del payload["category_name"]
    del payload["emergency_status"]
    before = _repair_count(api)
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME, payload)
    assert result.ok is True, result
    row = api._mock_transport.repair_fixtures.by_id(int(result.data["receipt"]["repair_id"]))
    from services.jgb.repair_fixtures import repair_categories
    other_ids = [c["id"] for c in repair_categories() if c.get("name") == "其他"]
    assert other_ids, "分類樹找不到「其他」大類（delta4 的落點不存在）"
    assert row["category_id"] == other_ids[0] and row["item_id"] is None
    assert row["emergency_status"] == 1
    assert _repair_count(api) == before + 1
    # 正對照：有給分類就照給的（父節點測試另有覆蓋），給 2 就是 2
    # ⚠️ 換 token：同 token＝冪等重送會回第一張單（test_same_token_twice_creates_only_one_repair）
    result2 = await _call(reg, action_tools.REPAIR_CREATE_NAME,
                          _repair_payload(emergency_status=2), token="tok-delta4-2")
    assert result2.ok is True, result2
    row2 = api._mock_transport.repair_fixtures.by_id(int(result2.data["receipt"]["repair_id"]))
    assert row2["emergency_status"] == 2


@pytest.mark.req(_REQ)
async def test_receipt_id_is_shape_safe(api):
    """receipt 的識別碼必須過 `confirm_card.receipt_id_of` 的形狀閘
    （否則回覆句會靜默省掉單號）。"""
    from services.agent.confirm_card import receipt_id_of

    reg = _registry(_Calls(ok=True))
    out = await _call(reg, action_tools.REPAIR_CREATE_NAME, _repair_payload())
    assert receipt_id_of(out.data["receipt"]) == out.data["receipt"]["repair_id"]


# ---------------------------------------------------------------------------
# 失敗注入：誠實回錯、不留殘單
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_downstream_failure_leaves_no_partial_write(api):
    reg = _registry(_Calls(ok=True))
    api._mock_transport.fail_next_write = True
    result = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert result.ok is False and result.error == "NO_MATCH"
    assert _bill_due(api) == _BILL_DUE, "失敗注入後不得留下半套變更"
    # 正對照組：旗用畢即清 ⇒ 下一次同樣的呼叫會成功（證明上面的失敗是注入的）
    ok = await _call(reg, action_tools.BILL_DUE_EXTEND_NAME, _extend_payload())
    assert ok.ok is True and _bill_due(api) == 20260818


@pytest.mark.req(_REQ)
async def test_repair_downstream_failure_leaves_no_ticket(api):
    reg = _registry(_Calls(ok=True))
    before = _repair_count(api)
    api._mock_transport.fail_next_write = True
    result = await _call(reg, action_tools.REPAIR_CREATE_NAME, _repair_payload())
    assert result.ok is False
    assert _repair_count(api) == before, "失敗注入後不得留下殘單"


# ---------------------------------------------------------------------------
# 冪等：同一把 token 重送
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_same_token_twice_creates_only_one_repair(api):
    """下游 idempotency key＝token（design 元件 3）⇒ 同 token 重送回同一份 receipt。

    ⚠️ 這是**第二道**保險：第一道是 Runtime 用 session 狀態裡的 receipt 短路
    （R4.3），正常流程根本走不到這裡。
    """
    reg = _registry(_Calls(ok=True))
    before = _repair_count(api)
    first = await _call(reg, action_tools.REPAIR_CREATE_NAME, _repair_payload(),
                        token="tok-same")
    second = await _call(reg, action_tools.REPAIR_CREATE_NAME, _repair_payload(),
                         token="tok-same")
    assert first.ok is True and second.ok is True
    assert first.data["receipt"]["repair_id"] == second.data["receipt"]["repair_id"]
    assert _repair_count(api) == before + 1

    # 正對照組：換一把 token 就會多一張單 ⇒ 上面的「只有一張」是冪等鍵擋的
    third = await _call(reg, action_tools.REPAIR_CREATE_NAME, _repair_payload(),
                        token="tok-other")
    assert third.data["receipt"]["repair_id"] != first.data["receipt"]["repair_id"]
    assert _repair_count(api) == before + 2
