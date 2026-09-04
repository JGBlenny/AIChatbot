"""integration：`agent_confirmation_tokens` 表與 token 兌現（agentic-mcp-orchestration 任務 2.4）。

真 DB：套 migration（冪等）→ `confirm.request` 寫一張 token →
兌現一次成功 → 第二次 `CONFIRMATION_REQUIRED`（冪等）→ 過期拒 → 跨 session 拒 →
payload 改一個鍵拒。無法連 DB → skip（非 fail）。測試列於 finally 清掉。

⚠️ 為什麼 `session.slots.set` 的 jsonb 寫入也在這一檔：那句 `jsonb_set(...)` 是
   本任務唯一沒有純 Python 對應物的東西——mock pool 只證明「我們傳了這些參數」，
   證明不了 Postgres 收得下、路徑建得對。故此處真跑一次來回。
"""
import os
import uuid

import pytest

from services.agent.identity import Identity
from services.agent.tools.confirm import (
    canonical_json,
    confirm_request,
    payload_digest,
    pending_id_for,
    redeem_token,
    sha256_hex,
)
from services.agent.tools.session import read_slots, slots_set

pytestmark = pytest.mark.integration

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260905_agent_confirmation_tokens.sql",
)
# ⚠️ `form_sessions` 是既有表：本檔 ⛔ 不建它，只插／清自己的測試列。

#: 測試列一律用這個前綴（tasks.md 鐵律），清理靠它。
_SESSION_PREFIX = "backtest_session_agent24_"
_CONVERSATIONAL_FORM_ID = "conversational"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _session_id() -> str:
    return _SESSION_PREFIX + uuid.uuid4().hex[:12]


def _identity(session_id: str) -> Identity:
    return Identity(
        vendor_id=1, target_user="tenant", mode="b2c",
        role_id="20151", user_id="1", session_id=session_id, api_key_id=1,
    )


@pytest.fixture
async def pool():
    import asyncpg
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    with open(_MIGRATION, encoding="utf-8") as f:
        await p.execute(f.read())
    try:
        yield p
    finally:
        await p.execute(
            "DELETE FROM agent_confirmation_tokens WHERE session_id LIKE $1",
            _SESSION_PREFIX + "%",
        )
        await p.execute(
            "DELETE FROM form_sessions WHERE session_id LIKE $1", _SESSION_PREFIX + "%"
        )
        await p.close()


