"""rag-orchestrator 服務對服務 API Key 認證（資料庫管理 + 安全可上線）。

金鑰存於 `api_keys` 表（只存 SHA-256 雜湊 + 前綴，不存明文，後台 CRUD 管理）。
- 開關：環境變數 `RAG_API_AUTH_ENFORCE`（預設關）。關→不強制（維持現狀，安全上線）；
  開→除豁免路徑外，請求須帶 Header `X-API-Key`，且其 sha256 命中 api_keys(is_active)。
- 命中時更新 last_used_at（看誰在用）。

純函式（hash/exempt/enforced）可離線單元測試；DB 驗證 verify_api_key 走 integration。
搭配「內網不對外」為縱深防禦；IP 白名單可於網路層另加（程式不需改）。
"""
import hashlib
import os
from typing import Optional

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


async def verify_api_key(pool, key: Optional[str]) -> Optional[dict]:
    """以 sha256(key) 查 api_keys（is_active）。命中→更新 last_used_at 並回 {id,name}；否則 None。"""
    if not key or pool is None:
        return None
    key_hash = hash_key(key)
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name FROM api_keys WHERE key_hash = $1 AND is_active = TRUE",
                key_hash,
            )
            if row:
                await conn.execute("UPDATE api_keys SET last_used_at = now() WHERE id = $1", row["id"])
                return dict(row)
    except Exception as e:
        print(f"⚠️ [security] API key 驗證查詢失敗：{e}")
        return None
    return None
