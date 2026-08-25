"""unit：v6 post-hoc regression ruler 的自驗（**零成本、不打模型**）。

⚠️ v6 **不能**驗證 v5、不能取代 v5 的 machine verdict、不得作為獨立證據；
它只在未來 routing／resolver 有變更時作 regression guard。

先證這把尺會分：
```text
fixture-grounded correct answer      → PASS
generic answer                       → FAIL
other-fixture answer                 → FAIL
correct answer without rent          → PASS   ← v5 誤判的那一格
answer using one valid timing fact   → PASS
```
"""
import pytest

from tests.support.brain_grounding import BrainGroundingFailure, assert_brain_uses_grounding
from tests.support.v6_regression_ruler import v6_regression_ruler

pytestmark = pytest.mark.unit

SPEC = v6_regression_ruler()

CORRECT = ("合約「信義區套房A」目前狀態為已點交（執行中），目前尚不可點退；"
           "合約到期日為 2026/12/31，需到期前 30 天（2026/12/01）起才可發送點退。")


@pytest.mark.req("face-exit-before-grounding:1")
def test_fixture_grounded_correct_answer_passes():
    out = assert_brain_uses_grounding(CORRECT, SPEC)
    assert out["passed"] is True


@pytest.mark.req("face-exit-before-grounding:1")
def test_correct_answer_without_rent_passes():
    """★ v5 被誤判的那一格：不提租金**不應**判紅。"""
    assert "25,000" not in CORRECT and "25000" not in CORRECT
    assert assert_brain_uses_grounding(CORRECT, SPEC)["passed"] is True


@pytest.mark.req("face-exit-before-grounding:1")
def test_answer_using_one_valid_timing_fact_passes():
    """timing 是 OR group：三種等價形式任一即可。"""
    one_fact = "這份合約目前是已點交（執行中），要到期前 30 天才能發送點退。"
    assert assert_brain_uses_grounding(one_fact, SPEC)["passed"] is True


@pytest.mark.req("face-exit-before-grounding:1")
def test_generic_answer_fails():
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding("我目前沒有找到符合您問題的資訊，請洽客服協助。", SPEC)
    assert "value_not_used" in ei.value.record["violated_dimensions"]


@pytest.mark.req("face-exit-before-grounding:1")
def test_other_fixture_answer_fails():
    other = "合約「中山區雅房B」目前狀態為已點交（執行中），到期日 2026/12/31。"
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding(other, SPEC)
    assert "wrong_instance" in ei.value.record["violated_dimensions"]


@pytest.mark.req("face-exit-before-grounding:1")
def test_closed_set_status_word_is_flagged_not_blocking():
    """封閉集狀態詞只記錄、不判紅——避免重演 v1／v2 的假紅。"""
    contrastive = ("目前是已點交（執行中），不是歷史完成；"
                   "合約到期日為 2026/12/31。")
    out = assert_brain_uses_grounding(contrastive, SPEC)
    assert out["passed"] is True
    assert [h["literal"] for h in out["adjudication_hits"]] == ["歷史完成"]


@pytest.mark.req("face-exit-before-grounding:1")
def test_ruler_does_not_require_the_title():
    """identity 已由 execution chain 獨立證明，不由本尺重複要求。"""
    no_title = "目前狀態為已點交（執行中），到期前 30 天（2026/12/01）起才可發送點退。"
    assert assert_brain_uses_grounding(no_title, SPEC)["passed"] is True
    assert all("信義區套房A" not in lit for group in SPEC.answer_must_contain for lit in group)
