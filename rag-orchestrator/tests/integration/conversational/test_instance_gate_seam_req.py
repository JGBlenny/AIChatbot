"""integration：instance-reference gate 的 **production seam** 契約
（spec routing-disambiguation 任務 4.1／4.2／4.4｜R1.1, R1.2, R7.1）。

Task 4 是 `GateDecision` **第一次**取得 production authority。本檔鎖四件事：

```text
flag OFF                      → routing 完全不變
flag ON 但 holdout 未授權       → 仍不得生效（requested ≠ authorized）
gate block                    → 只抑制 C ∧ D 的 Routing Hints，且 category 順序不得繞過
gate exception                → fail-open，且**與 abstain 可稽核區分**
```

⚠️ **抑制集合只由 `gate_applies_to`（C ∧ D）決定**，
SHALL NOT 擴成「所有 categories／所有 bill_ref Face／所有 dialog Face／所有 required_slots Face」。
"""
import json
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
PRODUCTION_TOP_K = 5
TARGET_USER = "property_manager"
MODE = "b2b"
ACTIVE_PROTOCOL_DIGEST = "4690a258f502d98d"

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_PROTOCOL = os.path.join(_REPO, ".kiro", "specs", "routing-disambiguation",
                         "robustness-protocol.json")

#: 合成的第二個「已納管」Face——**刻意不用 production 的 billing_anomaly**
SYNTH_KEY = "synthetic_instance_face"
SYNTH_CATEGORY = "（測試）合成診斷面向"


def _cases(name):
    with open(_PROTOCOL, encoding="utf-8") as f:
        return json.load(f)["case_sets"][name]["cases"]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture(scope="module")
def retriever():
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    return VendorKnowledgeRetrieverV2()


@pytest.fixture
async def pool():
    import asyncpg
    from services import conversational_config as cc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache()
    yield p
    cc.reset_cache()
    await p.close()


@pytest.fixture(autouse=True)
def deterministic_flags(monkeypatch):
    """`PREENTRY_ROUTABILITY_GATE` 會呼叫 LLM——關掉才歸因得了。"""
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "false")


@pytest.fixture
def authorized(monkeypatch):
    """把 gate 變成**已授權**（synthetic manifest）。

    ⚠️ 這只替換「授權來源」，不替換判定邏輯——
    production manifest 仍是 `not_run`，真實授權要等任務 6 的 holdout。
    """
    from services import instance_reference_gate as m
    base = m.current_manifest()                     # ⚠️ 先取再 patch，否則遞迴
    authorized_manifest = m.RulesetManifest(
        version=base.version, positive_patterns=dict(base.positive_patterns),
        counter_patterns=dict(base.counter_patterns), digest=base.digest,
        holdout=m.HoldoutRecord(status="passed", ruleset_digest=base.digest,
                                protocol_digest=ACTIVE_PROTOCOL_DIGEST,
                                dataset_id="synthetic", dataset_digest="ds-synthetic"))
    monkeypatch.setattr(m, "current_manifest", lambda: authorized_manifest)
    return m


@pytest.fixture
async def synthetic_face(pool, monkeypatch):
    """在 config registry 建立**第二個已納管 Face**（C=true、D=true）。

    ⚠️ 為何用合成 Face 而非 `billing_anomaly`：後者的產品歸屬**尚未逐 Face 裁定**。
    為了讓 N4 轉綠而提前把它宣告成 true，就是拿「機制上需要它」當「產品裁示」——
    erratum 01 原則③明令禁止。**機制正確性**與**哪個 production Face 進 Level A**
    必須繼續分離。
    """
    from services import conversational_config as cc
    md = {"conversational_config": {
        "key": SYNTH_KEY, "enabled": True, "answer_mode": "conversational",
        "persona_role": "property_manager",
        "topic_scope": {"mode": "category", "category": SYNTH_CATEGORY},
        "grounding_scope": {"requires_instance_reference": True, "required_slots": ["bill_ref"]}}}
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO knowledge_base (question_summary, answer, category, target_user,"
            " is_active, generation_metadata) VALUES ($1,$2,'對話規則',$3,TRUE,$4::jsonb)",
            f"對話規則：{SYNTH_CATEGORY}", "（測試用合成面向）", ["property_manager"],
            json.dumps(md, ensure_ascii=False))
    cc.reset_cache()
    from services import instance_reference_gate as m
    monkeypatch.setattr(m, "LEVEL_A_INSTANCE_GATE_SCOPE",
                        frozenset({"bill_diagnosis", SYNTH_KEY}))
    yield SYNTH_CATEGORY
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM knowledge_base WHERE category='對話規則'"
                           " AND question_summary=$1", f"對話規則：{SYNTH_CATEGORY}")
    cc.reset_cache()


