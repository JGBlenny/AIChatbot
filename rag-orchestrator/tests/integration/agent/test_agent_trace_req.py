"""integration：`GET /api/v1/agent/trace/{trace_id}`・`/trace?session_id=`（任務 2.7）。

真測試庫 ＋ 真 HTTP（ASGI transport）。鏡射 `test_agent_router_req.py`：只掛
`routers.agent.router`，`app.state.db_pool` 指向測試庫真 pool，⛔ 不起整個
`app.py`（否則結論會被 embedding／OpenAI 等外部相依淹掉）。

## 快照怎麼來的：**不是手寫 fixture**
`_agent_snapshot_from_real_trace()` 建一個真的 `runtime.TurnTrace`，交給
**2.5 的正式落點** `services/agent/runtime.py:_emit_agent_decision` 去組，再從
`usage_metering` 的 context 取回它實際會寫進 `decision_snapshot` 的那份 dict。
所以本檔驗的是「2.5 真的寫出來的形狀，2.7 讀不讀得懂」，⛔ 不是「我猜的形狀，
我自己讀得懂」——手寫 fixture 會在 2.6 動快照時安靜地繼續綠。

## 涵蓋
① `vendor_ids=NULL` 的 key ⇒ 讀得到 vendor 1 的 trace，工具序列與 `face` 都在。
② `vendor_ids=[2]` 的 key 讀 vendor 1 的 trace ⇒ **404**（正對照：同一把 key
   讀 vendor 2 自己的 trace ⇒ 200，證明 404 來自業者範圍而不是查詢壞了）。
③ 超出時間窗 ⇒ 404（正對照：把 `AGENT_TRACE_WINDOW_DAYS` 放大到涵蓋它 ⇒ 200）。
④ session 時間軸：同 session 兩回合依 `ts` 由舊到新，`session_id` 只以遮罩出現。
⑤ 不變量 28（`scripts/audit/checks/agent_boundary.py`）在 `/trace` 加入後仍綠。

⚠️ 時間欄是 `usage_events.ts`——本表**沒有** `created_at`
（`database/migrations/add_usage_events.sql`；實查測試庫
`information_schema.columns` 亦無此欄）。
"""
import datetime
import json
import os
import uuid

import pytest

from services import usage_metering
from services.agent import runtime as agent_runtime
from services.agent import trace_view
from services.agent.output_schema import VerifierVerdict
from services.api_key_auth import _reset_agent_scope_detection, hash_key

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:2.7"

VENDOR_OK = 1
VENDOR_OTHER = 2

_KEY_ALL_NAME = "test-agent-trace-2-7-all"
_KEY_ALL = "agent-trace-integration-key-unscoped"
_KEY_V2_NAME = "test-agent-trace-2-7-v2"
_KEY_V2 = "agent-trace-integration-key-vendor2"

_LITERAL_TERM = "保證獲利"          # 2.6 前 verifier 真的會把字面詞寫進 term_id


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _agent_snapshot_from_real_trace(trace_id: str) -> dict:
    """走 2.5 的正式落點組快照（見模組 docstring）。回傳 `{"agent": {...}}`。"""
    trace = agent_runtime.TurnTrace(
        trace_id=trace_id,
        tool_calls=[
            agent_runtime.ToolCallRecord(
                id="call_1", name="kb.search",
                args_summary={"has_keyword": True, "k": 5},
                ms=84, status="ok", n_items=3,
            ),
            agent_runtime.ToolCallRecord(
                id="call_2", name="jgb2.query.bills",
                args_summary={"face": "bill_status", "has_ref": True},
                ms=210, status="ok", n_items=1,
            ),
        ],
        llm_calls=3, prompt_tokens=4210, completion_tokens=318,
        verifier=[
            VerifierVerdict.model_construct(ok=False, reason="FORBIDDEN_TERM", sent=2,
                            term_id=_LITERAL_TERM, quote_len=0),  # model_construct：2.6 後正式路徑不可能出現字面詞，此處故意繞過驗證測遮罩
            VerifierVerdict(ok=True, quote_len=12),
        ],
        final_kind="answer", handoff_reason=None, latency_ms=1930,
        violations=[], rules_sha="a" * 64, outline_sha="b" * 64,
    )
    usage_metering.begin({
        "vendor_id": VENDOR_OK, "mode": "b2b", "session_id": "snapshot-builder",
        "message": "x",
    })
    agent_runtime._emit_agent_decision(trace)
    # `_ctx` 是 usage_metering 的私有 ContextVar——這裡刻意讀它，因為要拿的正是
    # 「2.5 準備寫進 DB 的那份 dict」，任何複製版本都會失去這個測試的意義。
    ctx = usage_metering._ctx.get()
    assert ctx is not None and ctx.decision_snapshot, "usage_metering context 沒建起來——大聲失敗"
    snapshot = json.loads(json.dumps(ctx.decision_snapshot, ensure_ascii=False, default=str))
    usage_metering.finalize(status="success", http_status=200, db_pool=None)  # 不寫 DB
    assert snapshot["agent"]["trace_id"] == trace_id
    return snapshot


