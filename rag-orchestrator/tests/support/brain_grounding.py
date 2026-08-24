"""C4b「真 brain 是否**使用** grounding 作答」的斷言量尺
（spec conversational-routing-execution 任務 6.1，R3.2）。

## 與 C4a 量尺的分工（**不可互相替代**）

```text
C4a  tests/support/chain_closure.py   斷言對象＝grounding；**明文禁止**碰最終回答文字
C4b  本模組                            斷言對象＝**最終回答文字**；grounding 已由 C4a 證明送達
```

C4a 用腳本化 brain，對其輸出下斷言等於自證，故 `chain_closure` 在結構上拒收回答文字。
C4b 用**真 LLM**，回答文字不是測試寫的，才**首次**成為可斷言對象。
⚠️ 因此**不得**把本模組用在腳本化 brain 上——那會讓 C4a 的禁令從後門失效。

## 兩個維度（任務 6.1 明訂，且**只有**這兩個）

``answer_must_contain``
    **該筆實際值字面是否出現**。每個元素是**一組可接受的表面形式**
    （同一個事實值的不同寫法，如 ``("7,500", "7500")``），任一命中即該組滿足。
    ⚠️ 用「一組替代寫法」而非單一字串，是為了在**不鎖措辭**的前提下仍能鎖住值：
    真 LLM 會寫 `NT$ 7,500` 也會寫 `7,500 元`，但它**不會**把 7,500 寫成 18,000。

``answer_must_not_contain`` ／ ``generic_fallback_markers``
    **是否退回泛用 KB 答案**、以及**是否引用到別筆**。
    前者收「錯誤實例的字面」（別筆 fixture 的值），後者收「未落地標記」
    （推託、泛論、要求使用者再提供已提供之識別）。

## 四條結構性禁令（**拋例外**，不是只寫在註解裡）

```text
1. answer_must_contain 為空            → 未驗「有沒有用」，不構成 C4b 證據
2. 任一待驗字面出現在凍結的使用者輸入   → 那是測試自己餵進去的，不是 brain 引用的
3. 字面過長或含句讀                     → 那是在鎖措辭，真 LLM 非決定性，必假紅
4. generic_fallback_markers 為空        → 「是否退回泛用答案」未被驗
```

⚠️ 禁令 2 直接對應任務 6.3 的 🔍V 理由：
「需獨立確認『引用字面』不是測試自己餵進去的」——在**量尺層**先擋掉，
而不是等驗證者事後用肉眼看。
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

#: 單一字面的長度上限——超過即視為在鎖措辭（值不會這麼長，句子才會；最長的合法值是帳單標題，約 11 字）
_MAX_LITERAL_LEN = 16

#: 句讀／換行出現在待驗字面中 → 鎖的是句子而非值
_SENTENCE_MARKS = ("。", "！", "？", "\n", "，", "、")


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
    """待驗字面未宣告其 fixture 出處 → 無法排除「值是測試自己編的」。"""


class AnswerTextRequiredError(AssertionError):
    """斷言對象不是回答文字（例如誤傳 grounding 物件）。"""


#: 疑似「grounding／決策物件」的鍵——出現任一即拒絕
_NON_ANSWER_KEYS = frozenset({"grounding", "facts", "state", "decision", "system_md"})


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
    #: 錯誤實例的字面（別筆 fixture 的值）——出現即判引用到別筆
    answer_must_not_contain: Sequence[str] = ()
    #: 未落地標記（推託／泛論／要求再提供已提供之識別）
    generic_fallback_markers: Sequence[str] = ()
    #: 每組首個字面 → fixture 欄位出處（如 "900003.total"）
    literal_provenance: "dict[str, str]" = field(default_factory=dict)
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
                "「是否退回泛用 KB 答案」是任務 6.1 明訂的第二個維度，不得省略"
            )
        joined_input = "\n".join(self.user_turns or ())
        for group in self.answer_must_contain:
            if not group:
                raise GroundingUseNotAssertedError(
                    f"案例 {self.case!r} 有空的字面組——一組至少要有一個可接受寫法"
                )
            for literal in group:
                if len(literal) > _MAX_LITERAL_LEN or any(m in literal for m in _SENTENCE_MARKS):
                    raise WordingLockError(
                        f"案例 {self.case!r} 的待驗字面 {literal!r} 在鎖措辭"
                        f"（上限 {_MAX_LITERAL_LEN} 字且不得含句讀）"
                    )
                if literal in joined_input:
                    raise LiteralFedByTestError(
                        f"案例 {self.case!r} 的待驗字面 {literal!r} 已出現在使用者輸入中——"
                        "brain 原樣複述即可命中，該字面不是引用證據（任務 6.3 🔍V 的關鍵）"
                    )
            if group[0] not in self.literal_provenance:
                raise ProvenanceNotDeclaredError(
                    f"案例 {self.case!r} 的字面組 {group[0]!r} 未宣告 fixture 出處——"
                    "期望值一律自 frozen fixture 取得，不得在測試中另抄一份"
                )


def assert_brain_uses_grounding(
    answer: Any,
    spec: BrainGroundingAssertion,
    *,
    foil_literals: "Optional[Sequence[str]]" = None,
) -> "dict[str, Any]":
    """對**最終回答文字**執行兩維度斷言；通過回傳可直接入 6.3 報告的摘要。

    :param answer: 真 LLM 產出的回答文字（**必須是字串**）。
    :param foil_literals: 選填，額外的「別筆 fixture 字面」；與
        ``spec.answer_must_not_contain`` 合併判定。

    回傳的 ``quoted_literals`` 即**實際被引用的字面**——
    任務 6.3 要求逐面向列出的就是它，不是「通過/未通過」而已。
    """
    if isinstance(answer, dict):
        offending = _NON_ANSWER_KEYS & set(answer)
        raise AnswerTextRequiredError(
            f"斷言對象必須是最終回答文字，收到疑似 grounding／決策物件"
            f"（含鍵 {sorted(offending) or sorted(answer)[:3]}）"
        )
    if not isinstance(answer, str):
        raise AnswerTextRequiredError(
            f"斷言對象必須是最終回答文字，收到 {type(answer).__name__}"
        )

    quoted: "dict[str, str]" = {}
    missing_groups: "list[list[str]]" = []
    for group in spec.answer_must_contain:
        hit = next((lit for lit in group if lit in answer), None)
        if hit is None:
            missing_groups.append(list(group))
        else:
            quoted[group[0]] = hit

    wrong_instance = [s for s in (list(spec.answer_must_not_contain) + list(foil_literals or ()))
                      if s in answer]
    fallback_hits = [s for s in spec.generic_fallback_markers if s in answer]

    if missing_groups or wrong_instance or fallback_hits:
        raise AssertionError(
            f"C4b 案例 {spec.case!r} 未通過：\n"
            f"  未引用該筆實際值（每組任一即可）：{missing_groups}\n"
            f"  引用到別筆的字面：{wrong_instance}\n"
            f"  退回泛用答案的標記：{fallback_hits}\n"
            f"  實際引用到的字面：{quoted}"
        )

    return {
        "case": spec.case,
        "execution_face": spec.execution_face,
        "fixture_bill_id": spec.fixture_bill_id,
        "quoted_literals": quoted,
        "literal_provenance": dict(spec.literal_provenance),
        "known_non_discriminating": list(spec.known_non_discriminating),
        "fallback_markers_checked": list(spec.generic_fallback_markers),
    }
