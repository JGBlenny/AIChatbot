"""e2e：B′ production-equivalent diagnostic variant（spec face-exit-before-grounding）。

⚠️ **不是「把 B 再跑一次」**：B 用 `_preentry_routable`，實測證明它給 `billing_anomaly`
的是 **base** system context（digest `d1f88c90…`），而非該面向真正 in-session 的
「帳單異常」脈絡（`2158ebdc…`）。B′ 消掉這個 confounder，只回答一句反事實：

> `billing_anomaly` 在它自己真正的 in-session responsibility context 下，
> 到底會不會接受這句 query？

凍結協議：`.kiro/specs/face-exit-before-grounding/r1b-prime-protocol-frozen.md`
（model／temperature／max_tokens／query bytes／repetitions／retry／
 target≤8・all_provider≤20／**四格填滿的裁決表**，皆先於本次執行凍結並 commit。）

⚠️ 全程 production path：由 `billing_anomaly` 自己建立 session（direct entry），
context 組裝與 scope 判定一律真 production；**不人工餵 context**、
**`PREENTRY_ROUTABILITY_GATE` 維持 false**。

⚠️ 會真的花錢（目標 seam 名目 3 次）。需 `RUN_E2E=1` ＋ 整服務；預設略過、不擋 CI。
"""
import hashlib
import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.e2e

QUERY = "幫我查點退帳單金額"
FACE = "billing_anomaly"
PERSONA = "pm_billing_anomaly"
EXPECTED_INSESSION_CTX = "2158ebdc2d8fe7e6"     # 協議 §3 的成立條件
EXPECTED_RULES_DIGEST = "aefa054899cdd7e6"      # 以此區分 billing_anomaly 的那次呼叫

# ⚠️ 2026-08-26「統一 mini」後，brain 與第 2 輪合成**同為 gpt-4o-mini**，
#    故 target-call 辨識**不得再以 model 名區分**，一律以 max_tokens=400 認 brain 輪。
FROZEN_BRAIN = {"model": os.getenv("PRESALES_SYNTH_MODEL", "gpt-4o-mini"),
                "temperature": 0.4, "max_tokens": 400}
REPETITIONS = 3
MAX_TARGET_SCOPE_CALLS = 8
MAX_ALL_PROVIDER_CALLS = 20
INFRA_RETRIES = 2
_INFRA_MARKERS = ("timeout", "timed out", "rate limit", "ratelimit", "429",
                  "500", "502", "503", "504", "connection", "apiconnection")

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".r1b_prime_evidence.json")


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
    pass


class Ledger:
    def __init__(self):
        self.all_calls, self.target_calls = [], []

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
    prev = os.environ.get("USE_MOCK_JGB_API")
    os.environ["USE_MOCK_JGB_API"] = "true"
    # 協議 §1：B′ 不經 pre-entry seam，gate 維持 false
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"
    yield
    if prev is None:
        os.environ.pop("USE_MOCK_JGB_API", None)
    else:
        os.environ["USE_MOCK_JGB_API"] = prev


@pytest.fixture(scope="module")
def client(_env):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


_RIG = None


@pytest.fixture(scope="module")
def rig(client):
    provider = client.app.state.llm_answer_optimizer.llm_provider
    real = provider.chat_completion
    led, captures = Ledger(), []

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
            captures.append({"system_msg": sysmsg, "system_sha": _sha(sysmsg),
                             "system_len": len(sysmsg), "user_prompt": usermsg,
                             "user_sha": _sha(usermsg),
                             "history_block": "【最近對話】" in usermsg,
                             "scope_result_raw": scope_raw, "raw_json": raw[:400]})
        return result

    provider.chat_completion = spy
    global _RIG
    _RIG = {"ledger": led, "captures": captures}
    yield _RIG
    provider.chat_completion = real


def _face_context():
    """取 billing_anomaly 的 rules 與 in-session system context（digest 對照用）。"""
    import asyncio

    import asyncpg

    async def _q():
        from services.conversational_config import config_for_key, reset_cache
        from services.conversational_rules import load_rules
        from services.system_context import get_system_context
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
        try:
            cfg = await config_for_key(pool, FACE)
            rules = await load_rules(pool, PERSONA)
            key = (getattr(cfg, "topic_scope", None) or {}).get("category")
            ctx = await get_system_context(pool, key)
            return {"rules": rules, "rules_digest": _sha(rules),
                    "insession_ctx_key": key, "insession_ctx_digest": _sha(ctx),
                    "insession_ctx": ctx}
        finally:
            await pool.close()
    return asyncio.run(_q())


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


