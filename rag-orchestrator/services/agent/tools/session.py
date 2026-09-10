"""`session.slots.get` / `session.slots.set` 工具（spec agentic-mcp-orchestration・任務 2.4）。

見 design.md 元件 3 表格 `session.slots.get/set` 列與資料模型 `SlotValue`。
槽位存在既有的對話 state：`form_sessions.collected_data.slots[<SlotKey>] =
{value, source, confirmed}`——這個位置與形狀原與舊鏈 `conversational_engine.
SlotValue`／`TransactionState.slots` 相同（該模組已隨舊鏈於 2026-09-10 退役），
⛔ 不另開一張表或另一個鍵，理由不變：既有 DB 資料列是同一格 jsonb，換位置／
換形狀就讀不到舊資料。

**`SlotKey` 是封閉 enum**：十值——六個識別／數量槽位（`contract_ref`／
`bill_ref`／`estate_ref`／`repair_ref`／`unit_count`／`business_type`）＋
任務 4.2 加的四個售前對話槽位（`identity_detail`／`team`／`pain`／
`interested`）——進 `input_schema.enum`，非法 key 在 registry 第④步就被擋成
`INVALID_INPUT`，⛔ 不讓模型自創槽位名——槽位名是 `jgb2.query` 圈定範圍的依據
（design 元件 3：「`ref`／`keyword` 只能在 session 已確立的 slot 範圍內縮小」），
開放槽位名等於開放圈定範圍。

**⛔ `identity`／`identity_source` 不在本 enum 內**（任務 4.2／Plan §4.1-3）：
那兩個鍵是 `runtime._slots_for_prompt` 之後由**入口身分**現算的派生值，模型與
儲存側都不得寫。`parse_slot_key("identity")` 回 `None` ⇒ `INVALID_INPUT`；
`write_slot` 首行另有一道封閉值域自驗（它是 `collected_data.slots` 唯一 DB 寫入點）。
⚠️ `identity_detail` 只是**角色子類**的自由文字，⛔ 不是身分本身、⛔ 不影響 prompt
的 `identity` 段。

**value 清洗**（`sanitize_slot_value`）：
- **≤ 120 字**（`SLOT_VALUE_MAX_CHARS`）——schema 的 `maxLength` 先擋一次，
  清洗後再截一次（清洗只會變短，這第二次是給繞過 schema 的直呼用的）。
- **去換行**：`\\n`／`\\r`／`\\t` 與其餘控制字元一律換成空白後收斂連續空白。
  理由：槽位值會回到 prompt，換行是最便宜的「假裝自己是新段落／新指令」手法。
- **去標記字元 `<>{}[]`**：模板與標記語言的骨架字元。
  ⚠️ 這**不是**完整的 prompt-injection 防線——那一層在
  `prompt_assembler.wrap_tool_data`（每回合隨機 nonce）。此處只做欄位層級的
  最小清洗，⛔ 不在這裡重造第二套包裝規則。
- 清洗後為空 ⇒ `INVALID_INPUT`（⛔ 不存空字串槽位：空槽位在
  `_has_basic_info` 的 `all(fields.get(k) ...)` 語義下等同「沒填」，
  存了只會讓人以為填過）。

**⚠️ `set` ⛔ 不建立會話列**：找不到 `state='COLLECTING'` 的對話會話 ⇒ 回
`NO_MATCH`（而非靜默成功）。理由：會話的建立要帶 `config_key` 等鍵，是
Runtime（任務 2.1／2.6）的責任；由工具補一列半成品，`handle_conversational_session`
會把它當成可續的對話接手、還原不出設定。**靜默 no-op 更糟**——UPDATE 影響 0 列
卻回 ok，模型會以為槽位存進去了。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Final, Optional, Tuple

from services.agent.identity import Identity
from services.agent.tools.registry import ToolResult, ToolSpec
from services.form_contract import CONVERSATIONAL_FORM_ID


class SlotKey(str, Enum):
    """封閉槽位鍵（design 元件 3）。值域改動＝改設計，⛔ 不在程式內以關鍵字推導。

    任務 4.2（票 B）加四值：`identity_detail`（角色子類）／`team`／`pain`／
    `interested`——售前對話要記住的答案，避免每回合重問。
    ⛔ `identity`／`identity_source` **不得加進來**（見模組 docstring）。
    """

    contract_ref = "contract_ref"
    bill_ref = "bill_ref"
    estate_ref = "estate_ref"
    repair_ref = "repair_ref"
    unit_count = "unit_count"
    business_type = "business_type"
    identity_detail = "identity_detail"
    team = "team"
    pain = "pain"
    interested = "interested"


#: `input_schema.enum` 的唯一來源（由 enum 反射，⛔ 不手抄）。
SLOT_KEYS: Final[Tuple[str, ...]] = tuple(k.value for k in SlotKey)

#: 槽位值長度上限（design 元件 3：`value: str≤120`）。
SLOT_VALUE_MAX_CHARS: Final[int] = 120

#: 欄位層級剝除的標記骨架字元（見模組 docstring）。
SLOT_MARKUP_CHARS: Final[str] = "<>{}[]"

#: 工具寫入的槽位一律標這個來源（design 資料模型 `SlotValue.source`）。
SLOT_SOURCE_TOOL: Final[str] = "tool"

#: state 內放槽位表的鍵（原與舊鏈 `conversational_engine.TransactionState.slots`
#: 同鍵，該模組已隨舊鏈於 2026-09-10 退役，鍵名本身不變）。
SLOTS_STATE_KEY: Final[str] = "slots"

_SLOT_KEY_SCHEMA: Final[dict] = {"type": "string", "enum": list(SLOT_KEYS)}

SLOTS_GET_SPEC: ToolSpec = {
    "name": "session.slots.get",
    "description": "讀回本次對話已確立的槽位（合約／帳單／物件／修繕識別、戶數、業態）。",
    "input_schema": {
        "type": "object",
        "properties": {"key": _SLOT_KEY_SCHEMA},
        "required": ["key"],
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": {"prospect": "M1", "property_manager": "M1", "tenant": "M1"},
}

SLOTS_SET_SPEC: ToolSpec = {
    "name": "session.slots.set",
    "description": (
        "把本次對話已確立的一個槽位記下來，供後續查詢縮小範圍。"
        "value 最多 120 字，只放識別字串本身。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": _SLOT_KEY_SCHEMA,
            "value": {"type": "string", "maxLength": SLOT_VALUE_MAX_CHARS},
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    },
    # ⚠️ scope="read"：`scope="write"` 在 registry 第②步會強制要求
    #    `confirmation_token`（那是 `jgb2.action.*` 的語義——對外部系統的
    #    不可逆動作）。槽位只是本次對話的暫存，要使用者按確認才記得住自己
    #    講過的合約編號是荒謬的。design 元件 3 也把 write scope 保留給
    #    `jgb2.action.*` 一列。
    #
    # 🔴 **已知缺口，留給任務 2.1／元件 7 裁（⛔ 勿在本檔自行「修掉」）**：
    #    design 元件 7 說影子以 `readonly_view=True` 建構、「寫入工具不可見」，
    #    但 `specs_for` 的唯一規則是用 `scope=="write"` 判斷可見性——
    #    `session.slots.set` 既然是 `scope="read"`，**影子看得到它，也就寫得進
    #    真實 session 的 `form_sessions.collected_data.slots`**（影子與正式回合
    #    共用同一個 `session_id`）。兩個可選出口都不在本任務範圍內：
    #      (a) `specs_for` 的可見性規則改看「會不會寫狀態」而不只看 scope；
    #      (b) `AgentRuntime` 在 `readonly_view=True` 時不把 `session.slots.set`
    #          放進工具清單。
    #    ⛔ 不得為了關掉這個缺口而把 scope 改成 "write"——那會讓正式回合的
    #    每一次記槽位都要 `confirmation_token`，等於把工具廢掉。
    "scope": "read",
    "mutates_session": True,  # DSP-016 裁：影子 readonly_view 不可見
    "stage": {"prospect": "M1", "property_manager": "M1", "tenant": "M1"},
}


def parse_slot_key(value: Any) -> Optional[SlotKey]:
    """字串 → `SlotKey`；非 str／不在封閉值域 ⇒ `None`（⛔ 不 strip、不 lower）。"""
    if not isinstance(value, str):
        return None
    try:
        return SlotKey(value)
    except ValueError:
        return None


def sanitize_slot_value(raw: Any) -> Optional[str]:
    """清洗槽位值：去控制字元與換行、去標記字元 `<>{}[]`、收斂空白、截 120 字。

    非 str 或清洗後為空 ⇒ `None`（呼叫端回 `INVALID_INPUT`）。清洗規則與理由見模組 docstring。
    """
    if not isinstance(raw, str):
        return None
    cleaned = "".join(
        " " if (ord(ch) < 32 or ord(ch) == 127) else ch for ch in raw
    )
    cleaned = "".join(ch for ch in cleaned if ch not in SLOT_MARKUP_CHARS)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    return cleaned[:SLOT_VALUE_MAX_CHARS]


def _session_id_of(identity: Identity) -> Optional[str]:
    session_id = getattr(identity, "session_id", None)
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    return session_id


async def read_slots(db_pool, session_id: str) -> Dict[str, Any]:
    """讀回該 session 的槽位表；無會話／無槽位一律回 `{}`（讀取端不需要區分兩者）。

    取法與 `services.agent.session_persistence.AgentSessionStore.get_state`
    同式（`form_id='conversational'`、`state='COLLECTING'`、最新一列；原與舊鏈
    `conversational_engine.ConversationalEngine.get_state` 同式，該模組已隨
    舊鏈於 2026-09-10 退役），⛔ 不另立第二套取法。
    """
    row = await db_pool.fetchrow(
        "SELECT collected_data FROM form_sessions "
        "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING' "
        "ORDER BY id DESC LIMIT 1",
        session_id,
        CONVERSATIONAL_FORM_ID,
    )
    if row is None or row["collected_data"] is None:
        return {}
    collected = row["collected_data"]
    if isinstance(collected, str):
        import json

        try:
            collected = json.loads(collected)
        except ValueError:
            return {}
    if not isinstance(collected, dict):
        return {}
    slots = collected.get(SLOTS_STATE_KEY)
    return slots if isinstance(slots, dict) else {}


#: 單述句槽位寫入（⛔ 不做 read-modify-write）。
#
#  為什麼是一句 SQL：讀出整個 `collected_data`、在 Python 改一個鍵、再寫回去，
#  會把同一輪內其他寫入者（引擎的 `_save`、另一個槽位的 set）在讀寫之間做的
#  更動整包蓋掉。`jsonb_set` 只改指定路徑，其餘鍵原封不動。
#
#  第二個 `CASE`：`jsonb_set` 對「父路徑不存在」是**回傳原值**（靜默不寫），
#  所以先確保 `slots` 物件存在——⛔ 不能只寫 `jsonb_set(..., ARRAY['slots', key], ...)`。
_SLOT_UPSERT_SQL: Final[str] = """
UPDATE form_sessions
   SET collected_data = jsonb_set(
           CASE WHEN COALESCE(collected_data, '{}'::jsonb) ? 'slots'
                THEN COALESCE(collected_data, '{}'::jsonb)
                ELSE COALESCE(collected_data, '{}'::jsonb) || '{"slots": {}}'::jsonb
           END,
           ARRAY['slots', $2::text],
           $3::jsonb,
           true
       ),
       last_activity_at = now()
 WHERE id = (SELECT id FROM form_sessions
              WHERE session_id = $1 AND form_id = $4 AND state = 'COLLECTING'
              ORDER BY id DESC LIMIT 1)
