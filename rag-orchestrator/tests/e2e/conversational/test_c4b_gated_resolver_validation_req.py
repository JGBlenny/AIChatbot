"""e2e：`C4b-gated-resolver-validation`（spec face-exit-before-grounding）。

⚠️ **不是重跑舊 C4b**：舊歷史（C4a CONFIRMED／C4b NOT PASSED／gate CLOSED）不動、不回填。
本檔是**新 implementation 的 acceptance evidence**。

凍結協議：`.kiro/specs/face-exit-before-grounding/c4b-gated-resolver-validation-protocol-frozen.md`

要同時成立五項（只看最終答案不算過）：

```text
① chain     bill_diagnosis → billing_anomaly → contract_closeout（逐跳 verdict／delegate）
② session   只 commit contract_closeout
③ grounding contract_closeout 的 execution 真的跑到
④ answer    最終回答使用該 grounding（沿用 C4b v2 尺）
⑤ verdict   每一跳的 reason 必須是 responsibility_contract——**fail_open 不算過**
```

⚠️ 隔離：delegates 只寫**測試庫**兩列並於結束**還原**；`PREENTRY_ROUTABILITY_GATE`
只在本行程開啟（`.env`／compose 一律不動）。⚠️ 會真的花錢（名目 5 次／run × 3 runs）。
"""
import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.e2e

QUERY = "幫我查點退帳單金額"
TURN2 = "678"                      # 方法級 mock 的合約 id（決定性）
SEED, MID, TARGET = "bill_diagnosis", "billing_anomaly", "contract_closeout"
EXPECTED_CHAIN = [(SEED, "switch", MID), (MID, "switch", TARGET), (TARGET, "stay", None)]

FROZEN_BRAIN = {"model": "gpt-4o", "temperature": 0.4, "max_tokens": 400}
REPETITIONS = 3
MAX_TARGET_CALLS, MAX_ALL_CALLS = 30, 60
INFRA_RETRIES = 2
_INFRA = ("timeout", "timed out", "rate limit", "429", "500", "502", "503", "504", "connection")

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".c4b_gated_v4_evidence.json")


def _conn_kwargs():
    return dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "aichatbot"),
                password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                database=os.getenv("DB_NAME", "aichatbot_test"))


class BudgetExceeded(RuntimeError):
    pass


def _is_infra(e) -> bool:
    if isinstance(e, (AssertionError, BudgetExceeded)):
        return False
    return any(m in f"{type(e).__name__} {e}".lower() for m in _INFRA)


# ── fixture：只動測試庫，結束還原 ────────────────────────────────────────────
@pytest.fixture(scope="module")
def _delegates_fixture():
    import asyncio

    import asyncpg

    # ⚠️ `when` **逐字取自現有 authoritative persona responsibility wording**，不自行發明 ownership：
    #    bill_diagnosis 規則：「帳單金額組成/看不到帳單（帳單異常）… → scope="switch"」
    #    billing_anomaly 規則：「封存/點退帳單處理、其他領域完整新問題 → scope="switch"」
    edges = {SEED: {"target": MID, "when": "帳單金額組成/看不到帳單"},
             MID: {"target": TARGET, "when": "封存/點退帳單處理"}}
    saved = {}

    def _extend_declared_schema(rules_text: str) -> str:
        """(a) output-contract repair：把 `delegate_facet_key` 升格進**規則宣告的 JSON 形狀**。

        v3 證據：模型輸出的鍵集合與 persona 宣告的形狀逐鍵吻合，且不含附加在規則之後的
        delegation instruction。⇒ 該改的是 schema declaration，不是再堆 wording。

        ⚠️ 作用域只限**本 fixture 修改的兩個面向**（有宣告 delegates 者）；
        其餘 Face 的 prompt／output shape 逐位元不變。
        """
        marker = "每輪輸出 JSON："
        i = rules_text.find(marker)
        if i < 0:
            return rules_text                     # 沒有宣告行 → 不動（由斷言在下方擋下）
        j = rules_text.find("\n", i)
        line = rules_text[i:j if j > 0 else len(rules_text)]
        k = line.rfind("}")
        if k < 0:
            return rules_text
        extended = (line[:k] + ',"delegate_facet_key":"…（見下）"' + line[k:]
                    + "\n【delegate_facet_key 規則】"
                      "scope=\"stay\" → 必須為 \"\"；"
                      "scope=\"switch\" 且符合上列已宣告的轉交對象 → 必須填該對象的鍵；"
                      "scope=\"switch\" 但無法對應合法轉交對象 → \"\"。")
        return rules_text[:i] + extended + (rules_text[j:] if j > 0 else "")

    async def _apply():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            for facet, edge in edges.items():
                row = await conn.fetchrow(
                    "SELECT id, generation_metadata, answer FROM knowledge_base "
                    "WHERE category='對話規則' AND is_active "
                    "  AND generation_metadata->'conversational_config'->>'key' = $1", facet)
                if row is None:
                    return False
                md = row["generation_metadata"]
                md = json.loads(md) if isinstance(md, str) else dict(md)
                saved[row["id"]] = (json.dumps(md, ensure_ascii=False), row["answer"])
                md.setdefault("conversational_config", {})["responsibility"] = {
                    "delegates": [dict(edge)]}
                new_rules = _extend_declared_schema(row["answer"] or "")
                if "delegate_facet_key" not in new_rules:
                    return False                  # 宣告行找不到＝前提不成立，不硬跑
                await conn.execute(
                    "UPDATE knowledge_base SET generation_metadata=$2::jsonb, answer=$3 "
                    "WHERE id=$1", row["id"], json.dumps(md, ensure_ascii=False), new_rules)
            return True
        finally:
            await conn.close()

    async def _restore():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            for kid, (original_md, original_rules) in saved.items():
                await conn.execute(
                    "UPDATE knowledge_base SET generation_metadata=$2::jsonb, answer=$3 "
                    "WHERE id=$1", kid, original_md, original_rules)
        finally:
            await conn.close()

    try:
        ok = asyncio.run(_apply())
    except Exception as e:                                   # pragma: no cover
        pytest.skip(f"無法寫入測試庫 delegates fixture：{e}")
        return
    if not ok:
        asyncio.run(_restore())
        pytest.skip("面向設定未供裝")
        return
    yield edges
    asyncio.run(_restore())                                   # ★ 一定還原


