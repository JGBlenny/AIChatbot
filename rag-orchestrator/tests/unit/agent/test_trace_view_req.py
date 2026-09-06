"""unit：回合軌跡渲染與 `/api/v1/agent/trace` 的閘（任務 2.7）。

涵蓋：
① `services/agent/trace_view.py:render_trace`——
   - 含**字面 `term_id`** 的 fixture（2.6 前 `verifier.py` 真的會寫字面詞）
     ⇒ `rule == "redacted"`，⛔ 字面詞不出現在輸出任何角落。
   - 輸出**不含原文鍵**（`answer`／`quote`／`text`／`user_message`／原始
     `session_id`）——遞迴掃鍵名＋掃序列化後的字串值。
   - `session` 遮罩形狀：前 4 碼＋`…`＋sha256 前 8。
   - `args_hash` **在或不在都一樣**（2.6 會刪這個鍵，渲染不得依賴它）。
② 端點閘（TestClient，假 DB）——缺 X-API-Key ⇒ 401；有 key 但缺
   `X-JGB-Identity` ⇒ 400。
③ AST：`routers/agent.py` 不得出現 `RAG_API_AUTH_ENFORCE` 的判定函式名
   （不變量 28；本檔以 `scripts/audit/checks/agent_boundary.py` 的
   `check_28_mcp_auth_unconditional` 直接驗，⛔ 不自寫第二套判準）。

⛔ 不在本檔驗跨業者 404／時間窗——那需要真的有列可讀，見
`tests/integration/agent/test_agent_trace_req.py`。
"""
import datetime
import hashlib
import importlib.util
import json
import os

import pytest

from services.agent import trace_view

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:2.7"

# 2.6 前 `services/agent/verifier.py` 寫進 term_id 的**就是字面詞**
# （`VerifierVerdict(ok=False, reason="FORBIDDEN_TERM", term_id=term)`）。
_LITERAL_TERM = "保證獲利"
_LITERAL_PATTERN = r"\d+(\.\d+)?%"

_SESSION_ID = "sess-abcdef-0123456789"

_ANSWER_TEXT = "這是絕對不該出現在軌跡輸出裡的回答全文"


def _agent_snapshot(*, with_args_hash: bool = True) -> dict:
    """2.5 落地的封閉白名單快照形狀（`services/agent/runtime.py:_emit_agent_decision`）。"""
    call = {
        "name": "kb.search",
        "args_summary": {"has_keyword": True, "k": 5},
        "ms": 84,
        "status": "ok",
        "n_items": 3,
    }
    if with_args_hash:
        call["args_hash"] = "0f1e2d3c4b5a6978"
    faced = {
        "name": "jgb2.query.bills",
        "args_summary": {"face": "bill_status", "has_ref": True},
        "ms": 210,
        "status": "ok",
        "n_items": 1,
    }
    if with_args_hash:
        faced["args_hash"] = "89abcdef01234567"
    return {
        "trace_id": "t-2f9c1a",
        "tool_calls": [call, faced],
        "llm_calls": 3,
        "prompt_tokens": 4210,
        "completion_tokens": 318,
        "verifier": [
            {"reason": "FORBIDDEN_TERM", "sent": 2, "term_id": _LITERAL_TERM, "quote_len": 0},
            {"reason": "SENSITIVE_TOPIC", "sent": 1, "term_id": _LITERAL_PATTERN, "quote_len": 0},
            {"reason": None, "sent": None, "term_id": None, "quote_len": 12},
        ],
        "final_kind": "answer",
        "handoff_reason": None,
        "latency_ms": 1930,
        "rules_sha": "a" * 64,
        "outline_sha": "b" * 64,
        "violations": ["replayed_from:t-earlier"],
        "replayed_from": "t-earlier",
    }


