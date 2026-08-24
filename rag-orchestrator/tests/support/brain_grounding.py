"""C4b「真 brain 是否**使用** grounding 作答」的斷言量尺
（spec conversational-routing-execution 任務 6.1，R3.2）。

**版本：v2**（`c4b-ruler-v2-amendment.md`）。
v1 曾凍結但**未執行**，於首次付費量測前被 audit 反證——三處把「非 C4b 聲稱的能力」
寫成了失敗條件。v1 的逐案尺 `c4b-ruler-frozen.md` **維持 FROZEN、一字未改**；
本模組實作的是 v2。

```text
No model output was observed before amendment.
No paid C4b call had been executed.
Amendment was based solely on ruler semantics and known C4b claim boundaries.
```

## 責任邊界（v2 的核心，決定什麼**不**該進這把尺）

```text
C4a  證明 grounding 是**哪一筆**（OB-3 已機器斷言 case → fixture identity）
C4b  證明真 brain **有使用該筆 grounding 中被問到的值**
```

⇒ 回答**不必**複述帳單標題：那是在 C4b 這一層重驗 identity。
⇒ 語義方向（如「能不能收回」）**機械上不可靠**，交 6.3 人工判讀，
   不以 brittle substring 假裝 semantics。

## 三件、也只有三件事由機器判定

```text
1. 回答有使用「被問到的本筆 grounding value」        answer_must_contain
2. 沒有把明確屬於別筆的 instance-specific value 當本筆答案   answer_must_not_contain
3. 沒有退化成與 fixture grounding 無關的泛用回答      generic_fallback_markers
```

`adjudication_flags` 是**第四個維度但不阻斷**：命中只記錄，交 6.3 人工判讀
（方向性表述片段屬此類——「無法收回」可以出現在比較句、否定句、條件句裡，
「字面曾出現」不等價於「模型判錯」）。

## 結構性禁令（**拋例外**，不是只寫在註解裡）

```text
1. answer_must_contain 為空                → 未驗「有沒有用」，不構成 C4b 證據
2. 任一待驗字面出現在凍結的使用者輸入       → 那是測試自己餵進去的，不是 brain 引用的
3. 字面過長或含句讀（正向與**阻斷型反向**皆適用）→ 那是在鎖措辭，真 LLM 必假紅
4. generic_fallback_markers 為空            → 「是否退回泛用答案」未被驗
5. 阻斷型反向字面未宣告**別筆 fixture 出處** → 它就不是「別筆的值」，只是措辭（v2 新增）
6. 同一字面同時列為阻斷型反向與 adjudication → 語義矛盾（v2 新增）
```

⚠️ 禁令 5 是 v2 的 A／B 兩項修訂的**機制落點**：
`"無法收回"` 這類方向片段拿不出 fixture 出處，**在結構上就進不了阻斷集**。

⚠️ 禁令 2 對應任務 6.3 的 🔍V 理由（「需獨立確認引用字面不是測試自己餵進去的」）。

## 證據保全（v2 的 C 項）

`evaluate_brain_grounding()` **無論過與不過都回傳完整紀錄**，且：

```text
raw_answer      **原文逐字**，永不正規化——否定詞與句構必須留下
matched_spans   命中片段另欄，附前後文窗（單一 token 不足以 adjudicate）
```

`assert_brain_uses_grounding()` 失敗時拋 `BrainGroundingFailure`，
該例外帶 `.record`（同一份紀錄）——紅燈也留得下原文。
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

#: 單一字面的長度上限——超過即視為在鎖措辭（值不會這麼長，句子才會；最長的合法值是帳單標題，約 11 字）
_MAX_LITERAL_LEN = 16

#: 句讀／換行出現在待驗字面中 → 鎖的是句子而非值
_SENTENCE_MARKS = ("。", "！", "？", "\n", "，", "、")

#: 命中片段前後保留的字元數——否定詞（「不是」「並非」）與句構要留得住
_CONTEXT_WINDOW = 24


class GroundingUseNotAssertedError(AssertionError):
    """`answer_must_contain` 為空 → 未驗「brain 有沒有用 grounding」。"""


class FallbackNotAssertedError(AssertionError):
    """`generic_fallback_markers` 為空 → 未驗「是否退回泛用 KB 答案」。"""


class LiteralFedByTestError(AssertionError):
    """待驗字面出現在凍結的使用者輸入中。

    ⚠️ 這種字面即使出現在回答裡也**不是證據**：brain 只要原樣複述使用者的話就會命中。
    """


class WordingLockError(AssertionError):
    """待驗字面在鎖措辭（過長或含句讀）——真 LLM 非決定性，這種斷言必產生假紅。"""


class ProvenanceNotDeclaredError(AssertionError):
    """正向字面未宣告其 fixture 出處 → 無法排除「值是測試自己編的」。"""


class FoilProvenanceNotDeclaredError(AssertionError):
    """阻斷型反向字面未宣告**別筆** fixture 出處。

    ⚠️ v2：拿不出別筆出處的字面不是「別筆的值」，只是方向性措辭——
    它可以出現在比較句／否定句／條件句裡，不得據以判紅。改列 `adjudication_flags`。
    """


class ContradictoryFlagError(AssertionError):
    """同一字面同時是阻斷型反向與非阻斷 adjudication flag。"""


class AnswerTextRequiredError(AssertionError):
    """斷言對象不是回答文字（例如誤傳 grounding 物件）。"""


class BrainGroundingFailure(AssertionError):
    """C4b 斷言失敗；`.record` 帶完整紀錄（含 `raw_answer`）供 6.3 裁決。"""

    def __init__(self, message: str, record: "dict[str, Any]") -> None:
        super().__init__(message)
        self.record = record


#: 疑似「grounding／決策物件」的鍵——出現任一即拒絕
_NON_ANSWER_KEYS = frozenset({"grounding", "facts", "state", "decision", "system_md", "answer"})


def _spans(answer: str, literal: str) -> "list[dict[str, Any]]":
    """回傳該字面在原文中的所有出現位置與前後文窗（原文片段，不做任何正規化）。"""
    out: "list[dict[str, Any]]" = []
    start = answer.find(literal)
    while start != -1:
        lo = max(0, start - _CONTEXT_WINDOW)
        hi = min(len(answer), start + len(literal) + _CONTEXT_WINDOW)
        out.append({"literal": literal, "start": start, "context": answer[lo:hi]})
        start = answer.find(literal, start + 1)
    return out


@dataclass(frozen=True)
class BrainGroundingAssertion:
    """一個 C4b 案例的斷言基準（**須在跑 LLM 之前凍結**，不得看到回答再調）。"""

    case: str
    execution_face: str
    fixture_bill_id: int
    #: 凍結的使用者輸入（逐輪）——同時是禁令 2 的比對來源
    user_turns: Sequence[str]
    #: 每個元素＝一個事實值的可接受表面形式集合；任一命中即該組滿足
    answer_must_contain: "Sequence[Sequence[str]]"
    #: **阻斷型**反向：別筆 fixture 的 instance-specific value（每一條都須有 foil_provenance）
    answer_must_not_contain: Sequence[str] = ()
    #: 未落地標記（推託／泛論／要求再提供已提供之識別）
    generic_fallback_markers: Sequence[str] = ()
    #: **非阻斷**：方向性／語義表述片段；命中只記錄，交 6.3 人工判讀（v2 新增）
    adjudication_flags: Sequence[str] = ()
    #: 每組首個字面 → 本筆 fixture 欄位出處（如 "900003.total"）
    literal_provenance: "dict[str, str]" = field(default_factory=dict)
    #: 每個阻斷型反向字面 → **別筆** fixture 欄位出處（如 "900001.total"）
    foil_provenance: "dict[str, str]" = field(default_factory=dict)
    #: 誠實登記：本案已知**無法辨識實例**的字面（例：與另一筆 fixture 同值）
    known_non_discriminating: Sequence[str] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.answer_must_contain:
            raise GroundingUseNotAssertedError(
                f"案例 {self.case!r} 的 answer_must_contain 為空——"
                "未驗「brain 有沒有用 grounding」，不構成 C4b 通過的證據（任務 6.1）"
            )
        if not self.generic_fallback_markers:
            raise FallbackNotAssertedError(
                f"案例 {self.case!r} 未宣告 generic_fallback_markers——"
                "「是否退回泛用 KB 答案」是任務 6.1 明訂的維度，不得省略"
            )
        overlap = set(self.answer_must_not_contain) & set(self.adjudication_flags)
        if overlap:
            raise ContradictoryFlagError(
                f"案例 {self.case!r} 的 {sorted(overlap)} 同時是阻斷型反向與 adjudication flag——"
                "一個字面只能有一種身分"
            )
        joined_input = "\n".join(self.user_turns or ())

        def _check_literal(literal: str, kind: str) -> None:
            if len(literal) > _MAX_LITERAL_LEN or any(m in literal for m in _SENTENCE_MARKS):
                raise WordingLockError(
                    f"案例 {self.case!r} 的{kind}字面 {literal!r} 在鎖措辭"
                    f"（上限 {_MAX_LITERAL_LEN} 字且不得含句讀）"
                )
            if literal in joined_input:
                raise LiteralFedByTestError(
                    f"案例 {self.case!r} 的{kind}字面 {literal!r} 已出現在使用者輸入中——"
                    "brain 原樣複述即可命中，該字面不是引用證據（任務 6.3 🔍V 的關鍵）"
                )

        for group in self.answer_must_contain:
            if not group:
                raise GroundingUseNotAssertedError(
                    f"案例 {self.case!r} 有空的字面組——一組至少要有一個可接受寫法"
                )
            for literal in group:
                _check_literal(literal, "待驗")
            if group[0] not in self.literal_provenance:
                raise ProvenanceNotDeclaredError(
                    f"案例 {self.case!r} 的字面組 {group[0]!r} 未宣告 fixture 出處——"
                    "期望值一律自 frozen fixture 取得，不得在測試中另抄一份"
                )

        for literal in self.answer_must_not_contain:
            _check_literal(literal, "阻斷型反向")
            if literal not in self.foil_provenance:
                raise FoilProvenanceNotDeclaredError(
                    f"案例 {self.case!r} 的阻斷型反向字面 {literal!r} 未宣告別筆 fixture 出處——"
                    "拿不出別筆出處者不是『別筆的值』，只是方向性措辭，"
                    "應改列 adjudication_flags（非阻斷，交 6.3 判讀）"
                )


def evaluate_brain_grounding(
    answer: Any,
    spec: BrainGroundingAssertion,
    *,
    foil_literals: "Optional[Sequence[str]]" = None,
) -> "dict[str, Any]":
    """對**最終回答文字**評分，**無論過與不過都回傳完整紀錄**（v2 的 C 項）。

    :param answer: 真 LLM 產出的回答文字（**必須是字串**）。
    :param foil_literals: 選填，額外的「別筆 fixture 字面」（呼叫端自 fixture 表算出）。

    紀錄中 ``raw_answer`` 為**原文逐字**，永不正規化；``matched_spans`` 另欄並附前後文窗——
    「是待對帳，**不是**待繳費」這種判讀需要否定詞與句構，單一 token 不足以裁決。
    """
    if isinstance(answer, dict):
        offending = _NON_ANSWER_KEYS & set(answer)
        raise AnswerTextRequiredError(
            f"斷言對象必須是最終回答文字，收到疑似 grounding／回應物件"
            f"（含鍵 {sorted(offending) or sorted(answer)[:3]}）"
        )
    if not isinstance(answer, str):
        raise AnswerTextRequiredError(
            f"斷言對象必須是最終回答文字，收到 {type(answer).__name__}"
        )

    matched_spans: "list[dict[str, Any]]" = []
    missing_groups: "list[list[str]]" = []
    for group in spec.answer_must_contain:
        hit = next((lit for lit in group if lit in answer), None)
        if hit is None:
            missing_groups.append(list(group))
        else:
            for sp in _spans(answer, hit):
                matched_spans.append({"group_key": group[0], **sp})

    blocking_foils = list(spec.answer_must_not_contain) + list(foil_literals or ())
    wrong_instance_hits = [sp for lit in blocking_foils for sp in _spans(answer, lit)]
    fallback_hits = [sp for lit in spec.generic_fallback_markers for sp in _spans(answer, lit)]
    #: 非阻斷——命中不影響 passed，只交 6.3
    adjudication_hits = [sp for lit in spec.adjudication_flags for sp in _spans(answer, lit)]

    violated = []
    if missing_groups:
        violated.append("value_not_used")
    if wrong_instance_hits:
        violated.append("wrong_instance")
    if fallback_hits:
        violated.append("generic_fallback")

    return {
        "case": spec.case,
        "execution_face": spec.execution_face,
        "fixture_bill_id": spec.fixture_bill_id,
        "passed": not violated,
        "raw_answer": answer,                       # 原文逐字，永不正規化
        "matched_spans": matched_spans,             # 命中片段另欄（附前後文窗）
        "missing_groups": missing_groups,
        "wrong_instance_hits": wrong_instance_hits,
        "fallback_hits": fallback_hits,
        "adjudication_hits": adjudication_hits,     # **非阻斷**，交 6.3 人工判讀
        "violated_dimensions": violated,
        "literal_provenance": dict(spec.literal_provenance),
        "foil_provenance": dict(spec.foil_provenance),
        "known_non_discriminating": list(spec.known_non_discriminating),
        "fallback_markers_checked": list(spec.generic_fallback_markers),
        "adjudication_flags_checked": list(spec.adjudication_flags),
    }


def assert_brain_uses_grounding(
    answer: Any,
    spec: BrainGroundingAssertion,
    *,
    foil_literals: "Optional[Sequence[str]]" = None,
) -> "dict[str, Any]":
    """`evaluate_brain_grounding` 的斷言包裝：不過即拋 `BrainGroundingFailure`。

    ⚠️ 例外帶 `.record`（與通過時同格式的完整紀錄，含 `raw_answer`）——
    紅燈也必須留下原文，否則 6.3 無法把 `ruler_false_red` 與 `wrong_direction` 分開。
    """
    record = evaluate_brain_grounding(answer, spec, foil_literals=foil_literals)
    if not record["passed"]:
        raise BrainGroundingFailure(
            f"C4b 案例 {spec.case!r} 未通過（{record['violated_dimensions']}）：\n"
            f"  未引用該筆實際值（每組任一即可）：{record['missing_groups']}\n"
            f"  引用到別筆的字面：{[h['literal'] for h in record['wrong_instance_hits']]}\n"
            f"  退回泛用答案的標記：{[h['literal'] for h in record['fallback_hits']]}\n"
            f"  （非阻斷）待裁決標記：{[h['literal'] for h in record['adjudication_hits']]}\n"
            f"  回答原文：{answer!r}",
            record,
        )
    return record
