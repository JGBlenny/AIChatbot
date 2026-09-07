"""unit：`handoff.request`／`session.slots.*`／`confirm.request`（agentic-mcp-orchestration 任務 2.4）。

涵蓋：
- reason 封閉值域正反（含 2.4 新增兩值）＋`HandoffSignal` Literal 逐值對帳；
- `HandoffReason` 擴值 ⛔ 不改既有 `build_*` 的推導行為；
- slot key 白名單與 value 清洗（含經 registry 的 schema 層擋）；
- `confirm.request` 回三顆機器值、`pending_id`，且**任何欄位都不含 token**；
- `canonical_json` 決定性；
- registry 在 M3 之前 `specs_for` 取不到 write 工具（帶正對照組）。

⚠️ 每個「取不到／不存在」的斷言旁都放一個**已知必然存在**的正對照組——
   工具或條件壞掉時要看得出來是工具壞了，不是目標不存在。
"""
import json
from unittest.mock import AsyncMock

import pytest

from services.agent.identity import Identity
from services.agent.confirm_card import CONFIRM_ACTIONS
from services.agent.confirm_card import render as render_card
from services.agent.tools.confirm import (
    CONFIRM_QUICK_REPLY_VALUES,
    CONFIRM_SPEC,
    canonical_json,
    confirm_quick_replies,
    confirm_request,
    payload_digest,
    pending_id_for,
    sha256_hex,
)
from services.agent.tools.handoff import (
    HANDOFF_REASONS,
    HANDOFF_SPEC,
    handoff_request,
    parse_handoff_reason,
)
from services.agent.tools.registry import ToolRegistry, ToolSpec
from services.agent.tools.session import (
    SLOT_KEYS,
    SLOT_VALUE_MAX_CHARS,
    SLOTS_GET_SPEC,
    SLOTS_SET_SPEC,
    SlotKey,
    parse_slot_key,
    sanitize_slot_value,
    slots_get,
    slots_set,
)
from services.conversational_config import (
    PRESALES_HANDOFF_CHANNEL_DEFAULT,
    PRESALES_HANDOFF_MESSAGE,
)
from services.presales_gate import FactClass, HandoffReason, build_handoff

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:2.4"

#: DSP-038-2：`payload` 必含 `action`（封閉值域）＋該 action 的完整欄位——
#: 確認卡由 `confirm_card.render(action, payload)` 決定性產出，缺欄位即
#: `INVALID_INPUT`。本檔所有「形狀正確」的 payload 一律用這一份。
_VALID_PAYLOAD = {
    "action": "bill_due_extend",
    "bill_id": "900001",
    "date_expire_before": "20260815",
    "days": 3,
    "date_expire_after": "20260818",
}

#: 2.4 新增的兩個 reason。
_NEW_REASONS = ("tool_unavailable", "budget_exhausted")
#: 正對照組：擴值前就存在、⛔ 不得因擴值而消失。
_EXISTING_REASONS = (
    "no_grounding",
    "sensitive_no_grounding",
    "llm_mentioned_handoff",
    "partial_grounding",
)


def _identity(**over):
    base = dict(
        vendor_id=1,
        target_user="prospect",
        mode="b2c",
        session_id="backtest_session_unit_2_4",
        api_key_id=7,
    )
    base.update(over)
    return Identity(**base)


# ════════════════════════════════════════════════════════════════════
# handoff.request：reason 值域正反
# ════════════════════════════════════════════════════════════════════


@pytest.mark.req(_REQ)
def test_handoff_reason_enum_covers_existing_four_and_two_new():
    """schema 的 enum ＝ `HandoffReason` 全值域；新兩值在、舊四值也還在（正對照組）。"""
    schema_enum = HANDOFF_SPEC["input_schema"]["properties"]["reason"]["enum"]
    assert schema_enum == list(HANDOFF_REASONS)
    assert schema_enum == [r.value for r in HandoffReason]
    for value in _NEW_REASONS:
        assert value in schema_enum
    for value in _EXISTING_REASONS:   # 正對照組：擴值沒有把既有值弄丟
        assert value in schema_enum


@pytest.mark.req(_REQ)
def test_handoff_signal_literal_matches_handoff_reason_value_for_value():
    """`routers/chat.py:HandoffSignal.reason` 的 Literal 必須與 `HandoffReason` 逐值相同。"""
    from typing import get_args

    from routers.chat import HandoffSignal

    literal_values = set(get_args(HandoffSignal.model_fields["reason"].annotation))
    assert literal_values == {r.value for r in HandoffReason}


@pytest.mark.req(_REQ)
def test_parse_handoff_reason_rejects_unknown_and_non_str():
    assert parse_handoff_reason("tool_unavailable") is HandoffReason.tool_unavailable
    assert parse_handoff_reason("no_grounding") is HandoffReason.no_grounding  # 正對照組
    assert parse_handoff_reason("Tool_Unavailable") is None   # ⛔ 不做大小寫正規化
    assert parse_handoff_reason("no_such_reason") is None
    assert parse_handoff_reason(None) is None
    assert parse_handoff_reason(123) is None


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("reason", [r.value for r in HandoffReason])
async def test_handoff_request_accepts_every_reason_in_domain(reason):
    result = await handoff_request(
        _identity(), {"reason": reason, "fact_class": "pricing"}, db_pool=None
    )
    assert result.ok is True
    assert result.data["handoff"]["reason"] == reason
    assert result.data["handoff"]["fact_class"] == "pricing"


