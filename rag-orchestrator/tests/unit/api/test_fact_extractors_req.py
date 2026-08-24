"""TDD：面向專屬 observation adapter（任務 5.2 前置，業主裁定 (b) 的 B-1～B-3）。

⚠️ **本組驗的是觀測器會不會咬**，不是被測系統。三條硬限制逐條驗：

* **B-1** extractor 不得擁有 sufficiency policy——只回觀測到的 key，不判「夠不夠」；
* **B-2** 不綁排版符號——`• 狀態：X` 與 `狀態：X` 必須觀測到同一個 fact；
* **B-3** 每個 extractor 各有 negative controls——證明抓的是**欄位輸出結構**，非 keyword spotting。
"""
import pytest

from services.jgb.bills import build_bill_anomaly_facts, build_bill_diagnosis_facts
from services.jgb.fixtures import BillFixtureTable
from tests.support.fact_extractors import (
    FACET_FACT_EXTRACTORS,
    anomaly_labeled_field_extractor,
    diagnosis_bracket_fact_extractor,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def row():
    return dict(BillFixtureTable().by_id(900001))


# ── 對真 formatter 實跑（不是對自製字串）──────────────────────────────────
def test_diagnosis_extractor_on_real_formatter_output(row):
    keys = diagnosis_bracket_fact_extractor(build_bill_diagnosis_facts(row, ""))
    assert keys == {
        "send_determination", "cancel_determination", "manual_complete_determination"
    }


def test_anomaly_extractor_on_real_formatter_output(row):
    """⚠️ 這正是 5.1 逼出的問題：anomaly formatter **不用** `【鍵】`，
    但它確實輸出了語義欄位——換觀測器即可，不需改 production formatter。"""
    keys = anomaly_labeled_field_extractor(build_bill_anomaly_facts(row, ""))
    assert {"bill_status", "amount_stored", "due_date", "billing_period"} <= keys


def test_two_extractors_share_one_canonical_key_space():
    """兩者輸出同一組 canonical key，故充分性判準仍然唯一。"""
    assert set(FACET_FACT_EXTRACTORS) == {"條件診斷：帳單", "帳單異常"}


# ── B-1：observer ≠ judge ────────────────────────────────────────────────
def test_extractors_return_observations_not_verdicts(row):
    """extractor 只回 set；**不得**有任何「夠不夠」的判斷介面。"""
    for fn in (diagnosis_bracket_fact_extractor, anomaly_labeled_field_extractor):
        assert isinstance(fn(build_bill_anomaly_facts(row, "")), set)
    import inspect

    import tests.support.fact_extractors as fe

    # 結構檢查（非文字掃描）：公開 callable 只吃一個文字參數、且模組不含任何判定介面
    for name in dir(fe):
        if name.startswith("_"):
            continue
        obj = getattr(fe, name)
        if callable(obj) and getattr(obj, "__module__", "") == fe.__name__:
            params = list(inspect.signature(obj).parameters)
            assert params == ["grounding"], f"{name} 應只吃 grounding（B-1）：{params}"
        assert not any(w in name.lower() for w in ("required", "sufficient", "assert")), (
            f"observer 模組不得暴露判定介面：{name}（B-1）"
        )


# ── B-2：不綁排版符號 ────────────────────────────────────────────────────
@pytest.mark.parametrize("text", [
    "• 狀態：待繳費",
    "狀態：待繳費",
    "  狀態 ： 待繳費",
    "帳單「x」（編號 1）狀態:待繳費。",     # 半形冒號
])
def test_status_observed_regardless_of_typography(text):
    assert "bill_status" in anomaly_labeled_field_extractor(text)


@pytest.mark.parametrize("text", ["• 計費期間：2026/08/01 ~ 2026/08/31",
                                  "計費期間：2026/08/01 ~ 2026/08/31"])
def test_billing_period_observed_regardless_of_bullet(text):
    assert "billing_period" in anomaly_labeled_field_extractor(text)


# ── B-3：negative controls（證明不是 keyword spotting）────────────────────
def test_prose_mentioning_status_is_not_a_fact():
    assert anomaly_labeled_field_extractor("目前帳單看起來正常") == set()


def test_prose_mentioning_amount_is_not_a_fact():
    """⚠️ 「金額」二字出現在句子裡，不得被觀測成 amount。"""
    assert "amount_stored" not in anomaly_labeled_field_extractor("金額可能有問題，請再確認")


def test_amount_requires_the_stored_value_context():
    """本 formatter 的 amount 契約是 `帳單金額 …（系統存值）`，不是任何「金額：」字樣。

    ⚠️ 與業主示例的差異（刻意）：示例寫 `• 金額：1,000 → amount`，
    但**真 formatter 實際輸出**為 `帳單金額 NT$ 18,000（系統存值）`（`_bill_head()`）。
    觀測契約以**實際輸出**為準，不以示例為準——否則觀測的是想像中的 formatter。
    """
    assert "amount_stored" in anomaly_labeled_field_extractor("帳單金額 NT$ 1,000（系統存值）。")
    assert "amount_stored" not in anomaly_labeled_field_extractor("• 金額：1,000")


def test_empty_label_value_is_not_a_fact():
    """欄位名出現但沒有值 → 不算觀測到。"""
    assert anomaly_labeled_field_extractor("狀態：") == set()


def test_unknown_bracket_key_is_ignored():
    """未登錄的括號鍵不猜——未知鍵不是 fact，是尚未建立觀測契約的東西。"""
    assert diagnosis_bracket_fact_extractor("【未知判定】某些內容") == set()


def test_diagnosis_extractor_ignores_anomaly_syntax():
    """兩個觀測器互不越界：diagnosis 觀測器不得認得 anomaly 的欄位表示法。"""
    assert diagnosis_bracket_fact_extractor("狀態：待繳費\n計費期間：2026/08") == set()


def test_anomaly_extractor_ignores_bracket_syntax():
    assert anomaly_labeled_field_extractor("【發送判定】已發送") == set()
