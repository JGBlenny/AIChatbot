"""integration：C4a 執行鏈閉環——`bill_diagnosis`（任務 5.3，R3.1／R7.1）。

真 DB ＋ 真 `ConversationalEngine` ＋ **真 `APICallHandler`** ＋ 真 `JGBSystemAPI`
＋ `JGBMockTransport`（4.1–4.5）＋ 腳本化 brain（零 OpenAI）。

**凍結輸入**（全部先於本檔）：
  案例  `c4a-case-set-frozen.md`（451c0d2）｜尺 `c4a-required-facts-frozen.md`（1dbf94c）
  觀測  `tests/support/fact_extractors.py`｜量尺 `tests/support/chain_closure.py`
  資料  `services/jgb/fixtures.py`（4.4）

**本檔涵蓋**：`c4a-diag-01`／`c4a-diag-02` ＋ **OB-3**（case→fixture identity）。
⚠️ **OB-1／OB-2 屬 `c4a-anom-01`，在 5.4 落地**——本檔提供通用 primitive，
   但**不得**宣稱 OB-1／OB-2 已由 5.3 驗收。

## ⚠️ Claim ceiling（5.3 PASS 只能證明這些）

```text
✅ 兩個 frozen bill_diagnosis C4a case 的 **numeric branch** chain closure
❌ bill_diagnosis 對一般自然語言穩健
❌ 非數字 bill_ref 分支已證（get_contracts 未遷移）
❌ routing 到 bill_diagnosis 正確（case inclusion 不構成 routing ownership 證據）
❌ adapter 全分支已 closure
```
"""
import os

import pytest

pytestmark = pytest.mark.integration

FACET = "條件診斷：帳單"
DETAIL_TMPL = "/api/external/v1/bills/{bill_id}"


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")


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
    from services import conversational_config as cc, system_context as sc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=3)
    except Exception as e:                                   # pragma: no cover
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache(); sc.reset_cache()
    cfg = await cc.config_for_category(p, FACET)
    if cfg is None:
        await p.close()
        pytest.skip(f"面向設定未就緒：{FACET}")
        return
    yield p
    await p.close()


class _Brain:
    """腳本化 brain：第 1 輪追問，第 2 輪收斂並帶 `bill_ref`（數字分支）。"""

    def __init__(self, bill_ref: int):
        self.turn = 0
        self.bill_ref = str(bill_ref)

    async def conversational_step(self, rules, system_md, state, msg, faces=None, kb_search=None):
        self.turn += 1
        if self.turn == 1:
            return {"action": "ask", "converge_kind": "answer", "extracted_fields": {},
                    "next_question": "請問是哪一張帳單？", "scope": "stay"}
        return {"action": "converge", "converge_kind": "answer",
                "extracted_fields": {"bill_ref": self.bill_ref},
                "scope": "stay", "face": FACET}


def _engine(pool, brain, recorder_box):
    from services.api_call_handler import APICallHandler
    from services.conversational_engine import ConversationalEngine
    from services.conversational_rules import load_rules
    from services import system_context as sc
    from tests.support.c4a_harness import install_recorders

    handler, rec = install_recorders(APICallHandler(db_pool=None))
    recorder_box.append((rec, handler))

    return ConversationalEngine(
        db_pool=pool, optimizer=brain, retriever=None,
        get_system_context=sc.get_system_context, rules_loader=load_rules,
        api_handler=handler)


async def _run_case(pool, query: str, bill_ref: int):
    """跑完 frozen chain，回傳 (grounding, recorder)。"""
    from services import conversational_config as cc

    cc.reset_cache()
    cfg = await cc.config_for_category(pool, FACET)
    box = []
    eng = _engine(pool, _Brain(bill_ref), box)
    sid = "c4a-diag-" + os.urandom(4).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, query, config=cfg, role_id="20151")
        assert d1["kind"] == "ask", f"第 1 輪應追問，實得 {d1['kind']}"
        d2 = await eng.prepare(sid, "u1", 7, str(bill_ref), config=None, role_id="20151")
        assert d2["kind"] == "converge", f"第 2 輪應收斂，實得 {d2['kind']}｜{d2}"
        return (d2["grounding"], *box[0])
    finally:
        await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


