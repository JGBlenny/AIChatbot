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

# ⚠️ 2026-08-26「統一 mini」後，brain 與第 2 輪合成**同為 gpt-4o-mini**，
#    故 target-call 辨識**不得再以 model 名區分**，一律以 max_tokens=400 認 brain 輪。
FROZEN_BRAIN = {"model": os.getenv("PRESALES_SYNTH_MODEL", "gpt-4o-mini"),
                "temperature": 0.4, "max_tokens": 400}
REPETITIONS = 3
MAX_TARGET_CALLS, MAX_ALL_CALLS = 30, 60
INFRA_RETRIES = 2
_INFRA = ("timeout", "timed out", "rate limit", "429", "500", "502", "503", "504", "connection")

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".p3_true_brain_evidence.json")


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
    prev = {k: os.environ.get(k) for k in ("USE_MOCK_JGB_API", "PREENTRY_ROUTABILITY_GATE",
                                           "PREENTRY_ROUTABILITY_FACETS")}
    os.environ["USE_MOCK_JGB_API"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "true"          # ⚠️ 只在本行程
    # ⚠️ facet-scoped rollout：只開旗標**不會**啟用 resolver（fail-safe）。
    #    這一行漏掉的話，本檔會安靜地驗到舊路徑——M0 修的就是這個。
    os.environ["PREENTRY_ROUTABILITY_FACETS"] = ",".join((SEED, MID, TARGET))
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
    from tests.support.resolver_capture import build_hop_evidence, classify_delegate_drop
    real_resolve = resp_mod.resolve_entry_candidate
    real_step = LLMAnswerOptimizer.conversational_step_result
    state = {"all": [], "target": [], "resolutions": [], "raw": [], "hops": []}

    def spy_cc(*a, **kw):
        is_target = kw.get("max_tokens") == FROZEN_BRAIN["max_tokens"]
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
        result = await real_step(self, rules, system_md, st, msg, **kw)   # 任務 8：回 StepResult
        normalized = result.payload if result else None
        raw = state["raw"][mark] if len(state["raw"]) > mark else None
        specs = kw.get("delegates") or []
        allowed = [d if isinstance(d, str) else d[0] for d in specs]
        if allowed:                              # 只記 resolver 的那幾跳（進場後的 brain 不帶白名單）
            state["hops"].append(build_hop_evidence("(pending)", raw, allowed, normalized))
        # ★ P3-B：即使 payload 被 action validator 擋掉，parsed scope 仍要看得到
        state.setdefault("parsed", []).append({
            "payload_is_none": normalized is None,
            "scope": getattr(result, "scope", None),
            "delegate": getattr(result, "delegate_facet_key", None),
            "reject_reason": getattr(result, "reject_reason", None),
            "raw_scope": classify_delegate_drop(raw, allowed or ["_"], normalized).get("raw_scope"),
        })
        return result

    provider.chat_completion = spy_cc
    resp_mod.resolve_entry_candidate = spy_resolve
    LLMAnswerOptimizer.conversational_step_result = spy_step
    global _RIG
    _RIG = state
    yield state
    provider.chat_completion = real_cc
    resp_mod.resolve_entry_candidate = real_resolve
    LLMAnswerOptimizer.conversational_step_result = real_step


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
    """**P3 起改用 v6 regression ruler**（`tests/support/v6_regression_ruler.py`，已凍結）。

    ⚠️ 舊的 v2 尺（下方保留供追溯）期望的是 contracts **方法級 mock** 的字面
    （「25,000」等）；contracts 已於 2026-08-25 遷入 transport 替身，
    且 formatter 對點退 action **不渲染租金**——那正是 v5 被誤判為 value_not_used 的成因。
    """
    from tests.support.v6_regression_ruler import v6_regression_ruler
    return v6_regression_ruler()


def _ruler_v2_superseded():
    """（已被 v6 取代，保留供追溯，不再使用）"""
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


_EVIDENCE = {"protocol": "p3-run-parameters-frozen.md",
             "variant": "P3-true-brain-regression（A：delegation／B：mid-session salvage）",
             "brain_model_env": os.getenv("PRESALES_SYNTH_MODEL", "(unset→config default)"),
             "runs": [], "mid_session": []}


def _post(client, message, sid):
    return client.post("/api/v1/message", json={
        "message": message, "vendor_id": 2, "target_user": "property_manager",
        "mode": "b2b", "role_id": "20151", "session_id": sid, "stream": False})


@pytest.mark.req("face-exit-before-grounding:1")
def test_gated_resolver_vertical_slice(client, rig):
    from tests.support.brain_grounding import evaluate_brain_grounding

    spec = _ruler()
    # ── M0 守門：resolver 必須真的被啟用，否則直接紅（不得安靜驗到舊路） ──
    assert os.getenv("PREENTRY_ROUTABILITY_GATE", "").lower() == "true", "gate 未開"
    _allow = {f.strip() for f in os.getenv("PREENTRY_ROUTABILITY_FACETS", "").split(",") if f.strip()}
    assert SEED in _allow, (
        f"seed 面向 {SEED} 不在 PREENTRY_ROUTABILITY_FACETS={_allow}——"
        "resolver 不會啟用，本檔會驗到舊路徑（feature flag 語義改變時的靜默失效）")

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


# ════════════════════════════════════════════════════════════════════════════
# P3-B：mid-session scope salvage regression（Task 8 新增的 production behavior）
# ════════════════════════════════════════════════════════════════════════════

MID_SESSION_OFFTOPIC = "我要看團隊成員的權限設定"     # 明顯不屬 contract_closeout 職責


def _run_mid_session(client, rig, salvage: str):
    """三輪：進場 → 給識別碼 → **岔到別領域**；回傳該輪的 parsed 紀錄與控制流觀察。"""
    os.environ["FACET_SCOPE_SALVAGE"] = salvage
    sid = f"p3b-{salvage}-{uuid.uuid4().hex[:8]}"
    parsed_before = len(rig.get("parsed", []))
    _post(client, QUERY, sid)
    _post(client, TURN2, sid)
    r3 = _post(client, MID_SESSION_OFFTOPIC, sid)
    parsed = rig.get("parsed", [])[parsed_before:]
    rows = _session_rows(sid)
    _cleanup(sid)
    return {"salvage": salvage, "session_id": sid, "http3": r3.status_code,
            "answer3": (r3.json().get("answer") or "")[:200] if r3.status_code == 200 else None,
            "parsed_turns": parsed,
            "session_rows": rows,
            # 控制流可觀察量：會話是否被關掉（switch 語義）＝ 沒有殘留 COLLECTING
            "left_collecting": [r["state"] for r in rows if r["state"] == "COLLECTING"]}


@pytest.mark.req("conversational-routing-execution:5.2")
def test_mid_session_scope_salvage(client, rig):
    """B：raw payload 的 scope=switch 必須活著走到 consumer。

    判準（p3-run-parameters-frozen.md §三）：
      ① raw payload 確實含 scope=switch
      ② 即使 action 越界，parsed StepResult.scope 仍為 'switch'
         ——**若真模型本輪未自然產生越界 action，如實記錄「未觀察到」**，
           不得以決定性注入冒充（該分支已由 unit 16 條覆蓋）
      ③ SALVAGE=on 時 observable control flow 真的改變（payload 被擋仍退出）
      ④ SALVAGE=off 時維持舊行為
    """
    prev = os.environ.get("FACET_SCOPE_SALVAGE")
    try:
        off = _run_mid_session(client, rig, "false")
        on = _run_mid_session(client, rig, "true")
    finally:
        if prev is None:
            os.environ.pop("FACET_SCOPE_SALVAGE", None)
        else:
            os.environ["FACET_SCOPE_SALVAGE"] = prev

    _EVIDENCE["mid_session"] = [off, on]
    failures = []

    # ① 真模型在岔題輪是否輸出 switch（raw 層）
    def _switch_turns(rec):
        return [t for t in rec["parsed_turns"] if t.get("scope") == "switch"]

    if not _switch_turns(off) and not _switch_turns(on):
        failures.append("①: 兩次執行的 raw payload 都沒有 scope=switch——"
                        "本情境未觸發中途切換，B 無法取證（非 salvage 邏輯的紅）")

    # ② **必須是「payload 被擋 ∧ scope=switch」那一格**才算觀察到 salvage 適用情境。
    #    ⚠️ 只看 payload_is_none 是不夠的：scope=stay 的拒絕（如 missing_next_question）
    #       根本不會走 salvage 分支，拿它去解釋 on/off 的差異＝把雜訊當證據。
    rejected = [t for rec in (off, on) for t in rec["parsed_turns"]
                if t["payload_is_none"] and t.get("scope") == "switch"]
    rejected_any = [t for rec in (off, on) for t in rec["parsed_turns"] if t["payload_is_none"]]
    _EVIDENCE["b2_salvage_applicable_observed"] = bool(rejected)
    _EVIDENCE["b2_any_rejection_observed"] = [t.get("reject_reason") for t in rejected_any]
    _EVIDENCE["b2_note"] = (
        "真模型自然產生「payload 被擋 ∧ scope=switch」，salvage 情境成立" if rejected else
        "**未觀察到 salvage 適用情境**：本輪的拒絕皆為 scope=stay（salvage 分支依定義不會啟動），"
        "故 on/off 的控制流差異**不可歸因於 salvage**；該分支由 unit "
        "test_step_contract_layers_req.py 覆蓋，不以注入或雜訊冒充")
    for t in rejected:
        if t.get("scope") != t.get("raw_scope"):
            failures.append(f"②: 越界輪的 parsed scope={t['scope']} 與 raw={t['raw_scope']} 不一致")

    # ③④ 控制流：有越界輪時 on/off 必須不同；沒有時兩者應一致（零回歸）
    if rejected:
        if off["left_collecting"] == on["left_collecting"]:
            failures.append("③: 出現 salvage 適用輪，但 on/off 控制流相同——salvage 未生效")
    else:
        # ⚠️ 這裡**不比對** on/off 的控制流：兩次是各自獨立的真模型會話，
        #    輸出本來就會不同，差異不構成任何結論（既不能證明 salvage 有效，也不能證明越權）。
        _EVIDENCE["b34_note"] = ("salvage 適用情境未出現 ⇒ ③④ **INCONCLUSIVE**；"
                                 "跨會話的控制流差異是隨機性，不作為證據")

    _EVIDENCE["b_verdict"] = ("B_OK" if (not failures and rejected)
                              else "B_INCONCLUSIVE" if not failures else "B_NOT_VALIDATED")
    _EVIDENCE["b_failures"] = failures
    assert not failures, "B 未成立：\n  " + "\n  ".join(failures)


@pytest.fixture(scope="module", autouse=True)
def _write_evidence():
    yield
    _EVIDENCE["target_scope_calls"] = len(_RIG["target"]) if _RIG else None
    _EVIDENCE["all_provider_calls"] = len(_RIG["all"]) if _RIG else None
    # ⚠️ **每一次 brain 呼叫的解析結果**都留檔（不只 resolver hop）——
    #    P3 第 2 次執行時，in-session 那一輪被擋在哪一條規則上只能用猜的，
    #    因為當時只保存了 resolver hop 的 attribution。
    _EVIDENCE["all_parsed_turns"] = (_RIG.get("parsed") if _RIG else None) or []
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump(_EVIDENCE, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 gated-resolver evidence → {os.path.abspath(EVIDENCE_PATH)}")
