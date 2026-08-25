"""e2e：C4b production-brain smoke——真 brain 是否**使用** grounding 作答
（spec conversational-routing-execution 任務 6.2，R3.2／R7.2）。

## ⚠️ 本檔會**真的花錢**

```text
凍結參數        c4b-run-parameters-frozen.md（＋ c4b-ruler-v2-amendment.md §5）
逐案尺          c4b-ruler-v2-amendment.md（**v2**；v1 c4b-ruler-frozen.md 已被執行前 audit 反證）
量尺實作        tests/support/brain_grounding.py

預期成本量級    名目 4 案 × 3 次 × 2 次呼叫 = **24 次**；硬上限 **30 次**（含 retry 配額）
                第 1 輪 brain      gpt-4o        溫度 0.4  max_tokens 400
                第 2 輪 factual 合成 gpt-4o-mini  溫度 0.2  max_tokens 800
                以公開費率量級換算，整輪 < US$1（費率以帳單為準）
```

需 `RUN_E2E=1` ＋ 整服務（DB／embedding／semantic-model／OPENAI）。
⚠️ **`make test-unit` 全綠與本檔是否通過完全無關**——本檔預設略過、不擋 CI。

## 這一層在證什麼、不證什麼

```text
C4a  grounding 能被**送到** answer stage，且是**哪一筆**（OB-3 已機器斷言 identity）
C4b  真 brain **有使用該筆 grounding 中被問到的值**
```

**機器只判三件事**（v2 §3）：用了被問到的值／沒把明確屬於別筆的值當本筆答案／
沒退化成泛用回答。方向語義（如「能不能收回」）**不由機器判**——
`adjudication_flags` 命中只記錄，連同回答原文交 6.3 人工裁決。

## harness fidelity（六條，逐條都有機器檢查，不靠註解）

```text
F1 真 brain 真的跑到      `conversational_step` **未被** monkeypatch／腳本化；
                          以**純觀測**的 passthrough spy 記錄每一次 provider 呼叫，
                          斷言第 1 輪確實發生真 brain 呼叫（模型/溫度/上限逐項對得上）
F2 mock 只在外部依賴      只有 `JGBMockTransport`（jgb2 替身）；
                          engine → handler → adapter → grounding 全段真跑，一律不 mock
F3 直達只收窄 routing     `trigger_facet_key` 只跳過檢索與分類（非本層測量目標）；
                          進 Face 後仍走真 prepare → grounding → brain（等價性見
                          c4b-entry-path-equivalence-resolved.md）
F4 persona rules 硬失敗   規則缺失 → **fail**（不是 skip、不是默默降級後仍算有效 run）
F5 兩輪各走 frozen 組態   付費前先做**零成本 preflight**斷言解析後的模型/溫度/上限；
                          事後再以 spy 逐次比對，env fallback 讓兩輪同模型即紅
F6 重跑語義不被扭曲       3 次全過才算過；斷言紅**不 retry**；只有 infra 類可 retry（≤2）；
                          總呼叫 hard cap 30 由 spy 強制，超過即中止本輪
```
"""
import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.e2e

# ── 凍結參數（與 c4b-run-parameters-frozen.md 逐項對應；此處為斷言基準，不是預設值）──
# ⚠️ 2026-08-26「統一 mini」後，brain 與第 2 輪合成**同為 gpt-4o-mini**，
#    故 target-call 辨識**不得再以 model 名區分**，一律以 max_tokens=400 認 brain 輪。
FROZEN_BRAIN = {"model": os.getenv("PRESALES_SYNTH_MODEL", "gpt-4o-mini"),
                "temperature": 0.4, "max_tokens": 400}
FROZEN_SYNTH = {"model": "gpt-4o-mini", "temperature": 0.2, "max_tokens": 800}
RUNS_PER_CASE = 3
NOMINAL_CALLS = 24
HARD_CAP_CALLS = 30
INFRA_RETRIES_PER_RUN = 2

ROLE_ID = os.getenv("TEST_ROLE_ID", "20151")
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER = os.getenv("TEST_DIAG_TARGET_USER", "property_manager")

#: 基礎設施類失敗的判別字樣（凍結：只有這些可 retry）
_INFRA_MARKERS = ("timeout", "timed out", "rate limit", "ratelimit", "429",
                  "500", "502", "503", "504", "connection", "apiconnection")

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".c4b_evidence.json")


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_test"),
    )


