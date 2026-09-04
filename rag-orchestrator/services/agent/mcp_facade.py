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
- **每小時上限** `AGENT_TURN_CAP`（預設 120，key `(api_key_id, vendor_id)`）。
註冊本身受 `AGENT_TURN_ENABLED`（預設 false）管，⛔ 不受 `AGENT_AUDIENCES` 左右。

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
import inspect
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from pydantic import BaseModel

from services.agent.identity import Identity, Stage
from services.agent.state_store import NamespacedStateStore
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

_VALID_MODES = ("b2b", "b2c")
_DEFAULT_MODE = "b2c"

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

#: `agent.turn` 專屬：`app.state.agent_runtime`／`app.state.conversational_engine`
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

    mode = payload.get("mode")
    if mode not in _VALID_MODES:
        mode = _DEFAULT_MODE

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
        target_user=_normalize_target_user(payload.get("target_user")),
        mode=mode,
        role_id=_opt_str(payload.get("role_id")),
        user_id=_opt_str(payload.get("user_id")),
        session_id=session_id.strip(),
        api_key_id=(key or {}).get("id"),
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
      `app.state.conversational_engine`（狀態存取用的引擎）、
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
_AGENT_TURN_CAP_ENV = "AGENT_TURN_CAP"

#: 預設 **30 秒 > `Budget.deadline_s`（20）**（2.6 前置 security review P2）：
#: 門面對一般唯讀工具的 3 秒逾時是給「一次 DB／API 查詢」用的，整回合會跑
#: 多次模型呼叫，3 秒必然砍在半路。⛔ 不要把兩者合成同一個值。
_DEFAULT_AGENT_TURN_TIMEOUT_S = 30.0

#: `registry.call()` 外層 `wait_for` 相對於內層回合逾時的寬限（秒）。
#: 內層（`_agent_turn` 自己的 `wait_for`）先炸 ⇒ 保證「逾時不 save」；
#: 外層只是**卡死的 save 也有出口**的保險，⛔ 不該是先觸發的那一個。
_AGENT_TURN_OUTER_MARGIN_S = 5.0

#: 每小時每 `(api_key_id, vendor_id)` 的 `agent.turn` 次數上限（比照 `KB_GET_CAP`）。
_DEFAULT_AGENT_TURN_CAP = 120
_AGENT_TURN_WINDOW_S = 3600.0

#: 滑動視窗：`(api_key_id, vendor_id) -> [呼叫時戳]`。
#: ⚠️ **行程內記憶體**——多 worker 部署時每個 worker 各有一份，實際上限是
#: `cap × worker 數`。這與 `ToolRegistry` 既有的 `RATE_PER_MIN`／`KB_GET_CAP`
#: 同一個限制，⛔ 不在 2.6 另建共享計數器（那是額度層 `usage_metering` 的事）。
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
    """`AGENT_TURN_CAP`（預設 120／小時／`(api_key_id, vendor_id)`）；非法值回預設。"""
    raw = (os.getenv(_AGENT_TURN_CAP_ENV) or "").strip()
    if not raw:
        return _DEFAULT_AGENT_TURN_CAP
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_AGENT_TURN_CAP
    return value if value >= 0 else _DEFAULT_AGENT_TURN_CAP


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


def _jgb2_spec(domain: str, faces: list) -> ToolSpec:
    """`jgb2.query.<domain>` 的 ToolSpec（`face` ＝該域註冊表鍵的封閉 enum）。

    `stage` 依 design 元件 2 矩陣：`{property_manager: M0, tenant: M0}`；
    **prospect 缺鍵＝永不可見**（售前不查 jgb2 個資）。
    """
    return {
        "name": f"jgb2.query.{domain}",
        "description": (
            f"查詢 {domain} 領域的決定性事實；face 決定回傳哪一組 facts，"
            "ref／keyword 只能在已確立的範圍內縮小。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "face": {"type": "string", "enum": list(faces)},
                "ref": {"type": "string"},
                "keyword": {"type": "string"},
            },
            "required": ["face"],
            "additionalProperties": False,
        },
        "scope": "read",
        "stage": {"property_manager": "M0", "tenant": "M0"},
    }


