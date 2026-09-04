"""`/api/v1/agent/openapi.json`・`/api/v1/agent/health`（spec agentic-mcp-orchestration・任務 1.8）。

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
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from services.agent import mcp_facade
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
    )
