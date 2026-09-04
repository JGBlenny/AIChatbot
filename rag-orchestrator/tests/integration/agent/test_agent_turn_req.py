"""integration：`agent.turn` 走真 MCP client ＋ 真測試庫（任務 2.6）。

真測試庫（`form_sessions`／`api_keys`／`usage_events`）＋真 MCP SDK；
**只有 LLM 是假的**（腳本化 provider，⛔ 不呼叫真 OpenAI）。Verifier 是**真的**
（`bootstrap.build_runtime` 載入 `config/agent_verifier_rules.json` 並跑過自證）。

涵蓋 tasks 2.6「測試：整合」四案 ＋ 計量一案：
① MCP client 兩回合對話，第二回合看得到第一回合留下的 session 狀態（slots）
② **同 `session_id` 不同 vendor（兩把 key）⇒ 讀不到前回合 slots，且原列不改**
   （前置 security review 的唯一 P1 驗收句）
③ prospect 以外身分 ⇒ `NO_MATCH`
④ Verifier 拒兩次 ⇒ 固定句＋handoff、⛔ 回應不含被拒文字
⑤ 一回合後 `usage_events` 恰一列且 `prompt_tokens > 0`

清理：本檔寫入的 `api_keys`／`usage_events`／`form_sessions` 一律在 finally 依
名稱／前綴刪除；開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import asyncio
import json
import os
import uuid
from types import SimpleNamespace

import pytest

from services.agent import mcp_facade as F
from services.agent.bootstrap import build_runtime
from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry
from services.api_key_auth import _reset_agent_scope_detection, hash_key
from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:2.6"

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260904_api_keys_agent_scope.sql",
)

_KEY_NAME_A = "test-agent-turn-2-6-vendor1"
_KEY_NAME_B = "test-agent-turn-2-6-vendor2"
_PLAIN_KEY_A = "agent-turn-integration-key-vendor-one"
_PLAIN_KEY_B = "agent-turn-integration-key-vendor-two"
_SESSION_PREFIX = "backtest_agentturn26_"
#: `form_sessions` 清理用：本檔建的列一律以命名空間前綴開頭。
_ROW_PREFIX = "mcp:"

VENDOR_A = 1
VENDOR_B = 2


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg

    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=4)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"測試 DB 不可達（{type(e).__name__}）→ agent.turn 整合測試未驗")
        return

    with open(_MIGRATION, encoding="utf-8") as f:
        await p.execute(f.read())
    _reset_agent_scope_detection()

    # 正對照組：vendors 必須有 1 與 2，否則「跨業者隔離」根本無從證明
    present = await p.fetchval(
        "SELECT count(*) FROM vendors WHERE id = ANY($1::int[])", [VENDOR_A, VENDOR_B])
    if present != 2:
        pytest.skip(f"[env] 測試庫 vendors 缺 {VENDOR_A}／{VENDOR_B}（實得 {present}）")
    # 正對照組：`form_sessions` 的 form_id 外鍵指向的那一列必須存在
    assert await p.fetchval(
        "SELECT 1 FROM form_schemas WHERE form_id = 'conversational'"), \
        "form_schemas 缺 'conversational'——`_start` 會因外鍵而失敗"

    await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                    [_KEY_NAME_A, _KEY_NAME_B])
    for name, plain, vendor in ((_KEY_NAME_A, _PLAIN_KEY_A, VENDOR_A),
                                (_KEY_NAME_B, _PLAIN_KEY_B, VENDOR_B)):
        await p.execute(
            "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
            " VALUES ($1,$2,$3,TRUE,FALSE,$4::int[])",
            name, hash_key(plain), plain[:8], [vendor])

    try:
        yield p
    finally:
        await p.execute("DELETE FROM api_keys WHERE name = ANY($1::text[])",
                        [_KEY_NAME_A, _KEY_NAME_B])
        await p.execute("DELETE FROM usage_events WHERE session_id LIKE $1",
                        _SESSION_PREFIX + "%")
        await p.execute("DELETE FROM form_sessions WHERE session_id LIKE $1",
                        _ROW_PREFIX + "%" + _SESSION_PREFIX + "%")
        await p.close()
        _reset_agent_scope_detection()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    monkeypatch.setenv("AGENT_STAGE", "M1")
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "30")
    monkeypatch.setenv("AGENT_TURN_CAP", "500")
    F.reset_agent_turn_cap()
    F.reset_premise_stats()


# ════════════════════════════════════════════════════════════════════
# 假 provider（⛔ 不呼叫真 OpenAI）與真組裝
# ════════════════════════════════════════════════════════════════════
def _fake_response(content: str, *, prompt_tokens=137, completion_tokens=42):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def _agent_output(*, kind="answer", answer="您好。", fact_class="feature",
                  handoff_reason=None) -> str:
    """`AgentOutput` 的 JSON 字串。預設是一句**問候句**——真 Verifier 的白名單
    句型裡問候句不需要引用，故這是最小的「會被放行」的輸出。"""
    sents = [s for s in answer.split("。") if s]
    return json.dumps({
        "kind": kind, "answer": answer, "citations": [],
        "sentence_map": [{"sent": i, "kind": "greeting", "cite": []}
                         for i in range(len(sents))],
        "fact_class": fact_class, "handoff_reason": handoff_reason,
    }, ensure_ascii=False)


class FakeProvider:
    def __init__(self, script):
        self.script = list(script)
        self.calls: list = []
        outer = self

        class _Completions:
            async def create(self, **kwargs):
                outer.calls.append(kwargs)
                assert outer.script, "假 provider 腳本已耗盡——測試少寫了一步"
                return outer.script.pop(0)

        self.async_client = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))


def _engine(pool):
    """最小引擎：**沿用 `ConversationalEngine` 的三個狀態方法本體**（同一張表、
    同一組 SQL）。⛔ 不在測試裡另寫一份 SQL——那樣測的就不是產品那條路了。"""

    class _Engine:
        db_pool = pool
        get_state = ConversationalEngine.get_state
        _start = ConversationalEngine._start
        _save = ConversationalEngine._save

    return _Engine()


def _make_runtime(pool, script):
    """真 Verifier（含自證）＋真 PromptAssembler ＋假 provider。"""
    return build_runtime(pool, FakeProvider(script), ToolRegistry(), budget=None)


def _app(pool, runtime):
    state = SimpleNamespace(agent_runtime=runtime, conversational_engine=_engine(pool),
                            db_pool=pool)
    return SimpleNamespace(state=state)


def _deps(app, pool):
    return F.FacadeDeps(get_db_pool=lambda: pool, get_kb_pool=lambda: None,
                        get_app=lambda: app, stage="M1")


def _registry(deps) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    return reg


class _FakeCtx:
    def __init__(self, headers):
        self.headers = headers


def _ident(vendor_id, session_id, target_user="prospect", mode="b2c"):
    return json.dumps({"vendor_id": vendor_id, "session_id": session_id,
                       "target_user": target_user, "mode": mode}, ensure_ascii=False)


def _session():
    return _SESSION_PREFIX + uuid.uuid4().hex[:12]


async def _count_events(pool, session_id):
    return await pool.fetchval(
        "SELECT count(*) FROM usage_events WHERE session_id = $1", session_id)


async def _wait_for_events(pool, session_id, expected, timeout_s=8.0):
    """`finalize` 是 fire-and-forget（create_task）⇒ 輪詢等它落地，
    再多等一段確認**沒有多餘的列**偷偷落地。"""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        if await _count_events(pool, session_id) >= expected:
            break
        await asyncio.sleep(0.15)
    await asyncio.sleep(0.5)
    return await _count_events(pool, session_id)


async def _row(pool, key):
    return await pool.fetchrow(
        "SELECT collected_data FROM form_sessions "
        "WHERE session_id=$1 AND form_id='conversational' AND state='COLLECTING' "
        "ORDER BY id DESC LIMIT 1", key)


async def _state(pool, key):
    """該命名空間鍵目前的 `collected_data`（asyncpg 可能回 str 或 dict）。"""
    row = await _row(pool, key)
    if row is None:
        return None
    cd = row["collected_data"]
    return json.loads(cd) if isinstance(cd, str) else cd


async def _api_key_id(pool, name):
    return await pool.fetchval("SELECT id FROM api_keys WHERE name = $1", name)


# ════════════════════════════════════════════════════════════════════
# ⑤ 一回合 ⇒ 恰一列 usage_events 且 prompt_tokens > 0
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_one_turn_writes_exactly_one_event_with_prompt_tokens(pool, env):
    """處置④：Runtime 的 LLM 呼叫要經 `usage_metering.add_llm_usage` 灌回事件層，
    否則 `/mcp` 這條路徑的 token／費用完全量不到（內部 key 又免額度）。"""
    session_id = _session()
    assert await _count_events(pool, session_id) == 0, "起跑前該 session 就有事件——區間不乾淨"

    runtime = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))])
    deps = _deps(_app(pool, runtime), pool)
    invoke = F._make_invoke(_registry(deps), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY_A,
                    "x-jgb-identity": _ident(VENDOR_A, session_id)})

    out = await invoke(F.AGENT_TURN_NAME, ctx, {"message": "你好"})
    assert out["kind"] == "answer" and out["answer"] == "您好。"

    assert await _wait_for_events(pool, session_id, 1) == 1
    row = await pool.fetchrow(
        "SELECT prompt_tokens, completion_tokens, llm_calls, channel, processing_path "
        "FROM usage_events WHERE session_id = $1", session_id)
    assert row["prompt_tokens"] > 0, "LLM token 沒進事件層 ⇒ 處置④ 沒生效"
    assert row["completion_tokens"] > 0
    assert row["llm_calls"] == 1
    assert row["channel"] == "mcp"
    assert row["processing_path"] == f"mcp:{F.AGENT_TURN_NAME}"


# ════════════════════════════════════════════════════════════════════
# ② 同 session_id 不同 vendor（兩把 key）⇒ 隔離（前置 security review P1）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_same_session_id_different_vendor_is_isolated(pool, env):
    session_id = _session()
    key_a_id = await _api_key_id(pool, _KEY_NAME_A)
    key_b_id = await _api_key_id(pool, _KEY_NAME_B)
    assert key_a_id and key_b_id and key_a_id != key_b_id

    row_key_a = f"mcp:{key_a_id}:{VENDOR_A}:{session_id}"
    row_key_b = f"mcp:{key_b_id}:{VENDOR_B}:{session_id}"

    # ── A 業者跑一回合，並在列上留下 slots ────────────────────────────
    runtime_a = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))])
    app_a = _app(pool, runtime_a)
    deps_a = _deps(app_a, pool)
    invoke_a = F._make_invoke(_registry(deps_a), deps_a)
    await invoke_a(F.AGENT_TURN_NAME, _FakeCtx(
        {"x-api-key": _PLAIN_KEY_A, "x-jgb-identity": _ident(VENDOR_A, session_id)}),
        {"message": "第一句"})

    # 正對照組：A 的列真的在**命名空間鍵**底下（⛔ 不在裸 session_id 底下）
    assert await _row(pool, row_key_a) is not None
    assert await _row(pool, session_id) is None, "⛔ 不得以裸 session_id 建列"

    # 模擬 A 這一輪留下的 slots（`session.slots.set` 落地後就是這個位置）
    state_a = await _state(pool, row_key_a)
    state_a.setdefault("agent", {})["slots"] = {"unit_count": "600"}
    await app_a.state.conversational_engine._save(row_key_a, state_a)
    before = await _state(pool, row_key_a)
    assert before["agent"]["slots"] == {"unit_count": "600"}   # 正對照組

    # ── B 業者拿**同一個 session_id**、另一把 key 跑一回合 ─────────────
    seen_slots = {}

    class _SpyAssembler:
        def __init__(self, inner):
            self._inner = inner

        def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
            seen_slots.update({"slots": dict(slots)})
            return self._inner.build_messages(identity, outline, slots, dialog,
                                              tool_specs, nonce)

    runtime_b = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))])
    runtime_b.assembler = _SpyAssembler(runtime_b.assembler)
    app_b = _app(pool, runtime_b)
    deps_b = _deps(app_b, pool)
    invoke_b = F._make_invoke(_registry(deps_b), deps_b)
    await invoke_b(F.AGENT_TURN_NAME, _FakeCtx(
        {"x-api-key": _PLAIN_KEY_B, "x-jgb-identity": _ident(VENDOR_B, session_id)}),
        {"message": "第二句"})

    # ⓵ B ⛔ 讀不到 A 的 slots
    assert seen_slots["slots"] == {}, f"跨業者讀到了 slots：{seen_slots['slots']}"
    # ⓶ B 走的是自己的列
    assert await _row(pool, row_key_b) is not None
    # ⓷ A 的**原列不改**
    after = await _state(pool, row_key_a)
    assert after == before, "A 的列被 B 的回合改到了——跨業者隔離破了"


# ════════════════════════════════════════════════════════════════════
# ① 兩回合：第二回合看得到第一回合留下的狀態
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_two_turns_second_sees_first_turn_state(pool, env):
    """第二回合的 `slots` 要來自第一回合存下的那一列（同一把命名空間鍵）。

    ⚠️ slots 由 `session.slots.set` 寫入，而該工具在 `build_registry` 尚未接線
    （2.4 交付了函式、還沒進 registry）⇒ 這裡以引擎直接寫入同一個位置模擬它，
    測的是**「回合之間狀態有沒有沿著命名空間鍵接起來」**這條路。
    """
    session_id = _session()
    key_id = await _api_key_id(pool, _KEY_NAME_A)
    row_key = f"mcp:{key_id}:{VENDOR_A}:{session_id}"

    runtime = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))])
    app = _app(pool, runtime)
    deps = _deps(app, pool)
    invoke = F._make_invoke(_registry(deps), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY_A,
                    "x-jgb-identity": _ident(VENDOR_A, session_id)})

    await invoke(F.AGENT_TURN_NAME, ctx, {"message": "第一句"})

    state = await _state(pool, row_key)
    state["agent"]["slots"] = {"unit_count": "600"}
    await app.state.conversational_engine._save(row_key, state)

    seen = {}

    class _SpyAssembler:
        def __init__(self, inner):
            self._inner = inner

        def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
            seen["slots"] = dict(slots)
            return self._inner.build_messages(identity, outline, slots, dialog,
                                              tool_specs, nonce)

    runtime.assembler = _SpyAssembler(runtime.assembler)
    runtime.provider.script.append(_fake_response(_agent_output(answer="您好。")))
    await invoke(F.AGENT_TURN_NAME, ctx, {"message": "第二句"})

    assert seen["slots"] == {"unit_count": "600"}, "第二回合沒讀到第一回合的 slots"
    # 兩回合、兩列事件（不變量 31：一次呼叫一列）
    assert await _wait_for_events(pool, session_id, 2) == 2


# ════════════════════════════════════════════════════════════════════
# ③ prospect 以外身分 ⇒ NO_MATCH
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("target_user,mode", [
    ("tenant", "b2c"),
    ("property_manager", "b2b"),
    ("who-am-i", "b2c"),          # 未知 ⇒ 正規化為 tenant
])
async def test_non_prospect_identity_is_no_match(pool, env, target_user, mode):
    session_id = _session()
    runtime = _make_runtime(pool, [])          # ⚠️ 腳本空：被叫到就是紅
    deps = _deps(_app(pool, runtime), pool)
    invoke = F._make_invoke(_registry(deps), deps)
    ctx = _FakeCtx({"x-api-key": _PLAIN_KEY_A,
                    "x-jgb-identity": _ident(VENDOR_A, session_id, target_user, mode)})

    with pytest.raises(Exception) as e:
        await invoke(F.AGENT_TURN_NAME, ctx, {"message": "你好"})
    assert str(e.value) == "NO_MATCH", "⛔ 錯誤訊息只能含業務代碼"
    # ⛔ 不得留下任何會話列
    assert await _wait_for_events(pool, session_id, 1) == 1   # 但事件仍留一列（不變量 31）


@pytest.mark.req(_SPEC)
async def test_prospect_positive_control(pool, env):
    """正對照組：同一組接線換成 prospect 就會通——否則上面三個 `NO_MATCH`
    可能只是因為整條路本來就壞了。"""
    session_id = _session()
    runtime = _make_runtime(pool, [_fake_response(_agent_output(answer="您好。"))])
    deps = _deps(_app(pool, runtime), pool)
    invoke = F._make_invoke(_registry(deps), deps)
    out = await invoke(F.AGENT_TURN_NAME, _FakeCtx(
        {"x-api-key": _PLAIN_KEY_A, "x-jgb-identity": _ident(VENDOR_A, session_id)}),
        {"message": "你好"})
    assert out["kind"] == "answer"


# ════════════════════════════════════════════════════════════════════
# ④ Verifier 拒兩次 ⇒ 固定句＋handoff、⛔ 無被拒文字
# ════════════════════════════════════════════════════════════════════
_REJECTED_DRAFT = "我們保證三天內完工並全額退費。"


@pytest.mark.req(_SPEC)
async def test_verifier_double_reject_returns_fixed_sentence_without_rejected_text(pool, env):
    """真 Verifier：一句沒有引用的斷言 ⇒ `UNCITED_ASSERTION`；連兩次 ⇒ 固定句。"""
    session_id = _session()
    draft = json.dumps({
        "kind": "answer", "answer": _REJECTED_DRAFT, "citations": [],
        "sentence_map": [{"sent": 0, "kind": "fact", "cite": []}],
        "fact_class": "feature", "handoff_reason": None,
    }, ensure_ascii=False)
    runtime = _make_runtime(pool, [_fake_response(draft), _fake_response(draft)])
    deps = _deps(_app(pool, runtime), pool)
    invoke = F._make_invoke(_registry(deps), deps)

    out = await invoke(F.AGENT_TURN_NAME, _FakeCtx(
        {"x-api-key": _PLAIN_KEY_A, "x-jgb-identity": _ident(VENDOR_A, session_id)}),
        {"message": "三天做得完嗎"})

    assert out["kind"] == "handoff"
    assert out["handoff"] and out["handoff"]["reason"] == "budget_exhausted"
    assert out["answer"] and out["answer"] != _REJECTED_DRAFT
    # ⛔ 被拒的草稿一個字都不得外流
    serialized = json.dumps(out, ensure_ascii=False)
    assert _REJECTED_DRAFT not in serialized
    assert "保證" not in serialized
    # 正對照組：真的被拒了兩次（provider 腳本被吃光）
    assert runtime.provider.script == []


# ════════════════════════════════════════════════════════════════════
# 真 MCP client：兩回合對話（SDK 未裝 ⇒ skip 是**供裝壞了**，不是常態）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_real_mcp_client_two_turn_conversation(pool, env):
    available, reason = F.mcp_sdk_available()
    if not available:
        pytest.skip(
            f"[env] MCP SDK 匯入失敗（{reason}）——DSP-014 A 之後 mcp==2.1.1 已是"
            "正式相依，這代表**供裝壞了**，⛔ 不是預期中的 skip")

    import uvicorn
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    from starlette.applications import Starlette
    from starlette.routing import Mount

    session_id = _session()
    key_id = await _api_key_id(pool, _KEY_NAME_A)
    row_key = f"mcp:{key_id}:{VENDOR_A}:{session_id}"

    runtime = _make_runtime(pool, [
        _fake_response(_agent_output(answer="您好。")),
        _fake_response(_agent_output(answer="您好。")),
    ])
    app_obj = _app(pool, runtime)
    deps = _deps(app_obj, pool)
    registry = _registry(deps)
    server = F.build_mcp_server(registry, deps)
    inner = Starlette(routes=[Mount("/mcp", app=F.build_asgi_app(server))])
    asgi = F.McpServiceGate(inner, get_pool=lambda: pool)

    async with server.session_manager.run():
        config = uvicorn.Config(asgi, host="127.0.0.1", port=8901, log_level="warning")
        uv = uvicorn.Server(config)
        serve_task = asyncio.create_task(uv.serve())
        try:
            for _ in range(200):
                if uv.started:
                    break
                await asyncio.sleep(0.05)

            import httpx2

            http = httpx2.AsyncClient(headers={
                "X-API-Key": _PLAIN_KEY_A,
                "X-JGB-Identity": _ident(VENDOR_A, session_id)})
            async with Client(streamable_http_client("http://127.0.0.1:8901/mcp",
                                                     http_client=http),
                              raise_exceptions=True) as client:
                names = {t.name for t in (await client.list_tools()).tools}
                assert names == {F.AGENT_TURN_NAME}

                first = await client.call_tool(F.AGENT_TURN_NAME, {"message": "第一句"})
                assert first.is_error is False

                # 第一回合的狀態落在命名空間鍵上；補進 slots 模擬 session.slots.set
                state = await _state(pool, row_key)
                state["agent"]["slots"] = {"unit_count": "600"}
                await app_obj.state.conversational_engine._save(row_key, state)

                seen = {}
                inner_assembler = runtime.assembler

                class _SpyAssembler:
                    def build_messages(self, identity, outline, slots, dialog,
                                       tool_specs, nonce):
                        seen["slots"] = dict(slots)
                        return inner_assembler.build_messages(
                            identity, outline, slots, dialog, tool_specs, nonce)

                runtime.assembler = _SpyAssembler()
                second = await client.call_tool(F.AGENT_TURN_NAME, {"message": "第二句"})
                assert second.is_error is False
            await http.aclose()

            assert seen["slots"] == {"unit_count": "600"}, \
                "第二回合沒看到第一回合的 slots"
            assert await _wait_for_events(pool, session_id, 2) == 2
        finally:
            uv.should_exit = True
            await serve_task