# ══════════════════════════════════════════════════════════════════════════
# 期望值：**一律自 frozen fixture 推導**，不得手抄（v2 §4「期望值的來源」）
# ══════════════════════════════════════════════════════════════════════════

def _money_forms(v) -> "tuple[str, ...]":
    return (f"{v:,.0f}", f"{v:.0f}")


def _date_forms(ymd: int) -> "tuple[str, ...]":
    s = str(ymd)
    return (f"{s[:4]}/{s[4:6]}/{s[6:]}", f"{int(s[:4])}年{int(s[4:6])}月{int(s[6:])}日", s)


def _fixtures():
    from services.jgb.fixtures import BillFixtureTable
    t = BillFixtureTable()
    return {r["id"]: r for r in t.rows()}


def _status_label(status: int) -> str:
    from services.jgb.bills import STATUS_LABELS
    return STATUS_LABELS[status]


def _build_specs():
    """依 c4b-ruler-v2-amendment.md §4 逐案組尺；所有字面自 fixture 推導。"""
    from tests.support.brain_grounding import BrainGroundingAssertion

    f = _fixtures()
    b1, b2, b3 = f[900001], f[900002], f[900003]
    fallback = ("請洽客服", "請聯繫客服", "聯繫客服", "一般來說", "通常來說",
                "無法查詢", "查詢不到", "請提供帳單編號", "NO_MATCH")

    def foils(*pairs):
        """pairs: (literal, provenance)；回 (tuple_of_literals, provenance_dict)。"""
        return tuple(p[0] for p in pairs), {p[0]: p[1] for p in pairs}

    specs = []

    # ── c4b-diag-01 ─────────────────────────────────────────────────────
    lits, prov = foils(
        *[(s, "fixtures 900001.total") for s in _money_forms(b1["total"])],
        *[(s, "fixtures 900002.total") for s in _money_forms(b2["total"])],
        (b1["title"], "fixtures 900001.title"),
        (b2["title"], "fixtures 900002.title"),
    )
    specs.append(BrainGroundingAssertion(
        case="c4b-diag-01", execution_face="bill_diagnosis", fixture_bill_id=900003,
        user_turns=("幫我查點退帳單金額", "900003"),
        answer_must_contain=(_money_forms(b3["total"]),),
        answer_must_not_contain=lits, foil_provenance=prov,
        generic_fallback_markers=fallback,
        literal_provenance={_money_forms(b3["total"])[0]: "fixtures 900003.total"},
        rationale="問句直接問金額；required fact = amount_due（5.2 frozen）",
    ))

    # ── c4b-diag-02 ─────────────────────────────────────────────────────
    lits, prov = foils(
        *[(s, "fixtures 900003.total") for s in _money_forms(b3["total"])],
        *[(s, "fixtures 900002.total") for s in _money_forms(b2["total"])],
        (b2["title"], "fixtures 900002.title"),
        (b3["title"], "fixtures 900003.title"),
    )
    specs.append(BrainGroundingAssertion(
        case="c4b-diag-02", execution_face="bill_diagnosis", fixture_bill_id=900001,
        user_turns=("這張帳單現在還能不能收回", "900001"),
        answer_must_contain=((_status_label(b1["status"]),),),
        answer_must_not_contain=lits, foil_provenance=prov,
        generic_fallback_markers=fallback,
        adjudication_flags=(_status_label(b3["status"]), _status_label(b2["status"]),
                            "無法收回", "不能收回", "不可收回", "已失效"),
        literal_provenance={_status_label(b1["status"]): "fixtures 900001.status→STATUS_LABELS"},
        rationale=("machine PASS 只證明回答用了該筆狀態值；"
                   "可收回結論的語義正確性**不由機器證明**，交 6.3（v2 claim ceiling）"),
    ))

    # ── c4b-anom-01 ─────────────────────────────────────────────────────
    lits, prov = foils(
        *[(s, "fixtures 900001.date_start") for s in _date_forms(b1["date_start"])],
        *[(s, "fixtures 900001.date_end") for s in _date_forms(b1["date_end"])],
        *[(s, "fixtures 900001.total") for s in _money_forms(b1["total"])],
        *[(s, "fixtures 900003.total") for s in _money_forms(b3["total"])],
        (b1["title"], "fixtures 900001.title"),
        (b3["title"], "fixtures 900003.title"),
    )
    specs.append(BrainGroundingAssertion(
        case="c4b-anom-01", execution_face="billing_anomaly", fixture_bill_id=900002,
        user_turns=("這張帳單的計費期間是哪一段", "900002"),
        answer_must_contain=(_date_forms(b2["date_start"]), _date_forms(b2["date_end"])),
        answer_must_not_contain=lits, foil_provenance=prov,
        generic_fallback_markers=fallback,
        literal_provenance={_date_forms(b2["date_start"])[0]: "fixtures 900002.date_start",
                            _date_forms(b2["date_end"])[0]: "fixtures 900002.date_end"},
        known_non_discriminating=(
            "known_non_discriminating for instance identity at C4b layer："
            "900003 期間與 900002 相同；identity 屬 C4a OB-3，非本層聲稱之能力",),
        rationale="承 OB-1：date_start 與 date_end **各自**都要命中，不得以期間字串代過",
    ))

    # ── c4b-anom-02 ─────────────────────────────────────────────────────
    lits, prov = foils(
        *[(s, "fixtures 900001.total") for s in _money_forms(b1["total"])],
        *[(s, "fixtures 900002.total") for s in _money_forms(b2["total"])],
        *[(s, "fixtures 900001.date_start") for s in _date_forms(b1["date_start"])],
        (b1["title"], "fixtures 900001.title"),
        (b2["title"], "fixtures 900002.title"),
    )
    specs.append(BrainGroundingAssertion(
        case="c4b-anom-02", execution_face="billing_anomaly", fixture_bill_id=900003,
        user_turns=("這張帳單現在的狀態是什麼", "900003"),
        answer_must_contain=((_status_label(b3["status"]),),),
        answer_must_not_contain=lits, foil_provenance=prov,
        generic_fallback_markers=fallback,
        adjudication_flags=(_status_label(b1["status"]), _status_label(b2["status"]),
                            "待發送", "排定發送", "已失效"),
        literal_provenance={_status_label(b3["status"]): "fixtures 900003.status→STATUS_LABELS"},
        rationale="問句所問即狀態本身（5.2 frozen required fact = bill_status）",
    ))
    return specs


