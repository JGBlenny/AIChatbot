"""規則集的版本化與**啟用守門**
（spec routing-disambiguation 元件 4｜任務 2.6｜R3.5, R7.2, R9.2）。

責任：使規則集成為**可追溯、可比較**的資產，並讓「未經 matching holdout 驗證者
不得啟用 gate」成為**結構上不可繞過**的事實。

本檔含 **gate 判定**（任務 3.1／3.2）與 **membership × rollout 合取**（任務 3.3）。
⚠️ **仍不碰 seam**：`GateDecision` 尚未被 production routing 消費（任務 4.2），
   故 routing 行為此刻完全不變。

⚠️ **三重 digest 綁定**，缺一不可：

```text
status == "passed"                                  ← 防「沒跑過」與「跑了但失敗」
holdout.ruleset_digest  == manifest.digest          ← 防「舊版 PASS 沿用到改過的規則」
holdout.protocol_digest == 現行量尺 digest           ← 防「舊尺 PASS 沿用到新尺」
```

原設計的 `holdout_result != None` 只防 missing、**不防 failed**——
`"FAILED"` 也是 non-None，照那份契約反而**可以**開旗標。
那是**假的 fail-closed**，與前案 `startswith("[gate]")` 恆為 False 的分類器同型。

⚠️ **本模組是本專案僅三處不 fail-open 的其中之一**：拒絕即拋出，**不得降級為 warning**。
"""
import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, FrozenSet, Literal, Mapping

HoldoutStatus = Literal["not_run", "passed", "failed"]


class GateNotEnablable(RuntimeError):
    """規則集未經 matching holdout 驗證——**不得啟用 gate**。"""


@dataclass(frozen=True)
class HoldoutRecord:
    """一次 holdout 驗證的結果。

    **綁定它驗的是「哪一版規則、用哪一份資料、依哪支量尺」**——
    三者任一對不上，這筆 PASS 就不屬於當前候選。
    """

    status: HoldoutStatus
    ruleset_digest: str = ""
    protocol_digest: str = ""
    dataset_id: str = ""
    dataset_digest: str = ""


@dataclass(frozen=True)
class RulesetManifest:
    """規則集作為**版本化資產**：內容雜湊、版本、holdout 紀錄。

    ⚠️ pattern 表以 `MappingProxyType` 保存**副本**——`frozen=True` 只凍結欄位綁定，
    直接存 dict 會讓「規則集不可變」名不副實（同 `InstanceEvidence.spans` 的理由）。
    """

    version: str
    positive_patterns: Mapping[str, str]
    counter_patterns: Mapping[str, str]
    digest: str
    holdout: HoldoutRecord = field(default_factory=lambda: HoldoutRecord(status="not_run"))

    def __post_init__(self):
        object.__setattr__(self, "positive_patterns",
                           MappingProxyType(dict(self.positive_patterns)))
        object.__setattr__(self, "counter_patterns",
                           MappingProxyType(dict(self.counter_patterns)))


def ruleset_digest(version: str, positive: Mapping[str, str], counter: Mapping[str, str]) -> str:
    """規則集內容雜湊：**規則一改，digest 就變**，舊的 holdout PASS 隨即失效。"""
    body = {"version": version,
            "positive": dict(sorted(positive.items())),
            "counter": dict(sorted(counter.items()))}
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode()).hexdigest()[:16]


def current_manifest() -> RulesetManifest:
    """當前規則集的 manifest。

    ⚠️ `holdout.status` **恆為 `not_run`，直到任務 6 的 unseen holdout 做出裁決**。
    此處不得先寫 `passed`——量尺測得出「PASS 時會放行」，
    **不等於** production manifest 現在可以寫 PASS。
    """
    from services.instance_evidence import (COUNTER_PATTERNS, POSITIVE_PATTERNS,
                                            InstanceEvidenceExtractor)
    version = InstanceEvidenceExtractor.RULESET_VERSION
    return RulesetManifest(
        version=version,
        positive_patterns=POSITIVE_PATTERNS,
        counter_patterns=COUNTER_PATTERNS,
        digest=ruleset_digest(version, POSITIVE_PATTERNS, COUNTER_PATTERNS),
        holdout=HoldoutRecord(status="not_run"),
    )