@pytest.mark.req(_REQ)
async def test_handoff_request_rejects_reason_outside_domain():
    for bad in ("no_such_reason", "", None, 42):
        result = await handoff_request(
            _identity(), {"reason": bad, "fact_class": "pricing"}, db_pool=None
        )
        assert result.ok is False
        assert result.error == "INVALID_INPUT"


@pytest.mark.req(_REQ)
async def test_handoff_request_message_is_effective_handoff_message():
    """無設定 ⇒ code 保底固定句；有設定 ⇒ 用 DB 供給的（`effective_handoff_message` 語義）。"""
    result = await handoff_request(
        _identity(), {"reason": "budget_exhausted", "fact_class": "other"}, db_pool=None
    )
    assert result.data["message"] == PRESALES_HANDOFF_MESSAGE
    assert result.data["handoff"]["message"] == PRESALES_HANDOFF_MESSAGE
    assert result.data["handoff"]["channel"] == PRESALES_HANDOFF_CHANNEL_DEFAULT
    assert result.text_for_model == PRESALES_HANDOFF_MESSAGE

    class _Cfg:
        handoff_message = "這題請洽專人。"
        handoff_channel = "line_vendor_x"

    result = await handoff_request(
        _identity(), {"reason": "budget_exhausted", "fact_class": "other"}, cfg=_Cfg()
    )
    assert result.data["message"] == "這題請洽專人。"
    assert result.data["handoff"]["channel"] == "line_vendor_x"


@pytest.mark.req(_REQ)
async def test_handoff_request_provenance_is_empty_so_it_cannot_be_cited():
    """固定句 ⛔ 不是知識來源——Verifier 步③④ 無 `Provenance.text` 可比對即拒。"""
    result = await handoff_request(
        _identity(), {"reason": "tool_unavailable", "fact_class": "feature"}, db_pool=None
    )
    assert result.provenance == []


@pytest.mark.req(_REQ)
def test_existing_build_handoff_behaviour_unchanged_by_new_reasons():
    """擴值 ⛔ 不得改動既有推導：敏感 ⇒ sensitive_no_grounding，其餘 ⇒ no_grounding。"""
    sensitive = build_handoff(FactClass.pricing, channel="c", message="m")
    assert sensitive.reason is HandoffReason.sensitive_no_grounding
    plain = build_handoff(FactClass.feature, channel="c", message="m")
    assert plain.reason is HandoffReason.no_grounding


# ════════════════════════════════════════════════════════════════════
# session.slots：白名單與清洗
# ════════════════════════════════════════════════════════════════════


@pytest.mark.req(_REQ)
def test_slot_key_enum_is_closed_ten_values():
    """封閉值域**恰好相等**（⛔ 不得改成子集斷言）。

    任務 4.2（knowledge-outline-and-intent-architecture:4.2）加四值：
    `identity_detail`／`team`／`pain`／`interested`。
    ⛔ `identity`／`identity_source` 不在其中——那是 runtime 依入口身分現算的
    派生鍵，進 enum 等於讓模型寫得進去。
    """
    assert SLOT_KEYS == (
        "contract_ref",
        "bill_ref",
        "estate_ref",
        "repair_ref",
        "unit_count",
        "business_type",
        "identity_detail",
        "team",
        "pain",
        "interested",
    )
    assert "identity" not in SLOT_KEYS and "identity_source" not in SLOT_KEYS
    assert SLOTS_GET_SPEC["input_schema"]["properties"]["key"]["enum"] == list(SLOT_KEYS)
    assert SLOTS_SET_SPEC["input_schema"]["properties"]["key"]["enum"] == list(SLOT_KEYS)
    assert SLOTS_SET_SPEC["input_schema"]["properties"]["value"]["maxLength"] == 120


@pytest.mark.req(_REQ)
def test_parse_slot_key_rejects_anything_outside_whitelist():
    assert parse_slot_key("contract_ref") is SlotKey.contract_ref   # 正對照組
    for bad in ("vendor_id", "role_id", "Contract_Ref", "", None, 1):
        assert parse_slot_key(bad) is None


@pytest.mark.req(_REQ)
def test_sanitize_slot_value_strips_newlines_markup_and_truncates():
    assert sanitize_slot_value("基隆溫馨一人宅") == "基隆溫馨一人宅"   # 正對照組：正常值原樣通過
    # 換行／tab／控制字元 → 空白並收斂
    assert sanitize_slot_value("A\nB\tC\r\nD") == "A B C D"
    # 標記骨架字元剝除
    assert sanitize_slot_value("<script>{x}[y]") == "scriptxy"
    # 前後空白 strip
    assert sanitize_slot_value("   x   ") == "x"
    # 長度上限
    long_value = "字" * (SLOT_VALUE_MAX_CHARS + 50)
    assert len(sanitize_slot_value(long_value)) == SLOT_VALUE_MAX_CHARS
    # 清洗後為空 ⇒ None（⛔ 不存空槽位）
    assert sanitize_slot_value("<>{}[]") is None
    assert sanitize_slot_value("   ") is None
    assert sanitize_slot_value("") is None
    assert sanitize_slot_value(None) is None
    assert sanitize_slot_value(123) is None