"""


async def write_slot(db_pool, session_id: str, key: str, value: str) -> bool:
    """把一個槽位寫進 `collected_data.slots`；找不到對話會話回 `False`（⛔ 不建列）。

    首行是**封閉值域自驗**（任務 4.2／Plan §4.1-3 第 (2) 道守門）：本函式是
    `collected_data.slots` 的唯一 DB 寫入點，而 `SLOT_KEYS` 之外的鍵——尤其
    `identity`／`identity_source`——一旦落地就會在下一回合被當成槽位讀回。
    現行呼叫端（`slots_set`）已先過 `parse_slot_key`，這道是**給未來的直呼者**
    的自驗，⛔ 不因為「現在沒有壞的呼叫端」而省略。

    Raises:
        ValueError: `key` 不在 `SLOT_KEYS` 封閉值域內（⛔ 訊息不帶 key 值本身——
            它是模型／呼叫端自由字串）。
    """
    if key not in SLOT_KEYS:
        raise ValueError("write_slot: key 不在 SLOT_KEYS 封閉值域內")
    import json

    slot_value = {
        "value": value,
        "source": SLOT_SOURCE_TOOL,
        "confirmed": False,
    }
    status = await db_pool.execute(
        _SLOT_UPSERT_SQL,
        session_id,
        key,
        json.dumps(slot_value, ensure_ascii=False),
        CONVERSATIONAL_FORM_ID,
    )
    # asyncpg 的 execute 回 command tag（"UPDATE 1"／"UPDATE 0"）。
    # 影響 0 列＝沒有進行中的對話會話 ⇒ 大聲失敗，⛔ 不回 ok。
    return isinstance(status, str) and status.strip().endswith(" 1")


async def slots_get(identity: Identity, args: dict, *, db_pool) -> ToolResult:
    """`session.slots.get`：回 `data={"slots": {...}}`（全表）。

    ⚠️ 回全表而非單鍵：模型多半是為了「我還缺什麼」而問，回全表省一次來回；
    同一 session 的槽位對同一個模型本來就全部可見，⛔ 不構成額外揭露。
    `key` 仍為必填——它決定 `text_for_model` 講哪一個槽位。
    """
    key = parse_slot_key(args.get("key"))
    if key is None:
        return ToolResult(ok=False, error="INVALID_INPUT")
    session_id = _session_id_of(identity)
    if session_id is None:
        return ToolResult(ok=False, error="INVALID_INPUT")

    slots = await read_slots(db_pool, session_id)
    entry = slots.get(key.value)
    if isinstance(entry, dict) and entry.get("value"):
        text = f"{key.value}={entry['value']}"
    else:
        text = f"{key.value} 尚未設定"
    return ToolResult(
        ok=True,
        data={"slots": slots},
        provenance=[],  # 槽位是對話暫存，不是可引用的知識來源
        text_for_model=text,
    )


async def slots_set(identity: Identity, args: dict, *, db_pool) -> ToolResult:
    """`session.slots.set`：清洗後寫入，回 `data={"slots": {...}}`（寫入後全表）。"""
    key = parse_slot_key(args.get("key"))
    if key is None:
        return ToolResult(ok=False, error="INVALID_INPUT")
    value = sanitize_slot_value(args.get("value"))
    if value is None:
        return ToolResult(ok=False, error="INVALID_INPUT")
    session_id = _session_id_of(identity)
    if session_id is None:
        return ToolResult(ok=False, error="INVALID_INPUT")

    if not await write_slot(db_pool, session_id, key.value, value):
        # 沒有進行中的對話會話（見模組 docstring 的「⛔ 不建立會話列」）
        return ToolResult(ok=False, error="NO_MATCH")

    slots = await read_slots(db_pool, session_id)
    return ToolResult(
        ok=True,
        data={"slots": slots},
        provenance=[],
        text_for_model=f"{key.value}={value}",
    )


__all__ = [
    "SlotKey",
    "SLOT_KEYS",
    "SLOT_VALUE_MAX_CHARS",
    "SLOT_MARKUP_CHARS",
    "SLOT_SOURCE_TOOL",
    "SLOTS_STATE_KEY",
    "SLOTS_GET_SPEC",
    "SLOTS_SET_SPEC",
    "parse_slot_key",
    "sanitize_slot_value",
    "read_slots",
    "write_slot",
    "slots_get",
    "slots_set",
]