def assert_gate_enablable(manifest: RulesetManifest, *, active_protocol_digest: str) -> None:
    """三條同時成立才允許啟用；否則 `GateNotEnablable`。

    ⚠️ **SHALL NOT 降級為 warning**——守門若可被降級，它就不是守門。
    """
    holdout = manifest.holdout
    if holdout is None or holdout.status != "passed":
        raise GateNotEnablable(
            f"holdout 狀態為 {getattr(holdout, 'status', None)!r}——"
            "僅 'passed' 得啟用（'not_run' 與 'failed' 皆拒絕）")
    if holdout.ruleset_digest != manifest.digest:
        raise GateNotEnablable(
            f"holdout 驗的是規則集 {holdout.ruleset_digest!r}，當前為 {manifest.digest!r}"
            "——規則集改過後，舊的 PASS 不得沿用")
    if holdout.protocol_digest != active_protocol_digest:
        raise GateNotEnablable(
            f"holdout 依的量尺為 {holdout.protocol_digest!r}，現行為 {active_protocol_digest!r}"
            "——換尺後，舊的 PASS 不得沿用")


#: 供稽核與報表引用；與 protocol v1 的 digest 同源
ACTIVE_PROTOCOL_DIGEST: Final[str] = "4690a258f502d98d"


# ════════════════════════════════════════════════════════════════════
# gate 判定（任務 3.1／3.2｜R1.1, R1.2, R1.3, R3.1）
# ════════════════════════════════════════════════════════════════════

Verdict = Literal["allow", "block", "abstain"]


@dataclass(frozen=True)
class GateDecision:
    """三值判定 ＋ 可稽核的理由（命中哪些正／反向證據）。"""

    verdict: Verdict
    reason: str
    positive: FrozenSet[str] = frozenset()
    counter: FrozenSet[str] = frozenset()


def instance_reference_gate(evidence, *, face_requires_instance: bool) -> GateDecision:
    """判定表（design v1.2）——**不得順手加產品 heuristic**：

    ```text
    face 不要求 instance          → allow
    positive ≠ ∅ 且 counter = ∅   → allow
    positive = ∅ 且 counter ≠ ∅   → block      ← 雙條件，缺一不可
    positive ≠ ∅ 且 counter ≠ ∅   → abstain
    positive = ∅ 且 counter = ∅   → abstain
    ```

    ⚠️ **反向標記不得採 veto**。實測反例就在凍結案例集裡：

    ```text
    「我的這張點退帳單金額怎麼算出來的」
      positive = {possessive}   counter = {explanation_request}
    ```

    寫成 `if counter: block` 會誤殺這一筆——正是前案 3.4
    「rule 側修好、instance 側受傷」的形態（design 決策 4）。

    ⚠️ **`abstain` 是第三態，不是「還沒決定的 allow」**。
    rollout 政策（不阻擋）由 `suppresses_hint()` 表示，
    **與 verdict 分屬兩欄**——政策效果像 allow，不代表語義是 allow：
    稽核、holdout 的 abstain 率、未來 L5 clarification 都要讀得到它。
    """
    positive = frozenset(getattr(evidence, "positive", frozenset()) or frozenset())
    counter = frozenset(getattr(evidence, "counter", frozenset()) or frozenset())

    if not face_requires_instance:
        return GateDecision("allow", "face-not-instance-requiring", positive, counter)
    if positive and not counter:
        return GateDecision("allow", f"positive={sorted(positive)}", positive, counter)
    if not positive and counter:
        return GateDecision("block", f"no-positive+counter={sorted(counter)}", positive, counter)
    if positive and counter:
        return GateDecision(
            "abstain", f"mixed positive={sorted(positive)} counter={sorted(counter)}",
            positive, counter)
    return GateDecision("abstain", "no-signal", positive, counter)


def suppresses_hint(decision: GateDecision) -> bool:
    """**rollout action**：只有 `block` 抑制 Hint；`abstain` 維持既有行為。

    ⚠️ 與 `verdict` 分屬兩件事——把兩者併成一個布林，`abstain` 就在型別上消失了。
    """
    return decision.verdict == "block"
