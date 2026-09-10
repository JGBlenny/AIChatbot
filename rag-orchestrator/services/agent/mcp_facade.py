"""MCP 門面（spec agentic-mcp-orchestration・任務 1.7）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` **元件 4**、附錄 B
不變量 27／28／31、附錄 C2／C3 相關列。

## `agent.turn`（任務 2.6，本檔下半段）
一支**門面專屬**（`facade_only=True`）的整回合工具：呼叫端給一句 `message`，
門面以 `X-JGB-Identity` 解析出的 `Identity` 呼叫同一個
`AgentRuntime.run_turn`（Verifier／固定句／預算／計量全同，⛔ 不另寫第二條
回合邏輯），一次性回 `{answer, kind, handoff, quick_replies, trace_id}`。
四個必讀約束（前置 security review 處置，見
`.kiro/specs/agentic-mcp-orchestration/reviews/m1-security-review-2.6-2.7.md`）：
- **狀態命名空間**：回合狀態一律以 `mcp:{api_key_id}:{vendor_id}:{session_id}`
  為 `form_sessions` 鍵（`services/agent/state_store.py`），⛔ 不得裸 `session_id`；
- **schema 只收 `message`**（⛔ 無 `dialog_ref`）；
- **獨立逾時** `AGENT_TURN_TIMEOUT_S`（預設 30 > `Budget.deadline_s`），逾時／
  取消 ⇒ 不 save；
- **每小時上限** `LIMITS.turns_per_hour`（DSP-045 封閉表，預設 1200，
  key `(api_key_id, vendor_id)`；⛔ 不再讀 `AGENT_TURN_CAP` env）。
註冊本身受 `AGENT_TURN_ENABLED`（預設 false）管，⛔ 不受 `AGENT_AUDIENCES` 左右。

## 命名空間身分（任務 2.9）
2.4 的 `session.slots.*`／`confirm.request` 各自用 `identity.session_id` 去
`form_sessions`／`agent_confirmation_tokens` 找列，而那些 SQL **沒有 vendor
條件**。故 `/mcp` 這條路徑交給**任何**工具的身分，一律先過
`namespaced_identity()`（`session_id` → `mcp:{api_key_id}:{vendor_id}:{session_id}`）
——否則 2.6 才擋掉的「同 session_id 跨業者互讀」會從工具這扇側門走回來。
`agent.turn` 是唯一例外（它自己餵 `NamespacedStateStore`，那支會加前綴；
換過就成雙前綴），但它傳給 `AgentRuntime.run_turn` 的身分**是**命名空間身分，
於是回合內模型呼叫的工具同樣落在命名空間鍵下。REST 路徑 ⛔ 不換（見函式 docstring）。

## 這一層在守什麼（DSP-011）
授權（誰能看到誰的個資）由 jgb2 `external/v1` 全權處理，本系統 ⛔ 不建授權層。
本系統對呼叫者只有兩道閘：**服務層閘**（有效 X-API-Key）與**額度**
（`usage_metering.quota_check`）。因此 `/mcp` 是**非公開認證面**——它只給
上游／內部呼叫者（jgb2 後端、回測工具、內部操作者），信任等級與
`/api/v1/message` 相同；身分隨請求以 `X-JGB-Identity` header 提供，⛔ 不自證、
⛔ 不簽發 bearer、⛔ 不設 `token_verifier`／`auth`。
**例外**：知識池可見性（vendor_ids／business_types／target_user／保留分類）住
本系統 DB，jgb2 管不到，仍由 `build_visibility_predicate` 謂詞守（見
`services/agent/tools/kb.py`）。

## 三道請求層檢查（順序固定，⛔ 不得調換）
1. `require_api_key_unconditional` — 缺／錯 key ⇒ 401。**無條件**，⛔ 不看
   `RAG_API_AUTH_ENFORCE`（不變量 28 以 AST 檢查本檔不得引用該旗標的判定函式；
   本檔只在 `premise_stats()` 的**前提偵測**裡讀該 env 的原始值當遙測，
   ⛔ 不用它決定放不放行）。
2. `check_origin` — Origin **三態**：缺 Origin ⇒ 放行（server-to-server client
   不送 Origin）；有且在 `MCP_ALLOWED_ORIGINS` ⇒ 放行；有且不在 ⇒ 403。
   `MCP_ALLOWED_ORIGINS` 未設定 ⇒ **啟動即 raise**（必須明示；`-` 代表空集合
   ＝「任何帶 Origin 的請求都拒」）。
3. `parse_identity` — fail-closed：JSON 不合法／缺 `vendor_id`／缺 `session_id`
   ⇒ 400；`vendor_id` 不在 `vendors` 表 ⇒ 403＋告警計數；key 的 `vendor_ids`
   非 NULL 且不含 header 的 `vendor_id` ⇒ 403；未知 `target_user` ⇒
   `_effective_target_user` 正規化為 `tenant`；`mode` 缺／非法 ⇒ `b2c`。

三道檢查在**兩個地方**各跑一次，這是刻意的縱深防禦：
- `McpServiceGate`（ASGI middleware，掛在 middleware 堆疊最外層）——擋掉
  `initialize`／`tools/list`／DELETE 等**非工具**請求，也讓「enforce 關時
  `/mcp` 缺 key 仍 401」在 MCP SDK 尚未安裝時依然成立。
- `_invoke`（每個工具薄包裝的入口）——身分**只從 SDK 的請求 context 取**，
  見下方〈SDK 用法〉。門面即使日後被改成別的掛法，工具層仍 fail-closed。

## SDK 用法（mcp 2.1.1 實查，2026-09-04）
- `from mcp.server.mcpserver import MCPServer, Context`；`MCPServer("jgb-tools")`，
  ⛔ 不傳 `token_verifier`／`auth`。
- **取 headers**：工具函式加一個標註為 `Context` 的參數，SDK 會注入；
  `ctx.headers` 是 `Mapping[str, str] | None`（實作為
  `getattr(ctx.request_context.request, "headers", None)`，HTTP 傳輸下即
  starlette 的大小寫不敏感 `Headers`；stdio 為 `None`）。SDK 的 docstring 明寫
  「Headers are client-supplied input - never treat one as an identity assertion」
  ——與 DSP-011 一致：這是**上游信任輸入**，不是自證。
- **工具註冊**：`@mcp.tool(name=..., description=...)`；input schema 由**函式簽名**
  以 pydantic 產生（`Tool.from_function` → `func_metadata(...).arg_model
  .model_json_schema()`），⛔ 無法直接餵一份 JSON Schema ⇒ 本檔以
  `_build_wrapper()` 依 `ToolSpec.input_schema` **生成對應簽名**（enum 轉
  `Literal[...]`，選填參數給 `None` 預設並在轉發前剔除）。回傳標註
  `dict[str, Any]` ⇒ `structured_output` 自動判為結構化輸出。
- **錯誤**：`from mcp.server.mcpserver.exceptions import ToolError`。實測（2.1.1）
  模型端收到的是 `Error executing tool <name>: <我們的訊息>`（`tools/base.py`
  對**刻意**的 `ToolError` 會補上工具名；真正的 crash 走 `UnexpectedToolError`，
  只給 `Error executing tool <name>`、⛔ 不帶原文）⇒ 本檔的訊息**只含業務代碼**
  （`_tool_error_message`），⛔ 不含 SQL、例外文字、身分或原文；補上的工具名
  是呼叫端本來就知道的資訊。
- **掛載**：`Mount("/mcp", app=build_asgi_app(mcp))`。三個實測坑都在
  `build_asgi_app()` 與 `McpServiceGate` 的註解裡：子 app 路徑要設 `"/"`
  （否則 `/mcp/mcp`）、要顯式關掉 SDK 的 localhost-only DNS rebinding 檢查
  （否則經 nginx 一律 421）、`POST /mcp` 無尾斜線會被外層 router 307
  （MCP client 不跟隨轉址 ⇒ 握手失敗）故由 gate 改寫路徑。
- **lifespan**：`mcp.session_manager.run()` 必須進主 app 的 lifespan，否則首個
  請求會 `RuntimeError: Task group is not initialized`；且
  `MCPServer.session_manager` 在 `streamable_http_app()` 被呼叫前存取會 raise，
  故建構順序是「先 `streamable_http_app()`（建 ASGI app 並掛好）→ lifespan 再
  `session_manager.run()`」。
- SDK 自帶的 `TransportSecurityMiddleware`（DNS rebinding）預設**停用**
  （`streamable_http_app(transport_security=None)`），本檔 ⛔ 不啟用它——
  Origin 判定的唯一來源是 `check_origin`（三態語義與 SDK 的兩態不同）。

## 額度落點（不變量 31：一次工具呼叫恰一列 `usage_events`）
**門面是唯一寫入者**：每次工具呼叫 `begin()` → `quota_check()` → 呼叫 →
`finalize()`。`app.py:usage_metering_middleware` 對 `/mcp` **只做額度短路**
（拒 ⇒ 429），⛔ 不 begin／finalize（否則一次呼叫兩列）。
`INTERNAL_RULES` 的 `session_id` 前綴規則（`backtest_`／`loop_`…）
**⛔ 不適用於 `/mcp`**：那是呼叫方可自訂的字串，等於讓呼叫方自己關掉額度。
`/mcp` 的 `is_internal` 與可用 `vendor_ids` 一律由 **API key 紀錄**決定
（migration `20260904_api_keys_agent_scope.sql`）。
計量不可用（`USAGE_METERING_ENABLED=false` 或 context 建不起來）⇒ **拒絕服務**
（`METERING_UNAVAILABLE`），⛔ 不靜默略過——額度是本系統對呼叫者的唯一控制，
量不到就等於沒有控制。
"""
from __future__ import annotations

import asyncio
import base64
import inspect
import json
import re
import logging
import os
import time
from dataclasses import dataclass, field, replace as dataclass_replace
from typing import Any, Callable, Mapping, Optional

from pydantic import BaseModel

from services.agent import image_fetch
from services.agent.identity import (
    DEFAULT_ENTRY_MODE,
    ENTRY_MODES,
    Identity,
    Stage,
    normalize_entry_mode,
)
from services.agent.limits import LIMITS
from services.agent.state_store import (
    NamespacedStateStore,
    is_expired as _session_is_expired,
    stamp_last_turn,
)
from services.agent.tools.registry import (
    Provenance,
    ToolResult,
    ToolSpec,
    ToolRegistry,
)

logger = logging.getLogger(__name__)

#: `RAG_API_AUTH_ENFORCE` 的**變數名**——只在前提偵測（遙測）裡讀原始值，
#: ⛔ 不參與任何放行判斷（不變量 28）。
_ENFORCE_ENV_NAME = "RAG_API_AUTH_ENFORCE"
_ENFORCE_TRUTHY = ("1", "true", "yes", "on")

_ALLOWED_ORIGINS_ENV = "MCP_ALLOWED_ORIGINS"
#: `MCP_ALLOWED_ORIGINS` 的「空集合」明示值——⛔ 不用空字串（那與「沒設」無法區分）。
EMPTY_ORIGIN_SET = "-"

_IDENTITY_HEADER = "x-jgb-identity"
_API_KEY_HEADER = "x-api-key"

#: `mode` 值域與預設值——**別名**，唯一定義來源在
#: `services/agent/identity.py`（`ENTRY_MODES`／`DEFAULT_ENTRY_MODE`），
#: 名稱保留給既有測試與呼叫端；⛔ 不在本檔另抄一份字面值。
_VALID_MODES = ENTRY_MODES
_DEFAULT_MODE = DEFAULT_ENTRY_MODE

_DEFAULT_STAGE: Stage = "M0"
_DEFAULT_TOOL_TIMEOUT_S = 3.0


# ════════════════════════════════════════════════════════════════════
# 錯誤型別
# ════════════════════════════════════════════════════════════════════
class McpRequestError(Exception):
    """請求層 fail-closed 拒絕（帶 HTTP 狀態碼與**業務代碼**）。

    `code` 是封閉值域的短代碼，會同時出現在 HTTP body 與（工具層時）
    `ToolError` 訊息裡——⛔ 不放例外文字、SQL、身分或原文。
    """

    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


# 400（解析失敗）
ERR_IDENTITY_MALFORMED = "IDENTITY_MALFORMED"
ERR_IDENTITY_NO_VENDOR = "IDENTITY_MISSING_VENDOR_ID"
ERR_IDENTITY_NO_SESSION = "IDENTITY_MISSING_SESSION_ID"
# 401
ERR_API_KEY = "API_KEY_REQUIRED"
# 403
ERR_ORIGIN = "ORIGIN_NOT_ALLOWED"
ERR_VENDOR_UNKNOWN = "VENDOR_UNKNOWN"
ERR_VENDOR_OUT_OF_KEY_SCOPE = "VENDOR_NOT_IN_KEY_SCOPE"
# 429／503（額度與計量）
ERR_QUOTA = "QUOTA_EXCEEDED"
ERR_METERING = "METERING_UNAVAILABLE"

#: `agent.turn` 專屬：`app.state.agent_runtime`／`app.state.agent_session_store`
#: 任一缺席（2.2 尚未接線、或啟動時 `bootstrap.build_runtime` 失敗）⇒ 回這個碼。
#: ⛔ 不退化成「就地建一個 runtime」——那會繞過 `build_runtime` 的 Verifier 自證。
ERR_AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"


# ════════════════════════════════════════════════════════════════════
# DSP-011 前提偵測（tasks 1.8 的 /api/v1/agent/health 讀這裡）
# ════════════════════════════════════════════════════════════════════
@dataclass
class _PremiseStats:
    calls_by_api_key: dict = field(default_factory=dict)
    #: DSP-011 第一旗（任務 2.8 修正）：未登錄或非 `is_internal` 的 api_key_id
    #: 分佈——⛔ 只有這個欄位致紅，`calls_by_api_key` 本身只是觀測值。
    flagged_api_keys: dict = field(default_factory=dict)
    vendor_not_in_table: int = 0
    origin_not_allowed: int = 0
    enforce_off_with_mcp_traffic: bool = False
    metering_unavailable: int = 0
    #: 任務 4.2（Plan §4.1-1）：入口 `mode` 被正規化改寫的次數——**觀測值**，
    #: ⛔ 不進 `premise.red_flags`、⛔ 不致紅（正規化是刻意行為，不是前提破裂）。
    identity_mode_normalized: int = 0


_STATS = _PremiseStats()


def _enforce_flag_is_on() -> bool:
    """`RAG_API_AUTH_ENFORCE` 的原始值是否為真——**只供遙測**。

    ⛔ 不得用於放行判斷：`/mcp` 的服務層閘無條件生效（不變量 28）。
    """
    return os.getenv(_ENFORCE_ENV_NAME, "").strip().lower() in _ENFORCE_TRUTHY


def note_mcp_traffic(api_key_id: Optional[int], *, is_internal: Optional[bool] = None) -> None:
    """記一次 `/mcp` 流量（依 api_key_id 分佈，觀測用）＋「旗標關著卻有流量」旗標。

    任務 2.8：`is_internal=False`（含未登錄 key——呼叫端在該情境傳
    `is_internal=False`）⇒ 額外累進 `flagged_api_keys`，這是 DSP-011 第一旗
    唯一致紅的依據。`is_internal=None` 代表呼叫端此刻沒有 key 屬性可傳（例如
    請求層在拿到 key 屬性前就因 `vendor_not_in_table`／`origin_not_allowed`
    失敗——那兩種已各自有獨立旗標，⛔ 不重複算進本旗，避免用「不知道」冒充「有問題」）。
    """
    key = str(api_key_id) if api_key_id is not None else "unknown"
    _STATS.calls_by_api_key[key] = _STATS.calls_by_api_key.get(key, 0) + 1
    if not _enforce_flag_is_on():
        _STATS.enforce_off_with_mcp_traffic = True
    if is_internal is False:
        _STATS.flagged_api_keys[key] = _STATS.flagged_api_keys.get(key, 0) + 1


