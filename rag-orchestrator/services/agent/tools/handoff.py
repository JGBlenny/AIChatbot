"""`handoff.request` 工具（spec agentic-mcp-orchestration・任務 2.4）。

見 design.md 元件 3 表格 `handoff.request` 列：輸入 `{reason, fact_class}`，
輸出 `data={message, handoff}`，`message` 一律取自
`conversational_config.effective_handoff_message(cfg)`。

**值域唯一來源＝`presales_gate.HandoffReason`（⛔ 不在本檔另抄一份字面量）**：
2.4 把 `tool_unavailable`／`budget_exhausted` 兩值加進該 enum，本檔的
`input_schema.enum` 由 enum 反射產生——多一份手抄清單就會有兩份會漂的真相，
而漂掉的那一份正好是「模型能不能講出這個 reason」的守門。

⚠️ **舊鏈隔離 S3（2026-09-10）失去的防線**：舊鏈 `routers/chat.py` 曾有自己的
`HandoffSignal.reason`（pydantic `Literal`），與這裡的 `HandoffReason` 逐值核對
由 `tests/unit/agent/test_session_confirm_tools_req.py` 的一條回歸測試把關——
舊鏈砍掉後那份 Literal 與測試一併消失，**本檔現在是這個值域唯一的權威**、
⛔ 不再有第二份獨立真相可以互相對帳防漂移。日後改動 `HandoffReason` 的值域
前，除了走 `presales_gate.py` 這個唯一來源，也要記得：這裡沒有另一個「兩邊
都要改」的提醒機制了，全靠人記得。

**⚠️ 三個刻意的決定：**

1. **⛔ 不呼叫 `presales_gate.build_handoff`**：那支由 `fact_class` 的敏感性
   *推導* reason（只會回 `no_grounding`／`sensitive_no_grounding` 兩值），
   而本工具的 reason 是**模型指定的**（例如 `tool_unavailable`）。用它會把
   模型講的原因悄悄改寫成另一個原因。故直接建構 `Handoff`——
   ⛔ 這不是繞過閘門：`Handoff` 只是 dataclass，閘門在 reason 的封閉值域。

2. **設定查不到 ⇒ 退回 code 保底固定句，⛔ 不回錯誤**：handoff 是整條回合的
   **最後出口**。若它自己會因為 DB 抖動而失敗，模型就只剩「自己編一段話」
   一條路——那正是 presales-grounding-gate 立案要擋的病灶。
   `effective_handoff_message(None)` 回 `PRESALES_HANDOFF_MESSAGE` 常數，
   是合法且安全的固定句，故此處 fail-soft 成立。

3. **`provenance=[]`（空）**：固定句不是「知識來源」。Verifier 步③④ 對它沒有
   可逐字比對的 `Provenance.text`，模型若拿 handoff 當引用來源一律會被拒——
   這是要的行為，⛔ 不得為了讓模型好引用而在這裡塞一筆 `citable=True`。
"""
from __future__ import annotations

from typing import Any, Final, Optional, Tuple

from services.agent.identity import Identity
from services.agent.tools.registry import ToolResult, ToolSpec
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import FactClass, Handoff, HandoffReason, parse_fact_class

#: 模型可傳的 reason 值域＝`HandoffReason` 全值域（現行四值＋2.4 的兩個新值）。
HANDOFF_REASONS: Final[Tuple[str, ...]] = tuple(r.value for r in HandoffReason)
#: `fact_class` 值域＝`FactClass` 封閉七值（presales_gate 需求 3.1）。
HANDOFF_FACT_CLASSES: Final[Tuple[str, ...]] = tuple(f.value for f in FactClass)

HANDOFF_SPEC: ToolSpec = {
    "name": "handoff.request",
    "description": (
        "本題無法以工具取回的資料回答時，取回固定的轉人文案與結構化轉人訊號。"
        "reason 說明為何轉人；fact_class 是本題的事實分類。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "enum": list(HANDOFF_REASONS)},
            "fact_class": {"type": "string", "enum": list(HANDOFF_FACT_CLASSES)},
        },
        "required": ["reason", "fact_class"],
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": {"prospect": "M1", "property_manager": "M1", "tenant": "M1"},
}


def parse_handoff_reason(value: Any) -> Optional[HandoffReason]:
    """字串 → `HandoffReason`；非 str／不在封閉值域 ⇒ `None`。

    ⛔ 不 strip、不 lower、不做同義映射——比照
    `presales_gate.parse_fact_class` 的刻意設計：容忍變體等於讓上游的資料
    品質問題靜默通過。
    """
    if not isinstance(value, str):
        return None
    try:
        return HandoffReason(value)
    except ValueError:
        return None


async def _resolve_config(db_pool, identity: Identity):
    """取本次身分對應的對話設定；任何取不到的情形一律回 `None`（見模組 docstring 決定 2）。"""
    if db_pool is None:
        return None
    target_user = getattr(identity, "target_user", None)
    if not isinstance(target_user, str) or not target_user:
        return None
    try:
        from services.conversational_config import config_for_target_user

        return await config_for_target_user(db_pool, target_user)
    except Exception as exc:  # noqa: BLE001 — fail-soft 到 code 保底固定句
        print(f"⚠️ [handoff.request] 取對話設定失敗，改用 code 保底固定句：{exc}")
        return None


async def handoff_request(
    identity: Identity,
    args: dict,
    *,
    db_pool=None,
    cfg=None,
) -> ToolResult:
    """`handoff.request` 入口。

    Args:
        identity: 呼叫者身分（取 `target_user` 決定用哪一份對話設定）。
        args: `{"reason": <HandoffReason 值>, "fact_class": <FactClass 值>}`。
        db_pool: 查對話設定用（handoff_message／handoff_channel）；`None` ⇒ 走 code 保底。
        cfg: 已取好的 `ConversationalConfig`（呼叫端／測試已有時直接帶入，省一次查詢）。

    Returns:
        `ToolResult(ok=True, data={"message": str, "handoff": {...}})`；
        reason 不在封閉值域 ⇒ `INVALID_INPUT`。
    """
    reason = parse_handoff_reason(args.get("reason"))
    if reason is None:
        return ToolResult(ok=False, error="INVALID_INPUT")

    # `fact_class` 的封閉值域由 `input_schema.enum` 在 registry 第④步擋；
    # 直呼（繞過 registry）時沿用 presales_gate 的唯一正規化函式，⛔ 不另寫第二份。
    fact_class = parse_fact_class(args.get("fact_class"))

    if cfg is None:
        cfg = await _resolve_config(db_pool, identity)

    message = effective_handoff_message(cfg)
    channel = effective_handoff_channel(cfg)
    handoff = Handoff(
        reason=reason, fact_class=fact_class, channel=channel, message=message
    )
    return ToolResult(
        ok=True,
        data={"message": message, "handoff": handoff.to_dict()},
        provenance=[],  # 固定句不是知識來源（見模組 docstring 決定 3）
        text_for_model=message,
    )


__all__ = [
    "HANDOFF_SPEC",
    "HANDOFF_REASONS",
    "HANDOFF_FACT_CLASSES",
    "parse_handoff_reason",
    "handoff_request",
]