_INSERT = (
    "INSERT INTO usage_events"
    " (request_id, ts, date_tpe, vendor_id, mode, user_type, session_id,"
    "  channel, is_internal, message_len, status, decision_snapshot)"
    " VALUES ($1, $2, $3, $4, 'b2b', 'prospect', $5, 'web', FALSE, 1, 'success', $6)"
)


@pytest.fixture
async def env():
    """測試庫 pool ＋ 兩把 key ＋ 四列軌跡；離場全部清掉。"""
    import asyncpg

    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=4)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"測試 DB 不可達（{type(e).__name__}）→ agent trace 整合測試未驗")
        return

    # 正對照組：兩個業者都必須存在，否則 `parse_identity` 會先以 403 擋掉，
    # 下面的 404 斷言就證明不了「範圍過濾生效」。
    for vid in (VENDOR_OK, VENDOR_OTHER):
        if not await pool.fetchval("SELECT count(*) FROM vendors WHERE id = $1", vid):
            await pool.close()
            pytest.skip(f"[env] 測試庫 vendors 缺 {vid}")

    # 決策快照欄未套 migration ⇒ 本測試無意義，大聲略過（⛔ 不靜默通過）
    has_col = await pool.fetchval(
        "SELECT count(*) FROM information_schema.columns"
        " WHERE table_name='usage_events' AND column_name='decision_snapshot'")
    if not has_col:
        await pool.close()
        pytest.skip("[env] 測試庫 usage_events 缺 decision_snapshot 欄（migration 未套）")

    _reset_agent_scope_detection()
    for name in (_KEY_ALL_NAME, _KEY_V2_NAME):
        await pool.execute("DELETE FROM api_keys WHERE name = $1", name)
    await pool.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
        " VALUES ($1,$2,$3,TRUE,FALSE,NULL)",
        _KEY_ALL_NAME, hash_key(_KEY_ALL), _KEY_ALL[:8])
    await pool.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix, is_active, is_internal, vendor_ids)"
        " VALUES ($1,$2,$3,TRUE,FALSE,$4)",
        _KEY_V2_NAME, hash_key(_KEY_V2), _KEY_V2[:8], [VENDOR_OTHER])

    now = datetime.datetime.now(datetime.timezone.utc)
    suffix = uuid.uuid4().hex[:8]
    session_a = f"trace27-{suffix}-sess-a"
    session_old = f"trace27-{suffix}-sess-old"
    session_v2 = f"trace27-{suffix}-sess-v2"
    rows = {
        # 名稱 → (trace_id, vendor, session, ts)
        "recent": (f"t27-{suffix}-recent", VENDOR_OK, session_a, now - datetime.timedelta(minutes=1)),
        "earlier": (f"t27-{suffix}-earlier", VENDOR_OK, session_a, now - datetime.timedelta(minutes=9)),
        "stale": (f"t27-{suffix}-stale", VENDOR_OK, session_old, now - datetime.timedelta(days=30)),
        "v2": (f"t27-{suffix}-v2", VENDOR_OTHER, session_v2, now - datetime.timedelta(minutes=1)),
    }
    request_ids = []
    for trace_id, vendor, session, ts in rows.values():
        rid = uuid.uuid4()
        request_ids.append(rid)
        await pool.execute(
            _INSERT, rid, ts, ts.astimezone(datetime.timezone.utc).date(), vendor, session,
            json.dumps(_agent_snapshot_from_real_trace(trace_id), ensure_ascii=False),
        )

    try:
        yield {"pool": pool, "rows": rows, "session_a": session_a}
    finally:
        await pool.execute("DELETE FROM usage_events WHERE request_id = ANY($1)", request_ids)
        for name in (_KEY_ALL_NAME, _KEY_V2_NAME):
            await pool.execute("DELETE FROM api_keys WHERE name = $1", name)
        await pool.close()
        _reset_agent_scope_detection()