def premise_stats() -> dict:
    """DSP-011 前提偵測四項（＋計量不可用計數）。

    design 元件 4：前三項任一非零或第四項為真 ⇒ 告警。這是兩條 P0 REJECT
    （「不建 bearer」「MCP 暴露 jgb2.query」）的補償條件——**前提破了要重開**。

    ⚠️ 任務 2.8：第一項的致紅依據改為 `mcp_calls_flagged_by_api_key`
    （未登錄或非 `is_internal` 的 key）；`mcp_calls_by_api_key` 仍原樣輸出，
    但只是觀測值——非零不再代表出事。
    """
    return {
        "mcp_calls_by_api_key": dict(_STATS.calls_by_api_key),
        "mcp_calls_flagged_by_api_key": dict(_STATS.flagged_api_keys),
        "vendor_not_in_table": _STATS.vendor_not_in_table,
        "origin_not_allowed": _STATS.origin_not_allowed,
        "enforce_off_with_mcp_traffic": _STATS.enforce_off_with_mcp_traffic,
        "metering_unavailable": _STATS.metering_unavailable,
        "identity_mode_normalized": _STATS.identity_mode_normalized,
    }


def reset_premise_stats() -> None:
    """測試用：歸零計數器（⛔ 產品路徑不呼叫）。"""
    global _STATS
    _STATS = _PremiseStats()


# ════════════════════════════════════════════════════════════════════
# headers 工具
# ════════════════════════════════════════════════════════════════════
def _header(headers: Any, name: str) -> Optional[str]:
    """大小寫不敏感取 header（starlette `Headers` 或普通 Mapping 皆可）。"""
    if headers is None:
        return None
    try:
        value = headers.get(name)
    except AttributeError:
        return None
    if value is not None:
        return value
    lowered = name.lower()
    try:
        items = headers.items()
    except AttributeError:
        return None
    for k, v in items:
        if str(k).lower() == lowered:
            return v
    return None


# ════════════════════════════════════════════════════════════════════
# Origin 三態
# ════════════════════════════════════════════════════════════════════
def load_allowed_origins() -> frozenset:
    """讀 `MCP_ALLOWED_ORIGINS`；**未設定／空字串 ⇒ raise**（啟動紅）。

    `-` 代表空集合＝「任何帶 Origin 的請求都拒」。必須明示的理由：
    「沒設定」與「刻意不允許任何瀏覽器來源」在安全語義上完全不同，
    讓它們共用同一個表示法等於允許一次遺漏靜默變成放行。
    """
    raw = os.getenv(_ALLOWED_ORIGINS_ENV)
    if raw is None or not raw.strip():
        raise RuntimeError(
            f"{_ALLOWED_ORIGINS_ENV} 未設定——`/mcp` 的 Origin 白名單必須明示；"
            f"若刻意不允許任何瀏覽器來源，請設為 {EMPTY_ORIGIN_SET!r}。"
        )
    if raw.strip() == EMPTY_ORIGIN_SET:
        return frozenset()
    return frozenset(p.strip() for p in raw.split(",") if p.strip())


def check_origin(headers: Any, allowed: Optional[frozenset] = None) -> None:
    """Origin 三態判定；不放行 ⇒ raise `McpRequestError(403, ORIGIN_NOT_ALLOWED)`。

    - **缺 Origin ⇒ 放行**：server-to-server client 不送 Origin（只記錄不告警）。
    - 有 Origin 且在白名單 ⇒ 放行。
    - 有 Origin 且不在 ⇒ 403（瀏覽器直連／DNS rebinding），計入前提偵測。
    """
    origin = _header(headers, "origin")
    if origin is None:
        return
    allow = load_allowed_origins() if allowed is None else allowed
    if origin in allow:
        return
    _STATS.origin_not_allowed += 1
    raise McpRequestError(403, ERR_ORIGIN)


# ════════════════════════════════════════════════════════════════════
# X-JGB-Identity 解析（fail-closed）
# ════════════════════════════════════════════════════════════════════
def _normalize_target_user(raw: Any) -> str:
    """未知／空 ⇒ `tenant`。⛔ 不另寫第二份判準——沿用檢索器的唯一定義。"""
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    return VendorKnowledgeRetrieverV2._effective_target_user(raw)


def _coerce_vendor_id(raw: Any) -> Optional[int]:
    """`vendor_id` 允許整數或整數字串；其餘（含 bool、浮點、空）視為缺。"""
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
        return int(raw.strip())
    return None


async def parse_identity(
    headers: Any,
    *,
    key: Optional[Mapping] = None,
    vendor_check: Callable[[int], Any],
) -> Identity:
    """把 `X-JGB-Identity` header 解析成 `Identity`（fail-closed）。

    Args:
        headers: starlette `Headers` 或普通 Mapping（MCP 工具層由
            `Context.headers` 取得）。
        key: `verify_api_key()` 回傳的 key 紀錄（`{id, name, is_internal,
            vendor_ids}`）。`vendor_ids` 非 NULL 且不含 header 的 `vendor_id`
            ⇒ 403。`None` 代表尚未驗（僅測試用）。
        vendor_check: `(vendor_id) -> bool | Awaitable[bool]`，判斷該業者是否
            存在於 `vendors` 表。**必填**——沒有它就無法 fail-closed，故
            ⛔ 不給預設值（預設值等於預設放行）。

    Raises:
        McpRequestError: 400（JSON 不合法／缺 vendor_id／缺 session_id）、
            403（vendor 不存在／不在 key 的 vendor_ids 內）。
    """
    raw = _header(headers, _IDENTITY_HEADER)
    if not raw:
        raise McpRequestError(400, ERR_IDENTITY_MALFORMED)
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        raise McpRequestError(400, ERR_IDENTITY_MALFORMED)
    if not isinstance(payload, dict):
        raise McpRequestError(400, ERR_IDENTITY_MALFORMED)

    vendor_id = _coerce_vendor_id(payload.get("vendor_id"))
    if vendor_id is None:
        raise McpRequestError(400, ERR_IDENTITY_NO_VENDOR)

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise McpRequestError(400, ERR_IDENTITY_NO_SESSION)

    # 任務 4.2（Plan §4.1-1 收尾審查 P2）：**先**正規化 `target_user` 再決 mode。
    # payload 的合法形狀含 list（`["prospect"]`）——拿原值餵
    # `normalize_entry_mode` 會比不到 prospect，留下「受眾說 prospect、可見性
    # 謂詞說 b2c」的分裂身分（正是本次要消滅的東西）。⛔ 不得對調順序。
    target_user = _normalize_target_user(payload.get("target_user"))
    mode = payload.get("mode")
    if mode not in _VALID_MODES:
        mode = _DEFAULT_MODE
    normalized_mode = normalize_entry_mode(target_user, mode)
    if normalized_mode != mode:
        _STATS.identity_mode_normalized += 1
        # ⛔ 只印 target_user 與前後 mode（皆為封閉值域的列舉值），不印 payload。
        # ⚠️ 進到這裡代表正規化真的改寫了 mode ⇒ `target_user` 必為字面值
        # `prospect`（唯一會改寫的分支），印它不等於印 payload。
        logger.info(
            "[mcp] 入口 mode 正規化：target_user=%s mode %s -> %s",
            target_user, mode, normalized_mode,
        )
    mode = normalized_mode

    exists = vendor_check(vendor_id)
    if inspect.isawaitable(exists):
        exists = await exists
    if not exists:
        _STATS.vendor_not_in_table += 1
        logger.warning("[mcp] X-JGB-Identity 的 vendor_id 不在 vendors 表（前提偵測計數）")
        raise McpRequestError(403, ERR_VENDOR_UNKNOWN)

    key_vendor_ids = (key or {}).get("vendor_ids")
    if key_vendor_ids is not None and vendor_id not in list(key_vendor_ids):
        raise McpRequestError(403, ERR_VENDOR_OUT_OF_KEY_SCOPE)

    def _opt_str(value: Any) -> Optional[str]:
        return value if isinstance(value, str) and value.strip() else None

    return Identity(
        vendor_id=vendor_id,
        target_user=target_user,
        mode=mode,
        role_id=_opt_str(payload.get("role_id")),
        user_id=_opt_str(payload.get("user_id")),
        session_id=session_id.strip(),
        api_key_id=(key or {}).get("id"),
        # DSP-038-1／W1b：**唯一**把 `entry` 設成 `"mcp"` 的真身分建構點。
        # ⛔ 不是由 payload 決定——`entry` 回答的是「從哪一道門進來」，這一行
        # 之所以能寫 `"mcp"`，是因為本函式只被 `/mcp` 的請求層（`resolve_call`）
        # 呼叫。`namespaced_identity` 走 `dataclasses.replace` ⇒ 自動繼承；
        # `_ToolListFilter` 用的也是本函式的結果（經 `resolve_call`）。
        # 其餘建構點（`routers/agent_entry.build_identity`／`health._PROBE_IDENTITY`
        # ／`outline.py`／`agent_eval.py`）一律不帶 ⇒ 落 `"rest"`（fail-closed）。
        entry="mcp",
    )


# ════════════════════════════════════════════════════════════════════
# 依賴與工具接線
# ════════════════════════════════════════════════════════════════════
@dataclass
class FacadeDeps:
    """門面所需的外部資源——一律以 **getter** 提供。

    理由：`app.py` 在 import 期就要建好 MCP server 並掛上 `Mount`，而 pool 要到
    lifespan 才存在；getter 讓「建構」與「取得資源」解耦。

    - `get_db_pool`：asyncpg pool（`api_keys`／`vendors`／`usage_events`／
      `help_center_pages`）。
    - `get_kb_pool`：psycopg2 風格 pool（`getconn()`／`putconn()`），給
      `kb.get`——`build_visibility_predicate` 回傳 `%s` 佔位符，⛔ 不可餵 asyncpg
      （任務 1.4 收案註記）。
    - `get_retriever`：`VendorKnowledgeRetrieverV2` 實例，給 `kb.search`。
    - `get_outline_resolver`：回 `tools/kb.py:OutlineResolver`（`(identity, "outline:x")
      -> ToolResult`）或 `None`，給 `kb.get("outline:*")`。`None` ⇒ `kb.get` 對
      `outline:*` 一律 `NO_MATCH`（fail-closed，⛔ 不退化成查 KB 整數 id）。
      正產線由 `app.py` 以 `services.agent.outline.make_outline_resolver(cache)`
      建好放 `app.state.outline_resolver`，這個 getter 讀它。
    - `get_app`：回 FastAPI/Starlette 的 app 物件（`agent.turn` 用）。門面靠它讀
      `app.state.agent_runtime`（2.2 建的 `AgentRuntime`）、
      `app.state.agent_session_store`（狀態存取用的 `AgentSessionStore`，
      舊鏈隔離 S3 取代原本的 `conversational_engine`）、
      `app.state.agent_outline`（行程級大綱物件）。⛔ 門面**不自建** runtime——
      `bootstrap.build_runtime` 的 Verifier 自證只跑在啟動路徑上，就地新建一個
      等於帶著一把沒驗過的尺上線。缺 ⇒ `ToolError("AGENT_UNAVAILABLE")`。
    """

    get_db_pool: Callable[[], Any]
    get_kb_pool: Optional[Callable[[], Any]] = None
    get_retriever: Optional[Callable[[], Any]] = None
    get_outline_resolver: Optional[Callable[[], Any]] = None
    get_app: Optional[Callable[[], Any]] = None
    stage: Stage = _DEFAULT_STAGE
    tool_timeout_s: float = _DEFAULT_TOOL_TIMEOUT_S


def current_stage() -> Stage:
    """部署里程碑（env `AGENT_STAGE`，預設 M0）。"""
    raw = (os.getenv("AGENT_STAGE") or "").strip().upper()
    return raw if raw in ("M0", "M1", "M2", "M3", "M4", "M5") else _DEFAULT_STAGE


# ════════════════════════════════════════════════════════════════════
# `agent.turn` 的三個 env 旋鈕（任務 2.6：回切開關／逾時／每小時上限）
# ════════════════════════════════════════════════════════════════════
#: `agent.turn` 的工具名（一處定義，⛔ 別在字面量之間漂）。
AGENT_TURN_NAME = "agent.turn"

_AGENT_TURN_ENABLED_ENV = "AGENT_TURN_ENABLED"
_AGENT_TURN_TIMEOUT_ENV = "AGENT_TURN_TIMEOUT_S"

#: 預設 **30 秒 > `Budget.deadline_s`（20）**（2.6 前置 security review P2）：
#: 門面對一般唯讀工具的 3 秒逾時是給「一次 DB／API 查詢」用的，整回合會跑
#: 多次模型呼叫，3 秒必然砍在半路。⛔ 不要把兩者合成同一個值。
_DEFAULT_AGENT_TURN_TIMEOUT_S = 30.0

#: `registry.call()` 外層 `wait_for` 相對於內層回合逾時的寬限（秒）。
#: 內層（`_agent_turn` 自己的 `wait_for`）先炸 ⇒ 保證「逾時不 save」；
#: 外層只是**卡死的 save 也有出口**的保險，⛔ 不該是先觸發的那一個。
_AGENT_TURN_OUTER_MARGIN_S = 5.0

#: 每小時每 `(api_key_id, vendor_id)` 的 `agent.turn` 次數上限——DSP-045 封閉表
#: `LIMITS.turns_per_hour`（預設 1200），⛔ 不再有本檔獨立預設常數。
_AGENT_TURN_WINDOW_S = 3600.0

#: 滑動視窗：`(api_key_id, vendor_id) -> [呼叫時戳]`。
#: ⚠️ **行程內記憶體**——多 worker 部署時每個 worker 各有一份，實際上限是
#: `cap × worker 數`。這與 `ToolRegistry` 既有的 `LIMITS.tool_calls_per_minute`／
#: `LIMITS.kb_get_per_hour` 同一個限制，⛔ 不在此另建共享計數器（那是額度層
#: `usage_metering` 的事）。
#: ⚠️ 這段滑動視窗與 `tools/registry.py:_check_and_record_rate` 是**兩份實作**：
#: registry.py 不在 2.6 的可改檔案清單內，而 `agent.turn` 的上限依 brief 歸門面。
#: 之後若要合併，合併點是 registry 的 `_prune`／`_check_and_record_*`。
_agent_turn_calls: dict = {}


def agent_turn_enabled() -> bool:
    """`AGENT_TURN_ENABLED`（**預設 false**）——關閉 ⇒ `build_registry` 不註冊，
    `/mcp` 的 `tools/list` 就看不到它。與 `AGENT_AUDIENCES` 同性質的回切開關，
    但兩者**互不管轄**：`AGENT_AUDIENCES` 只管 REST 入口（`routers/agent_entry.py`），
    ⛔ 不左右 `agent.turn`（design 1.4.6）。
    """
    return (os.getenv(_AGENT_TURN_ENABLED_ENV) or "").strip().lower() in _ENFORCE_TRUTHY


def agent_turn_timeout_s() -> float:
    """`AGENT_TURN_TIMEOUT_S`（預設 30，> `Budget.deadline_s`）；非法值回預設。"""
    raw = (os.getenv(_AGENT_TURN_TIMEOUT_ENV) or "").strip()
    if not raw:
        return _DEFAULT_AGENT_TURN_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_AGENT_TURN_TIMEOUT_S
    return value if value > 0 else _DEFAULT_AGENT_TURN_TIMEOUT_S


def agent_turn_cap() -> int:
    """`LIMITS.turns_per_hour`（DSP-045 封閉表，預設 1200／小時／
    `(api_key_id, vendor_id)`）；⛔ 不再讀 `AGENT_TURN_CAP` env。"""
    return LIMITS.turns_per_hour