def _slots_pool(update_status="UPDATE 1", collected=None):
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value=update_status)
    pool.fetchrow = AsyncMock(
        return_value=None if collected is None else {"collected_data": collected}
    )
    return pool


@pytest.mark.req(_REQ)
async def test_slots_set_rejects_key_outside_whitelist():
    pool = _slots_pool()
    result = await slots_set(_identity(), {"key": "vendor_id", "value": "9"}, db_pool=pool)
    assert result.ok is False and result.error == "INVALID_INPUT"
    pool.execute.assert_not_awaited()


@pytest.mark.req(_REQ)
async def test_slots_set_requires_session_id():
    pool = _slots_pool()
    result = await slots_set(
        _identity(session_id=""), {"key": "contract_ref", "value": "A1"}, db_pool=pool
    )
    assert result.ok is False and result.error == "INVALID_INPUT"
    pool.execute.assert_not_awaited()


@pytest.mark.req(_REQ)
async def test_slots_set_stores_sanitized_slot_value_shape():
    """存進去的是 `{value, source:"tool", confirmed:false}`，且 value 已清洗。"""
    pool = _slots_pool(collected={"slots": {"contract_ref": {"value": "A1 B", "source": "tool", "confirmed": False}}})
    result = await slots_set(
        _identity(), {"key": "contract_ref", "value": "A1\n<B>"}, db_pool=pool
    )
    assert result.ok is True
    args = pool.execute.await_args.args
    assert args[1] == "backtest_session_unit_2_4"   # session_id
    assert args[2] == "contract_ref"                # 槽位鍵
    assert json.loads(args[3]) == {"value": "A1 B", "source": "tool", "confirmed": False}
    assert result.data["slots"]["contract_ref"]["source"] == "tool"


@pytest.mark.req(_REQ)
async def test_slots_set_without_conversational_session_fails_loudly():
    """UPDATE 影響 0 列 ⇒ `NO_MATCH`，⛔ 不得靜默回 ok（見 session.py 模組 docstring）。"""
    pool = _slots_pool(update_status="UPDATE 0")
    result = await slots_set(
        _identity(), {"key": "bill_ref", "value": "B-1"}, db_pool=pool
    )
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_REQ)
async def test_slots_get_returns_slots_map_and_flags_unset_key():
    pool = _slots_pool(collected={"slots": {"contract_ref": {"value": "A1", "source": "tool", "confirmed": False}}})
    hit = await slots_get(_identity(), {"key": "contract_ref"}, db_pool=pool)
    assert hit.ok is True and hit.data["slots"]["contract_ref"]["value"] == "A1"
    assert "A1" in hit.text_for_model

    miss = await slots_get(_identity(), {"key": "bill_ref"}, db_pool=pool)
    assert miss.ok is True
    assert "尚未設定" in miss.text_for_model


@pytest.mark.req(_REQ)
async def test_slots_get_tolerates_json_string_and_missing_session():
    pool = _slots_pool(collected=json.dumps({"slots": {"unit_count": {"value": "600"}}}))
    result = await slots_get(_identity(), {"key": "unit_count"}, db_pool=pool)
    assert result.data["slots"]["unit_count"]["value"] == "600"

    empty = _slots_pool()   # fetchrow → None（沒有對話會話）
    result = await slots_get(_identity(), {"key": "unit_count"}, db_pool=empty)
    assert result.ok is True and result.data["slots"] == {}


# ════════════════════════════════════════════════════════════════════
# confirm.request：三顆機器值、⛔ 不回 token
# ════════════════════════════════════════════════════════════════════


#: 合法 JSON 但**不是物件**（純量）——`confirm_request` 必須拒。
JSON_SCALAR = json.dumps("just a string")
#: 超過 `CONFIRM_PAYLOAD_MAX_CHARS`（8000）的字串。
OVERSIZED_PAYLOAD = "x" * 8001


def _confirm_pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return pool


