"""`/api/v1/agent/openapi.json`・`/health`・`/trace`（spec agentic-mcp-orchestration・任務 1.8／2.7）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 4、附錄 B 不變量 28。

## 兩端點的無條件服務層閘
兩者都用 `services.api_key_auth.require_api_key_unconditional`——**無條件**要求
有效 `X-API-Key`，⛔ 不受 `RAG_API_AUTH_ENFORCE` 左右（不變量 28 以 AST 檢查
本檔不得出現該旗標的判定函式名）。這與 `/mcp` 同一把閘、同一函式，⛔ 不另寫
第二套認證邏輯。

`McpServiceGate`（`app.py` 掛載的最外層 middleware，`mcp_facade.GATED_PREFIXES`
已含 `/api/v1/agent`）在到達本檔之前就會先跑完整三道檢查（key／Origin／
`X-JGB-Identity`），本檔的呼叫是**縱深防禦第二層**——與 `mcp_facade._invoke`
對 `/mcp` 工具呼叫的做法同構：門面即使日後改掛法，這一層仍 fail-closed；
也讓本檔可離開完整 app（含 middleware）單獨做 unit 測試。

## registry 的取得方式
`build_registry(deps)` 是 1.7 已交付的純接線函式（不查 DB、只註冊工具函式），
本檔在**本行程內快取一份**（`_get_registry_and_deps`），⛔ 不手刻第二份工具
清單——沿用的是同一個 `build_registry` 函式與同一組 `FacadeDeps` 建構方式，
只是與 `app.py` 為 `/mcp` 建的那份是兩個獨立實例（`app.py` 的那份只在 MCP SDK
可匯入時才建，見 app.py 的 `_mcp_sdk_ok` 分支；本端點不應被「SDK 未裝」擋住，
`openapi.json`／`health` 都是純 FastAPI 路由，與 MCP SDK 是否可匯入無關）。

## `/trace` 兩端點的越權邊界（任務 2.7）
軌跡是**別的業者的對話行為紀錄**，跨業者可讀就是安全事故。三層擋：

1. **無條件 X-API-Key**（同上，`require_api_key_unconditional`）。
2. **`X-JGB-Identity` 必帶**（`mcp_facade.parse_identity`）——`/api/v1/agent` 在
   `mcp_facade.GATED_PREFIXES` 內，門面 middleware 本來就會要；這裡是第二層，
   讓端點離開完整 app 時仍 fail-closed（前置 security review P3）。
3. **key 的 `vendor_ids` 過濾列的 `vendor_id`**——非 NULL 且不含該列的
   `vendor_id` ⇒ **404**，與「trace 不存在」**同一個狀態碼**：⛔ 不得用 403／404
   的差別告訴呼叫端「這個 trace_id 存在、只是不屬於你」（那是可枚舉的預言機）。

查詢一律帶**時間窗**（`AGENT_TRACE_WINDOW_DAYS`，預設 7）＋`LIMIT`：
`decision_snapshot->'agent'->>'trace_id'` 沒有索引，無窗查詢等於開放全表掃。

⚠️ **時間欄是 `usage_events.ts`，不是 `created_at`**——本表沒有 `created_at` 欄
（正本：`database/migrations/add_usage_events.sql` 的 `CREATE TABLE`；四支
`ALTER TABLE usage_events` migration 也都沒加）。派工契約寫的 `created_at` 與
實表不符，已於回報標記交裁決。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from services.agent import mcp_facade, trace_view
from services.agent.health import compute_agent_health
from services.api_key_auth import require_api_key_unconditional

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

# ════════════════════════════════════════════════════════════════════
# registry／deps：本行程內快取一份（首次請求時建）
# ════════════════════════════════════════════════════════════════════
_registry = None
_deps = None
_kb_pool = None


def _build_deps(app) -> "mcp_facade.FacadeDeps":
    global _kb_pool
    if _kb_pool is None:
        _kb_pool = mcp_facade.LazyPsycopg2Pool()
    return mcp_facade.FacadeDeps(
        get_db_pool=lambda: getattr(app.state, "db_pool", None),
        get_kb_pool=lambda: _kb_pool,
        get_retriever=None,
        stage=mcp_facade.current_stage(),
    )


def _get_registry_and_deps(request: Request):
    """首次呼叫建構、之後沿用同一份（`build_registry` 只註冊函式，無 I/O）。"""
    global _registry, _deps
    if _registry is None:
        _deps = _build_deps(request.app)
        _registry = mcp_facade.build_registry(_deps)
    return _registry, _deps


def reset_registry_cache() -> None:
    """測試用：清掉行程內快取（⛔ 產品路徑不呼叫）。"""
    global _registry, _deps, _kb_pool
    _registry, _deps, _kb_pool = None, None, None


async def _require_key(request: Request) -> dict:
    pool = getattr(request.app.state, "db_pool", None)
    return await require_api_key_unconditional(request, pool)


def _make_vendor_check(pool):
    async def _check(vendor_id: int) -> bool:
        return await mcp_facade.vendor_exists(pool, vendor_id)

    return _check


async def _require_identity(request: Request, key: dict, pool) -> "mcp_facade.Identity":
    """`X-JGB-Identity` 必帶（缺／壞 400、越權 403）——⛔ 不給預設身分。"""
    try:
        return await mcp_facade.parse_identity(
            request.headers, key=key, vendor_check=_make_vendor_check(pool)
        )
    except mcp_facade.McpRequestError as e:
        raise HTTPException(status_code=e.status, detail=e.code) from None


# ════════════════════════════════════════════════════════════════════
# GET /api/v1/agent/trace/{trace_id}・GET /api/v1/agent/trace?session_id=
# ════════════════════════════════════════════════════════════════════
_TRACE_NOT_FOUND = "TRACE_NOT_FOUND"

# 時間欄是 `ts`（見模組 docstring 的 ⚠️）。`$3::int[] IS NULL` 讓「key 不限業者」
# 與「key 限業者」共用同一句 SQL，⛔ 不用字串拼接組 WHERE。
_TRACE_BY_ID_SQL = (
    "SELECT ts, session_id, vendor_id, decision_snapshot"
    " FROM usage_events"
    " WHERE decision_snapshot->'agent'->>'trace_id' = $1"
    "   AND ts > now() - ($2 || ' days')::interval"
    "   AND ($3::int[] IS NULL OR vendor_id = ANY($3::int[]))"
    " LIMIT 1"
)

_TRACE_BY_SESSION_SQL = (
    "SELECT ts, session_id, vendor_id, decision_snapshot"
    " FROM usage_events"
    " WHERE session_id = $1"
    "   AND decision_snapshot->'agent'->>'trace_id' IS NOT NULL"
    "   AND ts > now() - ($2 || ' days')::interval"
    "   AND ($3::int[] IS NULL OR vendor_id = ANY($3::int[]))"
    " ORDER BY ts ASC"
    f" LIMIT {trace_view.SESSION_TIMELINE_LIMIT}"
)


def _key_vendor_ids(key: dict) -> Optional[list]:
    """key 的業者範圍。NULL／缺 ⇒ None（不限），其餘轉成 int 清單。"""
    raw = (key or {}).get("vendor_ids")
    if raw is None:
        return None
    return [int(v) for v in raw]


def _row_in_scope(row: Any, vendor_ids: Optional[list]) -> bool:
    """縱深防禦第二層：SQL 已經過濾過，這裡再擋一次（SQL 被改壞時仍 fail-closed）。"""
    if vendor_ids is None:
        return True
    try:
        return int(row["vendor_id"]) in vendor_ids
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def _require_pool(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="DB_UNAVAILABLE")
    return pool


@router.get("/trace/{trace_id}")
async def agent_trace_by_id(trace_id: str, request: Request):
    """單一回合軌跡。查無／不在 key 的業者範圍內 ⇒ **一律 404**（同碼）。"""
    key = await _require_key(request)
    pool = getattr(request.app.state, "db_pool", None)
    await _require_identity(request, key, pool)
    pool = _require_pool(request)

    vendor_ids = _key_vendor_ids(key)
    row = await pool.fetchrow(
        _TRACE_BY_ID_SQL, trace_id, str(trace_view.window_days()), vendor_ids
    )
    if row is None or not _row_in_scope(row, vendor_ids):
        raise HTTPException(status_code=404, detail=_TRACE_NOT_FOUND)
    return trace_view.render_trace(row)


@router.get("/trace")
async def agent_trace_by_session(
    request: Request,
    session_id: str = Query(..., min_length=1, max_length=120),
):
    """同 session 的多回合時間軸（時間窗內、最多 50 筆、依 `ts` 由舊到新）。"""
    key = await _require_key(request)
    pool = getattr(request.app.state, "db_pool", None)
    await _require_identity(request, key, pool)
    pool = _require_pool(request)

    vendor_ids = _key_vendor_ids(key)
    rows = await pool.fetch(
        _TRACE_BY_SESSION_SQL, session_id, str(trace_view.window_days()), vendor_ids
    )
    views = [
        trace_view.render_trace(r) for r in rows if _row_in_scope(r, vendor_ids)
    ]
    # ⛔ 回應不帶原始 `session_id`（連呼叫端自己送來的那個也不回）——遮罩值
    # 就是端點對外的唯一 session 識別。
    return {
        "session": trace_view.mask_session(session_id),
        "count": len(views),
        "window_days": trace_view.window_days(),
        "traces": views,
    }


# ════════════════════════════════════════════════════════════════════
# GET /api/v1/agent/openapi.json
# ════════════════════════════════════════════════════════════════════
@router.get("/openapi.json")
async def agent_openapi(request: Request):
    """只列該身分可見的工具（門面視角，`for_model=False`）。"""
    key = await _require_key(request)
    registry, deps = _get_registry_and_deps(request)
    pool = getattr(request.app.state, "db_pool", None)

    try:
        identity = await mcp_facade.parse_identity(
            request.headers, key=key, vendor_check=_make_vendor_check(pool)
        )
    except mcp_facade.McpRequestError as e:
        raise HTTPException(status_code=e.status, detail=e.code) from None

    return registry.openapi(identity, deps.stage)


# ════════════════════════════════════════════════════════════════════
# GET /api/v1/agent/health
# ════════════════════════════════════════════════════════════════════
@router.get("/health")
async def agent_health(request: Request):
    """健檢：HTTP 一律 200，紅以 body 的 `status` 表達（見 `services/agent/health.py`）。"""
    await _require_key(request)
    registry, deps = _get_registry_and_deps(request)
    return await compute_agent_health(
        registry=registry,
        get_kb_pool=deps.get_kb_pool,
        stage=deps.stage,
        # `api_keys` 欄位偵測要 asyncpg pool——`deps.get_db_pool` 就是
        # `app.state.db_pool`（1.10 P2 的 `api_keys_agent_scope_ready` 一項）。
        get_api_key_pool=deps.get_db_pool,
        get_runtime=lambda: getattr(request.app.state, "agent_runtime", None),
    )
