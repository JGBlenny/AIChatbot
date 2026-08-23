"""unit：`InstanceEvidenceExtractor` 的**空輸入契約**
（spec routing-disambiguation 任務 2.4｜R3.1）。

```text
None ／ "" ／ "   " ／ "\\n\\t "
   → empty InstanceEvidence（positive=∅、counter=∅、spans=()）
   → Task 3 對應：gate 判 abstain
```

⚠️ **不得靠 exception → fail-open 間接達成**（設計明訂）：
靠例外的行為不會被型別或測試鎖住，而且會讓兩件本質不同的事變得無法區分——

```text
「沒有訊號」            ← 應回空 evidence
「extractor 壞掉後被吃掉」← 應向上拋，由 seam 依 4.4 判 abstain
```

故本檔同時鎖**反向**：抽取器**不得**有 blanket try/except；
餵入結構上不合法的輸入時 SHALL 拋出，而非靜默回空。
fail-open 的正確位置在 production seam（任務 4.4），不在抽取器內部。
"""
import pytest

pytestmark = pytest.mark.unit

EMPTY_INPUTS = [None, "", "   ", "\n\t ", "　"]   # 末筆為全形空白


def _extractor():
    from services.instance_evidence import InstanceEvidenceExtractor
    return InstanceEvidenceExtractor()


@pytest.mark.req("routing-disambiguation:3.1")
@pytest.mark.parametrize("value", EMPTY_INPUTS, ids=["none", "empty", "spaces", "ws", "ideographic"])
def test_empty_input_yields_empty_evidence(value):
    e = _extractor().extract(value)
    assert e.positive == frozenset() and e.counter == frozenset() and e.spans == ()
    assert e.has_instance_signal is False and e.has_explanation_signal is False


@pytest.mark.req("routing-disambiguation:3.1")
def test_empty_input_path_is_not_exception_driven():
    """⚠️ 反向鎖：抽取器**不得**把任意錯誤吞成「空 evidence」。

    若這裡回的是空 evidence 而非拋出，代表內部有 blanket try/except——
    屆時「沒有訊號」與「壞掉了」在型別上不可區分，
    而 gate 會把後者當成前者，一路 abstain 下去而沒有人知道。
    """
    class _NotAString:
        def __bool__(self):
            return True

    with pytest.raises(Exception):
        _extractor().extract(_NotAString())


@pytest.mark.req("routing-disambiguation:3.1")
def test_whitespace_only_is_not_confused_with_a_real_question():
    """空白輸入與真問句必須落在不同結果——否則上一條的空 evidence 沒有意義。"""
    x = _extractor()
    assert x.extract("   ") == x.extract(None)
    assert x.extract("我的這張帳單") != x.extract("   ")