#: 面向 key ← execution_face（trigger_facet_key 直達用；registry by_key）
FACET_KEY = {"bill_diagnosis": "bill_diagnosis", "billing_anomaly": "billing_anomaly"}
#: persona ← execution_face（F4 規則硬失敗檢查用）
PERSONA = {"bill_diagnosis": "pm_bill_diagnosis", "billing_anomaly": "pm_billing_anomaly"}


# ══════════════════════════════════════════════════════════════════════════
# F6：呼叫帳本（**純觀測**的 passthrough spy，不改變任何行為）
# ══════════════════════════════════════════════════════════════════════════

class BudgetExceeded(RuntimeError):
    """外部呼叫超過凍結的 hard cap → 立即中止，不得續跑到綠。"""


class CallLedger:
    def __init__(self, hard_cap: int) -> None:
        self.hard_cap = hard_cap
        self.calls: "list[dict]" = []

    def note(self, kwargs: dict) -> None:
        if len(self.calls) + 1 > self.hard_cap:
            raise BudgetExceeded(
                f"外部呼叫已達凍結上限 {self.hard_cap}——中止（不得跑到綠為止）")
        self.calls.append({
            "model": kwargs.get("model"),
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_tokens"),
            "has_response_format": "response_format" in kwargs,
        })

    def since(self, mark: int) -> "list[dict]":
        return self.calls[mark:]

    def __len__(self) -> int:
        return len(self.calls)


def _is_infra(exc: BaseException) -> bool:
    """凍結的 infra 判別：只有這些可 retry。斷言紅一律不 retry。"""
    if isinstance(exc, (AssertionError, BudgetExceeded)):
        return False
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in _INFRA_MARKERS)


# ══════════════════════════════════════════════════════════════════════════
# fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def _mock_jgb_env():
    """F2：jgb2 替身。**必須在 app 啟動前設**——`JGBSystemAPI.__init__` 讀值一次。"""
    prev = os.environ.get("USE_MOCK_JGB_API")
    os.environ["USE_MOCK_JGB_API"] = "true"
    yield
    if prev is None:
        os.environ.pop("USE_MOCK_JGB_API", None)
    else:
        os.environ["USE_MOCK_JGB_API"] = prev


