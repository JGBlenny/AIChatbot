"""C4a 執行鏈閉環的斷言量尺（spec conversational-routing-execution 任務 5.1，R3.1／R4.2）。

⚠️ **斷言對象只有 grounding，明文禁止對最終回答文字下斷言。**
C4a 用的是腳本化 brain——它的輸出是測試自己寫的，對它下斷言等於自證。
本模組因此在**結構上**只接受 grounding 字串；傳入疑似最終回應者一律拒絕。

**兩個正交維度**（缺一不可，且不得互相替代）：

``grounding_must_contain``
    **送達性**——該筆的實際值字面是否真的進了底稿（例：帳單編號、金額）。
    只證明「查到的東西送到了」，**不證明**送到的東西足以回答問題。

``required_grounding_facts``
    **充分性**——formatter 是否產出了回答該問題所必需的**事實鍵**
    （grounding 中的 ``【鍵】`` 標記，例：``發送判定``）。
    比對的是鍵，**不看 LLM 措辭**。

⚠️ ``required_grounding_facts`` 為空即視為**未驗充分性**，本模組直接拒絕
（任務 5.2 的紀律由此在機制上強制，無法靠忘記填而繞過）。
"""

import re
from dataclasses import dataclass, field
from typing import Any

#: grounding 中事實鍵的標記形式：`【鍵】`（各面向 formatter 共用，見 services/jgb/bills.py）
_FACT_KEY = re.compile(r"【([^】]+)】")

#: 疑似「最終回應物件」的鍵——出現任一即拒絕（防止把腳本化 brain 的輸出當斷言對象）
_ANSWER_LIKE_KEYS = frozenset({"answer", "message", "content", "reply", "text"})


class ChainClosureScopeError(AssertionError):
    """closure scope 未宣告，或宣告了未知的 scope。"""


class AnswerTextAssertionError(AssertionError):
    """試圖對最終回答文字下斷言。

    ⚠️ 腳本化 brain 的輸出由測試自己撰寫，對它斷言等於自證——本量尺結構上不允許。
    """


class SufficiencyNotAssertedError(AssertionError):
    """`required_grounding_facts` 為空 → 未驗充分性，不構成 C4a 通過的證據。"""


#: 目前可宣告的閉環範圍。
#:
#: ⚠️ ``numeric_bill_ref`` 是**部分閉環**：`bill_ref` adapter 的非數字分支會呼叫
#: 尚未遷移的 `get_contracts`，故該分支**不在**本次 closure claim 之內。
#: 任務 5.5 報告時 **SHALL NOT** 把部分閉環寫成 full closure。
CLOSURE_SCOPES: "frozenset[str]" = frozenset({"numeric_bill_ref"})


def extract_fact_keys(grounding: str) -> "set[str]":
    """取出 grounding 中所有事實鍵（`【鍵】` 的鍵名）。"""
    return set(_FACT_KEY.findall(grounding or ""))


@dataclass(frozen=True)
class ChainClosureAssertion:
    """一個 C4a 案例的斷言基準（**須在執行前明示**，不得看到輸出再調）。"""

    case: str
    #: 送達性：這些字面必須出現在 grounding 中
    grounding_must_contain: "list[str]"
    #: 充分性：這些事實鍵必須由 formatter 產出（不得為空）
    required_grounding_facts: "list[str]"
    #: 本案例所宣告的閉環範圍（見 `CLOSURE_SCOPES`）
    closure_scope: str = "numeric_bill_ref"
    #: 選填：說明為何這組 facts 是「回答該問題所必需」
    rationale: str = ""
    #: 選填：本案例已知不涵蓋的部分（會原樣帶進報告，避免部分閉環被寫成 full）
    not_covered: "list[str]" = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.closure_scope not in CLOSURE_SCOPES:
            raise ChainClosureScopeError(
                f"未知的 closure_scope：{self.closure_scope!r}；"
                f"可用：{sorted(CLOSURE_SCOPES)}"
            )
        if not self.required_grounding_facts:
            raise SufficiencyNotAssertedError(
                f"案例 {self.case!r} 的 required_grounding_facts 為空——"
                "未驗充分性即不構成 C4a 通過的證據（任務 5.2）"
            )


def assert_chain_closure(grounding: Any, spec: ChainClosureAssertion) -> "dict[str, Any]":
    """對 grounding 執行送達性與充分性兩維度斷言；通過回傳可入報告的結果摘要。

    ⚠️ `grounding` **必須是字串**。傳入 dict／物件（疑似最終回應）一律拒絕——
    這是「不得對最終回答文字下斷言」在機制上的落點，而非只寫在註解裡。
    """
    if isinstance(grounding, dict):
        offending = _ANSWER_LIKE_KEYS & set(grounding)
        raise AnswerTextAssertionError(
            f"斷言對象必須是 grounding 字串，收到疑似最終回應物件"
            f"（含鍵 {sorted(offending) or sorted(grounding)[:3]}）"
        )
    if not isinstance(grounding, str):
        raise AnswerTextAssertionError(
            f"斷言對象必須是 grounding 字串，收到 {type(grounding).__name__}"
        )

    missing_literals = [s for s in spec.grounding_must_contain if s not in grounding]
    present_keys = extract_fact_keys(grounding)
    missing_facts = [k for k in spec.required_grounding_facts if k not in present_keys]

    if missing_literals or missing_facts:
        raise AssertionError(
            f"C4a 案例 {spec.case!r} 未閉環：\n"
            f"  送達性缺字面：{missing_literals}\n"
            f"  充分性缺事實鍵：{missing_facts}（實際產出：{sorted(present_keys)}）"
        )

    return {
        "case": spec.case,
        "closure_scope": spec.closure_scope,
        "delivered": list(spec.grounding_must_contain),
        "facts_asserted": list(spec.required_grounding_facts),
        "facts_present": sorted(present_keys),
        "not_covered": list(spec.not_covered),
    }
