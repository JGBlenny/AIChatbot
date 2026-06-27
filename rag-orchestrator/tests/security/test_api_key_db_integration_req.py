"""整合測試（真實 DB）：verify_api_key 以 sha256 查 api_keys 表驗證。

驗證：有效啟用 key→回 {id,name} 並更新 last_used_at；錯 key/停用 key→None。測完清理。
"""
import os

import asyncpg
import pytest

from services.api_key_auth import hash_key, verify_api_key

pytestmark = pytest.mark.integration

_PLAIN = "qa-apikey-integration-secret"
_NAME = "__qa_apikey__"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("api-key-auth:1.1")
async def test_verify_api_key_db():
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM api_keys WHERE name = $1", _NAME)
            await conn.execute(
                "INSERT INTO api_keys (name, key_hash, key_prefix, is_active) VALUES ($1,$2,$3,TRUE)",
                _NAME, hash_key(_PLAIN), _PLAIN[:8],
            )

        # 有效 key → 命中 + 回名稱
        ok = await verify_api_key(pool, _PLAIN)
        assert ok and ok["name"] == _NAME

        # last_used_at 已更新
        async with pool.acquire() as conn:
            lu = await conn.fetchval("SELECT last_used_at FROM api_keys WHERE name=$1", _NAME)
        assert lu is not None

        # 錯 key → None
        assert await verify_api_key(pool, "wrong-key") is None
        # 沒帶 → None
        assert await verify_api_key(pool, None) is None

        # 停用後 → None
        async with pool.acquire() as conn:
            await conn.execute("UPDATE api_keys SET is_active=FALSE WHERE name=$1", _NAME)
        assert await verify_api_key(pool, _PLAIN) is None
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM api_keys WHERE name = $1", _NAME)
        await pool.close()