async def _issue_token(pool, session_id: str, payload: dict, summary: str = "確認送出這筆"):
    """走真的 `confirm.request`，再從表裡把 token 撈回來（工具本身 ⛔ 不回 token）。"""
    result = await confirm_request(
        _identity(session_id), {"summary": summary, "payload": payload}, db_pool=pool
    )
    assert result.ok is True, result
    row = await pool.fetchrow(
        "SELECT token, payload_sha256, summary_sha256, redeemed, "
        "       expires_at > now() AS alive "
        "FROM agent_confirmation_tokens WHERE session_id = $1", session_id,
    )
    assert row is not None, "confirm.request 應該寫進一列（正對照組）"
    return result, row


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_confirm_request_writes_hashes_only_and_hides_token(pool):
    """表裡只有雜湊；`ToolResult` 完全不含 token。"""
    session_id = _session_id()
    payload = {"repair_id": 12, "note": "水管漏水"}
    result, row = await _issue_token(pool, session_id, payload)

    assert row["payload_sha256"] == payload_digest(payload)
    assert row["summary_sha256"] == sha256_hex("確認送出這筆")
    assert row["redeemed"] is False
    assert row["alive"] is True
    # 原文 ⛔ 不落地
    assert "水管漏水" not in canonical_json(dict(row))
    # token ⛔ 不回給模型
    assert row["token"] not in result.model_dump_json()
    assert result.data["pending_id"] == pending_id_for(row["token"])


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_redeem_succeeds_once_then_is_idempotently_refused(pool):
    session_id = _session_id()
    payload = {"repair_id": 12, "note": "水管漏水"}
    _, row = await _issue_token(pool, session_id, payload)
    token = row["token"]

    first = await redeem_token(pool, session_id, token, payload)
    assert first.ok is True, "第一次兌現必須成功（正對照組）"
    assert first.payload_sha256 == payload_digest(payload)

    second = await redeem_token(pool, session_id, token, payload)
    assert second.ok is False
    assert second.error == "CONFIRMATION_REQUIRED"

    third = await redeem_token(pool, session_id, token, payload)
    assert third.ok is False and third.error == "CONFIRMATION_REQUIRED"

    still = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE token = $1", token
    )
    assert still["redeemed"] is True


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_expired_token_is_refused(pool):
    session_id = _session_id()
    payload = {"a": 1}
    _, row = await _issue_token(pool, session_id, payload)
    token = row["token"]

    # 正對照組：動手腳前它是可兌現的——先確認「還沒過期時真的會過」
    probe = await pool.fetchrow(
        "SELECT expires_at > now() AS alive FROM agent_confirmation_tokens WHERE token=$1",
        token,
    )
    assert probe["alive"] is True

    await pool.execute(
        "UPDATE agent_confirmation_tokens SET expires_at = now() - interval '1 second' "
        "WHERE token = $1", token,
    )
    expired = await redeem_token(pool, session_id, token, payload)
    assert expired.ok is False and expired.error == "CONFIRMATION_REQUIRED"
    # 過期的 token ⛔ 不得被標成已兌現（`UPDATE` 的 WHERE 沒中）
    row2 = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE token=$1", token
    )
    assert row2["redeemed"] is False


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_cross_session_redeem_is_refused(pool):
    session_a, session_b = _session_id(), _session_id()
    payload = {"a": 1}
    _, row = await _issue_token(pool, session_a, payload)
    token = row["token"]

    stolen = await redeem_token(pool, session_b, token, payload)
    assert stolen.ok is False and stolen.error == "CONFIRMATION_REQUIRED"
    # 未被燒掉：合法 session 仍然兌現得到（正對照組——證明拒絕來自 session 不符，
    # 不是因為 token 本身壞了）
    legit = await redeem_token(pool, session_a, token, payload)
    assert legit.ok is True


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_payload_tampered_by_one_key_is_refused(pool):
    """使用者確認的是 A、送來的是 B ⇒ 拒；且 token 當場燒掉（刻意，見模組 docstring）。"""
    session_id = _session_id()
    payload = {"repair_id": 12, "note": "水管漏水", "urgent": False}
    _, row = await _issue_token(pool, session_id, payload)
    token = row["token"]

    tampered = dict(payload)
    tampered["urgent"] = True          # 只改一個鍵
    bad = await redeem_token(pool, session_id, token, tampered)
    assert bad.ok is False and bad.error == "CONFIRMATION_REQUIRED"

    burned = await redeem_token(pool, session_id, token, payload)
    assert burned.ok is False and burned.error == "CONFIRMATION_REQUIRED", (
        "雜湊不符時 token 必須已被燒掉——留著可用等於允許反覆試 payload"
    )


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_reordered_payload_still_redeems(pool):
    """`canonical_json` 的 `sort_keys`：鍵順序不同、內容相同的 payload 仍兌現得到。

    ⛔ 這條不能鬆——鬆掉的話 payload 只要在序列化時換個順序（dict 來源不同、
    JSON 解析順序不同）就兌現不了，使用者按了確認卻永遠送不出去。
    """
    session_id = _session_id()
    payload = {"b": 2, "a": {"y": 1, "x": [3, "中文"]}}
    _, row = await _issue_token(pool, session_id, payload)
    reordered = {"a": {"x": [3, "中文"], "y": 1}, "b": 2}
    assert canonical_json(payload) == canonical_json(reordered)

    first = await redeem_token(pool, session_id, row["token"], reordered)
    assert first.ok is True, "換過鍵順序的同一份 payload 必須兌現得到"


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_sha256_shape_constraint_rejects_non_hash(pool):
    """migration 的 CHECK：雜湊欄位不是 64 字十六進位 ⇒ 寫不進去。"""
    session_id = _session_id()
    with pytest.raises(Exception, match="(?i)constraint|check"):
        await pool.execute(
            "INSERT INTO agent_confirmation_tokens "
            "(token, session_id, payload_sha256, summary_sha256, expires_at) "
            "VALUES ($1, $2, 'not-a-sha', $3, now() + interval '10 minutes')",
            "tok-" + uuid.uuid4().hex, session_id, sha256_hex("x"),
        )
    # 正對照組：形狀正確就寫得進去
    await pool.execute(
        "INSERT INTO agent_confirmation_tokens "
        "(token, session_id, payload_sha256, summary_sha256, expires_at) "
        "VALUES ($1, $2, $3, $4, now() + interval '10 minutes')",
        "tok-" + uuid.uuid4().hex, session_id, sha256_hex("a"), sha256_hex("b"),
    )


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_slots_set_round_trip_against_real_jsonb(pool):
    """`session.slots.set` 的 `jsonb_set` 在真 Postgres 上寫得進、讀得回、不蓋掉其他鍵。"""
    session_id = _session_id()
    await pool.execute(
        "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, "
        "current_field_index, collected_data) "
        "VALUES ($1,$2,$3,$4,'COLLECTING',0,$5::jsonb)",
        session_id, "1", 1, _CONVERSATIONAL_FORM_ID,
        '{"config_key": "test_cfg", "collected_fields": {"identity": "pm"}}',
    )

    identity = _identity(session_id)
    result = await slots_set(identity, {"key": "contract_ref", "value": "A1\n<B>"}, db_pool=pool)
    assert result.ok is True, result

    slots = await read_slots(pool, session_id)
    assert slots["contract_ref"] == {"value": "A1 B", "source": "tool", "confirmed": False}

    # 第二個槽位不得蓋掉第一個（jsonb_set 只動指定路徑）
    await slots_set(identity, {"key": "unit_count", "value": "600"}, db_pool=pool)
    slots = await read_slots(pool, session_id)
    assert set(slots) == {"contract_ref", "unit_count"}

    # 既有鍵原封不動（正對照組：證明我們沒把整包 collected_data 覆蓋掉）
    row = await pool.fetchrow(
        "SELECT collected_data FROM form_sessions WHERE session_id=$1", session_id
    )
    import json as _json
    collected = row["collected_data"]
    collected = _json.loads(collected) if isinstance(collected, str) else collected
    assert collected["config_key"] == "test_cfg"
    assert collected["collected_fields"] == {"identity": "pm"}


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_slots_set_without_conversational_session_returns_no_match(pool):
    """沒有進行中的對話會話 ⇒ `NO_MATCH`，⛔ 不靜默成功。"""
    session_id = _session_id()   # 刻意不插 form_sessions 列
    result = await slots_set(
        _identity(session_id), {"key": "bill_ref", "value": "B-1"}, db_pool=pool
    )
    assert result.ok is False and result.error == "NO_MATCH"
    assert await read_slots(pool, session_id) == {}
