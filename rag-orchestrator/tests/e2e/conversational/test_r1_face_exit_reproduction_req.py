"""e2e：R1 diagnostic reproduction（spec face-exit-before-grounding，R1）。

⚠️ **這是 diagnostic reproduction，不是 acceptance benchmark。**
它不判「系統對不對」，只產生兩件事的 runtime 證據：

```text
A  bill_diagnosis 的 reroute residue——第二次進場的輸入是否與第一次語義等價
B  billing_anomaly 是否在 runtime 也拒絕同一句 query（目前只有讀規則的推論）
```

凍結協議：`.kiro/specs/face-exit-before-grounding/r1-protocol-frozen.md`
（model／temperature／max_tokens／query bytes／empty state／repetition／retry／
 target_scope_calls≤12／all_provider_calls≤30／裁決表，皆先於本次執行凍結。）

⚠️ **會真的花錢**：目標 seam 名目 9 次（A：3 次請求 ×2 brain；B：3 次），
另有共用 provider 的非目標呼叫（適用性把關、兜底合成）——兩者分開記。

⚠️ **不改 production**：`PREENTRY_ROUTABILITY_GATE` 只在本行程內設為 true 以觸達
production 判定邏輯（diagnostic invocation），不改 `.env`／compose，不進 production。

需 `RUN_E2E=1` ＋ 整服務。預設略過、不擋 CI。
"""
import hashlib
import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.e2e

QUERY = "幫我查點退帳單金額"
FACE_A = "bill_diagnosis"
FACE_B = "billing_anomaly"
PERSONA = {FACE_A: "pm_bill_diagnosis", FACE_B: "pm_billing_anomaly"}

FROZEN_BRAIN = {"model": "gpt-4o", "temperature": 0.4, "max_tokens": 400}
REPETITIONS = 3
MAX_TARGET_SCOPE_CALLS = 12
MAX_ALL_PROVIDER_CALLS = 30
INFRA_RETRIES = 2
_INFRA_MARKERS = ("timeout", "timed out", "rate limit", "ratelimit", "429",
                  "500", "502", "503", "504", "connection", "apiconnection")

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".r1_evidence.json")


def _sha(text) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_test"),
    )


class BudgetExceeded(RuntimeError):
    """超過凍結上限 → 委派前中止，不得續跑。"""


class Ledger:
    """兩個命題分開記：目標 seam 呼叫 vs 共用 provider 全部呼叫。"""

    def __init__(self):
        self.all_calls = []
        self.target_calls = []

    def note(self, kwargs) -> bool:
        is_target = (kwargs.get("model") == FROZEN_BRAIN["model"]
                     and kwargs.get("max_tokens") == FROZEN_BRAIN["max_tokens"]
                     and "response_format" in kwargs)
        if len(self.all_calls) + 1 > MAX_ALL_PROVIDER_CALLS:
            raise BudgetExceeded(f"all_provider_calls 超過 {MAX_ALL_PROVIDER_CALLS}")
        if is_target and len(self.target_calls) + 1 > MAX_TARGET_SCOPE_CALLS:
            raise BudgetExceeded(f"target_scope_calls 超過 {MAX_TARGET_SCOPE_CALLS}")
        rec = {"model": kwargs.get("model"), "temperature": kwargs.get("temperature"),
               "max_tokens": kwargs.get("max_tokens"), "target": is_target}
        self.all_calls.append(rec)
        if is_target:
            self.target_calls.append(rec)
        return is_target


def _is_infra(exc) -> bool:
    if isinstance(exc, (AssertionError, BudgetExceeded)):
        return False
    return any(m in f"{type(exc).__name__} {exc}".lower() for m in _INFRA_MARKERS)


@pytest.fixture(scope="module")
def _env():
    prev_mock = os.environ.get("USE_MOCK_JGB_API")
    os.environ["USE_MOCK_JGB_API"] = "true"
    yield
    if prev_mock is None:
        os.environ.pop("USE_MOCK_JGB_API", None)
    else:
        os.environ["USE_MOCK_JGB_API"] = prev_mock


@pytest.fixture(scope="module")
def client(_env):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def rig(client):
    """passthrough spy：記錄請求參數與回應內容，原樣委派、原樣回傳。"""
    provider = client.app.state.llm_answer_optimizer.llm_provider
    real = provider.chat_completion
    led = Ledger()
    captures = []

    def spy(*args, **kwargs):
        is_target = led.note(kwargs)
        result = real(*args, **kwargs)
        if is_target:
            msgs = kwargs.get("messages") or []
            sysmsg = next((m["content"] for m in msgs if m["role"] == "system"), "")
            usermsg = next((m["content"] for m in msgs if m["role"] == "user"), "")
            raw = (result or {}).get("content") or ""
            try:
                scope_raw = json.loads(raw).get("scope")
            except Exception:
                scope_raw = f"<unparsable:{raw[:40]}>"
            captures.append({
                "model": kwargs.get("model"), "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
                "system_sha": _sha(sysmsg), "system_len": len(sysmsg),
                "user_sha": _sha(usermsg), "user_prompt": usermsg,
                "query_in_prompt": QUERY in usermsg,
                "history_block": ("【最近對話】" in usermsg) or None,
                "scope_result_raw": scope_raw,
                "raw_json": raw[:400],
            })
        return result

    provider.chat_completion = spy
    global _RIG
    _RIG = {"ledger": led, "captures": captures}
    yield _RIG
    provider.chat_completion = real