@pytest.mark.req(_REQ)
async def test_confirm_request_returns_three_machine_values_reusing_engine_constants():
    """DSP-038：`value` 改成 `<引擎前綴>:<pending_id>`，label 沿用引擎常數。"""
    from services.conversational_engine import _DEFAULT_QR_LABELS, _QR_CANCEL, _QR_EDIT, _QR_SUBMIT

    assert CONFIRM_QUICK_REPLY_VALUES == (_QR_SUBMIT, _QR_EDIT, _QR_CANCEL)

    pool = _confirm_pool()
    result = await confirm_request(
        _identity(), {"summary": "要送出修繕單嗎？", "payload": json.dumps(_VALID_PAYLOAD)},
        db_pool=pool,
    )
    assert result.ok is True
    pid = result.data["pending_id"]
    assert result.data["quick_replies"] == [
        {"label": _DEFAULT_QR_LABELS[_QR_SUBMIT], "value": f"confirm_submit:{pid}"},
        {"label": _DEFAULT_QR_LABELS[_QR_EDIT], "value": f"confirm_edit:{pid}"},
        {"label": _DEFAULT_QR_LABELS[_QR_CANCEL], "value": f"confirm_cancel:{pid}"},
    ]
    assert result.data["quick_replies"] == confirm_quick_replies(pid)
    # label ⛔ 不在本檔另抄字面量：與引擎常數逐值對帳（改值時兩邊一起紅）
    assert [q["label"] for q in result.data["quick_replies"]] == [
        _DEFAULT_QR_LABELS[v] for v in (_QR_SUBMIT, _QR_EDIT, _QR_CANCEL)
    ]


@pytest.mark.req(_REQ)
async def test_confirm_request_data_carries_card_action_payload_but_never_token():
    """DSP-038-2：`data` ＝ `{pending_id, action, payload, card, quick_replies}`；
    `card` 逐字等於 `confirm_card.render(action, payload)`，`summary_sha256` 是它的雜湊。"""
    pool = _confirm_pool()
    result = await confirm_request(
        _identity(), {"summary": "模型自己寫的摘要（⛔ 不會成為卡）",
                      "payload": json.dumps(_VALID_PAYLOAD)},
        db_pool=pool,
    )
    assert result.ok is True
    assert set(result.data) == {"pending_id", "action", "payload", "card", "quick_replies"}
    assert result.data["action"] == "bill_due_extend"
    assert result.data["payload"] == _VALID_PAYLOAD
    assert result.data["card"] == render_card("bill_due_extend", _VALID_PAYLOAD)
    # 表裡的 summary_sha256 ＝ 卡文字的雜湊，⛔ 不是模型 summary 的雜湊
    insert_args = pool.execute.await_args.args
    assert insert_args[4] == sha256_hex(result.data["card"])
    assert insert_args[4] != sha256_hex("模型自己寫的摘要（⛔ 不會成為卡）")
    # pending_id 落表（$6）
    assert insert_args[6] == result.data["pending_id"] == pending_id_for(insert_args[1])


@pytest.mark.req(_REQ)
async def test_confirm_request_rejects_payload_without_valid_action():
    """`payload.action` 必填且在封閉值域內；缺欄位／不認得的 action ⇒ INVALID_INPUT。"""
    pool = _confirm_pool()
    bad_payloads = [
        {k: v for k, v in _VALID_PAYLOAD.items() if k != "action"},   # 沒有 action
        {**_VALID_PAYLOAD, "action": "delete_everything"},            # 值域外
        {**_VALID_PAYLOAD, "action": None},
        {k: v for k, v in _VALID_PAYLOAD.items() if k != "days"},     # action 對、欄位缺
    ]
    for payload in bad_payloads:
        result = await confirm_request(
            _identity(), {"summary": "s", "payload": json.dumps(payload)}, db_pool=pool
        )
        assert result.ok is False and result.error == "INVALID_INPUT", payload
    pool.execute.assert_not_awaited()   # ⛔ 一列都不得寫進表
    # 正對照組：同一支 pool、形狀正確就會過
    ok = await confirm_request(
        _identity(), {"summary": "s", "payload": json.dumps(_VALID_PAYLOAD)}, db_pool=pool
    )
    assert ok.ok is True


@pytest.mark.req(_REQ)
def test_confirm_action_enum_is_closed_and_documented_to_the_model():
    """值域封閉，且**逐字寫進工具 description**——`payload` 是 JSON 字串，
    schema 表達不了字串內部的 enum，模型只能從 description 得知值域。"""
    assert CONFIRM_ACTIONS == ("bill_due_extend", "repair_create")
    for action in CONFIRM_ACTIONS:
        assert action in CONFIRM_SPEC["description"]


@pytest.mark.req(_REQ)
async def test_confirm_request_never_returns_the_token():
    """token ⛔ 不進 `ToolResult` 的任何欄位；`pending_id` 是它的單向短摘要。"""
    pool = _confirm_pool()
    payload = dict(_VALID_PAYLOAD)
    result = await confirm_request(
        _identity(), {"summary": "確認送出", "payload": json.dumps(payload)}, db_pool=pool
    )

    insert_args = pool.execute.await_args.args
    token = insert_args[1]
    # 正對照組：token 真的被寫進 DB 了（否則下面的「找不到 token」只是因為根本沒 token）
    assert isinstance(token, str) and len(token) >= 40
    assert insert_args[2] == "backtest_session_unit_2_4"
    assert insert_args[3] == payload_digest(payload)
    # DSP-038-2：$4 改成**卡文字**的雜湊（⛔ 不再是模型 summary 的雜湊）
    assert insert_args[4] == sha256_hex(render_card("bill_due_extend", payload))
    assert insert_args[5] == 600   # 10 分鐘
    assert insert_args[6] == pending_id_for(token)

    serialized = result.model_dump_json()
    assert token not in serialized
    assert result.data["pending_id"] == pending_id_for(token)
    assert token not in result.data["pending_id"]
    assert result.provenance == []