def _build_app(pool):
    from fastapi import FastAPI

    from routers import agent as agent_router

    agent_router.reset_registry_cache()
    app = FastAPI()
    app.state.db_pool = pool
    app.include_router(agent_router.router)
    return app


def _client(app):
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                             base_url="http://agent-trace-test")


def _headers(key: str, vendor_id: int, session_id: str = "s1") -> dict:
    return {
        "X-API-Key": key,
        "X-JGB-Identity": json.dumps(
            {"vendor_id": vendor_id, "session_id": session_id, "target_user": "prospect"}
        ),
    }


# ════════════════════════════════════════════════════════════════════
# ① 不限業者的 key 讀得到（含工具序列與 face）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_unscoped_key_reads_vendor1_trace(env):
    trace_id = env["rows"]["recent"][0]
    async with _client(_build_app(env["pool"])) as c:
        # 正對照：缺 key 仍 401（否則下面的 200 可能只是沒掛認證）
        assert (await c.get(f"/api/v1/agent/trace/{trace_id}")).status_code == 401

        r = await c.get(f"/api/v1/agent/trace/{trace_id}",
                        headers=_headers(_KEY_ALL, VENDOR_OK))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trace_id"] == trace_id
    names = [s["name"] for s in body["steps"]]
    assert names == ["kb.search", "jgb2.query.bills"]
    assert body["steps"][1]["face"] == "bill_status"     # face 看得到（業主要的那件事）
    assert body["steps"][0]["k"] == 5 and body["steps"][0]["has_keyword"] is True
    assert body["counts"]["llm_calls"] == 3
    assert body["kind"] == "answer"
    # 遮罩與拒因索引
    assert body["session"] == trace_view.mask_session(env["session_a"])
    assert body["verifier"][0]["reason"] == "FORBIDDEN_TERM"
    assert body["verifier"][0]["rule"] == "redacted"
    assert _LITERAL_TERM not in r.text
    assert env["session_a"] not in r.text


# ════════════════════════════════════════════════════════════════════
# ② 業者範圍：vendor_ids=[2] 讀 vendor 1 ⇒ 404（正對照：讀自己的 ⇒ 200）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_key_scoped_to_vendor2_cannot_read_vendor1_trace(env):
    v1_trace = env["rows"]["recent"][0]
    v2_trace = env["rows"]["v2"][0]
    async with _client(_build_app(env["pool"])) as c:
        own = await c.get(f"/api/v1/agent/trace/{v2_trace}",
                          headers=_headers(_KEY_V2, VENDOR_OTHER))
        other = await c.get(f"/api/v1/agent/trace/{v1_trace}",
                            headers=_headers(_KEY_V2, VENDOR_OTHER))
    assert own.status_code == 200, f"正對照失敗（自己的 trace 也讀不到）：{own.text}"
    assert other.status_code == 404, other.text
    assert v1_trace not in other.text       # ⛔ 連「這個 id 存在」都不透露


@pytest.mark.req(_SPEC)
async def test_session_timeline_is_scoped_by_key_vendor(env):
    """session 模式同樣受業者範圍管——否則猜到 session_id 就能看別人的時間軸。"""
    async with _client(_build_app(env["pool"])) as c:
        r = await c.get("/api/v1/agent/trace",
                        params={"session_id": env["session_a"]},
                        headers=_headers(_KEY_V2, VENDOR_OTHER))
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 0


