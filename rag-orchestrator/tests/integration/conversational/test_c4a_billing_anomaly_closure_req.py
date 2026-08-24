"""integration：C4a 執行鏈閉環——`billing_anomaly`（任務 5.4，R3.1／R3.3／R7.1）。

**本檔是 5.3 的結構性對照組**，要證的不是「grounding 會動」，而是：

> **chain closure 不依賴 `secondary_call` 才能成立。**

```text
5.3 bill_diagnosis   secondary_call_required = true
5.4 billing_anomaly  secondary_call_required = false   ← 本檔
```

**本檔涵蓋**：`c4a-anom-01`（＋**OB-1／OB-2**）、`c4a-anom-02`、全案 **OB-3**。

⚠️ **不得越界**：`execution_face = billing_anomaly` 只是 **test context**。
5.4 PASS **SHALL NOT** 寫成「使用者問『帳單現在的狀態』就應 route billing_anomaly」——
那會越界到 `routing-authority-model`（BLOCKED_BY_EXTERNAL_DECISION）。
"""
import os

import pytest

pytestmark = pytest.mark.integration

FACET = "帳單異常"


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
    if await cc.config_for_category(p, FACET) is None:
        await p.close()
        pytest.skip(f"面向設定未就緒：{FACET}")
        return
    yield p
    await p.close()


class _Brain:
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


async def _run_case(pool, query: str, bill_ref: int):
    """跑完 frozen chain，回傳 `(grounding, transport_recorder, handler_recorder)`。"""
    from services import conversational_config as cc
    from services.api_call_handler import APICallHandler
    from services.conversational_engine import ConversationalEngine
    from services.conversational_rules import load_rules
    from services import system_context as sc
    from tests.support.c4a_harness import install_recorders

    cc.reset_cache()
    cfg = await cc.config_for_category(pool, FACET)
    handler, rec = install_recorders(APICallHandler(db_pool=None))
    eng = ConversationalEngine(
        db_pool=pool, optimizer=_Brain(bill_ref), retriever=None,
        get_system_context=sc.get_system_context, rules_loader=load_rules,
        api_handler=handler)
    sid = "c4a-anom-" + os.urandom(4).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, query, config=cfg, role_id="20151")
        assert d1["kind"] == "ask", f"第 1 輪應追問，實得 {d1['kind']}"
        d2 = await eng.prepare(sid, "u1", 7, str(bill_ref), config=None, role_id="20151")
        assert d2["kind"] == "converge", f"第 2 輪應收斂，實得 {d2['kind']}｜{d2}"
        return d2["grounding"], rec, handler
    finally:
        await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


def _fixture(bill_id: int):
    from services.jgb.fixtures import BillFixtureTable
    return BillFixtureTable().by_id(bill_id)


def _rendered(date_int: int) -> str:
    """expected value 一律經 **production 渲染器**產生，不在測試中手抄日期。"""
    from services.jgb.bills import _format_date_int
    return _format_date_int(date_int)


# ══ c4a-anom-01：OB-1（semantic fact ＋ 兩個來源值）════════════════════════
@pytest.mark.req("conversational-routing-execution:3.3")
async def test_c4a_anom_01_closure_with_both_source_values(pool):
    """`這張帳單的計費期間是哪一段`｜fixture 900002｜required = billing_period ＋ OB-1。"""
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import anomaly_labeled_field_extractor

    row = _fixture(900002)
    grounding, rec, handler = await _run_case(pool, "這張帳單的計費期間是哪一段", 900002)

    # OB-3
    ids = rec.detail_bill_ids()
    assert ids and set(ids) == {900002}, f"OB-3 失敗：實際 detail 請求 {ids}"
    # secondary_call_required = false（正向斷言，見下方獨立測試的說明）
    assert handler.secondary_dispatch_count() == 0

    # OB-1：兩個來源值皆須送達（expected 自 frozen fixture ＋ production 渲染器取得）
    assert_chain_closure(
        grounding,
        ChainClosureAssertion(
            case="c4a-anom-01",
            grounding_must_contain=[_rendered(row["date_start"]), _rendered(row["date_end"])],
            required_grounding_facts=["billing_period"],
            not_covered=["bill_ref 非數字分支（get_contracts 未遷移）"],
        ),
        observed_fact_keys=anomaly_labeled_field_extractor(grounding),
    )