@pytest.mark.req(_REQ)
async def test_confirm_request_rejects_malformed_input():
    """2.6 處置⑧：`payload` 已改成 **JSON 字串**（strict function calling 不吃
    開放 object）——非字串、非法 JSON、以及「合法 JSON 但不是物件」三型都要拒。"""
    pool = _confirm_pool()
    valid = json.dumps(_VALID_PAYLOAD)
    for args in (
        {"summary": "", "payload": valid},
        {"summary": "   ", "payload": valid},
        {"summary": 1, "payload": valid},
        {"summary": "ok", "payload": _VALID_PAYLOAD},     # 舊形狀：dict ⇒ 不再收
        {"summary": "ok", "payload": "not-json"},         # 非法 JSON
        {"summary": "ok", "payload": "[1, 2]"},           # 合法 JSON 但不是物件
        {"summary": "ok", "payload": JSON_SCALAR},        # 同上（純量）
        {"summary": "ok", "payload": OVERSIZED_PAYLOAD},  # 超過 CONFIRM_PAYLOAD_MAX_CHARS
        {"summary": "ok", "payload": "{}"},               # DSP-038-2：沒有 action
    ):
        result = await confirm_request(_identity(), args, db_pool=pool)
        assert result.ok is False and result.error == "INVALID_INPUT", args
    # 正對照組：形狀正確就會過
    ok = await confirm_request(_identity(), {"summary": "ok", "payload": valid}, db_pool=pool)
    assert ok.ok is True


@pytest.mark.req(_REQ)
def test_confirm_spec_payload_is_a_json_string_not_an_object():
    """2.6 處置⑧ 的形狀斷言：schema 上 `payload` 必須是 string。

    ⛔ 不得改回 `{"type": "object"}`——那是 2.4 收案註記裡明寫「與 strict
    function calling 相衝、2.6 接線時處理」的那一條。
    """
    from services.agent.tools.confirm import CONFIRM_PAYLOAD_MAX_CHARS, CONFIRM_SPEC

    props = CONFIRM_SPEC["input_schema"]["properties"]
    assert props["payload"]["type"] == "string"
    assert props["payload"]["maxLength"] == CONFIRM_PAYLOAD_MAX_CHARS
    assert set(props) == {"summary", "payload"}


@pytest.mark.req(_REQ)
async def test_confirm_request_digest_matches_redeem_side_object_digest():
    """字串進、dict 出：存進 DB 的雜湊必須等於**兌現端對 dict 算的雜湊**。

    兌現端（`redeem_token`）收到的是動作工具的 `payload` **物件**；若這裡改成
    對原始字串取雜湊，鍵順序或空白差一點就永遠兌現不了。
    """
    pool = _confirm_pool()
    payload = dict(reversed(list(_VALID_PAYLOAD.items())))   # 鍵順序相反、同一份內容
    # 故意用「鍵順序相反、帶空白」的序列化字串
    await confirm_request(
        _identity(), {"summary": "s", "payload": json.dumps(payload, indent=1)}, db_pool=pool
    )
    assert pool.execute.await_args.args[3] == payload_digest(_VALID_PAYLOAD)


@pytest.mark.req(_REQ)
async def test_confirm_request_requires_session_id():
    pool = _confirm_pool()
    result = await confirm_request(
        _identity(session_id=""),
        {"summary": "ok", "payload": json.dumps(_VALID_PAYLOAD)},
        db_pool=pool,
    )
    assert result.ok is False and result.error == "INVALID_INPUT"
    pool.execute.assert_not_awaited()


# ════════════════════════════════════════════════════════════════════
# canonical_json 決定性
# ════════════════════════════════════════════════════════════════════


@pytest.mark.req(_REQ)
def test_canonical_json_is_key_order_independent_and_compact():
    a = {"b": 1, "a": {"z": [1, 2], "y": "中文"}}
    b = {"a": {"y": "中文", "z": [1, 2]}, "b": 1}
    assert canonical_json(a) == canonical_json(b)
    assert canonical_json(a) == '{"a":{"y":"中文","z":[1,2]},"b":1}'
    assert " " not in canonical_json(a)          # separators 去空格
    assert "\\u" not in canonical_json(a)        # ensure_ascii=False
    assert payload_digest(a) == payload_digest(b)


@pytest.mark.req(_REQ)
def test_canonical_json_digest_changes_when_any_value_changes():
    base = {"repair_id": 12, "note": "水管漏水"}
    assert payload_digest(base) != payload_digest({"repair_id": 13, "note": "水管漏水"})
    assert payload_digest(base) != payload_digest({"repair_id": 12, "note": "水管漏水 "})
    assert payload_digest(base) != payload_digest({"repair_id": "12", "note": "水管漏水"})
    # 正對照組：同一份資料重算兩次必須相同
    assert payload_digest(base) == payload_digest(dict(base))


