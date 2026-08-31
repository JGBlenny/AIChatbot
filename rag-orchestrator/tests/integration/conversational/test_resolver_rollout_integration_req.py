"""integration：resolver rollout 的 **mock 能證明的全部**（M1；零 OpenAI）。

⚠️ evaluator 為**腳本化替身**——本檔驗的是
`migration → config loading → scoped activation → resolver control flow → persistence → fallback`，
不是模型判得對不對（那屬 v6 付費回歸）。

⚠️ 全程只碰**測試庫**：migration 於 fixture 內套用、結束**還原**；
`PREENTRY_ROUTABILITY_*` 只在本行程設定。
"""
import asyncio
import json
import time
import os
import uuid

import pytest

pytestmark = pytest.mark.integration

SEED, MID, TARGET = "bill_diagnosis", "billing_anomaly", "contract_closeout"
MIGRATION = "/app/database/migrations/seed_responsibility_delegates_v1.sql"
#: ⚠️ **E-DEBT-02**（2026-08-31）：本檔原本指向 `migrations/` 根目錄，但檔案實際在
#: `migrations/rollback/` ⇒ teardown 每次 FileNotFoundError ⇒ seed **永遠沒被還原**，
#: 每跑一次 integration 就把 delegates 殘留進 `aichatbot_test`，污染所有 regression baseline。
ROLLBACK = "/app/database/migrations/rollback/seed_responsibility_delegates_v1_rollback.sql"

#: 受本 migration 影響的兩個面向——snapshot／還原與 dirty sentinel 都以它們為準
AFFECTED_FACETS = (SEED, MID)


def _conn_kwargs():
    return dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "aichatbot"),
                password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                database=os.getenv("DB_NAME", "aichatbot_test"))


async def _exec_sql(path):
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        await conn.execute(open(path, encoding="utf-8").read())
    finally:
        await conn.close()


async def _snapshot_affected():
    """擷取受影響兩列的完整內容——⚠️ 還原以**快照**為準，⛔ 不假設 rollback SQL 是完美逆運算。"""
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        rows = await conn.fetch(
            "SELECT id, generation_metadata::text AS gm, answer FROM knowledge_base "
            "WHERE category = '對話規則' AND is_active "
            "  AND generation_metadata->'conversational_config'->>'key' = ANY($1::text[]) "
            "ORDER BY id", list(AFFECTED_FACETS))
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def _restore_affected(snap):
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        for r in snap:
            await conn.execute(
                "UPDATE knowledge_base SET generation_metadata = $2::jsonb, answer = $3 "
                "WHERE id = $1", r["id"], r["gm"], r["answer"])
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def migrated_db():
    """★ ② 走**正式 migration 產出的 DB 狀態**，不再直接塞 config 物件。

    ## E-DEBT-02 —— REGRESSION_BASELINE_DB_ISOLATION（2026-08-31 業主裁定）

    ```text
    fixture 必須是 **state-neutral**：跑完後 aichatbot_test 逐欄位回到跑之前
    ```
    ⚠️ 原本 teardown 只呼叫 `ROLLBACK` 腳本，而該路徑是錯的 ⇒ 靜默失敗、殘留累積。

    ## ⛔ 為什麼 teardown **不能**跑 rollback 腳本

    業主 2026-08-31 裁定：canonical baseline ＝ **seed 已套用 ＋ 帳本已記**。
    在那個 baseline 上跑 rollback 腳本是**破壞性**的——它會把正典狀態裡本來就該有的
    delegates 拔掉。⇒ teardown 一律以 **snapshot 還原**，⛔ 不以「跑逆向腳本」代替還原。
    ⚠️ `MIGRATION` 本身有冪等守衛（`responsibility IS NULL`），baseline 已套用時是 no-op；
    這是**正常**的，⛔ 不得因此判測試失效。
    """
    if not os.path.exists(MIGRATION):
        pytest.skip("migration 檔不在容器內")
    snap = asyncio.run(_snapshot_affected())
    assert snap, "snapshot 為空 ⇒ 受影響的規則列不存在，測試前提不成立（⛔ 不是『乾淨』）"
    try:
        asyncio.run(_exec_sql(MIGRATION))
    except Exception as e:                                   # pragma: no cover
        pytest.skip(f"無法套用 migration：{e}")
        return
    yield
    # ⚠️ 無條件以 snapshot 還原——⛔ 不判斷「應該沒變吧」就跳過（那是 E-DEBT-02 的病）
    asyncio.run(_restore_affected(snap))
    after = asyncio.run(_snapshot_affected())
    if after != snap:                                        # pragma: no cover
        raise AssertionError("snapshot 還原後仍與進場狀態不符 ⇒ 還原機制本身失效")