def check_and_record_agent_turn(key: tuple, now: Optional[float] = None) -> bool:
    """滑動視窗記一次 `agent.turn`；已達上限 ⇒ `False`（且**不記**這一次）。"""
    now = time.monotonic() if now is None else now
    cap = agent_turn_cap()
    calls = _agent_turn_calls.setdefault(key, [])
    cutoff = now - _AGENT_TURN_WINDOW_S
    while calls and calls[0] <= cutoff:
        calls.pop(0)
    if len(calls) >= cap:
        return False
    calls.append(now)
    return True


#: `agent_configured()` 判準逐位元搬自 `app.py::_agent_configured`（任務 4.1／
#: Plan §2.1-7）——`app.py` 之後改呼叫這裡的薄別名，名稱保留給既有測試。
_AGENT_CONFIGURED_ENV_KEYS: tuple = (
    "AGENT_AUDIENCES", "AGENT_SHADOW_AUDIENCES", "AGENT_TURN_ENABLED",
)


def agent_configured() -> bool:
    """任一 agent 開關（`AGENT_AUDIENCES`／`AGENT_SHADOW_AUDIENCES`／
    `AGENT_TURN_ENABLED`）`strip()` 後不在 `{"", "0", "false", "False"}` ⇒ 真。

    ⚠️ 不是「任一有值」——`AGENT_TURN_ENABLED=0` 仍是未啟用（與 `app.py` 舊判準
    逐位元相同）。`health.py` 以**模組屬性**呼叫本函式（`mcp_facade.agent_configured()`，
    ⛔ 不 `from … import`）讓 monkeypatch 生效；`agent_turn_enabled()` 語義不等價
    （只看 `AGENT_TURN_ENABLED`），⛔ 不可互相替代。
    """
    return any(
        (os.getenv(k, "") or "").strip() not in ("", "0", "false", "False")
        for k in _AGENT_CONFIGURED_ENV_KEYS
    )


def reset_agent_turn_cap() -> None:
    """測試用：清掉行程內的滑動視窗（⛔ 產品路徑不呼叫）。"""
    _agent_turn_calls.clear()


class LazyPsycopg2Pool:
    """`getconn()`／`putconn()` 介面的最小 pool，延遲建立。

    `kb.get` 走同步 psycopg2（見 `tools/kb.py` 的佔位符風格硬約束），而 app 只有
    asyncpg pool。這裡在**第一次被用到**時才建連線池，避免 import 期連 DB。
    """

    def __init__(self, minconn: int = 1, maxconn: int = 4) -> None:
        self._minconn = minconn
        self._maxconn = maxconn
        self._pool = None

    def _ensure(self):
        if self._pool is None:
            import psycopg2.pool

            from services.db_utils import get_db_config

            self._pool = psycopg2.pool.ThreadedConnectionPool(
                self._minconn, self._maxconn, **get_db_config()
            )
        return self._pool

    def getconn(self):
        return self._ensure().getconn()

    def putconn(self, conn):
        self._ensure().putconn(conn)

    def closeall(self):
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


HELP_READ_SPEC: ToolSpec = {
    "name": "help.read",
    "description": "依 slug 讀取幫助中心單頁；citable=false 的頁可讀但不得當引用來源。",
    "input_schema": {
        "type": "object",
        "properties": {"slug": {"type": "string"}},
        "required": ["slug"],
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
}


#: W8 (3)／DSP-042（design 元件 3）：**只有 `repairs` 域**多收一個 `estate_id`。
#: ⚠️ 這張表是 `_jgb2_spec(extra_properties=…)` 的唯一來源——⛔ 不在 `build_registry`
#: 裡臨時組一份字典字面量，那會讓「哪個域多了哪個參數」散成兩處。
#: ⛔ 值域不得放進任何身分鍵（不變量 27 會擋，但這裡先講清楚為什麼不該試）。
JGB2_EXTRA_PROPERTIES: dict[str, dict] = {
    "repairs": {"estate_id": {"type": "string", "maxLength": 32}},
}

#: L15 (b)：**契約層的定義句**——`keyword` 在該域是什麼、查不到時往哪走。
#: ⛔ 只寫定義、⛔ 不寫例子（`feedback_no_special_case_fixes`）；表裡沒有的域
#: description 逐位元不變（回退面＝把該域從這張表拿掉）。
JGB2_DOMAIN_HINTS: dict[str, str] = {
    "contracts": "keyword 是物件名稱或承租人名；帳單編號查不到合約，同戶合約先用該帳單的物件名稱查。",
    "bills": "keyword 是物件名稱。",
}


def _jgb2_spec(domain: str, faces: list, extra_properties: Optional[dict] = None) -> ToolSpec:
    """`jgb2.query.<domain>` 的 ToolSpec（`face` ＝該域註冊表鍵的封閉 enum）。

    `stage` 依 design 元件 2 矩陣：`{property_manager: M0, tenant: M0}`；
    **prospect 缺鍵＝永不可見**（售前不查 jgb2 個資）。

    `extra_properties`（W8 (3)）：某一域專屬的額外選填參數。**預設 `None` ⇒
    其餘五域逐位元不變**（回退面：這個參數拔掉即回到 W8 之前的 schema）。
    ⛔ `additionalProperties: False` 一律保留——多開的參數只能經這張表進來，
    ⛔ 不得改成開放物件讓呼叫端自由夾帶。
    """
    return {
        "name": f"jgb2.query.{domain}",
        "description": (
            f"查詢 {domain} 領域的決定性事實；face 決定回傳哪一組 facts，"
            "ref／keyword 只能在已確立的範圍內縮小。"
            + JGB2_DOMAIN_HINTS.get(domain, "")
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "face": {"type": "string", "enum": list(faces)},
                "ref": {"type": "string"},
                "keyword": {"type": "string"},
                **(extra_properties or {}),
            },
            "required": ["face"],
            "additionalProperties": False,
        },
        "scope": "read",
        "stage": {"property_manager": "M0", "tenant": "M0"},
    }


# ════════════════════════════════════════════════════════════════════
# W8 (2)：照片進場（`image_urls`）——抓檔／縮圖／辨識的**編排**住在門面
# ════════════════════════════════════════════════════════════════════
#: 抓檔＋縮圖＋辨識的**總**時間預算上限（秒）。實際預算見 `image_budget_s()`。
IMAGE_MAX_BUDGET_S = 15.0

#: 縮圖後的長邊上限（去 EXIF 是同一個 `downscale_image` 的副作用）。
IMAGE_MAX_PX = 1024

#: `/mcp` 路徑的 vision `detail`——**程式釘死**（S9-8：⛔ 不由 env，
#: 那會讓「一張照片要花多少錢」變成部署者可調的東西）。
IMAGE_DETAIL = "low"


def image_budget_s() -> float:
    """`min(IMAGE_MAX_BUDGET_S, agent_turn_timeout_s() / 2)`（S9-7）。

    上界是回合逾時的一半——照片吃掉的每一秒都是模型迴圈少掉的一秒，
    ⛔ 不讓照片把整個回合的預算吃光。
    """
    return min(IMAGE_MAX_BUDGET_S, agent_turn_timeout_s() / 2)


async def _image_fetch_one(url: str, *, timeout_s: float):
    """抓一張（六道閘全在 `image_fetch` 裡）。**測試的注入點就是這個模組屬性**。"""
    return await image_fetch.fetch_image(url, timeout_s=timeout_s)


def _image_validate_and_downscale(data: bytes, content_type: str) -> tuple:
    """`validate_format`（MIME＋magic bytes）→ `downscale_image`（≤1024px、去 EXIF）。

    ⚠️ 兩支都是**模組級／staticmethod**，⛔ 不需要 `S3ImageService` 實例
    （那支建構時缺 `S3_BUCKET_NAME` 會直接 `ValueError`，而這條路根本不上傳 S3；
    驗收 (xiii)）。格式不符 ⇒ `ValueError` ⇒ 呼叫端丟棄該張。
    """
    from services.s3_image_service import S3ImageService, downscale_image

    fmt = S3ImageService.validate_format(data, content_type)
    return downscale_image(data, IMAGE_MAX_PX), fmt


async def _image_recognize_batch(
    data_urls: list, *, category_names: Optional[list], categories_tree: Optional[list],
    db_pool, timeout_s: float,
) -> dict:
    """一批（≤5 張）送 vision。**測試的注入點就是這個模組屬性**。

    - `detail` 程式釘 `low`、`max_retries=1` 顯式（S9-7／S9-8）；
    - `max_images=None` ⇒ ⛔ 不套 REST 的 `[:3]` 截斷（S9-6）；
    - 模型名走 `IMAGE_RECOGNITION_MODEL`（gpt-5 系列的參數差異由
      `image_recognition_service._completion_params` 處理，S9-16）；
    - `db_pool` 有給 ⇒ 成本進 `openai_cost_tracking`（`operation='image_recognition'`，
      ⛔ 不進 `model_breakdown`＝額度看不到 vision 成本，S9-9 明列取捨）。
    """
    from services.image_recognition_service import ImageRecognitionService

    service = ImageRecognitionService(
        detail=IMAGE_DETAIL, timeout=max(1, int(timeout_s)), max_retries=1
    )
    return await service.analyze_images(
        data_urls, None, category_names, categories_tree, db_pool, None,
        max_images=None, detail=IMAGE_DETAIL,
    )