async def _best(retriever, question, cache):
    from services.decision_layer import DecisionConfig
    if question not in cache:
        cfg = DecisionConfig.load()
        rows = await retriever.retrieve_knowledge_hybrid(
            query=question, vendor_id=VENDOR_ID, top_k=PRODUCTION_TOP_K,
            similarity_threshold=cfg.kb_threshold, target_user=TARGET_USER, mode=MODE)
        cache[question] = rows[0] if rows else None
    return cache[question]


async def _seam(pool, best, question):
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig
    if best is None:
        return ("single", None)
    cfg, _face_authority = await _diagnosis_config_for_knowledge(pool, best, DecisionConfig.load(),
                                                user_message=question)
    return ("single", None) if cfg is None else ("dialog", getattr(cfg, "key", "?"))


def _synthetic_knowledge(categories):
    from services.decision_layer import DecisionConfig
    return {"id": -1, "question_summary": "（合成）", "answer": "（合成）",
            "categories": list(categories), "category": categories[0],
            "similarity": DecisionConfig.load().form_trigger_threshold + 0.05,
            "action_type": "direct_answer"}


# ── 4.1：旗標 OFF ／ 未授權 → routing 完全不變 ────────────────
FROZEN = _cases("RULE") + _cases("INSTANCE") + _cases("CONTROL") + _cases("BLAST") \
    + _cases("UNDECIDED")


@pytest.mark.req("routing-disambiguation:7.1")
async def test_flag_off_and_requested_but_unauthorized_are_both_inert(pool, retriever, monkeypatch):
    """凍結案例集全體：OFF 與「ON 但未授權」的 routing SHALL 與彼此完全相同。

    ⚠️ 不是抽幾個代表案例——RULE／INSTANCE／CONTROL／BLAST／UNDECIDED 全跑。
    ⚠️ 第二種狀態是本條的重點：**把 env 設成 true 也不得生效**，
    因為 production manifest 仍是 `not_run`（授權未到）。
    """
    from services.instance_reference_gate import gate_authorized
    assert gate_authorized() is False, "production manifest 已被宣稱授權——本條的前提消失"

    cache, off, requested = {}, {}, {}
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "false")
    for q in FROZEN:
        off[q] = await _seam(pool, await _best(retriever, q, cache), q)
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    for q in FROZEN:
        requested[q] = await _seam(pool, await _best(retriever, q, cache), q)

    drift = [(q, off[q], requested[q]) for q in FROZEN if off[q] != requested[q]]
    assert drift == [], "未授權卻改變了 routing：\n" + "\n".join(
        f"  {q}：{a} → {b}" for q, a, b in drift)


# ── 4.2：抑制語義（需授權）────────────────────────────────
@pytest.mark.req("routing-disambiguation:1.2")
@pytest.mark.parametrize("question", _cases("RULE"))
async def test_rule_questions_are_suppressed_when_active(pool, retriever, monkeypatch,
                                                         authorized, question):
    """gate 真正生效時，rule 問句 SHALL NOT 進入受納管的 Face。"""
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, await _best(retriever, question, {}), question)
    assert route == "single", f"rule 問句仍進了「{facet}」"