def _row(*, snapshot_as_str: bool = False, with_args_hash: bool = True) -> dict:
    """一列 `usage_events`（`ts` 是真欄名；本表沒有 `created_at`）。"""
    snapshot = {"agent": _agent_snapshot(with_args_hash=with_args_hash)}
    return {
        "ts": datetime.datetime(2026, 9, 5, 11, 22, 33, tzinfo=datetime.timezone.utc),
        "session_id": _SESSION_ID,
        "vendor_id": 1,
        "decision_snapshot": json.dumps(snapshot, ensure_ascii=False) if snapshot_as_str else snapshot,
    }


# ════════════════════════════════════════════════════════════════════
# ① render_trace
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_literal_term_id_is_redacted():
    view = trace_view.render_trace(_row())
    rules = [v["rule"] for v in view["verifier"]]
    assert rules[0] == "redacted"          # 字面詞
    assert rules[1] == "redacted"          # regex pattern
    assert rules[2] is None                # 通過的 verdict 本來就沒有 term
    blob = json.dumps(view, ensure_ascii=False)
    assert _LITERAL_TERM not in blob
    assert _LITERAL_PATTERN not in blob


@pytest.mark.req(_SPEC)
def test_rule_index_form_passes_through():
    """2.6 會把 term_id 改成 `rule#n`——那個形狀要原樣印出來（正對照組：
    沒有它就證明不了上一個測試是「遮罩生效」而不是「整欄都印不出來」）。"""
    row = _row()
    row["decision_snapshot"]["agent"]["verifier"][0]["term_id"] = "rule#7"
    view = trace_view.render_trace(row)
    assert view["verifier"][0]["rule"] == "rule#7"


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize("bogus", ["rule#", "rule#7x", "rule#-1", "Rule#7", "rule#7 保證"])
def test_only_exact_rule_index_passes(bogus):
    assert trace_view.rule_index(bogus) == "redacted"


@pytest.mark.req(_SPEC)
def test_no_verbatim_keys_in_view():
    row = _row()
    # 就算快照被人塞了原文鍵（不變量 30 會擋寫入端，這裡驗讀出端也不轉發）
    row["decision_snapshot"]["agent"]["tool_calls"][0]["text"] = _ANSWER_TEXT
    view = trace_view.render_trace(row)

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)

    keys = set(walk(view))
    assert not (keys & {"answer", "quote", "text", "user_message", "session_id"})
    assert "steps" in keys                                  # 正對照：真的走到了鍵
    assert _ANSWER_TEXT not in json.dumps(view, ensure_ascii=False)


@pytest.mark.req(_SPEC)
def test_top_level_key_set_is_closed():
    view = trace_view.render_trace(_row())
    assert set(view) == {
        "trace_id", "at", "kind", "handoff_reason", "replayed_from",
        "steps", "verifier", "counts", "session", "rules_sha", "outline_sha",
        "candidates",  # 任務 4.1：鏡射 TurnTrace 三鍵
    }
    assert set(view["counts"]) == {
        "llm_calls", "prompt_tokens", "completion_tokens", "latency_ms"
    }
    assert set(view["candidates"]) == {"ids", "winning_key_kind", "miss_kind"}
    # DSP-029 r13 #7：多一個 `schema_cause`（封閉列舉值，⛔ 無原文）——
    # 只回 `SCHEMA` 時七種結構性失敗全擠成同一格，稽核看不出差別。
    assert set(view["verifier"][0]) == {"reason", "schema_cause", "sent", "rule"}


@pytest.mark.req(_SPEC)
def test_session_is_masked():
    view = trace_view.render_trace(_row())
    expected = (
        _SESSION_ID[:4] + "…" + hashlib.sha256(_SESSION_ID.encode("utf-8")).hexdigest()[:8]
    )
    assert view["session"] == expected
    assert _SESSION_ID not in json.dumps(view, ensure_ascii=False)
    # 遮罩要有辨識力：不同 session ⇒ 不同輸出
    assert trace_view.mask_session("sess-zzzzzz-9876543210") != expected