# ════════════════════════════════════════════════════════════════════
# registry：M3 之前取不到 write 工具（帶正對照組）
# ════════════════════════════════════════════════════════════════════


_FAKE_WRITE_SPEC: ToolSpec = {
    # 假的 write 工具，只為證明可見性規則；⛔ M0–M3 產線 registry 不註冊任何 `jgb2.action.*`。
    "name": "jgb2.action.fake_for_test",
    "description": "測試用假寫入工具",
    "input_schema": {
        "type": "object",
        # ⚠️ 連帶約束（registry.register 的 additionalProperties=False）：
        #    write 工具的 `confirmation_token` **必須**寫進 properties，否則守門②
        #    放行後會在第④步被封閉 schema 擋成 INVALID_INPUT。
        "properties": {
            "payload": {"type": "object"},
            "confirmation_token": {"type": "string"},
        },
        "required": ["payload", "confirmation_token"],
    },
    "scope": "write",
    # DSP-038-1／W1b：`scope="write"` **必須**同時 `mcp_only=True`（`register()` 期
    # raise），且寫入面另受 `AGENT_WRITE_TOOLS_ENABLED` 與入口 `entry=="mcp"` 兩道閘。
    "mcp_only": True,
    "stage": {"tenant": "M4", "property_manager": "M5"},
}


async def _noop_fn(identity, args):
    from services.agent.tools.registry import ToolResult

    return ToolResult(ok=True, data={})


def _registry_with_2_4_tools():
    # 旗標**釘住 True**：本檔驗的是 stage 判斷（M0–M3 看不到 write 工具），
    # ⛔ 不讓結論取決於跑測試那台機器的 env——旗標關著的話 M4 那條反向對照
    # 也會落空，整個測試就變成恆真。
    registry = ToolRegistry(write_tools_enabled=True)
    registry.register(HANDOFF_SPEC, _noop_fn)
    registry.register(SLOTS_GET_SPEC, _noop_fn)
    registry.register(SLOTS_SET_SPEC, _noop_fn)
    registry.register(CONFIRM_SPEC, _noop_fn)
    return registry


@pytest.mark.req(_REQ)
def test_no_write_tool_visible_before_m3():
    """M0–M3 任一 stage 下 `specs_for` 都拿不到 write 工具；同一次呼叫拿得到 read 工具（正對照組）。"""
    registry = _registry_with_2_4_tools()
    registry.register(_FAKE_WRITE_SPEC, _noop_fn)
    # `entry="mcp"`：⛔ 不用預設的 `"rest"`——那樣「看不見」會是**入口**擋的，
    # stage 判斷就沒被驗到（下面 M4 的反向對照也會一起落空、變成恆真）。
    identity = _identity(target_user="tenant", mode="b2c", entry="mcp")

    for stage in ("M0", "M1", "M2", "M3"):
        visible = registry.specs_for(identity, stage, for_model=True)
        names = {s["name"] for s in visible}
        assert not [s for s in visible if s.get("scope") == "write"], (
            f"stage={stage} 不該看得到任何 write 工具"
        )
        assert "jgb2.action.fake_for_test" not in names
        if stage != "M0":
            # 正對照組：同一次呼叫看得到 M1 的 read 工具 ⇒ 可見性規則本身沒壞
            assert "handoff.request" in names

    # 反向對照：把 stage 推到 M4，同一支假 write 工具就看得見 ⇒ 上面的「看不見」
    # 是 stage 判斷生效，不是 registry 壞了。
    visible_m4 = {s["name"] for s in registry.specs_for(identity, "M4", for_model=True)}
    assert "jgb2.action.fake_for_test" in visible_m4


@pytest.mark.req(_REQ)
def test_2_4_tools_are_all_read_scope_and_stage_m1():
    registry = _registry_with_2_4_tools()
    identity = _identity()
    assert {s["name"] for s in registry.specs_for(identity, "M0")} == set()
    names_m1 = {s["name"] for s in registry.specs_for(identity, "M1")}
    assert names_m1 == {
        "handoff.request",
        "session.slots.get",
        "session.slots.set",
        "confirm.request",
    }
    for spec in (HANDOFF_SPEC, SLOTS_GET_SPEC, SLOTS_SET_SPEC, CONFIRM_SPEC):
        assert spec["scope"] == "read"
        assert spec["stage"] == {
            "prospect": "M1",
            "property_manager": "M1",
            "tenant": "M1",
        }


@pytest.mark.req(_REQ)
async def test_registry_schema_layer_rejects_bad_enum_values():
    """非法 reason／非法 slot key 在 registry 第④步就被擋成 `INVALID_INPUT`。"""
    registry = _registry_with_2_4_tools()
    identity = _identity()

    bad_reason = await registry.call(
        identity, "handoff.request",
        {"reason": "no_such_reason", "fact_class": "pricing"}, 3.0, stage="M1",
    )
    assert bad_reason.error == "INVALID_INPUT"

    bad_key = await registry.call(
        identity, "session.slots.set", {"key": "vendor_id", "value": "9"}, 3.0, stage="M1",
    )
    assert bad_key.error == "INVALID_INPUT"

    too_long = await registry.call(
        identity, "session.slots.set",
        {"key": "contract_ref", "value": "字" * 121}, 3.0, stage="M1",
    )
    assert too_long.error == "INVALID_INPUT"

    # 正對照組：合法輸入走得通 ⇒ 上面三個 INVALID_INPUT 是 schema 判定，不是全都被擋
    ok = await registry.call(
        identity, "handoff.request",
        {"reason": "budget_exhausted", "fact_class": "other"}, 3.0, stage="M1",
    )
    assert ok.ok is True