@pytest.fixture
async def pool(migrated_db):
    import asyncpg
    from services import conversational_config as cc
    p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cc.reset_cache()
    yield p
    cc.reset_cache()
    await p.close()


class ScriptedEvaluator:
    """腳本化 responsibility evaluator：依 rules 原文反查目前是哪個面向。"""

    def __init__(self, script, rules_by_facet):
        self.script = script
        self.rules_by_facet = rules_by_facet
        self.seen = []

    async def conversational_step_result(self, *a, **kw):
        """任務 8 後引擎改呼叫這支；轉呼下方既有腳本並包成 StepResult。"""
        from tests.support.brain_stub import as_step_result
        return as_step_result(await self.conversational_step(*a, **kw))

    async def conversational_step(self, rules, system_md, state, msg, **kw):
        facet = next(f for f, r in self.rules_by_facet.items() if r == rules)
        scope, delegate = self.script.get(facet, ("stay", None))
        self.seen.append({"facet": facet, "delegates": kw.get("delegates"),
                          "rules_declares_field": "delegate_facet_key" in (rules or "")})
        out = {"action": "ask", "next_question": "q", "scope": scope}
        if delegate:
            out["delegate_facet_key"] = delegate
        return out          # 相容層回 payload；上方 adapter 負責包成 StepResult


async def _rules_map(pool, facets):
    from services.conversational_config import config_for_key
    from services.conversational_rules import load_rules
    out = {}
    for f in facets:
        cfg = await config_for_key(pool, f)
        if cfg is None:
            pytest.skip(f"面向 {f} 未供裝")
        out[f] = await load_rules(pool, cfg.persona_role)
    return out


# ── ② migration 產出的 DB 狀態能驅動 delegation chain ────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_chain_runs_from_migration_produced_config(pool):
    from services.conversational_config import config_for_key
    from services.responsibility import allowed_delegates, delegate_specs, resolve_entry_candidate

    seed_cfg = await config_for_key(pool, SEED)
    assert allowed_delegates(seed_cfg) == (MID,), "migration 未產出 delegates"
    assert delegate_specs(seed_cfg)[0][1], "migration 未帶 `when` 語義條件"

    rules = await _rules_map(pool, (SEED, MID, TARGET))
    brain = ScriptedEvaluator({SEED: ("switch", MID), MID: ("switch", TARGET),
                               TARGET: ("stay", None)}, rules)
    res = await resolve_entry_candidate(pool, seed_cfg, "幫我查點退帳單金額", optimizer=brain)

    assert res.committed_key == TARGET and res.stop_reason == "stay"
    assert [h["facet_key"] for h in res.chain] == [SEED, MID, TARGET]
    # migration 的第二段：規則宣告形狀確實含該欄位（否則真 brain 不會輸出）
    assert all(s["rules_declares_field"] for s in brain.seen[:2])
    # 白名單與 when 都由 DB 契約提供
    assert brain.seen[0]["delegates"] == [(MID, "帳單金額組成/看不到帳單")]
    assert brain.seen[1]["delegates"] == [(TARGET, "封存/點退帳單處理")]