@pytest.mark.req(_SPEC)
def test_steps_carry_shape_only():
    view = trace_view.render_trace(_row())
    kb, bills = view["steps"]
    assert kb["name"] == "kb.search"
    assert "face" not in kb                       # 沒有 face 就不編造一個
    assert kb["has_keyword"] is True and kb["has_ref"] is False
    assert kb["k"] == 5 and kb["n_items"] == 3 and kb["status"] == "ok" and kb["ms"] == 84
    assert bills["face"] == "bill_status" and bills["has_ref"] is True
    assert "k" not in bills
    assert "args_hash" not in kb and "args_hash" not in bills


@pytest.mark.req(_SPEC)
def test_render_is_identical_with_and_without_args_hash():
    """2.6 會刪 `args_hash`——渲染結果必須完全不受影響。"""
    assert trace_view.render_trace(_row(with_args_hash=True)) == trace_view.render_trace(
        _row(with_args_hash=False)
    )


@pytest.mark.req(_SPEC)
def test_snapshot_as_json_string_is_accepted():
    """asyncpg 預設把 jsonb 交回字串；psycopg2 交回 dict——兩者同結果。"""
    assert trace_view.render_trace(_row(snapshot_as_str=True)) == trace_view.render_trace(_row())


@pytest.mark.req(_SPEC)
def test_row_without_agent_snapshot_is_empty_view():
    view = trace_view.render_trace({"ts": None, "session_id": None, "decision_snapshot": None})
    assert view["trace_id"] is None and view["steps"] == [] and view["session"] == ""


@pytest.mark.req(_SPEC)
def test_render_text_has_no_verbatim():
    text = trace_view.render_text(trace_view.render_trace(_row()))
    assert "kb.search" in text and "bill_status" in text     # 正對照：真的印了東西
    assert _LITERAL_TERM not in text and _SESSION_ID not in text


@pytest.mark.req(_SPEC)
def test_window_days_env(monkeypatch):
    monkeypatch.delenv(trace_view.TRACE_WINDOW_ENV, raising=False)
    assert trace_view.window_days() == 7
    monkeypatch.setenv(trace_view.TRACE_WINDOW_ENV, "3")
    assert trace_view.window_days() == 3
    for bad in ("0", "-5", "abc", ""):
        monkeypatch.setenv(trace_view.TRACE_WINDOW_ENV, bad)
        assert trace_view.window_days() == 7, f"{bad!r} 應退回預設，⛔ 不放大窗"


# ════════════════════════════════════════════════════════════════════
# ② 端點閘（TestClient＋假 DB）
# ════════════════════════════════════════════════════════════════════
class _FakePool:
    """只回應 `fetchrow`／`fetch` 的假 pool——本區塊的測試都在到 DB 之前就該擋下。"""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self.rows[0] if self.rows else None

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return list(self.rows)


def _client(pool):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from routers import agent as agent_router

    agent_router.reset_registry_cache()
    app = FastAPI()
    app.state.db_pool = pool
    app.include_router(agent_router.router)
    return TestClient(app, raise_server_exceptions=False)


def _bypass_key(monkeypatch, vendor_ids=None):
    from routers import agent as agent_router
    from services.agent import mcp_facade as F

    key = {"id": 1, "name": "t", "is_internal": False, "vendor_ids": vendor_ids}

    async def _fake_require_key(request, pool):
        return key

    async def _fake_vendor_exists(pool, vendor_id):
        return True

    monkeypatch.setattr(agent_router, "require_api_key_unconditional", _fake_require_key)
    monkeypatch.setattr(F, "vendor_exists", _fake_vendor_exists)
    return key


@pytest.mark.req(_SPEC)
def test_trace_without_api_key_is_401(monkeypatch):
    """`RAG_API_AUTH_ENFORCE` 關著也一樣 401——這條路徑不看那個旗標。"""
    monkeypatch.delenv("RAG_API_AUTH_ENFORCE", raising=False)
    with _client(_FakePool()) as c:
        assert c.get("/api/v1/agent/trace/t-1").status_code == 401
        assert c.get("/api/v1/agent/trace", params={"session_id": "s"}).status_code == 401