@pytest.mark.req(_REQ)
def test_tool_input_schemas_carry_no_identity_keys():
    """不變量 18／27：`register()` 會擋身分鍵；四支 spec 註冊得起來即證明無身分鍵。"""
    registry = _registry_with_2_4_tools()   # register 內含身分鍵檢查，會 raise
    assert len(registry.specs_for(_identity(), "M1")) == 4


# ════════════════════════════════════════════════════════════════════
# 任務 2.9：接進 `build_registry` ＋ 命名空間身分 ＋ slots 路徑對齊
# ════════════════════════════════════════════════════════════════════
_REQ_29 = "agentic-mcp-orchestration:2.9"

_2_4_TOOL_NAMES = frozenset(
    {"handoff.request", "session.slots.get", "session.slots.set", "confirm.request"}
)


def _facade_deps(pool=None):
    from services.agent import mcp_facade as F

    return F.FacadeDeps(get_db_pool=lambda: pool, get_kb_pool=lambda: None,
                        get_retriever=lambda: None, stage="M1")


@pytest.mark.req(_REQ_29)
def test_build_registry_wires_the_four_2_4_tools():
    """2.6 收案註記「2.9 前置」①：四支 2.4 工具要真的進 `build_registry`。"""
    from services.agent import mcp_facade as F

    names = {s["name"] for s in F.union_specs(F.build_registry(_facade_deps()), "M1")}
    missing = _2_4_TOOL_NAMES - names
    assert not missing, f"未接線：{sorted(missing)}"
    # 正對照組：1.4–1.6 既有工具仍在（否則「四支都在」可能只是 registry 換了實作）
    assert {"kb.get", "help.read"} <= names
    # 不變量 27 的下限：門面聯集至少 8 支（kb.get／kb.search／help.read／
    # 五支 jgb2.query／四支 2.4）——⛔ 不寫死等於，新工具進來不該讓這條紅。
    assert len(names) >= 8, sorted(names)


@pytest.mark.req(_REQ_29)
def test_wired_mutating_tools_are_invisible_to_shadow_readonly_view():
    """DSP-016 在**接線後**仍成立：影子看不到 `slots.set`／`confirm.request`。"""
    from services.agent import mcp_facade as F

    reg = F.build_registry(_facade_deps())
    identity = _identity()

    def names(**kw):
        return {s["name"] for s in reg.specs_for(identity, "M1", **kw)}

    shadow = names(readonly_view=True, for_model=True)
    assert "session.slots.set" not in shadow
    assert "confirm.request" not in shadow
    # 正對照組：同一次呼叫看得到不寫狀態的兩支 ⇒ 上面兩個「看不到」是
    # `mutates_session` 判定，不是影子視圖整個空了
    assert "session.slots.get" in shadow and "handoff.request" in shadow
    # 反對照：非影子視角看得到 set（否則它可能根本沒註冊）
    assert "session.slots.set" in names(for_model=True)


@pytest.mark.req(_REQ_29)
async def test_wired_tools_fail_closed_without_db_pool():
    """pool 缺席 ⇒ `NO_MATCH`；⛔ `confirm.request` 不得在沒寫進表時回 ok。"""
    from services.agent import mcp_facade as F

    reg = F.build_registry(_facade_deps(pool=None))
    identity = _identity()

    for name, args in (
        ("session.slots.get", {"key": "contract_ref"}),
        ("session.slots.set", {"key": "contract_ref", "value": "A-1"}),
        ("confirm.request", {"summary": "摘要", "payload": '{"a":1}'}),
    ):
        result = await reg.call(identity, name, args, 3.0, stage="M1")
        assert result.ok is False and result.error == "NO_MATCH", name

    # 正對照組：handoff 是最後出口，⛔ 不因 pool 缺席而失敗（fail-soft 到保底句）
    handoff = await reg.call(identity, "handoff.request",
                             {"reason": "tool_unavailable", "fact_class": "other"},
                             3.0, stage="M1")
    assert handoff.ok is True and handoff.data["message"]