# ── ③ scoped gate：allowlist 內走新路、外部逐位不變 ──────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_scoped_gate_out_of_allowlist_is_untouched(pool, monkeypatch):
    from routers import chat as chat_mod
    from services import responsibility as resp_mod
    from services.conversational_config import config_for_key

    other_cfg = await config_for_key(pool, "billing_invoice")
    if other_cfg is None:
        pytest.skip("對照面向未供裝")
    calls = {"n": 0}
    real = resp_mod.resolve_entry_candidate

    async def counting(*a, **kw):
        calls["n"] += 1
        return await real(*a, **kw)

    monkeypatch.setattr(resp_mod, "resolve_entry_candidate", counting)
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
    monkeypatch.setenv("PREENTRY_ROUTABILITY_FACETS", SEED)

    # 裁定 001-A：回傳改為 (config, face authority)
    out, authority = await chat_mod._resolve_pre_commit_candidate(pool, other_cfg, "問句")
    assert out is other_cfg and calls["n"] == 0, "allowlist 外的面向不得走新路"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_scoped_gate_inside_allowlist_uses_resolver(pool, monkeypatch):
    from routers import chat as chat_mod
    from services import responsibility as resp_mod
    from services.conversational_config import config_for_key

    seed_cfg = await config_for_key(pool, SEED)
    rules = await _rules_map(pool, (SEED, MID, TARGET))
    brain = ScriptedEvaluator({SEED: ("stay", None)}, rules)
    real = resp_mod.resolve_entry_candidate
    seen = {"n": 0}

    async def with_scripted(*a, **kw):
        seen["n"] += 1
        return await real(*a, **{**kw, "optimizer": brain})

    monkeypatch.setattr(resp_mod, "resolve_entry_candidate", with_scripted)
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
    monkeypatch.setenv("PREENTRY_ROUTABILITY_FACETS", SEED)

    out, authority = await chat_mod._resolve_pre_commit_candidate(pool, seed_cfg, "問句")
    assert seen["n"] == 1 and getattr(out, "key", None) == SEED
    # 腳本化 evaluator 判的是真 model stay ⇒ 必須帶 authority（裁定 001-A 第 1 列）
    from services.responsibility import FACE_AUTHORITATIVE
    assert authority == FACE_AUTHORITATIVE


@pytest.mark.req("face-exit-before-grounding:1")
async def test_gate_open_without_allowlist_is_fail_safe(pool, monkeypatch):
    from routers import chat as chat_mod
    from services import responsibility as resp_mod
    from services.conversational_config import config_for_key

    seed_cfg = await config_for_key(pool, SEED)
    calls = {"n": 0}

    async def counting(*a, **kw):
        calls["n"] += 1

    monkeypatch.setattr(resp_mod, "resolve_entry_candidate", counting)
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
    monkeypatch.delenv("PREENTRY_ROUTABILITY_FACETS", raising=False)
    out, authority = await chat_mod._resolve_pre_commit_candidate(pool, seed_cfg, "問句")
    from services.responsibility import FACE_UNEVALUATED
    assert out is seed_cfg and calls["n"] == 0, "只開旗標不得等於全站啟用"
    # resolver 沒跑 ⇒ unevaluated（既有行為），**不是** authority、也不是 fail-open
    assert authority == FACE_UNEVALUATED


# ── ⑤ fallback：三條路都不 commit，且不建立 transient session ─────────────────
async def _rows(sid):
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        return await conn.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational'",
            sid)
    finally:
        await conn.close()