@pytest.fixture(scope="module")
def _env(_delegates_fixture):
    prev = {k: os.environ.get(k) for k in ("USE_MOCK_JGB_API", "PREENTRY_ROUTABILITY_GATE")}
    os.environ["USE_MOCK_JGB_API"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "true"          # ⚠️ 只在本行程
    yield
    for k, v in prev.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture(scope="module")
def client(_env):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


_RIG = None


@pytest.fixture(scope="module")
def rig(client):
    """passthrough spy：記呼叫預算＋攔截 resolver 結果（原樣委派）。"""
    provider = client.app.state.llm_answer_optimizer.llm_provider
    real_cc = provider.chat_completion
    from services import responsibility as resp_mod
    from services.llm_answer_optimizer import LLMAnswerOptimizer
    from tests.support.resolver_capture import build_hop_evidence
    real_resolve = resp_mod.resolve_entry_candidate
    real_step = LLMAnswerOptimizer.conversational_step
    state = {"all": [], "target": [], "resolutions": [], "raw": [], "hops": []}

    def spy_cc(*a, **kw):
        is_target = (kw.get("model") == FROZEN_BRAIN["model"]
                     and kw.get("max_tokens") == FROZEN_BRAIN["max_tokens"])
        if len(state["all"]) + 1 > MAX_ALL_CALLS:
            raise BudgetExceeded(f"all_provider_calls > {MAX_ALL_CALLS}")
        if is_target and len(state["target"]) + 1 > MAX_TARGET_CALLS:
            raise BudgetExceeded(f"target_scope_calls > {MAX_TARGET_CALLS}")
        state["all"].append(kw.get("model"))
        result = real_cc(*a, **kw)
        if is_target:
            state["target"].append(kw.get("model"))
            state["raw"].append(result)          # ★ 原始 provider JSON（歸因用）
        return result

    async def spy_resolve(*a, **kw):
        res = await real_resolve(*a, **kw)
        state["resolutions"].append({"committed": res.committed_key,
                                     "stop_reason": res.stop_reason,
                                     "chain": list(res.chain or [])})
        return res

    async def spy_step(self, rules, system_md, st, msg, **kw):
        """★ raw output attribution：原始 payload ／ 白名單 ／ 正規化結果三者並列。

        只在測試側 spy，**不改 production 契約**——production 的 conversational_step
        仍只回正規化後的 dict。
        """
        mark = len(state["raw"])
        normalized = await real_step(self, rules, system_md, st, msg, **kw)
        raw = state["raw"][mark] if len(state["raw"]) > mark else None
        specs = kw.get("delegates") or []
        allowed = [d if isinstance(d, str) else d[0] for d in specs]
        if allowed:                              # 只記 resolver 的那幾跳（進場後的 brain 不帶白名單）
            state["hops"].append(build_hop_evidence("(pending)", raw, allowed, normalized))
        return normalized

    provider.chat_completion = spy_cc
    resp_mod.resolve_entry_candidate = spy_resolve
    LLMAnswerOptimizer.conversational_step = spy_step
    global _RIG
    _RIG = state
    yield state
    provider.chat_completion = real_cc
    resp_mod.resolve_entry_candidate = real_resolve
    LLMAnswerOptimizer.conversational_step = real_step


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
                            "config_key": cd.get("config_key")})
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


