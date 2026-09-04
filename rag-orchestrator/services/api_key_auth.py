"""rag-orchestrator 服務對服務 API Key 認證（資料庫管理 + 安全可上線）。

金鑰存於 `api_keys` 表（只存 SHA-256 雜湊 + 前綴，不存明文，後台 CRUD 管理）。
- 開關：環境變數 `RAG_API_AUTH_ENFORCE`（預設關）。關→不強制（維持現狀，安全上線）；
  開→除豁免路徑外，請求須帶 Header `X-API-Key`，且其 sha256 命中 api_keys(is_active)。
- 命中時更新 last_used_at（看誰在用）。

⚠️ **無條件通道（agentic-mcp-orchestration 1.7，不變量 28）**：
`/mcp` 與 `/api/v1/agent/*` **不受上述開關左右**——見
`require_api_key_unconditional()`。理由：DSP-011 把「額度」定為本系統對呼叫者的
唯一控制，而額度綁在 API key 紀錄上；沒有 key 就沒有額度歸屬，等於沒有控制。
`_EXEMPT_PREFIX` ⛔ 不得加入 `/mcp`（不變量 28 以 AST 檢查）。

純函式（hash/exempt/enforced）可離線單元測試；DB 驗證 verify_api_key 走 integration。
搭配「內網不對外」為縱深防禦；IP 白名單可於網路層另加（程式不需改）。
"""
import hashlib
import os
from typing import Any, Optional

# 豁免路徑：健康檢查 / 文件 / 首頁（CORS 預檢 OPTIONS 於 middleware 另行放行）
_EXEMPT_EXACT = {"/", "/api/v1/health"}
_EXEMPT_PREFIX = ("/docs", "/redoc", "/openapi")


def is_exempt(path: str) -> bool:
    """是否為免認證路徑。"""
    return path in _EXEMPT_EXACT or path.startswith(_EXEMPT_PREFIX)


def hash_key(key: str) -> str:
    """API key 的 SHA-256 hex（與後台寫入時一致；高熵金鑰用快雜湊即可）。"""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def auth_enforced() -> bool:
    """是否強制 API Key（環境變數 RAG_API_AUTH_ENFORCE）。預設關＝不強制。"""
    return os.getenv("RAG_API_AUTH_ENFORCE", "").strip().lower() in ("1", "true", "yes", "on")


# ── api_keys 的 agent 作用域兩欄（migration 20260904_api_keys_agent_scope.sql）──
# 一次性偵測快取，比照 services/usage_metering.py 的 `_score_cols_present` 慣例：
# None＝尚未偵測；True/False＝欄位是否已建。**欄位未建時降級**（is_internal=False、
# vendor_ids=None＝不限），⛔ 不讓整筆驗證失敗——migration 未套不該把既有呼叫者鎖在門外。
_AGENT_SCOPE_COLS = ("is_internal", "vendor_ids")
_agent_scope_cols_present: Optional[bool] = None

_BASE_SELECT = "SELECT id, name FROM api_keys WHERE key_hash = $1 AND is_active = TRUE"
_EXTENDED_SELECT = (
    "SELECT id, name, is_internal, vendor_ids FROM api_keys "
    "WHERE key_hash = $1 AND is_active = TRUE"
)


def _reset_agent_scope_detection() -> None:
    """測試用：清掉欄位偵測快取（⛔ 產品路徑不呼叫）。"""
    global _agent_scope_cols_present
    _agent_scope_cols_present = None


async def _detect_agent_scope_cols(conn) -> bool:
    """查 information_schema 判斷兩欄是否都在；偵測失敗保持未知（下次重試）。"""
    global _agent_scope_cols_present
    if _agent_scope_cols_present is not None:
        return _agent_scope_cols_present
    try:
        n = await conn.fetchval(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'api_keys' AND column_name = ANY($1::text[])",
            list(_AGENT_SCOPE_COLS),
        )
    except Exception as e:  # noqa: BLE001 — 偵測失敗＝未知，維持 None 下次重試
        print(f"⚠️ [security] api_keys agent 作用域欄位偵測失敗（本次降級）：{e}")
        return False
    _agent_scope_cols_present = (int(n or 0) == len(_AGENT_SCOPE_COLS))
    return _agent_scope_cols_present


