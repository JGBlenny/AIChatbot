"""`InstanceEvidence` 訊號契約與決定性抽取器
（spec routing-disambiguation 元件 1｜任務 2.1／2.2／2.3｜R2.1, R2.3, R3.1）。

把「問句是否指涉特定個體」表示為 **first-class、可程式消費、決定性**的值物件。

⚠️ **SHALL NOT 呼叫 LLM、SHALL NOT 讀取相似度分數、SHALL NOT 做 IO。**
與相似度正交是本元件存在的**唯一**理由（R3.1）；若它偷讀分數，
整個方案退化為「換個地方做相似度競爭」（R2.3）。

⚠️ **正反兩種證據都要帶**：research.md 主題 1 實測，反向標記 `explanation_request`
比任一正向特徵更強（8/9 vs 最高 5/11）——**只找正向特徵會漏掉「規則問句」這一半**。

⚠️ **本元件的最大風險已登記**（design 元件 1）：規則集是**看著 protocol v1 的 20 筆
案例事後挑出**的，屬定義上的 overfit。**未經未見案例（holdout）驗證前，
SHALL NOT 宣稱本元件可用。**

⚠️ **規則集為版本化資產**：本檔的 `POSITIVE_PATTERNS`／`COUNTER_PATTERNS`
變更即構成 ruleset 變更，SHALL 重跑 protocol v1 並保留前版結果（R3.5／任務 2.6）。
"""
import re
from dataclasses import dataclass
from typing import Final, FrozenSet, Literal, Mapping, Optional, Tuple

EvidenceKind = Literal["identifier", "possessive", "lookup_verb", "problem_report"]
CounterKind = Literal["explanation_request"]

# ── 規則集 ie-v1（逐條取自 research.md 主題 1 的實測特徵表，不自行增刪）──
#
# ⚠️ `identifier` 的 id-like token 樣式**沿用** `conversational_engine._ID_TOKEN_RE`
#    的既有慣例（含「與日期分隔符或其他數字相鄰者不算識別」這道 e2e 真跑逼出的守門），
#    在此**逐字複製而非 import**——本模組須維持零相依、零 IO（R3.1／任務 2.5），
#    import `conversational_engine` 會拖進 config 載入。
#    ⚠️ 兩處樣式**不得漂移**：同步守門屬任務 2.5 的不變量測試。
_ID_TOKEN_RE: Final = re.compile(r"(?<![\d/\-])(?<!\d\.)\d{4,15}(?![\d/\-])(?!\.\d)")

#: 整句即編號（沿用 `conversational_engine._looks_like_identifier`：純數字 2–15 位）
_WHOLE_ID_MIN, _WHOLE_ID_MAX = 2, 15

POSITIVE_PATTERNS: Final[Mapping[str, str]] = {
    "possessive": r"我的|我這|這張|這筆|這期",
    "lookup_verb": r"幫我查|查一下|多少錢",
    "problem_report": r"為什麼|怎麼會|怪怪的|失敗|不了|不出|卡",
}

COUNTER_PATTERNS: Final[Mapping[str, str]] = {
    # `…嗎` 為句尾疑問標記，另以 `_ENDS_WITH_MA` 判定（不能當成句中子字串）
    "explanation_request": r"怎麼算|是怎麼|在哪裡|有哪些|哪幾種",
}

_ENDS_WITH_MA: Final = re.compile(r"嗎[\s？?！!。.]*$")

_POSITIVE_RE: Final = {k: re.compile(v) for k, v in POSITIVE_PATTERNS.items()}
_COUNTER_RE: Final = {k: re.compile(v) for k, v in COUNTER_PATTERNS.items()}


@dataclass(frozen=True)
class InstanceEvidence:
    """問句側的個體指涉證據（決定性；零 LLM）。"""

    positive: FrozenSet[str]
    counter: FrozenSet[str]
    #: 各證據命中的原文片段（可解釋性／稽核）
    #: ⚠️ 用 tuple 而非 dict：`frozen=True` 只凍結**欄位綁定**，
    #:    dict 內容仍可 mutate——型別契約會名不副實（任務 2.1）。
    spans: Tuple[Tuple[str, str], ...] = ()

    @property
    def has_instance_signal(self) -> bool:
        return bool(self.positive)

    @property
    def has_explanation_signal(self) -> bool:
        return bool(self.counter)


EMPTY_EVIDENCE: Final = InstanceEvidence(positive=frozenset(), counter=frozenset(), spans=())


class InstanceEvidenceExtractor:
    """決定性抽取器（零 LLM／零 IO／不讀相似度）。"""

    RULESET_VERSION: Final[str] = "ie-v1"

    def extract(self, question: Optional[str]) -> InstanceEvidence:
        """`None`／空白字串 → **空 evidence**（正反皆空）→ 由 gate 判 `abstain`。

        ⚠️ 明訂此路徑，**不依賴 exception → fail-open 間接達成**——
        靠例外的行為不會被型別或測試鎖住（任務 2.4）。
        """
        text = (question or "").strip()
        if not text:
            return EMPTY_EVIDENCE

        positive, counter, spans = set(), set(), []

        ident = self._identifier_span(text)
        if ident is not None:
            positive.add("identifier")
            spans.append(("identifier", ident))

        for kind, rx in _POSITIVE_RE.items():
            m = rx.search(text)
            if m:
                positive.add(kind)
                spans.append((kind, m.group(0)))

        for kind, rx in _COUNTER_RE.items():
            m = rx.search(text)
            if m:
                counter.add(kind)
                spans.append((kind, m.group(0)))
        if "explanation_request" not in counter:
            m = _ENDS_WITH_MA.search(text)
            if m:
                counter.add("explanation_request")
                spans.append(("explanation_request", m.group(0)))

        return InstanceEvidence(positive=frozenset(positive), counter=frozenset(counter),
                                spans=tuple(spans))

    @staticmethod
    def _identifier_span(text: str) -> Optional[str]:
        """整句純數字（2–15 位）→ 該句；否則取第一個 id-like token（4–15 位）。"""
        if text.isdigit() and _WHOLE_ID_MIN <= len(text) <= _WHOLE_ID_MAX:
            return text
        m = _ID_TOKEN_RE.search(text)
        return m.group(0) if m else None