@pytest.fixture(scope="module")
def client(_mock_jgb_env):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def preflight(client):
    """**零成本**前置檢查：任何一項不成立就別花錢（F2／F3／F4／F5）。"""
    import asyncio

    app_state = client.app.state

    # F2：替身確實生效，且不是真網路
    from services.jgb.transport import JGBMockTransport
    jgb_api = app_state.conversational_engine.api_handler.jgb_api
    assert jgb_api.use_mock is True, "USE_MOCK_JGB_API 未生效——本檔不得打真 jgb2"
    assert isinstance(jgb_api._mock_transport, JGBMockTransport), \
        f"替身型別不符：{type(jgb_api._mock_transport).__name__}"

    # F5：解析後的模型／溫度／上限必須等於凍結值（付費前先擋 env fallback 漂移）
    opt = app_state.llm_answer_optimizer
    brain = {"model": os.getenv("PRESALES_SYNTH_MODEL", opt.config["model"]),
             "temperature": float(os.getenv("ADVISOR_TEMP", "0.4")),
             "max_tokens": 400}
    synth = {"model": os.getenv("PRESALES_ANSWER_MODEL",
                                os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
             "temperature": float(os.getenv("LLM_ANSWER_SYNTH_TEMP", "0.2")),
             "max_tokens": int(opt.config["max_tokens"])}
    assert brain == FROZEN_BRAIN, f"brain 組態偏離凍結值：{brain} != {FROZEN_BRAIN}"
    assert synth == FROZEN_SYNTH, f"合成組態偏離凍結值：{synth} != {FROZEN_SYNTH}"
    assert brain["model"] != synth["model"], \
        "兩輪落到同一模型——env fallback 已讓 runner 失真（F5）"

    # F3／F4：面向設定與 persona 規則
    async def _check():
        import asyncpg
        from services.conversational_config import config_for_key, reset_cache
        from services.conversational_rules import load_rules
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
        try:
            out = {}
            for face, key in FACET_KEY.items():
                cfg = await config_for_key(pool, key)
                out[key] = (cfg, await load_rules(pool, PERSONA[face]) if cfg else None)
            return out
        finally:
            await pool.close()

    try:
        checked = asyncio.run(_check())
    except Exception as e:                                   # DB 不可達＝環境問題
        pytest.skip(f"無法連 DB 做前置檢查：{e}")

    for key, (cfg, rules) in checked.items():
        # F3：直達進場的 registry 必須命中且啟用
        assert cfg is not None and getattr(cfg, "enabled", False), \
            f"面向 {key} 未命中 registry 或未啟用——trigger_facet_key 會落回既有管線"
        scope = getattr(cfg, "grounding_scope", None) or {}
        assert not scope.get("enabled_gate") and not scope.get("prefill_api"), \
            (f"面向 {key} 宣告了 enabled_gate／prefill_api——直達進場不再等價，"
             f"C4b 不得以此入口取證（見 c4b-entry-path-equivalence-resolved.md）")
        # F4：persona 規則缺失 → **fail**，不是 skip、不是默默降級
        assert rules and rules.strip(), (
            f"面向 {key} 的 persona 規則缺失——引擎會直接降級回 None，"
            f"該次 run **不得**被當成有效 C4b 量測（F4 fail-closed）")
    return True


@pytest.fixture(scope="module")
def ledger(client, preflight):
    """F1／F5／F6：passthrough spy。**只觀測**——原樣委派、原樣回傳，不改變行為。"""
    provider = client.app.state.llm_answer_optimizer.llm_provider
    real = provider.chat_completion
    led = CallLedger(HARD_CAP_CALLS)

    def spy(*args, **kwargs):
        led.note(kwargs)          # 觀測
        return real(*args, **kwargs)   # 原樣委派，回傳不加工

    provider.chat_completion = spy
    global _LEDGER
    _LEDGER = led
    yield led
    provider.chat_completion = real


# ══════════════════════════════════════════════════════════════════════════
# 一次 run＝兩輪
# ══════════════════════════════════════════════════════════════════════════

def _post(client, message, sid, *, trigger_facet_key=None):
    body = {"message": message, "vendor_id": VENDOR_ID, "target_user": TARGET_USER,
            "mode": "b2b", "role_id": ROLE_ID, "session_id": sid, "stream": False}
    if trigger_facet_key:
        body["trigger_facet_key"] = trigger_facet_key
    return client.post("/api/v1/message", json=body)


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


#: 本模組已用過的 session_id——每個 run／每次 infra retry 都必須是**全新**的一條
_SEEN_SESSIONS: "set[str]" = set()


class SessionReuseError(AssertionError):
    """同一條 session 被重用 → 「三次獨立重跑」實際變成「同一 session 累積狀態跑三遍」。"""


def _new_session_id(case: str, run_idx: int, attempt: int) -> str:
    """配發一條**保證未用過**的 session_id（harness isolation，不動 production code）。"""
    sid = f"c4b-{case}-r{run_idx}a{attempt}-{uuid.uuid4().hex[:10]}"
    if sid in _SEEN_SESSIONS:
        raise SessionReuseError(f"session_id 重複配發：{sid}")
    _SEEN_SESSIONS.add(sid)
    return sid


def _conversational_rows(sid: str) -> int:
    """該 session 目前的對話偽會話列數（0 = 乾淨起點）。"""
    import asyncio

    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            return await conn.fetchval(
                "SELECT count(*) FROM form_sessions "
                "WHERE session_id=$1 AND form_id='conversational'", sid)
        finally:
            await conn.close()
    return int(asyncio.run(_q()) or 0)


def _one_run(client, ledger, spec, run_idx, attempt):
    """跑一個案例一次：第 1 輪真 brain 追問，第 2 輪決定性填槽 → grounding → 真合成。

    ⚠️ **每個 run、每次 infra retry 都開全新 session**——否則 attempt 1 建立的 Face 會話、
    已收槽位、asked_count 會被 attempt 2 繼承，「三次獨立重跑」就變成
    「同一條 session 累積狀態後連續跑三遍」（harness false-green）。
    """
    from tests.support.brain_grounding import evaluate_brain_grounding

    sid = _new_session_id(spec.case, run_idx, attempt)
    partial = {"case": spec.case, "run": run_idx, "attempt": attempt, "session_id": sid,
               "passed": False, "raw_answer": None, "violated_dimensions": ["harness"]}
    _PARTIAL.setdefault(spec.case, []).append(partial)
    assert _conversational_rows(sid) == 0, \
        f"session {sid} 起點不乾淨——本次量測不是從全新會話開始"
    mark = len(ledger)
    try:
        r1 = _post(client, spec.user_turns[0], sid,
                   trigger_facet_key=FACET_KEY[spec.execution_face])
        assert r1.status_code == 200, r1.text
        j1 = r1.json()
        partial["turn1_answer"] = j1.get("answer")
        partial["turn1_intent_type"] = j1.get("intent_type")
        assert (j1.get("answer") or "").strip(), "第 1 輪無回覆"
        # F3：直達確實進了對話（不是落回單發知識）
        assert j1.get("intent_type") == "conversational", \
            f"第 1 輪未進面向對話（intent_type={j1.get('intent_type')}）——直達進場失敗"
        # F1：第 1 輪必須真的打到 brain，且參數＝凍結的 brain 組態
        turn1 = ledger.since(mark)
        assert turn1, "第 1 輪沒有任何外部呼叫——brain 未真的跑到（F1）"
        assert any(c["model"] == FROZEN_BRAIN["model"]
                   and c["temperature"] == FROZEN_BRAIN["temperature"]
                   and c["max_tokens"] == FROZEN_BRAIN["max_tokens"]
                   and c["has_response_format"] for c in turn1), \
            f"第 1 輪呼叫參數不符凍結的 brain 組態：{turn1}"

        mark2 = len(ledger)
        r2 = _post(client, spec.user_turns[1], sid)     # 續對話：**不帶** trigger_facet_key
        assert r2.status_code == 200, r2.text
        answer = (r2.json().get("answer") or "")
        partial["raw_answer"] = answer
        assert answer.strip(), "第 2 輪無回覆"
        # F5：第 2 輪必須是 factual 合成組態（與第 1 輪不同模型）
        turn2 = ledger.since(mark2)
        assert any(c["model"] == FROZEN_SYNTH["model"]
                   and c["temperature"] == FROZEN_SYNTH["temperature"]
                   and c["max_tokens"] == FROZEN_SYNTH["max_tokens"] for c in turn2), \
            f"第 2 輪呼叫參數不符凍結的合成組態：{turn2}"
        # ⚠️ 2026-08-26「統一 mini」後 brain 與合成**同模型**，**不得再以 model 名區分**。
        #    brain 輪的辨識特徵是 max_tokens=400 ＋ response_format=json_object。
        assert not [c for c in turn2
                    if c["max_tokens"] == FROZEN_BRAIN["max_tokens"]
                    and c.get("has_response_format")], \
            (f"第 2 輪出現 brain 組態呼叫（max_tokens=400＋json_object）——"
             f"決定性填槽路徑未生效，執行路徑已偏離凍結形狀"
             f"（harness／exec-path divergence，非 brain 失敗）：{turn2}")

        record = evaluate_brain_grounding(answer, spec)
        _PARTIAL[spec.case].remove(partial)      # 已有完整紀錄，撤下暫存
        record["run"] = run_idx
        record["attempt"] = attempt
        record["session_id"] = sid
        record["calls"] = ledger.since(mark)
        return record
    finally:
        _cleanup(sid)


def _run_case(client, ledger, spec):
    """3 次全過才算過；斷言紅不 retry，只有 infra 可 retry（≤2）。"""
    records, retries = [], 0
    for run_idx in range(1, RUNS_PER_CASE + 1):
        attempt = 0
        while True:
            try:
                records.append(_one_run(client, ledger, spec, run_idx, attempt))
                break
            except BudgetExceeded:
                raise
            except BaseException as e:                     # noqa: BLE001
                if _is_infra(e) and attempt < INFRA_RETRIES_PER_RUN:
                    attempt += 1
                    retries += 1
                    time.sleep(2 ** attempt)
                    continue
                if _is_infra(e):
                    records.append({"case": spec.case, "run": run_idx, "attempt": attempt,
                                    "passed": False, "violated_dimensions": ["infra"],
                                    "raw_answer": None,
                                    "error": f"{type(e).__name__}: {e}"})
                    break
                raise                                       # 斷言紅：**不 retry**
    return records, retries


_EVIDENCE: "list[dict]" = []
#: 逐案的部分紀錄（harness 紅時仍取得回原文；case → list[dict]）
_PARTIAL: "dict[str, list]" = {}
#: teardown 取用；fixture 收掉後 getfixturevalue 取不到，evidence 會少記 external_calls
_LEDGER = None


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("spec", _build_specs(), ids=lambda s: s.case)
def test_c4b_brain_uses_grounding(client, ledger, spec):
    try:
        records, retries = _run_case(client, ledger, spec)
    except BaseException as e:                              # noqa: BLE001
        # ⚠️ harness／exec-path 斷言紅也**必須**留下 evidence——
        #    否則該案在報告裡會整個消失（首次執行實際踩到，2026-08-25）。
        _EVIDENCE.append({"case": spec.case, "runs": list(_PARTIAL.get(spec.case, [])),
                          "retries": 0, "outcome": "FAILED",
                          "harness_error": f"{type(e).__name__}: {e}"})
        raise
    _EVIDENCE.append({"case": spec.case, "runs": records, "retries": retries,
                      "outcome": "PASSED" if all(r["passed"] for r in records) else "FAILED"})
    failed = [r for r in records if not r["passed"]]
    assert not failed, (
        f"C4b 案例 {spec.case}：{RUNS_PER_CASE} 次中 {len(failed)} 次未過"
        f"（不取多數決）→ {[(r['run'], r['violated_dimensions']) for r in failed]}\n"
        f"回答原文：{[r.get('raw_answer') for r in failed]}")


@pytest.fixture(scope="module", autouse=True)
def _write_evidence(request):
    """evidence **MUST** 記錄 executed／skipped／external_calls，不得只貼 pytest summary。"""
    yield
    total_calls = len(_LEDGER) if _LEDGER is not None else None
    call_log = list(_LEDGER.calls) if _LEDGER is not None else []
    executed = len(_EVIDENCE)
    payload = {
        "spec": "conversational-routing-execution / 6.2 C4b",
        "ruler": "c4b-ruler-v2-amendment.md",
        "parameters": "c4b-run-parameters-frozen.md (+ v2 §5)",
        "runs_per_case": RUNS_PER_CASE,
        "nominal_calls": NOMINAL_CALLS,
        "hard_cap_calls": HARD_CAP_CALLS,
        "executed_cases": executed,
        "skipped_cases": len(_build_specs()) - executed,
        "external_calls": total_calls,
        "retries": sum(e.get("retries", 0) for e in _EVIDENCE),
        "call_log": call_log,
        "cases": _EVIDENCE,
    }
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 C4b evidence → {os.path.abspath(EVIDENCE_PATH)}")