# ══ OB-2：半段期間必須紅 ═════════════════════════════════════════════════
@pytest.mark.req("conversational-routing-execution:3.3")
@pytest.mark.parametrize("drop", ["date_start", "date_end"])
async def test_ob2_half_period_must_fail(pool, drop):
    """⚠️ **OB-2 正式落地**：只送一半來源值——即使文字仍保留「計費期間」label——**必須紅**。

    這證明：`billing_period` observer green **≠** provenance delivery complete。
    """
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import anomaly_labeled_field_extractor

    row = _fixture(900002)
    grounding, _, _ = await _run_case(pool, "這張帳單的計費期間是哪一段", 900002)

    mutated = grounding.replace(_rendered(row[drop]), "（缺）")
    assert "計費期間" in mutated, "前提：label 仍在，證明不是靠 label 消失才紅"
    assert "billing_period" in anomaly_labeled_field_extractor(mutated), \
        "前提：observer 仍觀測到 billing_period——紅必須來自 delivery，不是 observation"

    with pytest.raises(AssertionError) as ei:
        assert_chain_closure(
            grounding=mutated,
            spec=ChainClosureAssertion(
                case=f"c4a-anom-01(negative:{drop})",
                grounding_must_contain=[_rendered(row["date_start"]), _rendered(row["date_end"])],
                required_grounding_facts=["billing_period"],
            ),
            observed_fact_keys=anomaly_labeled_field_extractor(mutated),
        )
    assert "送達性缺字面" in str(ei.value)


# ══ c4a-anom-02 ══════════════════════════════════════════════════════════
@pytest.mark.req("conversational-routing-execution:3.3")
async def test_c4a_anom_02_closure(pool):
    """`這張帳單現在的狀態是什麼`｜fixture 900003｜required = bill_status（不含 bit_status）。"""
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import anomaly_labeled_field_extractor

    grounding, rec, handler = await _run_case(pool, "這張帳單現在的狀態是什麼", 900003)

    ids = rec.detail_bill_ids()
    assert ids and set(ids) == {900003}, f"OB-3 失敗：實際 detail 請求 {ids}"
    assert handler.secondary_dispatch_count() == 0

    assert_chain_closure(
        grounding,
        ChainClosureAssertion(
            case="c4a-anom-02",
            grounding_must_contain=["待對帳"],       # fixture 900003 status=8 的權威標籤
            required_grounding_facts=["bill_status"],
            not_covered=["bill_ref 非數字分支（get_contracts 未遷移）"],
        ),
        observed_fact_keys=anomaly_labeled_field_extractor(grounding),
    )


@pytest.mark.req("conversational-routing-execution:3.3")
async def test_sufficiency_bites_on_anomaly_path(pool):
    """完整 chain 上移除 required key → 必須紅（證明尺在 anomaly path 也會咬）。"""
    from tests.support.chain_closure import ChainClosureAssertion, assert_chain_closure
    from tests.support.fact_extractors import anomaly_labeled_field_extractor

    grounding, _, _ = await _run_case(pool, "這張帳單現在的狀態是什麼", 900003)
    observed = anomaly_labeled_field_extractor(grounding) - {"bill_status"}

    with pytest.raises(AssertionError) as ei:
        assert_chain_closure(
            grounding,
            ChainClosureAssertion(case="c4a-anom-02(negative)",
                                  grounding_must_contain=["待對帳"],
                                  required_grounding_facts=["bill_status"]),
            observed_fact_keys=observed,
        )
    assert "充分性缺事實鍵" in str(ei.value)


# ══ 對照 invariant：secondary_call 的有／無由 execution trace 證明 ═════════
@pytest.mark.req("conversational-routing-execution:3.3")
async def test_no_secondary_dispatch_even_though_detail_endpoint_was_called(pool):
    """⚠️ **本檔最容易假紅之處**：anomaly 沒有 `secondary_call`，
    但 adapter 的數字分支**仍會**打一次 detail 端點。

    故 secondary call 的有無 **MUST** 由 `execute_api_call` 的派發次數判定，
    **不得**以「`bill_detail` 有沒有被呼叫」代表。
    """
    _, rec, handler = await _run_case(pool, "這張帳單現在的狀態是什麼", 900003)

    assert "bill_detail" in rec.endpoint_keys(), "前提：adapter 數字分支確實打了 detail"
    assert handler.secondary_dispatch_count() == 0, (
        f"anomaly 不應有 Face secondary dispatch，實得 {handler.dispatched}")