# ════════════════════════════════════════════════════════════════════
# `agent.turn`：整回合工具（任務 2.6｜design 元件 4「agent.turn 工具」段、決策 15、R3.7）
# ════════════════════════════════════════════════════════════════════
class AgentTurnOutput(BaseModel):
    """`agent.turn` 的回傳形狀（R3.7 明列的五個鍵）。

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
        "properties": {"message": {"type": "string", "minLength": 1, "maxLength": 2000}},
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
    # 本 spec 的對話對象只有 prospect（範圍聲明）；tenant／pm **缺鍵＝永不可見**。
    "stage": {"prospect": "M1"},
}


def _app_state(deps: FacadeDeps, name: str) -> Any:
    """讀 `app.state.<name>`；沒有 `get_app`／沒有該屬性一律 `None`（fail-closed）。"""
    if deps.get_app is None:
        return None
    app = deps.get_app()
    state = getattr(app, "state", None)
    return getattr(state, name, None) if state is not None else None


def _open_state_store(deps: FacadeDeps, identity: Identity) -> NamespacedStateStore:
    """建 `NamespacedStateStore` 並**當場驗一次鍵**（超長／缺 id ⇒ `ValueError`）。

    `_invoke` 的 preflight 與 `_agent_turn` 各呼叫一次：前者是為了把失敗轉成
    正確的錯誤碼（registry 內拋例外一律被吞成 `NO_MATCH`），後者才是真的用它。
    兩次都是純運算、無 I/O，⛔ 不值得為此在 `ToolFn` 簽名上開洞傳物件。
    """
    engine = _app_state(deps, "conversational_engine")
    store = NamespacedStateStore(engine, identity.api_key_id, identity.vendor_id)
    store.key(identity.session_id)  # 形狀／長度先驗
    return store


def _make_agent_turn(deps: FacadeDeps) -> Callable:
    """`agent.turn` 的 `ToolFn`：載入命名空間狀態 → `run_turn` → 存回。

    ⛔ **不另寫第二條回合邏輯**（R3.7）：Verifier、固定句、預算、計量全都在
    `AgentRuntime.run_turn` 裡，這裡只負責狀態的載入與存回。
    """

    async def _agent_turn(identity: Identity, args: dict) -> ToolResult:
        message = args.get("message")
        if not isinstance(message, str) or not message.strip():
            return ToolResult(ok=False, error="INVALID_INPUT")

        runtime = _app_state(deps, "agent_runtime")
        if runtime is None:
            # `_invoke` 的 preflight 已經擋過（回 AGENT_UNAVAILABLE）；走到這裡
            # 代表有人繞過門面直接呼 `registry.call()` ⇒ 用封閉錯誤值域裡的
            # `NO_MATCH`，⛔ 不在對模型可見的值域上多開一個碼。
            return ToolResult(ok=False, error="NO_MATCH")
        try:
            store = _open_state_store(deps, identity)
        except ValueError:
            return ToolResult(ok=False, error="INVALID_INPUT")

        session_id = identity.session_id
        state = await store.load(session_id)
        if state is None:
            state = await store.start(
                session_id,
                identity.user_id or "anonymous",
                identity.vendor_id,
                identity.role_id,
            )

        agent_state = state.setdefault("agent", {})
        # 大綱是**行程級共用物件**（`app.state.agent_outline`）。Runtime 從
        # `state["agent"]["outline"]` 取，故這裡進場前塞、存檔前 pop——
        # ⛔ 不得讓它被序列化進 `form_sessions.collected_data`（每個 session 存一份
        # 幾千字的大綱，而且會就此凍結在舊版本）。與 `routers/agent_entry.py`
        # 的 REST 路徑同一個處置。
        outline = _app_state(deps, "agent_outline")
        if outline is not None:
            agent_state["outline"] = outline
        try:
            # 逾時**只包住 run_turn**（2.6 前置 security review P2／處置③）：
            # 逾時或被取消 ⇒ 直接跳出，`store.save` ⛔ 不執行，落不了半寫狀態。
            result = await asyncio.wait_for(
                runtime.run_turn(identity, message, state),
                timeout=agent_turn_timeout_s(),
            )
        except asyncio.TimeoutError:
            return ToolResult(ok=False, error="TOOL_TIMEOUT")
        agent_state.pop("outline", None)
        await store.save(session_id, state)

        return ToolResult(
            ok=True,
            data=AgentTurnOutput(
                answer=result.answer,
                kind=result.kind,
                handoff=result.handoff,
                quick_replies=list(result.quick_replies or []),
                trace_id=result.trace.trace_id,
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
    from services.agent.tools import help as help_tool
    from services.agent.tools import jgb2 as jgb2_tools
    from services.agent.tools.kb import KB_GET_SPEC, KB_SEARCH_SPEC, kb_get, kb_search
    from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
    from services.jgb.bills import BILL_FACE_BUILDERS
    from services.jgb.contracts import FACE_BUILDERS as CONTRACT_FACE_BUILDERS
    from services.jgb.estates import ESTATE_FACE_BUILDERS
    from services.jgb.iot import METER_FACE_BUILDERS

    reg = registry if registry is not None else ToolRegistry()

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

    reg.register(KB_GET_SPEC, _kb_get)
    reg.register(KB_SEARCH_SPEC, _kb_search)
    reg.register(HELP_READ_SPEC, _help_read)

    domains = (
        ("bills", BILL_FACE_BUILDERS, jgb2_tools.query_bills),
        ("contracts", CONTRACT_FACE_BUILDERS, jgb2_tools.query_contracts),
        ("accounts", ACCOUNT_FACE_BUILDERS, jgb2_tools.query_accounts),
        ("meters", METER_FACE_BUILDERS, jgb2_tools.query_meters),
        ("estates", ESTATE_FACE_BUILDERS, jgb2_tools.query_estates),
    )
    for domain, builders, fn in domains:

        def _make(fn=fn):
            async def _query(identity: Identity, args: dict) -> ToolResult:
                return _as_tool_result(await fn(identity, args))

            return _query

        reg.register(_jgb2_spec(domain, sorted(builders.keys())), _make())

    # `agent.turn`：**受 env 回切開關管**（任務 2.6）。關閉 ⇒ 根本不註冊，
    # 於是 `union_specs`／`tools/list`／`registry.call` 三處同時看不到它——
    # ⛔ 不是「註冊了但呼叫時才拒」，回切要的是整條路徑消失。
    if agent_turn_enabled():
        reg.register(AGENT_TURN_SPEC, _make_agent_turn(deps))

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
        deps, "conversational_engine"
    ) is None:
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

        try:
            result = await registry.call(
                identity, name, args, timeout_s, stage=deps.stage
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
        probe = Identity(vendor_id=None, target_user=target_user, mode=mode)
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
