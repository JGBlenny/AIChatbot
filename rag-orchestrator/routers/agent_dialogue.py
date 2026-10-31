"""專用對話 API：`POST /api/v1/agent/turn`・`POST /api/v1/agent/upload-ticket`（DSP-131）。

計畫：`.kiro/specs/agentic-mcp-orchestration/plan-dialogue-api-20261031.md` §5.1、§5.2 第 1 項。
對外經 nginx 為 `{AICHATBOT_BASE}/v1/agent/turn`、`.../upload-ticket`；一回合一次 HTTP POST，
⛔ 沒有 MCP 的 `initialize`／`Mcp-Session-Id`。

## 與 `/mcp` 共用同一條路（⛔ 不得另寫第二套）
- 認證：兩條路徑都在 `mcp_facade.GATED_PREFIXES`（`/api/v1/agent`）之下，`McpServiceGate`
  （`app.py` 最外層 middleware）在到達本檔前就跑完 key → Origin → `X-JGB-Identity` 三道檢查；
  `_invoke` 內的 `resolve_call(entry="dialogue")` 是第二層（同 `/mcp`）。本檔 ⛔ 看
  `RAG_API_AUTH_ENFORCE`（不變量 28）。
- 呼叫：`_invoke` 由 `mcp_facade._make_invoke(registry, deps, entry="dialogue")` 建，
  `registry`／`deps` **必須是 `app.py` 的 `_mcp_registry`／`_mcp_deps` 同一份**
  （每分鐘上限掛在 registry 實例上；⛔ 照抄 `routers/agent.py` 自建 registry）。
  ⇒ 本檔只提供 `build_router(registry, deps)`，沒有模組層 `router`；`app.py` 一行接上：
  `app.include_router(agent_dialogue.build_router(_mcp_registry, _mcp_deps))`。
- 計量：每次進到 `_invoke` 的呼叫恰一列 `usage_events`（不變量 31），
  `channel="dialogue_api"`、`processing_path="api:<tool>"`、`answer_source="dialogue_api"`。

## body
收原始 JSON（⛔ pydantic body 模型——會走 FastAPI 422、回顯 `input`、不經 `_invoke`、
不寫 `usage_events`，計畫 F5）。不是 JSON object ⇒ 400 `INVALID_INPUT`（不進 `_invoke`，
與 `/mcp` 送壞 JSON-RPC 一樣不寫列）；其餘原樣交 `_invoke`，身分鍵剝除與
`additionalProperties` 由 `registry.call` 做。body 上限＝`mcp_facade.DIALOGUE_MAX_BODY_BYTES`
（與 `/mcp` 的 SDK 上限相同），超過 ⇒ 413。

## 回應
- 200：工具結果 dict 原樣（`agent.turn` 為 `AgentTurnOutput`）。
- 非 200：`{"code": <業務代碼>, "detail"?: <_input_detail 白名單內的字>}`；狀態依
  `mcp_facade.DIALOGUE_STATUS_BY_CODE`（計畫 §5.1）。請求層代碼（金鑰／Origin／身分）
  的 body 與 `McpServiceGate` 相同（`{"detail": code, "code": code}`），呼叫端不論被哪一層
  擋下看到的都一樣。
- 表外代碼與非預期例外 ⇒ 500 固定 body `{"code": "INTERNAL_ERROR"}`，⛔ 帶例外文字。

⛔ 本檔不 import `mcp.*`（稽核 `agent_boundary.py` 檢查）：對話 API 不得因 MCP SDK
供裝與否而掛掉。log 只記代碼與例外類名，⛔ 記 body、身分或例外訊息。
"""
from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.agent import mcp_facade

logger = logging.getLogger(__name__)

#: 請求層代碼：body 與 `McpServiceGate` 相同（`{"detail": code, "code": code}`）。
_REQUEST_LAYER_CODES: frozenset = frozenset({
    mcp_facade.ERR_IDENTITY_MALFORMED,
    mcp_facade.ERR_IDENTITY_NO_VENDOR,
    mcp_facade.ERR_IDENTITY_NO_SESSION,
    mcp_facade.ERR_IDENTITY_NO_USER,
    mcp_facade.ERR_API_KEY,
    mcp_facade.ERR_ORIGIN,
    mcp_facade.ERR_VENDOR_UNKNOWN,
    mcp_facade.ERR_VENDOR_OUT_OF_KEY_SCOPE,
})


