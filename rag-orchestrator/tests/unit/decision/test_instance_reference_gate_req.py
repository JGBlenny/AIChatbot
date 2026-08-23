"""unit：`instance_reference_gate` 的三值判定（任務 3.1／3.2／3.4｜R1.1, R1.2, R1.3, R3.1）。

判定表（design v1.2，**不得順手加產品 heuristic**）：

```text
face 不要求 instance          → allow
positive ≠ ∅ 且 counter = ∅   → allow
positive = ∅ 且 counter ≠ ∅   → block      ← 雙條件，缺一不可
positive ≠ ∅ 且 counter ≠ ∅   → abstain
positive = ∅ 且 counter = ∅   → abstain
```

⚠️ **第三、四列是本檔的重點**：
反向標記**不得採 veto**——凍結案例集裡就有反例
（`我的這張點退帳單金額怎麼算出來的` 同時命中 possessive 與 explanation_request）。
寫成 `if counter: block` 會誤殺它，正是前案 3.4「rule 側修好、instance 側受傷」。

⚠️ **`abstain` 必須真的保有第三態**：不得被摺疊成 `allow` 或 `block`。
rollout 政策（不阻擋）效果像 allow，**不代表 verdict 語義是 allow**——
稽核、holdout 的 abstain 率、未來 L5 clarification 都要讀得到它。
"""
import dataclasses

import pytest

pytestmark = pytest.mark.unit


def _gate():
    from services import instance_reference_gate as m
    return m


def _ev(positive=(), counter=()):
    from services.instance_evidence import InstanceEvidence
    return InstanceEvidence(positive=frozenset(positive), counter=frozenset(counter), spans=())


def _decide(positive=(), counter=(), requires=True):
    return _gate().instance_reference_gate(_ev(positive, counter), face_requires_instance=requires)


# ── 判定表逐列 ────────────────────────────────────────
@pytest.mark.req("routing-disambiguation:1.1")
@pytest.mark.parametrize("positive,counter,requires,expected", [
    (["possessive"], [], False, "allow"),                       # face 不要求 instance
    ([], ["explanation_request"], False, "allow"),              # 同上：連 block 條件都不看
    (["possessive"], [], True, "allow"),
    ([], ["explanation_request"], True, "block"),
    (["possessive"], ["explanation_request"], True, "abstain"),
    ([], [], True, "abstain"),
], ids=["not-required-pos", "not-required-ctr", "pos-only", "ctr-only", "mixed", "no-signal"])
def test_decision_table(positive, counter, requires, expected):
    assert _decide(positive, counter, requires).verdict == expected


# ── block 的雙條件：反向標記不得 veto ──────────────────
@pytest.mark.req("routing-disambiguation:1.3")
def test_counter_evidence_is_not_a_veto():
    """⚠️ 真實反例（protocol v1 的 INSTANCE 第一筆），不是假想情境。"""
    from services.instance_evidence import InstanceEvidenceExtractor
    ev = InstanceEvidenceExtractor().extract("我的這張點退帳單金額怎麼算出來的")
    assert ev.positive and ev.counter, "本案例的前提（正反同時命中）已不成立，反例失效"

    d = _gate().instance_reference_gate(ev, face_requires_instance=True)
    assert d.verdict != "block", (
        "正反證據同時存在卻判 block——反向標記被當成 veto，"
        "instance 問句會被誤殺（前案 3.4 的形態）")
    assert d.verdict == "abstain"


@pytest.mark.req("routing-disambiguation:1.3")
def test_block_requires_both_conditions():
    """只有「無正向 ＋ 有反向」得 block；其餘任何組合皆不得 block。"""
    assert _decide([], ["explanation_request"]).verdict == "block"
    for positive, counter in ([["possessive"], []], [["possessive"], ["explanation_request"]], [[], []]):
        assert _decide(positive, counter).verdict != "block"


# ── abstain 的第三態不得被摺疊（兩個方向都鎖）──────────
@pytest.mark.req("routing-disambiguation:1.3")
@pytest.mark.parametrize("positive,counter", [(["possessive"], ["explanation_request"]), ([], [])],
                         ids=["mixed", "no-signal"])
def test_abstain_is_not_collapsed_into_allow_or_block(positive, counter):
    v = _decide(positive, counter).verdict
    assert v == "abstain", f"第三態被摺疊成 {v!r}"
    assert v != "allow" and v != "block"


@pytest.mark.req("routing-disambiguation:1.3")
def test_rollout_action_is_a_separate_field_from_verdict():
    """`abstain` 的**政策效果**是不阻擋，但**語義**不是 allow——兩者不得併成一欄。"""
    m = _gate()
    mixed = _decide(["possessive"], ["explanation_request"])
    blocked = _decide([], ["explanation_request"])
    allowed = _decide(["possessive"], [])

    assert m.suppresses_hint(mixed) is False and mixed.verdict == "abstain", \
        "政策不阻擋就把 verdict 寫成 allow——abstain 在型別上消失了"
    assert m.suppresses_hint(blocked) is True
    assert m.suppresses_hint(allowed) is False


# ── 可稽核性與不可變 ─────────────────────────────────
@pytest.mark.req("routing-disambiguation:3.1")
def test_reason_names_the_evidence_that_drove_the_verdict():
    d = _decide([], ["explanation_request"])
    assert "explanation_request" in d.reason
    assert _decide(["possessive"], []).reason.count("possessive") == 1
    assert _decide([], [], requires=False).reason == "face-not-instance-requiring"


@pytest.mark.req("routing-disambiguation:3.1")
def test_decision_is_immutable_and_carries_the_evidence_sets():
    d = _decide(["possessive"], ["explanation_request"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.verdict = "allow"
    assert d.positive == frozenset({"possessive"}) and d.counter == frozenset({"explanation_request"})


@pytest.mark.req("routing-disambiguation:3.1")
def test_gate_is_deterministic():
    first = _decide(["possessive"], ["explanation_request"])
    for _ in range(20):
        assert _decide(["possessive"], ["explanation_request"]) == first