@pytest.mark.req("routing-disambiguation:1.1")
@pytest.mark.parametrize("question", _cases("INSTANCE"))
async def test_instance_questions_survive_activation(pool, retriever, monkeypatch,
                                                     authorized, question):
    """⚠️ 雙邊同看：instance 側 SHALL NOT 被一起殺掉。"""
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, await _best(retriever, question, {}), question)
    assert (route, facet) == ("dialog", "bill_diagnosis"), \
        f"instance 問句落到 {route}/{facet}——rule 側修好、instance 側陪葬"


@pytest.mark.req("routing-disambiguation:4.2")
@pytest.mark.parametrize("question", _cases("UNDECIDED"))
async def test_undecided_utterances_are_never_suppressed(pool, retriever, monkeypatch,
                                                         authorized, question):
    """2.0 falsifier 在 **seam 層**的第三次確認；仍**不**裁定它們該進哪個 facet。"""
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, _ = await _seam(pool, await _best(retriever, question, {}), question)
    assert route == "dialog", "未決問句被抑制——erratum 01 的可分離前提被推翻"


# ── N4：category 順序不得繞過抑制（合成第二個已納管 Face）────
@pytest.mark.req("routing-disambiguation:1.2")
@pytest.mark.parametrize("order", [0, 1], ids=["diagnosis_first", "synthetic_first"])
async def test_category_order_cannot_bypass_suppression(pool, monkeypatch, authorized,
                                                        synthetic_face, order):
    """同一 KB 掛兩個**已納管** Face，rule 問句 SHALL 仍收斂為 single。

    ⚠️ 這是 N4 的**機制**契約——第二個 Face 用合成的，
    不靠提前把 production 的 `billing_anomaly` 裁成 true 來讓它轉綠。
    """
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    cats = ["條件診斷：帳單", synthetic_face]
    if order:
        cats.reverse()
    route, facet = await _seam(pool, _synthetic_knowledge(cats), "點退帳單的金額是怎麼算的")
    assert route == "single", f"rule 問句經 categories={cats} 進了「{facet}」——順序繞過了抑制"


@pytest.mark.req("routing-disambiguation:2.5")
async def test_suppression_does_not_leak_to_unmanaged_faces(pool, monkeypatch, authorized,
                                                            synthetic_face):
    """⚠️ 抑制集合只由 C ∧ D 決定：**未納管的 Face 不受影響**。

    `帳單異常`（未宣告 C）在同一筆 rule 問句下 SHALL 仍可接手——
    否則就是把抑制擴成「所有 dialog Face」，越過 Level A。
    """
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, _synthetic_knowledge(["條件診斷：帳單", "帳單異常"]),
                               "點退帳單的金額是怎麼算的")
    assert (route, facet) == ("dialog", "billing_anomaly"), (
        f"未納管的 Face 也被抑制（實得 {route}/{facet}）——抑制集合溢出 C ∧ D。"
        "\n⚠️ 這一條會在 billing_anomaly 完成逐 Face 裁定並宣告後改判，屆時應改為 single。")


# ── 4.4：fail-open，且與 abstain 可區分 ───────────────────
@pytest.mark.req("routing-disambiguation:1.3")
async def test_exception_fails_open_and_is_not_disguised_as_abstain(pool, monkeypatch,
                                                                    authorized, capsys):
    """抽取器爆炸 → 維持既有 routing，且訊息 SHALL 明示「非 abstain」。"""
    import services.instance_evidence as ie

    def _boom(self, question):
        raise RuntimeError("抽取器爆炸（測試注入）")

    monkeypatch.setattr(ie.InstanceEvidenceExtractor, "extract", _boom)
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, _synthetic_knowledge(["條件診斷：帳單"]),
                               "點退帳單的金額是怎麼算的")
    assert (route, facet) == ("dialog", "bill_diagnosis"), "例外未 fail-open"
    out = capsys.readouterr().out
    assert "fail-open" in out and "非 abstain" in out, \
        f"例外被靜默吞掉或被寫成 abstain——「壞掉」偽裝成「沒有訊號」：{out[-300:]}"