class _BodyTooLarge(Exception):
    """body 超過 `DIALOGUE_MAX_BODY_BYTES`。"""


def _code_response(status: int, code: str, detail: Any = None) -> JSONResponse:
    if code in _REQUEST_LAYER_CODES:
        return JSONResponse(status_code=status, content={"detail": code, "code": code})
    body: dict = {"code": code}
    if isinstance(detail, str) and detail:
        body["detail"] = detail
    return JSONResponse(status_code=status, content=body)


def _internal_error() -> JSONResponse:
    return JSONResponse(status_code=500, content={"code": mcp_facade.DIALOGUE_INTERNAL_ERROR})


async def _read_capped_body(request: Request) -> bytes:
    """讀 body，超過上限即停（⛔ 讀完整包）。`Content-Length` 已超過 ⇒ 不讀直接拒。"""
    limit = mcp_facade.DIALOGUE_MAX_BODY_BYTES
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > limit:
                raise _BodyTooLarge()
        except ValueError:
            pass  # 宣告值不是整數 ⇒ 不信它，下面邊讀邊計數
    chunks: list = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise _BodyTooLarge()
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_object(raw: bytes) -> Any:
    """JSON object ⇒ dict；其餘（空 body、壞 JSON、非 UTF-8、陣列、純量）⇒ `None`。"""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


async def _handle(request: Request, invoke: Callable, tool_name: str) -> JSONResponse:
    try:
        raw = await _read_capped_body(request)
    except _BodyTooLarge:
        return _code_response(413, mcp_facade.DIALOGUE_BODY_TOO_LARGE)
    args = _parse_object(raw)
    if args is None:
        return _code_response(400, "INVALID_INPUT")

    # shim ctx：`_invoke` 只讀 `.headers`（與 MCP `Context` 同介面）。
    ctx = SimpleNamespace(headers=request.headers)
    try:
        out = await invoke(tool_name, ctx, args)
    except mcp_facade.FacadeCallError as err:
        if err.code not in mcp_facade.DIALOGUE_STATUS_BY_CODE:
            logger.error("[dialogue] %s 表外代碼 → 500：%s", tool_name, err.code)
            return _internal_error()
        return _code_response(err.status, err.code, err.detail)
    except Exception as exc:  # noqa: BLE001 — 固定 500，⛔ 帶例外文字
        logger.error("[dialogue] %s 未預期例外 → 500：%s", tool_name, type(exc).__name__)
        return _internal_error()

    try:
        return JSONResponse(status_code=200, content=out)
    except Exception as exc:  # noqa: BLE001 — 結果序列化失敗同樣固定 500
        logger.error("[dialogue] %s 結果無法序列化 → 500：%s", tool_name, type(exc).__name__)
        return _internal_error()


def build_router(registry: Any, deps: Any) -> APIRouter:
    """建對話 API 的 router；`registry`／`deps` 必須是 `/mcp` 用的同一份（見模組 docstring）。"""
    invoke = mcp_facade._make_invoke(registry, deps, entry="dialogue")
    router = APIRouter(tags=["agent"])

    async def agent_turn(request: Request) -> JSONResponse:
        return await _handle(request, invoke, mcp_facade.AGENT_TURN_NAME)

    async def agent_upload_ticket(request: Request) -> JSONResponse:
        return await _handle(request, invoke, mcp_facade.UPLOAD_TICKET_NAME)

    # 路徑只准取自 `mcp_facade` 的常數（稽核 28 以 AST 驗它們在 `GATED_PREFIXES` 之下）。
    router.add_api_route(mcp_facade.DIALOGUE_TURN_PATH, agent_turn,
                         methods=["POST"], include_in_schema=False)
    router.add_api_route(mcp_facade.DIALOGUE_UPLOAD_TICKET_PATH, agent_upload_ticket,
                         methods=["POST"], include_in_schema=False)
    return router
