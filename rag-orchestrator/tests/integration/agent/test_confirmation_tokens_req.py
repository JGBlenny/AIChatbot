"""integration：`agent_confirmation_tokens` 表與 token 兌現（agentic-mcp-orchestration 任務 2.4）。

真 DB：套 migration（冪等）→ `confirm.request` 寫一張 token →
兌現一次成功 → 第二次 `CONFIRMATION_REQUIRED`（冪等）→ 過期拒 → 跨 session 拒 →
payload 改一個鍵拒。無法連 DB → skip（非 fail）。測試列於 finally 清掉。

⚠️ 為什麼 `session.slots.set` 的 jsonb 寫入也在這一檔：那句 `jsonb_set(...)` 是
   本任務唯一沒有純 Python 對應物的東西——mock pool 只證明「我們傳了這些參數」，
   證明不了 Postgres 收得下、路徑建得對。故此處真跑一次來回。
"""
import json
import os
import uuid

import pytest

from services.agent.confirm_card import render as render_card
from services.agent.identity import Identity
from services.agent.tools.confirm import (
    assert_redeemed,
    canonical_json,
    confirm_quick_replies,
    confirm_request,
    payload_digest,
    pending_id_for,
    redeem_pending,
    redeem_token,
    sha256_hex,
)
from services.agent.tools.session import read_slots, slots_set

pytestmark = pytest.mark.integration

_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
)
#: 依序套（第二支 ALTER 第一支建的表）。兩支都冪等 ⇒ 可重入。
_MIGRATIONS = (
    "20260905_agent_confirmation_tokens.sql",
    "20260908_agent_confirmation_tokens_pending_id.sql",   # DSP-038-3
)

#: DSP-038-2：`payload` 必含 `action`（封閉值域）＋該 action 的完整欄位。
#: 本檔所有「合法」payload 一律由這個工廠產出。
def _payload(**overrides) -> dict:
    base = {
        "action": "bill_due_extend",
        "bill_id": "900001",
        "date_expire_before": "20260815",
        "days": 3,
        "date_expire_after": "20260818",
    }
    base.update(overrides)
    return base


def _card(payload: dict) -> str:
    return render_card(payload["action"], payload)
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
    for name in _MIGRATIONS:
        with open(os.path.join(_MIGRATIONS_DIR, name), encoding="utf-8") as f:
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
    """走真的 `confirm.request`，再從表裡把 token 撈回來（工具本身 ⛔ 不回 token）。

    ⚠️ 2.6 處置⑧：`confirm.request` 的 `payload` 已改成 **JSON 字串**（strict
    function calling 不吃開放 object）；兌現端 `redeem_token` 收到的仍是**物件**，
    兩邊都對 `canonical_json(dict)` 取雜湊，所以這裡序列化一次即可。
    """
    result = await confirm_request(
        _identity(session_id),
        {"summary": summary, "payload": json.dumps(payload, ensure_ascii=False)},
        db_pool=pool,
    )
    assert result.ok is True, result
    row = await pool.fetchrow(
        "SELECT token, pending_id, payload_sha256, summary_sha256, redeemed, "
        "       expires_at > now() AS alive "
        "FROM agent_confirmation_tokens WHERE session_id = $1", session_id,
    )
    assert row is not None, "confirm.request 應該寫進一列（正對照組）"
    return result, row


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_confirm_request_writes_hashes_only_and_hides_token(pool):
    """表裡只有雜湊；`ToolResult` 完全不含 token。"""
    session_id = _session_id()
    payload = _payload(bill_id="900042")
    result, row = await _issue_token(pool, session_id, payload)

    assert row["payload_sha256"] == payload_digest(payload)
    # DSP-038-2：`summary_sha256` ＝**確認卡文字**的雜湊，⛔ 不是模型 summary 的雜湊
    assert row["summary_sha256"] == sha256_hex(_card(payload))
    assert row["summary_sha256"] != sha256_hex("確認送出這筆")
    assert row["redeemed"] is False
    assert row["alive"] is True
    # 原文 ⛔ 不落地（帳單編號在卡上、在 payload 裡，但表只存雜湊）
    assert "900042" not in canonical_json(dict(row))
    # token ⛔ 不回給模型
    assert row["token"] not in result.model_dump_json()
    assert result.data["pending_id"] == pending_id_for(row["token"])
    # DSP-038-3：`pending_id` 落表（供 `redeem_pending` 當查詢鍵）
    assert row["pending_id"] == result.data["pending_id"]
    # DSP-038-2：`data.card` 逐字＝程式產出的卡；三顆機器值帶 pending_id
    assert result.data["card"] == _card(payload)
    assert result.data["quick_replies"] == confirm_quick_replies(row["pending_id"])