# ══ c4a-diag-01 ══════════════════════════════════════════════════════════
@pytest.mark.req("conversational-routing-execution:3.1")
async def test_c4a_diag_01_closure(pool):
    """`幫我查點退帳單金額`｜fixture 900003｜required = amount_due。"""
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import diagnosis_bracket_fact_extractor

    grounding, rec, handler = await _run_case(pool, "幫我查點退帳單金額", 900003)

    # OB-3：**所有**實際 detail 請求都必須指向本案 fixture
    # ⚠️ 實測 detail 會被呼叫兩次（adapter 數字分支直查 ＋ 面向 secondary_call）——
    #    這是既有 production 行為，故斷言「集合相符且非空」，不鎖次數。
    ids = rec.detail_bill_ids()
    assert ids and set(ids) == {900003}, (
        f"OB-3 失敗：實際 detail 請求 {ids}，本案 fixture 為 900003")
    # secondary_call_required=true：**由 execute_api_call 的派發次數**正向證明
    # ⚠️ 不以「bill_detail 有沒有被呼叫」代表——adapter 數字分支也會打 detail（見 5.4 對照）
    assert handler.secondary_dispatch_count() > 0, (
        f"應有 Face secondary dispatch，實得 {handler.dispatched}")

    assert_chain_closure(
        grounding,
        ChainClosureAssertion(
            case="c4a-diag-01",
            grounding_must_contain=["7,500"],       # fixture 900003 的 total（production 渲染）
            required_grounding_facts=["amount_due"],
            not_covered=["bill_ref 非數字分支（get_contracts 未遷移）"],
        ),
        observed_fact_keys=diagnosis_bracket_fact_extractor(grounding),
    )


# ══ c4a-diag-02 ══════════════════════════════════════════════════════════
@pytest.mark.req("conversational-routing-execution:3.1")
async def test_c4a_diag_02_closure(pool):
    """`這張帳單現在還能不能收回`｜fixture 900001｜required = cancel_determination。"""
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import diagnosis_bracket_fact_extractor

    grounding, rec, handler = await _run_case(pool, "這張帳單現在還能不能收回", 900001)

    ids = rec.detail_bill_ids()
    assert ids and set(ids) == {900001}, (
        f"OB-3 失敗：實際 detail 請求 {ids}，本案 fixture 為 900001")
    assert handler.secondary_dispatch_count() > 0

    assert_chain_closure(
        grounding,
        ChainClosureAssertion(
            case="c4a-diag-02",
            grounding_must_contain=["2026年8月租金"],   # fixture 900001 的 title
            required_grounding_facts=["cancel_determination"],
            not_covered=["bill_ref 非數字分支（get_contracts 未遷移）"],
        ),
        observed_fact_keys=diagnosis_bracket_fact_extractor(grounding),
    )


# ══ 反證：尺在**完整 chain** 上仍會咬 ═══════════════════════════════════
@pytest.mark.req("conversational-routing-execution:3.1")
async def test_sufficiency_still_bites_on_full_chain(pool):
    """⚠️ 送達 ≠ 充分：chain 正常查到帳單，但把該案 required key 從觀測中拿掉 → 必須紅。

    這證明 5.1 的尺在**真實 chain** 上仍有鑑別力，不只是 unit helper 會咬。
    """
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import diagnosis_bracket_fact_extractor

    grounding, _, _ = await _run_case(pool, "幫我查點退帳單金額", 900003)
    observed = diagnosis_bracket_fact_extractor(grounding) - {"amount_due"}

    with pytest.raises(AssertionError) as ei:
        assert_chain_closure(
            grounding,
            ChainClosureAssertion(case="c4a-diag-01(negative)",
                                  grounding_must_contain=["7,500"],
                                  required_grounding_facts=["amount_due"]),
            observed_fact_keys=observed,
        )
    assert "充分性缺事實鍵" in str(ei.value)


@pytest.mark.req("conversational-routing-execution:3.1")
async def test_ob3_binding_bites_when_fixture_mismatches(pool):
    """⚠️ OB-3 的反證：若把期望綁到**另一筆** fixture，斷言必須紅。

    這證明「兩案綁不同 fixture」真的能殺掉 constant-record 實作
    （component negative control；**不新增第五個 C4a case**）。
    """
    _, rec, _ = await _run_case(pool, "這張帳單現在還能不能收回", 900001)
    assert set(rec.detail_bill_ids()) == {900001}
    assert set(rec.detail_bill_ids()) != {900003}, "OB-3 綁定無鑑別力"