# ════════════════════════════════════════════════════════════════════
# ③ 時間窗
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_out_of_window_trace_is_404(env, monkeypatch):
    stale = env["rows"]["stale"][0]
    monkeypatch.setenv(trace_view.TRACE_WINDOW_ENV, "7")
    async with _client(_build_app(env["pool"])) as c:
        r = await c.get(f"/api/v1/agent/trace/{stale}", headers=_headers(_KEY_ALL, VENDOR_OK))
    assert r.status_code == 404, r.text

    # 正對照：把窗放大到涵蓋這列 ⇒ 200，證明 404 來自時間窗而不是列不見了
    monkeypatch.setenv(trace_view.TRACE_WINDOW_ENV, "60")
    async with _client(_build_app(env["pool"])) as c:
        r = await c.get(f"/api/v1/agent/trace/{stale}", headers=_headers(_KEY_ALL, VENDOR_OK))
    assert r.status_code == 200, r.text
    assert r.json()["trace_id"] == stale


# ════════════════════════════════════════════════════════════════════
# ④ session 時間軸
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_session_timeline_orders_by_ts(env):
    async with _client(_build_app(env["pool"])) as c:
        r = await c.get("/api/v1/agent/trace",
                        params={"session_id": env["session_a"]},
                        headers=_headers(_KEY_ALL, VENDOR_OK))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    assert [t["trace_id"] for t in body["traces"]] == [
        env["rows"]["earlier"][0], env["rows"]["recent"][0]
    ]
    assert body["session"] == trace_view.mask_session(env["session_a"])
    assert env["session_a"] not in r.text            # ⛔ 原始 session_id 不外洩
    assert _LITERAL_TERM not in r.text


# ════════════════════════════════════════════════════════════════════
# ⑤ CLI（`tools/agent_trace.py`）——與端點同一份渲染，走 psycopg2 直連測試庫
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_cli_prints_trace_and_masks(env, capsys):
    from tools.agent_trace import main

    trace_id = env["rows"]["recent"][0]
    assert main([trace_id, "--vendor", str(VENDOR_OK)]) == 0
    out = capsys.readouterr().out
    assert "kb.search" in out and "bill_status" in out       # 正對照：真的印了軌跡
    assert _LITERAL_TERM not in out                          # 字面拒因不外洩
    assert env["session_a"] not in out                       # 原始 session_id 不外洩
    assert trace_view.mask_session(env["session_a"]) in out


@pytest.mark.req(_SPEC)
async def test_cli_vendor_filter_and_exit_codes(env, capsys):
    """`--vendor` 是必填的範圍過濾：查別的業者的 trace ⇒ 退出碼 2（查無）。"""
    from tools.agent_trace import main

    trace_id = env["rows"]["recent"][0]                       # vendor 1 的
    assert main([trace_id, "--vendor", str(VENDOR_OTHER)]) == 2
    capsys.readouterr()

    assert main(["--session", env["session_a"], "--vendor", str(VENDOR_OK)]) == 0
    out = capsys.readouterr().out
    assert "共 2 回合" in out

    # 兩個都給／都不給 ⇒ 用法錯誤（1），⛔ 不是「查無」（2）
    assert main([trace_id, "--session", env["session_a"], "--vendor", "1"]) == 1
    capsys.readouterr()


@pytest.mark.req(_SPEC)
def test_cli_takes_no_credential_arguments():
    """憑證只走 `db_utils.get_db_config()`——⛔ 任何密碼類參數都不得存在於 argv。"""
    from tools.agent_trace import build_parser

    options = {
        opt for action in build_parser()._actions for opt in action.option_strings
    }
    assert {"--vendor", "--session", "--days"} <= options          # 正對照
    assert not (options & {"--password", "--dsn", "--db-password", "--pgpassword", "--url"})


# ════════════════════════════════════════════════════════════════════
# ⑥ 不變量 28 仍綠
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_invariant_28_still_green_with_trace_endpoints():
    import importlib.util

    here = os.path.dirname(os.path.abspath(__file__))            # tests/integration/agent
    rag_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    checker_py = os.path.join(os.path.dirname(rag_root), "scripts", "audit",
                              "checks", "agent_boundary.py")
    assert os.path.exists(checker_py), f"{checker_py} 不存在——盤查腳本位置變了"
    spec = importlib.util.spec_from_file_location("agent_boundary_checker_2_7_int", checker_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok, msg = mod.check_28_mcp_auth_unconditional()
    assert ok, msg
    assert "尚未建立" not in msg, f"routers/agent.py 應被掃到而非略過：{msg}"