@pytest.mark.req("agentic-mcp-orchestration:2.4")
async def test_redeem_succeeds_once_then_is_idempotently_refused(pool):
    session_id = _session_id()
    payload = _payload()
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
    payload = _payload()
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
    payload = _payload()
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
    payload = _payload()
    _, row = await _issue_token(pool, session_id, payload)
    token = row["token"]

    tampered = dict(payload)
    tampered["bill_id"] = "900002"     # 只改一個鍵
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
    payload = _payload()
    _, row = await _issue_token(pool, session_id, payload)
    reordered = dict(reversed(list(payload.items())))
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


# ═══════════════════════════════════════════════════════════════════
# DSP-038（子 spec agent-write-tools W2／W3）：pending_id 兌現與 Runtime 確認段
#
# 這一段跑的是**真 DB＋真 ToolRegistry＋真 confirm.request**，只有兩件事是替身：
#   ・provider（模型）——腳本化，讓它在該呼叫 `confirm.request` 的地方呼叫；
#   ・`jgb2.action.bill_due_extend` 的 **handler**——回一張 receipt（真 handler 是
#     W4 的事，見 `tests/unit/agent/test_action_tools_req.py`）。
# 於是 `mcp_only`／`entry`／旗標／stage 四道閘、單述句兌現、雜湊比對，
# 以及 `register()` 強制包上的**寫入 wrapper**（`assert_redeemed`＋pm 雙證，S-8／S-9）
# 全都是真的——替身只有那一顆最裡面的 handler。
# ═══════════════════════════════════════════════════════════════════
import logging
from types import SimpleNamespace

from services.agent.budget import Budget
from services.agent.confirm_card import ACTION_FAILED_TEXT, CANCELLED_TEXT, CONFIRMATION_REQUIRED_TEXT
from services.agent.runtime import PENDING_CONFIRM_KEY, AgentRuntime
from services.agent.tools.confirm import CONFIRM_SPEC
from services.agent.tools.registry import ToolRegistry, ToolResult

_ACTION_NAME = "jgb2.action.bill_due_extend"
_ACTION_SPEC = {
    "name": _ACTION_NAME,
    "description": "延後帳單到期日（替身）",
    "input_schema": {
        "type": "object",
        "properties": {
            "payload": {"type": "object"},
            "confirmation_token": {"type": "string"},
        },
        "required": ["payload", "confirmation_token"],
    },
    "scope": "write",
    "mcp_only": True,                       # DSP-038-1
    "stage": {"property_manager": "M1", "tenant": "M4"},
}