_EVIDENCE = {"protocol": "r1b-prime-protocol-frozen.md", "variant": "B-prime",
             "query": QUERY, "query_sha": _sha(QUERY), "repetitions": REPETITIONS, "runs": []}


@pytest.mark.req("face-exit-before-grounding:1")
def test_b_prime_insession_scope_verdict(client, rig):
    ctx = _face_context()
    _EVIDENCE["face_context"] = {k: v for k, v in ctx.items() if k not in ("rules", "insession_ctx")}
    assert ctx["rules_digest"] == EXPECTED_RULES_DIGEST, \
        f"rules digest 與協議不符：{ctx['rules_digest']} != {EXPECTED_RULES_DIGEST}"

    for rep in range(1, REPETITIONS + 1):
        sid = f"r1bp-{rep}-{uuid.uuid4().hex[:8]}"
        before = len(rig["captures"])
        attempt = 0
        while True:
            try:
                r = client.post("/api/v1/message", json={
                    "message": QUERY, "vendor_id": 2, "target_user": "property_manager",
                    "mode": "b2b", "role_id": "20151", "session_id": sid,
                    "stream": False, "trigger_facet_key": FACE})
                break
            except BudgetExceeded:
                raise
            except BaseException as e:                      # noqa: BLE001
                if _is_infra(e) and attempt < INFRA_RETRIES:
                    attempt += 1
                    time.sleep(2 ** attempt)
                    continue
                raise

        new = rig["captures"][before:]
        # 只採計 billing_anomaly 的那次（協議 §2）：以其 rules 原文出現於 system message 判定
        mine = [c for c in new if ctx["rules"] and ctx["rules"] in c["system_msg"]]
        others = [c for c in new if c not in mine]
        rec = {"repetition": rep, "session_id": sid, "http_status": r.status_code,
               "session_rows": _session_rows(sid),
               "counted_call": None,
               "uncounted_calls": [{"system_sha": c["system_sha"],
                                    "scope_result_raw": c["scope_result_raw"]} for c in others],
               "answer": (r.json().get("answer") if r.status_code == 200 else None)}
        if mine:
            c = mine[0]
            rec["counted_call"] = {
                "face_identity": FACE, "rules_digest": ctx["rules_digest"],
                "system_context_key": ctx["insession_ctx_key"],
                "system_context_in_prompt": ctx["insession_ctx"] in c["system_msg"],
                "system_context_digest_expected": ctx["insession_ctx_digest"],
                "system_sha": c["system_sha"], "system_len": c["system_len"],
                "user_prompt": c["user_prompt"], "user_sha": c["user_sha"],
                "history_block": c["history_block"],
                "scope_result_raw": c["scope_result_raw"], "raw_json": c["raw_json"]}
        _EVIDENCE["runs"].append(rec)
        _cleanup(sid)

    counted = [r["counted_call"] for r in _EVIDENCE["runs"]]
    assert all(counted), "有 repetition 未捕捉到 billing_anomaly 的 brain 呼叫"
    # 協議 §3 成立條件：必須是 in-session context，否則 B′ 無效
    assert all(c["system_context_in_prompt"] for c in counted), \
        ("B′ 無效：送進 producer 的 system message 不含 in-session（帳單異常）脈絡——"
         "confounder 未被消掉，須先查明原因再談結果")
    verdicts = [c["scope_result_raw"] for c in counted]
    _EVIDENCE["verdicts"] = verdicts
    _EVIDENCE["switch_count"] = sum(1 for v in verdicts if v == "switch")
    print(f"\n🔎 B′ verdicts = {verdicts}（switch {_EVIDENCE['switch_count']}/3）")


@pytest.fixture(scope="module", autouse=True)
def _write_evidence():
    yield
    led = _RIG["ledger"] if _RIG else None
    _EVIDENCE["all_provider_calls"] = len(led.all_calls) if led else None
    _EVIDENCE["target_scope_calls"] = len(led.target_calls) if led else None
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump(_EVIDENCE, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 B′ evidence → {os.path.abspath(EVIDENCE_PATH)}")