@pytest.mark.req(_SPEC)
def test_trace_without_identity_header_is_400(monkeypatch):
    _bypass_key(monkeypatch)
    with _client(_FakePool()) as c:
        r = c.get("/api/v1/agent/trace/t-1", headers={"X-API-Key": "k"})
        assert r.status_code == 400, r.text
        r = c.get(
            "/api/v1/agent/trace", params={"session_id": "s"}, headers={"X-API-Key": "k"}
        )
        assert r.status_code == 400, r.text


@pytest.mark.req(_SPEC)
def test_trace_with_identity_reaches_db_and_404s_on_empty(monkeypatch):
    """正對照：帶齊 key＋身分就會真的查下去（假 pool 收到查詢），查無 ⇒ 404。"""
    _bypass_key(monkeypatch)
    pool = _FakePool(rows=[])
    ident = json.dumps({"vendor_id": 1, "session_id": "s1"})
    with _client(pool) as c:
        r = c.get(
            "/api/v1/agent/trace/t-1",
            headers={"X-API-Key": "k", "X-JGB-Identity": ident},
        )
    assert r.status_code == 404
    assert len(pool.calls) == 1
    sql, args = pool.calls[0]
    assert "ts > now()" in sql and "LIMIT 1" in sql      # 時間窗＋LIMIT 都在
    assert args[0] == "t-1" and args[1] == "7"


@pytest.mark.req(_SPEC)
def test_session_timeline_response_masks_session(monkeypatch):
    _bypass_key(monkeypatch, vendor_ids=[1])
    pool = _FakePool(rows=[_row()])
    ident = json.dumps({"vendor_id": 1, "session_id": "s1"})
    with _client(pool) as c:
        r = c.get(
            "/api/v1/agent/trace",
            params={"session_id": _SESSION_ID},
            headers={"X-API-Key": "k", "X-JGB-Identity": ident},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1 and body["session"] == trace_view.mask_session(_SESSION_ID)
    assert _SESSION_ID not in r.text
    sql, args = pool.calls[0]
    assert f"LIMIT {trace_view.SESSION_TIMELINE_LIMIT}" in sql
    assert args[2] == [1]                                # key 的 vendor_ids 進了 SQL


@pytest.mark.req(_SPEC)
def test_row_outside_key_vendor_scope_is_404(monkeypatch):
    """縱深防禦第二層：SQL 若被改壞而回了範圍外的列，Python 這層仍擋成 404。"""
    _bypass_key(monkeypatch, vendor_ids=[2])
    row = _row()
    row["vendor_id"] = 1
    pool = _FakePool(rows=[row])
    ident = json.dumps({"vendor_id": 2, "session_id": "s1"})
    with _client(pool) as c:
        r = c.get(
            "/api/v1/agent/trace/t-2f9c1a",
            headers={"X-API-Key": "k", "X-JGB-Identity": ident},
        )
    assert r.status_code == 404
    # 正對照：同一列在「key 不限業者」時讀得到，證明 404 來自範圍而不是查詢壞了
    _bypass_key(monkeypatch, vendor_ids=None)
    with _client(_FakePool(rows=[row])) as c:
        r = c.get(
            "/api/v1/agent/trace/t-2f9c1a",
            headers={"X-API-Key": "k", "X-JGB-Identity": ident},
        )
    assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════════════
# ③ 不變量 28（AST）——加了 /trace 之後仍不得引用 enforce 旗標判定
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_invariant_28_still_green_after_trace_endpoints():
    here = os.path.dirname(os.path.abspath(__file__))          # tests/unit/agent
    rag_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    checker_py = os.path.join(
        os.path.dirname(rag_root), "scripts", "audit", "checks", "agent_boundary.py"
    )
    assert os.path.exists(checker_py), f"{checker_py} 不存在——盤查腳本位置變了"
    spec = importlib.util.spec_from_file_location("agent_boundary_checker_2_7", checker_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok, msg = mod.check_28_mcp_auth_unconditional()
    assert ok, msg
    assert "尚未建立" not in msg, f"routers/agent.py 應被掃到而非略過：{msg}"
