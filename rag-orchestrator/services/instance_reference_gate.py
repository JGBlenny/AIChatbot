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

    ⚠️ **任務 6 已於 2026-08-24 裁決：`REFUTED`** → `holdout.status = "failed"`。

    裁決依據不是「準確率低於某條事後訂的門檻」（該門檻從未凍結，事後訂即違反 Req.3.5），
    而是一個**不依賴數值的結構性反證**：

    ```text
    50 筆未見語料，gate ON 與 OFF 的 routing 逐筆完全相同 → routing effect = 0/50
    block 11 筆，實際抑制 Hint = 0 筆
    abstain 32/50 = 64%
    ```

    ⚠️ `failed` 與 `not_run` **在啟用守門上同樣拒絕**，但語義不同、且不得互換：
    前者代表**已驗且未通過**，後者代表**尚未驗**。寫成 `not_run` 會抹掉這次反證。
    ⚠️ **SHALL NOT** 因為想讓 gate 可啟用而把它改回 `not_run` 或改成 `passed`。
    """
    from services.instance_evidence import (COUNTER_PATTERNS, POSITIVE_PATTERNS,
                                            InstanceEvidenceExtractor)
    version = InstanceEvidenceExtractor.RULESET_VERSION
    return RulesetManifest(
        version=version,
        positive_patterns=POSITIVE_PATTERNS,
        counter_patterns=COUNTER_PATTERNS,
        digest=ruleset_digest(version, POSITIVE_PATTERNS, COUNTER_PATTERNS),
        holdout=HoldoutRecord(
            status="failed",
            ruleset_digest=ruleset_digest(version, POSITIVE_PATTERNS, COUNTER_PATTERNS),
            protocol_digest=ACTIVE_PROTOCOL_DIGEST,
            dataset_id="holdout-2026Q3-D1",
            dataset_digest="84134fc929554f00",   # labels_digest bc76fb74215d9852
        ),
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


# ════════════════════════════════════════════════════════════════════
# membership × rollout scope（design erratum 01｜任務 3.3／4.1｜R2.5, R5.2, R8）
# ════════════════════════════════════════════════════════════════════
#
# erratum 01 把兩個曾被混在一起的命題拆開，**兩層皆成立才實際納管**：
#
#   is_instance_requiring_face(face)   ← C：Face 語義上是否要求個體指涉（產品／架構語義）
#   in_gate_rollout_scope(face)        ← D：本次 release 是否已驗證可對它啟用（成熟度邊界）
#   gate_applies_to(face)              ← C ∧ D，**沒有第三條隱藏推論**
#
# ⚠️ 兩層不得摺疊：摺疊後 Level B 擴張就得回頭改 **membership 定義**，
#    語義契約會退化成 rollout 清單——那正是 erratum 否決「明列 key 作為 membership」的理由。

#: Face 自身宣告的鍵（`grounding_scope` 內，與 `required_slots`／`enabled_gate` 同處）
INSTANCE_REFERENCE_KEY: Final[str] = "requires_instance_reference"

#: **D：本次 release 已驗證可納管者**（Level A）。
#: ⚠️ 它表示「這次驗到哪」，**不表示**「這個 Face 語義上需要 instance」——後者只看 C。
LEVEL_A_INSTANCE_GATE_SCOPE: Final[frozenset] = frozenset({"bill_diagnosis"})


def is_instance_requiring_face(config) -> bool:
    """**C**：只讀 Face 自己的明示契約 `grounding_scope.requires_instance_reference`。

    ⚠️ **不得 fallback**：`bool(required_slots)`／`bill_ref ∈ required_slots`／
    `key == "bill_diagnosis"` 一律不得作為推導來源（erratum 01 原則 ①②）。
    ⚠️ 缺欄位 → `False`（fail-closed by scope）：舊 Face 未補宣告時
    **不得**被意外納管，Level A 的隔離才是結構性的而非靠運氣。
    """
    scope = getattr(config, "grounding_scope", None) or {}
    return scope.get(INSTANCE_REFERENCE_KEY) is True


def in_gate_rollout_scope(config) -> bool:
    """**D**：本次 release 是否已驗證可對此 Face 啟用 gate。"""
    return getattr(config, "key", None) in LEVEL_A_INSTANCE_GATE_SCOPE


def gate_applies_to(config) -> bool:
    """**C ∧ D**。此處刻意只有一行——任何額外推論都會讓兩層契約失效。"""
    return is_instance_requiring_face(config) and in_gate_rollout_scope(config)


# ════════════════════════════════════════════════════════════════════
# 啟用狀態（任務 4.1｜R7.1, R3.5）
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ **requested 與 authorized 是兩件事，不得摺疊成「flag=true → gate active」**：
#
#   requested  = 有人把旗標打開（運維意圖）
#   authorized = 規則集已通過 **matching** holdout（證據授權）
#   active     = requested AND authorized
#
# 於是「把 env 設成 true」**不足以**讓 gate 真正生效——
# Task 6 的 unseen holdout 裁決前，production candidate 一律處於「不可真正放行」狀態。

#: 運維旗標；**預設 false**
INSTANCE_REFERENCE_GATE_FLAG: Final[str] = "INSTANCE_REFERENCE_GATE"


def gate_requested() -> bool:
    """運維意圖：旗標是否被打開（預設 false）。"""
    import os
    return os.getenv(INSTANCE_REFERENCE_GATE_FLAG, "false").lower() == "true"


def gate_authorized() -> bool:
    """證據授權：當前規則集是否已通過 matching holdout。

    ⚠️ 這裡**吞掉的是 `GateNotEnablable`，不是任意例外**——
    把所有例外都當成「未授權」會讓「守門壞掉」與「尚未通過」無法區分。
    """
    try:
        assert_gate_enablable(current_manifest(), active_protocol_digest=ACTIVE_PROTOCOL_DIGEST)
        return True
    except GateNotEnablable:
        return False


def gate_active() -> bool:
    """`requested AND authorized`。**此處只有一行合取，沒有第三條旁路。**"""
    return gate_requested() and gate_authorized()