# ── 命名空間身分 ────────────────────────────────────────────────────
@pytest.mark.req(_REQ_29)
def test_namespaced_identity_shape_and_fail_closed():
    from services.agent import mcp_facade as F
    from services.agent.state_store import NamespacedStateStore

    ident = _identity(vendor_id=3, api_key_id=7, session_id="sid-1")
    out = F.namespaced_identity(ident)
    assert out.session_id == "mcp:7:3:sid-1"
    assert out.session_id == NamespacedStateStore(None, 7, 3).key("sid-1")
    # 其餘欄位一字不改（⛔ 只換 session_id）
    assert (out.vendor_id, out.api_key_id, out.target_user, out.mode,
            out.role_id, out.user_id) == (
        ident.vendor_id, ident.api_key_id, ident.target_user, ident.mode,
        ident.role_id, ident.user_id)
    # 原身分不被就地改（frozen dataclass ⇒ replace 產新物件）
    assert ident.session_id == "sid-1"

    # fail-closed：缺 id／鍵超長 ⇒ ValueError，⛔ 不退回裸 session_id
    for bad in (_identity(api_key_id=None), _identity(vendor_id=None)):
        with pytest.raises(ValueError):
            F.namespaced_identity(bad)
    with pytest.raises(ValueError):
        F.namespaced_identity(_identity(session_id="s" * 100))


@pytest.mark.req(_REQ_29)
def test_rest_path_identity_is_not_namespaced():
    """REST（`routers/agent_entry.build_identity`）⛔ 不加前綴——兩條路徑天然分池。"""
    from types import SimpleNamespace

    from routers.agent_entry import build_identity

    request = SimpleNamespace(vendor_id=3, target_user="prospect", mode="b2c",
                              role_id=None, user_id="u1", session_id="sid-1")
    assert build_identity(request).session_id == "sid-1"
    assert not build_identity(request).session_id.startswith("mcp:")


@pytest.mark.req(_REQ_29)
async def test_slots_tools_use_the_session_id_they_are_handed():
    """工具是拿 `identity.session_id` 去找列的——所以換身分就等於換命名空間。

    這條是「為什麼非換不可」的證據：同一個裸 `session_id`、不同身分，
    若不換身分，兩邊打到 DB 的就是同一把鍵。
    """
    seen = []

    class _Pool:
        async def fetchrow(self, sql, *args):
            seen.append(args[0])
            return None

    pool = _Pool()
    await slots_get(_identity(session_id="mcp:7:1:sid"), {"key": "contract_ref"},
                    db_pool=pool)
    await slots_get(_identity(session_id="mcp:9:2:sid"), {"key": "contract_ref"},
                    db_pool=pool)
    assert seen == ["mcp:7:1:sid", "mcp:9:2:sid"]


# ── slots 路徑對齊 ──────────────────────────────────────────────────
def _flatten(stored):
    from services.agent.runtime import _slots_for_prompt

    return _slots_for_prompt({"slots": stored})


@pytest.mark.req(_REQ_29)
def test_runtime_reads_slots_from_top_level_not_agent_subtree():
    """2.9 前置③：runtime 讀**頂層** `slots`（`session.slots.set` 寫的位置）。"""
    from services.agent.runtime import _slots_for_prompt

    stored = {"unit_count": {"value": "600", "source": "tool", "confirmed": False}}
    assert _slots_for_prompt({"slots": stored}) == {"unit_count": "600"}
    # 反對照：舊路徑 `state["agent"]["slots"]` 不再被讀（⛔ 別改回去）
    assert _slots_for_prompt({"agent": {"slots": stored}}) == {}
    # 缺鍵／型別不對 ⇒ 空表，⛔ 不炸
    assert _slots_for_prompt({}) == {}
    assert _slots_for_prompt({"slots": "not-a-dict"}) == {}
    # 已是純量就原樣（舊資料相容）；沒有 `value` 鍵的異常列跳過
    assert _slots_for_prompt({"slots": {"a": "1", "b": {"source": "x"}}}) == {"a": "1"}


@pytest.mark.req(_REQ_29)
def test_slot_value_shape_is_rejected_by_prompt_assembler_without_flattening():
    """攤平不是裝飾：`SlotValue` 直接進 PromptAssembler 會炸掉整個回合。

    這條把「為什麼 `_slots_for_prompt` 要攤平」釘住——⛔ 別把它簡化成
    `state.get("slots", {})`，那樣模型用過一次 `session.slots.set`，
    下一回合的 `build_messages` 就 raise。
    """
    from services.agent.prompt_assembler import PromptAssembler

    nonce = "0123456789abcdef"
    stored = {"unit_count": {"value": "600", "source": "tool", "confirmed": False}}
    with pytest.raises(ValueError):
        PromptAssembler._slot_blocks(stored, nonce)
    # 正對照組：攤平後同一支函式收得下
    assert PromptAssembler._slot_blocks(_flatten(stored), nonce)


@pytest.mark.req(_REQ_29)
def test_slots_set_tool_name_constant_matches_the_spec():
    """runtime 的第二份字面量與 `SLOTS_SET_SPEC["name"]` 釘在一起（改名即紅）。"""
    from services.agent.runtime import SLOTS_SET_TOOL_NAME, SLOTS_STATE_KEY
    from services.agent.tools.session import SLOTS_STATE_KEY as TOOL_SLOTS_KEY

    assert SLOTS_SET_TOOL_NAME == SLOTS_SET_SPEC["name"]
    assert SLOTS_STATE_KEY == TOOL_SLOTS_KEY == "slots"