def _session_rows(sid):
    import asyncio

    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            rs = await conn.fetch(
                "SELECT id, state, collected_data FROM form_sessions "
                "WHERE session_id=$1 AND form_id='conversational' ORDER BY id", sid)
            out = []
            for r in rs:
                cd = r["collected_data"]
                cd = json.loads(cd) if isinstance(cd, str) else (cd or {})
                out.append({"row_id": r["id"], "state": r["state"],
                            "config_key": cd.get("config_key"),
                            "collected_fields": cd.get("collected_fields"),
                            "asked_count": cd.get("asked_count")})
            return out
        finally:
            await conn.close()
    return asyncio.run(_q())


def _cleanup(sid):
    import asyncio

    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        finally:
            await conn.close()
    try:
        asyncio.run(_d())
    except Exception:
        pass


def _load_context_digests():
    """記錄兩個 seam 各自會拿到的 rules／system context digest（含實際 key，見協議 §1）。"""
    import asyncio

    import asyncpg

    async def _q():
        from services.conversational_config import config_for_key, reset_cache
        from services.conversational_rules import load_rules
        from services.system_context import get_system_context
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
        try:
            out = {}
            for face in (FACE_A, FACE_B):
                cfg = await config_for_key(pool, face)
                rules = await load_rules(pool, PERSONA[face])
                in_session_key = ((getattr(cfg, "topic_scope", None) or {}).get("category")
                                  or getattr(cfg, "persona_role", None))
                out[face] = {
                    "rules_digest": _sha(rules), "rules_len": len(rules or ""),
                    "in_session_ctx_key": in_session_key,
                    "in_session_ctx_digest": _sha(await get_system_context(pool, in_session_key)),
                    "preentry_ctx_key": getattr(cfg, "key", None),
                    "preentry_ctx_digest": _sha(await get_system_context(pool, getattr(cfg, "key", None))),
                }
            return out
        finally:
            await pool.close()
    return asyncio.run(_q())


#: teardown 取用（fixture 收掉後 getfixturevalue 取不到——C4b 已踩過一次）
_RIG = None

_EVIDENCE = {"protocol": "r1-protocol-frozen.md", "query": QUERY, "query_sha": _sha(QUERY),
             "repetitions": REPETITIONS, "goal_a": [], "goal_b": []}


@pytest.mark.req("face-exit-before-grounding:1")
def test_r1_goal_a_reroute_residue(client, rig):
    """A：同一 query 連走兩次進場，逐次記錄七欄，供 reroute residue 判定。"""
    digests = _load_context_digests()
    _EVIDENCE["context_digests"] = digests

    for rep in range(1, REPETITIONS + 1):
        sid = f"r1-a-{rep}-{uuid.uuid4().hex[:8]}"
        before = len(rig["captures"])
        attempt = 0
        while True:
            try:
                r = client.post("/api/v1/message", json={
                    "message": QUERY, "vendor_id": 2, "target_user": "property_manager",
                    "mode": "b2b", "role_id": "20151", "session_id": sid,
                    "stream": False, "trigger_facet_key": FACE_A})
                break
            except BudgetExceeded:
                raise
            except BaseException as e:                      # noqa: BLE001
                if _is_infra(e) and attempt < INFRA_RETRIES:
                    attempt += 1
                    time.sleep(2 ** attempt)
                    continue
                raise
        rows = _session_rows(sid)
        _EVIDENCE["goal_a"].append({
            "repetition": rep, "session_id": sid, "http_status": r.status_code,
            "brain_calls": rig["captures"][before:],
            "session_rows": rows,
            "answer": (r.json().get("answer") if r.status_code == 200 else None),
        })
        _cleanup(sid)

    # 本測試**不判對錯**：只要求證據齊全（診斷用，非 acceptance）
    for rec in _EVIDENCE["goal_a"]:
        assert rec["brain_calls"], f"rep {rec['repetition']} 未捕捉到任何 brain 呼叫"


@pytest.mark.req("face-exit-before-grounding:1")
def test_r1_goal_b_billing_anomaly_runtime_verdict(client, rig):
    """B：以 production `_preentry_routable` 判定 seam 實測 billing_anomaly。"""
    import asyncio

    import asyncpg

    async def _probe():
        from routers import chat as chat_mod
        from services.conversational_config import config_for_key
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
        try:
            cfg = await config_for_key(pool, FACE_B)
            assert cfg is not None, f"{FACE_B} 未在 registry"
            out = []
            for rep in range(1, REPETITIONS + 1):
                before = len(rig["captures"])
                routable = await chat_mod._preentry_routable(pool, cfg, QUERY)
                out.append({"repetition": rep, "routable": routable,
                            "verdict": "stay" if routable else "switch",
                            "brain_calls": rig["captures"][before:]})
            return out
        finally:
            await pool.close()

    prev = os.environ.get("PREENTRY_ROUTABILITY_GATE")
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "true"   # 僅本行程；不改 .env／compose
    try:
        _EVIDENCE["goal_b"] = asyncio.run(_probe())
    finally:
        if prev is None:
            os.environ.pop("PREENTRY_ROUTABILITY_GATE", None)
        else:
            os.environ["PREENTRY_ROUTABILITY_GATE"] = prev

    for rec in _EVIDENCE["goal_b"]:
        assert rec["brain_calls"], f"rep {rec['repetition']} 的判定 seam 未發生 brain 呼叫"


@pytest.fixture(scope="module", autouse=True)
def _write_evidence():
    yield
    led = _RIG["ledger"] if _RIG else None
    _EVIDENCE["all_provider_calls"] = len(led.all_calls) if led else None
    _EVIDENCE["target_scope_calls"] = len(led.target_calls) if led else None
    _EVIDENCE["all_call_log"] = led.all_calls if led else []
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump(_EVIDENCE, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 R1 evidence → {os.path.abspath(EVIDENCE_PATH)}")