def _normalize_key_row(row: Any) -> dict:
    """把查詢列正規化為固定四欄，缺欄一律降級。

    - `is_internal`：缺 ⇒ `False`（不得預設成內部，那等於免額度）。
    - `vendor_ids`：缺 ⇒ `None`＝**不限業者**（與 migration 的欄位語義同）。
    """
    data = dict(row)
    vendor_ids = data.get("vendor_ids")
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "is_internal": bool(data.get("is_internal") or False),
        "vendor_ids": (list(vendor_ids) if vendor_ids is not None else None),
    }


async def verify_api_key(pool, key: Optional[str]) -> Optional[dict]:
    """以 sha256(key) 查 api_keys（is_active）。

    命中→更新 last_used_at 並回 `{id, name, is_internal, vendor_ids}`；否則 None。

    ⚠️ 回傳形狀自 1.7 起由 `{id, name}` **擴為四欄**（新增欄位只增不改，既有
    呼叫端讀 `["id"]`／`["name"]` 不受影響）。兩個新欄在 migration 未套時降級為
    `False`／`None`，⛔ 不整筆失敗。
    """
    if not key or pool is None:
        return None
    key_hash = hash_key(key)
    try:
        async with pool.acquire() as conn:
            has_scope_cols = await _detect_agent_scope_cols(conn)
            try:
                row = await conn.fetchrow(
                    _EXTENDED_SELECT if has_scope_cols else _BASE_SELECT, key_hash
                )
            except Exception as e:  # noqa: BLE001 — 欄位在偵測與查詢之間被移除等
                print(f"⚠️ [security] api_keys 擴充欄位查詢失敗，降級為基本欄位：{e}")
                _reset_agent_scope_detection()
                row = await conn.fetchrow(_BASE_SELECT, key_hash)
            if row:
                await conn.execute("UPDATE api_keys SET last_used_at = now() WHERE id = $1", row["id"])
                return _normalize_key_row(row)
    except Exception as e:
        print(f"⚠️ [security] API key 驗證查詢失敗：{e}")
        return None
    return None


def _header_value(headers: Any, name: str) -> Optional[str]:
    """從 starlette `Headers`（大小寫不敏感）或普通 Mapping 取值。

    普通 Mapping 走「逐鍵小寫比對」——`X-Api-Key`／`x-api-key` 皆須取得到，
    否則大小寫差一個字母就等於沒帶 key（會被誤判成攻擊者而非組態錯誤）。
    """
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


async def require_api_key_unconditional(request, pool) -> dict:
    """`/mcp`／`/api/v1/agent/*` 專用：**無條件**要求有效 X-API-Key。

    ⛔ 本函式不讀 `RAG_API_AUTH_ENFORCE`（不變量 28 以 AST 檢查門面不得引用該旗標
    的判定函式）——服務層閘對這兩條路徑一律生效，缺／錯一律 401。

    Args:
        request: `starlette.Request`（取 `.headers`）或直接給一個 headers Mapping
            （MCP 工具層從 SDK 的 `Context.headers` 取得的就是後者）。
        pool: asyncpg pool。

    Returns:
        `{id, name, is_internal, vendor_ids}`。

    Raises:
        fastapi.HTTPException: 401（缺 key／key 無效／DB 不可達）。
    """
    from fastapi import HTTPException  # 局部匯入：純函式區塊保持可離線單元測試

    headers = getattr(request, "headers", request)
    row = await verify_api_key(pool, _header_value(headers, "x-api-key"))
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return row