class _ScriptedProvider:
    """`provider.async_client.chat.completions.create(**kwargs)`；腳本耗盡即斷言失敗。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        completions = SimpleNamespace(create=self._create)
        self.async_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        assert self.script, "假 provider 腳本已耗盡——這一步不該再叫模型"
        return self.script.pop(0)


def _confirm_call_response(payload: dict):
    tool_call = SimpleNamespace(
        id="call_confirm_1",
        function=SimpleNamespace(
            name="confirm.request",
            arguments=json.dumps(
                {"summary": "模型自己寫的摘要（⛔ 不會成為卡）",
                 "payload": json.dumps(payload, ensure_ascii=False)},
                ensure_ascii=False,
            ),
        ),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tool_call]))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )


class _StubAssembler:
    def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
        return [{"role": "system", "content": "persona"}]


class _StubVerifier:
    rules_sha = "stub"

    def __init__(self):
        self.calls = []

    def verify(self, out, tool_results, user_message, handoff, *, resolved, resolve_errors):
        from services.agent.output_schema import VerifierVerdict

        self.calls.append(out)
        return VerifierVerdict(ok=True)


def _mcp_identity(session_id: str) -> Identity:
    return Identity(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="1", session_id=session_id, api_key_id=1,
        entry="mcp",
    )


def _build_registry(pool, *, action_result=None, calls=None):
    from services.agent.tools.confirm import assert_redeemed as _assert_redeemed
    from services.agent.tools.confirm import confirm_request as _confirm_request

    # DSP-038／S-9：`register()` 對 `scope=="write"` 會**強制**包上共用 wrapper
    # （兌現查核＋pm 雙證）。這裡綁**真的** `assert_redeemed`（真 DB、真 token 表）
    # ⇒ 「Runtime 先燒、工具再確認燒過」這條鏈整條是真的，
    # ⛔ 不用恆真替身——那會讓 wrapper 這一道閘在本檔完全沒被驗到。
    async def _redeem_checker(token, session_id):
        return await _assert_redeemed(pool, token, session_id)

    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=_redeem_checker)

    async def _confirm(identity, args):
        return await _confirm_request(identity, args, db_pool=pool)

    async def _action(identity, args):
        if calls is not None:
            calls.append(args)
        return action_result or ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}})

    reg.register(CONFIRM_SPEC, _confirm)
    reg.register(_ACTION_SPEC, _action)
    return reg


def _build_runtime(pool, registry, *, provider=None, readonly_view=False, verifier=None):
    return AgentRuntime(
        provider or _ScriptedProvider([]),
        registry,
        verifier or _StubVerifier(),
        _StubAssembler(),
        Budget(),
        stage="M1",
        db_pool=pool,
        readonly_view=readonly_view,
    )


async def _confirm_turn(pool, session_id, *, calls=None, action_result=None, verifier=None):
    """真跑一次「確認回合」：模型呼叫 `confirm.request` ⇒ 回合以卡結束。

    回傳 `(runtime, state, result, row, registry)`。
    """
    payload = _payload()
    registry = _build_registry(pool, action_result=action_result, calls=calls)
    verifier = verifier or _StubVerifier()
    runtime = _build_runtime(
        pool, registry, provider=_ScriptedProvider([_confirm_call_response(payload)]),
        verifier=verifier,
    )
    state: dict = {}
    result = await runtime.run_turn(
        _mcp_identity(session_id), "900001 逾期了，幫我延 3 天", state
    )
    row = await pool.fetchrow(
        "SELECT token, pending_id, summary_sha256, redeemed FROM agent_confirmation_tokens "
        "WHERE session_id = $1", session_id,
    )
    return runtime, state, result, row, registry


# ── W2：redeem_pending 三態 ＋ assert_redeemed ──────────────────────


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_redeem_pending_three_states(pool):
    """① 第一次中、② 第二次沒中（已燒）、③ 跨 session 沒中。四種沒中共用同一個回傳值。"""
    session_a, session_b = _session_id(), _session_id()
    payload = _payload()
    result, row = await _issue_token(pool, session_a, payload)
    pid = row["pending_id"]

    first = await redeem_pending(pool, session_a, pid)
    assert first is not None, "第一次兌現必須成功（正對照組）"
    assert first.token == row["token"]
    assert first.payload_sha256 == payload_digest(payload)
    assert first.summary_sha256 == sha256_hex(_card(payload))

    assert await redeem_pending(pool, session_a, pid) is None      # ② 已燒

    # ③ 跨 session：另開一張新 token，用別的 session 兌現不了
    _, row_b = await _issue_token(pool, session_b, payload)
    assert await redeem_pending(pool, session_a, row_b["pending_id"]) is None
    # 正對照組：合法 session 兌現得到 ⇒ 上面的 None 來自 session 不符
    assert await redeem_pending(pool, session_b, row_b["pending_id"]) is not None


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_redeem_pending_rejects_expired_and_bad_shapes(pool):
    session_id = _session_id()
    _, row = await _issue_token(pool, session_id, _payload())
    pid = row["pending_id"]

    # 形狀不合 ⇒ 連查都不查（fail-closed）
    for bad in ("", "not-hex", pid.upper(), pid + "0", None, 123):
        assert await redeem_pending(pool, session_id, bad) is None, bad

    await pool.execute(
        "UPDATE agent_confirmation_tokens SET expires_at = now() - interval '1 second' "
        "WHERE pending_id = $1", pid,
    )
    assert await redeem_pending(pool, session_id, pid) is None
    still = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert still["redeemed"] is False, "過期的 token ⛔ 不得被標成已兌現"


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_assert_redeemed_only_true_after_redemption(pool):
    """W4 的 wrapper 用：兌現前 False、兌現後 True、換 session False。"""
    session_id = _session_id()
    _, row = await _issue_token(pool, session_id, _payload())
    token, pid = row["token"], row["pending_id"]

    assert await assert_redeemed(pool, token, session_id) is False
    assert await redeem_pending(pool, session_id, pid) is not None
    assert await assert_redeemed(pool, token, session_id) is True      # 正對照組
    assert await assert_redeemed(pool, token, _session_id()) is False
    assert await assert_redeemed(pool, "not-a-token", session_id) is False


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_pending_id_backfill_matches_python_digest(pool):
    """migration 的回填式（SQL `sha256`）必須與 `pending_id_for`（Python）逐位元相同。"""
    session_id = _session_id()
    token = "tok-" + uuid.uuid4().hex
    await pool.execute(
        "INSERT INTO agent_confirmation_tokens "
        "(token, session_id, payload_sha256, summary_sha256, expires_at) "
        "VALUES ($1, $2, $3, $4, now() + interval '10 minutes')",
        token, session_id, sha256_hex("a"), sha256_hex("b"),
    )
    row = await pool.fetchrow(
        "SELECT left(encode(sha256(convert_to(token, 'UTF8')), 'hex'), 16) AS sql_pid "
        "FROM agent_confirmation_tokens WHERE token = $1", token,
    )
    assert row["sql_pid"] == pending_id_for(token)


# ── W3：正向 ──────────────────────────────────────────────────────


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_confirm_turn_answer_is_the_card_and_matches_summary_sha256(pool):
    """卡逐字成為使用者看到的答案，且 `sha256(answer)` ＝ 表裡的 `summary_sha256`。

    ⚠️ 反例＝採用模型輸出：模型送的 `summary` 是「模型自己寫的摘要（⛔ 不會成為卡）」，
    下面第二條斷言會紅。
    """
    session_id = _session_id()
    verifier = _StubVerifier()
    _, state, result, row, _ = await _confirm_turn(pool, session_id, verifier=verifier)

    assert result.kind == "ask"
    assert result.answer == _card(_payload())
    assert sha256_hex(result.answer) == row["summary_sha256"]
    assert "模型自己寫的摘要" not in result.answer
    assert verifier.calls == [], "確認回合 ⛔ 不跑 Verifier"
    assert result.trace.pending_id == row["pending_id"]
    assert result.quick_replies == confirm_quick_replies(row["pending_id"])
    assert state["agent"][PENDING_CONFIRM_KEY][row["pending_id"]]["card_sha256"] == (
        row["summary_sha256"]
    )


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_submit_redeems_and_returns_receipt(pool):
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]

    result = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)

    assert result.answer == "已將帳單 900001 的到期日延至 2026/08/18。（單號 BILL-77）"
    assert result.trace.llm_calls == 0, "兌現段 ⛔ 不進模型"
    assert result.trace.receipt_id == "BILL-77"
    assert len(calls) == 1
    assert calls[0]["confirmation_token"] == row["token"]   # 行程內交付，⛔ 不落地
    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is True
    assert state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"] == {"id": "BILL-77"}


# ── W3：反向五條 ──────────────────────────────────────────────────


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
@pytest.mark.parametrize("verb", ["confirm_cancel", "confirm_edit"])
async def test_reverse_1_cancel_and_edit_burn_without_writing(pool, verb):
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]

    result = await runtime.run_turn(_mcp_identity(session_id), f"{verb}:{pid}", state)

    assert result.answer == CANCELLED_TEXT
    assert calls == [], "取消／修改 ⛔ 不得呼叫寫入工具"
    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is True, "取消也要把 token 燒掉"
    assert state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"] == {"cancelled": True}


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_reverse_2_resend_returns_the_same_receipt_once(pool):
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]

    first = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)
    second = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)

    assert second.answer == first.answer
    assert len(calls) == 1, "重送 ⛔ 不得再寫一次（R4.3）"


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
@pytest.mark.parametrize("message", ["好，送出", "confirm_submit", "confirm_submit:{other}"])
async def test_reverse_3_free_text_and_wrong_pid_do_not_redeem(pool, message):
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]
    text = message.format(other="0" * 16)

    # 這些訊息會照常進模型；腳本再給一個「最終輸出」讓回合走得完。
    runtime.provider.script.append(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"kind": "answer",
                                    "sentences": [{"text": "請按按鈕。", "kind": "greeting", "refs": []}],
                                    "fact_class": "feature", "handoff_reason": None}),
                tool_calls=None))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )
    )
    await runtime.run_turn(_mcp_identity(session_id), text, state)

    assert calls == [], f"{text!r} ⛔ 不得觸發寫入"
    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is False, f"{text!r} ⛔ 不得燒掉 token"


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_reverse_4_expired_token_requires_reconfirmation(pool):
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]
    await pool.execute(
        "UPDATE agent_confirmation_tokens SET expires_at = now() - interval '1 second' "
        "WHERE pending_id = $1", pid,
    )

    result = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)

    assert result.answer == CONFIRMATION_REQUIRED_TEXT
    assert calls == []
    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is False


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_reverse_5_tool_failure_is_honest_and_token_is_already_burned(pool):
    """S-12：token 已燒是刻意的——要再做一次就得重新確認。"""
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, _ = await _confirm_turn(
        pool, session_id, calls=calls,
        action_result=ToolResult(ok=False, error="TOOL_TIMEOUT"),
    )
    pid = row["pending_id"]

    result = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)

    assert result.answer == ACTION_FAILED_TEXT
    assert state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"] == {"error": "TOOL_TIMEOUT"}
    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is True


# ── W3：兩條隔離（DB 可反證） ──────────────────────────────────────


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_isolation_shadow_runtime_never_updates_the_row(pool):
    """影子（`readonly_view=True`）收同一句 ⇒ DB 0 次 UPDATE。
    正對照＝同一份狀態換成正式 Runtime 就兌現得到。"""
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, registry = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]

    shadow = _build_runtime(pool, registry, readonly_view=True,
                            provider=_ScriptedProvider([
                                SimpleNamespace(
                                    choices=[SimpleNamespace(message=SimpleNamespace(
                                        content=json.dumps({
                                            "kind": "answer",
                                            "sentences": [{"text": "影子。", "kind": "greeting", "refs": []}],
                                            "fact_class": "feature", "handoff_reason": None}),
                                        tool_calls=None))],
                                    usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
                                )
                            ]))
    await shadow.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", dict(state))

    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is False, "影子回合 ⛔ 不得兌現"
    assert calls == []

    # 正對照組
    ok = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)
    assert "BILL-77" in ok.answer
    after2 = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after2["redeemed"] is True


@pytest.mark.req("agentic-mcp-orchestration:R4.4")
async def test_isolation_rest_entry_cannot_redeem_the_same_session_string(pool):
    """S-6／S-7 的緩解本身：REST 身分帶**同一個字串** `session_id` 送同一個 pid
    ⇒ 該列 `redeemed=false` 不變、狀態無 receipt、`specs_for` 不含寫入工具。"""
    session_id = _session_id()
    calls: list = []
    runtime, state, _, row, registry = await _confirm_turn(pool, session_id, calls=calls)
    pid = row["pending_id"]

    rest_identity = Identity(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="1", session_id=session_id, api_key_id=1,
    )   # ⚠️ 刻意不帶 entry ⇒ 落預設 "rest"
    assert rest_identity.entry == "rest"
    assert _ACTION_NAME not in {
        s["name"] for s in registry.specs_for(rest_identity, "M1", for_model=True)
    }
    # 正對照組：同一個 registry、同一個 stage，MCP 身分看得到
    assert _ACTION_NAME in {
        s["name"] for s in registry.specs_for(_mcp_identity(session_id), "M1", for_model=True)
    }

    rest_state = dict(state)
    runtime.provider.script.append(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"kind": "answer",
                                    "sentences": [{"text": "請按按鈕。", "kind": "greeting", "refs": []}],
                                    "fact_class": "feature", "handoff_reason": None}),
                tool_calls=None))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )
    )
    await runtime.run_turn(rest_identity, f"confirm_submit:{pid}", rest_state)

    after = await pool.fetchrow(
        "SELECT redeemed FROM agent_confirmation_tokens WHERE pending_id=$1", pid
    )
    assert after["redeemed"] is False, "REST 入口 ⛔ 不得兌現"
    assert calls == []
    assert "receipt" not in rest_state["agent"][PENDING_CONFIRM_KEY][pid]

    # 正對照組：同一個 pid 由 MCP 身分送出，兌現得到 receipt
    ok = await runtime.run_turn(_mcp_identity(session_id), f"confirm_submit:{pid}", state)
    assert "BILL-77" in ok.answer


# ── W3：token 不變量 ──────────────────────────────────────────────


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_token_never_leaves_the_process(pool, caplog):
    """跑完一次「確認＋兌現」，token 不得出現在狀態快照／TurnResult／trace／log。
    **正對照組＝`pending_id` 找得到**（證明這幾份 blob 真的有內容可搜）。"""
    session_id = _session_id()
    with caplog.at_level(logging.DEBUG):
        runtime, state, card_result, row, _ = await _confirm_turn(pool, session_id)
        pid = row["pending_id"]
        submit_result = await runtime.run_turn(
            _mcp_identity(session_id), f"confirm_submit:{pid}", state
        )
    token = row["token"]
    assert isinstance(token, str) and len(token) >= 40   # 正對照組：token 真的存在

    blobs = {
        "state": json.dumps(state, ensure_ascii=False, default=str),
        "card_result": json.dumps(card_result.__dict__, ensure_ascii=False, default=str),
        "submit_result": json.dumps(submit_result.__dict__, ensure_ascii=False, default=str),
        "card_trace": json.dumps(card_result.trace.__dict__, ensure_ascii=False, default=str),
        "submit_trace": json.dumps(submit_result.trace.__dict__, ensure_ascii=False, default=str),
        "caplog": caplog.text,
    }
    for name, blob in blobs.items():
        assert token not in blob, f"token 外洩到 {name}"
    assert any(pid in blob for blob in blobs.values()), "正對照組：pending_id 應該找得到"


# ── W4：**真** `jgb2.action.*` handler 端到端（Runtime → wrapper → 替身）────────
#
# ⚠️ 上面每一條的最裡層 handler 都是替身（回一張假 receipt）。這一段把它換成
# `services/agent/tools/action.py` 的**真** handler ＋ 真 `JGBSystemAPI`
# （`JGBMockTransport`，純記憶體 fixture）⇒ 整條鏈只剩「模型」是腳本化的：
#   Runtime 確認段 → `redeem_pending`（真 DB 單述句）→ `registry.call`
#   → `register()` 強制包的寫入 wrapper（真 `assert_redeemed`，真 DB）
#   → 真 handler（範圍讀 → `PATCH /agent/v1/bills/{id}`）→ receipt → 決定性回覆句。
# ⛔ 這一段不得改用假 handler——它存在的理由就是「真 handler 也走得通」。


def _mcp_identity_with_viewer(session_id: str) -> Identity:
    """demo fixture 的 pm 身分：`user_id=9001` 在 `bill_visibility` 裡宣告可見（合成凍結鏈；demo 用戶 12291 只看真資料列）。

    ⚠️ 與上面的 `_mcp_identity`（`user_id="1"`）刻意不同：真 handler 會做**範圍讀**
    （`get_bills(viewer_user_id=...)`），`user_id="1"` 對 900001 未宣告可見 ⇒ 會被
    正確地擋成 `NO_MATCH`。⛔ 不要為了讓測試變綠而改寬替身的可見性宣告。
    """
    return Identity(
        vendor_id=4, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="9001", session_id=session_id, api_key_id=1,
        entry="mcp",
    )


def _real_action_registry(pool, api):
    """真 action 工具 ＋ 真 `assert_redeemed`（`register()` 會強制包上 wrapper）。"""
    from services.agent.tools import action as action_tools
    from services.agent.tools.confirm import assert_redeemed as _assert_redeemed
    from services.agent.tools.confirm import confirm_request as _confirm_request

    async def _redeem_checker(token, session_id):
        return await _assert_redeemed(pool, token, session_id)

    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=_redeem_checker)

    async def _confirm(identity, args):
        return await _confirm_request(identity, args, db_pool=pool)

    reg.register(CONFIRM_SPEC, _confirm)
    for spec, fn in action_tools.ACTION_SPECS:
        reg.register(spec, fn)
    return reg


@pytest.fixture()
def mock_api(monkeypatch):
    from services.agent.tools import jgb2 as jgb2_tools
    from services.jgb_system_api import JGBSystemAPI

    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    api = JGBSystemAPI()
    monkeypatch.setattr(jgb2_tools, "_api_singleton", api)
    return api


async def _confirm_then_submit(pool, api, session_id, payload, *, fail_next=False):
    registry = _real_action_registry(pool, api)
    runtime = _build_runtime(
        pool, registry, provider=_ScriptedProvider([_confirm_call_response(payload)]),
    )
    state: dict = {}
    card_turn = await runtime.run_turn(
        _mcp_identity_with_viewer(session_id), "幫我處理這一筆", state
    )
    row = await pool.fetchrow(
        "SELECT pending_id FROM agent_confirmation_tokens WHERE session_id = $1",
        session_id,
    )
    if fail_next:
        api._mock_transport.fail_next_write = True
    submit = await runtime.run_turn(
        _mcp_identity_with_viewer(session_id),
        f"confirm_submit:{row['pending_id']}", state,
    )
    return card_turn, submit, state, row["pending_id"]


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_real_bill_due_extend_writes_through_to_the_mock_backend(pool, mock_api):
    session_id = _session_id()
    payload = _payload()
    before = mock_api._mock_transport.fixtures.by_id(900001)["date_expire"]
    assert before == 20260815, "前提：替身的起始到期日就是卡上那一天"

    card_turn, submit, state, pid = await _confirm_then_submit(
        pool, mock_api, session_id, payload
    )

    assert card_turn.answer == _card(payload)
    assert submit.trace.llm_calls == 0, "兌現段 ⛔ 不進模型"
    assert submit.answer == "已將帳單 900001 的到期日延至 2026/08/18。（單號 900001）"
    assert submit.trace.receipt_id == "900001"
    # 替身**真的**被改到（⛔ 不只是回了一句好聽的話）
    assert mock_api._mock_transport.fixtures.by_id(900001)["date_expire"] == 20260818
    receipt = state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"]
    assert receipt == {"bill_id": "900001", "before": "2026-08-15", "after": "2026-08-18"}


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_real_action_resend_returns_same_receipt_and_writes_once(pool, mock_api):
    """R4.3：重送同一個 `pending_id` ⇒ 同一句、同一份 receipt，替身只變一次。"""
    session_id = _session_id()
    _, submit, state, pid = await _confirm_then_submit(
        pool, mock_api, session_id, _payload()
    )
    registry_state = state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"]

    runtime = _build_runtime(pool, _real_action_registry(pool, mock_api))
    again = await runtime.run_turn(
        _mcp_identity_with_viewer(session_id), f"confirm_submit:{pid}", state
    )
    assert again.answer == submit.answer
    assert state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"] == registry_state
    assert mock_api._mock_transport.fixtures.by_id(900001)["date_expire"] == 20260818


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_real_action_downstream_failure_is_honest_and_leaves_no_write(pool, mock_api):
    """替身注入失敗 ⇒ 誠實固定句、無殘留變更、狀態記 error（S-12：token 已燒是刻意）。"""
    session_id = _session_id()
    _, submit, state, pid = await _confirm_then_submit(
        pool, mock_api, session_id, _payload(), fail_next=True
    )
    assert submit.answer == ACTION_FAILED_TEXT
    assert mock_api._mock_transport.fixtures.by_id(900001)["date_expire"] == 20260815
    assert state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"] == {"error": "NO_MATCH"}


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_real_repair_create_accepts_parent_category_and_empty_description(pool, mock_api):
    """line-bot 線③：父節點分類＋空描述照樣開得成單，且單號進 trace。"""
    session_id = _session_id()
    payload = {"action": "repair_create", "estate_name": "信義區套房A",
               "category_name": "家電維修", "description": "",
               "emergency_status": 2}
    before = len(mock_api._mock_transport.repair_fixtures.rows())

    _, submit, state, pid = await _confirm_then_submit(
        pool, mock_api, session_id, payload
    )

    assert submit.answer.startswith("已為「信義區套房A」建立修繕單。（單號 ")
    assert len(mock_api._mock_transport.repair_fixtures.rows()) == before + 1
    assert submit.trace.receipt_id == state["agent"][PENDING_CONFIRM_KEY][pid]["receipt"]["repair_id"]


@pytest.mark.req("agentic-mcp-orchestration:R4.2")
async def test_real_action_blocks_bill_outside_viewer_scope(pool, mock_api):
    """範圍讀是真的：`user_id` 未被宣告可見 ⇒ NO_MATCH，且替身無變更。

    正對照組＝上面 `test_real_bill_due_extend_writes_through_to_the_mock_backend`
    （同一份 payload、同一條路，只差 `user_id`）⇒ 這裡的失敗不是路本身壞了。
    """
    session_id = _session_id()
    payload = _payload()
    registry = _real_action_registry(pool, mock_api)
    runtime = _build_runtime(
        pool, registry, provider=_ScriptedProvider([_confirm_call_response(payload)]),
    )
    identity = Identity(
        vendor_id=4, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="9002", session_id=session_id, api_key_id=1,
        entry="mcp",
    )
    state: dict = {}
    await runtime.run_turn(identity, "幫我處理這一筆", state)
    row = await pool.fetchrow(
        "SELECT pending_id FROM agent_confirmation_tokens WHERE session_id = $1",
        session_id,
    )
    submit = await runtime.run_turn(
        identity, f"confirm_submit:{row['pending_id']}", state
    )
    assert submit.answer == ACTION_FAILED_TEXT
    assert mock_api._mock_transport.fixtures.by_id(900001)["date_expire"] == 20260815