@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("script,expected_stop", [
    ({SEED: ("switch", None)}, "switch_without_delegate"),
    ({SEED: ("switch", MID), MID: ("switch", SEED)}, "delegation_cycle"),
])
async def test_fallback_paths_commit_nothing(pool, script, expected_stop):
    from services.conversational_config import config_for_key
    from services.responsibility import resolve_entry_candidate

    seed_cfg = await config_for_key(pool, SEED)
    rules = await _rules_map(pool, (SEED, MID, TARGET))
    brain = ScriptedEvaluator(script, rules)
    sid = f"rollout-fb-{uuid.uuid4().hex[:8]}"
    assert await _rows(sid) == 0

    res = await resolve_entry_candidate(pool, seed_cfg, "問句", optimizer=brain)
    assert res.committed_key is None and res.stop_reason == expected_stop
    assert await _rows(sid) == 0, "fallback 不得建立 transient session"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_unknown_delegate_fails_closed(pool):
    from services.conversational_config import config_for_key
    from services.responsibility import resolve_entry_candidate

    seed_cfg = await config_for_key(pool, SEED)
    rules = await _rules_map(pool, (SEED, MID, TARGET))
    brain = ScriptedEvaluator({SEED: ("switch", MID)}, rules)

    async def missing(_pool, _key):
        return None

    res = await resolve_entry_candidate(pool, seed_cfg, "問句",
                                        config_lookup=missing, optimizer=brain)
    assert res.committed_key is None
    assert res.stop_reason == "unknown_or_disabled_delegate"


# ── ④ telemetry 真落庫（走真 HTTP 路徑，evaluator 仍為腳本化） ────────────────
@pytest.mark.req("face-exit-before-grounding:1")
def test_resolver_telemetry_persists_to_usage_events(migrated_db, monkeypatch):
    import asyncpg
    from fastapi.testclient import TestClient

    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
    monkeypatch.setenv("PREENTRY_ROUTABILITY_FACETS", ",".join((SEED, MID, TARGET)))

    from app import app
    from services.conversational_config import reset_cache
    from services.llm_answer_optimizer import LLMAnswerOptimizer
    reset_cache()

    real_step = LLMAnswerOptimizer.conversational_step_result

    async def scripted(self, rules, system_md, state, msg, **kw):
        """以 delegates 白名單反查目前是哪一跳（末端無白名單＝TARGET）。"""
        specs = kw.get("delegates") or []
        if not specs:
            scope, delegate = "stay", None
        else:
            scope, delegate = "switch", specs[0][0]
        out = {"action": "ask", "next_question": "q", "scope": scope}
        if delegate:
            out["delegate_facet_key"] = delegate
        from tests.support.brain_stub import as_step_result
        return as_step_result(out)          # 任務 8：引擎/resolver 改吃 StepResult

    async def _q(sid):
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            return await conn.fetchval(
                "SELECT decision_snapshot FROM usage_events WHERE session_id=$1"
                " AND decision_snapshot ? 'resolver' ORDER BY id DESC LIMIT 1", sid)
        finally:
            await conn.close()

    LLMAnswerOptimizer.conversational_step_result = scripted
    sid = f"rollout-tm-{uuid.uuid4().hex[:8]}"
    snap = None
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/message", json={
                "message": "幫我查點退帳單金額", "vendor_id": 2,
                "target_user": "property_manager", "mode": "b2b", "role_id": "20151",
                "session_id": sid, "stream": False})
            assert r.status_code == 200, r.text
            # ⚠️ usage_events 是 `asyncio.create_task` fire-and-forget 寫入——
            #    必須**在 client 仍開著**（app 的 event loop 還活著）時等它落地，
            #    否則測試會拿到 None 而誤判成「telemetry 未落庫」。
            for _ in range(25):
                snap = asyncio.run(_q(sid))
                if snap is not None:
                    break
                time.sleep(0.2)
    finally:
        LLMAnswerOptimizer.conversational_step_result = real_step
    assert snap is not None, "resolver telemetry 未落庫"
    snap = json.loads(snap) if isinstance(snap, str) else snap
    t = snap["resolver"]
    for field in ("seed_facet", "final_committed_facet", "hop_count", "hops",
                  "fail_open", "fallback_reason", "resolver_model_calls",
                  "resolver_latency_ms"):
        assert field in t, f"telemetry 缺欄位 {field}"
    assert t["seed_facet"] == SEED
    assert all(set(h) >= {"candidate_facet", "scope", "delegate_facet_key",
                          "decision_source", "fail_open"} for h in t["hops"])
    assert "幫我查點退帳單金額" not in json.dumps(t, ensure_ascii=False), "telemetry 不得含聊天內容"