def _tree_names(tree: Optional[list]) -> list:
    """分類樹的**大類名稱**串（餵 `build_prompt(category_names=…)`）。"""
    names = []
    for node in tree or []:
        if isinstance(node, dict):
            name = str(node.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _resolve_tree_name(tree: Optional[list], name: Any) -> Optional[str]:
    """名稱在分類樹裡（大類或細項，**完全相同**）⇒ 回該名稱；否則 `None`。

    ⚠️ 判定沿用 `action._resolve_category` 的**同一支**（S9-12：卡上分類必須是
    封閉值域裡的名字）——⛔ 不在此另寫一套模糊比對：猜錯分類的代價是一張
    看起來完全正常、實際上分類錯誤的工單。
    """
    from services.agent.tools import action as action_tools

    if not isinstance(name, str) or not name.strip():
        return None
    cleaned = name.strip()
    return cleaned if action_tools._resolve_category(tree or [], cleaned) is not None else None


def _clamp_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.0
    if conf != conf:            # NaN
        return 0.0
    return max(0.0, min(1.0, conf))


#: 業主 2026-09-10 裁：**「照片裡的文字一律不進修繕單」（S9-11）撤銷**——辨識出的描述
#: （`description`）直接當修繕單問題描述（前綴「照片辨識：」由 runtime 加）；部位／原因短標籤
#: 為退路。描述經 `sanitize_data_piece`（單行、去不可見字元、去假標記）＋長度上限；
#: 短標籤只留中英字母、≤ `IMAGE_LABEL_MAX_CHARS` 字。修繕單描述是給師傅看的人讀文字，
#: ⛔ 不進模型資料段（模型看到的仍只有程式組的 facts）。
IMAGE_LABEL_MAX_CHARS = 12
IMAGE_DESCRIPTION_MAX_CHARS = 200


def _short_description(value: Any) -> Optional[str]:
    """vision 的描述 ⇒ 淨化＋截長；空 ⇒ None。"""
    from services.agent.completed_actions import sanitize_data_piece
    cleaned = sanitize_data_piece(value).strip()
    if not cleaned:
        return None
    return cleaned[:IMAGE_DESCRIPTION_MAX_CHARS]
_IMAGE_LABEL_KEEP_RE = re.compile(r"[^A-Za-z\u4e00-\u9fff]")


def _short_label(value: Any) -> Optional[str]:
    """vision 的短標籤 ⇒ 只留中英字母、上限 12 字；不合 ⇒ None（缺值）。"""
    if not isinstance(value, str):
        return None
    cleaned = _IMAGE_LABEL_KEEP_RE.sub("", value)
    if not cleaned or len(cleaned) > IMAGE_LABEL_MAX_CHARS:
        return None
    return cleaned


def _normalize_recognition(raw: Any, tree: Optional[list]) -> dict:
    """vision 回傳 ⇒ **決定性驗證後的封閉值**（S9-11／12／13）。

    `description` 經 `_short_description`（淨化＋≤200 字）收進 `ImageTurnInput.suggested_description`
    ——業主 2026-09-10 撤銷 S9-11「照片內文字不進修繕單」；它只用來組修繕單描述，
    ⛔ 不進模型資料段。`suggested_item`／`suggested_reason` 經 `_short_label` 才收。
    `suggested_emergency` 不在 `{1,2}` ⇒ 缺值（卡值由
    `confirm_card.emergency_status_of` 決定，缺值＝1，vision 的預設 2 ⛔ 不傳播）。
    """
    data = raw if isinstance(raw, dict) else {}
    category = _resolve_tree_name(tree, data.get("suggested_category"))
    others = []
    for name in data.get("secondary_damages") or []:
        resolved = _resolve_tree_name(tree, name)
        if resolved is not None:
            others.append(resolved)
    emergency = data.get("suggested_emergency")
    if isinstance(emergency, bool) or emergency not in (1, 2):
        emergency = None
    return {
        "damage_visible": bool(data.get("is_damage")),
        "confidence": _clamp_confidence(data.get("confidence")),
        "category": category,
        "others": others,
        "emergency": emergency,
        "item": _short_label(data.get("suggested_item")),
        "reason": _short_label(data.get("suggested_reason")),
        "description": _short_description(data.get("description")),
    }


def _image_facts(
    *, processed: int, total: int, damage_visible: bool, category: Optional[str],
) -> str:
    """影像事實＝**程式組的句子**（⛔ 無任何模型自由文字）。

    每一句都要是完整句（`provenance_units` 依句末標點切片；切不出片段的字串
    等於一段不可引用的資料）。
    """
    lines = [f"使用者本回合傳了 {total} 張照片，系統已辨識其中 {processed} 張。"]
    if not damage_visible:
        lines.append("照片看不出損壞。")
    elif category:
        lines.append(f"照片辨識到的修繕分類是「{category}」。")
    else:
        lines.append("照片辨識不出對應的修繕分類。")
    # ⛔ 照片的文字描述**不提供**（S9-11）：明講一句，模型才不會自己編一段。
    lines.append("照片的文字描述不提供，需要問題描述請向使用者確認。")
    return "\n".join(lines)


async def prepare_image_turn(
    image_urls: list,
    *,
    category_tree: Optional[list],
    db_pool=None,
    budget_s: Optional[float] = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple:
    """抓檔 → 縮圖 → 分批辨識 ⇒ `(ImageTurnInput, 已耗秒數)`。

    **順序與預算（Plan W8 (2)／S9-7／S9-21）**：
      逐張抓檔→縮圖→**丟原 bytes**（任一時刻記憶體只有一張原檔＋已縮圖集）；
      滿 5 張送一批辨識；抓完後把不足 5 張的尾批送出。
      每次抓檔前、每次送辨識前各檢查一次預算——**預算一到就停**，
      ⛔ 不送半批（那會讓「0 批完成 ⇒ timeout」這條唯一映射失效）。

    **預算用罄的唯一映射（r3）**：已完成辨識批次 ≥1 ⇒ `partial`；0 批 ⇒ `timeout`。
    一張都沒處理成功、且預算沒用完（全被閘門擋掉／全部辨識失敗）⇒ `failed`。

    ⛔ bytes 不落地、不進任何紀錄；本函式只回封閉值。
    """
    from services.agent.runtime import IMAGE_CANDIDATE_MAX, IMAGE_CONFIDENCE_MIN, ImageTurnInput

    started = clock()
    budget = image_budget_s() if budget_s is None else budget_s
    total = len(image_urls)
    names = _tree_names(category_tree)

    def _elapsed() -> float:
        return clock() - started

    pending: list = []          # 已縮圖的 base64 data URL（⛔ 不留原檔 bytes）
    batches_done = 0
    processed = 0
    failed = False
    merged: list = []
    exhausted = False

    async def _flush() -> None:
        nonlocal batches_done, processed, failed, pending
        batch, pending = pending, []
        if not batch:
            return
        try:
            raw = await _image_recognize_batch(
                batch, category_names=names, categories_tree=category_tree,
                db_pool=db_pool, timeout_s=max(1.0, budget - _elapsed()),
            )
        except Exception:
            # ⛔ 例外物件不外流（訊息可能含 base64）；失敗一律可見：健檢＋violation。
            image_fetch.record_image_failure()
            failed = True
            return
        batches_done += 1
        processed += len(batch)
        merged.append(_normalize_recognition(raw, category_tree))

    for url in image_urls:
        if _elapsed() >= budget:
            exhausted = True
            break
        try:
            fetched = await _image_fetch_one(url, timeout_s=max(1.0, budget - _elapsed()))
            downscaled, fmt = _image_validate_and_downscale(fetched.data, fetched.content_type)
        except image_fetch.ImageFetchError:
            continue            # 閘門擋下／抓不到 ⇒ **丟棄該張**，回合照跑
        except Exception:
            continue            # 格式不符（`validate_format` 的 ValueError）等
        pending.append(
            "data:image/" + fmt + ";base64," + base64.b64encode(downscaled).decode("ascii")
        )
        del downscaled
        if len(pending) >= image_fetch.IMAGE_BATCH_SIZE:
            if _elapsed() >= budget:
                exhausted = True
                pending = []            # ⛔ 不送半批
                break
            await _flush()
            if failed:
                break
    if pending and not failed and not exhausted:
        if _elapsed() >= budget:
            exhausted = True
            pending = []
        else:
            await _flush()

    elapsed = _elapsed()
    if failed:
        return (
            ImageTurnInput(status="failed", processed=processed, total=total),
            elapsed,
        )
    if processed == 0:
        # 預算用完 ⇒ `timeout`；否則（全被閘門擋掉）⇒ `failed`，兩者都有固定句與
        # violation，⛔ 沒有「安靜地當作沒帶照片」這個選項。
        status = "timeout" if (exhausted or elapsed >= budget) else "failed"
        if status == "failed":
            image_fetch.record_image_failure()
        return ImageTurnInput(status=status, processed=0, total=total), elapsed

    # ── 多批合併：分類取信心最高者、`damage_visible` 任一為真即真、候選去重 ──
    best = max(merged, key=lambda m: m["confidence"])
    damage_visible = any(m["damage_visible"] for m in merged)
    confidence = best["confidence"]
    category = best["category"]
    emergency = best["emergency"]
    pool: list = []
    for m in merged:
        for name in ([m["category"]] if m["category"] else []) + m["others"]:
            if name not in pool:
                pool.append(name)
    candidates: tuple = ()
    if damage_visible and confidence < IMAGE_CONFIDENCE_MIN and len(pool) >= 2:
        candidates = tuple(pool[:IMAGE_CANDIDATE_MAX])
    status = "ok" if processed >= total else "partial"
    return (
        ImageTurnInput(
            status=status,
            facts=_image_facts(
                processed=processed, total=total,
                damage_visible=damage_visible, category=category,
            ),
            processed=processed,
            total=total,
            candidates=candidates,
            suggested_category=category,
            suggested_emergency=emergency,
            suggested_item=best.get("item"),
            suggested_reason=best.get("reason"),
            suggested_description=best.get("description"),
        ),
        elapsed,
    )


# ════════════════════════════════════════════════════════════════════
# W9 U1：文件進場（`attachment_purpose="document"` ＋ `file_urls`）
# ════════════════════════════════════════════════════════════════════
#: `attachment_purpose` 的封閉值域與預設值（**唯一定義來源**——`AGENT_TURN_SPEC`
#: 的 `enum` 由這裡導出，⛔ 不在兩處各抄一份）。缺鍵／顯式 `null` ⇒ `repair`
#: ＝現行行為逐位不變。
ATTACHMENT_PURPOSES: tuple = ("repair", "document")
DEFAULT_ATTACHMENT_PURPOSE = "repair"

#: 文件回合單頁渲染的時限上界（實際值再取「剩餘預算」的較小者）。
#: ⛔ 不由 env——它是 DoS 防線的一部分，不是效能旋鈕。
DOCUMENT_PAGE_TIMEOUT_S = 8.0


async def _document_fetch_one(url: str, *, timeout_s: float):
    """抓一份文件——**同一支 `fetch_image`、只換 bytes 上限**（W9-5）。

    ⛔ 不得改成另一支抓檔函式：六道閘（https／等值白名單／userinfo／IP／`exp`／
    不跟轉址／串流 bytes）全在那一支裡，第二支必定漏掉其中一道。
    **測試的注入點就是這個模組屬性**（同 `_image_fetch_one`）。
    """
    return await image_fetch.fetch_image(
        url, timeout_s=timeout_s, max_bytes=image_fetch.file_max_bytes()
    )


async def _document_extract_pages(data_urls: list, *, timeout_s: float) -> tuple:
    """一次擷取（≤`DOC_TOTAL_PAGES_MAX` 頁）⇒ `(驗過的 dict, usage, 模型名)`。

    **測試的注入點就是這個模組屬性**（同 `_image_recognize_batch`）。
    ⛔ **不收 `db_pool`**：成本由 `prepare_document_turn` 依回傳的 usage 自寫
    （W9-9：⛔ 不呼叫 `ImageRecognitionService._record_cost`，那支在 `image_id`
    非空時會把整包 JSON 寫進 `image_uploads.recognition_result`）。收一個用不到
    的 `db_pool` 會讓下一個讀這段的人以為成本已經在這裡記過了。
    """
    from services.agent.document_extract import DocumentExtractionService

    service = DocumentExtractionService(timeout_s=timeout_s, max_retries=1)
    result = await service.extract(data_urls, timeout_s=timeout_s, max_retries=1)
    return result, service.last_usage, service.model


async def _record_document_cost(db_pool, model: str, usage: Optional[dict]) -> None:
    """文件線**自寫**一列 `openai_cost_tracking`（W9-9）。

    ⛔⛔ **不碰 `image_uploads`**：`ImageRecognitionService._record_cost` 在
    `image_id` 非空時會 `UPDATE image_uploads SET recognition_result = <整包 JSON>`
    ——文件線的擷取結果 ⛔ 不得落地。這條路的 `image_id` 恆等於「沒有」，
    所以這裡**根本沒有那一段 SQL**（驗收：文件回合後 `image_uploads` 零新列／
    零 UPDATE，以假 pool 斷言呼叫面）。

    寫檔失敗只 warning，⛔ 不阻塞回合（同 `_record_cost` 的既有處置）。
    """
    if db_pool is None or not isinstance(usage, dict):
        return
    from services.usage_metering import DEFAULT_PRICING

    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    price = DEFAULT_PRICING.get(model)
    if price is None:
        # 價目表沒有這個模型 ⇒ 沿用舊的平頭費率（同 `_estimate_cost` 的退路）。
        cost_usd = ((prompt_tokens + completion_tokens) / 1_000_000) * 5.0
    else:
        cost_usd = (prompt_tokens / 1_000_000) * price[0] + (
            completion_tokens / 1_000_000
        ) * price[1]
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO openai_cost_tracking
                    (operation, model, prompt_tokens, completion_tokens, cost_usd)
                VALUES ($1, $2, $3, $4, $5)
                """,
                "document_extraction", model,
                prompt_tokens, completion_tokens, cost_usd,
            )
    except Exception as exc:      # noqa: BLE001 — ⛔ 只印例外類別名
        logger.warning("文件成本記錄寫入失敗：%s", type(exc).__name__)


async def prepare_document_turn(
    image_urls: list,
    file_urls: list,
    *,
    db_pool=None,
    budget_s: Optional[float] = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple:
    """抓檔 →（PDF ⇒ 頁圖）→ 擷取 ⇒ `(DocumentTurnInput, 已耗秒數)`。

    **形狀比照 `prepare_image_turn`**（Plan §3b 介面凍結），差別只有三處：
      ① PDF 多一段 `rasterize_pdf`（頁級／總時限、逐頁像素上限、只 render）；
      ② 照片頁＋PDF 頁**合計** > `DOC_TOTAL_PAGES_MAX` ⇒ `DocumentPageLimitExceeded`
         ⇒ 門面轉成整回合 `INVALID_INPUT`（W9-15；⛔ 不截斷後照跑）。
         ⚠️ 判斷點在**抓完 PDF、知道頁數之後**——2 頁的 PDF 配 8 張照片是合法的，
         早退用 `len(file_urls) × DOC_MAX_PAGES` 預估會誤殺它（那個最壞值只用在
         配額預扣，不用在拒絕）。
      ③ 成本自寫 `operation='document_extraction'`（W9-9）。

    **預算用罄的映射與照片線同一條**（⛔ 不另立第二套語義）：已完成擷取 ≥1 批
    ⇒ `partial`／`ok`；0 批 ⇒ 預算用完＝`timeout`、否則＝`failed`。

    ⛔ bytes 與擷取 JSON 不落地、不進任何紀錄；本函式只回封閉值。
    """
    from services.agent.document_extract import (
        DocumentPageLimitExceeded,
        DocumentTurnInput,
        build_document_facts,
        rasterize_pdf,
    )

    started = clock()
    budget = image_budget_s() if budget_s is None else budget_s

    def _elapsed() -> float:
        return clock() - started

    pages: list = []            # 已縮圖／已渲染的 base64 data URL（⛔ 不留原 bytes）
    photo_requested = len(image_urls or [])
    pdf_pages_total = 0
    pdf_pages_kept = 0
    pdf_timed_out = False
    exhausted = False

    # ── ① 照片頁：與報修線**同一支**縮圖／格式檢查（含 `Image.MAX_IMAGE_PIXELS`）──
    for url in image_urls or []:
        if _elapsed() >= budget:
            exhausted = True
            break
        try:
            fetched = await _image_fetch_one(url, timeout_s=max(1.0, budget - _elapsed()))
            downscaled, fmt = _image_validate_and_downscale(fetched.data, fetched.content_type)
        except image_fetch.ImageFetchError:
            continue            # 閘門擋下／抓不到 ⇒ **丟棄該張**，回合照跑
        except Exception:
            continue            # 格式不符／解壓縮炸彈（`DecompressionBombError`）等
        pages.append(
            "data:image/" + fmt + ";base64," + base64.b64encode(downscaled).decode("ascii")
        )
        del downscaled

    # ── ② PDF 頁：抓檔 → 雙檢 → rasterize ──
    for url in file_urls or []:
        if _elapsed() >= budget:
            exhausted = True
            break
        try:
            fetched = await _document_fetch_one(url, timeout_s=max(1.0, budget - _elapsed()))
            image_fetch.validate_pdf_bytes(fetched.data, fetched.content_type)
        except image_fetch.ImageFetchError:
            continue            # 閘門擋下／非 PDF ⇒ **丟棄該份**
        except Exception:
            continue
        try:
            rasterized = await rasterize_pdf(
                fetched.data,
                max_pages=image_fetch.doc_max_pages(),
                max_px=IMAGE_MAX_PX,
                page_timeout_s=min(DOCUMENT_PAGE_TIMEOUT_S, max(1.0, budget - _elapsed())),
                total_timeout_s=max(1.0, budget - _elapsed()),
            )
        except Exception:       # `DocumentRasterizeError` 等 ⇒ 丟棄該份
            continue
        del fetched
        pdf_pages_total += rasterized.pages_total
        pdf_timed_out = pdf_timed_out or rasterized.timed_out
        # W9-15：合計判在**知道頁數之後**。用「請求的照片張數」而不是「成功縮圖的
        # 張數」——被閘門擋掉的那幾張仍然是使用者這回合送進來的頁，用實際成功數
        # 會讓「多送幾張壞圖」變成繞過總頁數上限的方法（fail-closed 方向）。
        kept = min(rasterized.pages_total, image_fetch.doc_max_pages())
        if photo_requested + pdf_pages_kept + kept > image_fetch.doc_total_pages_max():
            raise DocumentPageLimitExceeded()
        pdf_pages_kept += kept
        for png in rasterized.pages:
            pages.append(
                "data:image/png;base64," + base64.b64encode(png).decode("ascii")
            )
        del rasterized

    pages_total = photo_requested + pdf_pages_total
    if not pages:
        elapsed = _elapsed()
        # PDF 的頁級／總時限命中而一頁都沒渲染出來 ⇒ 那是**逾時**，⛔ 不是
        # 「這份檔壞掉」——把逾時講成失敗會讓使用者以為換一份檔就好。
        status = (
            "timeout" if (exhausted or pdf_timed_out or elapsed >= budget) else "failed"
        )
        if status == "failed":
            image_fetch.record_image_failure()
        return (
            DocumentTurnInput(status=status, pages_seen=0, pages_total=pages_total),
            elapsed,
        )
    if _elapsed() >= budget:
        # 頁圖備妥但預算已盡 ⇒ 0 批完成＝`timeout`（⛔ 不送半批，同照片線）。
        return (
            DocumentTurnInput(status="timeout", pages_seen=0, pages_total=pages_total),
            _elapsed(),
        )

    # ── ③ 擷取 ──
    try:
        result, usage, model = await _document_extract_pages(
            pages, timeout_s=max(1.0, budget - _elapsed()),
        )
    except Exception:
        # ⛔ 例外物件不外流（訊息可能含 base64）；失敗一律可見：健檢＋violation。
        image_fetch.record_image_failure()
        return (
            DocumentTurnInput(
                status="failed", pages_seen=len(pages), pages_total=pages_total
            ),
            _elapsed(),
        )
    await _record_document_cost(db_pool, model, usage)

    facts = build_document_facts(result)
    pages_seen = len(pages)
    status = "ok" if (pages_seen >= pages_total and not pdf_timed_out) else "partial"
    return (
        DocumentTurnInput(
            status=status,
            kind=result.get("kind"),
            facts=facts,
            pages_seen=pages_seen,
            pages_total=pages_total,
        ),
        _elapsed(),
    )


# ════════════════════════════════════════════════════════════════════
# `agent.turn`：整回合工具（任務 2.6｜design 元件 4「agent.turn 工具」段、決策 15、R3.7）
# ════════════════════════════════════════════════════════════════════
class TurnOutcome(BaseModel):
    """DSP-043：機器可讀的回合結果（第七鍵 `outcome`；值域封閉、由 Runtime 程式設）。

    `state` 八值／`expects` **六值**（第六批 #4 加 `image`／`file`）／`ref.type`
    三值與 `runtime.OUTCOME_*` 同源；
    呼叫端（LINE 聊天、LIFF、之後的網頁）只看這個物件決定畫面，⛔ 不解析 `answer` 字串。
    """

    state: str
    expects: str
    action: Optional[str] = None
    ref: Optional[dict] = None


def _outcome_of(result: Any) -> dict:
    """`TurnResult.outcome`；未設（舊 fake runtime）⇒ 依 kind／quick_replies 導出。"""
    out = getattr(result, "outcome", None)
    if isinstance(out, dict) and out.get("state"):
        return out
    from services.agent.runtime import default_outcome   # 延遲載入：避免循環 import
    return default_outcome(result)


class AgentTurnOutput(BaseModel):
    """`agent.turn` 的回傳形狀（R3.7：五鍵固定＋依落地順序加的選填鍵）。

    ⛔ **不含 `citations`**：引用是 Verifier 的內部證據，對呼叫端沒有用途，
    卻會把「我們從哪一列知識取的哪一段字」外送。
    ⛔ **不含被拒文字**：Verifier 拒兩次時 `answer` 是固定句，被拒的草稿只留在
    Runtime 的 `messages`（模型自己的重寫上下文），⛔ 不進 `TurnResult`、
    自然也不會流到這裡（見 `runtime.py` 的 VERIFIER_REJECT 分支註解）。
    """

    answer: str
    kind: str
    handoff: Optional[dict] = None
    quick_replies: list = []
    trace_id: str
    #: W8 (5)／DSP-042：**第六鍵**（選填，預設 false）。只有「同一個
    #: `session_id` 隔超過 `SESSION_IDLE_TTL_S` 才再進來」的**那一回合**為 true
    #: ——它是給呼叫端（LIFF／line-bot）用來知道「上一段對話已經收掉了」，
    #: ⛔ 不是錯誤、⛔ 不改變 `answer`／`kind` 的語義。
    #: 鍵序＝落地順序（§0b）：W7 的 `transcript` 之後才會排到第七鍵。
    session_expired: bool = False
    #: DSP-043（2026-09-08）：**第七鍵** `outcome`（永遠有值；見 `TurnOutcome`）。
    outcome: TurnOutcome = TurnOutcome(state="answered", expects="text")


AGENT_TURN_SPEC: ToolSpec = {
    "name": AGENT_TURN_NAME,
    "description": (
        "把一句使用者訊息交給客服 agent 跑完一整個回合，回傳最終答覆。"
        "對話歷史由服務端依 session 保存，呼叫端只要每回合帶同一個 session_id。"
    ),
    "input_schema": {
        "type": "object",
        # ⛔ **只有 `message`**（2.6 前置 security review P2／處置②）：
        #    原 design 的 `dialog_ref` 查無任何實作、也沒有語義，留著只會變成
        #    「呼叫端可以指定要接哪一段歷史」的洞。歷史一律由服務端依
        #    `X-JGB-Identity.session_id` 取（見 `NamespacedStateStore`）。
        # W8 (2)：`minLength` 由 1 改 **0**（仍 required）——**純照片回合**
        # （只傳照片、不打字）是 LIFF 線的常態；早退改判「`message.strip()` 空
        # **且** `image_urls` 空 ⇒ `INVALID_INPUT`」，見 `_agent_turn`。
        # ⛔ `image_urls` **不寫 `maxItems`／`pattern`**：`registry._validate_value`
        #    兩者都不認（S9-5：寫了等於掛一張看起來有守、實際靜默無效的牌）。
        #    張數在 `_agent_turn` 程式層檢查；白名單在 `image_fetch`。
        # T1（Plan `inputs/…/plan-walkthrough-fixes-batch2-20260909.md` §2）：
        # `context` ＝呼叫端提供的**本回合背景資訊**（進場提示、頁面、已選項目、上一步結果；選填、每回合可帶）。2026-09-09 業主：欄位要通用的「背景資訊」，不是「進場句」。
        # ⛔ **不叫 `entry`**（security r1 #4）：`Identity.entry` 是確認兌現與工具
        #    可見性的安全欄位，同名招致日後誤併。
        # ⚠️ `maxLength` 由 `registry._validate_value` **真的**強制（不同於
        #    `image_urls` 的 `maxItems`／`pattern`，那兩個 registry 不認）。
        "properties": {
            "message": {"type": "string", "minLength": 0, "maxLength": 2000},
            "image_urls": {
                "type": "array",
                "items": {"type": "string", "maxLength": 2048},
            },
            "context": {
                "type": "string",
                "maxLength": 500,
                "description": "呼叫端提供的本回合背景資訊（進場提示、所在頁面、已選項目、上一步結果等）；視為脈絡，⛔ 不是使用者說的話，每回合可帶。",
            },
            # W9 U1（Plan `inputs/…/plan-document-summary-demo-20260909.md` §3）：
            # `attachment_purpose` ＝這一回合的附件是**做什麼用的**（封閉列舉）。
            # ⚠️ 缺鍵／顯式 `null` 一律等同 `repair`＝**現行行為逐位不變**
            #    （`_drop_null_optionals` 會把非 required 的 null 還原成「省略」）
            #    ——這個預設值本身就是本功能的開關（Plan §3b rollback 欄）。
            # ⚠️ `enum` 由 `registry._validate_value` **真的**強制（不同於
            #    `image_urls`／`file_urls` 的 `maxItems`，那個 registry 不認）。
            "attachment_purpose": {
                "type": "string",
                "enum": list(ATTACHMENT_PURPOSES),
                "description": "本回合附件的用途：repair＝報修照片（預設）；document＝上傳文件請 AI 歸納。缺值等同 repair。",
            },
            # ⛔ **不寫 `maxItems`**（S9-5／W9-18）：`registry._validate_value` 不認它
            #    ——寫了等於掛一張看起來有守、實際靜默無效的牌。份數（≤1）在
            #    `_agent_turn` 程式層檢查；白名單／bytes／`exp` 在 `image_fetch`。
            "file_urls": {
                "type": "array",
                "items": {"type": "string", "maxLength": 2048},
                "description": "本回合上傳的文件網址（relay 網域、application/pdf、必帶 exp）；只在 attachment_purpose=document 時可帶。",
            },
        },
        "required": ["message"],
        "additionalProperties": False,
    },
    "output_model": AgentTurnOutput,
    # 回合本身不改任何外部系統（寫入要另外走 confirm token）⇒ read。
    "scope": "read",
    # ⛔ 但它**會寫 session 狀態**（`form_sessions.collected_data`）⇒ 影子
    #    （`readonly_view=True`）一律不可見，否則影子回合會污染正式對話。
    "mutates_session": True,
    # 門面專屬：⛔ 不進模型工具清單（`for_model=True` 不可見 ⇒ 模型捏造這個名字
    # 只會拿到 NO_MATCH，沒有自呼遞迴）、⛔ 不進影子視圖。
    "facade_only": True,
    # 本 spec 的對話對象＝有 git 正本的兩個受眾（範圍聲明）；**tenant 缺鍵＝永不可見**
    # （它沒有正本，⛔ 不得順手補鍵）。
    # DSP-037（業主 2026-09-07 裁）：`property_manager` 於 M1 開放——pm 正本
    # （`canon/property_manager.md`，36 細目全 reviewed）已上線，門面依受眾取
    # `app.state.agent_outlines[audience]`，取不到一律 `AGENT_UNAVAILABLE`，
    # ⛔ 不塞 prospect 大綱（見 `_make_agent_turn`／`_agent_turn_preflight`）。
    "stage": {"prospect": "M1", "property_manager": "M1"},
}


def _app_state(deps: FacadeDeps, name: str) -> Any:
    """讀 `app.state.<name>`；沒有 `get_app`／沒有該屬性一律 `None`（fail-closed）。"""
    if deps.get_app is None:
        return None
    app = deps.get_app()
    state = getattr(app, "state", None)
    return getattr(state, name, None) if state is not None else None


#: `_outline_for_audience` 的第三種回答：「這個受眾沒有大綱」——與「這台機器根本
#: 沒接大綱」（回 `None`，維持 3.2 以來的既有行為：不塞、照跑）區分開。
_OUTLINE_UNAVAILABLE = object()


def _outline_for_audience(deps: FacadeDeps, audience: str) -> Any:
    """該受眾的行程級大綱（DSP-037／S1b）。

    - `app.state.agent_outlines`（複數）是**權威對照表**：非空 ⇒ 查無該受眾一律
      `_OUTLINE_UNAVAILABLE`（fail-closed，⛔ 不回退到 prospect）。
    - 沒有複數對照表（3.2～S1b 前的舊形狀、以及只塞單數的測試替身）⇒ 只有
      prospect 讀得到 `app.state.agent_outline`；其餘受眾一律 `_OUTLINE_UNAVAILABLE`
      ——⚠️ 這正是 S1b 修掉的洞：舊碼對**任何**受眾都塞那份售前大綱。
    """
    outlines = _app_state(deps, "agent_outlines")
    if isinstance(outlines, dict) and outlines:
        doc = outlines.get(audience)
        return doc if doc is not None else _OUTLINE_UNAVAILABLE
    if audience == "prospect":
        return _app_state(deps, "agent_outline")
    return _OUTLINE_UNAVAILABLE


def _open_state_store(deps: FacadeDeps, identity: Identity) -> NamespacedStateStore:
    """建 `NamespacedStateStore` 並**當場驗一次鍵**（超長／缺 id ⇒ `ValueError`）。

    `_invoke` 的 preflight 與 `_agent_turn` 各呼叫一次：前者是為了把失敗轉成
    正確的錯誤碼（registry 內拋例外一律被吞成 `NO_MATCH`），後者才是真的用它。
    兩次都是純運算、無 I/O，⛔ 不值得為此在 `ToolFn` 簽名上開洞傳物件。
    """
    engine = _app_state(deps, "agent_session_store")
    store = NamespacedStateStore(engine, identity.api_key_id, identity.vendor_id)
    store.key(identity.session_id)  # 形狀／長度先驗
    return store


def namespaced_identity(identity: Identity) -> Identity:
    """把 `/mcp` 身分的**裸 `session_id`** 換成命名空間鍵後的身分（任務 2.9）。

    ⚠️ **為什麼工具也要換身分，而不是只有 `agent.turn` 的狀態鍵要換**：
    2.6 只把 `agent.turn` 自己讀寫的 `form_sessions` 列搬進命名空間
    （`services/agent/state_store.py`），但 2.4 的三個工具是**各自**用
    `identity.session_id` 去找列的——
      - `session.slots.get/set` → `form_sessions.session_id = $1`
      - `confirm.request`／`redeem_token` → `agent_confirmation_tokens.session_id`
    這些 SQL **都沒有 vendor 條件**（正對照：`state_store.py` 模組 docstring 引的
    security review 原句就是在講同一組 SQL）。所以只要工具拿到的是裸
    `session_id`，持另一把 key／另一個 vendor 的呼叫端只要帶同一個
    `session_id`，就能讀他人的槽位、兌現他人的確認 token——**2.6 剛從正門擋掉的
    P1 會從這扇側門原封不動地走回來**。故：交給工具的身分一律換成命名空間身分。

    ⛔ **fail-closed**：`api_key_id`／`vendor_id` 缺、或鍵超過
    `form_sessions.session_id` 的 100 字 ⇒ `ValueError`（由呼叫端轉成
    `INVALID_INPUT`）。⛔ 不得「退回裸 session_id」——那正是被擋掉的那條路。

    ⚠️ REST 路徑（`routers/agent_entry.py`）**不呼叫本函式**：那條路的
    `session_id` 由 jgb2 上游 scope 過，且與舊鏈共用同一列
    （`form_sessions` 的 `config_key='agent:<audience>'`），加前綴會讓 REST 與
    舊鏈天然分池、續對話直接斷掉。兩條路徑的分池由「MCP 加前綴、REST 不加」
    達成，⛔ 不要為了「一致」而把 REST 也加上去。
    """
    store = NamespacedStateStore(None, identity.api_key_id, identity.vendor_id)
    return dataclass_replace(identity, session_id=store.key(identity.session_id))


def _make_agent_turn(
    deps: FacadeDeps, repair_category_tree: Optional[Callable] = None
) -> Callable:
    """`agent.turn` 的 `ToolFn`：載入命名空間狀態 →（照片）→ `run_turn` → 存回。

    ⛔ **不另寫第二條回合邏輯**（R3.7）：Verifier、固定句、預算、計量全都在
    `AgentRuntime.run_turn` 裡，這裡只負責狀態的載入與存回。

    `repair_category_tree`（W8 (2)）：`build_registry` 注入的閉包（形狀同
    `open_repairs`），回修繕分類樹或 `None`。⛔ 影像段不得直呼 `JGBSystemAPI`；
    沒注入／取不到 ⇒ 分類一律缺值（卡上 `UNSPECIFIED_CATEGORY_ZH`）、不回候選。
    """

    async def _agent_turn(identity: Identity, args: dict) -> ToolResult:
        message = args.get("message")
        # ── W8 (2)：照片進場的三道程式層檢查（schema 管不到的那三件事）──
        image_urls = args.get("image_urls")
        if image_urls is None:
            image_urls = []
        if not isinstance(image_urls, list) or not all(
            isinstance(u, str) for u in image_urls
        ):
            return ToolResult(ok=False, error="INVALID_INPUT")
        # ① 張數上限 10（第 11 張起整回合拒；registry 不認 `maxItems`，S9-5）。
        #    ⛔ 不截斷後照跑——那是靜默降級。
        if len(image_urls) > image_fetch.IMAGE_MAX_COUNT:
            return ToolResult(ok=False, error="INVALID_INPUT")

        # ── W9 U1：文件進場的三道程式層檢查（順序固定，⛔ 全部排在抓檔之前）──
        purpose = args.get("attachment_purpose")
        if purpose is None:
            purpose = DEFAULT_ATTACHMENT_PURPOSE
        if purpose not in ATTACHMENT_PURPOSES:
            # registry 的 `enum` 已經擋過（`_validate_value` 真的認 enum）；走到
            # 這裡代表有人繞過門面直呼 `registry.call()` 之外的路 ⇒ 第二道網。
            return ToolResult(ok=False, error="INVALID_INPUT")
        file_urls = args.get("file_urls")
        if file_urls is None:
            file_urls = []
        if not isinstance(file_urls, list) or not all(
            isinstance(u, str) for u in file_urls
        ):
            return ToolResult(ok=False, error="INVALID_INPUT")
        # ⓐ 修繕線 ⛔ 不收 PDF——`repair` 帶 `file_urls` 是呼叫端搞錯了用途，
        #    靜默忽略等於讓使用者以為文件送出去了。
        if purpose != "document" and file_urls:
            return ToolResult(ok=False, error="INVALID_INPUT")
        # ⓑ 份數上限（demo ≤1；registry 不認 `maxItems`，S9-5／W9-18）。
        #    ⛔ 不截斷後照跑——那是靜默降級。
        if len(file_urls) > image_fetch.FILE_MAX_COUNT:
            return ToolResult(ok=False, error="INVALID_INPUT")
        # ② 早退：三者皆空才 `INVALID_INPUT`（純照片／純文件回合都合法）。
        if not isinstance(message, str) or (
            not message.strip() and not image_urls and not file_urls
        ):
            return ToolResult(ok=False, error="INVALID_INPUT")

        runtime = _app_state(deps, "agent_runtime")
        if runtime is None:
            # `_invoke` 的 preflight 已經擋過（回 AGENT_UNAVAILABLE）；走到這裡
            # 代表有人繞過門面直接呼 `registry.call()` ⇒ 用封閉錯誤值域裡的
            # `NO_MATCH`，⛔ 不在對模型可見的值域上多開一個碼。
            return ToolResult(ok=False, error="NO_MATCH")
        # 大綱是**行程級共用物件**（`app.state.agent_outlines[audience]`），**依受眾取**
        # （DSP-037／S1b）：取不到一律 fail-closed，⛔ 不塞別的受眾（尤其 prospect）
        # 的大綱——那等於把售前正本餵給 pm 回合。
        # ⚠️ 這一關刻意排在 `store.load`／`store.start` **之前**：判不通過的回合
        # ⛔ 不該先在 `form_sessions` 留下一列半開的 session。
        # 錯誤碼用 `NO_MATCH`：`ToolError` 是封閉值域，`AGENT_UNAVAILABLE` 不在其中，
        # 且 ⛔ 不在對模型可見的值域上多開一個碼（同上方 runtime 缺席的處置）。
        # 呼叫端看到的 `AGENT_UNAVAILABLE` 由 `_agent_turn_preflight` 給——
        # 這裡是繞過門面直呼 `registry.call()` 時的第二道網。
        outline = _outline_for_audience(deps, identity.resolved_audience())
        if outline is _OUTLINE_UNAVAILABLE:
            return ToolResult(ok=False, error="NO_MATCH")

        # ③ 張數配額（`LIMITS.images_per_hour`／`LIMITS.files_per_hour`——DSP-045
        #    封閉表，⛔ 不再是 `IMAGE_COUNT_CAP_PER_HOUR` env——／`(api_key_id, vendor_id)`／
        #    行程內滑動窗）——**排在抓檔之前**：超過 ⇒ `RATE_LIMITED`、一張都不抓。
        #    W9-6：文件回合以**最壞值預扣**——一份 PDF 最多會變成 `DOC_MAX_PAGES`
        #    張頁圖，配額必須按那個最壞值先扣，⛔ 不能等抓完才知道扣多少
        #    （那時候檔已經下載完了，配額擋不到下載這件事本身）。
        quota_key = (identity.api_key_id, identity.vendor_id)
        page_charge = len(image_urls) + (
            len(file_urls) * image_fetch.doc_max_pages()
            if purpose == "document" else 0
        )
        if page_charge and not image_fetch.check_and_record_image_count(
            quota_key, page_charge
        ):
            return ToolResult(ok=False, error="RATE_LIMITED")
        if file_urls and not image_fetch.check_and_record_file_count(
            quota_key, len(file_urls)
        ):
            return ToolResult(ok=False, error="RATE_LIMITED")

        try:
            store = _open_state_store(deps, identity)
            # Runtime 收到的身分**就是命名空間身分**（任務 2.9）：回合內模型呼叫
            # `session.slots.*`／`confirm.request` 時，工具拿到的 `session_id`
            # 才會是這一列的鍵，而不是呼叫端給的裸值。⛔ 不把裸身分傳進 run_turn。
            turn_identity = namespaced_identity(identity)
        except ValueError:
            return ToolResult(ok=False, error="INVALID_INPUT")

        # ⚠️ `store` 自己會加前綴（`NamespacedStateStore.key`），所以這裡餵給它的
        #    必須是**裸** `session_id`——⛔ 別改成 `turn_identity.session_id`，
        #    那會變成 `mcp:k:v:mcp:k:v:sid`（雙前綴，且超長時直接 ValueError）。
        session_id = identity.session_id
        state = await store.load(session_id)
        # W8 (5)／DSP-042：同一把鍵隔太久再進 ⇒ **先把舊列關掉再開新列**。
        # ⚠️ 順序不得顛倒（S8-7）：先 `_start` 再 `_close` 會把剛開的新列一起
        # 關掉（`_close` 的 WHERE 只認 `session_id`＋`state='COLLECTING'`，
        # 認不得是哪一列）；不 `_close` 就 `_start` 則會留下兩列 COLLECTING，
        # 而 `get_state` 取 `ORDER BY id DESC LIMIT 1`＝舊列變成永遠讀不到卻
        # 還開著的殘列。
        # 舊列一關，掛在它 `collected_data` 上的 `pending_confirm` 也隨之作廢
        # （下一回合讀到的是新列的空狀態），⛔ 不另外清 token 表——那些 token
        # 本來就會過期，且 `redeem_pending` 找不到對應的 pending 就回固定句。
        session_expired = False
        if state is not None and _session_is_expired(state):
            await store.close(session_id)
            state = None
            session_expired = True
        if state is None:
            state = await store.start(
                session_id,
                identity.user_id or "anonymous",
                identity.vendor_id,
                identity.role_id,
            )

        agent_state = state.setdefault("agent", {})
        # Runtime 從 `state["agent"]["outline"]` 取，故這裡進場前塞、存檔前 pop——
        # ⛔ 不得讓它被序列化進 `form_sessions.collected_data`（每個 session 存一份
        # 幾千字的大綱，而且會就此凍結在舊版本）。與 `routers/agent_entry.py`
        # 的 REST 路徑同一個處置。
        if outline is not None:
            agent_state["outline"] = outline

        # ── W8 (2)：照片（抓檔→縮圖→辨識）在**進 run_turn 之前**跑完 ──
        # 交給 Runtime 的是 `ImageTurnInput`（全封閉值）；bytes 到這一行為止
        # 就只活在 `prepare_image_turn` 的區域變數裡，⛔ 不進 `state`／trace／log。
        image_input = None
        document_input = None
        image_elapsed = 0.0
        # 第六批 #8（line-bot 2026-09-10 回報）：`attachment_purpose="document"`
        # 但**一張照片、一份檔案都沒帶** ⇒ **視同一般回合**——⛔ 不走
        # `prepare_document_turn`、⛔ 不設 `document=`、⛔ 不套文件回合閘
        # （寫入面工具照樣可見）、⛔ 不 `INVALID_INPUT`。
        # ⚠️ 這是既有條件式（`and (image_urls or file_urls)`）本來就有的行為；
        #    這裡只是把它**記下來**：呼叫端送了那個鍵卻沒送附件是設定錯誤，
        #    而「什麼都沒發生」在稽核上是無聲的。⛔ 只記一個 bool。
        attachment_purpose_ignored = (
            purpose == "document" and not image_urls and not file_urls
        )
        if purpose == "document" and (image_urls or file_urls):
            # W9 U1／U2：文件回合走**另一條**準備函式（形狀同 `prepare_image_turn`）。
            # ⛔ 不與照片線混跑：`repair` 回合的行為必須逐位不變
            # （`tests/unit/agent/test_image_entry_req.py` 全綠即證）。
            from services.agent.document_extract import DocumentPageLimitExceeded

            try:
                document_input, image_elapsed = await prepare_document_turn(
                    image_urls, file_urls, db_pool=deps.get_db_pool(),
                )
            except DocumentPageLimitExceeded:
                # W9-15：照片頁＋PDF 頁合計超過上限 ⇒ **整回合拒**，
                # ⛔ 不截斷後照跑（那是靜默降級，使用者不會知道少看了幾頁）。
                return ToolResult(ok=False, error="INVALID_INPUT")
        elif image_urls:
            tree = None
            if repair_category_tree is not None:
                try:
                    tree = await repair_category_tree(identity)
                except Exception as exc:      # 取不到樹 ⇒ 分類缺值，⛔ 不讓回合炸掉
                    logger.warning("repair_category_tree 取不到：%s", type(exc).__name__)
                    tree = None
            image_input, image_elapsed = await prepare_image_turn(
                image_urls, category_tree=tree, db_pool=deps.get_db_pool(),
            )
        try:
            # 逾時**只包住 run_turn**（2.6 前置 security review P2／處置③）：
            # 逾時或被取消 ⇒ 直接跳出，`store.save` ⛔ 不執行，落不了半寫狀態。
            # W8 (2)：帶圖回合**扣掉照片已耗的秒數**（外層 margin 不動）——
            # ⛔ 不扣的話內層就不再是先炸的那一個，「逾時不 save」會失效。
            # ⚠️ `image=` **只在有照片時才傳**（⛔ 不無條件傳 `None`）：
            #    `run_turn` 的舊三參數簽名是 REST／影子／回測共用的介面，
            #    多傳一個具名參數會讓每一個既有替身都得跟著改。
            image_kwargs = {"image": image_input} if image_input is not None else {}
            # W9 U2：`document=` 同 `image=` 的慣例——**只在有值時才傳**
            # （`run_turn` 的舊簽名是 REST／影子／回測共用的介面，無條件多塞一個
            # 具名參數會讓每一個既有替身都得跟著改）。
            if document_input is not None:
                image_kwargs["document"] = document_input
            # T1：同 `image=` 的理由——**只在真的有值時才傳**，⛔ 不無條件多塞一個
            # 具名參數（`run_turn` 的舊簽名是 REST／影子／回測共用的介面）。
            # 正規化（控制字元／零寬／雙向／假標記）由 Runtime 端的
            # `sanitize_data_piece` 一手包辦，⛔ 不在門面先剝一次（兩處各剝一半
            # 的失敗方向是「以為對方剝過了」）。
            context = args.get("context")
            entry_kwargs = (
                {"context": context}
                if isinstance(context, str) and context.strip()
                else {}
            )
            result = await asyncio.wait_for(
                runtime.run_turn(
                    turn_identity, message, state, **image_kwargs, **entry_kwargs
                ),
                timeout=max(0.1, agent_turn_timeout_s() - image_elapsed),
            )
        except asyncio.TimeoutError:
            return ToolResult(ok=False, error="TOOL_TIMEOUT")
        # 第六批 #8：⛔ 只有 bool、⛔ 無任何附件資訊。時機在 `run_turn` **之後**
        # ——`attachment_purpose` 只有門面知道，而 `run_turn` 的舊簽名是 REST／
        # 影子／回測共用的介面（⛔ 不為一個稽核旗標多塞一個具名參數，那會讓每一個
        # 既有替身都得跟著改）。取捨：它因此**排在 `_emit_agent_decision` 之後**，
        # 只出現在 `TurnResult.trace` 上，⛔ 不進 `decision_snapshot`／trace 端點
        # （與 `has_document` 那四鍵同樣的處置，那四鍵也不在快照白名單裡）。
        if attachment_purpose_ignored:
            result.trace.attachment_purpose_ignored = True
        agent_state.pop("outline", None)
        # W8 (5)：過期戳**在存檔前才蓋**——逾時／取消的回合走不到這裡，
        # 那一列的戳因此停在上一個真正跑完的回合，⛔ 不會被一次失敗的呼叫續命。
        stamp_last_turn(agent_state)
        await store.save(session_id, state)

        return ToolResult(
            ok=True,
            data=AgentTurnOutput(
                answer=result.answer,
                kind=result.kind,
                handoff=result.handoff,
                quick_replies=list(result.quick_replies or []),
                trace_id=result.trace.trace_id,
                session_expired=session_expired,
                outcome=TurnOutcome(**_outcome_of(result)),
            ).model_dump(),
            provenance=[],
            text_for_model="",
        )

    return _agent_turn


def _as_tool_result(raw: Any) -> ToolResult:
    """把任務 1.5／1.6 的「未包裝 dict」轉成 `ToolResult`（⛔ 不改那些檔案）。"""
    if isinstance(raw, ToolResult):
        return raw
    if not isinstance(raw, dict):
        return ToolResult(ok=False, error="NO_MATCH")
    return ToolResult(
        ok=bool(raw.get("ok")),
        data=raw.get("data"),
        error=raw.get("error"),
        provenance=[Provenance(**p) for p in (raw.get("provenance") or [])],
        text_for_model=raw.get("text_for_model") or "",
    )


def build_registry(deps: FacadeDeps, registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """把 1.4／1.5／1.6 的工具函式接上 `ToolRegistry`（薄接線，⛔ 不改其行為）。

    每個 spec 都過 `registry.register()`，因此不變量 27（input_schema 無身分鍵）
    在註冊當下就會擋下違規 spec。
    """
    from services.agent.tools import action as action_tools
    from services.agent.tools import help as help_tool
    from services.agent.tools import jgb2 as jgb2_tools
    from services.agent.tools.confirm import (
        CONFIRM_SPEC,
        assert_redeemed,
        confirm_request,
    )
    from services.agent.tools.handoff import HANDOFF_SPEC, handoff_request
    from services.agent.tools.kb import KB_GET_SPEC, KB_SEARCH_SPEC, kb_get, kb_search
    from services.agent.tools.session import (
        SLOTS_GET_SPEC,
        SLOTS_SET_SPEC,
        slots_get,
        slots_set,
    )
    from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
    from services.jgb.bills import BILL_FACE_BUILDERS
    from services.jgb.contracts import FACE_BUILDERS as CONTRACT_FACE_BUILDERS
    from services.jgb.estates import ESTATE_FACE_BUILDERS
    from services.jgb.iot import METER_FACE_BUILDERS
    from services.jgb.repairs import REPAIR_FACE_BUILDERS

    # ⚠️ `write_tools_enabled` **不在此釘住**：預設 `None` ＝ 每次判可見性現讀 env
    # （registry 模組 docstring 的既定慣例）。理由是健檢印的
    # （`registry.write_tools_enabled()`）與閘門判的必須是**同一個值**，釘住會讓
    # 「這個行程啟動時的 env」與「現在的 env」在兩處各說各話。兩種來源都 fail-closed
    # （未設 ⇒ False），⛔ 不因此放寬任何一道閘。
    reg = registry if registry is not None else ToolRegistry()

    # ── 寫入型工具的確認兌現查核（S-9）：set-once 綁在 registry 上 ──────────
    # ⚠️ pool 走 **getter**（同 `_kb_get`／`_help_read` 的理由：pool 要到 lifespan
    #    才存在）。**pool 缺席 ⇒ 回 False ⇒ `CONFIRMATION_REQUIRED`**（fail-closed）：
    #    ⛔ 不得在拿不到 DB 時「當作已確認」放行一次寫入。
    async def _assert_redeemed(token: str, session_id: str) -> bool:
        pool = deps.get_db_pool() if deps.get_db_pool else None
        if pool is None:
            return False
        return await assert_redeemed(pool, token, session_id)

    reg.bind_redeem_checker(_assert_redeemed)

    async def _kb_get(identity: Identity, args: dict) -> ToolResult:
        pool = deps.get_kb_pool() if deps.get_kb_pool else None
        # ⚠️ resolver 在**每次呼叫**才取（⛔ 不在 build_registry 當下取一次）：
        #    `build_registry` 跑在 import／啟動早期，而 `app.state.outline_resolver`
        #    要到 lifespan 之後才有；取太早會永遠拿到 None。
        resolver = deps.get_outline_resolver() if deps.get_outline_resolver else None
        return await kb_get(identity, args, db_pool=pool, outline_resolver=resolver)

    async def _kb_search(identity: Identity, args: dict) -> ToolResult:
        retriever = deps.get_retriever() if deps.get_retriever else None
        if retriever is None:
            return ToolResult(ok=False, error="NO_MATCH")
        return await kb_search(identity, args, retriever=retriever)

    async def _help_read(identity: Identity, args: dict) -> ToolResult:
        raw = await help_tool.help_read(identity, args, db_pool=deps.get_db_pool())
        return _as_tool_result(raw)

    # ── 2.4 的三個工具（任務 2.9 接線）────────────────────────────────
    # 依賴一律經 `deps.get_db_pool` **getter**（同 `_kb_get`／`_help_read` 的理由：
    # pool 要到 lifespan 才存在，⛔ 不在 build_registry 當下取一次）。
    #
    # ⚠️ **pool 缺席一律 fail-closed 到 `NO_MATCH`**，⛔ 不讓它變成一個被
    #    registry 吞掉的 `AttributeError`（那也會回 NO_MATCH，但只在 trace 留
    #    `EXC:` 而不是可讀的原因）；`confirm.request` 尤其不得在無 pool 時
    #    「假裝發過 token」——沒寫進表就沒有 token，回 ok 等於憑空放行一次確認。
    async def _handoff_request(identity: Identity, args: dict) -> ToolResult:
        # ⚠️ handoff 自己 fail-soft（設定查不到 ⇒ code 保底固定句），
        #    故 pool 為 None 仍照走——它是整回合的最後出口（見 handoff.py 決定 2）。
        return await handoff_request(identity, args, db_pool=deps.get_db_pool())

    async def _slots_get(identity: Identity, args: dict) -> ToolResult:
        pool = deps.get_db_pool()
        if pool is None:
            return ToolResult(ok=False, error="NO_MATCH")
        return await slots_get(identity, args, db_pool=pool)

    async def _slots_set(identity: Identity, args: dict) -> ToolResult:
        pool = deps.get_db_pool()
        if pool is None:
            return ToolResult(ok=False, error="NO_MATCH")
        return await slots_set(identity, args, db_pool=pool)

    # ── W8 (3)：出卡前的「這個物件還有幾張未結單」查詢 ─────────────────
    #
    # ⚠️ **為什麼住在這個閉包、而不是 `confirm.py` 裡**（plan-verifier W8 r2／r3）：
    #    `confirm.py` 是工具函式，它手上沒有 registry、沒有 `stage`、沒有工具逾時，
    #    照 S8-11 的字面「走 registry」在那裡根本接不出來；而讓它自己 `import`
    #    `JGBSystemAPI` 就等於繞過 registry 的四步閘（可見性／速率／schema／
    #    身分鍵剝除）。故：**`_resolve_estate` 的唯一呼叫點在這裡**，
    #    `confirm.py` 只收一個具名注入的 callable（形狀同 `db_pool`）。
    #
    # ⛔ 取不到 `role_id` ⇒ 直接回 `None`（**不加提示行**，卡照出）：
    #    少了 `role_id` 的 `get_estate_status` 會跨 role 撈物件（r3 那一條），
    #    寧可沒有提示行，也不要一行算錯物件的提示。
    async def _open_repairs(identity: Identity, estate_name: Any) -> Optional[dict]:
        role_id = getattr(identity, "role_id", None)
        if not role_id:
            return None
        if not isinstance(estate_name, str) or not estate_name.strip():
            return None
        api = jgb2_tools._get_api()
        rows = jgb2_tools._rows_of(
            await api.get_estate_status(role_id=role_id, keyword=estate_name)
        )
        # 與 `action.repair_create` **逐字同形**：判不出唯一一列就回 None，
        # ⛔ 不挑第一筆（挑錯物件的提示行比沒有提示行更糟）。
        estate = action_tools._resolve_estate(rows, estate_name)
        if estate is None or estate.get("id") is None:
            return None
        estate_id = str(estate["id"])
        # L15 (a)⑥：**物件解析成功之後一律回 dict**（`count` 可為 0）——
        # `estate_id` 是 Runtime 判「這張卡是不是別戶」的唯一憑據，⛔ 不得因為
        # 「這一戶沒有未結單」就回 `None`：那會讓別戶的 `repair_create` 因為查無
        # 未結單而被當成「解析不出物件」放行出卡。提示行本身仍然只在 count>0 時
        # 出現（`confirm._open_repairs_hint` 判 `count <= 0`），⛔ 不在此重複判。
        result = await reg.call(
            identity,
            "jgb2.query.repairs",
            {"face": "修繕進度", "estate_id": estate_id},
            deps.tool_timeout_s,
            stage=current_stage(),
            for_model=False,
        )
        data = result.data if isinstance(result.data, dict) else {}
        # `query_repairs` 無 `ref`／`keyword` 時走 `fetch_default`＝**已濾掉結單／
        # 封存**（`_CLOSED_REPAIR_STATUSES`）的未結列，⛔ 不在此另抄一份狀態表。
        # ⚠️ 已知取捨：列數受 `JGB2_CANDIDATE_CAP`（預設 5）截斷 ⇒ 超過 5 張時
        #    N 只會顯示 5。提示行是資訊性文字、不含可兌現內容，接受。
        rows = data.get("candidates") if result.ok else None
        if not isinstance(rows, list):
            rows = []
        ids = [str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id") is not None]
        return {"estate_id": estate_id, "count": len(rows), "ids": ids}

    # ── W8 (2)：影像段要用的修繕分類樹 ─────────────────────────────────
    #
    # ⚠️ **形狀同 `_open_repairs`**：影像段（`prepare_image_turn`）⛔ 不得直呼
    #    `JGBSystemAPI`——那會繞過 registry 的四步閘，也會讓 `mcp_facade` 以外
    #    多一個 API 的呼叫點。取不到（例外／空）⇒ 回 `None` ⇒ 分類一律缺值、
    #    ⛔ 不回候選（卡上 `UNSPECIFIED_CATEGORY_ZH`）。
    async def _repair_category_tree(identity: Identity) -> Optional[list]:
        rows = jgb2_tools._rows_of(await jgb2_tools._get_api().get_repair_categories())
        return rows or None

    async def _confirm_request(identity: Identity, args: dict) -> ToolResult:
        pool = deps.get_db_pool()
        if pool is None:
            return ToolResult(ok=False, error="NO_MATCH")
        return await confirm_request(
            identity, args, db_pool=pool, open_repairs=_open_repairs
        )

    reg.register(KB_GET_SPEC, _kb_get)
    reg.register(KB_SEARCH_SPEC, _kb_search)
    reg.register(HELP_READ_SPEC, _help_read)
    reg.register(HANDOFF_SPEC, _handoff_request)
    reg.register(SLOTS_GET_SPEC, _slots_get)
    reg.register(SLOTS_SET_SPEC, _slots_set)
    reg.register(CONFIRM_SPEC, _confirm_request)

    domains = (
        ("bills", BILL_FACE_BUILDERS, jgb2_tools.query_bills),
        ("contracts", CONTRACT_FACE_BUILDERS, jgb2_tools.query_contracts),
        ("accounts", ACCOUNT_FACE_BUILDERS, jgb2_tools.query_accounts),
        ("meters", METER_FACE_BUILDERS, jgb2_tools.query_meters),
        ("estates", ESTATE_FACE_BUILDERS, jgb2_tools.query_estates),
        ("repairs", REPAIR_FACE_BUILDERS, jgb2_tools.query_repairs),
    )
    for domain, builders, fn in domains:

        def _make(fn=fn):
            async def _query(identity: Identity, args: dict) -> ToolResult:
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

    # ── W4：寫入型工具 `jgb2.action.*` ────────────────────────────────────
    # ⚠️ **一律註冊**，可見性交給 `specs_for` 的兩道閘（入口 `entry=="mcp"` ＋
    #    旗標 `AGENT_WRITE_TOOLS_ENABLED`）。⛔ 不學 `agent.turn` 那樣「旗標關就
    #    不註冊」——那條路的旗是**回切開關**（整條路徑消失），這裡的旗是**可見性
    #    閘**，兩者語義不同：不註冊會讓「旗標翻面不必重建 registry」這條慣例失效，
    #    而閘本身已經 fail-closed。
    for action_spec, action_fn in action_tools.ACTION_SPECS:
        reg.register(action_spec, action_fn)

    # `agent.turn`：**受 env 回切開關管**（任務 2.6）。關閉 ⇒ 根本不註冊，
    # 於是 `union_specs`／`tools/list`／`registry.call` 三處同時看不到它——
    # ⛔ 不是「註冊了但呼叫時才拒」，回切要的是整條路徑消失。
    if agent_turn_enabled():
        reg.register(
            AGENT_TURN_SPEC, _make_agent_turn(deps, repair_category_tree=_repair_category_tree)
        )

    return reg


# ════════════════════════════════════════════════════════════════════
# 工具薄包裝：簽名生成 ＋ 計量 ＋ ToolError
# ════════════════════════════════════════════════════════════════════
_JSON_TO_PY = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def _tool_error_message(code: Optional[str]) -> str:
    """`ToolError` 的訊息＝**業務代碼**，⛔ 不含任何其他資訊。

    SDK 會把 `ToolError` 的訊息原樣送到模型端；放進例外文字／SQL／身分等於把
    後端狀態洩給模型（research STRIDE：Information Disclosure）。
    """
    return code or "NO_MATCH"


def _annotation_source(prop: dict, required: bool) -> tuple:
    """由單一 property schema 產生 (標註原始碼, 標註物件或 None, 是否選填)。"""
    enum = prop.get("enum")
    if enum:
        return ("_lit", tuple(enum), not required)
    py = _JSON_TO_PY.get(prop.get("type", "string"), "str")
    return (py, None, not required)


def _build_wrapper(spec: ToolSpec, invoke: Callable, context_cls: Any) -> Callable:
    """依 `ToolSpec.input_schema` 生成一個簽名相符的 async 薄包裝。

    SDK 只從**函式簽名**推導 input schema（`Tool.from_function`），無法直接餵
    JSON Schema ⇒ 這裡用 `exec` 產生一個具名參數的函式。生成的參數名來自
    `input_schema.properties`，而不變量 27 已保證那裡不含身分鍵；此外本函式
    另外檢查參數名必須是合法識別字（⛔ 不讓 schema 內容變成可執行程式碼的縫）。
    """
    import typing

    schema = spec.get("input_schema", {}) or {}
    props: dict = schema.get("properties", {}) or {}
    required = list(schema.get("required", []) or [])

    params_src = ["ctx: _Context"]
    ns: dict = {
        "_invoke": invoke,
        "_name": spec["name"],
        "typing": typing,
        "_Context": context_cls,
        # ⚠️ 回傳標註必須是 `dict[str, Any]`，⛔ 不能是裸 `dict`——SDK 實測會擋：
        #    `InvalidSignature: return type <class 'dict'> is not serializable for
        #     structured output`（mcp 2.1.1，utilities/func_metadata.py）。
        "_RetT": typing.Dict[str, Any],
    }
    arg_names = []
    for i, (pname, prop) in enumerate(props.items()):
        if not pname.isidentifier() or pname.startswith("_"):
            raise ValueError(f"ToolSpec {spec['name']!r} 的參數名 {pname!r} 不是合法識別字")
        ann_kind, enum_values, optional = _annotation_source(prop, pname in required)
        ann_name = f"_ann_{i}"
        if ann_kind == "_lit":
            ns[ann_name] = typing.Literal[enum_values]  # type: ignore[valid-type]
        else:
            ns[ann_name] = {"str": str, "int": int, "float": float,
                            "bool": bool, "list": list, "dict": dict}[ann_kind]
        if optional:
            ns[ann_name] = typing.Optional[ns[ann_name]]
            params_src.append(f"{pname}: {ann_name} = None")
        else:
            params_src.append(f"{pname}: {ann_name}")
        arg_names.append(pname)

    body_args = ", ".join(f"{n!r}: {n}" for n in arg_names)
    src = (
        f"async def _tool({', '.join(params_src)}) -> _RetT:\n"
        f"    _args = {{{body_args}}}\n"
        f"    _args = {{k: v for k, v in _args.items() if v is not None}}\n"
        f"    return await _invoke(_name, ctx, _args)\n"
    )
    # ⚠️ `dont_inherit=True` 是必要的：本檔頂端有 `from __future__ import annotations`，
    #    而 `exec()` 預設**繼承呼叫端的 __future__ 旗標** ⇒ 生成函式的標註會變成
    #    字串（PEP 563），`inspect.signature()` 讀到 `'_ann_0'` 而非 `Literal[...]`。
    #    SDK 端雖然走 `get_type_hints` 能解回來，但簽名是本層對外的契約，不留這個坑。
    code = compile(src, "<mcp_facade generated>", "exec", dont_inherit=True)
    exec(code, ns)  # noqa: S102 — 來源是本檔生成的字串，變數只有已驗過的識別字
    fn = ns["_tool"]
    fn.__name__ = spec["name"].replace(".", "_")
    fn.__doc__ = spec.get("description", "")
    return fn


def _agent_turn_visible(registry: ToolRegistry, deps: FacadeDeps,
                        identity: Identity) -> bool:
    """`agent.turn` 對這個身分是否可見（門面視角 `for_model=False`）。

    ⛔ 不讀 registry 的私有字典——`specs_for` 才是唯一的可見性規則，
    未註冊（`AGENT_TURN_ENABLED=false`）與 stage/audience 不合都由它回答。
    """
    return any(
        spec["name"] == AGENT_TURN_NAME
        for spec in registry.specs_for(identity, deps.stage, for_model=False)
    )


def _agent_turn_preflight(deps: FacadeDeps, identity: Identity) -> Optional[str]:
    """`agent.turn` 專屬前置檢查；通過回 `None`，否則回**業務代碼字串**。

    順序刻意如此：
    ① runtime／engine 缺席 ⇒ `AGENT_UNAVAILABLE`（服務沒接好，⛔ 不燒配額）。
    ② 命名空間鍵組不出來（缺 `api_key_id`／`vendor_id`、或鍵超過
       `form_sessions.session_id` 的 100 字）⇒ `INVALID_INPUT`。
       這條在 registry 內部只會變成一個被吞掉的例外（`NO_MATCH`），
       所以必須在門面這一層先判，呼叫端才知道是自己的 `session_id` 太長。
    ③ 每小時上限 ⇒ `RATE_LIMITED`。放最後：前兩者都是「這次呼叫根本不成立」，
       不該把配額算在呼叫端頭上。
    """
    if _app_state(deps, "agent_runtime") is None or _app_state(
        deps, "agent_session_store"
    ) is None:
        return ERR_AGENT_UNAVAILABLE
    # DSP-037／S1b：`agent.turn` 已對 pm 可見，但 pm 正本可能沒上線（`app.py` 只跳過
    # 該受眾、⛔ 不掛啟動）⇒ 沒有這個受眾的大綱＝服務對他沒接好，回 ① 同一個碼。
    # ⚠️ 判準見 `_outline_for_audience`：prospect 在舊形狀（只有單數 `agent_outline`、
    # 或兩者皆無）下**永遠不會**落到這一條 ⇒ 既有 prospect 語義逐字不變，⛔ 不新增
    # 外顯失敗；會落到這裡的只有「有對照表卻缺該受眾」與「舊形狀下的非 prospect」，
    # 兩者都是 fail-closed 的正確答案（⛔ 不得改成放行後塞 prospect 大綱）。
    if _outline_for_audience(deps, identity.resolved_audience()) is _OUTLINE_UNAVAILABLE:
        return ERR_AGENT_UNAVAILABLE
    try:
        _open_state_store(deps, identity)
    except ValueError:
        return "INVALID_INPUT"
    if not check_and_record_agent_turn((identity.api_key_id, identity.vendor_id)):
        return "RATE_LIMITED"
    return None


def _make_invoke(registry: ToolRegistry, deps: FacadeDeps) -> Callable:
    """產生 `_invoke(name, ctx, args)`——三道檢查 ＋ 計量 ＋ registry.call。"""

    async def _invoke(name: str, ctx: Any, args: dict) -> dict:
        tool_error = _tool_error_cls()
        pool = deps.get_db_pool()
        headers = getattr(ctx, "headers", None)
        try:
            call = await resolve_call(headers, pool)
        except McpRequestError as e:
            raise tool_error(_tool_error_message(e.code)) from None

        identity = call.identity
        note_mcp_traffic(identity.api_key_id, is_internal=call.is_internal)

        from services import usage_metering as um

        um.begin(_metering_fields(identity))
        uctx = um._ctx.get()
        if uctx is None:
            _STATS.metering_unavailable += 1
            logger.error("[mcp] 計量 context 建立失敗（USAGE_METERING_ENABLED？）——拒絕服務")
            raise tool_error(_tool_error_message(ERR_METERING))
        _stamp_metering_context(uctx, identity, call.is_internal, name)

        quota = await um.quota_check(pool, identity.vendor_id, call.is_internal)
        if quota.state == "blocked":
            um.set_path("quota_blocked")
            um.finalize("blocked", 429, db_pool=pool)
            raise tool_error(_tool_error_message(ERR_QUOTA))

        timeout_s = deps.tool_timeout_s
        # ⚠️ preflight 只在 `agent.turn` **對這個身分可見**時才跑。不可見時
        #    （tenant／pm、或 stage 未到）一律讓 `registry.call()` 統一回
        #    `NO_MATCH`——否則一個看不到這支工具的身分還能從
        #    `AGENT_UNAVAILABLE`／`RATE_LIMITED` 分辨出「服務存在但沒起來」，
        #    等於把後端狀態洩給不該知道的人，也白燒他的配額。
        if name == AGENT_TURN_NAME and _agent_turn_visible(registry, deps, identity):
            # `agent.turn` 的三道 preflight（任務 2.6）。都在 `begin()`／
            # `quota_check()` **之後**——不變量 31 要的是「一次呼叫恰一列
            # `usage_events`」，被擋掉的呼叫同樣得留下那一列，⛔ 不能是免費的探測。
            code = _agent_turn_preflight(deps, identity)
            if code is not None:
                um.set_path(f"mcp:{AGENT_TURN_NAME}:{code}")
                um.finalize("blocked" if code == "RATE_LIMITED" else "error",
                            429 if code == "RATE_LIMITED" else 503, db_pool=pool)
                raise tool_error(_tool_error_message(code))
            # 外層只是保險（見 `_AGENT_TURN_OUTER_MARGIN_S`）；真正決定
            # 「逾時不 save」的是 `_agent_turn` 內層那個 `wait_for`。
            timeout_s = agent_turn_timeout_s() + _AGENT_TURN_OUTER_MARGIN_S

        # 交給工具的身分＝**命名空間身分**（任務 2.9，理由見 `namespaced_identity`）。
        # `agent.turn` 是唯一的例外：它自己要用裸 `session_id` 餵
        # `NamespacedStateStore`（那支會自己加前綴），換過就變雙前綴。
        identity_for_tool = identity
        if name != AGENT_TURN_NAME:
            try:
                identity_for_tool = namespaced_identity(identity)
            except ValueError:
                # 缺 api_key_id／vendor_id 或鍵超長 ⇒ fail-closed。⛔ 不退回裸身分。
                um.set_path(f"mcp:{name}:INVALID_INPUT")
                um.finalize("error", 400, db_pool=pool)
                raise tool_error(_tool_error_message("INVALID_INPUT"))

        try:
            result = await registry.call(
                identity_for_tool, name, args, timeout_s, stage=deps.stage
            )
        except Exception:
            um.finalize("error", 500, db_pool=pool)
            raise
        um.finalize("success" if result.ok else "error", 200, db_pool=pool)

        if not result.ok:
            raise tool_error(_tool_error_message(result.error))
        return result.data or {}

    return _invoke


def _metering_fields(identity: Identity) -> dict:
    """`usage_metering.begin()` 的欄位。

    ⛔ **刻意不傳 `session_id`**：`begin()` 會拿它跑 `INTERNAL_RULES`
    （`backtest_`／`loop_`／smoke 前綴 ⇒ is_internal=True），而 `/mcp` 的內部
    與否只能由 API key 紀錄決定（決策 13）。session_id 於
    `_stamp_metering_context()` 直接補進 context，⛔ 不經規則表。
    ⛔ 也不傳 `message`（門面不接觸對話原文）。
    """
    return {
        "vendor_id": identity.vendor_id,
        "mode": identity.mode,
        "target_user": identity.target_user,
        "role_id": identity.role_id,
        "user_id": identity.user_id,
        "channel": "mcp",
    }


def _stamp_metering_context(uctx: Any, identity: Identity, is_internal: bool, name: str) -> None:
    """把 `/mcp` 專屬欄位蓋回計量 context（session_id、is_internal、路徑）。"""
    uctx.session_id = identity.session_id
    uctx.is_internal = bool(is_internal)
    uctx.internal_kind = "api_key" if is_internal else None
    uctx.processing_path = f"mcp:{name}"[:60]
    uctx.answer_source = "mcp_tool"


@dataclass(frozen=True)
class ResolvedCall:
    """一次 `/mcp` 請求解析後的身分與 key 屬性。"""

    identity: Identity
    api_key_id: Optional[int]
    is_internal: bool


async def resolve_call(headers: Any, pool: Any, allowed_origins: Optional[frozenset] = None) -> ResolvedCall:
    """三道請求層檢查（順序固定）：key → Origin → 身分。

    Raises:
        McpRequestError: 401／403／400，`code` 為封閉業務代碼。
    """
    from fastapi import HTTPException

    from services.api_key_auth import require_api_key_unconditional

    try:
        key = await require_api_key_unconditional(headers, pool)
    except HTTPException:
        raise McpRequestError(401, ERR_API_KEY) from None

    check_origin(headers, allowed_origins)

    async def _vendor_exists(vendor_id: int) -> bool:
        return await vendor_exists(pool, vendor_id)

    identity = await parse_identity(headers, key=key, vendor_check=_vendor_exists)
    return ResolvedCall(
        identity=identity,
        api_key_id=key.get("id"),
        is_internal=bool(key.get("is_internal")),
    )


async def vendor_exists(pool: Any, vendor_id: int) -> bool:
    """`vendors` 表存在性檢查；**查不動 ⇒ 視為不存在**（fail-closed）。"""
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            return bool(await conn.fetchval(
                "SELECT 1 FROM vendors WHERE id = $1", vendor_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[mcp] vendors 存在性查詢失敗，fail-closed：{e}")
        return False


class FacadeToolError(Exception):
    """SDK 未安裝時的 `ToolError` 替身。

    ⚠️ 這**不是**放寬：MCP SDK 沒裝時 `/mcp` 的工具面根本沒掛（`app.py` 只掛
    服務層閘），走不到這個例外。它的存在只為了讓門面在沒有 SDK 的環境下仍可
    匯入與測試（額度落點、fail-closed 三道閘都在同一段程式裡）。
    真裝了 SDK 時 `_tool_error_cls()` 一定回 SDK 的 `ToolError`。
    """


def _tool_error_cls():
    """`mcp.server.mcpserver.exceptions.ToolError`（延遲匯入）；沒 SDK 回替身。"""
    try:
        from mcp.server.mcpserver.exceptions import ToolError
    except Exception:  # noqa: BLE001 — 見 FacadeToolError 的說明
        return FacadeToolError
    return ToolError


# ════════════════════════════════════════════════════════════════════
# MCP server 建構
# ════════════════════════════════════════════════════════════════════
def build_mcp_server(registry: ToolRegistry, deps: FacadeDeps):
    """建 `MCPServer("jgb-tools")` 並把每個 ToolSpec 註冊為薄包裝。

    ⛔ 無 `token_verifier`／`auth`（DSP-011：非公開認證面）。
    工具清單取 `specs_for(..., for_model=False)`——門面視角（含 `facade_only`
    工具，排除模型專屬過濾）；**per-identity 的可見性**由兩層守：
    ① `tools/list` 由 `_ToolListFilter` 依請求身分過濾（best-effort）；
    ② 真正的硬閘在 `registry.call()`——不可見的名字一律 `NO_MATCH`。
    """
    from mcp.server.mcpserver import Context, MCPServer

    mcp = MCPServer("jgb-tools", middleware=[_ToolListFilter(registry, deps)])
    invoke = _make_invoke(registry, deps)

    for spec in union_specs(registry, deps.stage):
        fn = _build_wrapper(spec, invoke, Context)
        mcp.add_tool(
            fn,
            name=spec["name"],
            description=spec.get("description", ""),
            structured_output=True,
        )
    return mcp


#: `specs_for` 的探針身分（三個 audience 各一），用來取「本階段任一身分可見」的聯集。
#: ⚠️ 實際建構在 `union_specs` 內，並帶 `entry="mcp"`（DSP-038-1／W1b）——
#: 本表只列 `(target_user, mode)` 兩軸，⛔ 不在此另存第三軸。
_PROBE_IDENTITIES = (
    ("prospect", "b2c"),
    ("property_manager", "b2b"),
    ("tenant", "b2c"),
)


def union_specs(registry: ToolRegistry, stage: Stage) -> list:
    """本階段**任一 audience** 看得見的 ToolSpec 聯集（門面視角 `for_model=False`）。

    MCP 的 `tools/list` 是 server 級靜態清單，而可見性是 per-identity 的 ⇒
    註冊聯集、逐次呼叫再由 `registry.call()` 依真實身分判一次（不可見一律
    `NO_MATCH`），`tools/list` 另由 `_ToolListFilter` 依身分過濾。
    用 `specs_for` 而非直接讀 registry 內部字典，是為了讓 `stage` 上限
    （例如 M0 不註冊 M4／M5 的寫入工具）自動生效。
    """
    seen: dict = {}
    for target_user, mode in _PROBE_IDENTITIES:
        # DSP-038-1／W1b：探針帶 `entry="mcp"`——這份聯集決定的是 **`/mcp` 的
        # `mcp.add_tool` 清單**（建構期一次），本來就只描述 MCP 入口看得到什麼。
        # ⛔ 不帶就等於「寫入型工具永遠不會被註冊到 MCP server 上」，
        # per-identity 的真閘仍在 `_ToolListFilter`（列表）與 `registry.call`（呼叫）。
        probe = Identity(vendor_id=None, target_user=target_user, mode=mode,
                         entry="mcp")
        for spec in registry.specs_for(probe, stage, for_model=False):
            seen[spec["name"]] = spec
    return list(seen.values())


class _MountPathNormalizer:
    """把 `Mount("/mcp", …)` 剝完前綴後的空路徑補成 `"/"`。

    ⚠️ 實測（mcp 2.1.1 + starlette）：`Mount("/mcp", app=子app)` 對
    `POST /mcp` 會把子 app 的 `scope["path"]` 設成 `""`，子 app 的 router 於是
    **307 轉址**到 `/mcp/`；而 MCP client 的 httpx 預設不跟隨轉址 ⇒ 握手直接
    以 `MCPError: Unexpected content type:`（空 body）失敗。
    補成 `"/"` 讓 `POST /mcp` 與 `POST /mcp/` 都直接命中，⛔ 不要求呼叫端記得加斜線。
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and not scope.get("path"):
            scope = dict(scope, path="/", raw_path=b"/")
        await self.app(scope, receive, send)


def build_asgi_app(mcp, *, mount_path: str = "/mcp"):
    """建 `/mcp` 的 ASGI 子 app（供 `Mount(mount_path, app=…)`）。

    兩個 ⛔ 不可省的參數：
    1. `streamable_http_path="/"` —— 子 app 的路徑；預設是 `"/mcp"`，
       和 `Mount("/mcp", …)` 相加會變成 `/mcp/mcp`。
    2. `transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)`
       —— **必須顯式關掉 SDK 自帶的 DNS rebinding 檢查**。實測：
       `streamable_http_app()` 的 `host` 預設是 `"127.0.0.1"`，SDK 會**自動**啟用
       只允許 `127.0.0.1`／`localhost`／`[::1]` 的 Host／Origin 白名單
       （`mcp/server/lowlevel/server.py` 的 "Auto-enable DNS rebinding protection
       for localhost"），於是任何經 nginx 進來、Host 是真實網域的請求一律
       **421 Invalid Host header**。
       本系統的 Origin 判定唯一來源是 `check_origin`（三態語義，缺 Origin 放行、
       非白名單 403），Host 的合法值屬部署層（nginx `server_name`）的事，
       ⛔ 不在應用層猜。**這一條要進 1.9 security review 的議程。**
    """
    from mcp.server.transport_security import TransportSecuritySettings

    sub = mcp.streamable_http_app(
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return _MountPathNormalizer(sub)


class _ToolListFilter:
    """`tools/list` 依請求身分過濾（`ServerMiddleware` 協定）。

    fail-closed：解析不出身分（缺 header、vendor 不明…）⇒ 回空清單，
    ⛔ 不回全集。真正的權限硬閘仍在 `registry.call()`。
    """

    def __init__(self, registry: ToolRegistry, deps: FacadeDeps) -> None:
        self._registry = registry
        self._deps = deps

    async def __call__(self, ctx, call_next):
        result = await call_next(ctx)
        if getattr(ctx, "method", None) != "tools/list":
            return result
        try:
            headers = getattr(getattr(ctx, "request", None), "headers", None)
            call = await resolve_call(headers, self._deps.get_db_pool())
            visible = {
                s["name"]
                for s in self._registry.specs_for(
                    call.identity, self._deps.stage, for_model=False
                )
            }
        except Exception:  # noqa: BLE001 — fail-closed
            visible = set()
        return _filter_tools(result, visible)


def _filter_tools(result: Any, visible: set) -> Any:
    """把 `tools/list` 結果裡不在 `visible` 的工具剔除（dict 與 BaseModel 皆支援）。"""
    if isinstance(result, dict) and isinstance(result.get("tools"), list):
        result["tools"] = [
            t for t in result["tools"]
            if (t.get("name") if isinstance(t, dict) else getattr(t, "name", None)) in visible
        ]
        return result
    tools = getattr(result, "tools", None)
    if isinstance(tools, list):
        try:
            result.tools = [t for t in tools if getattr(t, "name", None) in visible]
        except Exception:  # noqa: BLE001 — 不可變模型：改用複製
            return result
    return result


# ════════════════════════════════════════════════════════════════════
# ASGI 服務層閘
# ════════════════════════════════════════════════════════════════════
#: 受無條件服務層閘管轄的路徑前綴（不變量 28：⛔ 不得列入 `_EXEMPT_PREFIX`）。
GATED_PREFIXES = ("/mcp", "/api/v1/agent")


class McpServiceGate:
    """純 ASGI middleware：`/mcp`／`/api/v1/agent/*` 的三道請求層檢查。

    掛在 middleware 堆疊**最外層**（`app.add_middleware` 最後加者最外層），
    因此在 `api_key_guard` 與 `usage_metering_middleware` 之前跑。解析成功的
    `ResolvedCall` 放進 `scope["state"]["mcp_call"]`，供
    `usage_metering_middleware` 做 `/mcp` 的額度短路（⛔ 它不 begin／finalize）。

    ⚠️ OPTIONS **不豁免**：`/mcp` 僅 server-to-server，CORS 預檢本來就不該出現。
    """

    def __init__(self, app, *, get_pool: Callable[[], Any],
                 prefixes: tuple = GATED_PREFIXES) -> None:
        self.app = app
        self._get_pool = get_pool
        self._prefixes = prefixes
        # 啟動即讀——未設定 ⇒ raise（啟動紅）。
        self._allowed_origins = load_allowed_origins()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith(self._prefixes):
            await self.app(scope, receive, send)
            return

        from starlette.datastructures import Headers

        headers = Headers(scope=scope)
        try:
            call = await resolve_call(headers, self._get_pool(), self._allowed_origins)
        except McpRequestError as e:
            if str(scope.get("path", "")).startswith("/mcp"):
                # `ERR_API_KEY`（401）＝key 本身缺／驗不到——這才是「未登錄」；
                # 其他代碼（vendor_unknown／origin_not_allowed…）發生在 key 已
                # 驗過**之後**，各自已有獨立旗標，⛔ 不冒充成 key 問題。
                note_mcp_traffic(None, is_internal=False if e.code == ERR_API_KEY else None)
            await _send_json(send, e.status, {"detail": e.code, "code": e.code})
            return

        path = str(scope.get("path", ""))
        if path.startswith("/mcp"):
            note_mcp_traffic(call.api_key_id, is_internal=call.is_internal)
        scope.setdefault("state", {})["mcp_call"] = call
        if path == "/mcp":
            # ⚠️ 實測：`Mount("/mcp", …)` 的比對式是 `^/mcp(?P<path>/.*)$`，
            #    `POST /mcp`（無尾斜線）在**外層 router** 就被 307 轉址到 `/mcp/`，
            #    而 MCP client 的 HTTP 層預設不跟隨轉址 ⇒ 握手以
            #    `MCPError: Unexpected content type:`（空 body）失敗。
            #    在這裡改寫路徑，讓 `/mcp` 與 `/mcp/` 都直達，
            #    ⛔ 不要求呼叫端記得加斜線（design 的端點就寫作 `/mcp`）。
            scope = dict(scope, path="/mcp/", raw_path=b"/mcp/")
        await self.app(scope, receive, send)


async def _send_json(send, status: int, body: dict) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode())],
    })
    await send({"type": "http.response.body", "body": payload})


def mcp_sdk_available() -> tuple:
    """MCP SDK 是否可匯入 →（可用, 說明）。

    ✅ **SDK 已是正式相依**（DSP-014 裁 A，2026-09-04）：`requirements.txt` 已把
    web stack 升到承載 `mcp` 的版本（fastapi 0.115.14／starlette 0.46／
    pydantic 2.13／anyio 4.15／uvicorn 0.52／mcp 2.1.1），原先的
    `fastapi==0.104.1` × `anyio<4` 相依衝突**已解除**。

    因此本函式只是**防禦性守衛**，⛔ 不是「尚未安裝」的旗標——它讓 `/mcp` 的
    服務層閘（401／403／400）在 image 供裝出錯、SDK 匯不進來時仍然成立
    （工具面掛不上，請求走到 404），而不是整個 app 起不來。
    正常部署下它必為 `(True, "")`；回 False 代表**供裝壞了**，該去看 image。
    """
    try:
        import mcp.server.mcpserver  # noqa: F401
    except Exception as e:  # noqa: BLE001
        return (False, f"{type(e).__name__}: {e}")
    return (True, "")