def _ruler():
    """沿用 C4b v2 尺；期望值取自方法級 contracts mock（決定性）。"""
    from tests.support.brain_grounding import BrainGroundingAssertion
    return BrainGroundingAssertion(
        case="c4b-gated-resolver", execution_face=TARGET, fixture_bill_id=678,
        user_turns=(QUERY, TURN2),
        answer_must_contain=(("信義區套房A",), ("25,000", "25000")),
        answer_must_not_contain=("7,500", "18,000", "1,200"),
        foil_provenance={"7,500": "bills fixture 900003.total",
                         "18,000": "bills fixture 900001.total",
                         "1,200": "bills fixture 900002.total"},
        generic_fallback_markers=("請洽客服", "一般來說", "無法查詢", "NO_MATCH"),
        literal_provenance={"信義區套房A": "_mock_get_contracts data[0].title",
                            "25,000": "_mock_get_contracts data[0].rent"},
        rationale="grounding 來自 contract_closeout 的 jgb_contracts execution")


_EVIDENCE = {"protocol": "c4b-gated-resolver-validation-v4-protocol-frozen.md",
             "variant": "C4b-gated-resolver-validation-v4", "runs": []}


def _post(client, message, sid):
    return client.post("/api/v1/message", json={
        "message": message, "vendor_id": 2, "target_user": "property_manager",
        "mode": "b2b", "role_id": "20151", "session_id": sid, "stream": False})


@pytest.mark.req("face-exit-before-grounding:1")
def test_gated_resolver_vertical_slice(client, rig):
    from tests.support.brain_grounding import evaluate_brain_grounding

    spec = _ruler()
    for rep in range(1, REPETITIONS + 1):
        sid = f"c4bg-{rep}-{uuid.uuid4().hex[:8]}"
        before = len(rig["resolutions"])
        attempt = 0
        while True:
            try:
                r1 = _post(client, QUERY, sid)
                r2 = _post(client, TURN2, sid)
                break
            except BudgetExceeded:
                raise
            except BaseException as e:                        # noqa: BLE001
                if _is_infra(e) and attempt < INFRA_RETRIES:
                    attempt += 1
                    time.sleep(2 ** attempt)
                    continue
                raise

        resolutions = rig["resolutions"][before:]
        hops_before = rig["_hops_mark"] if "_hops_mark" in rig else 0
        attribution = rig["hops"][hops_before:]
        rig["_hops_mark"] = len(rig["hops"])
        for _res in resolutions:                 # 依序把候選面向補回 attribution
            for _i, _h in enumerate(_res["chain"]):
                if _i < len(attribution):
                    attribution[_i]["candidate_face"] = _h.get("facet_key")
        answer = (r2.json().get("answer") or "") if r2.status_code == 200 else ""
        record = evaluate_brain_grounding(answer, spec) if answer else {"passed": False}
        for _res in resolutions:
            for _h in _res["chain"]:
                _h["fail_open"] = _h.get("reason") != "responsibility_contract"
        rec = {"repetition": rep, "session_id": sid,
               "http": [r1.status_code, r2.status_code],
               "turn1_answer": (r1.json().get("answer") if r1.status_code == 200 else None),
               "resolutions": resolutions,
               "hop_attribution": attribution,
               "session_rows": _session_rows(sid),
               "grounding_record": record}
        _EVIDENCE["runs"].append(rec)
        _cleanup(sid)

    # ── 逐項裁決（五項須同時成立）──
    failures = []
    for rec in _EVIDENCE["runs"]:
        tag = f"rep{rec['repetition']}"
        res = rec["resolutions"][0] if rec["resolutions"] else None
        if not res:
            failures.append(f"{tag}: resolver 未被呼叫（gate 未生效？）")
            continue
        chain = [(h.get("facet_key"), h.get("verdict"), h.get("delegate_to"))
                 for h in res["chain"]]
        if chain != EXPECTED_CHAIN:
            failures.append(f"{tag}①: chain={chain}")
        if res["committed"] != TARGET:
            failures.append(f"{tag}②: committed={res['committed']}")
        keys = [r["config_key"] for r in rec["session_rows"]]
        if keys != [TARGET]:
            failures.append(f"{tag}②: session rows={keys}")
        # ⑤ 防假綠：任一跳 fail_open 即不算過
        reasons = [h.get("reason") for h in res["chain"]]
        if any(r != "responsibility_contract" for r in reasons):
            failures.append(f"{tag}⑤: stay_source 非 model_verdict → {reasons}")
        if not rec["grounding_record"].get("passed"):
            failures.append(f"{tag}③④: grounding／answer 未通過 → "
                            f"{rec['grounding_record'].get('violated_dimensions')}")

    _EVIDENCE["verdict"] = "GATED_RESOLVER_VALIDATED" if not failures else "NOT_VALIDATED"
    _EVIDENCE["failures"] = failures
    assert not failures, "五項未同時成立：\n  " + "\n  ".join(failures)


@pytest.fixture(scope="module", autouse=True)
def _write_evidence():
    yield
    _EVIDENCE["target_scope_calls"] = len(_RIG["target"]) if _RIG else None
    _EVIDENCE["all_provider_calls"] = len(_RIG["all"]) if _RIG else None
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump(_EVIDENCE, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 gated-resolver evidence → {os.path.abspath(EVIDENCE_PATH)}")
